#!/usr/bin/env python3
"""Five decades of meter-scale lunar regolith conductivity estimates,
keyed by DEFINITION CLASS (audit 2026-07-13, codex F1).

Two families must not be conflated:
  * FILLED markers -- Hayne-form deep CONTACT asymptote K_d (a model
    parameter): Hayne et al. (2017) global 3.4; this work's per-site
    K_d* (from results/kd_retrieval_results.json, never hardcoded).
  * OPEN markers -- TOTAL (effective) conductivity at measurement
    conditions: Apollo-soil laboratory range 0.7--2 (Cremers 1971;
    Hemingway 1973; Horai 1981); the ORIGINAL in-situ HFE reductions,
    10 +/-10% (A15) and 15 +/-10% (A17) mW m-1 K-1 [ALSEP Final
    Technical Report summary table p.5; Langseth et al. 1976 -- NOT the
    1--3 mW range previously drawn here, which mixed definitions]; and
    this work's effective K(T,z) at the retained sensors, computed from
    the model at K_d* (approx. 2.0x the contact asymptote at ~252-257 K).
  * Vasavada et al. (2012) ~7 is a deep parameter of its OWN K(T)
    normalization (chi = 1.48) -- drawn distinct (half-tone) from both.

Dotted ties connect this work's two currencies so the reader sees they
are the same retrieval expressed in the two definitions.

Writes ../figures/fig_prior_estimates.pdf.
Run: python code/pipeline/figures/make_prior_estimates_figure.py
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
                                  C_DIM, C_CHAR, C_GRID, FS_LEGEND, fmt_axis,
                                  legend_below, assert_no_overlap)
from lunar.properties import conductivity_hayne
from lunar.apollo_helpers import extract_sensor_stability

OUT = ROOT / ".." / "figures"

# Original in-situ reductions, TOTAL effective K below ~10 cm
# [ALSEP Final Technical Report, summary table p.5: "Average conductivity
#  below 10 cm, mW/m-K: 10 +/-10% (A15), 15 +/-10% (A17)"; Langseth 1976].
LANGSETH_INSITU = {"A15": (10.0, 1.0), "A17": (15.0, 1.5)}


def main():
    d = json.loads((ROOT / "results" /
                    "kd_retrieval_results.json").read_text())
    pts, keff = {}, {}
    for site, mission in (("A15", "a15"), ("A17", "a17")):
        star = d[site]["kd_star"] * 1e3
        sm = np.array(d[site]["bootstrap"]["samples"]) * 1e3
        p16, p50, p84 = np.percentile(sm, [15.865, 50, 84.135])
        pts[site] = (star, p50 - p16, p84 - p50)
        # effective K(T,z) at the retained sensors, evaluated at K_d*
        obs = extract_sensor_stability(mission, min_depth_cm=80)
        deep = np.asarray(obs["deep_mask"], dtype=bool)
        z = np.asarray(obs["depth_cm_all"])[deep] / 100.0
        T = np.asarray(obs["T_eq_all"])[deep]
        keff[site] = 1e3 * float(np.mean(
            conductivity_hayne(T, z, Kd=d[site]["kd_star"])))

    fig, ax = plt.subplots(figsize=(JGR_HALF, 3.6), constrained_layout=True)

    # --- effective/total-K family (open) -----------------------------------
    h_lab, = ax.plot([1971, 1971], [0.7, 2.0], color=C_PLUM, lw=5, alpha=0.6,
                     solid_capstyle="butt")
    ax.annotate("laboratory,\nApollo soils", (1971, 2.0), (1966.5, 3.4),
                fontsize=7, color=C_PLUM, ha="left",
                arrowprops=dict(arrowstyle="-", color=C_PLUM, lw=0.7))
    for site, col, dx in (("A15", C_A15, -0.6), ("A17", C_A17, 0.6)):
        v, e = LANGSETH_INSITU[site]
        ax.errorbar(1976 + dx, v, yerr=e, fmt="o", ms=7, mfc="white",
                    color=col, mec=col, mew=1.4, elinewidth=1.1, capsize=2.5,
                    zorder=4)
    ax.annotate("in situ, total $K$\n(original HFE reductions)",
                (1976.8, 15.0), (1981.5, 16.1), fontsize=7, color=C_CHAR,
                ha="left",
                arrowprops=dict(arrowstyle="-", color=C_DIM, lw=0.7))

    # --- contact-asymptote family (filled) ---------------------------------
    ax.plot(2017, 3.4, "s", color=C_HAYNE, ms=6, mec="white", mew=0.7,
            zorder=4)
    ax.annotate("global Diviner fit\n(the $K_d$ both sites reject)",
                (2017, 3.4), (2001.5, 1.0), fontsize=7, color=C_HAYNE,
                ha="left",
                arrowprops=dict(arrowstyle="-", color=C_HAYNE, lw=0.7))
    # Vasavada 2012: deep parameter of its OWN K(T) normalization
    ax.plot(2012, 7.0, "D", color=C_PLUM, ms=5.5, mec="white", mew=0.7,
            alpha=0.8, zorder=4)
    ax.annotate("orbital estimate\n(own $K(T)$ form)", (2012, 7.0),
                (1999.5, 8.3), fontsize=7, color=C_PLUM, ha="left",
                arrowprops=dict(arrowstyle="-", color=C_PLUM, lw=0.7))

    # --- this work: both currencies, tied ----------------------------------
    for site, col, dx in (("A15", C_A15, -0.7), ("A17", C_A17, 0.7)):
        star, lo, hi = pts[site]
        x = 2026 + dx
        ax.errorbar(x, star, yerr=[[lo], [hi]], fmt="*", ms=13, color=col,
                    mec="white", mew=0.8, elinewidth=1.3, capsize=3, zorder=5)
        ax.plot(x, keff[site], "*", ms=11, mfc="white", mec=col, mew=1.5,
                zorder=5)
        ax.plot([x, x], [star, keff[site]], ":", color=col, lw=1.0, zorder=3)
    ax.annotate("this work:\neffective $K$ at sensors",
                (2025.3, keff["A15"]), (2013.5, 12.1), fontsize=7,
                color=C_CHAR, ha="left",
                arrowprops=dict(arrowstyle="-", color=C_DIM, lw=0.7))
    ax.annotate("this work:\ncontact asymptote $K_d^{*}$",
                (2025.3, pts["A15"][0]), (2017.2, 2.2), fontsize=7,
                color=C_CHAR, ha="left",
                arrowprops=dict(arrowstyle="-", color=C_DIM, lw=0.7))

    # shared legend for the definition-class code
    from matplotlib.lines import Line2D
    handles = [
        Line2D([], [], marker="o", ls="none", mfc="white", mec=C_CHAR,
               mew=1.3, ms=7, label="total / effective $K$"),
        Line2D([], [], marker="s", ls="none", color=C_CHAR, ms=6,
               label="contact asymptote $K_d$"),
    ]
    fmt_axis(ax, xlabel="year",
             ylabel=r"conductivity  (mW m$^{-1}$ K$^{-1}$)",
             title="Five decades of meter-scale conductivity estimates")
    ax.set_xlim(1965, 2032)
    ax.set_ylim(0, 18)

    # small 2-entry key in the empty central pocket (below the top-left
    # "in situ" annotation, above the orbital-estimate label, and left of
    # the this-work markers) -- verified clear of both data and text
    ax.legend(handles, [h.get_label() for h in handles], ncol=1,
              loc="center", bbox_to_anchor=(0.43, 0.66),
              frameon=True, edgecolor=C_GRID, framealpha=0.95,
              fontsize=FS_LEGEND, handletextpad=0.5, borderpad=0.5,
              labelspacing=0.4)

    fig.canvas.draw()
    assert_no_overlap(ax)
    OUT.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT / "fig_prior_estimates.pdf", bbox_inches="tight")
    plt.close(fig)
    print(f"  -> fig_prior_estimates.pdf  (K_eff = "
          f"{keff['A15']:.1f}/{keff['A17']:.1f} mW/m/K)")


if __name__ == "__main__":
    main()
