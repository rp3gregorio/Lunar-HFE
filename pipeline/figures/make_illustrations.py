#!/usr/bin/env python3
"""Modern schematic *illustrations* for the guidebook (docs/guidebook/).

Clean, flat, vector-style clipart of the physical setup -- not data graphs.
Each writes a PDF into results/figures/.

Run:  python pipeline/figures/make_illustrations.py
"""
from __future__ import annotations
import pathlib
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import (FancyBboxPatch, FancyArrowPatch, Rectangle,
                                Circle, Polygon)

from lunar.plotting.style import (C_CORAL, C_TEAL, C_FOREST, C_CHAR, C_DIM,
                                  C_GRID, JGR_FULL)

OUT = pathlib.Path(__file__).resolve().parents[2] / "results" / "figures"
OUT.mkdir(parents=True, exist_ok=True)

REG = "#ECE2D2"      # regolith fill
REG_D = "#DCCBB2"    # deeper regolith
SKY = "#EAF1F3"      # lunar-day sky (light, modern)


def _rrect(ax, x, y, w, h, fc, ec=C_CHAR, lw=0.9, z=4, r=0.04):
    ax.add_patch(FancyBboxPatch((x, y), w, h,
                 boxstyle=f"round,pad=0,rounding_size={r}",
                 facecolor=fc, edgecolor=ec, lw=lw, zorder=z))


def fig_probe_layout():
    fig, ax = plt.subplots(figsize=(JGR_FULL, 4.7))
    ax.set_xlim(0, 10); ax.set_ylim(0, 7.2); ax.axis("off")

    ys = 4.5                                   # surface height in fig units
    cm = (ys - 0.55) / 155.0                   # fig units per cm of depth
    def dy(d):                                 # y-coord of a given depth (cm)
        return ys - d * cm

    # --- sky + distant massif (Apennine front), flat modern silhouette --------
    ax.add_patch(Rectangle((0, ys), 10, 7.2 - ys, facecolor=SKY, ec="none", zorder=0))
    ax.add_patch(Polygon([(4.7, ys), (6.2, 6.25), (7.4, 5.5), (8.6, 6.4),
                          (10, 5.5), (10, ys)], closed=True,
                         facecolor="#CAD6D4", ec="none", alpha=0.85, zorder=1))
    ax.add_patch(Polygon([(0, ys), (1.2, 5.4), (2.3, 5.0), (3.1, 5.3),
                          (3.8, ys)], closed=True,
                         facecolor="#D5DEDB", ec="none", alpha=0.7, zorder=1))

    # --- regolith body + surface line -----------------------------------------
    ax.add_patch(Rectangle((0, 0), 10, ys, facecolor=REG, ec="none", zorder=1))
    ax.add_patch(Rectangle((0, 0), 10, dy(120), facecolor=REG_D, ec="none",
                           alpha=0.45, zorder=1))
    xs = np.linspace(0, 10, 240)
    ax.plot(xs, ys + 0.045 * np.sin(xs * 1.7) + 0.02 * np.sin(xs * 5.3),
            color=C_CHAR, lw=1.4, zorder=3)

    # --- depth ruler (left margin) --------------------------------------------
    xr = 0.62
    ax.plot([xr, xr], [dy(0), dy(150)], color=C_DIM, lw=1.0, zorder=2)
    for d in (0, 50, 100, 140):
        ax.plot([xr - 0.06, xr + 0.06], [dy(d), dy(d)], color=C_DIM, lw=1.0, zorder=2)
        ax.text(xr - 0.12, dy(d), f"{d}", ha="right", va="center", fontsize=7.5,
                color=C_DIM)
    ax.text(xr - 0.12, dy(150) - 0.18, "cm", ha="right", fontsize=7.5, color=C_DIM)

    pw = 0.24
    def probe(x, total, sensors, borestem=30):
        # epoxy borestem (top, excluded zone) -- coral
        _rrect(ax, x - pw / 2, dy(borestem), pw, dy(0) - dy(borestem), C_CORAL)
        # heat-flow probe body -- teal
        _rrect(ax, x - pw / 2, dy(total), pw, dy(borestem) - dy(total), C_TEAL)
        # deep sensor beads
        for d in sensors:
            ax.add_patch(Circle((x, dy(d)), 0.058, facecolor=C_FOREST,
                                edgecolor="white", lw=0.7, zorder=6))
        # thermocouple squiggle just under the surface
        t = np.linspace(0, 1, 60)
        ax.plot(x + 0.32 * np.sin(t * 5 * np.pi) * (1 - t),
                dy(2) + 0.18 * t, color=C_DIM, lw=1.0, zorder=5)

    probe(7.15, 140, [66, 86, 116, 138])       # Probe 1 -> 140 cm
    probe(2.75, 100, [66, 86])                  # Probe 2 -> 100 cm

    # --- HFE electronics box + cables -----------------------------------------
    _rrect(ax, 4.55, ys + 0.06, 0.9, 0.5, "#E6DFD1", lw=1.0, z=5, r=0.06)
    ax.text(5.0, ys + 0.31, "HFE\nelectronics", ha="center", va="center",
            fontsize=7, color=C_CHAR)
    for xp, rad in ((7.15, 0.32), (2.75, -0.32)):
        ax.add_patch(FancyArrowPatch((5.0, ys + 0.06), (xp, dy(1)),
                     connectionstyle=f"arc3,rad={rad}", arrowstyle="-",
                     color=C_DIM, lw=1.2, zorder=4))

    # --- labels in the clear margins (leaders end at the part) ----------------
    def lab(xy, xytext, txt, col=C_CHAR, ha="left"):
        ax.annotate(txt, xy=xy, xytext=xytext, fontsize=8, color=col, ha=ha,
                    va="center", arrowprops=dict(arrowstyle="->", color=C_DIM,
                    lw=0.8), zorder=7)
    lab((7.27, dy(125)), (8.5, dy(132)), "heat-flow\nprobe 1 (140 cm)")
    lab((7.03, dy(15)), (8.5, dy(35)), "epoxy borestem\n(top 30 cm, excluded)", C_CORAL)
    lab((7.06, dy(116)), (8.5, dy(95)), "deep sensors\n$\\rightarrow K_d$", C_FOREST)
    lab((7.3, dy(3)), (8.5, dy(7)), "thermocouples", C_DIM)
    lab((2.63, dy(80)), (0.95, dy(82)), "heat-flow\nprobe 2 (100 cm)", ha="left")
    ax.text(2.75, dy(100) - 0.16, "obstruction", ha="center", va="top",
            fontsize=7, color=C_DIM, style="italic")

    ax.set_title("The two Apollo 15 heat-flow probes at Hadley Rille",
                 fontsize=11.5, fontweight="bold", loc="left", color=C_CHAR)
    fig.savefig(OUT / "fig_book_probelayout.pdf", bbox_inches="tight",
                pad_inches=0.06)
    plt.close(fig)
    print("  -> fig_book_probelayout.pdf")


def main():
    print("Building schematic illustrations:")
    fig_probe_layout()
    print("done.")


if __name__ == "__main__":
    main()
