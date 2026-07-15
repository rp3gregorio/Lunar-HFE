#!/usr/bin/env python3
r"""Five decades of meter-scale lunar regolith conductivity estimates, split
into the TWO definition classes so they are never conflated on one axis.
Every literature value was read from the actual paper (PDFs in references/);
this work's values come from the code.

  (a) Effective / total K -- what a sensor at depth measures, radiative term
      included (OPEN markers): laboratory Apollo 12 fines, 1.2-3.5 mW/m/K
      [Cremers & Birkebak 1971, abstract]; the revised in-situ HFE reductions
      ~10 (A15) / ~12 (A17) [Langseth et al. 1976, Fig. 6 / Table 1 diffusivity
      x c_p x rho]; this work's effective K at the retained sensors.
  (b) Contact asymptote K_d -- the Hayne-form model parameter (FILLED
      markers): global 3.4 [Hayne 2017] and 3.8 [Feng 2020]; this work's
      per-site K_d*.

The two panels share the year axis. This work appears in both, showing the
same retrieval expressed in each definition (K_eff ~ 2 K_d via the radiative
term). Writes ../figures/fig_prior_estimates.pdf.
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
                                  C_DIM, C_CHAR, FS_LEGEND, fmt_axis,
                                  assert_no_overlap)
from lunar.properties import conductivity_hayne
from lunar.apollo_helpers import extract_sensor_stability

OUT = ROOT / ".." / "figures"

# Verified literature values (see module docstring for sources).
LANGSETH_INSITU = {"A15": (10.0, 1.2), "A17": (12.4, 1.6)}   # Langseth 1976
CREMERS_LAB = (1.2, 3.5)                                      # Cremers 1971
HAYNE_GLOBAL, FENG_GLOBAL = 3.4, 3.8                          # Hayne17 / Feng20
SITES = (("A15", C_A15, -0.7), ("A17", C_A17, 0.7))
UNIT = r"(mW m$^{-1}$ K$^{-1}$)"


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
        kb = np.array(d[site]["bootstrap"]["samples"])
        eb = np.array([1e3 * float(np.mean(conductivity_hayne(T, z, Kd=ks)))
                       for ks in kb])
        e16, e50, e84 = np.percentile(eb, [15.865, 50, 84.135])
        keff_ci[site] = (e50 - e16, e84 - e50)

    fig, (axA, axB) = plt.subplots(
        2, 1, sharex=True, figsize=(JGR_HALF, 5.1),
        gridspec_kw={"height_ratios": [1.6, 1.0], "hspace": 0.42})

    # ===== (a) effective / total K -- OPEN markers =========================
    axA.plot([1971, 1971], list(CREMERS_LAB), color=C_PLUM, lw=5, alpha=0.6,
             solid_capstyle="butt", zorder=3)
    axA.annotate("laboratory\n(Cremers 1971)", (1971, CREMERS_LAB[1]),
                 (1967, 6.6), fontsize=7, color=C_PLUM, ha="left",
                 arrowprops=dict(arrowstyle="-", color=C_PLUM, lw=0.7))
    for site, col, dx in SITES:
        v, e = LANGSETH_INSITU[site]
        axA.errorbar(1976 + dx, v, yerr=e, fmt="o", ms=7, mfc="white",
                     color=col, mec=col, mew=1.4, elinewidth=1.1, capsize=2.5,
                     zorder=4)
    axA.annotate("in situ\n(Langseth 1976)", (1977.4, 12.4), (1982, 15.2),
                 fontsize=7, color=C_CHAR, ha="left",
                 arrowprops=dict(arrowstyle="-", color=C_DIM, lw=0.7))
    for site, col, dx in SITES:
        elo, ehi = keff_ci[site]
        axA.errorbar(2026 + dx, keff[site], yerr=[[elo], [ehi]], fmt="*",
                     ms=12, mfc="white", mec=col, color=col, mew=1.5,
                     elinewidth=1.2, capsize=3, zorder=5)
    axA.annotate("this work", (2025.0, keff["A15"]), (2009, 12.8),
                 fontsize=7.5, color=C_CHAR, ha="left", fontweight="bold",
                 arrowprops=dict(arrowstyle="-", color=C_DIM, lw=0.7))
    axA.set_ylim(0, 17.5)
    axA.set_yticks([0, 5, 10, 15])
    fmt_axis(axA, ylabel=r"$K_\mathrm{eff}$  " + UNIT,
             title=r"(a)  Effective / total $K$  (open $=$ what a sensor measures)")

    # ===== (b) contact asymptote K_d -- FILLED markers =====================
    axB.plot(2017, HAYNE_GLOBAL, "s", color=C_HAYNE, ms=6, mec="white",
             mew=0.7, zorder=4)
    axB.plot(2020, FENG_GLOBAL, "D", color=C_HAYNE, ms=5.5, mec="white",
             mew=0.7, zorder=4)
    axB.annotate("global fits\n(Hayne 3.4; Feng 3.8)", (2018.5, 3.5),
                 (2002, 1.4), fontsize=7, color=C_HAYNE, ha="left", va="bottom",
                 arrowprops=dict(arrowstyle="-", color=C_HAYNE, lw=0.7))
    for site, col, dx in SITES:
        star, lo, hi = pts[site]
        axB.errorbar(2026 + dx, star, yerr=[[lo], [hi]], fmt="*", ms=13,
                     color=col, mec="white", mew=0.8, elinewidth=1.3,
                     capsize=3, zorder=5)
    axB.annotate("this work", (2026.7, pts["A17"][0] + hi), (2015.5, 8.1),
                 fontsize=7.5, color=C_CHAR, ha="left", va="center",
                 fontweight="bold",
                 arrowprops=dict(arrowstyle="-", color=C_DIM, lw=0.7))
    axB.set_ylim(0, 9)
    axB.set_yticks([0, 2, 4, 6, 8])
    axB.set_xlim(1965, 2032)
    fmt_axis(axB, xlabel="year", ylabel=r"$K_d$  " + UNIT,
             title=r"(b)  Contact asymptote $K_d$  (filled $=$ the model parameter)")

    fig.canvas.draw()
    assert_no_overlap(axA)
    assert_no_overlap(axB)
    OUT.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT / "fig_prior_estimates.pdf", bbox_inches="tight")
    plt.close(fig)
    print(f"  -> fig_prior_estimates.pdf  (K_eff = "
          f"{keff['A15']:.1f}/{keff['A17']:.1f} mW/m/K)")


if __name__ == "__main__":
    main()
