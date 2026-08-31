#!/usr/bin/env python3
"""The geometric depth grid, illustrated: 69 cells, 2 mm to 37 cm.

Three panels, because no single view of this grid is honest on its own:

  A  the whole 5 m column on a LINEAR depth axis, every cell face drawn. This is
     the only view in which the coarsening is true to scale -- the deep cells are
     genuinely 37 cm thick and the shallow ones genuinely collapse into a line at
     the top. A log axis would render a geometric grid as a uniform ladder, which
     is the exact opposite of what it is.
  B  a zoom on the top 4 cm, where 12 of the 69 cells live, so the fine end is
     actually visible. Tied to panel A by a callout.
  C  the cell thickness against depth, log-log: the quantitative statement, a
     straight line because the growth is geometric.

WHY THE GRID IS BUILT THIS WAY. Resolution goes where the curvature is. The
~280 K diurnal swing is spent inside the top few centimetres, and the contact
conductivity climbs from K_s to K_d over H = 6 cm, so both need many cells; below
half a metre the profile is a straight line and cells there are nearly free.

Every number is live from lunar.grid.make_geometric_grid(**config.GRID):
    69 cells, dz0 = 2.00 mm, growth 8 % per cell, dz_last = 37.48 cm
    ratio 187x from the thinnest cell to the thickest
    12 cells above 4 cm, 15 above H = 6 cm, 40 above 54 cm

Outputs: figures/fig_grid_illustration.pdf (+ .png at 300 dpi)
Run:     python code/pipeline/figures/make_grid_illustration.py
"""
from __future__ import annotations

import pathlib
import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Polygon, Rectangle

_HERE = pathlib.Path(__file__).resolve().parent
_REPO = _HERE.parents[1]
for _p in (str(_REPO), str(_REPO / "src"), str(_HERE)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from lunar.config import GRID, HAYNE
from lunar.grid import make_geometric_grid
from lunar.plotting.style import C_CHAR, C_CORAL, C_DIM, C_GRID, C_TEAL

from make_surface_balance import (GROUND_DEEP, GROUND_LIT, GROUND_MID, PAPER,
                                 _shade, apply_style, setup_fonts)

FIGS = _REPO.parent / "figures"

W, H = 7.48, 3.70
WARM, COOL, DARK = C_CORAL, C_TEAL, C_CHAR

# ---- x budget (inches) ------------------------------------------------------
A_L, A_R = 0.74, 1.62          # panel A: the whole column, linear depth
B_L, B_R = 2.62, 3.62          # panel B: the top 4 cm, zoomed
C_BOX = [4.62, 0.68, 2.42, 2.30]   # panel C axes: left, bottom, width, height

# ---- y budget (inches) ------------------------------------------------------
A_TOP, A_BOT = 3.06, 0.42
B_TOP, B_BOT = 3.06, 0.42
N_ZOOM = 12                    # cells shown in panel B; Z_ZOOM is
                               # then set to that cell's own face so
                               # the panel cannot end mid-cell

HALO = dict(facecolor=PAPER, edgecolor="none", alpha=0.85, pad=1.2)


def cell_band(ax, x0, x1, y_hi, y_lo, shade):
    ax.add_patch(Rectangle((x0, y_lo), x1 - x0, y_hi - y_lo,
                           facecolor=shade, edgecolor=_shade(C_DIM, 0.15),
                           lw=0.35, zorder=3))


def draw_column(ax, g, y_top, y_bot, x0, x1, z_max, label_every=None,
                unit_on_last=None):
    """Every cell face, on a LINEAR depth axis so the coarsening is to scale."""
    zf = g.z_face[g.z_face <= z_max + 1e-12]
    span = y_top - y_bot

    def ymap(z):
        return y_top - (z / z_max) * span

    for i in range(zf.size - 1):
        t = zf[i] / z_max
        shade = _shade(GROUND_MID, 0.28 - 0.46 * t)
        cell_band(ax, x0, x1, ymap(zf[i]), ymap(zf[i + 1]), shade)
    # the surface line, and the base
    ax.plot([x0, x1], [y_top, y_top], color=DARK, lw=1.6,
            solid_capstyle="butt", zorder=6)
    ax.plot([x0, x0, x1, x1], [y_top, y_bot, y_bot, y_top], color=DARK, lw=0.7,
            zorder=6)
    if label_every:
        for k, z in enumerate(label_every):
            y = ymap(z)
            ax.plot([x0 - 0.05, x0], [y, y], color=C_DIM, lw=0.6, zorder=6)
            lab = "0" if z == 0 else (f"{z*100:.0f}" if z < 1
                                      else f"{z:.0f} m")
            if unit_on_last and k == len(label_every) - 1:
                lab = f"{lab} {unit_on_last}"
            ax.text(x0 - 0.08, y, lab, color=C_DIM, fontsize=7.5, ha="right",
                    va="center")
    return ymap


def main() -> None:
    family, cambria = setup_fonts()
    apply_style(family, cambria)

    g = make_geometric_grid(**GRID)
    dz, zf = g.dz, g.z_face
    n = g.n_layers
    z_max = float(zf[-1])
    Z_ZOOM = float(zf[N_ZOOM])          # flush with a cell face, by construction
    n_zoom = N_ZOOM
    n_H = int((zf[1:] <= HAYNE["H"]).sum())

    fig = plt.figure(figsize=(W, H))
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, W)
    ax.set_ylim(0, H)
    ax.axis("off")

    # ---- A: the whole column ------------------------------------------------
    ymap_a = draw_column(ax, g, A_TOP, A_BOT, A_L, A_R, z_max,
                         label_every=(0.0, 1.0, 2.0, 3.0, 4.0, 5.0))
    ax.text(A_L - 0.08, A_TOP + 0.26, "depth\n(m)", color=C_DIM,
            fontsize=7.5, ha="right", va="center", linespacing=1.2)
    ax.text(0.5 * (A_L + A_R), A_TOP + 0.30, f"all {n} cells",
            color=DARK, fontsize=10.0, ha="center", va="center")
    ax.text(0.5 * (A_L + A_R), A_BOT - 0.16,
            rf"$\Delta z_{{n-1}}={dz[-1]*100:.0f}$ cm",
            color=DARK, fontsize=8.5, ha="center", va="top")

    # the zoom callout: the top 4 cm of A, blown up into B
    y_zoom = float(ymap_a(Z_ZOOM))
    ax.add_patch(Rectangle((A_L, y_zoom), A_R - A_L, A_TOP - y_zoom,
                           facecolor="none", edgecolor=WARM, lw=1.1, zorder=8))
    ax.add_patch(Polygon([(A_R, A_TOP), (A_R, y_zoom), (B_L, B_BOT), (B_L, B_TOP)],
                         closed=True, facecolor=WARM, edgecolor="none",
                         alpha=0.10, zorder=1))
    for ya, yb in ((A_TOP, B_TOP), (y_zoom, B_BOT)):
        ax.plot([A_R, B_L], [ya, yb], color=WARM, lw=0.7, ls=(0, (2.2, 2.0)),
                zorder=8)

    # ---- B: the top 4 cm ----------------------------------------------------
    # the unit rides on the deepest tick: a separate "depth (cm)" header here ran
    # into the panel title, and panel A's metres would otherwise be assumed
    draw_column(ax, g, B_TOP, B_BOT, B_L, B_R, Z_ZOOM,
                label_every=(0.0, 0.01, 0.02, 0.03), unit_on_last="cm")
    ax.text(0.5 * (B_L + B_R), B_TOP + 0.30,
            f"the top {Z_ZOOM*100:.1f} cm: {n_zoom} cells",
            color=WARM, fontsize=10.0, ha="center", va="center")
    ax.text(B_R + 0.07, float(B_TOP - (dz[0] / Z_ZOOM) * (B_TOP - B_BOT) / 2),
            rf"$\Delta z_0={dz[0]*1e3:.0f}$ mm", color=DARK, fontsize=8.5,
            ha="left", va="center")
    ax.plot([B_R, B_R + 0.05],
            [B_TOP, B_TOP], color=C_DIM, lw=0.6, zorder=6)
    ax.plot([B_R, B_R + 0.05],
            [B_TOP - (dz[0] / Z_ZOOM) * (B_TOP - B_BOT)] * 2, color=C_DIM,
            lw=0.6, zorder=6)
    ax.text(0.5 * (B_L + B_R), B_BOT - 0.16,
            rf"{n_H} cells above $H={HAYNE['H']*100:.0f}$ cm",
            color=C_DIM, fontsize=8.0, ha="center", va="top")

    # ---- C: cell thickness vs depth ----------------------------------------
    axc = fig.add_axes([C_BOX[0] / W, C_BOX[1] / H, C_BOX[2] / W, C_BOX[3] / H])
    axc.step(g.z_mid * 100.0, dz * 100.0, where="post", color=COOL, lw=1.8)
    axc.set_xscale("log")
    axc.set_yscale("log")
    axc.set_xlabel("depth (cm)", fontsize=9.0, color=DARK)
    axc.set_ylabel(r"cell thickness $\Delta z$ (cm)", fontsize=9.0, color=DARK)
    axc.tick_params(labelsize=8.0, colors=DARK)
    axc.grid(axis="both", color=C_GRID, lw=0.5)
    axc.set_axisbelow(True)
    for s in ("top", "right"):
        axc.spines[s].set_visible(False)
    for s in ("left", "bottom"):
        axc.spines[s].set_color(DARK)
    axc.text(0.04, 0.95,
             f"{n} cells, {GRID['growth']*100:.0f}% growth per cell\n"
             rf"$\Delta z$: {dz[0]*1e3:.0f} mm $\to$ {dz[-1]*100:.0f} cm"
             f"  ({dz[-1]/dz[0]:.0f}$\\times$)",
             transform=axc.transAxes, fontsize=8.5, color=C_DIM, ha="left",
             va="top", linespacing=1.45)

    fig.canvas.draw()
    FIGS.mkdir(parents=True, exist_ok=True)
    with plt.rc_context({"savefig.pad_inches": 0.02}):
        fig.savefig(FIGS / "fig_grid_illustration.pdf")
        fig.savefig(FIGS / "fig_grid_illustration.png", dpi=300)
    plt.close(fig)
    print(f"  wrote figures/fig_grid_illustration.pdf + .png "
          f"({W:.2f} x {H:.2f} in)")
    print(f"  {n} cells, dz0 {dz[0]*1e3:.2f} mm -> {dz[-1]*100:.2f} cm "
          f"({dz[-1]/dz[0]:.0f}x), z_max {z_max:.4f} m")
    print(f"  {n_zoom} cells in the top {Z_ZOOM*100:.0f} cm, "
          f"{n_H} above H = {HAYNE['H']*100:.0f} cm")


if __name__ == "__main__":
    main()
