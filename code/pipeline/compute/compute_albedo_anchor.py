"""Anchor the effective albedo to the Hayne et al. (2017) standard model (audit 2026-10-04).

Why
---
The site albedos (0.131 / 0.137) are effective, level-setting values. This
script ties them to the published standard and records what the published
albedo treatments give at the two HFE sites, so the paper can state why none
of them is used directly.

Part 1 -- does our solver reproduce Hayne et al.'s own Apollo comparison?
    Hayne et al. (2017, Fig. A1) compare their standard model (Table A1:
    K_s = 7.4e-4, K_d = 3.4e-3, H = 0.06 m, chi = 2.7, eps = 0.95,
    Q = 0.018 W m^-2, A0 = 0.12) with the Apollo diurnal means (Keihm et al.
    1973a,b, their Table A2): surface ~217 / 214 / 211 K and 1 m ~261 / 257 /
    253 K at 0 / 20 / 26 deg (read from the figure). We solve the same set at
    those latitudes with (a) a constant A = 0.12 and (b) A0 = 0.12 with their
    eq. A8 angular law, and report the diurnal-mean surface and 1 m
    temperatures and the equatorial noon maximum / night minimum (their
    Table A2: 385 K / 95 K).

Part 2 -- the published albedo treatments, applied at the two sites
    Full K_d retrievals (compute_albedo_sensitivity.run_case) with
      * Hayne et al. (2017) standard: A0 = 0.12 + eq. A8 (a = 0.06, b = 0.25);
      * Feng et al. (2020) eq. 9, as used by Martinez & Siegler (2021):
        A0 = 0.39 x LOLA 1064-nm normal albedo + (1 - cos^0.2752 theta);
      * Vasavada et al. (2012) eq. 1 (Keihm 1984 form, a = 0.045, b = 0.14),
        with the site map A0 and with the mare mean A0 = 0.07 they quote.
    (Map value + eq. A8, and the constant map value, are already cases in
    albedo_sensitivity.json.)

Part 3 -- the global model at its own albedo
    Copied from albedo_sensitivity.json (constant A = 0.12): K_d*, mean bias,
    the model gradient at K_d = 3.4 vs observed, and Delta-AICc.

Part 4 -- what survives every admissible albedo treatment
    Over all constant, scaled-angular and published-law cases that pass both
    in-situ checks (mean sensor bias <= 1 K; diurnal-mean surface within
    +-5 K of Keihm et al. 1973), per site: the K_d* range, the model gradient
    at K_d = 3.4, the Delta-AICc range, and the inter-site ordering under the
    shared published law (Vasavada et al. 2012 with A0 = 0.07 at both sites).

Reads:  results/albedo_diagnostics.json, results/albedo_sensitivity.json
Writes: results/albedo_anchor.json
Runtime: ~6 min on 4 workers.

Run with:
    python pipeline/compute/compute_albedo_anchor.py
"""
from __future__ import annotations
import json, sys, pathlib, time
from multiprocessing import Pool

_REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO))
sys.path.insert(0, str(_REPO / "src"))
sys.path.insert(0, str(_REPO / "pipeline" / "compute"))

import numpy as np

A0_STANDARD = 0.12                     # Hayne et al. (2017) Table A1 (lunar average)
Q_STANDARD = 0.018                     # Hayne et al. (2017) Table A1 [W m^-2]
KD_STANDARD = 3.4e-3                   # Hayne et al. (2017) Table A1 [W m^-1 K^-1]
FIG_A1_LATS = (0.0, 20.19, 26.13)      # equator, A17, A15
FIG_A1_READ = {"surface_K": (217, 214, 211), "one_m_K": (261, 257, 253)}   # read from their Fig. A1
HAYNE_TO_LOLA, FENG_FROM_LOLA = 0.49, 0.39  # Hayne (2017) Sec. 3.2.2; Feng (2020) eq. 9
VASAVADA_AB = (0.045, 0.14)            # Vasavada et al. (2012) eq. 1
VASAVADA_MARE_A0 = 0.07                # Vasavada et al. (2012) para. 27


def standard_column(job):
    """Hayne et al. (2017) standard set at one latitude, constant or eq. A8 albedo."""
    lat, mode = job
    from lunar.config import HAYNE, GRID, DT_STEP, T_LUNAR, EQ_Z_ANCHOR, EQ_N_INNER, EQ_MAX_OUTER, EQ_ANCHOR_TOL
    from lunar.grid import make_geometric_grid
    from lunar.solver import periodic_time_grid, standard_insolation
    from lunar.properties import conductivity_hayne, specific_heat
    from lunar.equilibrium import solve_periodic_equilibrium
    G = make_geometric_grid(**GRID)
    t = periodic_time_grid(DT_STEP)
    S = standard_insolation(lat, t)
    if mode == "eq_A8":
        mu = np.cos(np.deg2rad(lat)) * np.cos(2 * np.pi * t / T_LUNAR)
        th = np.arccos(np.clip(mu, 0, 1))
        A = A0_STANDARD + 0.06 * (th / (np.pi / 4)) ** 3 + 0.25 * (th / (np.pi / 2)) ** 8
        insol, alb = (1 - np.clip(A, 0, 1)) * S, 0.0
    else:
        insol, alb = S, A0_STANDARD
    eq = solve_periodic_equilibrium(
        grid=G, t=t, insolation=insol, albedo=alb, emissivity=0.95, Q_b=Q_STANDARD,
        K_func=lambda T, z: conductivity_hayne(T, z, Ks=HAYNE["K_S"], Kd=KD_STANDARD, H=HAYNE["H"], chi=HAYNE["CHI"]),
        cp_func=lambda T: specific_heat(T, model="hayne"), T_guess=250.0, z_anchor=EQ_Z_ANCHOR,
        n_inner=EQ_N_INNER, max_outer=EQ_MAX_OUTER, anchor_tol_K=EQ_ANCHOR_TOL,
        hayne_params=(HAYNE["K_S"], KD_STANDARD, HAYNE["H"], HAYNE["CHI"]))
    Ts = eq.out.T_surface
    return dict(lat=lat, albedo=mode, surface_mean_K=float(Ts.mean()),
                T_1m_K=float(np.interp(1.0, G.z_mid, eq.T_mean)),
                noon_max_K=float(Ts.max()), night_min_K=float(Ts.min()))


def site_case(case):
    import compute_albedo_sensitivity as cas
    r = cas.run_case(case)
    keep = ("site", "label", "law", "A0", "a", "b", "kd_star_mW", "rmse_star_K", "at_grid_edge", "n_local_minima",
            "bias_K", "surface_mean_K", "surface_mean_obs_K", "gradient_model_at_global", "gradient_observed",
            "rmse_global_K", "delta_aicc_global_minus_fit")
    return {k: r[k] for k in keep if k in r}


def main():
    t0 = time.time()
    diag = json.loads((_REPO / "results" / "albedo_diagnostics.json").read_text())["site_albedo"]
    a0 = {s: diag[s]["bond_normal_incidence"] for s in ("A15", "A17")}
    lola = {s: {k: v / HAYNE_TO_LOLA for k, v in a0[s].items()} for s in a0}
    cases = []
    for s in ("A15", "A17"):
        cases.append(dict(site=s, family="angular", label="Hayne 2017 standard (A0 0.12 + eq. A8)",
                          law="keihm", A0=A0_STANDARD, a=0.06, b=0.25, f=1.0))
    for s, k in (("A15", "mean3x3"), ("A17", "pixel"), ("A17", "mean3x3")):
        cases.append(dict(site=s, family="angular", label=f"Feng 2020 eq. 9, LOLA {k}",
                          law="feng", A0=FENG_FROM_LOLA * lola[s][k], f=1.0))
    for s, k in (("A15", "mean3x3"), ("A17", "pixel"), ("A17", "mean3x3")):
        cases.append(dict(site=s, family="angular", label=f"Vasavada 2012 eq. 1, map A0 {k}",
                          law="keihm", A0=a0[s][k], a=VASAVADA_AB[0], b=VASAVADA_AB[1], f=1.0))
    for s in ("A15", "A17"):
        cases.append(dict(site=s, family="angular", label="Vasavada 2012 eq. 1, mare A0 0.07",
                          law="keihm", A0=VASAVADA_MARE_A0, a=VASAVADA_AB[0], b=VASAVADA_AB[1], f=1.0))
    jobs = [(lat, m) for lat in FIG_A1_LATS for m in ("constant", "eq_A8")]
    with Pool(4) as pool:
        fig = pool.map(standard_column, jobs)
        for r in fig:
            print(f"  Fig. A1 check  lat {r['lat']:5.2f}  {r['albedo']:8s}: surface {r['surface_mean_K']:6.1f} K, "
                  f"1 m {r['T_1m_K']:6.1f} K, noon {r['noon_max_K']:5.1f}, night min {r['night_min_K']:5.1f}", flush=True)
        sites = pool.map(site_case, cases)
        for r in sites:
            print(f"  {r['site']} {r['label']:42s} A0={r['A0']:.3f}: K_d*={r['kd_star_mW']:6.2f}"
                  f"{' EDGE' if r['at_grid_edge'] else '     '} bias={r['bias_K']:+.2f} K  "
                  f"<Ts>={r['surface_mean_K']:.1f} (obs {r['surface_mean_obs_K']:.0f}+-5)", flush=True)
    sens = json.loads((_REPO / "results" / "albedo_sensitivity.json").read_text())["cases"]
    own = [{k: c[k] for k in ("site", "A", "kd_star_mW", "rmse_star_K", "bias_K", "surface_mean_K",
                              "gradient_model_at_global", "gradient_observed", "rmse_global_K",
                              "delta_aicc_global_minus_fit")}
           for c in sens if c["family"] == "constant" and abs(c["A"] - A0_STANDARD) < 1e-9]
    for r in own:
        print(f"  global model at its own albedo, {r['site']}: bias {r['bias_K']:+.2f} K, gradient at 3.4 "
              f"{r['gradient_model_at_global']:.2f} vs {r['gradient_observed']:.2f} K/m, dAICc {r['delta_aicc_global_minus_fit']:+.1f}")
    ok = lambda c: (abs(c["bias_K"]) <= 1.0 and abs(c["surface_mean_K"] - c["surface_mean_obs_K"]) <= 5.0
                    and not c["at_grid_edge"])
    pool_cases = [c for c in sens if c["family"] in ("constant", "angular")] + sites
    admissible = {}
    for s in ("A15", "A17"):
        p = [c for c in pool_cases if c["site"] == s and ok(c)]
        rng = lambda k: [min(c[k] for c in p), max(c[k] for c in p)]
        admissible[s] = dict(n_cases=len(p), kd_star_mW=rng("kd_star_mW"),
                             gradient_model_at_global=rng("gradient_model_at_global"),
                             gradient_observed=p[0]["gradient_observed"],
                             delta_aicc_global_minus_fit=rng("delta_aicc_global_minus_fit"))
        print(f"  admissible {s}: {len(p)} cases, K_d* {admissible[s]['kd_star_mW'][0]:.2f}-{admissible[s]['kd_star_mW'][1]:.2f}, "
              f"dAICc {admissible[s]['delta_aicc_global_minus_fit'][0]:+.1f}..{admissible[s]['delta_aicc_global_minus_fit'][1]:+.1f}")
    shared = {r["site"]: r["kd_star_mW"] for r in sites if r["label"].endswith("mare A0 0.07")}
    admissible["shared_vasavada_mare"] = dict(kd_star_mW=shared, contrast_A17_minus_A15=shared["A17"] - shared["A15"])
    out = dict(meta=dict(purpose="anchor the effective albedo to the Hayne et al. (2017) standard (audit 2026-10-04)",
                         fig_A1_read_from_figure=dict(lat_deg=FIG_A1_LATS, **FIG_A1_READ),
                         table_A2=dict(equator_noon_K=385, equator_presunrise_K=95),
                         runtime_s=round(time.time() - t0, 1)),
               fig_A1_reproduction=fig, published_laws_at_sites=sites, global_model_at_A0_standard=own,
               admissible_treatments=admissible)
    p = _REPO / "results" / "albedo_anchor.json"
    p.write_text(json.dumps(out, indent=1))
    print(f"wrote {p.relative_to(_REPO)} in {time.time() - t0:.0f} s")


if __name__ == "__main__":
    main()
