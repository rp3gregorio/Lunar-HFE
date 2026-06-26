#!/usr/bin/env python3
"""Measured wall-clock: flux-anchored vs brute force (guidebook Fig.).

Honest, measured per-solve and per-sweep timings -- no inflated factors.
Numbers are MEASURED on this machine by scratchpad bench_speedup.py (median of
3 runs, Numba JIT warmed up); archived in results/speedup_benchmark.json:

  * flux-anchored solve  6.9 s       (median of 6.82, 6.91, 6.93 s; 10 outer iters)
  * brute-force rate     0.082 s/lun (from a 100- and 300-lunation timing)
  * brute-force solve    ~245 s      (0.082 s/lun x 3000 lun to ~0.1 K, the
                                      convergence established by fig_equilibrium_demo)
  * full K_d sweep = 56 solves (28 trial K_d x 2 sites)

  => per-solve speed-up ~35x (NOT the earlier hardcoded 80x: that assumed a
     0.23 s/lun brute rate, ~3x too high).

The bootstrap is deliberately omitted: it re-uses the 56 cached profiles and
costs seconds either way, so it does not multiply the comparison.

Run:  python pipeline/figures/make_speedup_figure.py
"""
from __future__ import annotations
import pathlib

import numpy as np
import matplotlib.pyplot as plt

from lunar.plotting.style import JGR_HALF, C_CORAL, C_FOREST, C_CHAR, C_DIM, C_GRID

_REPO = pathlib.Path(__file__).resolve().parents[2]
_OUT = _REPO / "results" / "figures"

T_ANCH = 6.9           # s, one flux-anchored solve (measured median of 3 runs)
T_BRUTE = 245.0        # s, one brute-force solve to ~0.1 K (0.082 s/lun x 3000 lun)
N_SOLVES = 56          # 28 trial K_d x 2 sites


def _fmt(t):
    if t < 90:
        return f"{t:.0f} s"
    if t < 5400:
        return f"{t/60:.0f} min"
    return f"{t/3600:.1f} h"


def main():
    groups = ["one solve", "full $K_d$ sweep\n(56 solves)"]
    anch = np.array([T_ANCH, T_ANCH * N_SOLVES])
    brute = np.array([T_BRUTE, T_BRUTE * N_SOLVES])
    y = np.arange(len(groups))[::-1]      # top group first
    h = 0.34

    fig, ax = plt.subplots(figsize=(JGR_HALF, 2.9), constrained_layout=True)
    ax.barh(y + h/2, brute, height=h, color=C_CORAL, label="brute force", zorder=3)
    ax.barh(y - h/2, anch, height=h, color=C_FOREST, label="flux-anchored", zorder=3)
    ax.set_xscale("log")
    ax.set_xlim(3, 6e4)

    # explicit labels (measured; kept consistent with the §3.13 prose), parked
    # just past each bar end so they never overlap the bar
    lab_brute = [r"$\approx$245 s", r"$\approx$3.8 h"]
    lab_anch = ["6.9 s", r"$\approx$6.5 min"]
    for yi, tb, ta, lb, la in zip(y, brute, anch, lab_brute, lab_anch):
        ax.text(tb * 1.18, yi + h/2, lb, va="center", ha="left",
                fontsize=8.5, color=C_CHAR)
        ax.text(ta * 1.18, yi - h/2, la, va="center", ha="left",
                fontsize=8.5, color=C_CHAR)
    # one ratio label, parked at the right edge clear of every bar
    ax.text(5.5e4, 0.5, r"$\approx 35\times$" + "\nfaster", ha="right",
            va="center", fontsize=10, color=C_DIM, fontstyle="italic")

    ax.set_yticks(y)
    ax.set_yticklabels(groups)
    ax.set_xlabel("wall-clock time  [s, log scale]")
    ax.set_title("Flux-anchored vs brute force, measured", loc="left")
    # The sweep brute-force bar runs almost to the right edge, so a lower-right
    # legend would sit on it; the top row's bars are short (<=700 s), leaving the
    # upper-right quadrant empty -- park the legend there instead.
    ax.legend(loc="upper right", frameon=True, edgecolor=C_GRID, framealpha=0.97)
    ax.grid(axis="x", color=C_GRID, lw=0.5, which="both")
    ax.set_axisbelow(True)
    ax.spines["left"].set_visible(False)
    ax.tick_params(axis="y", length=0)

    _OUT.mkdir(parents=True, exist_ok=True)
    out = _OUT / "fig_speedup.pdf"
    fig.savefig(out)
    plt.close(fig)
    print(f"  wrote {out}  (per-solve {T_BRUTE/T_ANCH:.0f}x; "
          f"sweep {_fmt(brute[1])} vs {_fmt(anch[1])})")


if __name__ == "__main__":
    main()
