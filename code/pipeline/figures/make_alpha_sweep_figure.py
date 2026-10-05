#!/usr/bin/env python3
"""Make the Martinez per-site density-scalar (alpha) sweep figure.

Two panels (A15, A17): RMSE vs alpha curve from the per-site Martinez
retrieval, with the physically admissible Apollo-core density band
shaded, the published Martinez baseline (alpha=1) marked, and the
retrieved alpha* highlighted. Reads results/headline_rmse.json.

Writes results/figures/fig_alpha_sweep.pdf.
"""
from __future__ import annotations
import json, pathlib
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

# House style (rcParams, fonts, palette) and the letter's colour roles:
# sites green / coral, Martinez violet dotted, bounds neutral grey.
from lunar.plotting.style import (JGR_FULL, C_A15, C_A17, C_CHAR, C_DIM, C_GRID,
                                  C_MS, LS_MS, FS_LABEL, FS_TICK, legend_below)
C_BASE = C_MS          # published Martinez baseline (alpha = 1)

ROOT = pathlib.Path(__file__).resolve().parents[2]
OUT  = ROOT / ".." / "figures"

# Apollo-core admissible deep bulk density envelope (Mitchell 1973;
# Carrier 1991). 1700-2000 kg/m^3 maps to alpha = [1700/1800, 2000/1800].
RHO_LO = 1700.0
RHO_HI = 2000.0
ALPHA_LO = RHO_LO / 1800.0   # 0.944
ALPHA_HI = RHO_HI / 1800.0   # 1.111
ALPHA_BASALT = 3000.0 / 1800.0   # solid lunar basalt absolute upper bound


def main(out_name="fig_alpha_sweep.pdf"):
    data = json.loads((ROOT / "results" / "headline_rmse.json").read_text())

    # Single-panel overlay -- both sites on shared axes so the
    # contrast between the two minima is immediate visually.
    fig, ax = plt.subplots(figsize=(JGR_FULL, 4.0))
    fig.subplots_adjust(left=0.10, right=0.985, top=0.96, bottom=0.14)

    # Apollo-core admissible density envelope: two narrow vertical
    # boundary lines + short tick caps on the X-AXIS itself, in a
    # neutral warm grey (green is the Apollo 15 colour). No shading.
    C_BOUND = "#8C857D"
    for x_b in (ALPHA_LO, ALPHA_HI):
        ax.axvline(x_b, color=C_BOUND, ls="-", lw=1.0,
                   alpha=0.65, zorder=1)
        # tiny ticks on the x-axis at the bounds, marker style
        ax.plot([x_b], [0], marker="^", color=C_BOUND,
                ms=7, mec="white", mew=0.6, zorder=4,
                transform=ax.get_xaxis_transform(), clip_on=False)

    # Solid-basalt absolute upper bound (very subtle dotted grey vert)
    ax.axvline(ALPHA_BASALT, color=C_DIM, ls=(0, (1, 2)),
               lw=1.0, alpha=0.55, zorder=1)

    # Published Martinez baseline (alpha = 1)
    ax.axvline(1.0, color=C_BASE, ls=LS_MS, lw=1.4, zorder=2)

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
            label=rf"Apollo {name[-2:]}: $\alpha^{{*}}={alpha_star:.2f}$")
        ax.plot(alpha_star, rmse_star, "*", ms=22, color=color,
                mec="white", mew=1.5, zorder=5)
        site_handles.append(line)

    # Axis cosmetics
    ax.set_xlabel(r"Density scalar $\alpha$  "
                  r"($\rho_d=\alpha\cdot 1800$ kg m$^{-3}$)",
                  fontsize=FS_LABEL)
    ax.set_ylabel(r"Meter-scale-sensor RMSE  (K)", fontsize=FS_LABEL)
    # Trim to the populated range: both retrieved minima now sit near
    # alpha ~ 1 and the solid-basalt reference (1.67) bounds the right;
    # the legacy 2.2 limit (sized for the superseded A17 minimum at
    # 1.83) left half the axis empty.
    ax.set_xlim(0.68, 1.85)
    ax.tick_params(labelsize=FS_TICK)
    ax.grid(color=C_GRID, lw=0.4, alpha=0.7)
    ax.set_axisbelow(True)

    # one shared legend below the panel, the house (Fig. 2) style
    band_handle = Line2D([0], [0], color=C_BOUND, ls="-", lw=1.0,
                         marker="^", ms=7, mec="white", mew=0.6)
    base_handle = Line2D([0], [0], color=C_BASE, ls=LS_MS, lw=1.4)
    basalt_handle = Line2D([0], [0], color=C_DIM, ls=(0, (1, 2)), lw=1.0)
    star_handle = Line2D([0], [0], marker="*", color="white", lw=0,
                         ms=12, mec=C_CHAR, mew=0.8)
    legend_below(fig, site_handles + [star_handle, band_handle, base_handle, basalt_handle],
                 [h.get_label() for h in site_handles]
                 + [r"retrieved $\alpha^{*}$", r"Apollo-core $\rho_d$ range",
                    r"published Martínez ($\alpha=1$)", r"solid basalt"])

    out = OUT / out_name
    fig.savefig(out)
    plt.close(fig)
    print(f"  -> {out}")


if __name__ == "__main__":
    main()
