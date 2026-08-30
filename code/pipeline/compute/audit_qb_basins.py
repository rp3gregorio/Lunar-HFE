"""Audit the K_d*(Q_b) map for multiple RMSE basins (2026-08-28).

Why: results/qb_degeneracy.json reported K_d*(A15, Q_b=10) = 7.74, out of
family with its neighbours (12 -> 1.57, 14 -> 2.07, 16 -> 2.72). Cause: at low
Q_b the A15 objective is BIMODAL, and compute_qb_degeneracy.kd_star_at_qb
starts its coarse pass at K_d = 1.5 mW, above the lower basin (~1.2), so the
auto-widen guard -- which only fires on an EDGE minimum -- never triggers and
the search refines the secondary basin instead.

This script scans a wide K_d grid at every Q_b, reports every local minimum,
and flags where the stored value disagrees with the global minimum. It does
not overwrite qb_degeneracy.json; it writes results/qb_basin_audit.json.

Run: python pipeline/compute/audit_qb_basins.py    (~15 min, fast path)
"""
from __future__ import annotations
import json, pathlib, sys, time
import numpy as np

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from lunar.apollo_helpers import extract_sensor_stability
from lunar.config import SITES
from retrieve_kd import run_with, _interp_profile_at_depths

QB = {"A15": [0.010, 0.012, 0.014, 0.016, 0.0185, 0.021, 0.0235, 0.026],
      "A17": [0.007, 0.0085, 0.010, 0.012, 0.014, 0.016, 0.018, 0.020]}
# Wide enough to contain BOTH basins at every Q_b (A15 lower basin ~1.2).
GRID = {"A15": np.linspace(0.8e-3, 14.0e-3, 45),
        "A17": np.linspace(1.5e-3, 26.0e-3, 60)}


def main():
    t0 = time.time()
    stored = json.loads((ROOT / "results" / "qb_degeneracy.json").read_text())["sites"]
    out = {"note": ("Wide-grid basin audit of the K_d*(Q_b) map. 'basins' "
                    "lists every interior local minimum of RMSE(K_d) at that "
                    "Q_b. Where n_basins > 1 the retrieval is ambiguous and "
                    "the reported K_d* is only the deeper of two competing "
                    "solutions."), "sites": {}}
    for tag, qbs in QB.items():
        site = SITES[tag]
        obs = extract_sensor_stability(site["mission"],
                                       min_depth_cm=site["MIN_DEPTH_CM"])
        z = np.asarray(obs["depth_cm_all"]) / 100.0
        T = np.asarray(obs["T_eq_all"])
        m = np.asarray(obs["deep_mask"], dtype=bool)
        z, T = z[m], T[m]
        g = GRID[tag]
        rows = []
        for qb, st in zip(qbs, stored[tag]):
            c = np.empty(len(g))
            for i, kd in enumerate(g):
                zm, Tm = run_with(site, kd=float(kd), qb=qb, k_model="hayne")
                c[i] = np.sqrt((( _interp_profile_at_depths(
                    z, zm, Tm, context=f"{tag} basin audit") - T) ** 2).mean())
            loc = [i for i in range(1, len(c) - 1)
                   if c[i] < c[i - 1] and c[i] < c[i + 1]]
            gm = int(np.argmin(c))
            basins = [{"kd_mW": float(g[i] * 1e3), "rmse_K": float(c[i])}
                      for i in loc]
            agrees = abs(g[gm] * 1e3 - st["kd_star_mW"]) < 0.6
            rows.append({
                "qb_mW": qb * 1e3,
                "stored_kd_star_mW": st["kd_star_mW"],
                "global_min_kd_mW": float(g[gm] * 1e3),
                "global_min_rmse_K": float(c[gm]),
                "n_basins": len(basins), "basins": basins,
                "stored_agrees_with_global_min": bool(agrees),
                "runner_up_gap_K": (float(sorted(b["rmse_K"] for b in basins)[1]
                                          - c[gm]) if len(basins) > 1 else None),
                "kd_grid_mW": (g * 1e3).tolist(), "rmse_K": c.tolist(),
            })
            print(f"  {tag} Qb={qb*1e3:5.1f}  global {g[gm]*1e3:6.2f} "
                  f"(R={c[gm]:.4f})  stored {st['kd_star_mW']:6.2f}  "
                  f"basins={len(basins)}"
                  f"{'' if agrees else '   <<< DISAGREES'}", flush=True)
        out["sites"][tag] = rows
    p = ROOT / "results" / "qb_basin_audit.json"
    p.write_text(json.dumps(out, indent=1))
    print(f"wrote {p} [{time.time()-t0:.0f} s]", flush=True)


if __name__ == "__main__":
    main()
