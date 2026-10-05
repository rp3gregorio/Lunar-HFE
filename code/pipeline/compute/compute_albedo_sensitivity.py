"""Albedo sensitivity of the per-site K_d retrieval (audit 2026-10-04).

Why
---
The production retrieval holds the Bond albedo constant at 0.131 (A15) and
0.137 (A17); no derivation of these values survives. The documented map value
(Hayne et al. 2017: 0.49 x LOLA 1064-nm normal albedo; read by
compute_albedo_diagnostics.py) is lower, and with it the modeled column runs
2-5 K warm. This script maps how the retrieval responds to the albedo choice,
under three families of surface treatment, so the paper can state what is and
is not robust to it.

Families (each case = a full K_d sweep at one site)
---------------------------------------------------
1. "constant"  constant albedo A = 0.08-0.20 (step 0.01), refined to step
               0.0025 over 0.12-0.16 where the in-situ band lies, plus the
               adopted site value, both sites.
2. "angular"   Hayne et al. (2017, eq. A8) incidence-dependent albedo,
               A(theta) = A0 + f [0.06 (theta/45 deg)^3 + 0.25 (theta/90 deg)^8],
               with A0 the map value at the site and the law's strength
               f = 0, 0.25, 0.5, 0.75, 1 (f = 0: constant map albedo;
               f = 1: Hayne's published law). Applied exactly: the solver is
               given the ABSORBED flux (1 - A(theta)) S with albedo 0, so the
               albedo is not counted twice.
3. "chi"       constant map albedo with the radiative-conductivity parameter
               chi = 1.8, 2.1, 2.4, 2.7 -- tests whether a weaker radiative
               rectification, rather than a higher albedo, reconciles the map
               albedo with the measured temperatures.

Per case: K_d* (0.5 mW sweep 1-26 mW, then a 0.1 mW band around the minimum,
shared vertex routine), RMSE*, mean bias, offset-removed misfit, number of
local minima on the coarse sweep, grid-edge flag, model gradient across the
retained sensors at K_d* and at the global 3.4, RMSE at 3.4, Delta-AICc
(global minus site fit, letter convention), and the diurnal-mean surface
temperature at K_d* -- compared with the Apollo surface means of Keihm et al.
(1973a,b) as tabulated by Hayne et al. (2017, Table A2): 211 +- 5 K (A15,
26 N) and 216 +- 5 K (A17, 20 N).

Reads:  results/albedo_diagnostics.json  (site map A0; run that script first)
Writes: results/albedo_sensitivity.json

Runtime: ~35 min on 4 workers (Hayne njit fast path).

Run with:
    python pipeline/compute/compute_albedo_sensitivity.py
"""
from __future__ import annotations
import json, sys, pathlib, time
from multiprocessing import Pool

_REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO))
sys.path.insert(0, str(_REPO / "src"))
sys.path.insert(0, str(_REPO / "pipeline" / "compute"))

import numpy as np

N_WORKERS = 4
KD_COARSE = np.round(np.arange(1.0, 26.01, 0.5), 3) * 1e-3
KD_GLOBAL = 3.4e-3
ANG_A, ANG_B = 0.06, 0.25                       # Hayne et al. (2017) eq. A8
FENG_P = 0.2752                                 # Feng et al. (2020) eq. 9 exponent
SURFACE_MEAN_OBS = {"A15": 211.0, "A17": 216.0}  # Keihm et al. (1973a,b) via Hayne (2017) Table A2
CONST_ALBEDOS = np.round(np.arange(0.08, 0.2001, 0.01), 3)
FINE_ALBEDOS = np.round(np.arange(0.12, 0.16001, 0.0025), 4)   # in-situ band, resolved
# The fixed site albedos used up to v1.1-jgr, kept as an explicit comparison row
# (letter Fig. 3 cross, SI albedo table) now that config.SITES holds the fitted values.
COMPARISON_ALBEDOS = (0.131, 0.137)
ANG_STRENGTHS = (0.0, 0.25, 0.5, 0.75, 1.0)
CHI_VALUES = (1.8, 2.1, 2.4, 2.7)


def _setup():
    import retrieve_kd as rk
    from lunar.config import SITES, GRID, DT_STEP, T_LUNAR
    from lunar.grid import make_geometric_grid
    from lunar.solver import periodic_time_grid, standard_insolation
    return rk, SITES, make_geometric_grid(**GRID), periodic_time_grid(DT_STEP), standard_insolation, T_LUNAR


def run_case(case):
    """One full K_d sweep for one (site, surface treatment)."""
    from lunar.config import HAYNE, EQ_Z_ANCHOR, EQ_N_INNER, EQ_MAX_OUTER, EQ_ANCHOR_TOL
    from lunar.properties import conductivity_hayne, specific_heat
    from lunar.equilibrium import solve_periodic_equilibrium
    from retrieve_kd import kd_star_from_residuals
    rk, SITES, G, T, standard_insolation, T_LUNAR = _setup()
    cfg = SITES[case["site"]]
    o = rk.extract_sensor_stability(cfg["mission"], min_depth_cm=cfg["MIN_DEPTH_CM"])
    m = np.asarray(o["deep_mask"], bool)
    z = np.asarray(o["depth_cm_all"])[m] / 100.0
    Tobs = np.asarray(o["T_eq_all"])[m]
    S = standard_insolation(cfg["lat"], T)
    if case["family"] == "angular":
        mu = np.cos(np.deg2rad(cfg["lat"])) * np.cos(2 * np.pi * T / T_LUNAR)
        th = np.arccos(np.clip(mu, 0.0, 1.0))
        if case.get("law") == "feng":   # Feng et al. (2020) eq. 9: A0 + (1 - cos^p theta)
            A = case["A0"] + case["f"] * (1.0 - np.clip(mu, 0.0, 1.0) ** FENG_P)
        else:                           # Keihm (1984) form; Hayne (2017) constants unless given
            a, b = case.get("a", ANG_A), case.get("b", ANG_B)
            A = case["A0"] + case["f"] * (a * (th / (np.pi / 4)) ** 3 + b * (th / (np.pi / 2)) ** 8)
        insol, albedo = (1.0 - np.clip(A, 0.0, 1.0)) * S, 0.0
    else:
        insol, albedo = S, case["A"]
    chi = case.get("chi", HAYNE["CHI"])
    cache = {}

    def solve(kd):
        key = round(kd, 9)
        if key not in cache:
            eq = solve_periodic_equilibrium(
                grid=G, t=T, insolation=insol, albedo=albedo, emissivity=cfg["emissivity"],
                Q_b=cfg["Q_BASAL"],
                K_func=lambda TT, zz, k=kd: conductivity_hayne(TT, zz, Ks=HAYNE["K_S"], Kd=k,
                                                              H=HAYNE["H"], chi=chi),
                cp_func=lambda TT: specific_heat(TT, model="hayne"), T_guess=cfg["T_MEAN_EFF"],
                z_anchor=EQ_Z_ANCHOR, n_inner=EQ_N_INNER, max_outer=EQ_MAX_OUTER,
                anchor_tol_K=EQ_ANCHOR_TOL, hayne_params=(HAYNE["K_S"], kd, HAYNE["H"], chi))
            cache[key] = (np.interp(z, G.z_mid, eq.T_mean), float(eq.out.T_surface.mean()))
        return cache[key]

    Rc = np.array([solve(kd)[0] - Tobs for kd in KD_COARSE]).T
    rmse_c = np.sqrt((Rc ** 2).mean(axis=0))
    interior = (rmse_c[1:-1] < rmse_c[:-2]) & (rmse_c[1:-1] < rmse_c[2:])
    k0 = KD_COARSE[int(np.argmin(rmse_c))]
    dense = np.round(np.arange(max(k0 - 1.0e-3, 0.5e-3), k0 + 1.0001e-3, 0.1e-3), 7)
    grid = np.unique(np.round(np.concatenate([KD_COARSE, dense]), 7))   # round: no last-bit twins
    R = np.array([solve(kd)[0] - Tobs for kd in grid]).T
    ks, rs = kd_star_from_residuals(R, grid, warn_coarse=False)
    edge = bool(ks <= grid[0] + 1e-12 or ks >= grid[-1] - 1e-12)
    T_ks, Ts_ks = solve(float(ks))
    T_g, _ = solve(KD_GLOBAL)
    ols = lambda TT: float(np.polyfit(z, TT, 1)[0])
    n = len(z)
    aicc = lambda r, k: n * np.log(r ** 2) + 2 * k + 2 * k * (k + 1) / (n - k - 1)
    rg = float(np.sqrt(np.mean((T_g - Tobs) ** 2)))
    r = T_ks - Tobs
    return dict(case, kd_star_mW=float(ks * 1e3), rmse_star_K=float(rs), at_grid_edge=edge,
                n_local_minima=int(interior.sum()), bias_K=float(r.mean()),
                offset_removed_misfit_K=float(r.std()),
                gradient_model_at_kd_star=ols(T_ks), gradient_model_at_global=ols(T_g),
                gradient_observed=ols(Tobs), rmse_global_K=rg,
                delta_aicc_global_minus_fit=float(aicc(rg, 1) - aicc(rs, 2)),
                surface_mean_K=Ts_ks, surface_mean_obs_K=SURFACE_MEAN_OBS[case["site"]])


def main():
    from lunar.config import SITES
    t0 = time.time()
    diag = json.loads((_REPO / "results" / "albedo_diagnostics.json").read_text())["site_albedo"]
    a0 = {"A15": {"map": diag["A15"]["bond_normal_incidence"]["mean3x3"]},
          "A17": {"map_pixel": diag["A17"]["bond_normal_incidence"]["pixel"],
                  "map": diag["A17"]["bond_normal_incidence"]["mean3x3"],
                  "map_5x5": diag["A17"]["bond_normal_incidence"]["mean5x5"]}}
    cases = []
    for s in ("A15", "A17"):
        grid_A = np.unique(np.round(np.concatenate([CONST_ALBEDOS, FINE_ALBEDOS, COMPARISON_ALBEDOS,
                                                    [SITES[s]["albedo"]]]), 4))
        cases += [dict(site=s, family="constant", A=float(A)) for A in grid_A]
        for lbl, A0 in a0[s].items():
            cases += [dict(site=s, family="angular", A0_label=lbl, A0=float(A0), f=f) for f in ANG_STRENGTHS]
        cases += [dict(site=s, family="chi", A=float(a0[s]["map"]), chi=c) for c in CHI_VALUES]
    print(f"{len(cases)} cases on {N_WORKERS} workers", flush=True)
    out = []
    with Pool(N_WORKERS) as pool:
        for r in pool.imap_unordered(run_case, cases):
            out.append(r)
            tag = {"constant": f"A={r.get('A', 0):.3f}",
                   "angular": f"{r.get('A0_label','')} A0={r.get('A0', 0):.3f} f={r.get('f', 0):.2f}",
                   "chi": f"A={r.get('A', 0):.3f} chi={r.get('chi', 0):.1f}"}[r["family"]]
            print(f"[{len(out):3d}/{len(cases)}] {r['site']} {r['family']:8s} {tag:28s} K_d*={r['kd_star_mW']:6.2f}"
                  f"{' EDGE' if r['at_grid_edge'] else '     '} RMSE*={r['rmse_star_K']:.3f} bias={r['bias_K']:+.2f} "
                  f"minima={r['n_local_minima']} dAICc={r['delta_aicc_global_minus_fit']:+.1f} "
                  f"<Ts>={r['surface_mean_K']:.1f}K ({time.time()-t0:.0f}s)", flush=True)
    order = {"constant": 0, "angular": 1, "chi": 2}
    out.sort(key=lambda r: (r["site"], order[r["family"]], r.get("A0_label", ""), r.get("A", 0), r.get("f", 0), r.get("chi", 0)))
    path = _REPO / "results" / "albedo_sensitivity.json"
    path.write_text(json.dumps(dict(meta=dict(purpose="albedo sensitivity of the per-site K_d retrieval (audit 2026-10-04)",
                                              angular_law=dict(a=ANG_A, b=ANG_B, source="Hayne et al. (2017) eq. A8"),
                                              surface_mean_obs=SURFACE_MEAN_OBS,
                                              runtime_s=round(time.time() - t0, 1)),
                               cases=out), indent=1))
    print(f"wrote {path.relative_to(_REPO)} in {time.time()-t0:.0f} s")


if __name__ == "__main__":
    main()
