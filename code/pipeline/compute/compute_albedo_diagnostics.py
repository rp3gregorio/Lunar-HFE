"""Site-albedo diagnostics (audit 2026-10-02): what albedo do the sites have, and what does the fit need?

Background
----------
config.SITES uses a constant Bond albedo of 0.131 (A15) and 0.137 (A17). No
derivation of these values survives; they predate this repository. This script
documents how they compare with the published albedo convention and with what
the HFE absolute temperatures require.

Q1 -- the published map value at each site
    Hayne et al. (2017, Sec. 3.2.2) build the bolometric Bond albedo as
    0.49 x the LOLA 1064-nm normal albedo (Lucey et al. 2014), scaled to the
    Diviner solar channel. The 10-ppd LOLA map (PDS LRO-L-LOLA-3-RDR-V1,
    lola_gdr/cylindrical/float_img/ldam_10_float.img) is read at the site
    pixel and its 3x3 / 5x5 neighbourhood with HTTP range requests (a few
    hundred bytes; the 26 MB file is not downloaded).

Q2 -- the incidence-weighted (effective) value implied by Hayne's angular law
    A(theta) = A0 + 0.06 (theta/45 deg)^3 + 0.25 (theta/90 deg)^8 (Hayne et al.
    2017, eq. A8), averaged over a lunar day weighted by incident flux.

Q3 -- what the HFE absolute temperatures require
    RMSE-minimising K_d (1 mW grid) at constant albedo A = 0.09-0.18 per site.

Q5 -- does the RMSE-based (AICc) rejection of the global value depend on albedo?
    At A17: dense-vertex K_d*, RMSE*, RMSE at K_d = 3.4 and Delta-AICc
    (global minus site fit, letter convention) at the adopted albedo and at
    the map values (site pixel, 3x3, 5x5).

Q4 -- does the gradient test depend on albedo?
    Model OLS gradient across the retained A17 sensors at K_d = 3.4 and 7.08
    for A = 0.095, 0.106, 0.137.

Writes:
    results/albedo_diagnostics.json

Runtime: ~10 min (Hayne njit fast path).

Run with:
    python pipeline/compute/compute_albedo_diagnostics.py
"""
from __future__ import annotations
import json, sys, pathlib, struct, subprocess, time

_REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO))
sys.path.insert(0, str(_REPO / "src"))
sys.path.insert(0, str(_REPO / "pipeline" / "compute"))

import numpy as np

import retrieve_kd as rk
from lunar.config import (SITES, GRID, DT_STEP, HAYNE, EQ_Z_ANCHOR,
                          EQ_N_INNER, EQ_MAX_OUTER, EQ_ANCHOR_TOL)
from lunar.grid import make_geometric_grid
from lunar.solver import periodic_time_grid, standard_insolation
from lunar.properties import conductivity_hayne, specific_heat
from lunar.equilibrium import solve_periodic_equilibrium

LOLA_URL = ("https://pds-geosciences.wustl.edu/lro/lro-l-lola-3-rdr-v1/lrolol_1xxx/"
            "data/lola_gdr/cylindrical/float_img/ldam_10_float.img")
LOLA_NS, LOLA_PPD = 3600, 10          # samples per line, pixels per degree (label)
HAYNE_SCALE = 0.49                    # Hayne et al. (2017) LOLA -> bolometric Bond
ANG_A, ANG_B = 0.06, 0.25             # Hayne et al. (2017) eq. A8 constants
ALBEDO_SCAN = np.round(np.arange(0.09, 0.181, 0.01), 3)
KD_COARSE = np.arange(1.0, 26.01, 1.0) * 1e-3

GRID_ = make_geometric_grid(**GRID)
T_ = periodic_time_grid(DT_STEP)


def lola_block(lat, lon, half=2):
    """(2h+1)^2 block of LOLA normal albedo centred on the site pixel."""
    i0 = int(np.floor((90.0 - lat) * LOLA_PPD))
    j0 = int(np.floor((lon % 360.0) * LOLA_PPD))
    rows = []
    for i in range(i0 - half, i0 + half + 1):
        a = (i * LOLA_NS + j0 - half) * 4
        # curl (system certificate store) rather than urllib, whose bundled
        # certificates are missing on some macOS Python installs
        raw = subprocess.run(["curl", "-sSf", "--max-time", "60", "-r",
                              f"{a}-{a + (2*half+1)*4 - 1}", LOLA_URL],
                             capture_output=True, check=True).stdout
        rows.append(struct.unpack(f"<{2*half+1}f", raw))
    return np.array(rows)


def effective_albedo(A0, lat):
    """Incident-flux-weighted daily mean of Hayne's A(theta) (no declination, as in the model)."""
    h = np.linspace(-np.pi / 2, np.pi / 2, 20001)
    mu = np.cos(np.deg2rad(lat)) * np.cos(h)
    th = np.arccos(np.clip(mu, 0, 1))
    A = A0 + ANG_A * (th / (np.pi / 4)) ** 3 + ANG_B * (th / (np.pi / 2)) ** 8
    return float(np.sum(A * mu) / np.sum(mu))


def observed(cfg):
    o = rk.extract_sensor_stability(cfg['mission'], min_depth_cm=cfg['MIN_DEPTH_CM'])
    m = np.asarray(o['deep_mask'], bool)
    return np.asarray(o['depth_cm_all'])[m] / 100.0, np.asarray(o['T_eq_all'])[m]


_CACHE = {}
def profile(cfg, kd, albedo):
    key = (cfg['tag'], round(kd, 9), round(albedo, 6))
    if key not in _CACHE:
        eq = solve_periodic_equilibrium(
            grid=GRID_, t=T_, insolation=standard_insolation(cfg['lat'], T_),
            albedo=albedo, emissivity=cfg['emissivity'], Q_b=cfg['Q_BASAL'],
            K_func=lambda T, z, k=kd: conductivity_hayne(T, z, Ks=HAYNE['K_S'], Kd=k,
                                                        H=HAYNE['H'], chi=HAYNE['CHI']),
            cp_func=lambda T: specific_heat(T, model='hayne'), T_guess=cfg['T_MEAN_EFF'],
            z_anchor=EQ_Z_ANCHOR, n_inner=EQ_N_INNER, max_outer=EQ_MAX_OUTER,
            anchor_tol_K=EQ_ANCHOR_TOL,
            hayne_params=(HAYNE['K_S'], kd, HAYNE['H'], HAYNE['CHI']))
        _CACHE[key] = (GRID_.z_mid, eq.T_mean)
    return _CACHE[key]


def main():
    t0 = time.time()
    out = dict(meta=dict(purpose="site-albedo diagnostics (audit 2026-10-02)",
                         lola_product=LOLA_URL, hayne_scale=HAYNE_SCALE,
                         angular_law=dict(a=ANG_A, b=ANG_B)))
    # Q1 + Q2
    maps = {}
    for name, cfg in SITES.items():
        B = lola_block(cfg['lat'], cfg['lon'])
        a0 = dict(pixel=float(HAYNE_SCALE * B[2, 2]),
                  mean3x3=float(HAYNE_SCALE * B[1:4, 1:4].mean()),
                  mean5x5=float(HAYNE_SCALE * B.mean()))
        maps[name] = dict(adopted=cfg['albedo'], lola_block=B.tolist(),
                          bond_normal_incidence=a0,
                          bond_incidence_weighted={k: effective_albedo(v, cfg['lat'])
                                                   for k, v in a0.items()})
        print(f"{name}: adopted {cfg['albedo']} | map A0 {a0} | effective "
              f"{maps[name]['bond_incidence_weighted']}", flush=True)
    out["site_albedo"] = maps
    # Q3
    scan = {}
    for name, cfg in SITES.items():
        z, Tobs = observed(cfg)
        rows = []
        for A in ALBEDO_SCAN:
            rm = np.array([np.sqrt(np.mean((np.interp(z, *profile(cfg, kd, float(A))) - Tobs) ** 2))
                           for kd in KD_COARSE])
            i = int(np.argmin(rm))
            rows.append(dict(albedo=float(A), best_kd_mW=float(KD_COARSE[i] * 1e3),
                             rmse_min_K=float(rm[i]), at_grid_edge=bool(i in (0, len(KD_COARSE) - 1))))
            print(f"  {name} A={A:.3f}: best K_d {KD_COARSE[i]*1e3:4.1f}, RMSE {rm[i]:.3f} K", flush=True)
        scan[name] = rows
    out["albedo_scan"] = scan
    # Q4
    cfg = SITES['A17']; z, Tobs = observed(cfg)
    ols = lambda zz, TT: float(np.polyfit(zz, TT, 1)[0])
    grad = dict(observed_K_per_m=ols(z, Tobs), rows=[])
    for A in (0.095, 0.106, 0.137):
        for kd in (3.4e-3, 7.08e-3):
            Tp = np.interp(z, *profile(cfg, kd, A))
            grad["rows"].append(dict(albedo=A, kd_mW=kd * 1e3, model_gradient_K_per_m=ols(z, Tp),
                                     mean_offset_K=float(np.mean(Tp - Tobs))))
    out["a17_gradient_vs_albedo"] = grad
    # Q5
    from retrieve_kd import kd_star_from_residuals
    def aicc(r, n, k):
        return n * np.log(r ** 2) + 2 * k + 2 * k * (k + 1) / (n - k - 1)
    n = len(z); a0 = maps['A17']['bond_normal_incidence']
    rows = []
    for label, A in (("adopted", cfg['albedo']), ("map_pixel", a0['pixel']),
                     ("map_3x3", a0['mean3x3']), ("map_5x5", a0['mean5x5'])):
        A = round(float(A), 4)
        rm = np.array([np.sqrt(np.mean((np.interp(z, *profile(cfg, kd, A)) - Tobs) ** 2))
                       for kd in KD_COARSE])
        k0 = KD_COARSE[int(np.argmin(rm))]
        grid = np.unique(np.round(np.concatenate([KD_COARSE, np.arange(max(k0 - 1.2e-3, 0.5e-3),
                                                                        k0 + 1.2001e-3, 0.1e-3)]), 7))
        R = np.array([np.interp(z, *profile(cfg, kd, A)) - Tobs for kd in grid]).T
        ks, rs = kd_star_from_residuals(R, grid)
        rg = float(np.sqrt(np.mean((np.interp(z, *profile(cfg, 3.4e-3, A)) - Tobs) ** 2)))
        rows.append(dict(label=label, albedo=A, kd_star_mW=float(ks * 1e3), rmse_star_K=float(rs),
                         rmse_global_K=rg, delta_aicc_global_minus_fit=float(aicc(rg, n, 1) - aicc(rs, n, 2))))
        print(f"  A17 {label:9s} A={A:.4f}: K_d*={ks*1e3:.2f} RMSE*={rs:.3f} RMSE(3.4)={rg:.3f} "
              f"dAICc={rows[-1]['delta_aicc_global_minus_fit']:+.1f}", flush=True)
    out["a17_aicc_vs_albedo"] = rows
    out["meta"]["runtime_s"] = round(time.time() - t0, 1)
    path = _REPO / "results" / "albedo_diagnostics.json"
    path.write_text(json.dumps(out, indent=1))
    print(f"wrote {path.relative_to(_REPO)} in {time.time() - t0:.0f} s")


if __name__ == "__main__":
    main()
