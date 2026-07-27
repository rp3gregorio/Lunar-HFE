#!/usr/bin/env python3
"""Discussion-chapter illustrations for the thesis (three small figures).

1. fig_audit_waterfall.pdf   -- the audit trail as a step chart:
     K_d*(A17) 8.12 -> 7.51 -> 7.16 -> 7.08 mW/m/K, each drop labeled
     with its cause (stale Q_b, n_inner bias, missing wrap step).
     Values certified in the audit trail (App. B of the thesis).
2. fig_contrast_mechanisms.pdf -- the physical-plausibility budget:
     porosity factor ~1.5 ((1-phi)^2 across Apollo-core phi 0.30-0.45),
     composition factor ~1.3 (basalt vs anorthosite), product ~1.9,
     against the retrieved ratio 7.08/4.60 = 1.54.
3. fig_tsukimi_chain.pdf     -- conceptual chain: THz sounder ->
     sub-skin emission -> RTM needs T(z) -> anchored by in-situ K_d*.

Every number appears in the thesis text with its source; nothing here
is computed fresh.

Run: python code/pipeline/figures/make_discussion_figures.py
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

from lunar.plotting.style import (JGR_HALF, JGR_SINGLE, C_A15, C_A17, C_TEAL,
                                  C_CHAR, C_DIM, C_GRID, C_FOREST, C_CORAL,
                                  fmt_axis, assert_no_overlap)

OUT = _REPO / ".." / "figures"


def fig_audit_waterfall():
    """K_d*(A17) stepping down through the three audited fixes."""
    values = [8.12, 7.51, 7.16, 7.08]          # certified audit trail
    labels = ["initial", "$Q_b$ fixed\n(15$\\to$16)",
              "inner loop\nresolved", "wrap step\nadded"]
    causes = ["stale basal flux", "$n_{\\rm inner}$ bias", "$\\Delta t$ defect"]

    fig, ax = plt.subplots(figsize=(JGR_SINGLE, 2.9),
                           constrained_layout=True)
    # horizontal step segments + dashed vertical drops
    for i, v in enumerate(values):
        color = C_FOREST if i == len(values) - 1 else C_A17
        ax.plot([i - 0.32, i + 0.32], [v, v], color=color, lw=3.2,
                solid_capstyle="round", zorder=3)
    for i in range(len(values) - 1):
        ax.plot([i + 0.32, i + 1 - 0.32], [values[i], values[i + 1]],
                color=C_DIM, lw=1.0, ls="--", zorder=2)
        dv = values[i + 1] - values[i]
        # label above the step's START level, clear of both the segment
        # and the dashed drop (guard-verified empty space)
        ax.annotate(f"${dv:+.2f}$\n{causes[i]}",
                    xy=(i + 0.5, values[i] + 0.08),
                    ha="center", va="bottom", fontsize=7.0, color=C_DIM,
                    linespacing=1.3, zorder=4)
    ax.annotate("certified\n7.08", xy=(3.0, values[-1] - 0.11),
                ha="center", va="top", fontsize=7.4, color=C_FOREST,
                fontweight="bold", linespacing=1.3, zorder=4)
    ax.set_xticks(range(len(values)), labels, fontsize=7.4)
    ax.set_xlim(-0.55, 3.55)
    ax.set_ylim(6.7, 8.72)
    fmt_axis(ax, ylabel="$K_d^{*}$(A17)  (mW m$^{-1}$ K$^{-1}$)",
             title="Three audited input errors, one milliwatt")
    fig.canvas.draw()
    assert_no_overlap(ax)
    fig.savefig(OUT / "fig_audit_waterfall.pdf")
    plt.close(fig)
    print("  -> fig_audit_waterfall.pdf")


def fig_contrast_mechanisms():
    """Mechanism budget for the retrieved A17/A15 conductivity ratio."""
    ratio = 7.08 / 4.60                        # = 1.54, retrieved values
    rows = [
        ("porosity alone\n$(1-\\phi)^2$, $\\phi = 0.30$–$0.45$", 1.5, C_TEAL),
        ("composition alone\nbasalt vs. anorthosite", 1.3, C_TEAL),
        ("both combined", 1.9, C_FOREST),
    ]
    fig, ax = plt.subplots(figsize=(JGR_SINGLE, 2.5),
                           constrained_layout=True)
    ys = [2, 1, 0]
    for (label, f, color), y in zip(rows, ys):
        ax.barh(y, f - 1.0, left=1.0, height=0.52, color=color,
                edgecolor="white", zorder=3,
                alpha=0.9 if color == C_FOREST else 0.75)
        ax.text(0.97, y, label, ha="right", va="center", fontsize=7.4,
                color=C_CHAR, linespacing=1.3)
    ax.axvline(ratio, color=C_A17, lw=1.6, ls="--", zorder=4)
    ax.text(ratio + 0.035, 2.62, "retrieved ratio\n$7.08/4.60 = 1.54$",
            ha="left", va="bottom", fontsize=7.4, color=C_A17,
            linespacing=1.3)
    ax.set_yticks([])
    ax.set_xlim(0.35, 2.05)
    ax.set_ylim(-0.5, 3.3)
    fmt_axis(ax, xlabel="conductivity ratio  A17 / A15",
             title="Ordinary regolith variation covers the contrast")
    fig.canvas.draw()
    assert_no_overlap(ax)
    fig.savefig(OUT / "fig_contrast_mechanisms.pdf")
    plt.close(fig)
    print("  -> fig_contrast_mechanisms.pdf")


def fig_tsukimi_chain():
    """Why a subsurface sounder needs this retrieval: four boxes."""
    boxes = [
        ("TSUKIMI\nterahertz surveyor",
         "maps brightness\ntemperatures from orbit", C_CHAR),
        ("emission from below\nthe diurnal skin",
         "the layer no orbital IR\ncalibration constrains", C_CHAR),
        ("RTM forward model",
         "needs the meter-scale\n$T(z)$ column as input", C_CHAR),
        ("anchored by this work",
         "per-site $K_d^{*}$ from the\nonly in-situ data", C_FOREST),
    ]
    fig, ax = plt.subplots(figsize=(JGR_HALF, 1.75))
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")

    w, h, gap = 0.205, 0.62, 0.052
    x = (1.0 - (len(boxes) * w + (len(boxes) - 1) * gap)) / 2
    y = 0.30
    arrow = dict(arrowstyle="-|>", color=C_CHAR, lw=1.3, mutation_scale=10,
                 shrinkA=0, shrinkB=0)
    for i, (title, detail, edge) in enumerate(boxes):
        ax.add_patch(FancyBboxPatch(
            (x, y), w, h, boxstyle="round,pad=0.010",
            facecolor="white", edgecolor=edge,
            linewidth=1.6 if edge != C_CHAR else 1.1, zorder=3))
        ax.text(x + w / 2, y + h - 0.145, title, ha="center", va="center",
                fontsize=7.6, fontweight="bold", color=C_CHAR,
                linespacing=1.25, zorder=4)
        ax.text(x + w / 2, y + 0.165, detail, ha="center", va="center",
                fontsize=6.7, color=C_DIM, linespacing=1.3, zorder=4)
        if i < len(boxes) - 1:
            ax.annotate("", xy=(x + w + gap - 0.006, y + h / 2),
                        xytext=(x + w + 0.006, y + h / 2),
                        arrowprops=arrow, zorder=2)
        x += w + gap
    ax.text(0.5, 0.09,
            "orbital calibrations constrain the top ${\\sim}30$ cm; "
            "only the Apollo boreholes constrain the meter scale",
            ha="center", va="center", fontsize=7.0, color=C_DIM, zorder=4)

    fig.subplots_adjust(left=0.01, right=0.99, top=0.98, bottom=0.02)
    fig.canvas.draw()
    assert_no_overlap(ax)
    fig.savefig(OUT / "fig_tsukimi_chain.pdf")
    plt.close(fig)
    print("  -> fig_tsukimi_chain.pdf")


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    fig_audit_waterfall()
    fig_contrast_mechanisms()
    fig_tsukimi_chain()


if __name__ == "__main__":
    main()
