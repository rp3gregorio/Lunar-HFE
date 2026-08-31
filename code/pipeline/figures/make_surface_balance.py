#!/usr/bin/env python3
"""The surface energy balance, drawn: what happens to sunlight when it lands.

Built to the rev-2 illustration brief. A lit, dimensional cutaway -- not a flat
schematic -- of one square metre of Apollo 15 regolith at local noon, with the
five fluxes that make up the surface boundary condition and the equation they
add up to.

RENDERING. One light source, the Sun in the picture, upper left; every shadow
falls down-right. The excavated ground is a BLOCK: a lit top face receding in
slight perspective plus a shaded cut face, on a soft ground shadow. Grains are
shaded solids (offset highlight, darker rim, contact shadow), loose and large at
the surface and small and crowded with depth, because bulk density runs
1100 -> 1800 kg/m^3 on a 6 cm scale. The grains are INDICATIVE, not to scale:
real regolith grains are microscopic and would be invisible here.

TYPOGRAPHY. Equations are set as PowerPoint sets them -- Cambria Italic for
variables, Cambria Math for symbols and brackets, Cambria upright for digits and
units. Cambria Math alone renders every variable upright, which reads as visibly
not-PowerPoint, so the italic has to come from Cambria Italic. The faces are
lifted from the local Microsoft Office install at build time and never committed;
without Office the figure falls back to STIX Two Math and says so.

WHY THE SCATTER IS A FAN. Regolith is a rough, dusty scatterer, not a mirror. A
single specular bounce would be wrong and would teach the wrong thing.

WHY THE OUTGOING HEAT IS WAVY AND COOL. It is not reflected sunlight; it is new
radiation the 374 K ground emits, peaking near 8 um against sunlight's 0.5 um.
Straight and warm = light arriving. Wavy and cool = heat leaving.

Every number is live, from the converged solve at the retrieved K_d*:
    incident   1222 W/m^2   = S_0 cos(26.13 deg), the site latitude
    scattered   160          = A * S,  A = 0.131  (Vasavada 2012)
    absorbed   1062          = (1 - A) * S
    radiated   1050          = eps sigma T_s^4,  T_s = 373.7 K, eps = 0.95
    conducted    12          = the remainder, 1.1 % of what was absorbed

Outputs: figures/fig_surface_balance.pdf (+ .png at 300 dpi)
Run:     python code/pipeline/figures/make_surface_balance.py
"""
from __future__ import annotations

import pathlib
import sys
import tempfile

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib import font_manager as fm
from matplotlib.colors import LinearSegmentedColormap, to_rgb
from matplotlib.patches import Circle, Ellipse, FancyArrowPatch, Polygon

_REPO = pathlib.Path(__file__).resolve().parents[1].parent
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))
sys.path.insert(0, str(_REPO / "src"))

from lunar.config import SITES, S0
from lunar.constants import SIGMA_SB
from lunar.plotting.style import (JGR_FULL, C_CHAR, C_CORAL, C_DIM, C_TEAL,
                                 assert_no_overlap)

FIGS = _REPO.parent / "figures"

W, H = JGR_FULL, JGR_FULL / 2.0          # 7.48 x 3.74 in, the brief's 2:1

# ---- palette: the thesis four, plus lightened/darkened shades of them -------
WARM, COOL, DARK = C_CORAL, C_TEAL, C_CHAR
GROUND_LIT = "#E8D8BE"       # the top face, catching the Sun
GROUND_MID = "#D6C0A0"       # the cut face, upper
GROUND_DEEP = "#A98D6B"      # the cut face, at depth
GRAIN_FACE = "#E4D2B4"
GRAIN_HI = "#F6EEDF"
GRAIN_RIM = "#9C8264"
PAPER = "#FFFFFF"


def _shade(hex_color: str, f: float) -> tuple:
    """Lighten (f>0) or darken (f<0) a colour without leaving the palette."""
    r, g, b = to_rgb(hex_color)
    if f >= 0:
        return (r + (1 - r) * f, g + (1 - g) * f, b + (1 - b) * f)
    return (r * (1 + f), g * (1 + f), b * (1 + f))


# ---- geometry, all in inches on the fixed canvas ----------------------------
BLK_L, BLK_R = 0.50, 3.10        # the front cut face; the side face adds SHEAR_X
Y_TOP, Y_BOT = 2.06, 0.44        # its top and bottom edges
SHEAR_X, SHEAR_Y = 0.26, 0.20    # how far the top face recedes
IMPACT = (1.30, 2.18)            # where the sunbeam lands, on the top face
SUN = (0.80, 3.34)
SUN_R = 0.105
# Thermal emission leaves the WHOLE surface, not the beam's impact point -- it is
# not scattered sunlight, it is the warm ground glowing. Drawing it from several
# points is both more correct and what untangles it from the scatter fan.
EMIT_X = (1.78, 2.18, 2.58, 2.94)
Y_CONDUCT = 1.95                 # where the conducted arrow starts
X_CONDUCT = 2.48

KEY_X = 3.90                     # the right-hand column
KEY_TEXT = 4.16
RIGHT_EDGE = 7.32


def setup_fonts() -> tuple[str, bool]:
    """Register Cambria + Cambria Math from the local Office install.

    Returns (family_name, is_cambria). Cambria Math lives as face 1 of a .ttc,
    which matplotlib will not address directly, so both faces are extracted to a
    throwaway directory. Nothing is written into the repository.
    """
    dfonts = pathlib.Path("/Applications/Microsoft PowerPoint.app/Contents/"
                          "Resources/DFonts")
    ttc = dfonts / "Cambria.ttc"
    if not ttc.exists():
        return "STIX Two Text", False
    try:
        from fontTools.ttLib import TTCollection
    except ImportError:
        return "STIX Two Text", False

    tmp = pathlib.Path(tempfile.mkdtemp(prefix="cambria-"))
    coll = TTCollection(str(ttc))
    coll.fonts[0].save(str(tmp / "Cambria.ttf"))          # roman
    coll.fonts[1].save(str(tmp / "CambriaMath.ttf"))       # the MATH face
    for f in (tmp / "Cambria.ttf", tmp / "CambriaMath.ttf"):
        fm.fontManager.addfont(str(f))
    for name in ("Cambriai.ttf", "Cambriab.ttf", "Cambriaz.ttf"):
        if (dfonts / name).exists():
            fm.fontManager.addfont(str(dfonts / name))
    setup_fonts._keep = tmp                                # outlive savefig
    return "Cambria", True


def apply_style(family: str, cambria: bool) -> None:
    plt.rcParams.update({
        "font.family": "serif",
        "font.serif": [family, "STIX Two Text", "Times New Roman"],
        "mathtext.fontset": "custom",
        # variables italic, symbols and brackets from the MATH face: this pairing
        # is what makes it read as a PowerPoint equation rather than upright text
        "mathtext.it": f"{family}:italic" if cambria else "STIX Two Math:italic",
        "mathtext.rm": family if cambria else "STIX Two Math",
        "mathtext.bf": f"{family}:bold" if cambria else "STIX Two Math:bold",
        "mathtext.cal": f"{family}:italic" if cambria else "STIX Two Math:italic",
        "mathtext.default": "it",
        "text.color": DARK,
        "figure.facecolor": PAPER, "savefig.facecolor": PAPER,
    })


# ---- drawing helpers --------------------------------------------------------
def top_face_x(y: float) -> tuple[float, float]:
    """Left and right edges of the receding top face at height y."""
    t = np.clip((y - Y_TOP) / SHEAR_Y, 0.0, 1.0)
    return BLK_L + t * SHEAR_X, BLK_R + t * SHEAR_X


def draw_block(ax):
    """The excavated ground as a lit block: shadow, cut face, top face."""
    # soft ground shadow, faked with three offset polygons (no blur available)
    for i, (dx, dy, a) in enumerate(((0.10, -0.10, 0.05),
                                     (0.06, -0.06, 0.06),
                                     (0.03, -0.03, 0.07))):
        ax.add_patch(Polygon([(BLK_L + dx, Y_BOT + dy),
                              (BLK_R + dx, Y_BOT + dy),
                              (BLK_R + SHEAR_X + dx, Y_BOT + SHEAR_Y + dy),
                              (BLK_L + SHEAR_X + dx, Y_BOT + SHEAR_Y + dy)],
                             closed=True, facecolor=DARK, edgecolor="none",
                             alpha=a, zorder=1))

    # the cut face, deepening with depth
    grad = np.linspace(0, 1, 256)[:, None]
    ax.imshow(grad, cmap=LinearSegmentedColormap.from_list(
                  "cut", [GROUND_MID, GROUND_DEEP]),
              aspect="auto", origin="upper",
              extent=(BLK_L, BLK_R, Y_BOT, Y_TOP), vmin=0, vmax=1, zorder=2)
    # a fine irregular texture over it, felt rather than seen
    rng = np.random.default_rng(3)
    noise = rng.normal(0.0, 1.0, (140, 90))
    ax.imshow(noise, cmap="Greys", aspect="auto", origin="upper", alpha=0.05,
              extent=(BLK_L, BLK_R, Y_BOT, Y_TOP), zorder=3)

    # The RIGHT SIDE FACE. Without it the block reads as a flat card with a lid
    # on top: the cut has depth, and at this viewing angle that depth is visible.
    # It faces away from the Sun, so it is the darkest ground in the picture.
    ax.add_patch(Polygon([(BLK_R, Y_TOP), (BLK_R + SHEAR_X, Y_TOP + SHEAR_Y),
                          (BLK_R + SHEAR_X, Y_BOT + SHEAR_Y), (BLK_R, Y_BOT)],
                         closed=True, facecolor=_shade(GROUND_MID, -0.20),
                         edgecolor="none", zorder=3))
    # graded down its height like the front face, but a stop darker throughout
    for k in range(90):
        t0, t1 = k / 90, (k + 1) / 90
        yy0 = Y_TOP - t0 * (Y_TOP - Y_BOT)
        yy1 = Y_TOP - t1 * (Y_TOP - Y_BOT)
        col = _shade(GROUND_MID if t0 < 0.5 else GROUND_DEEP,
                     -0.18 - 0.16 * t0)
        ax.add_patch(Polygon([(BLK_R, yy0), (BLK_R + SHEAR_X, yy0 + SHEAR_Y),
                              (BLK_R + SHEAR_X, yy1 + SHEAR_Y), (BLK_R, yy1)],
                             closed=True, facecolor=col, edgecolor="none",
                             zorder=3))

    # the lit top face
    ax.add_patch(Polygon([(BLK_L, Y_TOP), (BLK_R, Y_TOP),
                          (BLK_R + SHEAR_X, Y_TOP + SHEAR_Y),
                          (BLK_L + SHEAR_X, Y_TOP + SHEAR_Y)],
                         closed=True, facecolor=GROUND_LIT,
                         edgecolor=_shade(GRAIN_RIM, -0.15), lw=0.7, zorder=4))
    # the two edges that describe the block's depth
    ax.plot([BLK_R, BLK_R + SHEAR_X], [Y_TOP, Y_TOP + SHEAR_Y],
            color=_shade(GRAIN_RIM, -0.3), lw=0.8, zorder=6)
    ax.plot([BLK_R + SHEAR_X, BLK_R + SHEAR_X],
            [Y_TOP + SHEAR_Y, Y_BOT + SHEAR_Y],
            color=_shade(GRAIN_RIM, -0.3), lw=0.8, zorder=6)
    ax.plot([BLK_R, BLK_R + SHEAR_X], [Y_BOT, Y_BOT + SHEAR_Y],
            color=_shade(GRAIN_RIM, -0.3), lw=0.8, zorder=6)
    # the front edge, the brightest line in the picture
    ax.plot([BLK_L, BLK_R], [Y_TOP, Y_TOP], color=_shade(GROUND_LIT, 0.45),
            lw=1.4, solid_capstyle="butt", zorder=6)
    ax.plot([BLK_L, BLK_L, BLK_R, BLK_R], [Y_TOP, Y_BOT, Y_BOT, Y_TOP],
            color=_shade(GRAIN_RIM, -0.25), lw=0.8, zorder=6)


def grain(ax, x, y, r, z=7, dim=0.0):
    """One shaded grain: contact shadow, body, offset highlight, darker rim.

    ``dim`` darkens the whole grain, for the side face that turns away from the
    Sun. The highlight stays up-left on every grain, because there is one light.
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


def draw_grains(ax):
    """Loose and large at the surface, small and crowded with depth.

    The 6 cm compaction scale is short, so the change is deliberately fast: it
    happens inside the top fifth of the cut, which is what the density profile
    actually does.
    """
    rng = np.random.default_rng(17)
    # Bands EVENLY spaced in y, not geometrically: geometric spacing left a bare
    # stripe across the middle of the cut and made the deep half look sparser
    # than the shallow half, which is backwards.
    n_band = 22
    for i in range(n_band):
        f = i / (n_band - 1)                     # 0 at the surface, 1 deep
        y0 = Y_TOP - 0.07 - f * (Y_TOP - Y_BOT - 0.14)
        rad = 0.050 - 0.033 * f ** 0.6
        n_g = int(round(8 + 26 * f))             # crowding grows with depth
        for _ in range(n_g):
            gx = rng.uniform(BLK_L + 1.3 * rad, BLK_R - 1.3 * rad)
            gy = y0 + rng.uniform(-0.038, 0.038)
            if not (Y_BOT + 1.2 * rad < gy < Y_TOP - 1.2 * rad):
                continue
            grain(ax, gx, gy, rad * rng.uniform(0.72, 1.16))

    # grains on the SIDE face, dimmed: it is the same cut ground seen edge-on,
    # and leaving it bare was what made the block look hollow
    for _ in range(52):
        t = rng.uniform(0.16, 0.82)          # inset, or grains spill past the edge
        yy = rng.uniform(Y_BOT + 0.07, Y_TOP - 0.06)
        depth_f = (Y_TOP - yy) / (Y_TOP - Y_BOT)
        rad = (0.038 - 0.024 * depth_f ** 0.6) * rng.uniform(0.7, 1.1)
        grain(ax, BLK_R + t * SHEAR_X, yy + t * SHEAR_Y, rad, z=4, dim=0.22)

    # grains on the lit top face, catching the Sun: bigger and brighter than the
    # ones in shadow, which is what sells the face as lit
    for _ in range(34):
        yy = rng.uniform(Y_TOP + 0.035, Y_TOP + SHEAR_Y - 0.035)
        xl, xr = top_face_x(yy)
        gx = rng.uniform(xl + 0.05, xr - 0.05)
        if abs(gx - IMPACT[0]) < 0.11:
            continue
        grain(ax, gx, yy, rng.uniform(0.026, 0.042), z=5)


def draw_sun(ax):
    sx, sy = SUN
    for k in range(14):                       # radial glow, quick falloff
        t = k / 13
        ax.add_patch(Circle((sx, sy), SUN_R * (1.0 + 3.4 * t ** 1.5),
                            facecolor=WARM, edgecolor="none",
                            alpha=0.055 * (1 - t) ** 1.4, zorder=8))
    ax.add_patch(Circle((sx, sy), SUN_R, facecolor=_shade(WARM, 0.18),
                        edgecolor="none", zorder=9))
    ax.add_patch(Circle((sx, sy), SUN_R * 0.55,
                        facecolor=_shade(WARM, 0.42), edgecolor="none",
                        zorder=9))


def draw_fluxes(ax):
    """The five terms of the surface boundary condition."""
    ix, iy = IMPACT
    sx, sy = SUN
    d = np.array([ix - sx, iy - sy])
    d /= np.hypot(*d)                          # unit vector, Sun -> impact
    perp = np.array([-d[1], d[0]])
    ang = np.degrees(np.arctan2(-d[1], -d[0])) # bearing back toward the Sun

    # (1) incoming: one arrow, plus short parallel strokes in its UPPER third
    # only. Running the parallel rays the whole way down to the impact point made
    # them cross the scatter fan, which shares that origin -- the beam read as
    # part of the starburst instead of as the thing being scattered.
    p0 = np.array([sx, sy]) + d * 0.30
    for off, a in ((-0.070, 0.50), (0.070, 0.50), (-0.035, 0.68), (0.035, 0.68)):
        q0 = p0 + perp * off
        q1 = p0 + d * 0.52 + perp * off
        ax.plot([q0[0], q1[0]], [q0[1], q1[1]], color=WARM, lw=0.9, alpha=a,
                solid_capstyle="round", zorder=10)
    ax.add_patch(FancyArrowPatch(tuple(p0), (ix, iy), color=WARM, lw=2.3,
                                 arrowstyle="-|>", mutation_scale=13,
                                 shrinkA=0, shrinkB=0, zorder=11))

    # (2) scattered: a DIFFUSE fan across the sky, longest near vertical and
    # shortest near grazing -- the shape of a rough scatterer, not a mirror. Rays
    # inside the incoming beam's own lane are skipped: overlaying them made the
    # fan read as a second beam instead of as scatter.
    for a_deg in np.linspace(14.0, 164.0, 11):
        if abs(a_deg - ang) < 15.0:
            continue
        th = np.radians(a_deg)
        ln = 0.30 + 0.34 * np.sin(th) ** 1.3      # longest near vertical
        v = np.array([np.cos(th), np.sin(th)])
        # start clear of the impact point: the absorbed arrowhead sits there, and
        # rays running right into it tied the whole thing into a knot
        ax.plot([ix + v[0] * 0.10, ix + v[0] * ln * 0.60],
                [iy + v[1] * 0.10, iy + v[1] * ln * 0.60],
                color=WARM, lw=0.9, alpha=0.75, solid_capstyle="round",
                zorder=10)
        ax.plot([ix + v[0] * ln * 0.56, ix + v[0] * ln],
                [iy + v[1] * ln * 0.56, iy + v[1] * ln],
                color=WARM, lw=0.9, alpha=0.30, solid_capstyle="round",
                zorder=10)

    # (3) absorbed: the only term that changes the ground's temperature
    ax.add_patch(FancyArrowPatch((ix, iy - 0.02), (ix, iy - 0.42),
                                 color=WARM, lw=3.0, arrowstyle="-|>",
                                 mutation_scale=15, shrinkA=0, shrinkB=0,
                                 zorder=12))

    # (4) radiated back out: wavy, cool, faint outer glow, rising from points
    # spread along the whole top face -- the surface glows everywhere it is warm
    for j, ex in enumerate(EMIT_X):
        a_deg = 96.0 - 9.0 * j                 # fanning gently to the right
        th = np.radians(a_deg)
        v = np.array([np.cos(th), np.sin(th)])
        n = np.array([-v[1], v[0]])
        s = np.linspace(0.0, 1.0, 180)
        L = 0.78 + 0.05 * (j % 2)
        ey = Y_TOP + 0.06 + 0.03 * (j % 2)
        pts = (np.array([ex, ey])[None, :] + v[None, :] * (s * L)[:, None]
               + n[None, :] * (0.032 * np.sin(s * 4.2 * np.pi)
                               * np.clip(s * 3, 0, 1))[:, None])
        ax.plot(pts[:, 0], pts[:, 1], color=COOL, lw=3.6, alpha=0.10,
                solid_capstyle="round", zorder=9)
        ax.plot(pts[:, 0], pts[:, 1], color=COOL, lw=1.5, alpha=0.95,
                solid_capstyle="round", zorder=10)
        ax.add_patch(FancyArrowPatch(tuple(pts[-6]), tuple(pts[-1]),
                                     color=COOL, lw=1.5, arrowstyle="-|>",
                                     mutation_scale=11, shrinkA=0, shrinkB=0,
                                     zorder=10))

    # (5) conducted down: 1.1 % of what was absorbed, and it must look like it
    ax.add_patch(FancyArrowPatch((X_CONDUCT, Y_CONDUCT),
                                 (X_CONDUCT, Y_CONDUCT - 0.52),
                                 color=DARK, lw=1.1, arrowstyle="-|>",
                                 mutation_scale=9, shrinkA=0, shrinkB=0,
                                 zorder=12))


def draw_scene_labels(ax, f):
    """Symbol AND number against each arrow.

    Bare numbers were not enough: the reader could see 1222 without knowing it
    was S(t), so the arrows never connected to the equation on the right. Symbol
    on top, number under it, keeps each label narrow enough to place.
    """
    ix, iy = IMPACT

    def tag(x, y, sym, num, col, ha="left"):
        ax.text(x, y + 0.115, sym, color=col, fontsize=11.0, ha=ha,
                va="center", zorder=14,
                bbox=dict(facecolor=PAPER, edgecolor="none", alpha=0.78,
                          pad=1.0))
        ax.text(x, y - 0.115, num, color=col, fontsize=9.5, ha=ha,
                va="center", zorder=14,
                bbox=dict(facecolor=PAPER, edgecolor="none", alpha=0.78,
                          pad=1.0))

    tag(1.12, 3.02, r"$S(t)$", f"{f['inc']:.0f}", WARM)
    tag(0.60, 2.62, r"$A\,S$", f"{f['ref']:.0f}", WARM, ha="right")
    # LEFT of the absorbed arrow. On its right it ran into the conducted label,
    # and assert_no_overlap only polices text-on-DATA, not text-on-text.
    tag(ix - 0.14, iy - 0.34, r"$(1{-}A)\,S$", f"{f['abs']:.0f}", WARM,
        ha="right")
    tag(2.46, Y_TOP + 1.10, r"$\varepsilon\sigma T_s^{4}$", f"{f['emit']:.0f}",
        COOL, ha="center")
    tag(X_CONDUCT - 0.13, Y_CONDUCT - 0.30, r"$K\,\partial T/\partial z$",
        f"{f['cond']:.0f}", DARK, ha="right")


def draw_key(ax, f, site):
    """How the boundary condition works: two equations, each with its arithmetic
    set directly underneath, term by term.

    This replaced a five-row legend. The legend restated what the scene labels
    now carry, and it never showed the thing that matters -- that the terms
    BALANCE, and that the balance is what determines the surface temperature.
    """
    def row(y, parts, size, num_size):
        """parts = [(x, symbol, number, colour), ...]; numbers sit under symbols."""
        for x, sym, num, col in parts:
            ax.text(x, y, sym, color=col, fontsize=size, ha="center",
                    va="center")
            if num is not None:
                ax.text(x, y - 0.30, num, color=col, fontsize=num_size,
                        ha="center", va="center")

    # (1) what arrives splits in two: the albedo is the split
    ax.text(KEY_X, 3.52, "the sunlight splits", color=C_DIM, fontsize=9.0,
            ha="left", va="center")
    row(3.16, [(4.28, r"$S(t)$", f"{f['inc']:.0f}", WARM),
               (4.86, r"$=$", r"$=$", DARK),
               (5.40, r"$A\,S$", f"{f['ref']:.0f}", WARM),
               (5.90, r"$+$", r"$+$", DARK),
               (6.60, r"$(1{-}A)\,S$", f"{f['abs']:.0f}", WARM)],
        13.0, 11.0)

    # (2) what is absorbed must leave again: this IS the boundary condition
    ax.text(KEY_X, 2.28, "what is absorbed must balance", color=C_DIM,
            fontsize=9.0, ha="left", va="center")
    row(1.92, [(4.52, r"$(1{-}A)\,S$", f"{f['abs']:.0f}", WARM),
               (5.30, r"$=$", r"$=$", DARK),
               (5.86, r"$\varepsilon\sigma T_s^{4}$", f"{f['emit']:.0f}", COOL),
               (6.32, r"$+$", r"$+$", DARK),
               (6.86, r"$K\,\partial T/\partial z$", f"{f['cond']:.0f}", DARK)],
        13.0, 11.0)

    ax.text(RIGHT_EDGE, 1.62, r"W m$^{\mathrm{-2}}$", color=C_DIM,
            fontsize=9.0, ha="right", va="center")
    ax.plot([KEY_X, RIGHT_EDGE], [1.40, 1.40], color=_shade(C_DIM, 0.72),
            lw=0.7)

    # (3) the one unknown in line 2, and how it is found
    ax.text(KEY_X, 1.14,
            r"Only $T_s$ is unknown — so the surface temperature is"
            "\nwhatever value makes that line balance.",
            color=DARK, fontsize=10.0, ha="left", va="center", linespacing=1.4)
    ax.text(KEY_X, 0.62,
            rf"$T_s={f['Ts']:.1f}$ K   at this instant, by Newton iteration",
            color=DARK, fontsize=11.0, ha="left", va="center")
    ax.text(KEY_X, 0.30,
            rf"$A={site['albedo']}$,   $\varepsilon={site['emissivity']}$,   "
            rf"and only {f['cond']/f['abs']*100:.1f}% of the absorbed flux "
            "goes downward",
            color=C_DIM, fontsize=9.0, ha="left", va="center")


def fluxes(key: str = "A15") -> dict:
    """The five numbers, from the converged periodic solve at K_d*."""
    site = SITES[key]
    cache = _REPO / "results" / "model_anatomy_cache.npz"
    if not cache.exists():
        # T_s at noon comes from a converged solve, so build the shared cache
        # rather than fail on a cold checkout. make_model_anatomy owns it.
        sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
        from make_model_anatomy import build_cache
        build_cache()
    with np.load(cache, allow_pickle=False) as z:
        S = z[f"{key}_insol"]
        Ts = z[f"{key}_Ts"]
    i = int(np.argmax(S))
    inc = float(S[i])
    ref = site["albedo"] * inc
    absd = inc - ref
    emit = site["emissivity"] * SIGMA_SB * float(Ts[i]) ** 4
    return dict(inc=inc, ref=ref, abs=absd, emit=emit, cond=absd - emit,
                Ts=float(Ts[i]))


def main() -> None:
    family, cambria = setup_fonts()
    apply_style(family, cambria)
    site = SITES["A15"]
    f = fluxes("A15")

    fig = plt.figure(figsize=(W, H))
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, W)
    ax.set_ylim(0, H)
    ax.axis("off")

    draw_block(ax)
    draw_grains(ax)
    draw_sun(ax)
    draw_fluxes(ax)
    draw_scene_labels(ax, f)
    draw_key(ax, f, site)

    fig.canvas.draw()
    assert_no_overlap(ax)
    FIGS.mkdir(parents=True, exist_ok=True)
    with plt.rc_context({"savefig.pad_inches": 0.02}):
        fig.savefig(FIGS / "fig_surface_balance.pdf")
        fig.savefig(FIGS / "fig_surface_balance.png", dpi=300)
    plt.close(fig)
    print(f"  wrote figures/fig_surface_balance.pdf + .png  ({W:.2f} x {H:.2f} in)")
    print(f"  equations set in: {family}" + ("" if cambria else
          "  (Office not found — fell back)"))
    print(f"  incident {f['inc']:.0f}  scattered {f['ref']:.0f}  "
          f"absorbed {f['abs']:.0f}  radiated {f['emit']:.0f}  "
          f"conducted {f['cond']:.1f} W/m2   T_s {f['Ts']:.1f} K")


if __name__ == "__main__":
    main()
