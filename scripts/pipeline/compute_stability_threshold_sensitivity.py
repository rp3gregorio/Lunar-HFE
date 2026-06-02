#!/usr/bin/env python3
"""Sensitivity of K_d* to the stability-window slope threshold.

The retrieval depends on T_eq computed within an auto-selected
'stability window' -- the longest trailing portion of each sensor's
record whose OLS linear slope is below a threshold (default
0.08 K/yr, ~2.2e-4 K/d). The threshold is a methodological choice;
this script tests how much the retrieved deep conductivity K_d*
changes when that choice is varied.

For thresholds in {0.04, 0.06, 0.08, 0.12, 0.16} K/yr we:

  1. Recompute every deep sensor's T_eq and within-window sigma.
  2. Refit K_d (Hayne form) at each site by parabolic minimisation
     of the deep-sensor RMSE.

Output: a small JSON + a summary table showing how K_d* moves.

Run from the repo root:
  python scripts/pipeline/compute_stability_threshold_sensitivity.py
"""
from __future__ import annotations
import json
import sys
from pathlib import Path
from copy import deepcopy

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts" / "figures"))

from lunar.apollo_helpers import (                                  # noqa: E402
    extract_sensor_stability, find_stable_window,
    load_apollo_hfe_depth, iso_to_seconds,
)
from scripts.pipeline.phase_a_pipeline import (                     # noqa: E402
    SITES, run_with, kd_star_from_residuals,
)

THRESHOLDS_K_PER_YR = [0.04, 0.06, 0.08, 0.12, 0.16]
KD_GRID = {"A15": np.linspace(1.5e-3, 15.0e-3, 28),
           "A17": np.linspace(3.0e-3, 22.0e-3, 30)}


def deep_obs_at_threshold(mission, min_depth_cm, slope_thresh):
    """Recompute per-deep-sensor T_eq with a NEW slope threshold.

    Reimplements the relevant part of extract_sensor_stability with the
    threshold as a free parameter (the library hard-codes 0.08).
    """
    d1 = load_apollo_hfe_depth(mission, 1)
    d2 = load_apollo_hfe_depth(mission, 2)
    z_keep, T_keep, sig_keep = [], [], []
    for dtab in (d1, d2):
        for sensor in np.unique(dtab["sensor"]):
            mask = dtab["sensor"] == sensor
            subset = dtab[mask]
            i_start, _, _, _ = find_stable_window(
                subset, slope_thresh_K_per_year=slope_thresh)
            tail = subset[i_start:]
            depth = float(np.unique(tail["depth_cm"])[0])
            if depth < min_depth_cm:
                continue                            # borestem-zone exclude
            z_keep.append(depth / 100.0)
            T_keep.append(float(np.mean(tail["T"])))
            sig_keep.append(float(np.std(tail["T"])))
    return (np.asarray(z_keep), np.asarray(T_keep), np.asarray(sig_keep))


def retrieve_kd(site_cfg, kd_grid, z_obs, T_obs):
    R = np.empty((len(z_obs), len(kd_grid)))
    for k, kd in enumerate(kd_grid):
        z_mid, T_mean = run_with(site_cfg, kd=kd, k_model="hayne")
        R[:, k] = np.interp(z_obs, z_mid, T_mean) - T_obs
    kd_star, rmse_star = kd_star_from_residuals(R, kd_grid)
    return kd_star, rmse_star


def main():
    print(f"{'thresh (K/yr)':>13} | {'A15: N_deep  K_d* (mW/m/K)':>30} "
          f"| {'A17: N_deep  K_d* (mW/m/K)':>30}", flush=True)
    print("-" * 79, flush=True)

    out = {"thresholds_K_per_yr": THRESHOLDS_K_PER_YR,
           "A15": {"kd_star_mW": [], "N_deep": []},
           "A17": {"kd_star_mW": [], "N_deep": []}}

    for thr in THRESHOLDS_K_PER_YR:
        row = f"{thr:>13.2f} |"
        for s in ("A15", "A17"):
            cfg = SITES[s]
            z, T, _ = deep_obs_at_threshold(
                cfg["mission"], cfg["MIN_DEPTH_CM"], thr)
            if len(z) < 4:
                row += f"  insufficient deep sensors ({len(z)})         "
                out[s]["kd_star_mW"].append(None)
                out[s]["N_deep"].append(int(len(z)))
                continue
            kd, _ = retrieve_kd(cfg, KD_GRID[s], z, T)
            out[s]["kd_star_mW"].append(float(kd * 1e3))
            out[s]["N_deep"].append(int(len(z)))
            row += f"  N={len(z):>2}  K_d* = {kd*1e3:>6.2f}      "
        print(row, flush=True)

    # summary: how much does K_d* move?
    print("-" * 79)
    for s in ("A15", "A17"):
        vals = [v for v in out[s]["kd_star_mW"] if v is not None]
        if vals:
            spread = max(vals) - min(vals)
            print(f"  {s} K_d* spread across thresholds: "
                  f"{min(vals):.2f}-{max(vals):.2f} mW/m/K "
                  f"(range {spread:.2f}; "
                  f"{100*spread/np.mean(vals):.1f}% of mean)")

    json.dump(out, open(ROOT / "output" /
                        "stability_threshold_sensitivity.json", "w"),
              indent=2)
    print("\nwrote output/stability_threshold_sensitivity.json")


if __name__ == "__main__":
    main()
