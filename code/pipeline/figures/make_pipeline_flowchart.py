#!/usr/bin/env python3
"""Whole-thesis pipeline flowchart: restored record -> retrieved K_d*.

One downward spine (record -> windows -> cut -> solve -> vertex ->
uncertainty -> result) with a single loop-back channel on the right for
the K_d sweep. Chapter tags ride in each box's detail line, so the
figure doubles as a visual table of contents. Every number is certified:
  threshold 0.08 K/yr, N = 7/16, 0.636 s/solve, 29/32 sweep points,
  1500 bootstrap resamples, K_d* = 4.60/7.08, contrast +2.31 [-0.12, 3.56],
  ordering >= 99% across the flux envelope.

Output: figures/fig_pipeline_overview.pdf
Run:    python code/pipeline/figures/make_pipeline_flowchart.py
"""
from __future__ import annotations
import pathlib
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch

_REPO = pathlib.Path(__file__).resolve().parents[1].parent
sys.path.insert(0, str(_REPO / "src"))

from lunar.plotting.style import (JGR_HALF, C_CHAR, C_DIM, C_TEAL, C_FOREST,
                                  C_CORAL, assert_no_overlap)

OUT = _REPO / ".." / "figures"

# (title, detail, edge color)
BOXES = [
    ("Restored HFE record, 1971–1977",
     "both sites, both probes, restored from the\n"
     "original mission tapes  (Ch. 2)",
     C_CHAR),
    ("Stability windows $\\rightarrow$ one $T_{\\rm eq}$ per sensor",
     "longest flat tail, $|$trend$| < 0.08$ K yr$^{-1}$;\n"
     "fallback: final quarter  (Ch. 2)",
     C_CHAR),
    ("Deep-sensor cut $z \\geq 80$ cm",
     "amplitude diagnostic rejects borestem-heated\n"
     "sensors; $N = 7$ (A15), $16$ (A17)  (Ch. 2)",
     C_CHAR),
    ("Flux-anchored equilibrium solve",
     "periodic steady state for one $K_d$ candidate,\n"
     "${\\sim}2500\\times$ faster than brute force  (Ch. 3)",
     C_TEAL),
    ("RMSE$(K_d)$ $\\rightarrow$ parabolic vertex $K_d^{*}$",
     "29 / 32 candidates per site; deep-sensor\n"
     "misfit bowl  (Ch. 4)",
     C_TEAL),
    ("Uncertainty: bootstrap + systematics",
     "1500 sensor resamples with depth jitter;\n"
     "every fixed input swept  (Ch. 4)",
     C_CORAL),
    ("$K_d^{*} = 4.60\\,/\\,7.08$ mW m$^{-1}$ K$^{-1}$",
     "contrast $+2.31$ $[-0.12, 3.56]$, marginal;\n"
     "ordering $\\geq 99\\%$ across the $Q_b$ envelope  (Ch. 5)",
     C_FOREST),
]

BOX_W, BOX_H, GAP = 0.66, 0.105, 0.030
X0 = 0.03


def main():
    fig, ax = plt.subplots(figsize=(JGR_HALF, 6.2))
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")

    n = len(BOXES)
    total = n * BOX_H + (n - 1) * GAP
    y_top = 0.5 + total / 2

    pos = []
    for i, (title, detail, edge) in enumerate(BOXES):
        y = y_top - i * (BOX_H + GAP) - BOX_H
        ax.add_patch(FancyBboxPatch(
            (X0, y), BOX_W, BOX_H, boxstyle="round,pad=0.012",
            facecolor="white", edgecolor=edge,
            linewidth=1.6 if edge != C_CHAR else 1.1, zorder=3))
        cx = X0 + BOX_W / 2
        ax.text(cx, y + BOX_H - 0.024, title, ha="center", va="center",
                fontsize=8.6, fontweight="bold", color=C_CHAR, zorder=4)
        ax.text(cx, y + 0.034, detail, ha="center", va="center",
                fontsize=7.1, color=C_DIM, linespacing=1.35, zorder=4)
        pos.append((cx, y, y + BOX_H))

    arrow = dict(arrowstyle="-|>", color=C_CHAR, lw=1.4, mutation_scale=13,
                 shrinkA=0, shrinkB=0)
    for i in range(n - 1):
        cx = pos[i][0]
        ax.annotate("", xy=(cx, pos[i + 1][2] + 0.012),
                    xytext=(cx, pos[i][1] - 0.012), arrowprops=arrow, zorder=2)

    # sweep loop on the right: vertex box -> solver box, one clean channel
    xr = X0 + BOX_W + 0.014
    xc = X0 + BOX_W + 0.13
    y_vertex = (pos[4][1] + pos[4][2]) / 2
    y_solve = (pos[3][1] + pos[3][2]) / 2
    ax.plot([xr, xc], [y_vertex, y_vertex], color=C_CHAR, lw=1.4,
            solid_capstyle="round", zorder=2)
    ax.plot([xc, xc], [y_vertex, y_solve], color=C_CHAR, lw=1.4,
            solid_capstyle="round", zorder=2)
    ax.annotate("", xy=(xr, y_solve), xytext=(xc, y_solve),
                arrowprops=arrow, zorder=2)
    ax.text(xc + 0.012, (y_vertex + y_solve) / 2, "next $K_d$\ncandidate",
            fontsize=7.2, color=C_DIM, ha="left", va="center",
            linespacing=1.3, zorder=4)

    fig.subplots_adjust(left=0.01, right=0.99, top=0.995, bottom=0.005)
    fig.canvas.draw()
    assert_no_overlap(ax)
    OUT.mkdir(parents=True, exist_ok=True)
    out = OUT / "fig_pipeline_overview.pdf"
    fig.savefig(out)
    plt.close(fig)
    print(f"  -> {out.resolve()}")


if __name__ == "__main__":
    main()
