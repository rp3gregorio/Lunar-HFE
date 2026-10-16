#!/usr/bin/env python3
"""The Martinez & Siegler (2021) model with its deep density fitted (letter Sec. 4.3; SI Table S4).

The Martinez & Siegler K(T, rho) has no conductivity to fit; its one knob is the
density. This script scales the deep-asymptote density of the shared density
profile by one factor alpha per site (rho_d = alpha x 1800 kg/m^3), solves the
model at the joint-fit albedo (config.SITES) for each alpha on a grid that runs
past the solid-basalt bound, and finds the minimum of the meter-scale-sensor
RMSE by a parabola through the three lowest grid points. alpha = 1 is the
published model (the forward run of compute_joint_fit_checks.py).

The letter quotes the best densities (1871 and 1861 kg/m^3, inside the Apollo
core range) and that even there the A17 misfit stays at least 1.4 times that of
the joint fit. The same sweep was first run inside compute_headline_rmse.py
(2026-10-05, results/headline_rmse.json, an earlier-phase script that is not
part of the repository); this script repeats only its Martinez part.

Reads:  the Apollo record (lunar.apollo_helpers), config.SITES
Writes: results/martinez_density_fit.json
Runtime: about 20 min (31 densities x 2 sites, about 1 min per Martinez solve, 5 workers).

Run with:
    python pipeline/compute/compute_martinez_density.py
"""
from __future__ import annotations
import json, sys, time
from multiprocessing import Pool
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "pipeline" / "compute"))

from lunar.apollo_helpers import extract_sensor_stability   # noqa: E402
import retrieve_kd as rk                                     # noqa: E402

# deep-density factor alpha (rho_d = alpha x 1800 kg/m^3); runs past the
# solid-basalt bound (alpha ~1.67) so that any second branch would show
ALPHA_GRID = np.linspace(0.7, 2.2, 31)      # rho_d 1260-3960 kg/m^3
RHO_NOMINAL = 1800.0
N_WORKERS = 5                               # the Martinez form has no njit fast path


def deep_obs(cfg):
    obs = extract_sensor_stability(cfg["mission"], min_depth_cm=cfg["MIN_DEPTH_CM"])
    deep = np.asarray(obs["deep_mask"], dtype=bool)
    return np.asarray(obs["depth_cm_all"])[deep] / 100.0, np.asarray(obs["T_eq_all"])[deep]


def _rmse(job):
    site, alpha, z_obs, T_obs = job
    z_mid, T_mean = rk.run_with(rk.SITES[site], k_model="martinez", martinez_alpha=float(alpha))
    r = np.interp(z_obs, z_mid, T_mean) - T_obs
    return float(np.sqrt(np.mean(r ** 2))), float(np.mean(r))


def parabola_min(x, y):
    """Vertex of the parabola through the lowest grid point and its neighbours
    (the grid minimum if it lies on the edge)."""
    k = int(np.argmin(y))
    if not 0 < k < len(x) - 1:
        return float(x[k]), float(y[k])
    xs, ys = x[k - 1:k + 2], y[k - 1:k + 2]
    d = (xs[0] - xs[1]) * (xs[0] - xs[2]) * (xs[1] - xs[2])
    a = (xs[2] * (ys[1] - ys[0]) + xs[1] * (ys[0] - ys[2]) + xs[0] * (ys[2] - ys[1])) / d
    b = (xs[2] ** 2 * (ys[0] - ys[1]) + xs[1] ** 2 * (ys[2] - ys[0]) + xs[0] ** 2 * (ys[1] - ys[2])) / d
    xv = -b / (2 * a) if a > 0 else xs[1]
    return float(xv), float(np.interp(xv, xs, ys))


def main():
    t0 = time.time()
    out = {"meta": dict(purpose="Martinez & Siegler (2021) with the deep density fitted per site (letter Sec. 4.3; SI Table S4)",
                        alpha_grid=ALPHA_GRID.tolist(), rho_nominal_kg_m3=RHO_NOMINAL),
           "sites": {}}
    for s in ("A15", "A17"):
        cfg = rk.SITES[s]
        z, T = deep_obs(cfg)
        jobs = [(s, float(a), z, T) for a in ALPHA_GRID]
        print(f"{s}: {len(jobs)} Martinez solves on {N_WORKERS} workers (albedo {cfg['albedo']:.4f})", flush=True)
        with Pool(N_WORKERS) as pool:
            res = pool.map(_rmse, jobs, chunksize=1)
        rmse = np.array([r[0] for r in res]); bias = np.array([r[1] for r in res])
        a_star, rmse_star = parabola_min(ALPHA_GRID, rmse)
        fwd = _rmse((s, 1.0, z, T))
        out["sites"][s] = dict(albedo=cfg["albedo"], n_sensors=int(len(z)),
                               forward=dict(alpha=1.0, rho_d_kg_m3=RHO_NOMINAL, rmse_K=fwd[0], bias_K=fwd[1]),
                               best=dict(alpha=a_star, rho_d_kg_m3=a_star * RHO_NOMINAL, rmse_K=rmse_star),
                               rmse_curve_K=rmse.tolist(), bias_curve_K=bias.tolist())
        print(f"  forward (1800 kg/m^3): RMSE {fwd[0]:.4f} K;  best: alpha {a_star:.4f} "
              f"(rho_d {a_star * RHO_NOMINAL:.0f} kg/m^3), RMSE {rmse_star:.4f} K;  "
              f"lowest RMSE on the grid {rmse.min():.4f} K", flush=True)
    out["meta"]["runtime_s"] = time.time() - t0
    p = ROOT / "results" / "martinez_density_fit.json"
    p.write_text(json.dumps(out, indent=1))
    print(f"wrote {p.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
