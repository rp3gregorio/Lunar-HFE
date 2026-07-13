#!/usr/bin/env python3
"""Teaching figure: the K_d--Q_b degeneracy, measured (audit F-9).

Two panels from results/qb_degeneracy.json (one direct re-retrieval per
point; no proportional-degeneracy assumption):
  (a) K_d*(Q_b) per site -- the two sites' OPPOSITE responses, with the
      published fluxes marked and the disproved proportional rule shown
      as a ghost line for contrast;
  (b) the fit quality min-RMSE(Q_b) -- showing that RMSE alone cannot
      arbitrate the basal-flux debate (both sites fit BETTER at fluxes
      below the published values).

Writes docs/guidebook/figures/fig_qb_degeneracy.pdf.
Run: python pipeline/figures/make_qb_degeneracy_figure.py
"""
from __future__ import annotations

import json
import pathlib
import sys

import numpy as np
import matplotlib.pyplot as plt

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from lunar.plotting.style import (JGR_FULL, C_A15, C_A17, C_DIM, C_GRID,
                                  C_CHAR, fmt_axis, assert_no_overlap)

SRC = ROOT / "results" / "qb_degeneracy.json"
OUT = ROOT / ".." / "figures"
PUB = {"A15": 21.0, "A17": 16.0}   # published Q_b [mW m^-2] (Langseth 1976)


def main():
    d = json.loads(SRC.read_text())["sites"]
    from scipy.interpolate import PchipInterpolator

    fig, (axA, axB) = plt.subplots(1, 2, figsize=(JGR_FULL, 3.4),
                                   constrained_layout=True)

    for site, col in (("A15", C_A15), ("A17", C_A17)):
        qb = np.array([r["qb_mW"] for r in d[site]])
        kd = np.array([r["kd_star_mW"] for r in d[site]])
        rm = np.array([r["rmse_min_K"] for r in d[site]])
        qq = np.linspace(qb[0], qb[-1], 200)
        f = PchipInterpolator(qb, kd)

        # (a) the measured curve + points + published marker
        axA.plot(qq, f(qq), color=col, lw=1.6, zorder=3)
        axA.plot(qb, kd, "o", color=col, ms=4.5, mec="white", mew=0.6,
                 zorder=4, label=f"Apollo {site[1:]} (measured)")
        kd_pub = float(f(PUB[site]))
        axA.plot(PUB[site], kd_pub, "*", color=col, ms=15, mec="white",
                 mew=1.0, zorder=5)
        # the disproved proportional rule K_d = K_d(pub) * Qb/Qb_pub,
        # drawn as a ghost through the published point
        axA.plot(qq, kd_pub * qq / PUB[site], ls=":", color=col, lw=1.1,
                 alpha=0.55, zorder=2)

        # (b) fit quality vs Q_b
        axB.plot(qq, PchipInterpolator(qb, rm)(qq), color=col, lw=1.6,
                 zorder=3)
        axB.plot(qb, rm, "o", color=col, ms=4.5, mec="white", mew=0.6,
                 zorder=4)
        axB.axvline(PUB[site], color=col, ls="--", lw=0.9, alpha=0.6,
                    zorder=2)

    fmt_axis(axA, xlabel=r"assumed basal flux $Q_b$  (mW m$^{-2}$)",
             ylabel=r"retrieved $K_d^{*}$  (mW m$^{-1}$ K$^{-1}$)",
             title="(a)  The degeneracy, measured")
    fmt_axis(axB, xlabel=r"assumed basal flux $Q_b$  (mW m$^{-2}$)",
             ylabel=r"best-fit RMSE  (K)",
             title="(b)  Fit quality cannot pick $Q_b$")
    axB.set_ylim(0.2, 1.5)

    from matplotlib.lines import Line2D
    handles = [
        Line2D([0], [0], color=C_A15, lw=1.6, marker="o", ms=4.5,
               mec="white", label="Apollo 15 (one re-retrieval per point)"),
        Line2D([0], [0], color=C_A17, lw=1.6, marker="o", ms=4.5,
               mec="white", label="Apollo 17"),
        Line2D([0], [0], color=C_CHAR, marker="*", ls="none", ms=13,
               mec="white", label="Langseth (1976) $Q_b$ (21 / 16 mW m$^{-2}$)"),
        Line2D([0], [0], color=C_DIM, ls=":", lw=1.1,
               label="disproved proportional rule "
                     r"$K_d^{*}\!\propto\!Q_b$ (panel a)"),
        Line2D([0], [0], color=C_DIM, ls="--", lw=0.9,
               label="Langseth (1976) $Q_b$ (panel b)"),
    ]
    fig.legend(handles=handles, ncol=3, loc="lower center", frameon=True,
               edgecolor=C_GRID, fontsize=7.2, bbox_to_anchor=(0.5, -0.20))

    fig.canvas.draw()
    for ax in (axA, axB):
        assert_no_overlap(ax)
    OUT.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT / "fig_qb_degeneracy.pdf", bbox_inches="tight")
    plt.close(fig)
    print("  -> fig_qb_degeneracy.pdf")


if __name__ == "__main__":
    main()
