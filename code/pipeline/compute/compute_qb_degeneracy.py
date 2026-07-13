#!/usr/bin/env python3
"""Direct K_d*(Q_b) degeneracy map -- replaces the proportional surrogate.

Audit F-9 (2026-07-03): the qb_sensitivity block in kd_retrieval_results.json
and the Bayesian cross-check both encoded the analytic assumption that the
deep profile is invariant under (K_d, Q_b) -> (alpha K_d, alpha Q_b), i.e.
K_d*(alpha Q_b) = alpha K_d*(Q_b). Direct re-retrieval DISPROVES this: the
anchor's cycle-mean temperature carries a Q_b/K-dependent offset through the
skin column (measured -1.26 K depth-uniform at A17 under alpha = 10/16), and
the actual relation is INVERSE -- at A17, K_d*(Q_b = 10/16/18 mW m^-2) =
10.14 / 7.08 / 6.80 mW m^-1 K^-1, with the low-Q_b fit actually DEEPENING
the RMSE minimum (0.29 K vs 0.40 K). The honest degeneracy map is therefore
a direct re-retrieval at each Q_b, which this script performs (fast-path
solves; ~1 s each).

For each site and each Q_b value: a coarse wide K_d sweep, one dense
refinement bracket around the coarse minimum (auto-widened if the minimum
sits at an edge -- today's bracket-edge lesson), then the parabola vertex.

Writes results/qb_degeneracy.json.
Run: python pipeline/compute/compute_qb_degeneracy.py   (~4 min)
"""
from __future__ import annotations

import json
import pathlib
import sys

import numpy as np

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from lunar.apollo_helpers import extract_sensor_stability
from lunar.config import SITES

from retrieve_kd import run_with, _interp_profile_at_depths, kd_star_from_residuals

# Q_b values [W m^-2]: the published value, the +-25% reanalysis envelope,
# and (A17) the debated Saito/Nagihara low (~10) and upper (~18) endpoints
# quoted in the letter's degeneracy discussion.
QB_POINTS = {
    # Direct re-retrieval at each Q_b (no extrapolation). The grid extends
    # BELOW the published envelope (A15 to 10, A17 to 7) so the rendered map
    # (fig_robustness) frames the MCMC posterior median (~17.7, 13.7) near
    # centre with breathing room; the envelope box (14-25 x 10-18) and every
    # claim still sit inside the measured domain.
    "A15": [0.010, 0.012, 0.014, 0.016, 0.0185, 0.021, 0.0235, 0.026],
    "A17": [0.007, 0.0085, 0.010, 0.012, 0.014, 0.016, 0.018, 0.020],
}
COARSE = {"A15": (1.5e-3, 12.0e-3, 15), "A17": (2.0e-3, 16.0e-3, 15)}


def _sweep(site_cfg, z_deep, T_deep, qb, kd_grid):
    R = np.empty((z_deep.size, len(kd_grid)))
    for k, kd in enumerate(kd_grid):
        zm, Tm = run_with(site_cfg, kd=float(kd), qb=qb, k_model="hayne")
        R[:, k] = _interp_profile_at_depths(
            z_deep, zm, Tm, context=f"qb degeneracy (Qb={qb*1e3:g})") - T_deep
    return R, np.sqrt((R**2).mean(axis=0))


def kd_star_at_qb(site_cfg, z_deep, T_deep, qb, lo, hi, n):
    # coarse pass, auto-widened until the minimum is interior
    for _ in range(4):
        grid = np.linspace(lo, hi, n)
        _, rmse = _sweep(site_cfg, z_deep, T_deep, qb, grid)
        i = int(np.argmin(rmse))
        if i == 0:
            lo, hi = max(0.5e-3, lo * 0.5), grid[2]
        elif i == len(grid) - 1:
            lo, hi = grid[-3], hi * 1.6
        else:
            break
    else:
        raise RuntimeError(f"no interior minimum for Qb={qb} in [{lo},{hi}]")
    # dense refinement around the coarse minimum
    dense = np.linspace(grid[max(i - 1, 0)], grid[min(i + 1, len(grid) - 1)], 9)
    R, rmse_d = _sweep(site_cfg, z_deep, T_deep, qb, dense)
    ks, _ = kd_star_from_residuals(R, dense, warn_coarse=False)
    return float(ks), float(rmse_d.min())


def main():
    out = {}
    for skey, qbs in QB_POINTS.items():
        site = SITES[skey]
        obs = extract_sensor_stability(site["mission"],
                                       min_depth_cm=site["MIN_DEPTH_CM"])
        z = np.asarray(obs["depth_cm_all"]) / 100.0
        T = np.asarray(obs["T_eq_all"])
        m = np.asarray(obs["deep_mask"], dtype=bool)
        lo, hi, n = COARSE[skey]
        rows = []
        for qb in qbs:
            ks, rmin = kd_star_at_qb(site, z[m], T[m], qb, lo, hi, n)
            rows.append({"qb_mW": qb * 1e3, "kd_star_mW": ks * 1e3,
                         "rmse_min_K": rmin})
            print(f"{skey} Qb={qb*1e3:5.1f} mW: K_d* = {ks*1e3:6.2f} mW, "
                  f"min RMSE = {rmin:.3f} K", flush=True)
        out[skey] = rows

    path = ROOT / "results" / "qb_degeneracy.json"
    path.write_text(json.dumps({
        "note": ("DIRECT K_d*(Q_b) re-retrievals (fast-path); supersedes the "
                 "proportional qb_sensitivity surrogate (audit F-9). The "
                 "relation is inverse and non-proportional: the anchor "
                 "temperature carries a Q_b/K-dependent skin-column offset."),
        "sites": out,
    }, indent=1))
    print(f"wrote {path.relative_to(ROOT)}", flush=True)


if __name__ == "__main__":
    main()
