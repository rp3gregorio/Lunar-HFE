"""Joint (A, K_d) retrieval under other radiative factors chi and site-specific densities (2026-10-05).

The joint retrieval holds chi = 2.7 (Hayne et al. 2017) and the deep density
rho_d = 1800 kg m^-3 at both sites. Because the diffusivity fixes the effective
conductivity, K_d scales with 1 / (1 + chi (T/T_ref)^3) and with rho_d, so both
choices set the absolute values. This script re-runs the joint retrieval
  * for chi = 1.5, 2.2, 2.45, 2.95 and 3.2, each on an albedo grid wide enough
    that the fitted albedo does not sit on its edge (a lower chi gives a colder
    deep column, which a darker surface must compensate), and
  * with the site-specific deep densities of Langseth et al. (1976): the
    midpoints of their core ranges, 1825 kg m^-3 at A15 (1750-1900) and
    1960 kg m^-3 at A17 (1830-2090).

Reads:  results/joint_fit_sensitivities.json (nominal, same K_d grid)
Writes: results/joint_chi_density.json, results/joint_chi_density_cache.npz (resumable)
Runtime: ~50 min on 5 workers (keep the machine awake; resumable).
"""
from __future__ import annotations
import json, sys, pathlib, time
from multiprocessing import Pool
_REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO)); sys.path.insert(0, str(_REPO / "src")); sys.path.insert(0, str(_REPO / "pipeline" / "compute"))

import numpy as np
import compute_joint_albedo_fit as jf
from compute_joint_fit_sensitivities import fit, KD_V, A_V

N_WORKERS = 5
CHIS = (1.5, 2.2, 2.45, 2.95, 3.2)
A_LOW = np.round(np.arange(0.0, 0.20001, 0.005), 4)       # chi < 2.7: darker surfaces needed
A_HIGH = np.round(np.arange(0.10, 0.26001, 0.005), 4)     # chi > 2.7: brighter surfaces needed
A_COARSE = np.round(np.arange(0.0, 0.20001, 0.01), 4)     # chi = 1.5: only checks whether any albedo fits
RHO_SITE = {"A15": 1825.0, "A17": 1960.0}                 # Langseth et al. (1976) core-range midpoints
CACHE = _REPO / "results" / "joint_chi_density_cache.npz"
NAMES = ("Tz", "prof", "Ts", "clos", "kap")


def variants():
    v = []
    for s in ("A15", "A17"):
        for chi in CHIS:
            grid = A_COARSE if chi == 1.5 else (A_LOW if chi < 2.7 else A_HIGH)
            v.append((s, f"chi_{chi:g}", {"chi": chi}, grid))
        v.append((s, "rho_site", {"rho_d": RHO_SITE[s]}, A_V))
    return v


def key(vi, A):
    return f"v{vi}_A{A:.4f}"


def main():
    var = variants()
    done = {}
    if CACHE.exists():
        c = np.load(CACHE, allow_pickle=False)
        for k in {f.rsplit("_", 1)[0] for f in c.files}:
            done[k] = tuple(c[f"{k}_{nm}"] for nm in NAMES)
    jobs = [(vi, float(A)) for vi, (s, name, ov, grid) in enumerate(var) for A in grid if key(vi, float(A)) not in done]
    print(f"{len(done)} rows cached, {len(jobs)} to solve ({len(jobs) * len(KD_V)} solves)", flush=True)

    def save():
        np.savez_compressed(CACHE, **{f"{k}_{nm}": v[i] for k, v in done.items() for i, nm in enumerate(NAMES)})

    if jobs:
        args = [(var[vi][0], A, dict(var[vi][2], kd_grid=KD_V.tolist())) for vi, A in jobs]
        t0 = time.time()
        with Pool(N_WORKERS) as pool:
            for n, r in enumerate(pool.imap(jf.solve_row, args, chunksize=1)):
                vi, A = jobs[n]
                done[key(vi, A)] = r[2:]
                if (n + 1) % 20 == 0 or n + 1 == len(jobs):
                    save(); print(f"  {n+1}/{len(jobs)} rows ({time.time()-t0:.0f} s)", flush=True)

    sens = json.loads((_REPO / "results" / "joint_fit_sensitivities.json").read_text())
    out = dict(meta=dict(chis=list(CHIS), rho_site=RHO_SITE, kd_grid_mW=(KD_V * 1e3).tolist(),
                         note="nominal = chi 2.7, rho_d 1800, same K_d grid (joint_fit_sensitivities nominal_compact)"),
               sites={})
    for s in ("A15", "A17"):
        z, Tobs = jf.observed(s)
        site = {"nominal": sens["sites"][s]["variants"]["nominal_compact"]["with_diffusivity"]}
        for vi, (vs, name, ov, grid) in enumerate(var):
            if vs != s:
                continue
            st = lambda i: np.stack([done[key(vi, float(A))][i] for A in grid])
            res = fit(s, z, Tobs, *(st(i) for i in range(5)), grid, KD_V, True)
            site[name] = res
            print(f"  {s} {name:10s} A*={res['A']:.4f} K_d*={res['kd_star_mW']:6.2f}{' EDGE' if res['at_grid_edge'] else '     '} "
                  f"RMSE {res['sensor_rmse_K']:.3f} bias {res['bias_K']:+.2f} <Ts> {res['surface_mean_K']:.1f} "
                  f"kappa {np.round(res['kappa_model'], 2).tolist()} grad {res['gradient_model_K_per_m']:.2f}", flush=True)
        out["sites"][s] = site
    out["contrast_mW"] = {name: out["sites"]["A17"][name]["kd_star_mW"] - out["sites"]["A15"][name]["kd_star_mW"]
                          for name in out["sites"]["A15"]}
    (_REPO / "results" / "joint_chi_density.json").write_text(json.dumps(out, indent=1))
    print("contrast:", {k: round(v, 2) for k, v in out["contrast_mW"].items()})
    print("wrote results/joint_chi_density.json")


if __name__ == "__main__":
    main()
