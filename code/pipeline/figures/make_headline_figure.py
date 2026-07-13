#!/usr/bin/env python3
"""The result in one glance (guidebook ch. "The result", opening figure).

A two-row dot-and-whisker ("forest") plot: the retrieved per-site K_d* with
its 95% bootstrap CI, against the Hayne (2017) global value. This is the
simplest honest presentation of the headline result -- no distributions to
parse, just where each site landed and how far the intervals reach.

All values from results/kd_retrieval_results.json.
Run:  python pipeline/figures/make_headline_figure.py
"""
from __future__ import annotations

import json
import pathlib
import sys

import matplotlib.pyplot as plt

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "src"))
from lunar.plotting.style import (JGR_HALF, C_A15, C_A17, C_HAYNE, C_CHAR,
                                  C_DIM, C_GRID, fmt_axis, assert_no_overlap)

ROOT = pathlib.Path(__file__).resolve().parents[2]
OUT = ROOT / "results" / "figures"
HAYNE_GLOBAL = 3.4          # Hayne et al. (2017) single global K_d [mW/m/K]


def main():
    d = json.loads((ROOT / "results" / "kd_retrieval_results.json").read_text())
    rows = []
    for site, col in (("A17", C_A17), ("A15", C_A15)):     # A17 on top
        b = d[site]["bootstrap"]
        rows.append((d[site]["kd_star"] * 1e3, b["ci_lo"] * 1e3,
                     b["ci_hi"] * 1e3, site, col))

    fig, ax = plt.subplots(figsize=(JGR_HALF, 2.0), constrained_layout=True)
    for y, (kd, lo, hi, site, col) in enumerate(rows):
        ax.plot([lo, hi], [y, y], color=col, lw=2.2, solid_capstyle="butt",
                zorder=3)
        for x in (lo, hi):
            ax.plot([x, x], [y - 0.09, y + 0.09], color=col, lw=2.2, zorder=3)
        ax.plot([kd], [y], "o", color=col, mec="white", mew=1.2, ms=10,
                zorder=4)
        ax.text(kd, y + 0.22, f"{kd:.2f}", ha="center", va="bottom",
                fontsize=9, color=C_CHAR, fontweight="bold")
    ax.axvline(HAYNE_GLOBAL, color=C_HAYNE, ls="--", lw=1.3, zorder=2)
    ax.text(HAYNE_GLOBAL - 0.12, 1.62, "Hayne 2017\nglobal 3.4", ha="right",
            va="top", fontsize=8, color=C_HAYNE)

    ax.set_yticks([0, 1])
    ax.set_yticklabels(["Apollo 17", "Apollo 15"])
    ax.get_yticklabels()[0].set_color(C_A17)
    ax.get_yticklabels()[1].set_color(C_A15)
    ax.set_ylim(-0.55, 1.75)
    ax.set_xlim(2.5, 9.0)
    fmt_axis(ax, xlabel=r"deep conductivity $K_d^{*}$  (mW m$^{-1}$ K$^{-1}$)",
             ylabel="",
             title="the result in one glance: per-site $K_d^{*}$ with 95% CI")
    ax.tick_params(axis="y", length=0)
    for s in ("left",):
        ax.spines[s].set_visible(False)

    fig.canvas.draw()
    assert_no_overlap(ax)
    OUT.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT / "fig_headline.pdf")
    plt.close(fig)
    print("  -> fig_headline.pdf")


if __name__ == "__main__":
    main()
