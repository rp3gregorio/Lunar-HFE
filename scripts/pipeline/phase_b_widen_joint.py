"""Re-run the joint K_d × H sweep with a wider H range so the joint
minimum is bracketed away from the grid boundary and the star
markers in fig_robustness do not sit at the corners of the panels.

H grid is extended from [3, 10] cm to [3, 14] cm; resolution kept
at 8 points (so dH = ~1.6 cm). K_d grid stays the same span as in
phase_a_pipeline.py for each site.
"""
from __future__ import annotations
import json, sys, pathlib, time
import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "scripts"))
from phase_a_pipeline import (   # type: ignore
    SITES, joint_kd_h_dense, kd_star_from_residuals,
)

PHASE_A = pathlib.Path(__file__).resolve().parents[2] / "output/phase_a_results.json"

def main():
    t0 = time.time()
    d = json.loads(PHASE_A.read_text())

    # Wider H grid + 8-point K_d grid centered on each site's optimum
    h_grid = np.linspace(0.03, 0.14, 8)   # 3 → 14 cm

    for name in ("A15", "A17"):
        ks = d[name]["kd_star"]
        kd_grid = np.linspace(0.55 * ks, 1.45 * ks, 8)
        print(f"\n=== Joint K_d × H widened ({name}) — "
              f"K_d ∈ [{kd_grid[0]*1e3:.1f}, {kd_grid[-1]*1e3:.1f}], "
              f"H ∈ [{h_grid[0]*100:.0f}, {h_grid[-1]*100:.0f}] cm ===",
              flush=True)
        rmse = joint_kd_h_dense(SITES[name], kd_grid, h_grid)
        i, j = np.unravel_index(np.argmin(rmse), rmse.shape)
        d[name]["joint_kd_h"] = dict(
            h_grid=h_grid.tolist(), kd_grid=kd_grid.tolist(),
            rmse2d=rmse.tolist(),
            h_min=float(h_grid[i]), kd_min=float(kd_grid[j]),
            rmse_min=float(rmse[i, j]))
        print(f"   minimum: K_d = {kd_grid[j]*1e3:.2f} mW/m/K,  "
              f"H = {h_grid[i]*100:.1f} cm,  RMSE = {rmse[i, j]:.3f} K",
              flush=True)

    PHASE_A.write_text(json.dumps(d, indent=2))
    print(f"\nUpdated: {PHASE_A}    [t={time.time()-t0:.0f}s]", flush=True)

if __name__ == "__main__":
    main()
