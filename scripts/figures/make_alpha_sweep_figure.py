#!/usr/bin/env python3
"""Make the Martinez per-site density-scalar (alpha) sweep figure.

Two panels (A15, A17): RMSE vs alpha curve from the per-site Martinez
retrieval, with the physically admissible Apollo-core density band
shaded, the published Martinez baseline (alpha=1) marked, and the
retrieved alpha* highlighted. Reads output/headline_rmse.json.

Writes paper/letter/figures/fig_alpha_sweep.pdf.
"""
from __future__ import annotations
import json, pathlib
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

# Shared design tokens (match make_letter_figures.py)
JGR_FULL = 7.48
C_A15   = "#3D6E4A"   # forest
C_A17   = "#B85B3A"   # coral
C_CHAR  = "#2A2520"
C_DIM   = "#6E6862"
C_GRID  = "#E8E5E0"
C_PAPER = "#FBFAF8"
C_BAND  = "#D6E2D9"   # pale green for admissible Apollo-core band
C_BASE  = "#2A6478"   # teal for Martinez baseline (alpha=1)
FS_LABEL = 10.5
FS_TICK  = 9.5
FS_TITLE = 11.0

plt.rcParams.update({
    "font.family": "serif",
    "font.serif": ["Latin Modern Roman", "Times New Roman", "DejaVu Serif"],
    "mathtext.fontset": "cm",
    "axes.edgecolor": C_DIM,
    "axes.labelcolor": C_CHAR,
    "text.color": C_CHAR,
    "xtick.color": C_CHAR,
    "ytick.color": C_CHAR,
    "axes.linewidth": 0.8,
})

ROOT = pathlib.Path(__file__).resolve().parents[2]
OUT  = ROOT / "paper" / "letter" / "figures"

# Apollo-core admissible deep bulk density envelope (Mitchell 1973;
# Carrier 1991). 1700-2000 kg/m^3 maps to alpha = [1700/1800, 2000/1800].
RHO_LO = 1700.0
RHO_HI = 2000.0
ALPHA_LO = RHO_LO / 1800.0   # 0.944
ALPHA_HI = RHO_HI / 1800.0   # 1.111
ALPHA_BASALT = 3000.0 / 1800.0   # solid lunar basalt absolute upper bound


def main():
    data = json.loads((ROOT / "output" / "headline_rmse.json").read_text())

    # Single-panel overlay -- both sites on shared axes so the
    # contrast between the two minima is immediate visually.
    fig, ax = plt.subplots(figsize=(JGR_FULL, 5.2))
    fig.subplots_adjust(left=0.10, right=0.985, top=0.94, bottom=0.32)
    ax.set_facecolor(C_PAPER)

    # Apollo-core admissible density envelope: two narrow vertical
    # boundary lines + short tick caps on the X-AXIS itself, in a
    # neutral dark green. No shading, no integral interpretation.
    C_GREEN = "#3D6E4A"
    for x_b in (ALPHA_LO, ALPHA_HI):
        ax.axvline(x_b, color=C_GREEN, ls="-", lw=1.0,
                   alpha=0.65, zorder=1)
        # tiny ticks on the x-axis at the bounds, marker style
        ax.plot([x_b], [0], marker="^", color=C_GREEN,
                ms=7, mec="white", mew=0.6, zorder=4,
                transform=ax.get_xaxis_transform(), clip_on=False)

    # Solid-basalt absolute upper bound (very subtle dotted grey vert)
    ax.axvline(ALPHA_BASALT, color=C_DIM, ls=(0, (1, 2)),
               lw=1.0, alpha=0.55, zorder=1)

    # Published Martinez baseline (alpha = 1)
    ax.axvline(1.0, color=C_BASE, ls="--", lw=1.0, alpha=0.55,
               zorder=2)

    # Site curves with star at the minimum.
    site_handles = []
    for name, color in [("A15", C_A15), ("A17", C_A17)]:
        s = data["sites"][name]["martinez_site_fit"]
        alpha = np.array(s["alpha_grid"])
        rmse = np.array(s["rmse_curve"])
        alpha_star = s["alpha"]
        rmse_star = s["rmse_K"]
        rho_d_star = s["rho_d_kg_m3"]

        (line,) = ax.plot(
            alpha, rmse, "-", color=color, lw=2.4, zorder=3,
            label=(rf"A{name[-2:]}  $\alpha^{{*}}={alpha_star:.2f}$,  "
                   rf"$\rho_d^{{*}}={rho_d_star:.0f}$ kg m$^{{-3}}$"))
        ax.plot(alpha_star, rmse_star, "*", ms=22, color=color,
                mec="white", mew=1.5, zorder=5)
        site_handles.append(line)

    # Axis cosmetics
    ax.set_xlabel(r"Density scalar $\alpha$  "
                  r"($\rho_d=\alpha\cdot 1800$ kg m$^{-3}$)",
                  fontsize=FS_LABEL)
    ax.set_ylabel(r"Deep-sensor RMSE  (K)", fontsize=FS_LABEL)
    ax.set_xlim(0.68, 2.22)
    ax.tick_params(labelsize=FS_TICK)
    ax.grid(color=C_GRID, lw=0.4, alpha=0.7)
    ax.set_axisbelow(True)

    # Single shared legend below, in the Fig 6 style: a title line
    # over two rows of entries.
    band_handle = Line2D([0], [0], color="#3D6E4A", ls="-", lw=1.0,
                         marker="^", ms=8, mec="white", mew=0.6,
                         label="Apollo-core admissible $\\rho_d$ "
                               "(1700--2000 kg m$^{-3}$)")
    base_handle = Line2D([0], [0], color=C_BASE, ls="--", lw=1.2,
                         label="Martínez baseline " r"($\alpha=1$)")
    basalt_handle = Line2D([0], [0], color=C_DIM, ls=(0, (1, 2)),
                           lw=1.0,
                           label="Solid lunar basalt (3000 kg m$^{-3}$)")
    star_handle = Line2D([0], [0], marker="*", color="white", lw=0,
                         ms=14, mec=C_CHAR, mew=0.8,
                         label=r"Per-site retrieved $\alpha^{*}$")
    fig.legend(
        handles=site_handles + [band_handle, base_handle,
                                basalt_handle, star_handle],
        loc="lower center", bbox_to_anchor=(0.5, 0.012),
        ncols=2, frameon=True, edgecolor=C_GRID, framealpha=0.97,
        fontsize=FS_TICK, handlelength=2.2, borderpad=0.7,
        columnspacing=1.8,
        title=r"Stars: retrieved $\alpha^{*}$;  green verticals + triangles: "
              r"Apollo-core admissible $\rho_d$ bounds",
        title_fontsize=FS_LABEL,
    )

    out = OUT / "fig_alpha_sweep.pdf"
    fig.savefig(out)
    plt.close(fig)
    print(f"  -> {out}")


if __name__ == "__main__":
    main()
