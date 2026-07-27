#!/usr/bin/env python3
"""Boundary-condition schematic: how the Sun drives the top of the column
and the geothermal flux pins the bottom.

Pure schematic (no data axes): the Sun forces the surface energy balance,
whose three fluxes close the nonlinear equation for T_s at every step;
the base carries the Neumann geothermal condition. Values shown are the
certified inputs:
  S0 = 1361 W m^-2            (config / Kopp & Lean 2011)
  A  = 0.131 / 0.137          (config.SITES albedo)
  eps = 0.95                  (config emissivity)
  Q_b = 21 / 16 mW m^-2       (config.SITES, Langseth 1976)
  column depth 5 m            (config.GRID z_max)

Design notes (polish pass 2026-07-23): incident/reflected/absorbed meet at
one surface node so the balance reads as a node diagram; every label sits
in a white rounded box; one arrow style throughout; smooth depth gradient
for the regolith.

Output: figures/fig_boundary_conditions.pdf
Run:    python code/pipeline/figures/make_bc_illustration.py
"""
from __future__ import annotations
import pathlib
import sys

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap
from matplotlib.patches import Circle, Rectangle

_REPO = pathlib.Path(__file__).resolve().parents[1].parent
sys.path.insert(0, str(_REPO / "src"))

from lunar.plotting.style import (JGR_HALF, C_CHAR, C_DIM, C_GRID, C_CORAL,
                                  C_TEAL, C_FOREST, assert_no_overlap)

OUT = _REPO / ".." / "figures"

SAND = "#EFE3D0"        # regolith fill, consistent with the probe figure
SAND_DEEP = "#DECDB2"

# every label sits in the same white rounded box so text stays crisp on
# the gradient and the figure reads as one designed object
LBOX = dict(boxstyle="round,pad=0.32", facecolor="white",
            edgecolor=C_GRID, linewidth=0.8, alpha=0.96)


def main():
    fig, ax = plt.subplots(figsize=(JGR_HALF, 3.9))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 8)
    ax.axis("off")

    ysurf = 4.6
    ybase = 0.9
    # regolith column: smooth depth gradient (loose light surface fining
    # into darker, denser material) + a thin dust band under the surface
    sand_cmap = LinearSegmentedColormap.from_list("sand", [SAND_DEEP, SAND])
    grad = np.linspace(1.0, 0.0, 256).reshape(-1, 1)
    ax.imshow(grad, extent=(0.4, 9.6, ybase, ysurf), aspect="auto",
              cmap=sand_cmap, origin="upper", interpolation="bilinear",
              zorder=1)
    ax.add_patch(Rectangle((0.4, ysurf - 0.28), 9.2, 0.28,
                           facecolor="#F4EBDD", edgecolor="none",
                           alpha=0.8, zorder=1))
    ax.plot([0.4, 9.6], [ysurf, ysurf], color=C_CHAR, lw=2.0, zorder=3)
    ax.text(9.55, ysurf + 0.16, "lunar surface, $z=0$", ha="right",
            fontsize=7.8, color=C_CHAR, zorder=6)
    ax.plot([0.4, 9.6], [ybase, ybase], color=C_CHAR, lw=1.2, zorder=3)
    ax.text(9.55, ybase - 0.22, "base of the model column, $z=5$ m",
            ha="right", va="top", fontsize=7.8, color=C_DIM, zorder=6)

    # --- the Sun: clean disk, eight uniform rays --------------------------
    sx, sy, sr = 1.45, 7.15, 0.40
    ax.add_patch(Circle((sx, sy), sr, facecolor=C_CORAL, edgecolor="none",
                        zorder=4))
    for ang in np.linspace(0, 2 * np.pi, 8, endpoint=False):
        x0 = sx + (sr + 0.13) * np.cos(ang)
        y0 = sy + (sr + 0.13) * np.sin(ang)
        x1 = sx + (sr + 0.38) * np.cos(ang)
        y1 = sy + (sr + 0.38) * np.sin(ang)
        ax.plot([x0, x1], [y0, y1], color=C_CORAL, lw=1.2,
                solid_capstyle="round", zorder=4)
    ax.text(9.5, 7.55,
            r"$F_\odot(t)=\max(0,\ S_0\cos\theta_\odot(t))$," "\n"
            r"$S_0 = 1361$ W m$^{-2}$",
            ha="right", va="center", fontsize=7.6, color=C_DIM,
            linespacing=1.5, bbox=LBOX, zorder=6)

    # one arrow style for the whole figure
    arrow = dict(arrowstyle="-|>", lw=2.0, mutation_scale=14,
                 shrinkA=0, shrinkB=0)

    # --- the surface node: incident, reflected, absorbed meet at P -------
    px = 3.9
    # incident beam, sun -> node
    ax.annotate("", xy=(px, ysurf + 0.02), xytext=(1.95, 6.68),
                arrowprops=dict(color=C_CORAL, **arrow), zorder=5)
    ax.text(0.5, 5.15, r"absorbed" "\n" r"$(1-A)\,F_\odot$",
            fontsize=7.8, color=C_CORAL, ha="left", va="center",
            linespacing=1.4, bbox=LBOX, zorder=6)
    # reflected: away up-right, opposite the incoming beam
    ax.annotate("", xy=(5.0, 6.5), xytext=(px + 0.06, ysurf + 0.04),
                arrowprops=dict(color=C_DIM, **arrow), zorder=5)
    ax.text(5.0, 6.68, r"reflected  $A\,F_\odot$" "\n"
            r"$A = 0.131\,/\,0.137$",
            fontsize=7.8, color=C_DIM, ha="center", va="bottom",
            linespacing=1.4, bbox=LBOX, zorder=6)
    # emitted: everywhere on the surface; drawn right of the node
    ax.annotate("", xy=(6.85, 6.85), xytext=(6.85, ysurf + 0.04),
                arrowprops=dict(color=C_TEAL, **arrow), zorder=5)
    ax.text(7.05, 6.15, r"emitted  $\varepsilon\sigma T_s^{4}$" "\n"
            r"$\varepsilon = 0.95$",
            fontsize=7.8, color=C_TEAL, ha="left", va="center",
            linespacing=1.4, bbox=LBOX, zorder=6)
    # conducted into the ground
    ax.annotate("", xy=(8.55, 3.62), xytext=(8.55, ysurf - 0.04),
                arrowprops=dict(color=C_CHAR, **arrow), zorder=5)
    ax.text(8.75, 4.05, "conducted\n" r"$-K\,\partial_z T$",
            fontsize=7.8, color=C_CHAR, ha="left", va="center",
            linespacing=1.4, bbox=LBOX, zorder=6)

    # --- the balance equation, inside the column where nothing else sits -
    ax.text(5.35, 3.30,
            "surface energy balance\n"
            r"$(1-A)F_\odot - \varepsilon\sigma T_s^{4}"
            r"= -K\,\partial_z T\,|_{z=0}$" "\n"
            "closed for $T_s$ by Newton iteration at every step",
            fontsize=7.8, color=C_CHAR, ha="center", va="center",
            linespacing=1.75,
            bbox=dict(boxstyle="round,pad=0.5", facecolor="white",
                      edgecolor=C_GRID, linewidth=0.8, alpha=0.97),
            zorder=6)

    # --- geothermal flux at the base --------------------------------------
    ax.annotate("", xy=(1.6, 2.25), xytext=(1.6, 0.15),
                arrowprops=dict(color=C_FOREST, **arrow), zorder=5)
    ax.text(1.85, 1.42, "geothermal flux (Neumann)\n"
            r"$K\,\partial_z T\,|_{z=5\,\mathrm{m}} = Q_b"
            r"= 21\,/\,16$ mW m$^{-2}$",
            fontsize=7.8, color=C_FOREST, ha="left", va="center",
            linespacing=1.4, bbox=LBOX, zorder=6)

    fig.subplots_adjust(left=0.005, right=0.995, top=0.99, bottom=0.01)
    fig.canvas.draw()
    assert_no_overlap(ax)
    OUT.mkdir(parents=True, exist_ok=True)
    out = OUT / "fig_boundary_conditions.pdf"
    fig.savefig(out)
    plt.close(fig)
    print(f"  -> {out.resolve()}")


if __name__ == "__main__":
    main()
