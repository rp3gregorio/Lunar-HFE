#!/usr/bin/env python3
"""The whole column, both boundaries, and how K_d is actually found.

Companion to make_surface_balance.py, which is a close-up of the top few
centimetres. This one pulls back to the full 5 m and answers the questions that
close-up cannot: what holds the bottom, how the ground compacts on the way down,
where the daily temperature swing stops, and how a number for K_d comes out.

Four devices, deliberately different from one another so the eye has somewhere
to go:

  A  a lit block cutaway of the whole column, log depth axis, with the diurnal
     skin and the Apollo sensor zone banded, and the basal flux arriving below;
  B  the real density profile beside it on the same depth axis -- the compaction;
  C  the two boundary conditions as equations, top and bottom;
  D  the retrieval itself: the measured RMSE(K_d) bowls, one per site, with the
     vertex that defines K_d*.

THE ARGUMENT THE FIGURE MAKES. The daily wave dies within the top half-metre.
Below that the profile is a straight line whose slope is Q_b/K. The Apollo
sensors sit at 84-139 cm, under the dead wave, so what they measure is that
slope -- and since Q_b is known, the slope gives K. Sweep K_d, compare with the
sensors, take the minimum. That is the whole method, and D is a picture of it.

Every number is live:
    diurnal skin      1/e of the surface swing at 5.1 cm; amplitude under
                      0.1 K below 54 cm and under 0.01 K below 80 cm
    sensors           7 at 84-139 cm (A15), from the restored record
    density           1100 -> 1800 kg/m^3 on the 6 cm compaction scale
    Q_b               21 / 16 mW/m^2 (Langseth 1976)
    RMSE bowls        results/kd_retrieval_results.json, 29 and 32 swept values
    K_d*              4.60 / 7.08 mW/m/K

Outputs: figures/fig_column_and_retrieval.pdf (+ .png at 300 dpi)
Run:     python code/pipeline/figures/make_column_and_retrieval.py
"""
from __future__ import annotations

import json
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
for p in (str(_REPO), str(_REPO / "src"), str(_HERE)):
    if p not in sys.path:
        sys.path.insert(0, p)

from lunar.apollo_helpers import extract_sensor_stability
from lunar.config import HAYNE, SITES
from lunar.plotting.style import (JGR_FULL, C_A15, C_A17, C_CHAR, C_CORAL,
                                  C_DIM, C_FOREST, C_GRID, C_TEAL)
from lunar.properties import density_hayne

from make_surface_balance import (GRAIN_RIM, GROUND_DEEP, GROUND_LIT,
                                  GROUND_MID, PAPER, _shade, apply_style,
                                  grain, setup_fonts)

FIGS = _REPO.parent / "figures"

W, H = JGR_FULL, 5.90

WARM, COOL, DARK = C_CORAL, C_TEAL, C_CHAR
BAND_SKIN = "#F7E2D8"          # the diurnal skin, a warm wash
BAND_SENS = "#E3EDE5"          # the sensor zone, a cool wash

# ---- x budget (inches) ------------------------------------------------------
BLK_L, BLK_R = 0.66, 2.46
SHEAR_X, SHEAR_Y = 0.24, 0.19
DENS_L, DENS_R = 3.06, 3.74
EQ_X = 4.10
BOWL = [4.72, 0.72, 2.42, 2.06]   # left, bottom, width, height of the D axes
RIGHT_EDGE = 7.34

# ---- y budget (inches) ------------------------------------------------------
Y_TOP, Y_BOT = 4.52, 0.86
SUN, SUN_R = (0.98, 5.44), 0.085
Y_EQ_SURF, Y_EQ_BASE = 5.40, 4.50

Z_TOP, Z_BOT = 0.5, 500.0
TICKS = [(1, "1"), (10, "10"), (100, "100"), (500, "500")]

# measured from the converged cycle (see the amplitude scan in __main__ notes)
Z_SKIN_E = 5.1          # cm, where the swing falls to 1/e of the surface value
Z_SKIN_DEAD = 54.0      # cm, where it falls under 0.1 K

HALO = dict(facecolor=PAPER, edgecolor="none", alpha=0.80, pad=1.2)
ARROW = dict(arrowstyle="-|>", mutation_scale=11, lw=1.8, shrinkA=0, shrinkB=0)


def ymap(z_cm):
    z = np.clip(np.asarray(z_cm, dtype=float), Z_TOP, Z_BOT)
    return Y_TOP - (Y_TOP - Y_BOT) * (np.log10(z / Z_TOP)
                                      / np.log10(Z_BOT / Z_TOP))


# ============================================================ A: the block
def draw_block(ax, sens_cm):
    mid = 0.5 * (BLK_L + BLK_R)

    for dx, dy, a in ((0.09, -0.09, 0.05), (0.05, -0.05, 0.06),
                      (0.02, -0.02, 0.07)):
        ax.add_patch(Polygon([(BLK_L + dx, Y_BOT + dy), (BLK_R + dx, Y_BOT + dy),
                              (BLK_R + SHEAR_X + dx, Y_BOT + SHEAR_Y + dy),
                              (BLK_L + SHEAR_X + dx, Y_BOT + SHEAR_Y + dy)],
                             closed=True, facecolor=DARK, edgecolor="none",
                             alpha=a, zorder=1))

    grad = np.linspace(0, 1, 256)[:, None]
    ax.imshow(grad, cmap=LinearSegmentedColormap.from_list(
                  "cut", [GROUND_MID, GROUND_DEEP]),
              aspect="auto", origin="upper",
              extent=(BLK_L, BLK_R, Y_BOT, Y_TOP), vmin=0, vmax=1, zorder=2)

    # the side face, graded and a stop darker: it turns away from the Sun
    for k in range(80):
        t0, t1 = k / 80, (k + 1) / 80
        y0 = Y_TOP - t0 * (Y_TOP - Y_BOT)
        y1 = Y_TOP - t1 * (Y_TOP - Y_BOT)
        col = _shade(GROUND_MID if t0 < 0.5 else GROUND_DEEP,
                     -0.18 - 0.16 * t0)
        ax.add_patch(Polygon([(BLK_R, y0), (BLK_R + SHEAR_X, y0 + SHEAR_Y),
                              (BLK_R + SHEAR_X, y1 + SHEAR_Y), (BLK_R, y1)],
                             closed=True, facecolor=col, edgecolor="none",
                             zorder=3))

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

    # --- the two banded regions, drawn UNDER the grains ---------------------
    y_dead = float(ymap(Z_SKIN_DEAD))
    ax.add_patch(Rectangle((BLK_L, y_dead), BLK_R - BLK_L, Y_TOP - y_dead,
                           facecolor=BAND_SKIN, edgecolor="none", alpha=0.42,
                           zorder=2.5))
    y_s0, y_s1 = float(ymap(sens_cm.min())), float(ymap(sens_cm.max()))
    ax.add_patch(Rectangle((BLK_L, y_s1), BLK_R - BLK_L, y_s0 - y_s1,
                           facecolor=BAND_SENS, edgecolor="none", alpha=0.72,
                           zorder=2.5))

    # --- grains, compacting with depth --------------------------------------
    rng = np.random.default_rng(23)
    zz = np.geomspace(Z_TOP, Z_BOT, 200)
    rho = density_hayne(zz / 100.0)
    frac = (rho - rho.min()) / (rho.max() - rho.min())
    n_band = 24
    for i in range(n_band):
        t = i / (n_band - 1)
        y0 = Y_TOP - 0.06 - t * (Y_TOP - Y_BOT - 0.12)
        z_here = float(np.interp(y0, ymap(zz)[::-1], zz[::-1]))
        fq = float(np.interp(z_here, zz, frac))       # 0 loose -> 1 packed
        rad = 0.046 - 0.030 * fq
        for _ in range(int(round(7 + 24 * fq))):
            gx = rng.uniform(BLK_L + 1.3 * rad, BLK_R - 1.3 * rad)
            gy = y0 + rng.uniform(-0.036, 0.036)
            if not (Y_BOT + 1.2 * rad < gy < Y_TOP - 1.2 * rad):
                continue
            grain(ax, gx, gy, rad * rng.uniform(0.74, 1.15))
    for _ in range(40):
        tt = rng.uniform(0.16, 0.82)
        yy = rng.uniform(Y_BOT + 0.07, Y_TOP - 0.06)
        d_f = (Y_TOP - yy) / (Y_TOP - Y_BOT)
        grain(ax, BLK_R + tt * SHEAR_X, yy + tt * SHEAR_Y,
              (0.034 - 0.020 * d_f) * rng.uniform(0.7, 1.1), z=4, dim=0.22)
    for _ in range(26):
        yy = rng.uniform(Y_TOP + 0.03, Y_TOP + SHEAR_Y - 0.03)
        t = (yy - Y_TOP) / SHEAR_Y
        gx = rng.uniform(BLK_L + t * SHEAR_X + 0.05,
                         BLK_R + t * SHEAR_X - 0.05)
        if abs(gx - 1.28) < 0.10:
            continue
        grain(ax, gx, yy, rng.uniform(0.022, 0.036), z=5)

    # --- depth scale --------------------------------------------------------
    ax.text(BLK_L - 0.07, Y_TOP + 0.30, "depth\n(cm)", color=C_DIM,
            fontsize=8.0, ha="right", va="center", linespacing=1.2)
    for zc, lab in TICKS:
        y = float(ymap(zc))
        ax.plot([BLK_L - 0.05, BLK_L], [y, y], color=C_DIM, lw=0.6, zorder=6)
        ax.text(BLK_L - 0.08, y, lab, color=C_DIM, fontsize=8.0, ha="right",
                va="center")

    # --- the Sun and the surface exchange, compactly ------------------------
    sx, sy = SUN
    for k in range(12):
        t = k / 11
        ax.add_patch(Circle((sx, sy), SUN_R * (1 + 3.2 * t ** 1.5),
                            facecolor=WARM, edgecolor="none",
                            alpha=0.05 * (1 - t) ** 1.4, zorder=8))
    ax.add_patch(Circle((sx, sy), SUN_R, facecolor=_shade(WARM, 0.18),
                        edgecolor="none", zorder=9))
    ax.add_patch(FancyArrowPatch((sx + 0.12, sy - 0.20), (1.28, Y_TOP + 0.05),
                                 color=WARM, zorder=10, **ARROW))
    for j, ex in enumerate((1.62, 1.96, 2.26)):
        s = np.linspace(0, 1, 120)
        L = 0.60
        th = np.radians(92 - 8 * j)
        v = np.array([np.cos(th), np.sin(th)])
        n = np.array([-v[1], v[0]])
        pts = (np.array([ex, Y_TOP + 0.05])[None, :] + v[None, :] * (s * L)[:, None]
               + n[None, :] * (0.026 * np.sin(s * 4.0 * np.pi)
                               * np.clip(s * 3, 0, 1))[:, None])
        ax.plot(pts[:, 0], pts[:, 1], color=COOL, lw=1.3, alpha=0.95,
                solid_capstyle="round", zorder=10)
        ax.add_patch(FancyArrowPatch(tuple(pts[-5]), tuple(pts[-1]), color=COOL,
                                     lw=1.3, arrowstyle="-|>",
                                     mutation_scale=9, shrinkA=0, shrinkB=0,
                                     zorder=10))

    # --- the basal flux, arriving from below --------------------------------
    ax.add_patch(FancyArrowPatch((mid, Y_BOT - 0.22), (mid, Y_BOT + 0.16),
                                 color=C_FOREST, zorder=10, **ARROW))
    ax.text(mid, Y_BOT - 0.42,
            rf"$Q_b={SITES['A15']['Q_BASAL']*1e3:.0f}\,/\,"
            rf"{SITES['A17']['Q_BASAL']*1e3:.0f}$ mW m$^{{\mathrm{{-2}}}}$",
            color=C_FOREST, fontsize=9.5, ha="center", va="center")

    # --- band annotations ---------------------------------------------------
    # The long "below 54 cm..." sentence used to live in here and ran straight
    # through the sensor caption. It is an argument, not a label, so it moved to
    # the right column; what stays inside the block is short enough to fit.
    ax.text(BLK_L + 0.05, Y_TOP - 0.14,
            "the daily wave\n"
            rf"$1/e$ at {Z_SKIN_E:.1f} cm",
            color=_shade(WARM, -0.25), fontsize=8.0, ha="left", va="top",
            linespacing=1.3, zorder=12, bbox=HALO)
    # the depth where the swing effectively stops, marked on the block itself
    y_dead_line = float(ymap(Z_SKIN_DEAD))
    ax.plot([BLK_L, BLK_R], [y_dead_line, y_dead_line], color=_shade(WARM, -0.3),
            lw=0.8, ls=(0, (2.4, 2.0)), zorder=12)
    ax.text(BLK_R - 0.04, y_dead_line + 0.035,
            rf"swing $<0.1$ K below {Z_SKIN_DEAD:.0f} cm",
            color=_shade(WARM, -0.3), fontsize=7.5, ha="right", va="bottom",
            zorder=12, bbox=HALO)
    for zc in sens_cm:
        ax.add_patch(Circle((BLK_R - 0.14, float(ymap(zc))), 0.022,
                            facecolor=C_FOREST, edgecolor="white", lw=0.4,
                            zorder=13))
    ax.text(BLK_L + 0.05, 0.5 * (y_s0 + y_s1),
            f"{sens_cm.size} Apollo sensors\n"
            f"{sens_cm.min():.0f}–{sens_cm.max():.0f} cm",
            color=_shade(C_FOREST, -0.1), fontsize=8.0, ha="left",
            va="center", linespacing=1.3, zorder=12, bbox=HALO)


# ============================================================ B: compaction
def draw_density(ax):
    zz = np.geomspace(Z_TOP, Z_BOT, 400)
    rho = density_hayne(zz / 100.0)
    lo, hi = 1050.0, 1850.0
    xs = DENS_L + (rho - lo) / (hi - lo) * (DENS_R - DENS_L)
    ax.fill_betweenx(ymap(zz), DENS_L, xs, color=C_GRID, alpha=0.6, lw=0,
                     zorder=2)
    ax.plot(xs, ymap(zz), color=DARK, lw=1.6, solid_capstyle="round", zorder=5)
    for v in (1100, 1800):
        xv = DENS_L + (v - lo) / (hi - lo) * (DENS_R - DENS_L)
        ax.plot([xv, xv], [Y_BOT, Y_TOP], color=C_GRID, lw=0.6,
                ls=(0, (1.6, 1.6)), zorder=3)
        ax.text(xv, Y_TOP + 0.05, f"{v}", color=C_DIM, fontsize=8.0,
                ha="center", va="bottom")
    ax.text(0.5 * (DENS_L + DENS_R), Y_TOP + 0.22,
            r"$\rho$ (kg m$^{\mathrm{-3}}$)", color=C_DIM, fontsize=8.0,
            ha="center", va="bottom")
    yH = float(ymap(HAYNE["H"] * 100.0))
    ax.plot([DENS_L, DENS_R], [yH, yH], color=C_DIM, lw=0.7, ls=(0, (1.8, 1.8)),
            zorder=6)
    ax.text(DENS_R + 0.03, yH, r"$H$", color=C_DIM, fontsize=8.0, ha="left",
            va="center")
    ax.text(0.5 * (DENS_L + DENS_R), Y_BOT - 0.16,
            "most of the compaction\n"
            rf"happens above $H={HAYNE['H']*100:.0f}$ cm",
            color=C_DIM, fontsize=8.0, ha="center", va="top", linespacing=1.3)


# ============================================================ C: the two BCs
def draw_equations(ax):
    ax.text(EQ_X, Y_EQ_SURF + 0.19, "at the top", color=WARM, fontsize=8.5,
            ha="left", va="center")
    ax.text(EQ_X, Y_EQ_SURF - 0.03,
            r"$(1-A)\,S(t)=\varepsilon\sigma T_s^{4}+K\,\partial T/\partial z$",
            color=DARK, fontsize=11.5, ha="left", va="center")
    ax.text(EQ_X, Y_EQ_SURF - 0.26,
            r"solved for $T_s$ at every step", color=C_DIM, fontsize=8.0,
            ha="left", va="center")

    ax.text(EQ_X, Y_EQ_BASE + 0.19, r"at the bottom, $z=5$ m", color=C_FOREST,
            fontsize=8.5, ha="left", va="center")
    ax.text(EQ_X, Y_EQ_BASE - 0.03,
            r"$-K\,\partial T/\partial z=Q_b$",
            color=DARK, fontsize=11.5, ha="left", va="center")
    ax.text(EQ_X, Y_EQ_BASE - 0.26,
            r"the flux is fixed, not the temperature — so the deep"
            "\n"
            r"gradient must be $\mathrm{d}T/\mathrm{d}z=Q_b/K$",
            color=C_DIM, fontsize=8.0, ha="left", va="top", linespacing=1.35)


# ============================================================ D: the retrieval
def draw_bowl(fig, kd):
    ax = fig.add_axes([BOWL[0] / W, BOWL[1] / H, BOWL[2] / W, BOWL[3] / H])
    for key, col in (("A15", C_A15), ("A17", C_A17)):
        g = np.asarray(kd[key]["kd_grid"], dtype=float) * 1e3
        r = np.asarray(kd[key]["rmse_curve"], dtype=float)
        o = np.argsort(g)
        g, r = g[o], r[o]
        m = (g >= 2.2) & (g <= 12.0)
        ax.plot(g[m], r[m], color=col, lw=1.6, marker="o", ms=2.6,
                mec="white", mew=0.4, label=f"{SITES[key]['label']}")
        ks = float(kd[key]["kd_star"]) * 1e3
        rs = float(kd[key]["rmse_star"])
        ax.plot([ks], [rs], marker="v", ms=6.5, color=col, mec="white",
                mew=0.7, zorder=6)
        # A15's vertex sits directly above A17's rising limb, so its label goes
        # ABOVE the marker; below it landed on the other site's curve. A17 has
        # clear space beneath it and keeps the label there. The axis floor stays
        # at 0 either way — dropping it negative to make room printed a
        # meaningless negative RMSE.
        up = key == "A15"
        ax.annotate(rf"$K_d^{{*}}={ks:.2f}$", xy=(ks, rs),
                    xytext=(ks, rs + (0.30 if up else -0.26)), color=col,
                    fontsize=9.5, ha="center",
                    va="bottom" if up else "top",
                    arrowprops=dict(arrowstyle="-", lw=0.7, color=col,
                                    shrinkA=1, shrinkB=3))
    ax.set_xlim(2.2, 12.0)
    ax.set_ylim(0.0, 2.30)
    ax.set_xlabel(r"trial $K_d$ (mW m$^{\mathrm{-1}}$K$^{\mathrm{-1}}$)",
                  fontsize=9.0, color=DARK)
    ax.set_ylabel("RMSE against the\nsensors (K)", fontsize=9.0, color=DARK,
                  linespacing=1.3)
    ax.tick_params(labelsize=8.0, colors=DARK)
    ax.grid(axis="both", color=C_GRID, lw=0.5)
    ax.set_axisbelow(True)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    for s in ("left", "bottom"):
        ax.spines[s].set_color(DARK)
    ax.legend(loc="upper center", frameon=True, edgecolor=C_GRID,
              fontsize=8.5, ncols=2, handlelength=1.4, columnspacing=1.0)
    return ax


def main() -> None:
    family, cambria = setup_fonts()
    apply_style(family, cambria)

    site = SITES["A15"]
    sens = extract_sensor_stability(site["mission"], site["MIN_DEPTH_CM"])
    z_all = np.asarray(sens["depth_cm_all"], dtype=float)
    sens_cm = z_all[np.asarray(sens["deep_mask"], dtype=bool)]
    kd = json.loads((_REPO / "results"
                     / "kd_retrieval_results.json").read_text())

    fig = plt.figure(figsize=(W, H))
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, W)
    ax.set_ylim(0, H)
    ax.axis("off")

    draw_block(ax, sens_cm)
    draw_density(ax)
    draw_equations(ax)

    # the argument, moved out of the block where it collided with the sensor
    # caption: this is what ties the banded regions to the bowl below
    ax.text(EQ_X, 3.72, r"so how is $K_d$ found?", color=DARK, fontsize=11.0,
            ha="left", va="center")
    ax.text(EQ_X, 3.50,
            rf"Below {Z_SKIN_DEAD:.0f} cm the swing is gone and only the slope"
            "\n"
            r"$Q_b/K$ is left. The sensors sit there, so their slope"
            "\n"
            r"measures $K$. Sweep $K_d$ and take the bowl's bottom.",
            color=C_DIM, fontsize=8.5, ha="left", va="top", linespacing=1.4)

    draw_bowl(fig, kd)

    fig.canvas.draw()
    FIGS.mkdir(parents=True, exist_ok=True)
    with plt.rc_context({"savefig.pad_inches": 0.02}):
        fig.savefig(FIGS / "fig_column_and_retrieval.pdf")
        fig.savefig(FIGS / "fig_column_and_retrieval.png", dpi=300)
    plt.close(fig)
    print(f"  wrote figures/fig_column_and_retrieval.pdf + .png "
          f"({W:.2f} x {H:.2f} in)")
    print(f"  fonts: {family}" + ("" if cambria else "  (fell back)"))
    print(f"  skin 1/e {Z_SKIN_E} cm, dead by {Z_SKIN_DEAD} cm; "
          f"{sens_cm.size} sensors {sens_cm.min():.0f}-{sens_cm.max():.0f} cm")
    print(f"  bowls: {len(kd['A15']['kd_grid'])} / "
          f"{len(kd['A17']['kd_grid'])} swept values")


if __name__ == "__main__":
    main()
