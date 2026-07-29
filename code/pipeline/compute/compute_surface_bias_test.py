#!/usr/bin/env python3
"""Does the surface-temperature mismatch bias the deep K_d retrieval?

The forced model reproduces the Diviner diurnal SHAPE but runs warm by
12-17 K in absolute terms (anisothermal-footprint / sub-pixel-rock
effect). A referee will ask whether that surface bias propagates into
the deep-sensor K_d retrieval.

Physical expectation: it should not. The deep gradient is set by the
steady-state relation |dT/dz| = Q_b / K(T,z); a near-uniform vertical
shift of the column leaves dT/dz, and hence the deep-sensor residual
pattern that defines K_d*, essentially unchanged.

This script tests that directly. It perturbs the surface energy
balance through the Bond albedo A -- the dominant lever on the
absolute surface temperature -- by +/-0.02 and +/-0.04 (well beyond
the A15/A17 albedo uncertainty), re-runs the per-site K_d retrieval
for each perturbed A, and reports how far K_d* moves. If K_d* is
stable while the surface temperature shifts by several K, the deep
retrieval is decoupled from the surface-closure mismatch.

Run from the repo root:
  python pipeline/compute/compute_surface_bias_test.py
"""
from __future__ import annotations
import json
import sys
from copy import deepcopy
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "pipeline" / "figures"))

from lunar.apollo_helpers import extract_sensor_stability        # noqa: E402
from pipeline.compute.retrieve_kd import (                  # noqa: E402
    SITES, run_with, kd_star_from_residuals,
)

# Albedo offsets applied on top of each site's nominal Bond albedo.
# +/-0.01 is an ASSUMED envelope, not a published error bar.
# PROVENANCE NOTE (audited 2026-07-27): this was labelled "the published
# Vasavada et al. (2012) lat-band albedo scatter". Vasavada et al. (2012)
# quote no albedo uncertainty; they model a normal albedo of 0.1 and
# separate terrain by albedo >0.13 / <0.09. +/-0.01 is of the same order
# as the spread between published choices (this work uses 0.131/0.137
# per site, Hayne 2017 a global A0 = 0.12), which is why it is a
# reasonable envelope -- but it is assumed, and must not be presented as
# a quoted 1-sigma. Its role in the budget is to show how WEAKLY
# Apollo 17 constrains K_d: a shift this small moves the RMSE minimum
# further than the whole statistical uncertainty.
# See documents/notes/ERROR_BUDGET_PROVENANCE.md.  Larger perturbations
# (+/-0.02 and beyond) push the deep-T(K_d) response into a
# non-monotonic regime where the RMSE bowl develops a second minimum
# and the retrieval hops between branches; the resulting half-range is
# not a meaningful 1-sigma. See docs/FLAG_REPORT.md (third pass).
DA = [-0.01, 0.0, +0.01]
from lunar.config import KD_GRIDS as KD_GRID   # single-sourced dense vertex grid


def deep_obs(site_cfg):
    obs = extract_sensor_stability(site_cfg["mission"],
                                   min_depth_cm=site_cfg["MIN_DEPTH_CM"])
    deep = np.asarray(obs["deep_mask"], dtype=bool)
    z = np.asarray(obs["depth_cm_all"])[deep] / 100.0
    T = np.asarray(obs["T_eq_all"])[deep]
    return z, T


def retrieve_with_albedo(site_cfg, da, kd_grid, z_obs, T_obs):
    """K_d* and the mean surface temperature for a perturbed albedo."""
    cfg = deepcopy(site_cfg)
    cfg["albedo"] = site_cfg["albedo"] + da
    R = np.empty((len(z_obs), len(kd_grid)))
    surf_T = None
    for k, kd in enumerate(kd_grid):
        z_mid, T_mean = run_with(cfg, kd=kd, k_model="hayne")
        R[:, k] = np.interp(z_obs, z_mid, T_mean) - T_obs
        if k == len(kd_grid) // 2:           # representative surface T
            surf_T = float(T_mean[0])
    kd_star, _ = kd_star_from_residuals(R, kd_grid)
    return kd_star, surf_T


def main():
    out = {"delta_albedo": DA, "A15": {}, "A17": {}}
    for s in ("A15", "A17"):
        z_obs, T_obs = deep_obs(SITES[s])
        kds, surfs = [], []
        for da in DA:
            kd, surfT = retrieve_with_albedo(SITES[s], da,
                                             KD_GRID[s], z_obs, T_obs)
            kds.append(kd * 1e3)
            surfs.append(surfT)
        out[s] = {"kd_star": kds, "surface_T": surfs}
        kd0 = kds[DA.index(0.0)]
        st0 = surfs[DA.index(0.0)]
        print(f"\n=== {SITES[s]['label']} ===")
        print(f"{'dA':>7} | {'surf T (K)':>11} | {'K_d* (mW/m/K)':>14} "
              f"| {'dK_d*':>8}")
        print("-" * 50)
        for da, kd, st in zip(DA, kds, surfs):
            print(f"{da:>+7.2f} | {st:>11.2f} | {kd:>14.2f} "
                  f"| {kd-kd0:>+8.3f}")
        dsurf = max(surfs) - min(surfs)
        dkd = max(kds) - min(kds)
        print(f"  surface T swing = {dsurf:.2f} K  ->  "
              f"K_d* swing = {dkd:.3f} mW/m/K "
              f"({100*dkd/kd0:.1f}% of K_d*)")

    json.dump(out, open(ROOT / "results" / "surface_bias_test.json", "w"),
              indent=2)
    print("\nwrote results/surface_bias_test.json")


if __name__ == "__main__":
    main()
