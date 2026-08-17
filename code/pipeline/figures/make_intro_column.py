#!/usr/bin/env python3
"""Letter Figure 1 -- the column, its grid, the probes in it, and its density.

Extends the fig_column_illustration design (3-D sheared cutaway | the 69-cell
grid | rho(z)) with the two things the letter needs alongside them: the Apollo
borestems drawn at their real sensor depths in the material they measured, and
the two boundary conditions named on the fluxes that already carry them.

ORIGINAL DOC FOLLOWS.

The regolith column, lit, beside the density profile Hayne's model gives it.

Deliberately UNLABELLED apart from the two axes. This is the picture only -- the
boundary-condition equations are added downstream, in the document, so the figure
leaves the space and makes no claim of its own. That is why the arrows carry no
symbols: an equation printed here would have to be moved or deleted later.

  LEFT   a lit block cutaway of the full 5 m column. One light source, the Sun,
         upper left; every shadow falls down-right. The ground is a solid block
         with a lit top face and a shaded side face, and the grains loosen toward
         the surface and crowd with depth because the real density does.
         Five flux arrows, visually distinct so each can be labelled:
             straight warm, into the surface .... sunlight arriving
             warm fan off the impact point ...... scattered back (diffuse)
             thick warm, into the ground ........ absorbed
             wavy cool, off the whole surface ... radiated back out
             thin dark, downward ................ conducted into the column
             green, upward at the base .......... the interior's heat
  RIGHT  the density profile from lunar.properties.density_hayne on the SAME
         depth axis, with the compaction scale H marked.

WHY THE ARROWS LOOK THE WAY THEY DO. The scatter is a starburst, not a bounce:
regolith is a rough scatterer and a specular reflection would teach the wrong
thing. The outgoing heat is wavy, cool, and leaves the whole surface rather than
the impact point, because it is not reflected sunlight -- it is the warm ground
glowing, at a wavelength fifteen times longer.

DEPTH AXIS. Log, 0.5 cm to 500 cm, ticks printed. A linear 5 m axis buries the
entire density rise and the 6 cm compaction scale in the top 5 % of the frame.

Outputs: figures/fig_column_illustration.pdf (+ .png at 300 dpi)
Run:     python code/pipeline/figures/make_column_illustration.py
"""
from __future__ import annotations

import pathlib
import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import LinearSegmentedColormap
from matplotlib.patches import Circle, FancyArrowPatch, Polygon, Rectangle

_HERE = pathlib.Path(__file__).resolve().parent
_REPO = _HERE.parents[1]
for _p in (str(_REPO), str(_REPO / "src"), str(_HERE)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from lunar.apollo_helpers import extract_sensor_stability
from lunar.config import GRID, HAYNE, SITES
from matplotlib.colors import to_rgb

from lunar.constants import RHO_DEEP, RHO_SURFACE
from lunar.grid import make_geometric_grid
from lunar.plotting.style import (C_CHAR, C_CORAL, C_DIM, C_FOREST, C_GRID,
                                  C_MS, C_TEAL)
from lunar.properties import (conductivity_hayne, conductivity_martinez,
                              density_hayne)

from make_surface_balance import (GRAIN_RIM, GROUND_DEEP, GROUND_LIT,
                                  GROUND_MID, PAPER, _shade, apply_style,
                                  grain, setup_fonts)

FIGS = _REPO.parent / "figures"

W, H = 7.48, 4.36                     # landscape

WARM, COOL, DARK = C_CORAL, C_TEAL, C_CHAR
BAND_COMPACT = "#EFE7DC"              # the compaction zone, shared by both panels

# ---- x budget (inches) ------------------------------------------------------
BLK_L, BLK_R = 0.68, 3.32
SHEAR_X, SHEAR_Y = 0.26, 0.17
X_SPLIT = 0.68 + 0.66 * (3.32 - 0.68)  # material (left) | grid (right)
GAP_L = BLK_R + SHEAR_X + 0.10        # where the tie lines start
DENS_L, DENS_R = 4.16, 5.24
KPAN_L, KPAN_R = 5.86, 7.06        # the K(z) comparison panel
NOTE_X = KPAN_R + 0.12                 # (texture notes now live in the caption)
# The grid half carries its OWN LINEAR depth mapping. It cannot share the log
# axis: a log axis compresses exactly where the cells are fine, so cell faces
# drawn on one crowd at depth and spread at the surface -- 12 per inch near the
# surface against 36 deep, where the truth is 807 against 12. The price is that a
# horizontal line does not mean the same depth on both halves, so each half is
# labelled with its own scale and its own ticks.

# ---- y budget (inches) ------------------------------------------------------
Y_TOP, Y_BOT = 3.00, 0.52
SUN, SUN_R = (1.05, 3.90), 0.090
IMPACT = (1.34, 3.09)
EMIT_X = (1.88, 2.32, 2.74)
X_CONDUCT = 1.88

Z_TOP, Z_BOT = 0.5, 500.0
TICKS = [(1, "1"), (10, "10"), (100, "100"), (500, "500")]
Z_COMPACT = 30.0         # rho is within 0.7 % of its deep value by here
Z_SKIN_DEAD = 54.0       # cm, swing under 0.1 K (measured)
BORESTEM_CM = SITES["A15"]["MIN_DEPTH_CM"]   # 80 cm exclusion
TIE_Z = (1.0, 6.0, 15.0, 30.0)

HALO = dict(facecolor=PAPER, edgecolor="none", alpha=0.80, pad=1.2)
ARROW = dict(arrowstyle="-|>", mutation_scale=11, lw=1.8, shrinkA=0, shrinkB=0)


def ymap(z_cm):
    z = np.clip(np.asarray(z_cm, dtype=float), Z_TOP, Z_BOT)
    return Y_TOP - (Y_TOP - Y_BOT) * (np.log10(z / Z_TOP)
                                      / np.log10(Z_BOT / Z_TOP))



def _blend(c0, c1, t):
    a = np.array(to_rgb(c0)); b = np.array(to_rgb(c1))
    return tuple(a + (b - a) * float(np.clip(t, 0.0, 1.0)))


def zmap(y):
    """Inverse of ymap: the depth (cm) a y-coordinate stands for."""
    frac = (Y_TOP - np.asarray(y, dtype=float)) / (Y_TOP - Y_BOT)
    return Z_TOP * 10.0 ** (frac * np.log10(Z_BOT / Z_TOP))


def compaction(y):
    """0 at the loosest surface, 1 at the fully compacted deep value.

    The tone of the cut faces is driven by this rather than by position on the
    axis, so the block darkens exactly where rho(z) actually rises -- all of it
    above 30 cm -- and stops darkening below, where the regolith is already at
    its deep density. Position-linear shading implied compaction continuing to
    5 m, which the density panel to the right plainly contradicts.
    """
    rho = density_hayne(zmap(y) / 100.0)
    lo, hi = float(density_hayne(np.array([Z_TOP / 100.0]))[0]), RHO_DEEP
    return np.clip((rho - lo) / (hi - lo), 0.0, 1.0)


def dens_x(rho):
    return DENS_L + (np.asarray(rho) - 1050.0) / 800.0 * (DENS_R - DENS_L)


K_LO, K_HI = 0.0, 9.0                 # mW/m/K, the panel's span


def kx(k_mW):
    return KPAN_L + (np.asarray(k_mW) - K_LO) / (K_HI - K_LO) * (KPAN_R - KPAN_L)


def draw_shared_band(ax):
    """ONE band across BOTH panels: the surface down to 30 cm, which is where
    rho actually moves (99.3 % of its whole range).

    Drawn before the block so the grains sit on top of it, and carried through
    the gap and across the density panel at the same tone. That is what makes the
    texture and the curve read as one statement instead of two coincidences.
    """
    y0 = float(ymap(Z_COMPACT))
    # The band is a LOG-axis statement, so it stops at the split and resumes
    # beyond the block: over the grid half it would mark the wrong depth.
    ax.add_patch(Rectangle((BLK_L, y0), X_SPLIT - BLK_L, Y_TOP - y0,
                           facecolor=BAND_COMPACT, edgecolor="none",
                           alpha=0.30, zorder=6.5))
    ax.add_patch(Rectangle((GAP_L - 0.10, y0), DENS_R - GAP_L + 0.10,
                           Y_TOP - y0, facecolor=BAND_COMPACT,
                           edgecolor="none", alpha=0.30, zorder=6.5))
    ax.plot([BLK_L, X_SPLIT], [y0, y0], color=_shade(C_DIM, 0.25), lw=0.8,
            ls=(0, (2.6, 2.2)), zorder=6.6)
    ax.plot([GAP_L - 0.10, DENS_R], [y0, y0], color=_shade(C_DIM, 0.25),
            lw=0.8, ls=(0, (2.6, 2.2)), zorder=6.6)


def draw_block(ax):
    mid = 0.5 * (BLK_L + BLK_R)

    for dx, dy, a in ((0.09, -0.09, 0.05), (0.05, -0.05, 0.06),
                      (0.02, -0.02, 0.07)):
        ax.add_patch(Polygon([(BLK_L + dx, Y_BOT + dy), (BLK_R + dx, Y_BOT + dy),
                              (BLK_R + SHEAR_X + dx, Y_BOT + SHEAR_Y + dy),
                              (BLK_L + SHEAR_X + dx, Y_BOT + SHEAR_Y + dy)],
                             closed=True, facecolor=DARK, edgecolor="none",
                             alpha=a, zorder=1))

    _rows = np.linspace(Y_TOP, Y_BOT, 256)
    ax.imshow(compaction(_rows)[:, None],
              cmap=LinearSegmentedColormap.from_list(
                  "cut", [GROUND_MID, GROUND_DEEP]),
              aspect="auto", origin="upper",
              extent=(BLK_L, BLK_R, Y_BOT, Y_TOP), vmin=0, vmax=1, zorder=2)

    for k in range(80):                      # the shaded side face
        t0, t1 = k / 80, (k + 1) / 80
        y0 = Y_TOP - t0 * (Y_TOP - Y_BOT)
        y1 = Y_TOP - t1 * (Y_TOP - Y_BOT)
        ax.add_patch(Polygon([(BLK_R, y0), (BLK_R + SHEAR_X, y0 + SHEAR_Y),
                              (BLK_R + SHEAR_X, y1 + SHEAR_Y), (BLK_R, y1)],
                             closed=True,
                             facecolor=_shade(
                                 _blend(GROUND_MID, GROUND_DEEP,
                                        float(compaction(y0))),
                                 -0.18 - 0.16 * t0),
                             edgecolor="none", zorder=3))

    ax.add_patch(Polygon([(BLK_L, Y_TOP), (BLK_R, Y_TOP),
                          (BLK_R + SHEAR_X, Y_TOP + SHEAR_Y),
                          (BLK_L + SHEAR_X, Y_TOP + SHEAR_Y)],
                         closed=True, facecolor=GROUND_LIT,
                         edgecolor=_shade(GRAIN_RIM, -0.15), lw=0.6, zorder=4))
    for xa, ya, xb, yb in ((BLK_R, Y_TOP, BLK_R + SHEAR_X, Y_TOP + SHEAR_Y),
                           (BLK_R + SHEAR_X, Y_TOP + SHEAR_Y,
                            BLK_R + SHEAR_X, Y_BOT + SHEAR_Y),
                           (BLK_R, Y_BOT, BLK_R + SHEAR_X, Y_BOT + SHEAR_Y)):
        ax.plot([xa, xb], [ya, yb], color=_shade(GRAIN_RIM, -0.3), lw=0.7,
                zorder=6)
    ax.plot([BLK_L, BLK_R], [Y_TOP, Y_TOP], color=_shade(GROUND_LIT, 0.45),
            lw=1.3, solid_capstyle="butt", zorder=6)
    ax.plot([BLK_L, BLK_L, BLK_R, BLK_R], [Y_TOP, Y_BOT, Y_BOT, Y_TOP],
            color=_shade(GRAIN_RIM, -0.25), lw=0.7, zorder=6)

    # grains: counts and radii driven off the real density profile
    rng = np.random.default_rng(23)
    zz = np.geomspace(Z_TOP, Z_BOT, 200)
    rho = density_hayne(zz / 100.0)
    frac = (rho - RHO_SURFACE) / (RHO_DEEP - RHO_SURFACE)
    ygrid = ymap(zz)
    n_band = 23
    for i in range(n_band):
        t = i / (n_band - 1)
        y0 = Y_TOP - 0.06 - t * (Y_TOP - Y_BOT - 0.12)
        z_here = float(np.interp(y0, ygrid[::-1], zz[::-1]))
        fq = float(np.interp(z_here, zz, frac))
        rad = 0.046 - 0.030 * fq
        for _ in range(int(round(7 + 24 * fq))):
            gx = rng.uniform(BLK_L + 1.3 * rad, X_SPLIT - 1.3 * rad)
            gy = y0 + rng.uniform(-0.036, 0.036)
            if not (Y_BOT + 1.2 * rad < gy < Y_TOP - 1.2 * rad):
                continue
            grain(ax, gx, gy, rad * rng.uniform(0.74, 1.15))
    for _ in range(40):                       # on the shaded side face
        tt = rng.uniform(0.16, 0.82)
        yy = rng.uniform(Y_BOT + 0.07, Y_TOP - 0.06)
        d_f = (Y_TOP - yy) / (Y_TOP - Y_BOT)
        grain(ax, BLK_R + tt * SHEAR_X, yy + tt * SHEAR_Y,
              (0.034 - 0.020 * d_f) * rng.uniform(0.7, 1.1), z=4, dim=0.22)
    for _ in range(24):                       # on the lit top face
        yy = rng.uniform(Y_TOP + 0.03, Y_TOP + SHEAR_Y - 0.03)
        t = (yy - Y_TOP) / SHEAR_Y
        gx = rng.uniform(BLK_L + t * SHEAR_X + 0.05,
                         BLK_R + t * SHEAR_X - 0.05)
        if abs(gx - IMPACT[0]) < 0.10:
            continue
        grain(ax, gx, yy, rng.uniform(0.022, 0.036), z=5)

    # the depth scale
    ax.text(BLK_L - 0.07, Y_TOP + 0.30, "depth\n(cm)", color=C_DIM,
            fontsize=8.0, ha="right", va="center", linespacing=1.2)
    for zc, lab in TICKS:
        y = float(ymap(zc))
        ax.plot([BLK_L - 0.05, BLK_L], [y, y], color=C_DIM, lw=0.6, zorder=6)
        ax.text(BLK_L - 0.08, y, lab, color=C_DIM, fontsize=8.0, ha="right",
                va="center")
    return mid


def draw_grid_half(ax):
    """The right half of the block: the 69 cell faces, on a LINEAR depth mapping.

    The cell separations are the point of this half, and they are only truthful on
    a linear axis. Two earlier versions both failed on the shared log axis: faces
    drawn on it made the surface look coarsest (cell 2 is 160x thinner than the
    deepest cell yet was drawn 3.4x taller), and switching to bars whose LENGTH
    was the thickness fixed that reading but left the SPACING inverted -- 12 per
    inch near the surface against 36 deep, where reality is 807 against 12.

    So this half maps depth linearly over the same vertical extent. The fine cells
    now collapse into a dense band at the surface and the 37 cm cells are visibly
    thick, which is the truth. The cost is real and is signposted rather than
    hidden: a horizontal line does NOT mean the same depth on both halves, so each
    half gets its own scale label and its own ticks -- log in centimetres down the
    left, linear in metres inside the right.
    """
    g = make_geometric_grid(**GRID)
    zf = g.z_face
    z_max = float(zf[-1])
    span = Y_TOP - Y_BOT

    def ylin(z):
        return Y_TOP - (z / z_max) * span

    for i in range(zf.size - 1):
        t = zf[i] / z_max
        ax.add_patch(Rectangle((X_SPLIT, ylin(zf[i + 1])), BLK_R - X_SPLIT,
                               ylin(zf[i]) - ylin(zf[i + 1]),
                               facecolor=_shade(GROUND_MID, 0.26 - 0.42 * t),
                               edgecolor=_shade(C_DIM, 0.08), lw=0.3,
                               zorder=7.2))
    ax.plot([X_SPLIT, X_SPLIT], [Y_BOT, Y_TOP], color=_shade(C_CHAR, 0.15),
            lw=1.1, zorder=7.6)

    for z in (1.0, 2.0, 3.0, 4.0, 5.0):
        y = float(ylin(z))
        ax.plot([BLK_R - 0.07, BLK_R], [y, y], color=_shade(C_CHAR, 0.35),
                lw=0.6, zorder=7.7)
        ax.text(BLK_R - 0.10, y, f"{z:.0f}", color=_shade(C_CHAR, 0.25),
                fontsize=7.0, ha="right", va="center", zorder=7.8, bbox=HALO)

    ax.text(X_SPLIT + 0.05, Y_TOP - 0.10,
            rf"$\Delta z={g.dz[0]*1e3:.0f}$ mm", color=COOL, fontsize=7.5,
            ha="left", va="top", zorder=13, bbox=HALO)
    ax.text(X_SPLIT + 0.05, float(ylin(z_max - g.dz[-1] / 2)),
            rf"$\Delta z={g.dz[-1]*100:.0f}$ cm", color=COOL, fontsize=7.5,
            ha="left", va="center", zorder=13, bbox=HALO)
    return g


def draw_grid_notes(ax, g):
    dz = g.dz
    ax.text(0.5 * (BLK_L + X_SPLIT), Y_BOT - 0.17,
            "the material", color=C_CHAR, fontsize=8.5, ha="center",
            va="center")

    ax.text(0.5 * (X_SPLIT + BLK_R), Y_BOT - 0.17,
            f"the grid — {g.n_layers} cells", color=C_CHAR, fontsize=8.5,
            ha="center", va="center")
    # one line for both scales: two separate sub-labels overlapped at the split
    ax.text(0.5 * (BLK_L + BLK_R), Y_BOT - 0.42,
            r"left: log depth (cm, outer axis)  ·  right: linear depth "
            r"(m, inner ticks), each cell $1.08\times$ the last",
            color=C_DIM, fontsize=7.0, ha="center", va="center")


def draw_fluxes(ax, mid):
    ix, iy = IMPACT
    sx, sy = SUN

    for k in range(12):                       # the Sun's glow
        t = k / 11
        ax.add_patch(Circle((sx, sy), SUN_R * (1 + 3.2 * t ** 1.5),
                            facecolor=WARM, edgecolor="none",
                            alpha=0.05 * (1 - t) ** 1.4, zorder=8))
    ax.add_patch(Circle((sx, sy), SUN_R, facecolor=_shade(WARM, 0.18),
                        edgecolor="none", zorder=9))
    ax.add_patch(Circle((sx, sy), SUN_R * 0.55, facecolor=_shade(WARM, 0.42),
                        edgecolor="none", zorder=9))

    d = np.array([ix - sx, iy - sy], dtype=float)
    d /= np.hypot(*d)
    perp = np.array([-d[1], d[0]])
    ang = np.degrees(np.arctan2(-d[1], -d[0]))

    # arriving sunlight: one arrow, with parallel strokes in its upper third only
    p0 = np.array([sx, sy]) + d * 0.26
    for off, a in ((-0.060, 0.50), (0.060, 0.50), (-0.030, 0.68), (0.030, 0.68)):
        q0, q1 = p0 + perp * off, p0 + d * 0.42 + perp * off
        ax.plot([q0[0], q1[0]], [q0[1], q1[1]], color=WARM, lw=0.9, alpha=a,
                solid_capstyle="round", zorder=10)
    ax.add_patch(FancyArrowPatch(tuple(p0), (ix, iy), color=WARM, lw=2.1,
                                 arrowstyle="-|>", mutation_scale=12,
                                 shrinkA=0, shrinkB=0, zorder=11))

    # scattered back: a diffuse starburst, longest near vertical
    for a_deg in np.linspace(16.0, 162.0, 11):
        if abs(a_deg - ang) < 15.0:
            continue
        th = np.radians(a_deg)
        ln = 0.26 + 0.30 * np.sin(th) ** 1.3
        v = np.array([np.cos(th), np.sin(th)])
        ax.plot([ix + v[0] * 0.09, ix + v[0] * ln * 0.60],
                [iy + v[1] * 0.09, iy + v[1] * ln * 0.60],
                color=WARM, lw=0.85, alpha=0.75, solid_capstyle="round",
                zorder=10)
        ax.plot([ix + v[0] * ln * 0.56, ix + v[0] * ln],
                [iy + v[1] * ln * 0.56, iy + v[1] * ln],
                color=WARM, lw=0.85, alpha=0.30, solid_capstyle="round",
                zorder=10)

    # absorbed: into the ground
    ax.add_patch(FancyArrowPatch((ix, iy - 0.02), (ix, iy - 0.38), color=WARM,
                                 lw=2.8, arrowstyle="-|>", mutation_scale=13,
                                 shrinkA=0, shrinkB=0, zorder=12))

    # radiated back out: wavy, cool, from along the whole surface
    for j, ex in enumerate(EMIT_X):
        th = np.radians(95 - 8 * j)
        v = np.array([np.cos(th), np.sin(th)])
        n = np.array([-v[1], v[0]])
        s = np.linspace(0, 1, 150)
        L = 0.58 + 0.04 * (j % 2)
        # The wiggle ramps in from the surface AND back out before the tip, so
        # the last stretch is straight along v. Left at full amplitude the head
        # inherited the sine's steepest slope and skewed off the path.
        env = np.clip(s * 3.0, 0, 1) * np.clip((1.0 - s) * 5.0, 0, 1)
        pts = (np.array([ex, Y_TOP + 0.05])[None, :]
               + v[None, :] * (s * L)[:, None]
               + n[None, :] * (0.026 * np.sin(s * 4.0 * np.pi) * env)[:, None])
        ax.plot(pts[:, 0], pts[:, 1], color=COOL, lw=3.0, alpha=0.10,
                solid_capstyle="round", zorder=9)
        ax.plot(pts[:, 0], pts[:, 1], color=COOL, lw=1.3, alpha=0.95,
                solid_capstyle="round", zorder=10)
        ax.add_patch(FancyArrowPatch(tuple(pts[-14]), tuple(pts[-1]), color=COOL,
                                     lw=1.3, arrowstyle="-|>",
                                     mutation_scale=7.5, shrinkA=0, shrinkB=0,
                                     joinstyle="miter", zorder=10))

    # conducted downward: thin, and it should look thin
    ax.add_patch(FancyArrowPatch((X_CONDUCT, Y_TOP - 0.14),
                                 (X_CONDUCT, Y_TOP - 0.58),
                                 color=DARK, lw=1.0, arrowstyle="-|>",
                                 mutation_scale=8, shrinkA=0, shrinkB=0,
                                 zorder=12))

    # the interior's heat, arriving at the base. Kept left of centre: at the
    # block's midpoint its tail ran straight through the grid caption below.
    ax.add_patch(FancyArrowPatch((BLK_L + 0.16, Y_BOT - 0.28),
                                 (BLK_L + 0.16, Y_BOT + 0.16),
                                 color=C_FOREST, zorder=10, **ARROW))

    # the one physical note kept on the illustration
    y_dead = float(ymap(Z_SKIN_DEAD))
    ax.plot([BLK_L, X_SPLIT], [y_dead, y_dead], color=_shade(WARM, -0.3),
            lw=0.8, ls=(0, (2.4, 2.0)), zorder=12)
    ax.text(X_SPLIT - 0.04, y_dead + 0.03,
            rf"$<0.1$ K",
            color=_shade(WARM, -0.3), fontsize=7.5, ha="right", va="bottom",
            zorder=13, bbox=HALO)



# ---- the probes, drawn into the material they measured ----------------------
PROBE_LANES = {"a15": (BLK_L + 0.82, C_FOREST, "Apollo 15"),
               "a17": (BLK_L + 1.04, C_CORAL, "Apollo 17")}


def draw_probes(ax):
    """Both borestems, drawn as instruments rather than lines.

    Each is a pale drill casing with the probe rod inside it, a small head box
    at the surface, and the platinum sensors as beads on the rod: filled where
    the sensor enters the retrieval, open inside the excluded borestem zone.
    """
    for mis, (x, col, lab) in PROBE_LANES.items():
        o = extract_sensor_stability(mis, int(BORESTEM_CM))
        d = np.asarray(o["depth_cm_all"], dtype=float)
        m = np.asarray(o["deep_mask"], dtype=bool)
        y_s, y_e = float(ymap(Z_TOP)), float(ymap(d.max()))

        # the drilled casing: pale, wider, with a soft edge
        ax.plot([x, x], [y_s, y_e], color=PAPER, lw=5.2, alpha=0.85,
                solid_capstyle="round", zorder=12.6)
        ax.plot([x, x], [y_s, y_e], color=_shade(col, 0.55), lw=4.4,
                alpha=0.55, solid_capstyle="round", zorder=12.7)
        # the probe rod inside it
        ax.plot([x, x], [y_s, y_e], color=_shade(col, -0.10), lw=1.5,
                alpha=0.95, solid_capstyle="round", zorder=13)
        # the closed nose
        ax.plot([x], [y_e], marker="v", ms=3.4, color=_shade(col, -0.25),
                zorder=13.5)
        # the head box, sitting on the surface
        ax.add_patch(Rectangle((x - 0.055, y_s), 0.11, 0.075,
                               facecolor=_shade(col, 0.30),
                               edgecolor=_shade(col, -0.25), lw=0.6,
                               zorder=13.6))

        # the sensors
        ax.scatter(np.full(int(m.sum()), x), ymap(d[m]), s=13, facecolor=col,
                   edgecolor=PAPER, linewidth=0.6, zorder=14)
        ax.scatter(np.full(int((~m).sum()), x), ymap(d[~m]), s=13,
                   facecolor=PAPER, edgecolor=col, linewidth=0.8, zorder=14)

        side = -1 if mis == "a15" else 1          # labels point away from each other
        ax.text(x + 0.075 * side, y_e,
                f"{lab}\n{d.max()/100:.2f} m · {int(m.sum())} sensors",
                color=_shade(col, -0.2), fontsize=6.6, linespacing=1.35,
                ha=("right" if side < 0 else "left"), va="center",
                zorder=15, bbox=HALO)


def draw_kpanel(ax):
    """The difference that actually exists between the two published models:
    not rho(z) -- Martinez & Siegler adopt Hayne's exponential form (their
    Eq. 3) -- but K(z). Evaluated at 250 K, the mean deep temperature."""
    zz = np.geomspace(Z_TOP, Z_BOT, 400)
    T = np.full_like(zz, 250.0)
    kh = conductivity_hayne(T, zz / 100.0) * 1e3
    km = conductivity_martinez(T, zz / 100.0) * 1e3

    ax.plot([kx(K_LO), kx(K_HI)], [Y_TOP, Y_TOP], color=C_GRID, lw=0.8, zorder=3)
    ax.plot(kx(kh), ymap(zz), color=COOL, lw=1.7, solid_capstyle="round",
            zorder=5, label="Hayne")
    ax.plot(kx(km), ymap(zz), color=C_MS, lw=1.7, ls=(0, (4.0, 2.0)),
            solid_capstyle="round", zorder=5)

    for v in (0, 3, 6, 9):
        ax.plot([kx(v), kx(v)], [Y_TOP, Y_TOP + 0.055], color=C_DIM, lw=0.7,
                zorder=4)
        ax.text(kx(v), Y_TOP + 0.09, f"{v:g}", color=C_DIM, fontsize=7,
                ha="center", va="bottom", zorder=6)
    ax.text(0.5 * (KPAN_L + KPAN_R), Y_TOP + 0.30,
            r"$K$ (mW m$^{-1}$ K$^{-1}$) at 250 K", color=C_CHAR,
            fontsize=7.6, ha="center", va="bottom", zorder=6)

    ax.text(kx(6.9), ymap(2.2), "Hayne", color=COOL, fontsize=7.2,
            ha="left", va="center", zorder=7, bbox=HALO)
    ax.text(kx(8.1), ymap(320.0), "Mart\u00ednez\n& Siegler", color=C_MS,
            fontsize=7.2, ha="left", va="center", zorder=7, bbox=HALO)


def draw_bc_labels(ax):
    """Name the two boundary conditions on the fluxes already drawn."""
    ax.text(BLK_R + SHEAR_X + 0.06, Y_TOP + 0.86,
            r"$(1-A)F_\odot-\varepsilon\sigma T_s^{4}"
            r"=\left(-K\,\partial_z T\right)_{z=0}$",
            color=DARK, fontsize=7.2, ha="right", va="center", zorder=15,
            bbox=HALO)
    ax.text(BLK_L + 0.30, Y_BOT + 0.02,
            r"$K\,\partial_z T|_{z_{\max}}=Q_b$",
            color=_shade(C_FOREST, -0.2), fontsize=7.0, ha="left", va="bottom",
            zorder=15, bbox=HALO)


def draw_density(ax):
    zz = np.geomspace(Z_TOP, Z_BOT, 400)
    rho = density_hayne(zz / 100.0)
    lo, hi = 1050.0, 1850.0
    xs = DENS_L + (rho - lo) / (hi - lo) * (DENS_R - DENS_L)
    ax.fill_betweenx(ymap(zz), DENS_L, xs, color=C_GRID, alpha=0.6, lw=0,
                     zorder=2)
    ax.plot(xs, ymap(zz), color=DARK, lw=1.7, solid_capstyle="round", zorder=5)
    for v in (int(RHO_SURFACE), int(RHO_DEEP)):
        xv = DENS_L + (v - lo) / (hi - lo) * (DENS_R - DENS_L)
        ax.plot([xv, xv], [Y_BOT, Y_TOP], color=C_GRID, lw=0.6,
                ls=(0, (1.6, 1.6)), zorder=3)
        ax.text(xv, Y_TOP + 0.06, f"{v}", color=C_DIM, fontsize=8.0,
                ha="center", va="bottom")
    ax.text(0.5 * (DENS_L + DENS_R), Y_TOP + 0.24,
            r"$\rho$ (kg m$^{\mathrm{-3}}$)", color=C_DIM, fontsize=8.5,
            ha="center", va="bottom")
    # --- the tie lines: the packing at a depth <-> the density at that depth --
    # Four depths spanning the transition: 15 %, 63 %, 92 % and 99 % of the way
    # from the surface density to the deep one. Each runs from the block to a dot
    # on the curve, so the correspondence is traced rather than asserted.
    for zc in TIE_Z:
        y = float(ymap(zc))
        xr = float(dens_x(float(density_hayne(zc / 100.0))))
        ax.plot([GAP_L, xr], [y, y], color=_shade(C_DIM, 0.38), lw=0.6,
                ls=(0, (1.4, 1.6)), zorder=4)
        ax.plot([xr], [y], marker="o", ms=3.0, color=DARK, mec=PAPER, mew=0.5,
                zorder=6)
        tag = f"{zc:.0f}" + ("  ($H$)" if abs(zc - HAYNE["H"] * 100.0) < 0.1
                             else "")
        ax.text(GAP_L + 0.03, y, tag, color=C_DIM, fontsize=7.0, ha="left",
                va="center", zorder=7, bbox=HALO)


def draw_texture_notes(ax):
    """The two sentences the pairing exists to make."""
    y0 = float(ymap(Z_COMPACT))
    ax.text(NOTE_X, 0.5 * (Y_TOP + y0),
            "grains loosen upward\n"
            r"as $\rho$ falls — the whole" "\n"
            rf"change is above {Z_COMPACT:.0f} cm",
            color=DARK, fontsize=8.0, ha="left", va="center", linespacing=1.45)
    ax.text(NOTE_X, 0.5 * (y0 + Y_BOT),
            r"below it $\rho$ is constant," "\n"
            "so the packing stops\nchanging as well",
            color=C_DIM, fontsize=8.0, ha="left", va="center", linespacing=1.45)


def main() -> None:
    family, cambria = setup_fonts()
    apply_style(family, cambria)

    fig = plt.figure(figsize=(W, H))
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, W)
    ax.set_ylim(0, H)
    ax.axis("off")

    mid = draw_block(ax)
    g = draw_grid_half(ax)
    draw_fluxes(ax, mid)
    draw_density(ax)
    draw_shared_band(ax)          # a light wash, over both panels, drawn last
    draw_grid_notes(ax, g)
    draw_probes(ax)
    draw_kpanel(ax)
    draw_bc_labels(ax)

    fig.canvas.draw()
    FIGS.mkdir(parents=True, exist_ok=True)
    with plt.rc_context({"savefig.pad_inches": 0.02}):
        fig.savefig(FIGS / "fig_intro_column.pdf")
        fig.savefig(FIGS / "fig_intro_column.png", dpi=300)
    plt.close(fig)
    print(f"  wrote figures/fig_intro_column.pdf + .png "
          f"({W:.2f} x {H:.2f} in, landscape)")
    print("  grain radius AND count both computed from rho(z); tie lines at "
          + ", ".join(f"{z:.0f}" for z in TIE_Z) + " cm")
    print(f"  shared compaction band: surface to {Z_COMPACT:.0f} cm — the "
          "boundary-condition equations are left to the document")


if __name__ == "__main__":
    main()
