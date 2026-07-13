#!/usr/bin/env python3
"""Measured wall-clock: flux-anchored vs brute force (guidebook Fig.).

Honest, measured per-solve and per-sweep timings -- no inflated factors.
ALL numbers are read from results/speedup_benchmark.json, the archive
written by pipeline/compute/benchmark_speedup.py (median of 3 anchored
solves, JIT warmed; brute per-lunation cost x 3000 lunations to ~0.1 K).
Re-run that script after any solver-config change, then this figure.

The bootstrap is deliberately omitted: it re-uses the cached sweep profiles
and costs seconds either way, so it does not multiply the comparison.

Run:  python pipeline/figures/make_speedup_figure.py
"""
from __future__ import annotations
import json
import pathlib

import numpy as np
import matplotlib.pyplot as plt

from lunar.plotting.style import JGR_HALF, C_CORAL, C_FOREST, C_CHAR, C_DIM, C_GRID

_REPO = pathlib.Path(__file__).resolve().parents[2]
_OUT = _REPO / "results" / "figures"

_BENCH = json.loads((_REPO / "results" / "speedup_benchmark.json").read_text())
T_ANCH = float(_BENCH["t_anchored_s"])    # s, one flux-anchored solve (measured)
T_BRUTE = float(_BENCH["t_brute_s"])      # s, one brute-force solve to ~0.1 K
N_SOLVES = int(_BENCH["N_solves"])        # trial K_d count, both sites (KD_GRIDS)


def _fmt(t):
    if t < 90:
        return f"{t:.0f} s"
    if t < 5400:
        return f"{t/60:.0f} min"
    return f"{t/3600:.1f} h"


def main():
    groups = ["one solve", f"full $K_d$ sweep\n({N_SOLVES} solves)"]
    anch = np.array([T_ANCH, T_ANCH * N_SOLVES])
    brute = np.array([T_BRUTE, T_BRUTE * N_SOLVES])
    y = np.arange(len(groups))[::-1]      # top group first
    h = 0.34

    fig, ax = plt.subplots(figsize=(JGR_HALF, 2.9), constrained_layout=True)
    ax.barh(y + h/2, brute, height=h, color=C_CORAL, label="brute force", zorder=3)
    ax.barh(y - h/2, anch, height=h, color=C_FOREST, label="flux-anchored", zorder=3)
    ax.set_xscale("log")
    ax.set_xlim(3, 3e5)   # headroom so the right-edge labels never clip

    # explicit labels (straight from the measured archive), parked just past
    # each bar end so they never overlap the bar
    lab_brute = [rf"$\approx${_fmt(brute[0])}", rf"$\approx${_fmt(brute[1])}"]
    lab_anch = [_fmt(anch[0]), rf"$\approx${_fmt(anch[1])}"]
    for yi, tb, ta, lb, la in zip(y, brute, anch, lab_brute, lab_anch):
        ax.text(tb * 1.18, yi + h/2, lb, va="center", ha="left",
                fontsize=8.5, color=C_CHAR)
        ax.text(ta * 1.18, yi - h/2, la, va="center", ha="left",
                fontsize=8.5, color=C_CHAR)
    # one ratio label, parked at the right edge clear of every bar
    ax.text(2.6e5, 0.5, rf"$\approx {T_BRUTE / T_ANCH:.0f}\times$" + "\nfaster",
            ha="right", va="center", fontsize=10, color=C_DIM, fontstyle="italic")

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
