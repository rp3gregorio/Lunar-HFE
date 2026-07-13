"""Extend the shadowed K_d grids so both minima are properly bounded.

aogs_kd_shadowed.py found BOTH sites edge-limited: A15's misfit still
falling at the low edge (2.1 mW) and A17's at the high edge (~9.6 mW).
This script reuses that module's forcing + rmse_at verbatim and simply
adds grid points: A15 down to the physical floor K_d = K_s (the Hayne
K_c(z) form degenerates below the surface conductivity), A17 upward to
14 mW. Result: either an interior vertex, or the entire physical range
exhausted -- which turns "edge-limited" into a defensible statement.

Updates results/aogs_kd_shadowed.json in place (adds points + flags).
Run:  .venv/bin/python code/pipeline/compute/aogs_kd_shadowed_extend.py  (~3 min)
"""
from __future__ import annotations

import json
import multiprocessing as mp
import pathlib
import sys

import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3] / "src"))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from lunar._bootstrap import find_repo_root  # noqa: E402
from lunar.config import DT_STEP, HAYNE, SITES  # noqa: E402
from lunar.solver import periodic_time_grid  # noqa: E402

import s1_sensitivity as base  # noqa: E402
import s3_kd_shadowed as ks  # noqa: E402

ROOT = find_repo_root()
OUT = ROOT / "results" / "aogs_kd_shadowed.json"

# physical floor: Hayne K_c(z) interpolates K_s -> K_d; K_d < K_s inverts it
KS_MW = HAYNE["K_S"] * 1e3
NEW_POINTS = {
    "A15": [round(k, 3) for k in (0.75, 1.0, 1.25, 1.5, 1.75, 1.9)],
    "A17": [round(k, 3) for k in (10.0, 10.5, 11.0, 12.0, 13.0, 14.0)],
}


def main():
    d = json.loads(OUT.read_text())
    dem, ppd = base.load_dem()
    t = periodic_time_grid(DT_STEP)

    with mp.Pool(min(8, mp.cpu_count() - 1)) as pool:
        for sk in ("A15", "A17"):
            s = SITES[sk]
            az, hor = base.horizon_profile(dem, ppd, s["lat"], s["lon"])
            insol = base.shadowed_insolation(s["lat"], t, az, hor)
            have = set(d["sites"][sk]["kd_grid_mW"])
            new = [k for k in NEW_POINTS[sk] if k not in have and k >= KS_MW]
            out = pool.map(ks.rmse_at, [(sk, k, insol) for k in new])

            kds = d["sites"][sk]["kd_grid_mW"] + [o[1] for o in out]
            rs = d["sites"][sk]["rmse_K"] + [o[2] for o in out]
            order = np.argsort(kds)
            kds = [kds[i] for i in order]
            rs = [rs[i] for i in order]
            i_min = int(np.argmin(rs))
            interior = 0 < i_min < len(kds) - 1
            entry = d["sites"][sk]
            entry["kd_grid_mW"], entry["rmse_K"] = kds, rs
            entry["extended_to_physical_bounds"] = True
            entry["min_interior"] = bool(interior)
            entry["kd_at_min_mW"] = kds[i_min]
            entry["rmse_min_K"] = float(rs[i_min])
            if interior:
                entry["kd_star_shadowed_mW"] = round(ks.vertex(kds, rs), 3)
                entry["shift_mW"] = round(
                    entry["kd_star_shadowed_mW"]
                    - entry["kd_star_standard_mW"], 3)
            else:
                entry["kd_star_shadowed_mW"] = None       # unbounded: no
                entry["shift_mW"] = None                  # physical vertex
            print(f"  {sk}: min at {kds[i_min]:.2f} mW "
                  f"(RMSE {rs[i_min]:.3f} K), interior={interior}; "
                  f"grid now [{kds[0]:.2f}, {kds[-1]:.2f}] mW "
                  f"(physical floor K_s={KS_MW:.2f})")

    d["meta"]["extended"] = ("grids pushed to physical bounds "
                             "(A15 down to K_s, A17 up to 14 mW) by "
                             "aogs_kd_shadowed_extend.py")
    OUT.write_text(json.dumps(d, indent=1))
    print(f"updated {OUT}")


if __name__ == "__main__":
    main()
