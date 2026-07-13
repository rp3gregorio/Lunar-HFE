"""Diurnal wave decay at Apollo 15 (shadowed forcing) — talk-kit data.

One certified periodic-equilibrium solve (continuous Hayne properties at
the site's certified K_d*, DEM-shadowed forcing); stores the full
temperature cycle at a ladder of depths so the talk figure can show the
95-385 K surface swing collapsing with depth — the 5-second visual of
why deep sensors read a stable mean.

Outputs -> results/aogs_wave.json
Run:  .venv/bin/python code/pipeline/compute/aogs_wave.py   (~40 s)
"""
from __future__ import annotations

import functools
import json
import pathlib
import sys

import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3] / "src"))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from lunar._bootstrap import find_repo_root  # noqa: E402
from lunar.config import DT_STEP, GRID, HAYNE, SITES  # noqa: E402
from lunar.grid import make_geometric_grid  # noqa: E402
from lunar.solver import periodic_time_grid  # noqa: E402
from lunar.properties import conductivity_hayne, specific_heat  # noqa: E402
from lunar.equilibrium import solve_periodic_equilibrium  # noqa: E402

import s1_sensitivity as base  # noqa: E402

ROOT = find_repo_root()
OUT = ROOT / "results" / "aogs_wave.json"
DEPTHS_M = [0.0, 0.05, 0.15, 0.30]           # surface .. sub-skin


def main():
    sk = "A15"
    s = SITES[sk]
    dem, ppd = base.load_dem()
    t = periodic_time_grid(DT_STEP)
    az, hor = base.horizon_profile(dem, ppd, s["lat"], s["lon"])
    insol = base.shadowed_insolation(s["lat"], t, az, hor)
    kd = json.loads((ROOT / "results" / "kd_retrieval_results.json")
                    .read_text())[sk]["kd_star"]
    g = make_geometric_grid(**GRID)
    K = functools.partial(conductivity_hayne, Ks=HAYNE["K_S"], Kd=kd,
                          H=HAYNE["H"], chi=HAYNE["CHI"])
    cp = functools.partial(specific_heat, model="hayne")
    eq = solve_periodic_equilibrium(
        g, np.asarray(t), insol, s["albedo"], s["emissivity"], s["Q_BASAL"],
        K_func=K, cp_func=cp, rho_func=None, n_inner=24)

    T = eq.out.T                              # truncated-grid cycle (nz, nt)
    z = eq.out.z
    step = max(1, len(t) // 800)
    series = {}
    for zd in DEPTHS_M:
        i = int(np.argmin(np.abs(z - zd)))
        series[f"{100*zd:.0f}cm"] = dict(
            z_m=float(z[i]),
            T=[float(v) for v in T[i, ::step]],
            swing_K=float(T[i].max() - T[i].min()))
        print(f"  z={z[i]*100:5.1f} cm: swing {T[i].max()-T[i].min():7.2f} K")
    OUT.write_text(json.dumps(dict(
        meta=dict(site=sk, forcing="DEM-shadowed", kd_star=kd,
                  note="cycle from the certified equilibrium's final "
                       "inner run (truncated Step-A grid)"),
        t_days=[float(v) for v in np.asarray(t)[::step] / 86400.0],
        series=series), indent=1))
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
