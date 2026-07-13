#!/usr/bin/env python3
"""Teaching figure: certifying the time step in K_d* space (the dt ladder).

One panel, real certification data (A17, the sensitive site):
  * the BUGGY march (missing wrap step + frozen properties):
    K_d* = 7.699 / 7.397 / 7.251 mW at dt = 1800/900/450 s -- clean
    first-order convergence, with its Richardson extrapolation to dt -> 0;
  * the FIXED march (wrap step + midpoint Picard): 7.0795 / 7.0975 / 7.1045
    -- flat, and landing on the buggy scheme's extrapolated limit.
The two discretizations agreeing on the same continuum limit is the
built-in cross-check the guidebook section teaches.

Data: results/dt_kdstar_certification_A17wide.json (buggy march)
      results/dt_kdstar_certification_A17_wrapfix.json (fixed march)
Writes docs/guidebook/figures/fig_dt_ladder.pdf.
Run: python pipeline/figures/make_dt_ladder_figure.py
"""
from __future__ import annotations

import json
import pathlib
import sys

import numpy as np
import matplotlib.pyplot as plt

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from lunar.plotting.style import (JGR_HALF, C_CORAL, C_FOREST, C_DIM, C_GRID,
                                  C_CHAR, fmt_axis, assert_no_overlap)

OUT = ROOT / ".." / "figures"


def _load(tag):
    d = json.loads((ROOT / "results" /
                    f"dt_kdstar_certification_{tag}.json").read_text())
    if "rows" in d:            # dt_ladder.py schema (wrap-fix era)
        rows = d["rows"]
        return (np.array([r["dt_s"] for r in rows]),
                np.array([r["kd_star"] for r in rows]) * 1e3)
    # legacy schema: {"1800": {"kd_star_mW": ...}, ...} (buggy-march ladder)
    dts = sorted((float(k) for k in d), reverse=True)
    return (np.array(dts),
            np.array([d[f"{dt:g}"]["kd_star_mW"] for dt in dts]))


def main():
    dt_bug, kd_bug = _load("A17wide")
    dt_fix, kd_fix = _load("A17_wrapfix")
    # Richardson limit of the first-order (buggy) ladder from its finest pair
    rich = 2 * kd_bug[-1] - kd_bug[-2]

    fig, ax = plt.subplots(figsize=(JGR_HALF, 3.5), constrained_layout=True)

    ax.axhline(rich, color=C_DIM, ls="--", lw=1.1, zorder=1)
    ax.plot(dt_bug, kd_bug, "o-", color=C_CORAL, lw=1.6, ms=6,
            mec="white", mew=0.8, zorder=4,
            label="buggy march (missing wrap step): first order")
    # first-order extrapolation of the buggy ladder toward dt -> 0
    c = (kd_bug[-2] - kd_bug[-1]) / (dt_bug[-2] - dt_bug[-1])
    dts = np.linspace(0.0, dt_bug[0], 50)
    ax.plot(dts, rich + c * dts, ls=":", color=C_CORAL, lw=1.1, alpha=0.8,
            zorder=2, label=r"its $O(\Delta t)$ fit $\to$ Richardson limit")
    ax.plot(dt_fix, kd_fix, "s-", color=C_FOREST, lw=1.6, ms=6,
            mec="white", mew=0.8, zorder=5,
            label="fixed march (wrap step + midpoint Picard)")

    # annotate the punchline in the empty upper-left region, leader-free
    ax.text(0.03, 0.97,
            "two different discretizations,\n"
            f"one continuum limit: {rich:.2f} mW m$^{{-1}}$ K$^{{-1}}$",
            transform=ax.transAxes, ha="left", va="top", fontsize=8,
            color=C_CHAR)

    fmt_axis(ax, xlabel=r"time step $\Delta t$  (s)",
             ylabel=r"retrieved $K_d^{*}$(A17)  (mW m$^{-1}$ K$^{-1}$)",
             title="The dt ladder, in the quantity we publish")
    ax.set_xlim(0, 1900)
    ax.set_ylim(6.95, 7.80)
    # data spans the full width at both top and bottom -- legend goes
    # OUTSIDE (below), never into a guessed interior pocket
    h, l = ax.get_legend_handles_labels()
    fig.legend(h, l, ncol=1, loc="lower center", frameon=True,
               edgecolor=C_GRID, fontsize=7.2, bbox_to_anchor=(0.5, -0.28))

    fig.canvas.draw()
    assert_no_overlap(ax)
    OUT.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT / "fig_dt_ladder.pdf", bbox_inches="tight")
    plt.close(fig)
    print("  -> fig_dt_ladder.pdf")


if __name__ == "__main__":
    main()
