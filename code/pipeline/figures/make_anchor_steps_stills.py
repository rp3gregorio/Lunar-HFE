#!/usr/bin/env python3
"""The flux-anchored method in four stills, for an audience with no background.

    1  the daily swing dies with depth -- which is why an anchor exists at all
    2  STEP A: time-step only the skin, then read the anchor
    3  STEP B: integrate the deep column down from it, never time-stepping
    4  converged -- and two very different starting guesses land in the same place

Left panel is the daily temperature swing on a log axis: +/-134 K at the
surface, +/-0.08 K at the anchor, a factor of 1600 in half a metre. That is the
justification for the anchor depth, and without it 0.55 m looks arbitrary. It
cannot share the right panel's linear axis -- a 134 K band would flatten a 15 K
profile to a sliver -- so it gets its own panel on the same depth scale.

Right panel is the cycle-mean column being built. Green is what Step A
time-steps; teal is what Step B reconstructs. They never overlap, which is the
whole point: the green section is never simulated.

Everything is real. A15 at n_inner=4 (which exposes the outer A<->B contraction
cycle by cycle; production n_inner=96 converges in ~2 and hides the iteration --
same certified attractor). The deep column comes from the PRODUCTION integrator.
Frame 4's two profiles are genuine independent solves from T_guess = 230 K and
275 K, so the guess-independence claim is shown, not asserted.

    python pipeline/figures/make_anchor_steps_stills.py
"""
from __future__ import annotations

import functools
import pathlib

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from lunar.config import GRID, HAYNE, SITES, EQ_Z_ANCHOR, DT_STEP
from lunar.equilibrium import (solve_periodic_equilibrium, _rectified_flux,
                               _reconstruct_subskin)
from lunar.grid import make_geometric_grid
from lunar.plotting.style import (C_CHAR, C_CORAL, C_DIM, C_FOREST, C_GRID,
                                  C_TEAL, C_TEAL_L, fmt_axis)
from lunar.properties import conductivity_hayne, specific_heat
from lunar.solver import periodic_time_grid, standard_insolation

SITE = SITES["A15"]
KD = 4.60e-3
Z0 = EQ_Z_ANCHOR
ZMAX = 3.0
XLIM = (244.0, 259.0)
AMP_FLOOR = 3e-3          # log axis needs a floor; below ~0.9 m the swing is 0

OUT = (pathlib.Path(__file__).resolve().parents[4]
       / "Others" / "gedes" / "defense" / "img")


CACHE = (pathlib.Path(__file__).resolve().parents[2]
         / "results" / "anchor_stills_cache.npz")


def compute():
    """Three solves at n_inner=4 take ~90 s, so the result is cached. Delete
    results/anchor_stills_cache.npz to force a recompute."""
    if CACHE.exists():
        d = dict(np.load(CACHE))
        for k in ("i0", "i_skin"):
            d[k] = int(d[k])
        for k in ("anchorT", "ampA", "spread"):
            d[k] = float(d[k])
        print(f"  (cached: {CACHE.name})")
        return d
    return _compute()


def _compute():
    g = make_geometric_grid(**GRID)
    z = g.z_mid
    t = periodic_time_grid(DT_STEP)
    insol = standard_insolation(SITE["lat"], t)
    K = functools.partial(conductivity_hayne, Ks=HAYNE["K_S"], Kd=KD,
                          H=HAYNE["H"], chi=HAYNE["CHI"])
    cp = functools.partial(specific_heat, model="hayne")
    Qb = SITE["Q_BASAL"]

    def solve(tg):
        return solve_periodic_equilibrium(
            grid=g, t=t, insolation=insol, albedo=SITE["albedo"],
            emissivity=SITE["emissivity"], Q_b=Qb, K_func=K, cp_func=cp,
            T_guess=tg, n_inner=4)

    eq = solve(SITE["T_MEAN_EFF"])
    T_true = eq.T_mean
    amp = (eq.out.T.max(axis=1) - eq.out.T.min(axis=1)) / 2.0

    # frame 4: two deliberately silly starting temperatures
    cold, hot = solve(230.0).T_mean, solve(275.0).T_mean

    i0 = int(np.argmin(np.abs(z - Z0)))
    i_skin = int(np.argmin(np.abs(z - (Z0 + 0.15))))
    u_rect = _rectified_flux(eq.out.T, z, K)
    T_walk = _reconstruct_subskin(T_true.copy(), z, i0, Qb, K, u_rect)

    # a wrong start, linear in DEPTH (the grid is geometric, so a linspace over
    # the cell index would plot as a curve, not the straight line it claims)
    Tm = float(T_true.mean())
    T_guess = (Tm - 2.0) + 1.2 * z

    T_skin = T_guess.copy()
    T_skin[:i_skin] = T_true[:i_skin]

    spread = float(np.max(np.abs(cold - hot)[z <= ZMAX]))
    print(f"  guess-independence: 230 K vs 275 K start differ by "
          f"{spread:.4f} K over the top 3 m")

    D = dict(z=z, i0=i0, i_skin=i_skin, T_true=T_true, T_walk=T_walk,
             T_guess=T_guess, T_skin=T_skin, amp=amp, cold=cold, hot=hot,
             anchorT=float(T_true[i0]), ampA=float(amp[i0]), spread=spread)
    CACHE.parent.mkdir(parents=True, exist_ok=True)
    np.savez(CACHE, **D)
    return D


FRAMES = [
    (1, "The daily swing dies with depth"),
    (2, "STEP A — settle the skin, read the anchor"),
    (3, "STEP B — rebuild the deep column"),
    (4, "Converged — and the starting guess did not matter"),
]


def draw_swing(ax, D, frame):
    z, a = D["z"], np.maximum(D["amp"], AMP_FLOOR)
    keep = z <= ZMAX
    ax.semilogx(a[keep], z[keep], lw=2.6, color=C_CHAR, zorder=4)
    lit = frame in (2, 3)
    ax.axhline(Z0, lw=0.9 if lit else 0.7, color=C_DIM, ls=":",
               alpha=1.0 if lit else 0.45, zorder=2)
    if lit:
        ax.plot([D["ampA"]], [Z0], "o", ms=9, color=C_CHAR, mec="white",
                mew=1.5, zorder=5)
    ax.set_xlim(AMP_FLOOR / 3.0, 400)   # room so the floored tail is visible
    ax.set_ylim(ZMAX, 0.0)
    fmt_axis(ax, xlabel="daily swing  (± K)", ylabel="depth  (m)")
    ax.tick_params(labelsize=10)
    ax.xaxis.label.set_size(11.5)
    ax.yaxis.label.set_size(11.5)
    ax.grid(True, which="major", lw=0.5, color=C_GRID)


def draw_column(ax, D, frame):
    z, i0, s = D["z"], D["i0"], D["i_skin"]
    keep = z <= ZMAX

    if frame < 4:
        ax.plot(D["T_guess"][keep], z[keep], ls=(0, (5, 4)), lw=1.4,
                color=C_DIM, alpha=0.85 if frame == 1 else 0.40, zorder=2)

    if frame in (2, 3):
        ax.plot(D["T_true"][:s], z[:s], lw=3.0, color=C_FOREST, zorder=5)
        if frame == 2:
            ax.axhspan(0, z[s], color=C_FOREST, alpha=0.06, zorder=0)
    if frame == 3:
        d = (z >= Z0) & keep
        ax.plot(D["T_walk"][d], z[d], lw=3.0, color=C_TEAL, zorder=5)
        ax.axhspan(Z0, ZMAX, color=C_TEAL, alpha=0.06, zorder=0)

    if frame == 4:
        # two silly starts, drawn flat so it is obvious they disagree
        for T0 in (230.0, 275.0):
            ax.plot([T0, T0], [0, ZMAX], "-", lw=1.7,
                    color=C_CORAL, alpha=0.60, zorder=2)
        ax.plot(D["cold"][keep], z[keep], lw=5.0, color=C_TEAL_L, zorder=4)
        ax.plot(D["hot"][keep], z[keep], lw=2.0, color=C_TEAL, zorder=5)

    lit = frame in (2, 3)
    ax.axhline(Z0, lw=0.9 if lit else 0.7, color=C_DIM, ls=":",
               alpha=1.0 if lit else 0.40, zorder=1)
    if lit:
        ax.plot([D["anchorT"]], [Z0], "o", ms=10, color=C_CHAR,
                mec="white", mew=1.6, zorder=6)

    ax.set_ylim(ZMAX, 0.0)
    ax.set_xlim(226.0, 279.0) if frame == 4 else ax.set_xlim(*XLIM)
    fmt_axis(ax, xlabel="cycle-mean temperature  (K)", ylabel="")
    ax.tick_params(labelsize=10)
    ax.xaxis.label.set_size(11.5)


def main():
    D = compute()
    OUT.mkdir(parents=True, exist_ok=True)
    for n, title in FRAMES:
        fig = plt.figure(figsize=(10.4, 5.2))
        gs = fig.add_gridspec(1, 2, width_ratios=[1.0, 1.75],
                              left=0.075, right=0.975, top=0.855,
                              bottom=0.115, wspace=0.16)
        draw_swing(fig.add_subplot(gs[0]), D, n)
        draw_column(fig.add_subplot(gs[1]), D, n)
        col = {1: C_CHAR, 2: C_FOREST, 3: C_TEAL, 4: C_CHAR}[n]
        fig.text(0.075, 0.955, title, fontsize=13, fontweight="bold",
                 color=col, va="top")
        p = OUT / f"anchor_f{n}.png"
        fig.savefig(p, dpi=200, facecolor="white")
        plt.close(fig)
        print(f"  wrote {p.name}   {title}")
    print(f"\n4 stills -> {OUT}")


if __name__ == "__main__":
    main()
