#!/usr/bin/env python3
r"""Five decades of meter-scale lunar regolith conductivity estimates, keyed
by DEFINITION CLASS. Every literature value below was read from the actual
paper (PDFs in code/references/); this work's values come from the code.

Two families must not be conflated:
  * FILLED markers -- Hayne-form deep CONTACT asymptote K_d (a model
    parameter): Hayne et al. (2017) global 3.4 [verified, their abstract +
    Eq., K_d = 3.4e-3 W/m/K]; Feng et al. (2020) global 3.8 [verified,
    "kd = 3.8e-3 W/m/K"]; this work's per-site K_d* (from
    results/kd_retrieval_results.json, never hardcoded).
  * OPEN markers -- TOTAL (effective) conductivity at measurement
    conditions: Cremers & Birkebak (1971) Apollo 12 laboratory fines,
    1.2-3.5 mW/m/K over 160-428 K at rho=1300 [verified, their abstract];
    the revised in-situ HFE reductions of Langseth et al. (1976), ~10 (A15)
    and ~13 (A17) mW/m/K [verified from their Fig. 6 / Table 1 annual-wave
    diffusivities x c_p(Hemingway 1973) x rho(Carrier 1974)]; and this work's
    effective K(T,z) at the retained sensors, evaluated at K_d* (~2x the
    contact asymptote at ~252-257 K).

Dotted ties connect this work's two currencies so the reader sees they are
the same retrieval expressed in the two definitions. (The Vasavada 2012 "~7"
point was removed: it could not be verified from the paper.)

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
                                  assert_no_overlap)
from lunar.properties import conductivity_hayne
from lunar.apollo_helpers import extract_sensor_stability

OUT = ROOT / ".." / "figures"

# Revised in-situ reductions, TOTAL effective K = kappa*rho*c_p from Langseth
# et al. (1976) Table 1 annual-wave diffusivities (A15 0.74-0.87, A17
# 0.88-1.00 e-4 cm^2/s) x c_p 0.67 (Hemingway 1973) x rho (Carrier 1974):
# A15 8.7-11.1 -> 10.0 +/- 1.2; A17 10.8-14.0 -> 12.4 +/- 1.6 mW/m/K.
LANGSETH_INSITU = {"A15": (10.0, 1.2), "A17": (12.4, 1.6)}
# Cremers & Birkebak (1971) Apollo 12 lab fines, verified from the abstract.
CREMERS_LAB = (1.2, 3.5)
HAYNE_GLOBAL = 3.4        # Hayne et al. (2017), verified
FENG_GLOBAL = 3.8         # Feng et al. (2020), verified


def main():
    d = json.loads((ROOT / "results" /
                    "kd_retrieval_results.json").read_text())
    pts, keff, keff_ci = {}, {}, {}
    for site, mission in (("A15", "a15"), ("A17", "a17")):
        star = d[site]["kd_star"] * 1e3
        sm = np.array(d[site]["bootstrap"]["samples"]) * 1e3
        p16, p50, p84 = np.percentile(sm, [15.865, 50, 84.135])
        pts[site] = (star, p50 - p16, p84 - p50)
        obs = extract_sensor_stability(mission, min_depth_cm=80)
        deep = np.asarray(obs["deep_mask"], dtype=bool)
        z = np.asarray(obs["depth_cm_all"])[deep] / 100.0
        T = np.asarray(obs["T_eq_all"])[deep]
        keff[site] = 1e3 * float(np.mean(
            conductivity_hayne(T, z, Kd=d[site]["kd_star"])))
        # 1-sigma bootstrap on the effective K: propagate the K_d samples
        kb = np.array(d[site]["bootstrap"]["samples"])
        eb = np.array([1e3 * float(np.mean(conductivity_hayne(T, z, Kd=ks)))
                       for ks in kb])
        e16, e50, e84 = np.percentile(eb, [15.865, 50, 84.135])
        keff_ci[site] = (e50 - e16, e84 - e50)

    fig, ax = plt.subplots(figsize=(JGR_HALF, 3.6), constrained_layout=True)

    # --- total/effective-K family (open) -----------------------------------
    ax.plot([1971, 1971], list(CREMERS_LAB), color=C_PLUM, lw=5, alpha=0.6,
            solid_capstyle="butt", zorder=3)
    ax.annotate("laboratory,\nApollo 12 fines", (1971, CREMERS_LAB[1]),
                (1966.3, 5.2), fontsize=7, color=C_PLUM, ha="left",
                arrowprops=dict(arrowstyle="-", color=C_PLUM, lw=0.7))
    for site, col, dx in (("A15", C_A15, -0.6), ("A17", C_A17, 0.6)):
        v, e = LANGSETH_INSITU[site]
        ax.errorbar(1976 + dx, v, yerr=e, fmt="o", ms=7, mfc="white",
                    color=col, mec=col, mew=1.4, elinewidth=1.1, capsize=2.5,
                    zorder=4)
    ax.annotate("in situ, total $K$\n(Langseth 1976)",
                (1976.8, 13.0), (1980.5, 14.6), fontsize=7, color=C_CHAR,
                ha="left", arrowprops=dict(arrowstyle="-", color=C_DIM, lw=0.7))

    # --- contact-asymptote family (filled): Hayne + Feng global fits -------
    ax.plot(2017, HAYNE_GLOBAL, "s", color=C_HAYNE, ms=6, mec="white",
            mew=0.7, zorder=4)
    ax.plot(2020, FENG_GLOBAL, "D", color=C_HAYNE, ms=5.5, mec="white",
            mew=0.7, zorder=4)
    ax.annotate("global Diviner fits\n(Hayne 3.4; Feng 3.8)",
                (2018.5, 3.6), (2003.0, 1.0), fontsize=7, color=C_HAYNE,
                ha="left", arrowprops=dict(arrowstyle="-", color=C_HAYNE,
                                           lw=0.7))

    # --- this work: both currencies, tied ----------------------------------
    # Two DISTINCT quantities per site (not an error range): the contact
    # asymptote K_d* (filled) and the effective K at the sensors (open) --
    # the same retrieval in two definitions, ~2x apart via the radiative
    # term. Each carries its own small 1-sigma bootstrap error bar.
    for site, col, dx in (("A15", C_A15, -0.7), ("A17", C_A17, 0.7)):
        star, lo, hi = pts[site]
        elo, ehi = keff_ci[site]
        x = 2026 + dx
        ax.errorbar(x, star, yerr=[[lo], [hi]], fmt="*", ms=13, color=col,
                    mec="white", mew=0.8, elinewidth=1.3, capsize=3, zorder=5)
        ax.errorbar(x, keff[site], yerr=[[elo], [ehi]], fmt="*", ms=11,
                    mfc="white", mec=col, color=col, mew=1.5, elinewidth=1.1,
                    capsize=2.5, zorder=5)
    ax.text(2020.5, 11.9, "this work", ha="center", va="center",
            fontsize=7.5, color=C_CHAR, fontweight="bold", zorder=5)
    # name the two currencies next to their star pairs
    ax.text(2028.2, 12.0, r"$K_\mathrm{eff}$", ha="left", va="center",
            fontsize=8.5, color=C_CHAR, zorder=6)
    ax.text(2028.2, 5.85, r"$K_d^{*}$", ha="left", va="center",
            fontsize=8.5, color=C_CHAR, zorder=6)
    # callout box: point out WHY this work has two stars per site
    ax.text(1983.5, 8.7,
            r"$K_\mathrm{eff}$ (open) $\approx 2\,K_d$ (filled)" + "\n"
            "for the same retrieval:\n"
            r"the radiative term is in $K_\mathrm{eff}$," + "\n"
            r"not in the contact $K_d$",
            fontsize=6.3, color=C_CHAR, ha="left", va="center",
            bbox=dict(boxstyle="round,pad=0.4", facecolor="white",
                      edgecolor=C_GRID, alpha=0.96), zorder=7)

    from matplotlib.lines import Line2D
    handles = [
        Line2D([], [], marker="o", ls="none", mfc="white", mec=C_CHAR,
               mew=1.3, ms=7, label=r"open $K_\mathrm{eff}$: effective $K$"),
        Line2D([], [], marker="s", ls="none", color=C_CHAR, ms=6,
               label=r"filled $K_d$: contact"),
    ]
    fmt_axis(ax, xlabel="year",
             ylabel=r"conductivity  (mW m$^{-1}$ K$^{-1}$)",
             title="Five decades of meter-scale conductivity estimates")
    ax.set_xlim(1965, 2034)
    ax.set_ylim(0, 16)

    ax.legend(handles, [h.get_label() for h in handles], ncol=1,
              loc="center", bbox_to_anchor=(0.60, 0.80),
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
