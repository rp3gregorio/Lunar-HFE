#!/usr/bin/env python3
"""Letter Figure 2: the model column, the Apollo probes in it, and its properties.

(a) A cutaway of the 5 m regolith column on a logarithmic depth axis. The cut
    face is shaded by density and carries grains whose size and number follow
    rho(z); its right part shows the 69 cells of the model grid. Arrows mark the
    heat flows: sunlight arriving, scattered and absorbed, heat radiated back
    out, heat conducted down, and the basal heat flow. The two borestems of each
    site are drawn at their sensor depths; the dashed line is the 80 cm border
    of the borestem zone.
(b) The density profile of Hayne et al. (2017), with the scale depth H.
(c) The Hayne and the Martinez & Siegler (2021) conductivities at 250 K.

All three panels share the depth axis. All text is at the letter's 11 pt, and
the figure is drawn at the text width.

Output: figures/fig_joint_intro_column.pdf (+ .png)
Run:    python code/pipeline/figures/make_intro_column.py
"""
from __future__ import annotations

import pathlib
import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import LinearSegmentedColormap, to_rgb
from matplotlib.patches import Circle, Ellipse, FancyArrowPatch, Polygon, Rectangle

_HERE = pathlib.Path(__file__).resolve().parent
_REPO = _HERE.parents[1]
for _p in (str(_REPO), str(_REPO / "src"), str(_HERE)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from lunar.apollo_helpers import extract_sensor_stability
from lunar.config import GRID, HAYNE, SITES
from lunar.constants import RHO_DEEP, RHO_SURFACE
from lunar.grid import make_geometric_grid
from lunar.plotting import style
from lunar.plotting.style import (C_A15_2, C_A17_2, C_CHAR, C_CORAL, C_DIM, C_FOREST,
                                  C_GRID, C_HAYNE_GLOBAL, C_MS, LS_HAYNE_GLOBAL, LS_MS)
from lunar.properties import conductivity_hayne, conductivity_martinez, density_hayne

FIGS = _REPO.parent / "figures"

W, H = 7.48, 4.36                      # drawing coordinates, in inches before scaling
SCALE = (style.TEXT_W - 0.10) / W      # the canvas is scaled to the text width
PT = style.DOC_PT                      # every text at the letter's body size

# colours: green and coral are the sites, teal and violet the models, so the
# schematic uses gold for sunlight and grey for emitted heat
WARM, COOL, DARK = "#C99A2E", C_DIM, C_CHAR
GROUND_LIT = "#E8D8BE"                 # the lit top face
GROUND_MID = "#D6C0A0"                 # the cut face, near the surface
GROUND_DEEP = "#A98D6B"                # the cut face, at depth
GRAIN_FACE, GRAIN_HI, GRAIN_RIM = "#E4D2B4", "#F6EEDF", "#9C8264"
PAPER = "#FFFFFF"

# ---- layout, in drawing inches -----------------------------------------------
BLK_L, BLK_R = 0.68, 3.32              # the front face of the block
SHEAR_X, SHEAR_Y = 0.26, 0.17          # how far the top and side faces recede
X_SPLIT = 0.68 + 0.66 * (3.32 - 0.68)  # material (left) | grid (right)
DENS_L, DENS_R = 4.16, 5.24            # panel (b)
KPAN_L, KPAN_R = 5.86, 7.06            # panel (c)
Y_TOP, Y_BOT = 3.00, 0.52
SUN, SUN_R = (1.05, 3.90), 0.090
IMPACT = (1.34, 3.09)                  # where the sunbeam meets the surface
EMIT_X = (1.88, 2.32, 2.74)
X_CONDUCT = 1.88

Z_TOP, Z_BOT = 0.5, 500.0              # cm, the depth axis
TICKS = [(1, "1"), (10, "10"), (100, "100"), (500, "500")]
BORESTEM_CM = SITES["A15"]["MIN_DEPTH_CM"]   # 80 cm, the border of the borestem zone
K_LO, K_HI = 0.0, 9.0                  # mW m^-1 K^-1, the span of panel (c)

HALO = dict(facecolor=PAPER, edgecolor="none", alpha=0.80, pad=1.2)
ARROW = dict(arrowstyle="-|>", mutation_scale=11, lw=1.8, shrinkA=0, shrinkB=0)


def apply_style() -> None:
    plt.rcParams.update({
        "font.family": "serif",
        "font.serif": ["Times", "STIX Two Text", "Times New Roman"],
        "mathtext.fontset": "custom",
        "mathtext.it": "STIX Two Math:italic",
        "mathtext.rm": "STIX Two Math",
        "mathtext.bf": "STIX Two Math:bold",
        "mathtext.cal": "STIX Two Math:italic",
        "mathtext.default": "it",
        "text.color": DARK,
        "figure.facecolor": PAPER, "savefig.facecolor": PAPER,
    })
    plt.rcParams.update({"mathtext.fontset": "stix", "pdf.fonttype": 42})


def _shade(hex_color: str, f: float) -> tuple:
    """Lighten (f > 0) or darken (f < 0) a colour."""
    r, g, b = to_rgb(hex_color)
    if f >= 0:
        return (r + (1 - r) * f, g + (1 - g) * f, b + (1 - b) * f)
    return (r * (1 + f), g * (1 + f), b * (1 + f))


def _blend(c0, c1, t):
    a = np.array(to_rgb(c0)); b = np.array(to_rgb(c1))
    return tuple(a + (b - a) * float(np.clip(t, 0.0, 1.0)))


def grain(ax, x, y, r, z=7, dim=0.0):
    """One shaded grain: contact shadow, body, highlight and rim.

    ``dim`` darkens the grain, for the side face that turns away from the Sun.
    """
    ax.add_patch(Ellipse((x + 0.22 * r, y - 0.80 * r), 1.7 * r, 0.5 * r,
                         facecolor=DARK, edgecolor="none", alpha=0.13,
                         zorder=z))
    ax.add_patch(Circle((x, y), r, facecolor=_shade(GRAIN_FACE, -dim),
                        edgecolor="none", zorder=z + 1))
    ax.add_patch(Circle((x - 0.26 * r, y + 0.26 * r), 0.60 * r,
                        facecolor=_shade(GRAIN_HI, -dim), edgecolor="none",
                        alpha=0.60, zorder=z + 2))
    ax.add_patch(Circle((x, y), r, facecolor="none",
                        edgecolor=_shade(GRAIN_RIM, -0.1 - dim), lw=0.45,
                        zorder=z + 3))


def ymap(z_cm):
    """Depth (cm) to drawing y, on the shared logarithmic axis."""
    z = np.clip(np.asarray(z_cm, dtype=float), Z_TOP, Z_BOT)
    return Y_TOP - (Y_TOP - Y_BOT) * (np.log10(z / Z_TOP)
                                      / np.log10(Z_BOT / Z_TOP))


def zmap(y):
    """Inverse of ymap: the depth (cm) a y-coordinate stands for."""
    frac = (Y_TOP - np.asarray(y, dtype=float)) / (Y_TOP - Y_BOT)
    return Z_TOP * 10.0 ** (frac * np.log10(Z_BOT / Z_TOP))


def compaction(y):
    """0 at the loosest surface, 1 at the deep density: the shade of the cut face."""
    rho = density_hayne(zmap(y) / 100.0)
    lo, hi = float(density_hayne(np.array([Z_TOP / 100.0]))[0]), RHO_DEEP
    return np.clip((rho - lo) / (hi - lo), 0.0, 1.0)


def dens_x(rho):
    return DENS_L + (np.asarray(rho) - 1050.0) / 800.0 * (DENS_R - DENS_L)


def kx(k_mW):
    return KPAN_L + (np.asarray(k_mW) - K_LO) / (K_HI - K_LO) * (KPAN_R - KPAN_L)


def draw_block(ax):
    for dx, dy, a in ((0.09, -0.09, 0.05), (0.05, -0.05, 0.06),
                      (0.02, -0.02, 0.07)):           # the shadow under the block
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

    # grains: their number and size follow the density profile
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
            fontsize=PT, ha="right", va="center", linespacing=1.2)
    for zc, lab in TICKS:
        y = float(ymap(zc))
        ax.plot([BLK_L - 0.05, BLK_L], [y, y], color=C_DIM, lw=0.6, zorder=6)
        ax.text(BLK_L - 0.08, y, lab, color=C_DIM, fontsize=PT, ha="right",
                va="center")


def draw_grid_half(ax):
    """The right part of the block: the faces of the model's 69 cells, to scale.

    Unlike the material, the grid is drawn on a LINEAR depth scale from the
    surface to the base of the column, with its own metre ticks, so the cells
    show their true sizes: the 2 mm cells at the top crowd into a thin band and
    each cell below is 8 % thicker than the one above it, up to 37 cm at the
    base. (On the shared log axis the deep cells looked the most crowded.)
    """
    g = make_geometric_grid(**GRID)
    zf = g.z_face
    span = Y_TOP - Y_BOT

    def yz(z):                                # z in m, linear over the column
        return float(Y_TOP - span * z / zf[-1])

    for i in range(zf.size - 1):
        t = (Y_TOP - yz(zf[i])) / span
        ax.add_patch(Rectangle((X_SPLIT, yz(zf[i + 1])), BLK_R - X_SPLIT,
                               yz(zf[i]) - yz(zf[i + 1]),
                               facecolor=_shade(GROUND_MID, 0.26 - 0.42 * t),
                               edgecolor=_shade(C_DIM, 0.08), lw=0.3,
                               zorder=7.2))
    ax.plot([X_SPLIT, X_SPLIT], [Y_BOT, Y_TOP], color=_shade(C_CHAR, 0.15),
            lw=1.1, zorder=7.6)

    # the labels sit on the cell faces: a light halo lets the faces show through
    halo = dict(HALO, alpha=0.45)
    # below the band of 2 mm cells, with a short pointer up to it, so the band stays visible
    ax.annotate(rf"$\Delta z={g.dz[0]*1e3:.0f}$ mm", xy=(X_SPLIT + 0.16, Y_TOP - 0.03),
                xytext=(X_SPLIT + 0.05, Y_TOP - 0.26), color=COOL, fontsize=PT,
                ha="left", va="center", zorder=13, bbox=halo,
                arrowprops=dict(arrowstyle="-|>", color=COOL, lw=0.8, shrinkA=0, shrinkB=0,
                                mutation_scale=7))
    ax.text(X_SPLIT + 0.05, Y_BOT + 0.05,
            rf"$\Delta z={g.dz[-1]*100:.0f}$ cm", color=COOL, fontsize=PT,
            ha="left", va="bottom", zorder=13, bbox=halo)
    # the strip's own linear depth ticks (m), inside its right edge
    for zm in (1, 2, 3, 4):
        y = yz(zm)
        ax.plot([BLK_R - 0.05, BLK_R], [y, y], color=_shade(C_CHAR, 0.15), lw=0.8, zorder=12)
        ax.text(BLK_R - 0.07, y, f"{zm} m", color=COOL, fontsize=PT, ha="right",
                va="center", zorder=13, bbox=halo)
    return g


def draw_grid_notes(ax, g):
    ax.text(0.5 * (BLK_L + X_SPLIT), Y_BOT - 0.09,
            "the material", color=C_CHAR, fontsize=PT, ha="center",
            va="top")
    ax.text(0.5 * (X_SPLIT + BLK_R), Y_BOT - 0.09,
            f"the grid, to scale\n{g.n_layers} cells", color=C_CHAR, fontsize=PT,
            ha="center", va="top", linespacing=1.15)


def draw_fluxes(ax):
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

    # arriving sunlight: one arrow, with parallel strokes in its upper third
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

    # radiated back out: wavy, from along the whole surface
    for j, ex in enumerate(EMIT_X):
        th = np.radians(95 - 8 * j)
        v = np.array([np.cos(th), np.sin(th)])
        n = np.array([-v[1], v[0]])
        s = np.linspace(0, 1, 150)
        L = 0.58 + 0.04 * (j % 2)
        # the wiggle fades in from the surface and out before the tip, so the
        # head points along v
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

    # conducted downward
    ax.add_patch(FancyArrowPatch((X_CONDUCT, Y_TOP - 0.14),
                                 (X_CONDUCT, Y_TOP - 0.58),
                                 color=DARK, lw=1.0, arrowstyle="-|>",
                                 mutation_scale=8, shrinkA=0, shrinkB=0,
                                 zorder=12))

    # the basal heat flow, arriving at the base
    ax.add_patch(FancyArrowPatch((BLK_L + 0.16, Y_BOT - 0.28),
                                 (BLK_L + 0.16, Y_BOT + 0.16),
                                 color=C_CHAR, zorder=10, **ARROW))

    # the 80 cm border of the borestem zone, between the open and the filled sensors
    y_cut = float(ymap(BORESTEM_CM))
    ax.plot([BLK_L, X_SPLIT], [y_cut, y_cut], color=C_DIM,
            lw=0.8, ls=(0, (2.4, 2.0)), zorder=12)
    ax.text(X_SPLIT - 0.04, y_cut + 0.03, f"{BORESTEM_CM:.0f} cm",
            color=C_DIM, fontsize=PT, ha="right", va="bottom",
            zorder=13, bbox=HALO)


# one borestem per probe, in the probe colours of letter Figure 1;
# Apollo 15 left of the sunlight arrow, Apollo 17 right of it
PROBE_LANES = {"a15": ((BLK_L + 0.24, BLK_L + 0.37), (C_FOREST, C_A15_2), "A15"),
               "a17": ((BLK_L + 0.90, BLK_L + 1.03), (C_CORAL, C_A17_2), "A17")}


def draw_probes(ax):
    """The borestems at their real sensor depths.

    Each is a pale drill casing with the probe rod inside, a head box at the
    surface, and the thermometers as beads on the rod: gradient bridges (TG)
    as circles, ring bridges (TR) as squares, filled where the sensor enters
    the fit and open in the borestem zone. The thermocouples on the cable never
    enter the analysis and are left out. Each rod is numbered below its end.
    """
    for mis, (xs, cols, lab) in PROBE_LANES.items():
        o = extract_sensor_stability(mis, int(BORESTEM_CM))
        d_all = np.asarray(o["depth_cm_all"], dtype=float)
        m_all = np.asarray(o["deep_mask"], dtype=bool)
        probe = np.array([s["probe"] for s in o["sensors"]])
        stype = np.asarray(o["stype_all"])
        assert np.allclose([s["depth_cm"] for s in o["sensors"]], d_all)
        ends = []
        for p, x, col in zip((1, 2), xs, cols):
            k = (probe == p) & (stype != "TC")
            d, m, ty = d_all[k], m_all[k], stype[k]
            y_s, y_e = float(ymap(Z_TOP)), float(ymap(d.max()))
            ends.append(y_e)

            # the drilled casing, the probe rod inside it, its closed nose
            ax.plot([x, x], [y_s, y_e], color=PAPER, lw=5.2, alpha=0.85,
                    solid_capstyle="round", zorder=12.6)
            ax.plot([x, x], [y_s, y_e], color=_shade(col, 0.55), lw=4.4,
                    alpha=0.55, solid_capstyle="round", zorder=12.7)
            ax.plot([x, x], [y_s, y_e], color=_shade(col, -0.10), lw=1.5,
                    alpha=0.95, solid_capstyle="round", zorder=13)
            ax.plot([x], [y_e], marker="v", ms=3.4, color=_shade(col, -0.25),
                    zorder=13.5)
            # the head box, on the surface
            ax.add_patch(Rectangle((x - 0.055, y_s), 0.11, 0.075,
                                   facecolor=_shade(col, 0.30),
                                   edgecolor=_shade(col, -0.25), lw=0.6,
                                   zorder=13.6))

            for t, mk, size in (("TG", "o", 13), ("TR", "s", 11)):
                u, x_ = m & (ty == t), ~m & (ty == t)
                ax.scatter(np.full(int(u.sum()), x), ymap(d[u]), s=size, marker=mk,
                           facecolor=col, edgecolor=PAPER, linewidth=0.6, zorder=14)
                ax.scatter(np.full(int(x_.sum()), x), ymap(d[x_]), s=size, marker=mk,
                           facecolor=PAPER, edgecolor=col, linewidth=0.8, zorder=14)
            ax.text(x, y_e - 0.07, str(p), color=_shade(col, -0.2), fontsize=PT,
                    ha="center", va="top", zorder=15, bbox=dict(HALO, pad=0.3))

        # the site, beside the pair, level with its deeper end
        ax.text(xs[1] + 0.13, min(ends), lab,
                color=_shade(cols[0], -0.2), fontsize=PT, linespacing=1.35,
                ha="left", va="center", zorder=15, bbox=HALO)


def draw_depth_axis(ax, x_l, x_r):
    """The depth ticks repeated on the left of panels (b) and (c), with faint guides."""
    ax.plot([x_l, x_l], [Y_BOT, Y_TOP], color=C_DIM, lw=0.6, zorder=3)
    for zc, lab in TICKS:
        y = float(ymap(zc))
        ax.plot([x_l, x_r], [y, y], color=C_GRID, lw=0.6, zorder=1.5)
        ax.plot([x_l - 0.05, x_l], [y, y], color=C_DIM, lw=0.6, zorder=6)
        ax.text(x_l - 0.08, y, lab, color=C_DIM, fontsize=PT, ha="right",
                va="center", zorder=6)


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
        ax.text(xv, Y_TOP + 0.06, f"{v}", color=C_DIM, fontsize=PT,
                ha="center", va="bottom")
    ax.text(0.5 * (DENS_L + DENS_R), Y_TOP + 0.24,
            r"$\rho$ (kg m$^{\mathrm{-3}}$)", color=C_DIM, fontsize=PT,
            ha="center", va="bottom")
    draw_depth_axis(ax, DENS_L, DENS_R)
    # H marked on the curve, its label above and right of the dot
    zh = HAYNE["H"] * 100.0
    xh, yh = float(dens_x(float(density_hayne(zh / 100.0)))), float(ymap(zh))
    ax.plot([xh], [yh], marker="o", ms=3.0, color=DARK, mec=PAPER, mew=0.5, zorder=6)
    ax.text(xh + 0.06, yh + 0.02, rf"$H$ = {zh:.0f} cm", color=C_DIM, fontsize=PT,
            ha="left", va="bottom", zorder=7, bbox=HALO)


def draw_kpanel(ax):
    """The two conductivity models against depth, at 250 K, the mean deep temperature."""
    zz = np.geomspace(Z_TOP, Z_BOT, 400)
    T = np.full_like(zz, 250.0)
    kh = conductivity_hayne(T, zz / 100.0) * 1e3
    km = conductivity_martinez(T, zz / 100.0) * 1e3

    ax.plot([kx(K_LO), kx(K_HI)], [Y_TOP, Y_TOP], color=C_GRID, lw=0.8, zorder=3)
    ax.plot(kx(kh), ymap(zz), color=C_HAYNE_GLOBAL, lw=1.7, ls=LS_HAYNE_GLOBAL,
            zorder=5)
    ax.plot(kx(km), ymap(zz), color=C_MS, lw=1.7, ls=LS_MS,
            solid_capstyle="round", zorder=5)

    for v in (0, 3, 6, 9):
        ax.plot([kx(v), kx(v)], [Y_TOP, Y_TOP + 0.055], color=C_DIM, lw=0.7,
                zorder=4)
        ax.text(kx(v), Y_TOP + 0.09, f"{v:g}", color=C_DIM, fontsize=PT,
                ha="center", va="bottom", zorder=6)
    ax.text(0.5 * (KPAN_L + KPAN_R), Y_TOP + 0.30,
            r"$K$ at 250 K" "\n" r"(mW m$^{\mathrm{-1}}$ K$^{\mathrm{-1}}$)", color=C_CHAR,
            fontsize=PT, ha="center", va="bottom", zorder=6)

    draw_depth_axis(ax, KPAN_L, KPAN_R)
    ax.text(kx(3.6), ymap(0.75), "Hayne", color=_shade(C_HAYNE_GLOBAL, -0.3), fontsize=PT,
            ha="left", va="center", zorder=7, bbox=HALO)
    ax.text(kx(4.4), ymap(2.3), "Martínez\n& Siegler", color=C_MS,
            fontsize=PT, ha="left", va="center", zorder=7, bbox=HALO)


def draw_panel_labels(ax):
    """(a), (b), (c) in one row above the panels, over their depth tick labels."""
    for lab, x_l in (("(a)", BLK_L), ("(b)", DENS_L), ("(c)", KPAN_L)):
        ax.text(x_l - 0.42, Y_TOP + 1.00, lab, color=C_CHAR, fontsize=PT,
                fontweight="bold", ha="left", va="top", zorder=15)


def main(out_stem: str = "fig_joint_intro_column") -> None:
    apply_style()
    fig = plt.figure(figsize=(W * SCALE, H * SCALE))
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, W)
    ax.set_ylim(0, H)
    ax.axis("off")

    draw_block(ax)
    g = draw_grid_half(ax)
    draw_fluxes(ax)
    draw_density(ax)
    draw_grid_notes(ax, g)
    draw_probes(ax)
    draw_kpanel(ax)
    draw_panel_labels(ax)

    fig.canvas.draw()
    FIGS.mkdir(parents=True, exist_ok=True)
    with plt.rc_context({"savefig.pad_inches": 0.02}):
        fig.savefig(FIGS / f"{out_stem}.pdf")
        fig.savefig(FIGS / f"{out_stem}.png", dpi=300)
    plt.close(fig)
    print(f"  wrote figures/{out_stem}.pdf + .png ({W * SCALE:.2f} x {H * SCALE:.2f} in)")


if __name__ == "__main__":
    main()
