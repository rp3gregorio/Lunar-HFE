#!/usr/bin/env python3
"""The worked RMSE sweep, drawn: the A17 bowl, the three bracketing
points of App.~C's hand calculation, and the parabola vertex at 7.08.

All values read from results/kd_retrieval_results.json (the same artifact
the worked example quotes) -- nothing hand-entered.

Writes docs/guidebook/figures/fig_sweep_worked.pdf.
Run: python pipeline/figures/make_sweep_worked_figure.py
"""
from __future__ import annotations

import json
import pathlib
import sys

import numpy as np
import matplotlib.pyplot as plt

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from lunar.plotting.style import (JGR_HALF, C_A17, C_CHAR, C_DIM, C_GRID,
                                  C_FOREST, fmt_axis, assert_no_overlap)

OUT = ROOT / ".." / "figures"


def main():
    d = json.loads((ROOT / "results" / "kd_retrieval_results.json").read_text())
    kg = np.array(d["A17"]["kd_grid"]) * 1e3
    rc = np.array(d["A17"]["rmse_curve"])
    ks = d["A17"]["kd_star"] * 1e3

    # the three hand-worked bracket points (equal 0.2 mW spacing)
    bx = np.array([6.8, 7.0, 7.2])
    by = np.array([rc[np.argmin(np.abs(kg - v))] for v in bx])
    # the parabola through them (the App-C arithmetic, drawn)
    coef = np.polyfit(bx, by, 2)
    xx = np.linspace(6.55, 7.45, 200)

    fig, ax = plt.subplots(figsize=(JGR_HALF, 3.1), constrained_layout=True)
    m = (kg >= 6.0) & (kg <= 8.6)
    ax.plot(kg[m], rc[m], "o-", ms=3.5, lw=1.0, color=C_DIM, mec="white",
            mew=0.4, zorder=2, label="swept RMSE grid")
    ax.plot(xx, np.polyval(coef, xx), "-", color=C_A17, lw=1.6, zorder=3,
            label="parabola through the 3 bracket points")
    ax.plot(bx, by, "o", ms=7, color=C_A17, mec="white", mew=0.9, zorder=4,
            label=r"bracket: $y_-,\,y_0,\,y_+$ (worked by hand)")
    ax.axvline(ks, color=C_FOREST, lw=1.2, ls="--", zorder=1)
    ax.annotate(rf"vertex $K_d^{{*}} = {ks:.2f}$",
                (ks, np.polyval(coef, ks)), (7.62, 0.394), fontsize=8,
                color=C_FOREST,
                arrowprops=dict(arrowstyle="-", color=C_FOREST, lw=0.8))

    fmt_axis(ax, xlabel=r"trial $K_d$  (mW m$^{-1}$ K$^{-1}$)",
             ylabel="RMSE  (K)",
             title="The worked sweep, drawn (Apollo 17)")
    ax.set_xlim(5.9, 8.7)
    ax.set_ylim(0.392, 0.435)
    h, l = ax.get_legend_handles_labels()
    fig.legend(h, l, ncol=1, loc="lower center", frameon=True,
               edgecolor=C_GRID, fontsize=7, bbox_to_anchor=(0.5, -0.24))

    fig.canvas.draw()
    assert_no_overlap(ax)
    OUT.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT / "fig_sweep_worked.pdf", bbox_inches="tight")
    plt.close(fig)
    print("  -> fig_sweep_worked.pdf")


if __name__ == "__main__":
    main()
