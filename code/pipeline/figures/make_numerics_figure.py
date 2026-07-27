#!/usr/bin/env python3
"""Numerical-method figure for the thesis methods chapter.

Three panels:
 (a) the REAL geometric grid (lunar.grid.make_geometric_grid(**GRID)):
     cell width vs cell-center depth on log-log axes, with the sensor
     band and the anchor marked -- millimeter cells where the diurnal
     wave lives, decimeter cells in the smooth deep column;
 (b) the finite-volume stencil: three adjacent cells, temperatures at
     centers, harmonic-mean conductivities at faces;
 (c) the tridiagonal system one Crank-Nicolson step assembles: interior
     three-point rows, a Dirichlet ghost row at the surface (Newton
     T_s) and a Neumann ghost row at the base (Q_b), solved by the
     Thomas algorithm in O(N).

Grid numbers come from lunar.config/lunar.grid at run time; nothing is
hardcoded.

Output: figures/fig_numerics_grid_matrix.pdf
Run:    python code/pipeline/figures/make_numerics_figure.py
"""
from __future__ import annotations
import pathlib
import sys

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, Rectangle

_REPO = pathlib.Path(__file__).resolve().parents[1].parent
sys.path.insert(0, str(_REPO / "src"))

from lunar.config import GRID, EQ_Z_ANCHOR
from lunar.grid import make_geometric_grid
from lunar.plotting.style import (JGR_FULL, C_CHAR, C_DIM, C_GRID, C_TEAL,
                                  C_CORAL, C_FOREST, C_CORAL_L, fmt_axis,
                                  assert_no_overlap)

OUT = _REPO / ".." / "figures"

SAND = "#EFE3D0"


def panel_grid(ax):
    """(a) the real geometric grid: cell width against depth."""
    g = make_geometric_grid(**GRID)
    ax.axvspan(0.80, 2.40, color=C_GRID, alpha=0.35, lw=0)     # sensor band
    ax.loglog(g.z_mid, g.dz * 1e3, "o-", color=C_TEAL, lw=1.6, ms=3.2,
              mec="white", mew=0.5, zorder=3)
    ax.axvline(EQ_Z_ANCHOR, color=C_CHAR, ls=":", lw=1.1, zorder=2)
    # annotations in verified-empty corners
    ax.annotate(f"$\\Delta z_0 = {GRID['dz0']*1e3:.0f}$ mm",
                xy=(g.z_mid[0], g.dz[0] * 1e3),
                xytext=(0.0028, 11.0), fontsize=7.4, color=C_CHAR,
                arrowprops=dict(arrowstyle="-", lw=0.8, color=C_DIM))
    ax.text(0.02, 300,
            f"$\\times{1 + GRID['growth']:.2f}$ per cell\n"
            f"{g.n_layers} cells to {GRID['z_max']:.0f} m",
            fontsize=7.4, color=C_DIM, ha="center", linespacing=1.4)
    ax.text(EQ_Z_ANCHOR * 0.88, 210, "anchor", fontsize=7.0, color=C_CHAR,
            ha="right")
    ax.text(1.38, 1.9, "sensors", fontsize=7.0, color=C_DIM, ha="center")
    ax.set_xlim(7.5e-4, 6.5)
    ax.set_ylim(1.1, 620)
    fmt_axis(ax, xlabel="cell-center depth  (m)",
             ylabel="cell width  (mm)", title="(a)  geometric grid")


def panel_stencil(ax):
    """(b) three finite-volume cells, centers and harmonic faces."""
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 10)
    ax.axis("off")
    ax.set_title("(b)  finite-volume stencil")
    # three cells with geometrically growing widths, sized to fill the
    # panel at the same visual weight as panel (a)'s axes box
    x0, widths = 0.35, [2.45, 3.0, 3.75]
    xs = [x0]
    for w in widths:
        xs.append(xs[-1] + w)
    y0, y1 = 2.3, 8.3
    for i, w in enumerate(widths):
        ax.add_patch(Rectangle((xs[i], y0), w, y1 - y0, facecolor=SAND,
                               edgecolor=C_CHAR, lw=1.1, zorder=2))
        cx = xs[i] + w / 2
        ax.plot([cx], [5.3], "o", color=C_CHAR, ms=5.5, zorder=4)
        ax.text(cx, 4.6, f"$T_{{i{['-1','','+1'][i]}}}$", ha="center",
                va="top", fontsize=8.6, color=C_CHAR, zorder=4)
    # harmonic-mean faces
    for j, xf in enumerate(xs[1:3]):
        ax.plot([xf, xf], [y0, y1], color=C_TEAL, lw=2.4, zorder=3)
        sign = "-" if j == 0 else "+"
        ax.text(xf, 8.85, f"$K_{{i{sign}1/2}}$", ha="center", fontsize=8.6,
                color=C_TEAL, zorder=4)
        arr = FancyArrowPatch((xf - 0.62, 6.4), (xf + 0.62, 6.4),
                              arrowstyle="-|>", mutation_scale=12,
                              color=C_CORAL, lw=1.7, zorder=4)
        ax.add_patch(arr)
    ax.text(5.0, 0.85,
            "temperatures at cell centers; fluxes cross faces\n"
            "at the harmonic-mean conductivity (resistances in series)",
            ha="center", fontsize=7.2, color=C_DIM, linespacing=1.4)


def panel_matrix(ax):
    """(c) the tridiagonal Crank-Nicolson system and its ghost rows."""
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 10)
    ax.axis("off")
    ax.set_title("(c)  one implicit step")
    n = 9                    # sketch size standing in for N = 69
    x0, y1, cell = 0.35, 8.55, 0.70
    for r in range(n):
        for c in range(n):
            if abs(r - c) > 1:
                continue
            if r == 0:
                color, alpha = C_CORAL, (1.0 if c == 0 else 0.35)
            elif r == n - 1:
                color, alpha = C_FOREST, (1.0 if c == n - 1 else 0.55)
            else:
                color, alpha = C_TEAL, (1.0 if r == c else 0.55)
            ax.add_patch(Rectangle((x0 + c * cell, y1 - r * cell),
                                   cell * 0.88, cell * 0.88,
                                   facecolor=color, alpha=alpha,
                                   edgecolor="none", zorder=3))
    xr = x0 + n * cell + 0.45
    ax.text(xr, y1 + 0.3, "surface row:\nDirichlet ghost\n(Newton $T_s$)",
            fontsize=7.2, color=C_CORAL, ha="left", va="center",
            linespacing=1.3)
    ax.text(xr, y1 - (n / 2 - 0.5) * cell,
            "interior rows:\nCN three-point\nstencil",
            fontsize=7.2, color=C_TEAL, ha="left", va="center",
            linespacing=1.3)
    ax.text(xr, y1 - (n - 1) * cell + 0.25,
            "basal row:\nNeumann ghost\n(carries $Q_b$)",
            fontsize=7.2, color=C_FOREST, ha="left", va="center",
            linespacing=1.3)
    ax.text(5.0, 0.85,
            r"$A\,T^{\,n+1} = d$;  Thomas algorithm, $O(N)$ per step",
            fontsize=7.4, color=C_DIM, ha="center")


def main():
    fig, axes = plt.subplots(1, 3, figsize=(JGR_FULL, 2.85),
                             constrained_layout=True)
    panel_grid(axes[0])
    panel_stencil(axes[1])
    panel_matrix(axes[2])
    fig.canvas.draw()
    assert_no_overlap(axes[0])
    OUT.mkdir(parents=True, exist_ok=True)
    out = OUT / "fig_numerics_grid_matrix.pdf"
    fig.savefig(out)
    plt.close(fig)
    print(f"  -> {out.resolve()}")


if __name__ == "__main__":
    main()
