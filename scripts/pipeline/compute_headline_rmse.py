#!/usr/bin/env python3
"""Phase-1 headline RMSE table.

Four deep-sensor RMSE values per site, all reproducible from a
single script:

  1. Hayne (2017) functional form, K_d held at the published global
     value 3.4 mW/m/K.  (No per-site freedom; the 'how much does a
     global K_d miss' reference row.)
  2. Hayne form, K_d swept to the per-site deep-sensor RMSE minimum.
  3. Martinez & Siegler (2021) K(T, rho) evaluated forward at each
     site.  No fitted knob -- the published model applied as-published.
  4. Martinez & Siegler (2021) K(T, rho) with the deep-asymptote
     density rescaled by a single per-site factor alpha, swept against
     the deep-sensor RMSE.  alpha=1 reproduces row 3.  This is the
     apples-to-apples per-site retrieval under the Martinez form.

Writes output/headline_rmse.json and prints an ASCII summary.

Run from the repo root:
  python scripts/pipeline/compute_headline_rmse.py
"""
from __future__ import annotations
import json, sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts" / "figures"))

from lunar.apollo_helpers import extract_sensor_stability   # noqa: E402
from scripts.pipeline import retrieve_kd as pap        # noqa: E402

KD_GRID = {"A15": np.linspace(1.5e-3, 15.0e-3, 28),
           "A17": np.linspace(3.0e-3, 22.0e-3, 30)}

# Martinez per-site density-scalar grid.  alpha=1 is the published
# baseline (rho_d = 1800 kg/m^3); we sweep up to 2.2 to bracket the
# A17 minimum, which lies above the Apollo-core 1700-2000 kg/m^3
# envelope -- itself a scientifically meaningful finding (see manuscript).
MS_ALPHA_GRID = np.linspace(0.7, 2.2, 31)   # rho_d in [1260, 3960] kg/m^3

HAYNE_GLOBAL_KD = 3.4e-3   # W/m/K -- the published global value


def deep_obs(site_cfg):
    obs = extract_sensor_stability(site_cfg["mission"],
                                   min_depth_cm=site_cfg["MIN_DEPTH_CM"])
    deep = np.asarray(obs["deep_mask"], dtype=bool)
    z = np.asarray(obs["depth_cm_all"])[deep] / 100.0
    T = np.asarray(obs["T_eq_all"])[deep]
    return z, T


def rmse_forward(site_cfg, *, k_model, kd=None, z_obs, T_obs):
    z_mid, T_mean = pap.run_with(site_cfg, kd=kd, k_model=k_model)
    return float(np.sqrt(np.mean((np.interp(z_obs, z_mid, T_mean) - T_obs) ** 2)))


def kd_sweep_hayne(site_cfg, kd_grid, z_obs, T_obs):
    R = np.empty((len(z_obs), len(kd_grid)))
    for k, kd in enumerate(kd_grid):
        z_mid, T_mean = pap.run_with(site_cfg, kd=kd, k_model="hayne")
        R[:, k] = np.interp(z_obs, z_mid, T_mean) - T_obs
    kd_star, rmse_star = pap.kd_star_from_residuals(R, kd_grid)
    return float(kd_star), float(rmse_star)


def alpha_sweep_martinez(site_cfg, alpha_grid, z_obs, T_obs):
    """Per-site Martinez retrieval: sweep the density-scalar alpha,
    parabolically refine the RMSE minimum, return (alpha*, rmse*)."""
    rmse = np.empty(len(alpha_grid))
    for k, alpha in enumerate(alpha_grid):
        z_mid, T_mean = pap.run_with(site_cfg, k_model="martinez",
                                     martinez_alpha=float(alpha))
        rmse[k] = np.sqrt(np.mean(
            (np.interp(z_obs, z_mid, T_mean) - T_obs) ** 2))
    # parabolic minimum across the alpha grid
    k_min = int(np.argmin(rmse))
    if 0 < k_min < len(alpha_grid) - 1:
        x = alpha_grid[k_min-1:k_min+2]
        y = rmse[k_min-1:k_min+2]
        denom = (x[0]-x[1])*(x[0]-x[2])*(x[1]-x[2])
        a = (x[2]*(y[1]-y[0]) + x[1]*(y[0]-y[2]) + x[0]*(y[2]-y[1])) / denom
        b = (x[2]**2*(y[0]-y[1]) + x[1]**2*(y[2]-y[0]) + x[0]**2*(y[1]-y[2])) / denom
        alpha_star = -b / (2*a) if a > 0 else alpha_grid[k_min]
        rmse_star = float(np.interp(alpha_star, x, y))
    else:
        alpha_star = float(alpha_grid[k_min])
        rmse_star = float(rmse[k_min])
    return float(alpha_star), float(rmse_star), alpha_grid.tolist(), rmse.tolist()


def main():
    out = {"hayne_global_kd_W_per_m_K": HAYNE_GLOBAL_KD, "sites": {}}
    for s in ("A15", "A17"):
        print(f"\n=== {s} ===", flush=True)
        cfg = pap.SITES[s]
        z, T = deep_obs(cfg)
        rmse_global = rmse_forward(cfg, k_model="hayne",
                                   kd=HAYNE_GLOBAL_KD, z_obs=z, T_obs=T)
        kd_h, rmse_h = kd_sweep_hayne(cfg, KD_GRID[s], z, T)
        rmse_m = rmse_forward(cfg, k_model="martinez", z_obs=z, T_obs=T)
        alpha_star, rmse_ms_fit, alpha_grid_list, rmse_alpha_curve = \
            alpha_sweep_martinez(cfg, MS_ALPHA_GRID, z, T)
        rho_d_star = alpha_star * 1800.0
        print(f"  Hayne global  K_d=3.4    : RMSE = {rmse_global:.3f} K")
        print(f"  Hayne site-fit          : K_d* = {kd_h*1e3:.2f} "
              f"mW/m/K, RMSE = {rmse_h:.3f} K")
        print(f"  Martinez forward        : RMSE = {rmse_m:.3f} K")
        print(f"  Martinez site-fit alpha : alpha* = {alpha_star:.3f} "
              f"(rho_d* = {rho_d_star:.0f} kg/m^3), RMSE = "
              f"{rmse_ms_fit:.3f} K")
        out["sites"][s] = {
            "N_deep": int(len(z)),
            "hayne_global":      {"kd_mW": HAYNE_GLOBAL_KD * 1e3,
                                  "rmse_K": rmse_global},
            "hayne_site_fit":    {"kd_mW": kd_h * 1e3,
                                  "rmse_K": rmse_h},
            "martinez_forward":  {"rmse_K": rmse_m},
            "martinez_site_fit": {"alpha": alpha_star,
                                  "rho_d_kg_m3": rho_d_star,
                                  "rmse_K": rmse_ms_fit,
                                  "alpha_grid": alpha_grid_list,
                                  "rmse_curve": rmse_alpha_curve},
        }
    out_path = ROOT / "output" / "headline_rmse.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    json.dump(out, open(out_path, "w"), indent=2)
    print(f"\nwrote {out_path}")

    print("\n" + "=" * 78)
    print(f"{'Player':<33} | {'A15 RMSE':>9} | {'A17 RMSE':>9} | "
          f"{'A15 knob':>10} | {'A17 knob':>10}")
    print("-" * 78)
    rows = [("Hayne, global K_d = 3.4",       "hayne_global",      "K_d"),
            ("Hayne, site-fit K_d",           "hayne_site_fit",    "K_d"),
            ("Martinez forward (no fit)",     "martinez_forward",  None),
            ("Martinez, site-fit alpha",      "martinez_site_fit", "alpha")]
    for label, key, knob in rows:
        a, b = out["sites"]["A15"][key], out["sites"]["A17"][key]
        if knob == "K_d":
            ka = f"{a.get('kd_mW', float('nan')):>10.2f}"
            kb = f"{b.get('kd_mW', float('nan')):>10.2f}"
        elif knob == "alpha":
            ka = f"{a['alpha']:>10.3f}"
            kb = f"{b['alpha']:>10.3f}"
        else:
            ka = "        --"
            kb = "        --"
        print(f"{label:<33} | {a['rmse_K']:>9.3f} | {b['rmse_K']:>9.3f}"
              f" | {ka} | {kb}")
    print("=" * 78)


if __name__ == "__main__":
    main()
