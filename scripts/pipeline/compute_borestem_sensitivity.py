#!/usr/bin/env python3
"""Sensitivity of the K_d retrieval to the borestem exclusion depth.

The retrieval uses only sensors deeper than an 80 cm "borestem zone"
cut. A referee will ask whether the result is an artefact of that one
choice. This script re-runs the per-site K_d retrieval with the
exclusion depth swept over 60, 70, 80, 90, 100 cm and reports how
K_d^A15, K_d^A17, and the contrast change.

Run from the repo root:
  python scripts/pipeline/compute_borestem_sensitivity.py
"""
from __future__ import annotations
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts" / "figures"))

from lunar.apollo_helpers import extract_sensor_stability        # noqa: E402
from scripts.pipeline.retrieve_kd import (                  # noqa: E402
    SITES, run_with, kd_star_from_residuals,
)

CUT_CM = [60, 70, 80, 90, 100]
KD_GRID = {"A15": np.linspace(1.5e-3, 15.0e-3, 28),
           "A17": np.linspace(3.0e-3, 22.0e-3, 30)}


def retrieve(site_cfg, cut_cm, kd_grid):
    """Retrieve K_d* using only sensors deeper than cut_cm."""
    obs = extract_sensor_stability(site_cfg["mission"], min_depth_cm=0)
    z = np.asarray(obs["depth_cm_all"]) / 100.0
    T = np.asarray(obs["T_eq_all"])
    keep = z >= cut_cm / 100.0
    z_keep, T_keep = z[keep], T[keep]
    if len(z_keep) < 4:
        return None, 0
    R = np.empty((len(z_keep), len(kd_grid)))
    for k, kd in enumerate(kd_grid):
        z_mid, T_mean = run_with(site_cfg, kd=kd, k_model="hayne")
        R[:, k] = np.interp(z_keep, z_mid, T_mean) - T_keep
    kd_star, _ = kd_star_from_residuals(R, kd_grid)
    return kd_star, int(len(z_keep))


def main():
    out = {"cut_cm": CUT_CM, "A15": [], "A17": [],
           "n_A15": [], "n_A17": [], "contrast": []}
    print(f"{'cut':>5} | {'A15 K_d*':>9} (N) | {'A17 K_d*':>9} (N) "
          f"| {'contrast':>9}")
    print("-" * 56)
    used_cuts = []
    for cut in CUT_CM:
        kd15, n15 = retrieve(SITES["A15"], cut, KD_GRID["A15"])
        kd17, n17 = retrieve(SITES["A17"], cut, KD_GRID["A17"])
        if kd15 is None or kd17 is None:
            # too few deep sensors survive this cut to retrieve K_d
            print(f"{cut:>5} | skipped (fewer than 4 deep sensors "
                  f"at one site)")
            continue
        used_cuts.append(cut)
        contrast = (kd17 - kd15) * 1e3
        out["A15"].append(kd15 * 1e3)
        out["A17"].append(kd17 * 1e3)
        out["n_A15"].append(n15)
        out["n_A17"].append(n17)
        out["contrast"].append(contrast)
        print(f"{cut:>5} | {kd15*1e3:>9.2f} ({n15}) | "
              f"{kd17*1e3:>9.2f} ({n17}) | {contrast:>9.2f}")
    out["cut_cm"] = used_cuts

    json.dump(out, open(ROOT / "output" / "borestem_sensitivity.json",
                        "w"), indent=2)
    print("\nwrote output/borestem_sensitivity.json")
    # quick verdict
    c = np.array(out["contrast"])
    print(f"\ncontrast across 60-100 cm cuts: "
          f"{c.min():.2f} to {c.max():.2f} mW/m/K "
          f"(spread {c.max()-c.min():.2f}); "
          f"sign {'STABLE (all positive)' if (c > 0).all() else 'CHANGES'}")


if __name__ == "__main__":
    main()
