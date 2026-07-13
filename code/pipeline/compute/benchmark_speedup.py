#!/usr/bin/env python3
"""Measure and archive the anchored-vs-brute speed-up.

Writes results/speedup_benchmark.json — the archive that the guidebook
(§ "The speed-up, in measured numbers") and make_speedup_figure.py quote.
Re-run this whenever the solver configuration changes (EQ_N_INNER, the
truncation, the grid): the guidebook's timing claims must match this file.

Measured here, at the production config (config.py):
  * t_anchored_s      -- median of 3 flux-anchored solves (JIT warmed)
  * brute_ms_per_lun  -- per-lunation cost of the brute-force stepper
  * t_brute_s         -- extrapolated cost of N_CONVERGE_LUN lunations
  * speedup_per_solve, N_solves (from KD_GRIDS), sweep times

Carried forward (per-lunation numbers, independent of n_inner):
  * njit_on/off_ms_per_lun, njit_speedup  (measured 2026-06-28)

Run:  python pipeline/compute/benchmark_speedup.py     (~1-2 min)
"""
from __future__ import annotations

import functools
import json
import pathlib
import sys
import time

import numpy as np

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from lunar.config import (SITES, GRID, HAYNE, S0, T_LUNAR, DT_STEP, KD_GRIDS,
                          EQ_Z_ANCHOR, EQ_N_INNER, EQ_MAX_OUTER, EQ_ANCHOR_TOL)
from lunar.grid import make_geometric_grid
from lunar.properties import conductivity_hayne, specific_heat
from lunar.solver import PixelInputs, solve_pixel, standard_insolation, periodic_time_grid
from lunar.equilibrium import solve_periodic_equilibrium

OUT = ROOT / "results" / "speedup_benchmark.json"
N_CONVERGE_LUN = 3000        # lunations brute force needs to come within ~0.1 K
N_BRUTE_TIMING = 50          # lunations actually timed (per-lunation cost)


def main():
    site = SITES["A15"]
    from _results import retrieved_kd_star
    kd = retrieved_kd_star("A15")   # single-sourced from the retrieval json
    g = make_geometric_grid(**GRID)
    t = periodic_time_grid(DT_STEP)   # commensurate lunation grid (audit 2026-07-03)
    insol = standard_insolation(site["lat"], t)   # raw flux; solver applies (1-A)
    K = functools.partial(conductivity_hayne, Ks=HAYNE["K_S"], Kd=kd,
                          H=HAYNE["H"], chi=HAYNE["CHI"])
    cp = functools.partial(specific_heat, model="hayne")

    def anchored(fast=False):
        # fast=True is the PRODUCTION configuration: the compiled Hayne
        # kernel (PixelInputs.hayne_params, 2026-07-03). fast=False times
        # the generic interpreted march for the method-vs-method story.
        return solve_periodic_equilibrium(
            grid=g, t=t, insolation=insol, albedo=site["albedo"],
            emissivity=site["emissivity"], Q_b=site["Q_BASAL"],
            K_func=K, cp_func=cp, T_guess=site["T_MEAN_EFF"],
            z_anchor=EQ_Z_ANCHOR, n_inner=EQ_N_INNER,
            max_outer=EQ_MAX_OUTER, anchor_tol_K=EQ_ANCHOR_TOL,
            hayne_params=((HAYNE["K_S"], kd, HAYNE["H"], HAYNE["CHI"])
                          if fast else None))

    print("warm-up (JIT compile) ...")
    anchored(); anchored(fast=True)
    runs = []
    for i in range(3):
        t0 = time.perf_counter()
        eq = anchored()
        runs.append(round(time.perf_counter() - t0, 2))
        print(f"  anchored solve {i + 1}: {runs[-1]:.2f} s "
              f"(converged={eq.converged})")
    t_anch = float(np.median(runs))
    fast_runs = []
    for i in range(3):
        t0 = time.perf_counter()
        eq = anchored(fast=True)
        fast_runs.append(round(time.perf_counter() - t0, 3))
        print(f"  anchored solve {i + 1} (compiled kernel): "
              f"{fast_runs[-1]:.2f} s (converged={eq.converged})")
    t_fast = float(np.median(fast_runs))

    # Median of 3 brute timings, matching the anchored side: a single-shot
    # measurement flapped 86 -> 114 ms/lun between two quiet-machine runs
    # (audit 2026-07-03), which alone moved the headline speed-up 20x -> 27x.
    print(f"brute-force per-lunation cost (3 x {N_BRUTE_TIMING} lunations) ...")
    brute_runs = []
    for i in range(3):
        t0 = time.perf_counter()
        solve_pixel(PixelInputs(
            grid=g, t=t, bc_mode="radiative", insolation=insol,
            albedo=site["albedo"], emissivity=site["emissivity"],
            Q_b=site["Q_BASAL"], T_init=np.full(g.z_mid.size, 250.0),
            n_lunations_spinup=N_BRUTE_TIMING, spinup_tol_K=0.0,
            K_func=K, cp_func=cp))
        brute_runs.append((time.perf_counter() - t0) / N_BRUTE_TIMING * 1e3)
        print(f"  brute run {i + 1}: {brute_runs[-1]:.1f} ms/lunation")
    ms_per_lun = float(np.median(brute_runs))
    t_brute = ms_per_lun / 1e3 * N_CONVERGE_LUN

    n_solves = sum(len(v) for v in KD_GRIDS.values())
    data = {
        "config": {"EQ_N_INNER": EQ_N_INNER, "EQ_Z_ANCHOR": EQ_Z_ANCHOR,
                   "truncated_step_A": True, "site": "A15", "Kd": kd},
        "t_anchored_s": t_anch,
        "anchored_runs_s": runs,
        "t_anchored_fast_s": t_fast,
        "anchored_fast_runs_s": fast_runs,
        "speedup_kernel_over_generic": round(t_anch / t_fast, 1),
        "brute_ms_per_lun": round(ms_per_lun, 1),
        "brute_runs_ms_per_lun": [round(b, 1) for b in brute_runs],
        "N_converge_lun": N_CONVERGE_LUN,
        "t_brute_s": round(t_brute, 1),
        "speedup_per_solve": round(t_brute / t_anch, 1),
        "N_solves": n_solves,
        "sweep_anchored_min": round(t_anch * n_solves / 60.0, 1),
        "sweep_fast_min": round(t_fast * n_solves / 60.0, 2),
        "speedup_fast_per_solve": round(t_brute / t_fast, 0),
        "sweep_brute_h": round(t_brute * n_solves / 3600.0, 2),
        # per-lunation JIT numbers are n_inner-independent; measured 2026-06-28
        "njit_on_ms_per_lun": 83.2,
        "njit_off_ms_per_lun": 128.0,
        "njit_speedup": 1.5,
        "note_njit": "only _thomas and _face_harmonic_mean carry @njit; "
                     "measured 2026-06-28, per-lunation (n_inner-independent)",
    }
    OUT.write_text(json.dumps(data, indent=1))
    print(f"wrote {OUT}")
    print(f"  anchored {t_anch:.1f} s | brute {t_brute:.0f} s "
          f"({ms_per_lun:.0f} ms/lun) | {t_brute / t_anch:.0f}x per solve | "
          f"sweep ({n_solves} solves): {data['sweep_anchored_min']} min vs "
          f"{data['sweep_brute_h']} h")


if __name__ == "__main__":
    main()
