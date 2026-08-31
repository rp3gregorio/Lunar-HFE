#!/usr/bin/env python3
"""Both RMSE sweeps on one axis, each with its parabola vertex.

The A17-only version (make_sweep_worked_figure.py) shows the arithmetic of the
worked example. This one superimposes Apollo 15 so the two results can be read
against each other, which makes three things visible at once:

  * the minima sit at different K_d      -> the sites differ (4.60 vs 7.08)
  * A17's whole bowl lies far lower      -> it also FITS much better
  * both bowls are shallow               -> a few hundredths of a kelvin over
                                            a ~3 mW span, which is why the
                                            bootstrap intervals are ~2 mW wide

That last point is the honest one. The vertex is well defined, but the bowl
around it is nearly flat, so small changes in the data slide the minimum a
long way. The figure should show that rather than hide it.

Everything is read from results/kd_retrieval_results.json — the same artifact
the retrieval writes. Nothing is hand-entered.

Output: figures/fig_sweep_both.pdf  + Others/gedes/defense/img/sweep_both.png
Run:    python code/pipeline/figures/make_sweep_both_figure.py
"""
from __future__ import annotations

import json
import pathlib
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from lunar.plotting.style import (JGR_HALF, C_A15, C_A17, C_CHAR, C_DIM,
                                  C_GRID, fmt_axis)

FIGS = ROOT / ".." / "figures"
DECK = ROOT.parents[1] / "Others" / "gedes" / "defense" / "img"

# the three bracketing points of each hand-worked parabola (0.2 mW spacing,
# the refinement-band step)
BRACKET = {"A15": (4.4, 4.6, 4.8), "A17": (6.8, 7.0, 7.2)}
WINDOW = {"A15": (3.2, 6.4), "A17": (5.4, 9.2)}
COLOUR = {"A15": C_A15, "A17": C_A17}


def main():
    d = json.loads((ROOT / "results" / "kd_retrieval_results.json").read_text())
    fig, ax = plt.subplots(figsize=(JGR_HALF, 4.0))

    for site in ("A15", "A17"):
        g = np.array(d[site]["kd_grid"]) * 1e3
        r = np.array(d[site]["rmse_curve"])
        o = np.argsort(g)
        g, r = g[o], r[o]
        lo, hi = WINDOW[site]
        m = (g >= lo) & (g <= hi)
        c = COLOUR[site]

        ax.plot(g[m], r[m], "-", lw=1.6, color=C_DIM, alpha=0.55, zorder=3)
        ax.plot(g[m], r[m], ".", ms=5, color=C_DIM, alpha=0.75, zorder=4)

        bx = np.array(BRACKET[site])
        by = np.array([r[np.argmin(np.abs(g - v))] for v in bx])
        coef = np.polyfit(bx, by, 2)
        xx = np.linspace(bx[0] - 0.25, bx[-1] + 0.25, 200)
        ax.plot(xx, np.polyval(coef, xx), "-", lw=2.6, color=c, zorder=5)
        ax.plot(bx, by, "o", ms=7, color=c, mec="white", mew=1.2, zorder=6)

        ks = -coef[1] / (2 * coef[0])
        ax.plot([ks], [np.polyval(coef, ks)], "*", ms=17, color=c,
                mec="white", mew=1.0, zorder=7)
        ax.axvline(ks, lw=1.0, ls=(0, (5, 4)), color=c, alpha=0.65, zorder=2)

        depth = r[m].max() - r[m].min()
        ax.annotate(f"{site}   $K_d^{{*}}$ = {ks:.2f}\n"
                    f"best misfit {r[m].min():.2f} K\n"
                    f"bowl only {depth*1000:.0f} mK deep",
                    xy=(ks, np.polyval(coef, ks)),
                    xytext=(ks + (-2.05 if site == "A15" else 0.55),
                            r[m].min() + (0.20 if site == "A15" else 0.24)),
                    fontsize=8.5, color=c, linespacing=1.45, fontweight="bold",
                    arrowprops=dict(arrowstyle="->", color=c, lw=1.0), zorder=8)

    ax.set_xlim(3.0, 9.6)
    ax.set_ylim(0.34, 1.32)
    fmt_axis(ax, xlabel="trial $K_d$  (mW m$^{-1}$K$^{-1}$)",
             ylabel="RMSE against the Apollo sensors  (K)",
             title="Both sweeps: different minima, and different depths")
    ax.grid(True, lw=0.5, color=C_GRID)

    h = [plt.Line2D([], [], color=C_DIM, marker=".", ls="-", alpha=0.7),
         plt.Line2D([], [], color=C_CHAR, lw=2.6),
         plt.Line2D([], [], color=C_CHAR, marker="*", ls="none", ms=13)]
    ax.legend(h, ["swept grid (one full solve per point)",
                  "parabola through the 3 bracketing points",
                  "vertex $\\to K_d^{*}$"],
              frameon=True, edgecolor=C_GRID, fontsize=8, loc="upper center")

    fig.tight_layout()
    FIGS.mkdir(parents=True, exist_ok=True)
    fig.savefig(FIGS / "fig_sweep_both.pdf")
    if DECK.exists():
        fig.savefig(DECK / "sweep_both.png", dpi=200, facecolor="white")
    plt.close(fig)
    print(f"  -> {(FIGS / 'fig_sweep_both.pdf').resolve()}")
    print(f"  -> {(DECK / 'sweep_both.png').resolve()}")


if __name__ == "__main__":
    main()
