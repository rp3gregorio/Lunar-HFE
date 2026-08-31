#!/usr/bin/env python3
"""The 1-D thermal model in four stills, for an audience with no background.

    1  the column, cut into layers -- millimetres at the top, decimetres below
    2  sunlight in, heat radiated out: the curved sun-driven top
    3  a steady flux from below: the straight deep gradient
    4  the one unknown in the middle -- K_d tilts that gradient

Companion to make_anchor_steps_stills.py and deliberately built to the same
grammar: two panels, one shared depth axis, the same colours, the same short
bold title. Slide 6 is the STANDARD model (no anchor, no Step A/B); slide 7 is
the method. Making them look like one picture is the point -- by the time the
anchor arrives the audience already knows the column, so the only new thing on
slide 7 is the method itself.

Left panel is the column itself, held identical across every frame: the real
cell faces from make_geometric_grid drawn as its layers -- 2 mm at the surface,
~0.24 m at 3 m, so the top reads as a dark gradient. That texture IS the
discretisation. The two boundary conditions arrive on it: coral arrows in and
out at the top (frame 2), a green arrow from below (frame 3), and in frame 4 a
teal wash over everything deeper than H, which is the reach of the one unknown.

Right panel is the cycle-mean column, on the SAME x-limits as the anchor
stills' right panel so slides 6 and 7 are literally the same picture. Frame 1
draws the whole profile in grey; frames 2 and 3 colour in the part each
boundary sets. Coral is the sun-driven top, green the geothermal deep gradient
-- the same two regions that become Step A and Step B on the next slide. The
split sits at EQ_Z_ANCHOR + 0.15 m, exactly where solve_periodic_equilibrium
truncates Step A, so the two figures divide the column in the same place.

Both panels clip the top cell: the cycle-mean surface temperature is ~216 K,
far left of the 244 K axis. The anchor stills clip it the same way.

Everything is real: three production solves (the retrieved K_d* plus the two
frame-4 trial values) through solve_periodic_equilibrium on the compiled
Hayne march, at the production n_inner. K_d* is read from
results/kd_retrieval_results.json, never hardcoded.

    python pipeline/figures/make_thermal_model_stills.py
"""
from __future__ import annotations

import functools
import json
import pathlib

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from lunar.config import DT_STEP, EQ_Z_ANCHOR, GRID, HAYNE, SITES
from lunar.equilibrium import solve_periodic_equilibrium
from lunar.grid import make_geometric_grid
from lunar.plotting.style import (C_CHAR, C_CORAL, C_DIM, C_FOREST, C_GRID,
                                  C_NEUTRAL, C_TEAL, C_TEAL_L, fmt_axis)
from lunar.properties import conductivity_hayne, specific_heat
from lunar.solver import periodic_time_grid, standard_insolation

SITE = SITES["A15"]
ZMAX = 3.0
ZSKY = -0.34              # headroom above z=0 for the two boundary arrows
ZSPLIT = EQ_Z_ANCHOR + 0.15   # coral/green divide == Step A's truncation depth
XLIM = (244.0, 259.0)     # identical to the anchor stills' right panel
KD_LOW, KD_HIGH = 2.5e-3, 9.0e-3   # frame-4 trials, inside KD_GRIDS["A15"]
COL_FILL = "#F0EEEA"      # the regolith column

ROOT = pathlib.Path(__file__).resolve().parents[2]
OUT = ROOT.parents[1] / "Others" / "gedes" / "defense" / "img"
CACHE = ROOT / "results" / "thermal_model_stills_cache.npz"
KD_JSON = ROOT / "results" / "kd_retrieval_results.json"


def compute():
    """Four production solves take ~1 min, so the result is cached. Delete
    results/thermal_model_stills_cache.npz to force a recompute."""
    if CACHE.exists():
        d = dict(np.load(CACHE))
        d["kd_star"] = float(d["kd_star"])
        print(f"  (cached: {CACHE.name})")
        return d
    return _compute()


def _solve(kd, g, t, insol):
    K = functools.partial(conductivity_hayne, Ks=HAYNE["K_S"], Kd=kd,
                          H=HAYNE["H"], chi=HAYNE["CHI"])
    cp = functools.partial(specific_heat, model="hayne")
    return solve_periodic_equilibrium(
        grid=g, t=t, insolation=insol, albedo=SITE["albedo"],
        emissivity=SITE["emissivity"], Q_b=SITE["Q_BASAL"], K_func=K,
        cp_func=cp, T_guess=SITE["T_MEAN_EFF"],
        # compiled march; standard Hayne property set (see PixelInputs)
        hayne_params=(HAYNE["K_S"], kd, HAYNE["H"], HAYNE["CHI"]))


def _compute():
    kd_star = float(json.loads(KD_JSON.read_text())["A15"]["kd_star"])
    g = make_geometric_grid(**GRID)
    t = periodic_time_grid(DT_STEP)
    insol = standard_insolation(SITE["lat"], t)

    eq = _solve(kd_star, g, t, insol)
    print(f"  K_d* = {kd_star*1e3:.3f} mW/m/K   anchor drift "
          f"{eq.anchor_drift_K:.4f} K   flux closure {eq.flux_closure:.2e}")
    lo = _solve(KD_LOW, g, t, insol)
    hi = _solve(KD_HIGH, g, t, insol)

    D = dict(z=g.z_mid, z_face=g.z_face, dz=g.dz, T_star=eq.T_mean,
             T_lo=lo.T_mean, T_hi=hi.T_mean, kd_star=kd_star)
    CACHE.parent.mkdir(parents=True, exist_ok=True)
    np.savez(CACHE, **D)
    return D


FRAMES = [
    (1, "The ground, cut into layers", C_CHAR),
    (2, "Sunlight in, heat radiated out", C_FOREST),
    (3, "A steady flux from below", C_TEAL),
    (4, "One unknown in the middle", C_TEAL),
]


COL_L, COL_R = 0.14, 0.86      # the column's left/right edge in the left panel


def cell_rules(ax, D, frame, x0=None, x1=None):
    """The real cell faces, drawn as the horizontal rules of BOTH panels -- so
    the figure's depth texture IS the model's discretisation. Lit inside the
    column in frame 1; a faint texture everywhere else."""
    lit = frame == 1 and x0 is not None
    inside = x0 is not None            # left panel: rules sit over the tints
    kw = dict(lw=0.5 if lit else (0.4 if inside else 0.32),
              zorder=4 if inside else 0,
              color=C_CHAR if lit else (C_DIM if inside else C_NEUTRAL),
              alpha=0.50 if lit else (0.30 if inside else 0.20))
    for zf in D["z_face"][D["z_face"] <= ZMAX]:
        if x0 is None:                      # full-width rule (right panel)
            ax.axhline(zf, **kw)
        else:                               # inside the column (left panel)
            ax.plot([x0, x1], [zf, zf], **kw)


def surface_line(ax, x0=None, x1=None):
    if x0 is None:
        ax.axhline(0.0, lw=1.8, color=C_CHAR, zorder=6)
    else:
        ax.plot([x0, x1], [0.0, 0.0], lw=1.8, color=C_CHAR, zorder=6,
                solid_capstyle="butt")


def draw_layers(ax, D, frame):
    """Left panel: the column itself, sliced at the real cell faces, with the
    two boundary conditions arriving on it. Identical in all four frames apart
    from what is lit."""
    ax.add_patch(plt.Rectangle((COL_L, 0.0), COL_R - COL_L, ZMAX,
                               fc=COL_FILL, ec="none", zorder=1))

    cell_rules(ax, D, frame, COL_L, COL_R)

    if frame == 2:                      # sunlight in, heat radiated out
        ax.add_patch(plt.Rectangle((COL_L, 0.0), COL_R - COL_L, ZSPLIT,
                                   fc=C_FOREST, alpha=0.14, ec="none", zorder=3))
        arrow(ax, 0.34, ZSKY + 0.02, -0.012, C_FOREST)
        arrow(ax, 0.66, -0.012, ZSKY + 0.02, C_FOREST)
    if frame == 3:                      # the geothermal flux, entering below
        ax.add_patch(plt.Rectangle((COL_L, ZSPLIT), COL_R - COL_L,
                                   ZMAX - ZSPLIT, fc=C_TEAL, alpha=0.12,
                                   ec="none", zorder=3))
        arrow(ax, 0.5, ZMAX, ZMAX - 0.62, C_TEAL)
    if frame == 4:                      # the one unknown, everywhere below H
        ax.add_patch(plt.Rectangle((COL_L, HAYNE["H"]), COL_R - COL_L,
                                   ZMAX - HAYNE["H"], fc=C_TEAL, alpha=0.12,
                                   ec="none", zorder=3))

    surface_line(ax, COL_L, COL_R)
    ax.set_xlim(0.0, 1.0)
    ax.set_ylim(ZMAX, ZSKY)
    fmt_axis(ax, xlabel="", ylabel="depth  (m)")
    ax.grid(False)
    ax.set_xticks([])
    ax.spines["bottom"].set_visible(False)
    ax.tick_params(labelsize=10)
    ax.yaxis.label.set_size(11.5)


def arrow(ax, x, y0, y1, color, filled=True):
    ax.annotate("", xy=(x, y1), xytext=(x, y0), zorder=6,
                arrowprops=dict(arrowstyle="-|>", lw=2.4, color=color,
                                fc=color if filled else "white",
                                mutation_scale=20, shrinkA=0, shrinkB=0))


def draw_column(ax, D, frame):
    """Right panel: the cycle-mean column, built one boundary at a time."""
    z = D["z"]
    keep = z <= ZMAX
    isplit = int(np.searchsorted(z, ZSPLIT))     # share the boundary cell, so
    top = keep.copy(); top[isplit + 1:] = False  # coral and green meet with no
    deep = keep.copy(); deep[:isplit] = False    # gap at ZSPLIT

    cell_rules(ax, D, frame)

    if frame < 4:      # the profile the model computes, coloured in by beat
        ax.plot(D["T_star"][keep], z[keep], lw=2.2, color=C_DIM,
                alpha=0.9 if frame == 1 else 0.30, zorder=3)
    if frame in (2, 3):
        ax.plot(D["T_star"][top], z[top], lw=3.0, color=C_FOREST, zorder=5)
    if frame == 2:
        ax.axhspan(0, ZSPLIT, color=C_FOREST, alpha=0.06, zorder=1)
    if frame == 3:
        ax.plot(D["T_star"][deep], z[deep], lw=3.0, color=C_TEAL, zorder=5)
        ax.axhspan(ZSPLIT, ZMAX, color=C_TEAL, alpha=0.06, zorder=1)

    if frame == 4:
        for key, col, lw in (("T_lo", C_TEAL_L, 2.2),
                             ("T_star", C_TEAL, 3.2),
                             ("T_hi", C_TEAL_L, 2.2)):
            ax.plot(D[key][keep], z[keep], lw=lw, color=col, zorder=5)

    surface_line(ax)
    ax.set_ylim(ZMAX, ZSKY)
    if frame == 4:  # noqa: SIM108 -- the fan needs its own span
        deep = keep & (z >= 0.3)
        hi = float(max(D["T_lo"][deep].max(), D["T_hi"][deep].max()))
        ax.set_xlim(XLIM[0] + 2.0, hi + 1.2)
    else:
        ax.set_xlim(*XLIM)
    fmt_axis(ax, xlabel="cycle-mean temperature  (K)", ylabel="")
    ax.grid(False)
    ax.grid(True, axis="x", which="major", lw=0.5, color=C_GRID)
    ax.tick_params(labelsize=10)
    ax.xaxis.label.set_size(11.5)


def main():
    D = compute()
    OUT.mkdir(parents=True, exist_ok=True)
    for n, title, col in FRAMES:
        fig = plt.figure(figsize=(10.4, 5.2))
        gs = fig.add_gridspec(1, 2, width_ratios=[0.80, 1.75],
                              left=0.075, right=0.975, top=0.855,
                              bottom=0.115, wspace=0.16)
        draw_layers(fig.add_subplot(gs[0]), D, n)
        draw_column(fig.add_subplot(gs[1]), D, n)
        fig.text(0.075, 0.955, title, fontsize=13, fontweight="bold",
                 color=col, va="top")
        p = OUT / f"model_f{n}.png"
        fig.savefig(p, dpi=200, facecolor="white")
        plt.close(fig)
        print(f"  wrote {p.name}   {title}")
    print(f"\n4 stills -> {OUT}")


if __name__ == "__main__":
    main()
