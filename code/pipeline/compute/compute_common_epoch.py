#!/usr/bin/env python3
"""Common-epoch sensitivity of the per-site K_d retrieval (audit F2).

THE PROBLEM (codex audit 2026-07-13, confirmed by diagnostic): the
per-sensor stability windows end at different calendar epochs while the
record is still warming. At A17 the retained sensors at 130--178 cm carry
mid-1977 windows while every sensor below 180 cm carries a 1974 window --
a 3.1-yr epoch spread aligned with depth, i.e. exactly the pattern that
distorts the fitted gradient. At A15 the spread is 1.0 yr with slopes
<= 0.22 K/yr (mild).

THE TEST: rebuild every retained sensor's T_eq from the SAME calendar
window (no extrapolation -- all sensors have data there):

  * variant "certified"      : production stability windows (validation --
                               must reproduce the archived K_d*).
  * variant "common_1974"    : one shared window per site
                               (A15 1973-12-01..1974-12-31,
                                A17 1974-01-01..1974-12-31), the span the
                               low-cadence/deep channels already use.
  * variant "translated_1974": each sensor's certified window mean
                               slope-translated to the common-window
                               midpoint using its own fitted tail slope
                               (cross-check on the direct construction).

For each variant x site, the K_d sweep is re-evaluated against the SAME
solved model profiles (the model is independent of T_obs; the grid is
solved once at production settings) and the full sensor bootstrap
(N=1500, +/-2.5 cm depth jitter) is re-run.

This is an archived SENSITIVITY STUDY: it does not re-baseline the
headline retrieval. Writes results/common_epoch_sensitivity.json.

Run: python code/pipeline/compute/compute_common_epoch.py   (~15 min)
"""
from __future__ import annotations

import datetime as dt
import json
import pathlib
import sys
import time

import numpy as np

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "pipeline" / "compute"))

from lunar.apollo_helpers import (load_apollo_hfe_depth, find_stable_window,
                                  iso_to_seconds)  # noqa: E402
from lunar.config import SITES, KD_GRIDS  # noqa: E402
from retrieve_kd import run_with  # noqa: E402

OUT = ROOT / "results" / "common_epoch_sensitivity.json"
N_BOOT = 1500
DEPTH_JITTER_CM = 2.5
RNG = np.random.default_rng(0)

COMMON_WINDOWS = {  # site -> (start, end), chosen with zero extrapolation
    "A15": ("1973-12-01", "1974-12-31"),
    "A17": ("1974-01-01", "1974-12-31"),
}


def _sec(datestr):
    return (dt.datetime.fromisoformat(datestr)
            - dt.datetime(1970, 1, 1)).total_seconds()


def sensor_variants(mission, site_name):
    """Per retained sensor: depth + T_eq under each variant."""
    t_lo, t_hi = (_sec(x) for x in COMMON_WINDOWS[site_name])
    t_mid_common = 0.5 * (t_lo + t_hi)
    rows = []
    for probe in (1, 2):
        tab = load_apollo_hfe_depth(mission, probe)
        for sensor in np.unique(tab["sensor"]):
            sub = tab[tab["sensor"] == sensor]
            depth = float(np.unique(sub["depth_cm"])[0])
            if depth < 80:
                continue
            t = iso_to_seconds(sub["time_iso"])
            T = sub["T"].astype(np.float64)
            # certified window
            i0, _, method, slope = find_stable_window(sub)
            T_cert = float(np.mean(T[i0:]))
            t_mid_cert = float(np.median(t[i0:]))
            # common calendar window (direct, no extrapolation)
            m = (t >= t_lo) & (t <= t_hi)
            assert m.sum() >= 20, f"{site_name} {sensor}: {m.sum()} pts in common window"
            T_common = float(np.mean(T[m]))
            # slope-translation of the certified mean to the common midpoint
            b = slope if np.isfinite(slope) else 0.0     # K / yr
            T_trans = T_cert + b * (t_mid_common - t_mid_cert) / (365.25 * 86400)
            rows.append(dict(sensor=sensor.strip(), depth_cm=depth,
                             method=method, slope_K_yr=round(float(slope), 3)
                             if np.isfinite(slope) else None,
                             T_certified=T_cert, T_common=T_common,
                             T_translated=T_trans,
                             n_common=int(m.sum())))
    rows.sort(key=lambda r: r["depth_cm"])
    return rows


def solve_grid(site_cfg, kd_grid):
    """Solve the production sweep grid once; keep full mean profiles."""
    profiles = []
    t0 = time.time()
    for i, kd in enumerate(kd_grid):
        z_mid, T_mean = run_with(site_cfg, kd=float(kd), k_model="hayne")
        profiles.append((np.asarray(z_mid), np.asarray(T_mean)))
        print(f"    kd {1e3*kd:5.2f} mW  [{i+1}/{len(kd_grid)}] "
              f"({time.time()-t0:.0f} s)", flush=True)
    return profiles


def kd_star(kd_grid, profiles, z_obs, T_obs):
    rmse = np.array([np.sqrt(np.mean((np.interp(z_obs, z, T) - T_obs) ** 2))
                     for z, T in profiles])
    i = int(np.argmin(rmse))
    if 0 < i < len(kd_grid) - 1:      # parabolic vertex through the bracket
        x = np.asarray(kd_grid[i-1:i+2], dtype=float)
        y = rmse[i-1:i+2]
        d = (y[0] - 2*y[1] + y[2])
        if d > 0:
            v = x[1] - 0.5*(x[2]-x[0])*(y[2]-y[0])/(2*d)
            return float(v), float(np.min(rmse)), rmse
    return float(kd_grid[i]), float(rmse[i]), rmse


def bootstrap(kd_grid, profiles, z_obs, T_obs):
    n = len(z_obs)
    stars = np.empty(N_BOOT)
    for b in range(N_BOOT):
        idx = RNG.integers(0, n, n)
        zj = z_obs[idx] + RNG.normal(0, DEPTH_JITTER_CM / 100.0, n)
        s, _, _ = kd_star(kd_grid, profiles,
                          np.clip(zj, 0.01, None), T_obs[idx])
        stars[b] = s
    return stars


def main():
    out = {"meta": dict(
        n_boot=N_BOOT, depth_jitter_cm=DEPTH_JITTER_CM,
        common_windows=COMMON_WINDOWS,
        note="sensitivity study (audit F2); does not re-baseline the "
             "headline retrieval. Model grid solved once at production "
             "settings; variants differ only in T_eq construction.")}
    stars = {}
    for site_name, mission in (("A15", "a15"), ("A17", "a17")):
        cfg = SITES[site_name] if site_name in SITES else SITES[mission]
        print(f"=== {site_name}: sensors ===", flush=True)
        rows = sensor_variants(mission, site_name)
        kd_grid = np.asarray(KD_GRIDS[site_name], dtype=float)
        print(f"=== {site_name}: solving {len(kd_grid)}-point grid ===",
              flush=True)
        profiles = solve_grid(cfg, kd_grid)
        z = np.array([r["depth_cm"] for r in rows]) / 100.0
        site_out = {"sensors": rows}
        for variant, key in (("certified", "T_certified"),
                             ("common_1974", "T_common"),
                             ("translated_1974", "T_translated")):
            T = np.array([r[key] for r in rows])
            star, rmse_min, rmse = kd_star(kd_grid, profiles, z, T)
            bs = bootstrap(kd_grid, profiles, z, T)
            lo, med, hi = np.percentile(bs, [2.5, 50, 97.5])
            site_out[variant] = dict(
                kd_star_mW=round(1e3 * star, 3),
                rmse_K=round(rmse_min, 4),
                boot_median_mW=round(1e3 * med, 3),
                ci95_mW=[round(1e3 * lo, 3), round(1e3 * hi, 3)])
            stars[(site_name, variant)] = bs
            print(f"  {site_name} {variant:16s} K_d* = {1e3*star:6.2f} mW "
                  f"(RMSE {rmse_min:.3f} K, CI [{1e3*lo:.2f},{1e3*hi:.2f}])",
                  flush=True)
        out[site_name] = site_out

    # contrast per variant (independent per-site draws)
    out["contrast"] = {}
    for variant in ("certified", "common_1974", "translated_1974"):
        d = stars[("A17", variant)] - stars[("A15", variant)]
        lo, med, hi = np.percentile(d, [2.5, 50, 97.5])
        out["contrast"][variant] = dict(
            median_mW=round(1e3 * med, 3),
            ci95_mW=[round(1e3 * lo, 3), round(1e3 * hi, 3)],
            p_boot_leq0=round(float(np.mean(d <= 0)), 4))
        print(f"  contrast {variant:16s} {1e3*med:+.2f} "
              f"[{1e3*lo:+.2f},{1e3*hi:+.2f}]  P_boot(<=0)="
              f"{np.mean(d <= 0):.4f}", flush=True)

    OUT.write_text(json.dumps(out, indent=2))
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
