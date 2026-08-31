#!/usr/bin/env python3
"""The regolith column, with every governing equation pinned where it acts.

An introductory illustration for the thesis. The annotations ARE the equations:
there is no explanatory prose on the figure, because the surrounding text does
that. Each equation sits at the height of the thing it governs and is joined to
it by a hairline leader, so the reader sees *where* each one applies:

    at z = 0     the surface energy balance
    inside       Hayne's K(T,z) and the density profile rho(z)
    in time      periodicity over one lunation
    at z = 5 m   the basal geothermal flux

Beside the column is the real density profile from lunar.properties.density_hayne
on the same depth axis, and inside it the Apollo probe at its true sensor depths.

THESIS STYLE, not deck style. The thesis is 11 pt Times (newtxtext) on a 15.2 cm
text block and its figures come from lunar.plotting.style -- so this is serif, on
the JGR palette, authored at JGR_HALF (5.51 in) to sit at \\linewidth unscaled.
The deck cartoon is a separate file on a different palette; do not sync them.

DEPTH AXIS. Log, 0.5 cm to 500 cm, ticks printed. A linear 5 m axis puts the
whole density rise and the 6 cm compaction scale in the top 5 % of the frame.
Nonlinear is fine as long as the reader is told, so the reader is told.

Every number is live: density from density_hayne, sensor depths from the restored
Apollo record, Q_b / H / chi / T_ref from lunar.config.

Outputs: figures/fig_regolith_cartoon.pdf (+ .png at 300 dpi)
Run:     python code/pipeline/figures/make_regolith_cartoon.py
"""
from __future__ import annotations

import pathlib
import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import LinearSegmentedColormap
from matplotlib.patches import Arc, Circle, FancyArrowPatch

_REPO = pathlib.Path(__file__).resolve().parents[1].parent
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))
sys.path.insert(0, str(_REPO / "src"))

from lunar.apollo_helpers import extract_sensor_stability
from lunar.config import HAYNE, SITES, T_LUNAR
from lunar.constants import RHO_DEEP, RHO_SURFACE
from lunar.plotting.style import (JGR_HALF, C_A15, C_CHAR, C_CORAL, C_DIM,
                                  C_FOREST, C_GRID, C_NEUTRAL, C_TEAL,
                                  FS_TICK, assert_no_overlap)
from lunar.properties import density_hayne

FIGS = _REPO.parent / "figures"

W, HGT = JGR_HALF, 4.25          # inches; fits \linewidth at 11 pt / 2.9 cm

# ---- the x budget (inches) --------------------------------------------------
COL_L, COL_R = 0.62, 1.42        # the column
PROBE_X = 1.22                   # the probe inside it
DENS_L, DENS_R = 1.76, 2.34      # the density curve, same depth axis
EQ_X = 2.62                      # left edge of every equation
LEAD_X = 2.54                    # where the leader lines end
RIGHT_EDGE = 5.46                # nothing may extend past this

# ---- the y budget (inches) --------------------------------------------------
Y_SURF, Y_BASE = 3.24, 1.00
SUN_XY, SUN_R = (0.86, 3.94), 0.10
Y_EQ_SURF = 3.72                 # the surface balance, above the ground line
Y_EQ_MAT = 2.36                  # the two material laws, mid-column
Y_EQ_TIME = 1.50                 # periodicity
Y_EQ_BASE = 0.70                 # the basal flux
Y_RULE = 0.46                    # hairline above the equation all four serve
Y_EQ_HEAT = 0.22                 # the heat equation itself

FS_EQ = 9.5                      # equations
FS_LAB = 7.5                     # the few unavoidable identifying labels

Z_TOP, Z_BOT = 0.5, 500.0        # cm, the ends of the shared depth map
TICKS = [(1, "1"), (10, "10"), (100, "100"), (500, "500")]

SAND, SAND_D = "#F4EADC", "#D9C6A6"
HALO = dict(facecolor="white", edgecolor="none", alpha=0.72, pad=1.2)
ARROW = dict(arrowstyle="-|>", mutation_scale=9, lw=1.5, shrinkA=0, shrinkB=0,
             zorder=7)
LEAD = dict(color=C_NEUTRAL, lw=0.5, zorder=4)


def ymap(z_cm):
    """Depth in cm -> canvas y in inches. Shared by the column and the curve."""
    z = np.clip(np.asarray(z_cm, dtype=float), Z_TOP, Z_BOT)
    return Y_SURF - (Y_SURF - Y_BASE) * (np.log10(z / Z_TOP)
                                         / np.log10(Z_BOT / Z_TOP))


def draw_column(ax, sens_cm):
    mid = 0.5 * (COL_L + COL_R)
    zz = np.geomspace(Z_TOP, Z_BOT, 240)
    rho = density_hayne(zz / 100.0)
    frac = (rho - rho.min()) / (rho.max() - rho.min())

    ax.imshow(frac[:, None],
              cmap=LinearSegmentedColormap.from_list("sand", [SAND, SAND_D]),
              aspect="auto", origin="upper",
              extent=(COL_L, COL_R, Y_BASE, Y_SURF), vmin=0, vmax=1, zorder=1)

    # grains: counts and radii both driven off the real density, so the drawing
    # coarsens for the same reason the physics does
    rng = np.random.default_rng(5)
    for zc in np.geomspace(0.8, 400.0, 10):
        y0 = float(ymap(zc))
        f = float(np.interp(zc, zz, frac))
        for _ in range(int(round(6 + 16 * f))):
            gx = rng.uniform(COL_L + 0.03, COL_R - 0.03)
            if abs(gx - PROBE_X) < 0.055:
                continue
            gy = y0 + rng.uniform(-0.052, 0.052)
            if not (Y_BASE + 0.02 < gy < Y_SURF - 0.02):
                continue
            ax.add_patch(Circle((gx, gy),
                                (0.026 - 0.015 * f) * rng.uniform(0.8, 1.15),
                                facecolor="none", edgecolor=C_NEUTRAL, lw=0.4,
                                alpha=0.9, zorder=2))

    ax.plot([COL_L, COL_R], [Y_SURF, Y_SURF], color=C_CHAR, lw=1.5,
            solid_capstyle="butt", zorder=6)
    ax.plot([COL_L, COL_L, COL_R, COL_R], [Y_SURF, Y_BASE, Y_BASE, Y_SURF],
            color=C_CHAR, lw=0.7, zorder=6)

    # depth scale
    ax.text(COL_L - 0.06, Y_SURF + 0.19, "depth\n(cm)", color=C_DIM,
            fontsize=FS_LAB, ha="right", va="center", linespacing=1.2)
    for zc, lab in TICKS:
        y = float(ymap(zc))
        ax.plot([COL_L - 0.05, COL_L], [y, y], color=C_DIM, lw=0.6, zorder=6)
        ax.text(COL_L - 0.075, y, lab, color=C_DIM, fontsize=FS_LAB,
                ha="right", va="center")

    # the Sun, and the two radiative fluxes it sets up
    sx, sy = SUN_XY
    ax.add_patch(Circle((sx, sy), SUN_R, facecolor=C_CORAL, edgecolor="none",
                        zorder=8))
    for a in np.arange(0, 360, 30):
        t = np.deg2rad(a)
        ax.plot([sx + 1.4 * SUN_R * np.cos(t), sx + 2.0 * SUN_R * np.cos(t)],
                [sy + 1.4 * SUN_R * np.sin(t), sy + 2.0 * SUN_R * np.sin(t)],
                color=C_CORAL, lw=0.9, solid_capstyle="round", zorder=8)
    ax.add_patch(FancyArrowPatch((sx + 0.09, sy - 0.15),
                                 (mid - 0.11, Y_SURF + 0.012),
                                 color=C_CORAL, **ARROW))
    ax.add_patch(FancyArrowPatch((mid + 0.09, Y_SURF + 0.012),
                                 (mid + 0.30, sy - 0.13),
                                 color=C_TEAL, **ARROW))

    # the Apollo probe
    y_hi, y_lo = float(ymap(sens_cm.min())), float(ymap(sens_cm.max()))
    ax.plot([PROBE_X, PROBE_X], [Y_SURF, y_lo - 0.06], color=C_CHAR, lw=1.9,
            solid_capstyle="round", zorder=7)
    ax.plot([PROBE_X, PROBE_X], [Y_SURF, y_lo - 0.06], color=C_NEUTRAL, lw=0.7,
            solid_capstyle="round", zorder=7)
    for zc in sens_cm:
        ax.add_patch(Circle((PROBE_X, float(ymap(zc))), 0.024,
                            facecolor=C_A15, edgecolor="white", lw=0.4,
                            zorder=8))
    ax.plot([PROBE_X - 0.065] * 2, [y_hi, y_lo], color=C_A15, lw=0.7, zorder=8)
    ax.text(PROBE_X - 0.10, 0.5 * (y_hi + y_lo),
            f"Apollo\n{sens_cm.size} sensors\n"
            f"{sens_cm.min():.0f}–{sens_cm.max():.0f} cm",
            color=C_A15, fontsize=FS_LAB, ha="right", va="center",
            linespacing=1.25, zorder=8, bbox=HALO)

    # the basal flux, arriving from below
    ax.add_patch(FancyArrowPatch((mid - 0.14, Y_BASE - 0.16),
                                 (mid - 0.14, Y_BASE + 0.17),
                                 color=C_FOREST, **ARROW))

    # the compaction scale
    yH = float(ymap(HAYNE["H"] * 100.0))
    ax.plot([COL_L, COL_R], [yH, yH], color=C_CHAR, lw=0.6, ls=(0, (1.8, 1.8)),
            zorder=6)
    ax.text(COL_R - 0.03, yH + 0.025, rf"$H$", color=C_CHAR, fontsize=FS_LAB,
            ha="right", va="bottom", zorder=7, bbox=HALO)

    # The cycle icon for the condition that lives in time. It sits beside its own
    # equation, not in the column's gutter: from there its leader had to cross
    # the density curve, and periodicity is not a place on the column anyway.
    cx, cy, cr = LEAD_X - 0.11, Y_EQ_TIME, 0.085
    ax.add_patch(Arc((cx, cy), 2 * cr, 2 * cr, theta1=100, theta2=425,
                     color=C_CORAL, lw=1.0, zorder=8))
    ax.add_patch(FancyArrowPatch((cx - 0.012, cy + cr), (cx + 0.05, cy + cr),
                                 arrowstyle="-|>", mutation_scale=6, lw=1.0,
                                 color=C_CORAL, shrinkA=0, shrinkB=0, zorder=8))
    return mid, cx, cy


def draw_density(ax):
    zz = np.geomspace(Z_TOP, Z_BOT, 400)
    rho = density_hayne(zz / 100.0)
    lo, hi = 1050.0, 1850.0
    xs = DENS_L + (rho - lo) / (hi - lo) * (DENS_R - DENS_L)
    ax.fill_betweenx(ymap(zz), DENS_L, xs, color=C_GRID, alpha=0.55, lw=0,
                     zorder=2)
    ax.plot(xs, ymap(zz), color=C_CHAR, lw=1.5, solid_capstyle="round",
            zorder=5)
    for v in (int(RHO_SURFACE), int(RHO_DEEP)):
        xv = DENS_L + (v - lo) / (hi - lo) * (DENS_R - DENS_L)
        ax.plot([xv, xv], [Y_BASE, Y_SURF], color=C_GRID, lw=0.6,
                ls=(0, (1.6, 1.6)), zorder=3)
        ax.text(xv, Y_SURF + 0.05, f"{v}", color=C_DIM, fontsize=FS_LAB,
                ha="center", va="bottom")
    # The axis reads along the TOP. Below the panel these labels occupied the
    # only clear lane the basal-flux leader had, and the guard caught the leader
    # running straight through them.
    ax.text(0.5 * (DENS_L + DENS_R), Y_SURF + 0.19,
            r"$\rho$ (kg m$^{-3}$)", color=C_DIM, fontsize=FS_LAB,
            ha="center", va="bottom")


def draw_equations(ax, mid, cx, cy):
    """Every governing equation, at the height of what it governs.

    Leaders run right-to-left from a fixed x, and the four equations are in the
    same top-to-bottom order as their targets, so no two leaders cross.
    """
    yH = float(ymap(HAYNE["H"] * 100.0))

    # --- at z = 0: the surface energy balance -------------------------------
    ax.plot([LEAD_X, mid + 0.34], [Y_EQ_SURF, Y_EQ_SURF], **LEAD)
    ax.plot([mid + 0.34, mid + 0.34], [Y_EQ_SURF, Y_SURF + 0.30], **LEAD)
    # Inline derivatives, not \dfrac: a stacked fraction here grows tall enough
    # to reach up into its own "at z = 0" tag.
    ax.text(EQ_X, Y_EQ_SURF + 0.15, r"at $z=0$", color=C_CORAL,
            fontsize=FS_LAB, ha="left", va="center")
    ax.text(EQ_X, Y_EQ_SURF - 0.03,
            r"$(1-A)\,S(t)=\varepsilon\sigma T_s^{4}"
            r"+K\,\partial T/\partial z$",
            color=C_CHAR, fontsize=FS_EQ, ha="left", va="center")

    # --- inside: the two material laws --------------------------------------
    # No leader. The material laws hold at EVERY depth, so a line to one height
    # would misstate them -- and to get there it had to cross the density curve.
    ax.text(EQ_X, Y_EQ_MAT + 0.40, r"inside the column", color=C_TEAL,
            fontsize=FS_LAB, ha="left", va="center")
    ax.text(EQ_X, Y_EQ_MAT + 0.21,
            r"$K(T,z)=\left[K_d-(K_d-K_s)\,e^{-z/H}\right]$",
            color=C_CHAR, fontsize=FS_EQ, ha="left", va="center")
    ax.text(EQ_X + 0.30, Y_EQ_MAT + 0.02,
            r"$\times\left[1+\chi\,(T/T_{\rm ref})^{3}\right]$",
            color=C_CHAR, fontsize=FS_EQ, ha="left", va="center")
    ax.text(EQ_X, Y_EQ_MAT - 0.21,
            r"$\rho(z)=\rho_d-(\rho_d-\rho_s)\,e^{-z/H}$",
            color=C_CHAR, fontsize=FS_EQ, ha="left", va="center")
    ax.text(EQ_X, Y_EQ_MAT - 0.42,
            rf"$K_s={HAYNE['K_S']*1e3:.2f}$ mW m$^{{-1}}$K$^{{-1}}$, "
            rf"$H={HAYNE['H']*100:.0f}$ cm,",
            color=C_DIM, fontsize=FS_LAB, ha="left", va="center")
    ax.text(EQ_X, Y_EQ_MAT - 0.57,
            rf"$\chi={HAYNE['CHI']}$, $T_{{\rm ref}}={HAYNE['T_REF']:.0f}$ K; "
            r"$K_d$ retrieved",
            color=C_DIM, fontsize=FS_LAB, ha="left", va="center")

    # --- in time: periodicity ------------------------------------------------
    ax.text(EQ_X, Y_EQ_TIME + 0.14, r"in time", color=C_CORAL,
            fontsize=FS_LAB, ha="left", va="center")
    ax.text(EQ_X, Y_EQ_TIME - 0.06,
            rf"$T(z,\,t+P)=T(z,\,t)$,  $P={T_LUNAR/86400.0:.2f}$ d",
            color=C_CHAR, fontsize=FS_EQ, ha="left", va="center")

    # --- at the base: the geothermal flux ------------------------------------
    ax.plot([LEAD_X, mid - 0.14], [Y_EQ_BASE, Y_EQ_BASE], **LEAD)
    ax.plot([mid - 0.14, mid - 0.14], [Y_EQ_BASE, Y_BASE - 0.16], **LEAD)
    ax.text(EQ_X, Y_EQ_BASE + 0.15, r"at $z=5$ m", color=C_FOREST,
            fontsize=FS_LAB, ha="left", va="center")
    ax.text(EQ_X, Y_EQ_BASE - 0.03,
            r"$-K\,\partial T/\partial z=Q_b="
            rf"{SITES['A15']['Q_BASAL']*1e3:.0f}\,/\,"
            rf"{SITES['A17']['Q_BASAL']*1e3:.0f}$ mW m$^{{-2}}$",
            color=C_CHAR, fontsize=FS_EQ, ha="left", va="center")

    # --- the equation all four of them serve ---------------------------------
    # This one keeps its stacked fractions: it is the point of the figure, it has
    # the whole bottom band to itself, and the rule above it is set clear of the
    # numerators.
    ax.plot([EQ_X, RIGHT_EDGE - 0.55], [Y_RULE, Y_RULE], color=C_GRID, lw=0.7)
    ax.text(EQ_X, Y_EQ_HEAT,
            r"$\rho(z)\,c_p(T)\,\dfrac{\partial T}{\partial t}"
            r"=\dfrac{\partial}{\partial z}"
            r"\!\left[K(T,z)\dfrac{\partial T}{\partial z}\right]$",
            color=C_CHAR, fontsize=FS_EQ + 1.0, ha="left", va="center")
    _ = yH


def main() -> None:
    site = SITES["A15"]
    sens = extract_sensor_stability(site["mission"], site["MIN_DEPTH_CM"])
    z_all = np.asarray(sens["depth_cm_all"], dtype=float)
    sens_cm = z_all[np.asarray(sens["deep_mask"], dtype=bool)]

    fig = plt.figure(figsize=(W, HGT))
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, W)
    ax.set_ylim(0, HGT)
    ax.axis("off")

    mid, cx, cy = draw_column(ax, sens_cm)
    draw_density(ax)
    draw_equations(ax, mid, cx, cy)

    fig.canvas.draw()
    assert_no_overlap(ax)
    FIGS.mkdir(parents=True, exist_ok=True)
    # style.py sets savefig.bbox='tight'; keep it, but with a hairline pad so the
    # deliberate canvas is not blown out by the default 0.15 in border
    with plt.rc_context({"savefig.pad_inches": 0.02}):
        fig.savefig(FIGS / "fig_regolith_cartoon.pdf")
        fig.savefig(FIGS / "fig_regolith_cartoon.png", dpi=300)
    plt.close(fig)
    print(f"  wrote figures/fig_regolith_cartoon.pdf + .png  "
          f"({W:.2f} x {HGT:.2f} in)")
    print(f"  A15 deep sensors: {sens_cm.size} at "
          f"{sens_cm.min():.0f}-{sens_cm.max():.0f} cm")


if __name__ == "__main__":
    main()
