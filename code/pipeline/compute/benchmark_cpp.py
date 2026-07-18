#!/usr/bin/env python3
"""Head-to-head: Python solver vs the faithful C++ port (cpp/solver.cpp).

Scope: the SOLVER only (the brute-force lunation march) -- no bootstrap, no
statistics. Both sides integrate the IDENTICAL problem: same commensurate
time grid, same forcing, same T_init, same constants (dumped to a binary
blob so nothing is re-derived in C++).

Protocol:
  1. verification -- N_VERIFY lunations from the same initial condition;
     require max |T_py - T_cpp| over the FULL final cycle < 1e-6 K
     (the arithmetic mirrors line-for-line; agreement is typically ~1e-9).
  2. timing -- N_TIME lunations, median of 3 runs per side, same machine,
     run back-to-back.

Writes: results/cpp_benchmark.json     (the archive; quote only from here)
Build first:  clang++ -O3 -std=c++17 -o cpp/lunar_solver cpp/solver.cpp
Run:          python pipeline/compute/benchmark_cpp.py
"""
from __future__ import annotations

import functools
import json
import pathlib
import struct
import subprocess
import sys
import time

import numpy as np

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from lunar.config import SITES, GRID, HAYNE, DT_STEP, CN_PICARD_SWEEPS
from lunar.constants import (SIGMA_SB, RHO_SURFACE, RHO_DEEP,
                             CP_HAYNE_C0, CP_HAYNE_C1, CP_HAYNE_C2,
                             CP_HAYNE_C3, CP_HAYNE_C4)
from lunar.grid import make_geometric_grid
from lunar.properties import conductivity_hayne, specific_heat
from lunar.solver import (PixelInputs, solve_pixel, standard_insolation,
                          periodic_time_grid)

BIN = ROOT / "cpp" / "lunar_solver"
OUT = ROOT / "results" / "cpp_benchmark.json"
SCRATCH = ROOT / "results" / ".cpp_io"
N_VERIFY = 10        # lunations for the bit-level verification run
N_TIME = 50          # lunations per timing run (median of 3 per side)
from _results import retrieved_kd_star
KD = retrieved_kd_star("A15")   # same problem as the main benchmark; single-sourced


def dump_inputs(path, g, t, insol, T_init, site, n_lun, kd=None):
    # kd overrides the default K_d so the C++ kernel can be driven across a
    # K_d sweep (used by the C++ brute-force retrieval demo in notebook 06);
    # the binary reads K_d from this file, so no recompile is needed.
    kd_use = KD if kd is None else float(kd)
    with open(path, "wb") as f:
        # n_picard mirrors config.CN_PICARD_SWEEPS so both sides march the
        # same midpoint-Picard scheme (solver._step, 2026-07-03)
        f.write(struct.pack("<4q", g.z_mid.size, t.size, n_lun,
                            CN_PICARD_SWEEPS))
        for arr in (g.z_mid, g.dz, t, insol, T_init):
            f.write(np.asarray(arr, dtype="<f8").tobytes())
        for v in (site["albedo"], site["emissivity"], site["Q_BASAL"],
                  HAYNE["K_S"], kd_use, HAYNE["H"], HAYNE["CHI"], HAYNE["T_REF"],
                  RHO_SURFACE, RHO_DEEP,
                  CP_HAYNE_C0, CP_HAYNE_C1, CP_HAYNE_C2, CP_HAYNE_C3,
                  CP_HAYNE_C4, SIGMA_SB):
            f.write(struct.pack("<d", float(v)))


def run_cpp(inp, outp, n_z, n_t):
    subprocess.run([str(BIN), str(inp), str(outp)], check=True,
                   capture_output=True)
    raw = np.fromfile(outp, dtype="<f8")
    secs = float(raw[0])
    T = raw[1:].reshape(n_z, n_t)
    return secs, T


def run_py(g, t, insol, T_init, site, n_lun, fast=False):
    """Time the Python march: generic _step loop, or (fast=True) the
    compiled hayne_params kernel -- the njit twin of the C++ port."""
    K = functools.partial(conductivity_hayne, Ks=HAYNE["K_S"], Kd=KD,
                          H=HAYNE["H"], chi=HAYNE["CHI"])
    cp = functools.partial(specific_heat, model="hayne")
    hp = (HAYNE["K_S"], KD, HAYNE["H"], HAYNE["CHI"]) if fast else None
    t0 = time.perf_counter()
    out = solve_pixel(PixelInputs(
        grid=g, t=t, bc_mode="radiative", insolation=insol,
        albedo=site["albedo"], emissivity=site["emissivity"],
        Q_b=site["Q_BASAL"], T_init=T_init.copy(),
        n_lunations_spinup=n_lun, spinup_tol_K=0.0, K_func=K, cp_func=cp,
        hayne_params=hp))
    return time.perf_counter() - t0, out.T


def main():
    if not BIN.exists():
        sys.exit(f"build first: clang++ -O3 -std=c++17 -o {BIN} cpp/solver.cpp")
    SCRATCH.mkdir(exist_ok=True)
    site = SITES["A15"]
    g = make_geometric_grid(**GRID)
    t = periodic_time_grid(DT_STEP)
    insol = standard_insolation(site["lat"], t)
    T_init = np.full(g.z_mid.size, site["T_MEAN_EFF"])

    # ---- 1. verification ---------------------------------------------------
    inp, outp = SCRATCH / "in.bin", SCRATCH / "out.bin"
    dump_inputs(inp, g, t, insol, T_init, site, N_VERIFY)
    _, T_cpp = run_cpp(inp, outp, g.z_mid.size, t.size)
    _, T_py = run_py(g, t, insol, T_init, site, N_VERIFY)
    _, T_fast = run_py(g, t, insol, T_init, site, N_VERIFY, fast=True)
    max_dev = float(np.max(np.abs(T_py - T_cpp)))
    max_dev_fast = float(np.max(np.abs(T_fast - T_cpp)))
    print(f"verification ({N_VERIFY} lunations): "
          f"max |T_py - T_cpp| = {max_dev:.3e} K, "
          f"|T_njit - T_cpp| = {max_dev_fast:.3e} K")
    assert max_dev < 1e-6, "C++ port does NOT reproduce the Python solver"
    assert max_dev_fast < 1e-6, "njit kernel does NOT reproduce the C++ port"

    if "--verify-only" in sys.argv:
        # correctness check without the quiet-machine timing requirement
        return

    # ---- 2. timing (median of 3 per side, interleaved) ---------------------
    dump_inputs(inp, g, t, insol, T_init, site, N_TIME)
    py_times, fast_times, cpp_times = [], [], []
    run_py(g, t, insol, T_init, site, 2, fast=True)   # JIT warm-up for Numba
    for _ in range(3):
        s_cpp, _ = run_cpp(inp, outp, g.z_mid.size, t.size)
        cpp_times.append(s_cpp)
        s_fast, _ = run_py(g, t, insol, T_init, site, N_TIME, fast=True)
        fast_times.append(s_fast)
        s_py, _ = run_py(g, t, insol, T_init, site, N_TIME)
        py_times.append(s_py)
    py_ms = float(np.median(py_times)) / N_TIME * 1e3
    fast_ms = float(np.median(fast_times)) / N_TIME * 1e3
    cpp_ms = float(np.median(cpp_times)) / N_TIME * 1e3

    data = {
        "config": {"DT_STEP_target": DT_STEP, "n_t_per_lunation": int(t.size),
                   "n_cells": int(g.z_mid.size), "site": "A15", "Kd": KD,
                   "N_verify_lun": N_VERIFY, "N_time_lun": N_TIME},
        "verification_max_dev_K": max_dev,
        "verification_max_dev_njit_K": max_dev_fast,
        "py_ms_per_lunation": round(py_ms, 2),
        "py_njit_ms_per_lunation": round(fast_ms, 3),
        "cpp_ms_per_lunation": round(cpp_ms, 3),
        "py_runs_s": [round(v, 3) for v in py_times],
        "py_njit_runs_s": [round(v, 3) for v in fast_times],
        "cpp_runs_s": [round(v, 3) for v in cpp_times],
        "speedup_cpp_over_py": round(py_ms / cpp_ms, 1),
        "speedup_njit_over_py": round(py_ms / fast_ms, 1),
        "speedup_cpp_over_njit": round(fast_ms / cpp_ms, 2),
        "note": ("solver march only (no bootstrap/statistics). Three sides: "
                 "generic interpreted _step loop, the compiled njit kernel "
                 "(production fast path), and the C++ port -- all verified "
                 "equal to <1e-6 K first"),
    }
    OUT.write_text(json.dumps(data, indent=1))
    print(f"python(generic): {py_ms:.1f} ms/lun | python(njit): "
          f"{fast_ms:.2f} ms/lun | c++: {cpp_ms:.2f} ms/lun | "
          f"c++ vs generic {py_ms/cpp_ms:.0f}x, njit vs generic "
          f"{py_ms/fast_ms:.0f}x, c++ vs njit {fast_ms/cpp_ms:.2f}x")
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
