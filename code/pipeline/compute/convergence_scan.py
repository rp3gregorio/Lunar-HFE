#!/usr/bin/env python3
"""n_inner convergence scan: K_d* vs Step-A inner-lunation count.

Writes results/convergence_scan.json, the artifact behind
fig_convergence_study (the figure that justifies EQ_N_INNER=96). Three
series: the OLD full-column Step A (cap=50 m, i.e. no truncation) at A17,
and the production truncated Step A at both sites. Promoted from a
session scratchpad into the pipeline (writer-script law) on 2026-07-04 and
re-based on the certified solver: commensurate wrap-fixed grid, midpoint
Picard, compiled kernel (~1 s/solve, so the whole scan is minutes).

Run: python pipeline/compute/convergence_scan.py   (~5 min)
"""
from __future__ import annotations

import json
import pathlib
import sys
import time

import numpy as np

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from lunar.config import (SITES, GRID, EQ_Z_ANCHOR, EQ_MAX_OUTER,
                          EQ_ANCHOR_TOL, HAYNE, DT_STEP)
from lunar.grid import make_geometric_grid
from lunar.properties import conductivity_hayne, specific_heat
from lunar.equilibrium import solve_periodic_equilibrium
from lunar.apollo_helpers import extract_sensor_stability
from lunar.solver import periodic_time_grid, standard_insolation

from retrieve_kd import kd_star_from_residuals

GRID_ = make_geometric_grid(**GRID)
T_S = periodic_time_grid(DT_STEP)
CP = lambda T: specific_heat(T, model="hayne")
# dense local grids for a clean vertex, bracketing the certified minima
GR = {"A15": np.linspace(3.6e-3, 6.0e-3, 13),
      "A17": np.linspace(6.0e-3, 8.6e-3, 14)}
N_SCAN = [12, 18, 24, 32, 48, 64, 96, 128]
# n=128 added 2026-08-28: the thesis/config plateau claim quoted a 2026-06-30
# (pre-wrap-step) study that this scan could not reproduce because it stopped
# at 96. Certified values are now 4.5968/4.6015/4.6022 at n=64/96/128 (A15).


def kd_star(site, n_inner, cap, kd_grid):
    insol = standard_insolation(site["lat"], T_S)
    obs = extract_sensor_stability(site["mission"],
                                   min_depth_cm=site["MIN_DEPTH_CM"])
    deep = np.asarray(obs["deep_mask"], bool)
    z_obs = np.asarray(obs["depth_cm_all"])[deep] / 100.0
    T_obs = np.asarray(obs["T_eq_all"])[deep]
    R = np.empty((len(z_obs), len(kd_grid)))
    clo = []
    t0 = time.perf_counter()
    for j, kd in enumerate(kd_grid):
        kf = lambda T, z, kd=kd: conductivity_hayne(
            T, z, Ks=HAYNE["K_S"], Kd=kd, H=HAYNE["H"], chi=HAYNE["CHI"])
        eq = solve_periodic_equilibrium(
            grid=GRID_, t=T_S, insolation=insol, albedo=site["albedo"],
            emissivity=site["emissivity"], Q_b=site["Q_BASAL"],
            K_func=kf, cp_func=CP, T_guess=site["T_MEAN_EFF"],
            z_anchor=EQ_Z_ANCHOR, n_inner=n_inner,
            max_outer=EQ_MAX_OUTER, anchor_tol_K=EQ_ANCHOR_TOL,
            step_a_depth_m=cap,
            hayne_params=(HAYNE["K_S"], kd, HAYNE["H"], HAYNE["CHI"]))
        R[:, j] = np.interp(z_obs, GRID_.z_mid, eq.T_mean) - T_obs
        clo.append(eq.flux_closure)
    ks, _ = kd_star_from_residuals(R, kd_grid, warn_coarse=False)
    return (ks * 1e3, (time.perf_counter() - t0) / len(kd_grid),
            float(np.median(clo)))


def main():
    out = {"n_inner": N_SCAN, "series": {},
           "note": ("certified solver (wrap step + CN_PICARD_SWEEPS, "
                    "commensurate grid, compiled kernel), 2026-07-04")}
    runs = [("A17_old", "A17", 50.0), ("A17_new", "A17", None),
            ("A15_new", "A15", None)]
    for key, site_name, cap in runs:
        kd, sps, clo = [], [], []
        for n in N_SCAN:
            k, s, c = kd_star(SITES[site_name], n, cap, GR[site_name])
            kd.append(round(k, 4)); sps.append(round(s, 2))
            clo.append(round(c * 100, 3))
            print(f"{key} n={n}: K_d*={k:.4f}  {s:.2f}s/solve  "
                  f"clo={c*100:.3f}%", flush=True)
        out["series"][key] = dict(kd_star=kd, s_per_solve=sps,
                                  closure_pct=clo)
    (ROOT / "results" / "convergence_scan.json").write_text(
        json.dumps(out, indent=2))
    print("wrote results/convergence_scan.json", flush=True)


if __name__ == "__main__":
    main()
