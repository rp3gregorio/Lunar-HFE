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


def fig_sun_moon():
    """Modern schematic: the Sun heats the rotating Moon (Sun-Earth-Moon geometry)."""
    from matplotlib.patches import Wedge
    C_SUN = "#E3A12C"
    C_EARTH = "#3A6B8A"
    fig, ax = plt.subplots(figsize=(JGR_FULL, 3.9))
    ax.set_xlim(0, 13); ax.set_ylim(0, 6.4); ax.axis("off"); ax.set_aspect("equal")

    # Sun (left) with rays
    sx0, sy0 = 1.0, 3.3
    ax.add_patch(Circle((sx0, sy0), 0.95, facecolor=C_SUN, ec="none", zorder=3))
    for a in np.linspace(0, 2 * np.pi, 16, endpoint=False):
        ax.plot([sx0 + 0.95 * np.cos(a), sx0 + 1.3 * np.cos(a)],
                [sy0 + 0.95 * np.sin(a), sy0 + 1.3 * np.sin(a)],
                color=C_SUN, lw=1.2, zorder=2)
    ax.text(sx0, sy0 - 1.7, "Sun", ha="center", fontsize=9, color=C_CHAR,
            fontweight="bold")

    # Earth + the Moon's orbit
    ex, ey = 6.4, 3.3
    ax.add_patch(Circle((ex, ey), 3.0, fill=False, edgecolor=C_DIM, lw=0.8,
                        ls=(0, (5, 4)), zorder=1))
    ax.add_patch(Circle((ex, ey), 0.5, facecolor=C_EARTH, edgecolor="white",
                        lw=0.8, zorder=4))
    ax.text(ex, ey - 0.8, "Earth", ha="center", fontsize=8.5, color=C_CHAR)
    ax.text(ex, ey + 3.18, "the Moon's orbit", ha="center", fontsize=7.5,
            color=C_DIM)

    # Moon on the orbit; left (sun-facing) half lit, right half night
    mx, my, mr = 9.4, 3.3, 0.85
    ax.add_patch(Wedge((mx, my), mr, 90, 270, facecolor=C_CORAL, edgecolor=C_CHAR,
                       lw=0.8, zorder=5))
    ax.add_patch(Wedge((mx, my), mr, -90, 90, facecolor=C_TEAL, edgecolor=C_CHAR,
                       lw=0.8, zorder=5))
    ax.plot([mx, mx], [my - mr, my + mr], color=C_CHAR, lw=0.8, ls=(0, (3, 2)),
            zorder=6)
    ax.text(mx, my - mr - 0.32, "Moon", ha="center", fontsize=9, color=C_CHAR,
            fontweight="bold")

    # sunlight rays striking the lit side
    for yy in (2.55, 3.3, 4.05):
        ax.add_patch(FancyArrowPatch((2.2, yy), (mx - mr - 0.05, yy),
                     arrowstyle="-|>", mutation_scale=10, color=C_SUN, lw=1.4,
                     zorder=2))

    # the borehole site on the lit side + rotation arrow
    sa = np.deg2rad(133)
    px, py = mx + mr * np.cos(sa), my + mr * np.sin(sa)
    ax.add_patch(Circle((px, py), 0.085, facecolor=C_FOREST, edgecolor="white",
                        lw=0.6, zorder=8))
    ax.plot([px, px + 0.2 * np.cos(sa)], [py, py + 0.2 * np.sin(sa)],
            color=C_CHAR, lw=1.6, zorder=8)
    ax.add_patch(FancyArrowPatch((mx - 0.15, my + mr + 0.28),
                 (mx + 0.55, my + mr + 0.05), connectionstyle="arc3,rad=-0.5",
                 arrowstyle="-|>", mutation_scale=9, color=C_DIM, lw=1.1, zorder=6))
    ax.text(mx + 0.05, my + mr + 0.6, "rotation", fontsize=7.5, color=C_DIM,
            ha="center")

    # day / night labels (above & below, clear of rays and disc)
    ax.text(mx - mr - 0.1, my + 1.15, "day side\n$\\sim$390 K", ha="center",
            va="center", fontsize=8, color=C_CORAL, fontweight="bold")
    ax.text(mx + mr + 0.55, my - 1.05, "night side\n$\\sim$100 K", ha="center",
            va="center", fontsize=8, color=C_TEAL, fontweight="bold")
    ax.annotate("borehole site", xy=(px, py), xytext=(mx - 2.4, my + 1.5),
                fontsize=7.5, color=C_FOREST, ha="center",
                arrowprops=dict(arrowstyle="->", color=C_DIM, lw=0.7))

    ax.text(6.5, 0.45, "The site turns to face the Sun, then away, once per "
            "synodic month (29.5 days) — one lunar day.", ha="center",
            fontsize=8.5, color=C_CHAR)
    ax.set_title("How the Sun heats the rotating Moon", fontsize=11.5,
                 fontweight="bold", loc="left", color=C_CHAR)
    fig.savefig(OUT / "fig_book_sunmoon.pdf", bbox_inches="tight", pad_inches=0.06)
    plt.close(fig)
    print("  -> fig_book_sunmoon.pdf")


def fig_flux_closure():
    """Interpret d<T>/dz = Q_b/K: same heat through every layer, so the gradient
    steepens where K is small (the river-through-a-pipe analogy)."""
    from lunar.plotting.style import fmt_axis
    fig, (axA, axB) = plt.subplots(1, 2, figsize=(JGR_FULL, 3.9),
                                   gridspec_kw={"width_ratios": [1.0, 1.05]})

    # (a) the analogy: a widening pipe; same water/s, so fast where narrow
    axA.add_patch(Polygon([(0.6, 0.6), (5.6, 1.0), (5.6, 0.0), (0.6, 0.4)],
                          closed=True, facecolor="#DCE7EA", edgecolor=C_TEAL,
                          lw=1.5))
    for x0, ln, lw in [(1.0, 1.5, 3.0), (3.3, 0.85, 2.2), (4.85, 0.45, 1.6)]:
        axA.annotate("", xy=(x0 + ln, 0.5), xytext=(x0, 0.5),
                     arrowprops=dict(arrowstyle="-|>", color=C_TEAL, lw=lw))
    axA.text(1.7, 1.2, "narrow (small $K$)\nwater is fast", color=C_CORAL,
             fontsize=8.5, ha="center", fontweight="bold")
    axA.text(4.7, -0.5, "wide (large $K$)\nwater is slow", color=C_FOREST,
             fontsize=8.5, ha="center", fontweight="bold")
    axA.text(3.1, -1.15, "the same water per second crosses every slice\n"
             "(conservation) --- exactly like the same heat $Q_b$", color=C_DIM,
             fontsize=8, ha="center")
    axA.set_xlim(0, 6); axA.set_ylim(-1.5, 1.6); axA.axis("off")
    axA.set_title("(a) a river through a widening pipe", loc="left",
                  fontsize=9.5, color=C_CHAR)

    # (b) the regolith: two segments -- steep where K small, gentle where K large
    zk = 0.30
    Tk = 250 + 8.0 * zk
    Tb = Tk + 1.5 * (1.2 - zk)
    axB.axhspan(0, zk, color=C_CORAL, alpha=0.09)
    axB.axhspan(zk, 1.2, color=C_FOREST, alpha=0.09)
    axB.plot([250, Tk], [0, zk], color=C_CORAL, lw=2.8, zorder=3)
    axB.plot([Tk, Tb], [zk, 1.2], color=C_FOREST, lw=2.8, zorder=3)
    axB.plot([Tk], [zk], "o", color=C_CHAR, ms=4, zorder=4)
    axB.set_ylim(1.2, -0.02); axB.set_xlim(249.4, Tb + 0.6)
    axB.text(250.2, 0.15, "small $K$:\nsteep slope", color=C_CORAL, fontsize=8,
             va="center", fontweight="bold")
    axB.text(Tb + 0.2, 0.85, "large $K$:\ngentle slope", color=C_FOREST,
             fontsize=8, va="center", ha="right", fontweight="bold")
    fmt_axis(axB, xlabel=r"mean temperature  $\langle T\rangle$  [K]",
             ylabel="depth  $z$  [m]")
    axB.set_title(r"(b) so the profile bends at the kink:  $d\langle T\rangle/dz=Q_b/K$",
                  loc="left", fontsize=9, color=C_CHAR)
    fig.suptitle("Flux closure: the same geothermal heat $Q_b$ crosses every "
                 "layer, so the gradient steepens where $K$ is small",
                 x=0.02, y=1.02, ha="left", fontsize=10.5, fontweight="bold",
                 color=C_CHAR)
    fig.savefig(OUT / "fig_book_fluxclosure.pdf", bbox_inches="tight",
                pad_inches=0.06)
    plt.close(fig)
    print("  -> fig_book_fluxclosure.pdf")


def fig_sites_compare():
    """Modern side-by-side comparison of the two sites and their retrieved K_d."""
    fig, ax = plt.subplots(figsize=(JGR_FULL, 4.6))
    ax.set_xlim(0, 12); ax.set_ylim(0, 8); ax.axis("off")
    ys, cw = 5.0, 5.2
    cards = [
        dict(x=0.3, name="Apollo 15", place="Hadley Rille",
             sub="mare basalt regolith", kd=4.58, qb=21, deep=1.39, alb=0.131,
             reg="#D9B48A", mtn="#BcC8C6",
             ridge=[(0.3, ys), (1.6, 6.3), (2.6, 5.7), (3.4, 6.0), (5.5, ys)]),
        dict(x=6.5, name="Apollo 17", place="Taurus--Littrow",
             sub="highland massif + dark mantle", kd=8.12, qb=15, deep=2.34,
             alb=0.137, reg="#A9774B", mtn="#A9B4B2",
             ridge=[(6.5, ys), (7.6, 6.7), (8.8, 5.9), (10.1, 6.8), (11.7, ys)]),
    ]
    for c in cards:
        x0 = c["x"]
        ax.add_patch(Rectangle((x0, ys), cw, 8 - ys, facecolor=SKY, ec="none"))
        ax.add_patch(Polygon(c["ridge"], closed=True, facecolor=c["mtn"],
                             ec="none", alpha=0.9))
        ax.add_patch(Rectangle((x0, 0.6), cw, ys - 0.6, facecolor=c["reg"],
                               ec=C_DIM, lw=0.8))
        ax.plot([x0, x0 + cw], [ys, ys], color=C_CHAR, lw=1.3)
        # probe to its deepest sensor (depth scaled into the card)
        px = x0 + cw * 0.5
        zbot = ys - (c["deep"] / 2.34) * (ys - 0.9)
        ax.plot([px, px], [ys, zbot], color=C_CHAR, lw=2.6)
        ax.add_patch(Circle((px, zbot), 0.09, facecolor=C_FOREST,
                            edgecolor="white", lw=0.7, zorder=5))
        ax.text(px + 0.2, (ys + zbot) / 2, f"{c['deep']:.2f} m", fontsize=7.5,
                color=C_CHAR, va="center")
        # title + facts block, all in clear space below the card
        ax.text(x0 + cw / 2, 8.05, c["name"], ha="center", fontsize=11,
                fontweight="bold", color=C_CHAR)
        ax.text(x0 + cw / 2, 7.55, c["place"], ha="center", fontsize=8.5,
                color=C_DIM, style="italic")
        kcol = C_FOREST if c["name"].endswith("15") else C_CORAL
        ax.text(x0 + cw / 2, 0.18, f"$K_d^*$ = {c['kd']:.2f} mW m$^{{-1}}$ K$^{{-1}}$",
                ha="center", fontsize=10, fontweight="bold", color=kcol)
        ax.text(x0 + 0.2, 4.4, f"$Q_b$ = {c['qb']} mW m$^{{-2}}$\nalbedo {c['alb']}\n"
                f"{c['sub']}", fontsize=8, color=C_CHAR, va="top")

    # centre comparison
    ax.annotate("", xy=(6.4, 2.7), xytext=(5.6, 2.7),
                arrowprops=dict(arrowstyle="-|>", color=C_CORAL, lw=2.2))
    ax.text(6.0, 3.25, "$\\approx$2$\\times$\nbetter", ha="center", fontsize=9,
            color=C_CORAL, fontweight="bold")
    fig.suptitle("Two sites, two regoliths: Apollo 17's deep layer conducts heat "
                 "about twice as well as Apollo 15's", x=0.02, y=1.0, ha="left",
                 fontsize=10.5, fontweight="bold", color=C_CHAR)
    fig.savefig(OUT / "fig_book_sites.pdf", bbox_inches="tight", pad_inches=0.06)
    plt.close(fig)
    print("  -> fig_book_sites.pdf")


def main():
    print("Building schematic illustrations:")
    # probe_layout, sun_moon, sites_compare were re-authored as SVG
    # (pipeline/figures/svg/*.svg -> make_svg_figures); flux_closure stays here
    # because it contains a real T(z) plot.
    fig_flux_closure()
    print("done.")


if __name__ == "__main__":
    main()
