#!/usr/bin/env python3
"""Discretization convergence check: dt and the spatial grid.

The 2026-07-03 audit found that dt = 3600 s and the geometric grid
(dz0 = 2 mm, growth = 8%) were the last two production inputs with NO
convergence artifact in results/ (the house rule: an input is founded when
a test shows the answer stopped depending on it). This script closes that
gap: one converged A15 solve at the retrieved K_d* under

  * the production setting        (dt = DT_STEP, dz0 = 2 mm, growth 0.08)
  * a halved time step            (dt = DT_STEP/2, same grid)
  * a refined grid                (dz0 = 1 mm, growth 0.06, same dt)

and reports the cycle-mean temperature shift at the deep-sensor depths
(0.8--2.4 m). The pass criterion mirrors the solver's own certification
scale: shifts well below the 0.05 K guess-independence threshold mean the
discretization contributes negligibly to K_d* (sensor-band dT of 0.01 K
maps to roughly 0.01-0.02 mW in K_d*, far under the 0.5+ mW bootstrap CI).

Writes: results/discretization_check.json
Run:    python pipeline/compute/check_discretization.py   (~2 min)
Re-run whenever DT_STEP or GRID changes in config.py.
"""
from __future__ import annotations

import functools
import json
import pathlib
import sys

import numpy as np

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from lunar.config import SITES, GRID, HAYNE, T_LUNAR, DT_STEP
from lunar.grid import make_geometric_grid
from lunar.properties import conductivity_hayne, specific_heat
from lunar.solver import standard_insolation, periodic_time_grid
from lunar.equilibrium import solve_periodic_equilibrium

from _results import retrieved_kd_star

OUT = ROOT / "results" / "discretization_check.json"
SENSOR_DEPTHS = np.array([0.80, 1.00, 1.40, 2.40])   # deep-sensor band [m]


def _solve(dt: float, grid_kw: dict) -> tuple[np.ndarray, np.ndarray]:
    site = SITES["A15"]
    kd = retrieved_kd_star("A15")   # single-sourced from the retrieval json
    g = make_geometric_grid(**grid_kw)
    t = periodic_time_grid(dt)      # commensurate -- arange grids are forbidden
    insol = standard_insolation(site["lat"], t)       # raw; solver applies (1-A)
    K = functools.partial(conductivity_hayne, Ks=HAYNE["K_S"], Kd=kd,
                          H=HAYNE["H"], chi=HAYNE["CHI"])
    cp = functools.partial(specific_heat, model="hayne")
    eq = solve_periodic_equilibrium(
        grid=g, t=t, insolation=insol, albedo=site["albedo"],
        emissivity=site["emissivity"], Q_b=site["Q_BASAL"],
        K_func=K, cp_func=cp, T_guess=site["T_MEAN_EFF"])
    assert eq.converged, f"solve did not converge (dt={dt}, grid={grid_kw})"
    return g.z_mid, eq.T_mean


def main():
    cases = {
        "nominal":   dict(dt=DT_STEP, grid=dict(GRID)),
        "dt_half":   dict(dt=DT_STEP / 2.0, grid=dict(GRID)),
        "grid_fine": dict(dt=DT_STEP, grid=dict(z_max=GRID["z_max"],
                                                dz0=0.001, growth=0.06)),
    }
    profiles = {}
    for name, c in cases.items():
        print(f"solving {name}: dt={c['dt']:.0f} s, grid={c['grid']} ...")
        z, Tm = _solve(c["dt"], c["grid"])
        profiles[name] = np.interp(SENSOR_DEPTHS, z, Tm)
        print(f"  <T> at sensors: {np.round(profiles[name], 4)}")

    ref = profiles["nominal"]
    report = {
        "config": {"dt_nominal_s": DT_STEP, "grid_nominal": GRID,
                   "site": "A15", "Kd": retrieved_kd_star("A15"),
                   "sensor_depths_m": SENSOR_DEPTHS.tolist()},
        "T_sensor_nominal_K": np.round(ref, 4).tolist(),
    }
    for name in ("dt_half", "grid_fine"):
        d = profiles[name] - ref
        report[f"dT_{name}_K"] = np.round(d, 4).tolist()
        report[f"max_abs_dT_{name}_K"] = float(np.max(np.abs(d)))
    report["pass_criterion"] = ("max |dT| at sensor depths << 0.05 K "
                                "(the guess-independence certification scale)")
    report["passed"] = bool(
        max(report["max_abs_dT_dt_half_K"],
            report["max_abs_dT_grid_fine_K"]) < 0.05)

    OUT.write_text(json.dumps(report, indent=1))
    print(f"\nwrote {OUT}")
    print(f"  dt/2:      max |dT| = {report['max_abs_dT_dt_half_K']*1e3:.1f} mK")
    print(f"  fine grid: max |dT| = {report['max_abs_dT_grid_fine_K']*1e3:.1f} mK")
    print(f"  PASSED: {report['passed']}")


if __name__ == "__main__":
    main()
