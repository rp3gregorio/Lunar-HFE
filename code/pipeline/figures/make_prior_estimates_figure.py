#!/usr/bin/env python3
"""Five decades of deep/meter-scale lunar regolith K_d estimates.

Context figure for the letter's prior-estimates comparison
(sec:disc-prior). Every plotted value is either quoted in that section
with its citation or read from the pipeline's own artifacts:

  * Apollo-soil laboratory measurements ~0.7--2 mW m-1 K-1
    (Cremers 1971; Hemingway 1973; Horai 1981)
  * original in-situ HFE reductions 1--3 mW m-1 K-1 (Langseth 1976)
  * Keihm (1984) and Grott et al. (2010): upward revisions of the in-situ
    values (direction quoted in the letter; no single number -- drawn as
    annotated arrows, not data points)
  * Vasavada et al. (2012) orbital estimate ~7 mW m-1 K-1
  * Hayne et al. (2017) global Diviner fit K_d = 3.4 mW m-1 K-1
  * this work: per-site K_d* with asymmetric 1-sigma bootstrap errors,
    read from results/kd_retrieval_results.json (never hardcoded).

Writes results/figures/fig_prior_estimates.pdf.
Run: python pipeline/figures/make_prior_estimates_figure.py
"""
from __future__ import annotations

import json
import pathlib
import sys

import numpy as np
import matplotlib.pyplot as plt

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from lunar.plotting.style import (JGR_HALF, C_A15, C_A17, C_HAYNE, C_PLUM,
                                  C_DIM, C_CHAR, C_GRID, fmt_axis,
                                  assert_no_overlap)

OUT = ROOT / ".." / "figures"


def main():
    d = json.loads((ROOT / "results" /
                    "kd_retrieval_results.json").read_text())
    pts = {}
    for site in ("A15", "A17"):
        star = d[site]["kd_star"] * 1e3
        sm = np.array(d[site]["bootstrap"]["samples"]) * 1e3
        p16, p50, p84 = np.percentile(sm, [15.865, 50, 84.135])
        pts[site] = (star, star - (star - (p50 - (p50 - p16))), p84 - p50)
        # asymmetric 1-sigma about the point estimate, bootstrap percentiles
        pts[site] = (star, p50 - p16, p84 - p50)

    fig, ax = plt.subplots(figsize=(JGR_HALF, 3.3), constrained_layout=True)

    # laboratory range (Apollo soils, 1971-1981)
    ax.plot([1971, 1971], [0.7, 2.0], color=C_PLUM, lw=5, alpha=0.75,
            solid_capstyle="butt")
    ax.annotate("laboratory,\nApollo soils", (1971, 2.0), (1966.5, 3.6),
                fontsize=7, color=C_PLUM, ha="left",
                arrowprops=dict(arrowstyle="-", color=C_PLUM, lw=0.7))
    # original in-situ reductions (Langseth 1976)
    ax.plot([1976, 1976], [1.0, 3.0], color=C_DIM, lw=5, alpha=0.85,
            solid_capstyle="butt")
    ax.annotate("in situ, original\nHFE reductions", (1976.3, 1.0),
                (1979.5, 0.55), fontsize=7, color=C_CHAR, ha="left",
                arrowprops=dict(arrowstyle="-", color=C_DIM, lw=0.7))
    # upward-revision reanalyses (direction only; no single value quoted)
    for yr in (1984, 2010):
        ax.annotate("", (yr, 4.4), (yr, 2.6),
                    arrowprops=dict(arrowstyle="-|>", color=C_DIM, lw=1.1))
    ax.text(1997, 4.9, "reanalyses revise upward\n(radiative term, borestem)",
            fontsize=7, color=C_DIM, ha="center")
    # orbital estimates
    ax.plot(2012, 7.0, "o", color=C_PLUM, ms=6, mec="white", mew=0.7)
    ax.annotate("orbital estimate", (2012, 7.0), (2001.5, 7.9), fontsize=7,
                color=C_PLUM, ha="left",
                arrowprops=dict(arrowstyle="-", color=C_PLUM, lw=0.7))
    ax.plot(2017, 3.4, "s", color=C_HAYNE, ms=6, mec="white", mew=0.7)
    ax.annotate("global Diviner fit\n(the value both sites reject)",
                (2017, 3.4), (2002.5, 1.35), fontsize=7, color=C_HAYNE,
                ha="left",
                arrowprops=dict(arrowstyle="-", color=C_HAYNE, lw=0.7))
    # this work
    for site, col, dx in (("A15", C_A15, -0.55), ("A17", C_A17, 0.55)):
        star, lo, hi = pts[site]
        ax.errorbar(2026 + dx, star, yerr=[[lo], [hi]], fmt="*", ms=13,
                    color=col, mec="white", mew=0.8, elinewidth=1.3,
                    capsize=3, zorder=5)
    ax.annotate("this work,\nper site", (2026.5, pts["A17"][0]),
                (2018.5, 9.4), fontsize=7, color=C_CHAR, ha="left",
                arrowprops=dict(arrowstyle="-", color=C_DIM, lw=0.7))

    fmt_axis(ax, xlabel="year", ylabel=r"$K_d$  (mW m$^{-1}$ K$^{-1}$)",
             title="Five decades of meter-scale $K_d$ estimates")
    ax.set_xlim(1965, 2032)
    ax.set_ylim(0, 11)

    fig.canvas.draw()
    assert_no_overlap(ax)
    OUT.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT / "fig_prior_estimates.pdf", bbox_inches="tight")
    plt.close(fig)
    print("  -> fig_prior_estimates.pdf")


if __name__ == "__main__":
    main()
