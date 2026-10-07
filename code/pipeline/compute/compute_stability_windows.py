"""Per-sensor stability windows of the Apollo HFE record (2026-10-05).

Lists, for every sensor at both sites, the window that defines its equilibrium
temperature T_eq: the selection method (strict criterion or fallback), the first
and last date in the window, the number of samples, T_eq, the within-window
standard deviation and the trailing slope. The windows are chosen sensor by
sensor (lunar.apollo_helpers.find_stable_window) and are NOT aligned in time;
this table is what a reproduction needs to rebuild each T_eq exactly.

Reads:  the HFE depth tables via lunar.apollo_helpers
Writes: results/stability_windows.json; prints the SI table rows (LaTeX)
Runtime: seconds.
"""
from __future__ import annotations
import json, sys, pathlib
_REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO)); sys.path.insert(0, str(_REPO / "src"))

import numpy as np
from lunar.config import SITES
from lunar.apollo_helpers import extract_sensor_stability


def main():
    out = {}
    for s in ("A15", "A17"):
        cfg = SITES[s]
        ex = extract_sensor_stability(cfg["mission"], min_depth_cm=0)
        rows = []
        for sen in ex["sensors"]:
            dtab = ex["d1"] if sen["probe"] == 1 else ex["d2"]
            mask = np.char.strip(dtab["sensor"].astype(str)) == sen["sensor"]
            times = dtab["time_iso"][mask]
            i0 = ex["probe_data"][sen["probe"]][sen["sensor"]]["i_start"]
            rows.append(dict(sensor=sen["sensor"], probe=int(sen["probe"]), depth_cm=float(sen["depth_cm"]),
                             used=bool(sen["depth_cm"] >= cfg["MIN_DEPTH_CM"]), method=sen["stable_method"],
                             window_start=str(times[i0])[:10], window_end=str(times[-1])[:10],
                             record_start=str(times[0])[:10], n_samples=int(sen["n_tail"]),
                             T_eq_K=float(sen["T_eq"]), T_std_K=float(sen["T_std"]),
                             trailing_slope_K_per_yr=float(sen["tail_slope_Kyr"])))
        out[s] = rows
    path = _REPO / "results" / "stability_windows.json"
    path.write_text(json.dumps(out, indent=1))
    for s, rows in out.items():
        for r in rows:
            if not r["used"]:
                continue
            meth = "strict" if r["method"] == "trend_flat" else "fallback"
            print(f"{s} & {r['probe']} & {r['sensor']} & {r['depth_cm']:.0f} & {meth} & {r['window_start']} -- {r['window_end']} & "
                  f"{r['n_samples']} & {r['T_eq_K']:.2f} & {r['T_std_K']:.2f} & {r['trailing_slope_K_per_yr']:+.2f} \\\\")
    print("methods seen:", sorted({r['method'] for rows in out.values() for r in rows}))
    print(f"wrote {path.relative_to(_REPO)}")


if __name__ == "__main__":
    main()
