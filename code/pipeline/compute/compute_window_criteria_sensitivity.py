#!/usr/bin/env python3
"""Sensitivity of K_d* to EVERY free choice in the stability-window selector.

``lunar.apollo_helpers.find_stable_window`` contains four numbers that were
chosen by judgement rather than derived:

  1. slope threshold    0.08 K/yr   -- the flatness bar
  2. scan floor         55 %        -- earliest candidate window start
  3. fallback fraction  last 25 %   -- used when no candidate is flat
  4. depth cut          80 cm       -- the borestem exclusion zone

Knobs 1 and 4 already had dedicated sweeps
(``stability_threshold_sensitivity.json``, ``borestem_sensitivity.json``).
Knobs 2 and 3 did not, which left the two most arbitrary numbers in the
selector untested -- and knob 3 is the branch 14 of the 23 retained sensors
actually take. This script sweeps all four through the SAME retrieval so the
results are directly comparable in one unit (mW/m/K).

Cost note: ``retrieve_kd.run_with`` caches forward profiles on
(site, K_d, model), and the window criteria change only the OBSERVED
temperatures, never the forward solve. So the whole four-knob sweep costs one
K_d grid per site (~61 solves, ~30 s), not one grid per setting.

Output: results/window_criteria_sensitivity.json
Run from the repo root:
  python pipeline/compute/compute_window_criteria_sensitivity.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

from lunar.apollo_helpers import iso_to_seconds                     # noqa: E402
from lunar.config import KD_GRIDS                                   # noqa: E402
from lunar.validation import load_apollo_hfe_depth                  # noqa: E402
from pipeline.compute.retrieve_kd import (                          # noqa: E402
    SITES, run_with, kd_star_from_residuals,
)

# Adopted values (the production configuration) and the swept alternatives.
ADOPTED = dict(slope=0.08, floor=0.55, fallback=0.75, depth=80)
SWEEPS = {
    "slope":    [0.04, 0.06, 0.08, 0.12, 0.16],       # K/yr
    "floor":    [0.35, 0.45, 0.55, 0.65, 0.75],       # fraction into record
    "fallback": [0.60, 0.65, 0.70, 0.75, 0.80],       # start of fallback window
    "depth":    [60, 70, 80, 90],                     # cm
}
LABELS = {
    "slope": "flatness threshold (K/yr)",
    "floor": "earliest window start (% into record)",
    "fallback": "fallback window start (% into record)",
    "depth": "borestem depth cut (cm)",
}
CEIL, N_CAND, MIN_FRAC = 0.85, 13, 0.20


def select_window(subset, slope_thresh, floor, fallback):
    """Re-implementation of find_stable_window with every knob exposed.

    Mirrors the library function exactly at the adopted settings; verified
    against it in ``_selfcheck`` below.
    """
    n = len(subset)
    t_sec = iso_to_seconds(subset["time_iso"])
    t_year = (t_sec - t_sec[0]) / 86400.0 / 365.25
    T = subset["T"].astype(np.float64)
    for frac in np.linspace(floor, CEIL, N_CAND):
        i0 = int(frac * n)
        if n - i0 < max(40, int(MIN_FRAC * n)):
            continue
        if np.ptp(t_year[i0:]) <= 0:
            continue
        if abs(np.polyfit(t_year[i0:], T[i0:], 1)[0]) <= slope_thresh:
            return i0, "trend_flat"
    return int(fallback * n), "fallback"


def deep_obs(mission, depth_cut, *, slope, floor, fallback):
    """Per-deep-sensor (depth [m], T_eq [K]) under one selector setting."""
    z, T, n_flat = [], [], 0
    for probe in (1, 2):
        dtab = load_apollo_hfe_depth(mission, probe)
        for sensor in np.unique(dtab["sensor"]):
            subset = dtab[dtab["sensor"] == sensor]
            i0, method = select_window(subset, slope, floor, fallback)
            tail = subset[i0:]
            depth_cm = float(np.unique(tail["depth_cm"])[0])
            if depth_cm < depth_cut:
                continue
            z.append(depth_cm / 100.0)
            T.append(float(np.mean(tail["T"])))
            n_flat += method == "trend_flat"
    order = np.argsort(z)
    return np.asarray(z)[order], np.asarray(T)[order], n_flat


def retrieve(site_cfg, kd_grid, z_obs, T_obs):
    R = np.empty((len(z_obs), len(kd_grid)))
    for k, kd in enumerate(kd_grid):
        z_mid, T_mean = run_with(site_cfg, kd=kd, k_model="hayne")
        R[:, k] = np.interp(z_obs, z_mid, T_mean) - T_obs
    kd_star, _ = kd_star_from_residuals(R, kd_grid)
    return float(kd_star * 1e3)


def _selfcheck():
    """The local selector must reproduce the shipping one at adopted settings."""
    from lunar.apollo_helpers import find_stable_window
    for mission in ("a15", "a17"):
        for probe in (1, 2):
            dtab = load_apollo_hfe_depth(mission, probe)
            for sensor in np.unique(dtab["sensor"]):
                sub = dtab[dtab["sensor"] == sensor]
                got, _ = select_window(sub, ADOPTED["slope"], ADOPTED["floor"],
                                       ADOPTED["fallback"])
                want, _, _, _ = find_stable_window(sub)
                if got != want:
                    raise AssertionError(
                        f"selector mismatch {mission} p{probe} {sensor.strip()}: "
                        f"{got} vs library {want}")
    print("  selfcheck: local selector reproduces find_stable_window exactly")


def main():
    _selfcheck()
    out = {"adopted": ADOPTED, "labels": LABELS, "sweeps": {}}

    for knob, values in SWEEPS.items():
        out["sweeps"][knob] = {"values": values,
                               "A15": {"kd_star_mW": [], "N_deep": [], "n_flat": []},
                               "A17": {"kd_star_mW": [], "N_deep": [], "n_flat": []}}
        print(f"\n{LABELS[knob]}")
        print(f"{'value':>10} | {'A15  N  n_flat  K_d*':>26} | {'A17  N  n_flat  K_d*':>26}")
        print("-" * 70)
        for v in values:
            kw = dict(slope=ADOPTED["slope"], floor=ADOPTED["floor"],
                      fallback=ADOPTED["fallback"])
            depth_cut = ADOPTED["depth"]
            if knob == "depth":
                depth_cut = v
            else:
                kw[knob] = v
            row = f"{v:>10} |"
            for site in ("A15", "A17"):
                cfg = SITES[site]
                z, T, n_flat = deep_obs(cfg["mission"], depth_cut, **kw)
                kd = retrieve(cfg, KD_GRIDS[site], z, T) if len(z) >= 4 else None
                rec = out["sweeps"][knob][site]
                rec["kd_star_mW"].append(kd)
                rec["N_deep"].append(int(len(z)))
                rec["n_flat"].append(int(n_flat))
                row += f"   N={len(z):>2}  flat={n_flat:>2}  " + \
                       (f"{kd:>6.3f}" if kd is not None else "   n/a") + "   |"
            print(row, flush=True)

        for site in ("A15", "A17"):
            vals = [x for x in out["sweeps"][knob][site]["kd_star_mW"] if x is not None]
            spread = max(vals) - min(vals)
            out["sweeps"][knob][site]["spread_mW"] = float(spread)
            print(f"    {site} K_d* spread {spread:.3f} mW/m/K "
                  f"({min(vals):.3f}-{max(vals):.3f})")

    dest = ROOT / "results" / "window_criteria_sensitivity.json"
    dest.write_text(json.dumps(out, indent=2))
    print(f"\nwrote {dest.relative_to(ROOT.parent)}")


if __name__ == "__main__":
    main()
