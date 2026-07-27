#!/usr/bin/env python3
"""Hardware-independent speed-up factors (thesis Ch-3 Fig.).

The thesis reports solver cost as a RATIO (machine-independent) rather
than wall-clock time (machine-dependent). This figure plots those
factors, all read from results/speedup_benchmark.json:
  speedup_per_solve         ~21x  (flux-anchored vs brute, both interpreted)
  speedup_kernel_over_generic ~117x (compiled kernel vs interpreted Step A)
  speedup_fast_per_solve    ~2500x (compiled anchored vs interpreted brute)
The same factor applies per solve and to the full N_solves sweep.

Distinct from fig_speedup.pdf (the guidebook's measured-time bar chart);
this one carries no absolute times.

Run:  python code/pipeline/figures/make_speedup_factors_figure.py
"""
from __future__ import annotations
import json
import pathlib

import numpy as np
import matplotlib.pyplot as plt

from lunar.plotting.style import (JGR_HALF, C_CORAL, C_FOREST, C_TEAL,
                                  C_CHAR, C_DIM, C_GRID)

_REPO = pathlib.Path(__file__).resolve().parents[2]
_OUT = _REPO / ".." / "figures"
_BENCH = json.loads((_REPO / "results" / "speedup_benchmark.json").read_text())

F_ALG = float(_BENCH["speedup_per_solve"])            # ~21x
F_KERNEL = float(_BENCH["speedup_kernel_over_generic"])  # ~117x
F_TOTAL = float(_BENCH["speedup_fast_per_solve"])     # ~2465x


def main():
    rows = [
        ("brute force\n(interpreted)", 1.0, C_DIM),
        ("flux-anchored\n(interpreted)", F_ALG, C_FOREST),
        ("flux-anchored\n(compiled kernel)", F_TOTAL, C_TEAL),
    ]
    labels = [r[0] for r in rows]
    vals = np.array([r[1] for r in rows])
    colors = [r[2] for r in rows]
    y = np.arange(len(rows))[::-1]

    fig, ax = plt.subplots(figsize=(JGR_HALF, 2.7), constrained_layout=True)
    ax.barh(y, vals, height=0.55, color=colors, zorder=3)
    ax.set_xscale("log")
    ax.set_xlim(0.7, 1.1e4)
    for yi, v, c in zip(y, vals, colors):
        lab = "1× (baseline)" if v == 1.0 else f"{v:.0f}×"
        ax.text(v * 1.25, yi, lab, va="center", ha="left", fontsize=9,
                color=C_CHAR)
    # decomposition note in the empty upper-right
    ax.text(9.5e3, y[0] + 0.02,
            f"$\\approx{F_ALG:.0f}\\times$ algorithm\n"
            f"$\\times\\,{F_KERNEL:.0f}\\times$ kernel",
            ha="right", va="center", fontsize=7.6, color=C_DIM,
            linespacing=1.4)
    ax.set_yticks(y)
    ax.set_yticklabels(labels, fontsize=8.5)
    ax.set_xlabel("speed-up factor vs brute force  (log scale, ratio)")
    ax.set_title("Solver speed-up (hardware-independent)", loc="left")
    ax.grid(axis="x", color=C_GRID, lw=0.5, which="both")
    ax.set_axisbelow(True)
    ax.spines["left"].set_visible(False)
    ax.tick_params(axis="y", length=0)

    _OUT.mkdir(parents=True, exist_ok=True)
    out = _OUT / "fig_speedup_factors.pdf"
    fig.savefig(out)
    plt.close(fig)
    print(f"  wrote {out}  ({F_ALG:.0f}x alg, {F_KERNEL:.0f}x kernel, "
          f"{F_TOTAL:.0f}x total)")


if __name__ == "__main__":
    main()
