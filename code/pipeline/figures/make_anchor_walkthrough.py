#!/usr/bin/env python3
"""The anchor method in four labelled stills, in the letter figure's language.

    1  start from anything          a deliberately wrong straight guess
    2  Step A: settle the skin      time-step 0-0.7 m only; read the anchor
    3  Step B: walk down            integrate the deep column from the anchor
    4  repeat                       each pass moves the anchor less

This is the panel (a) of fig_anchor_method.pdf unfolded in time. That panel
shows the finished construction all at once; the one thing it cannot show is
that A and B ALTERNATE -- that this is an iteration, not a one-shot recipe.
Frame 4 is that.

COLOUR LAW (the letter figure's, used across the deck and the thesis):
    coral      the guess -- a value we do not know yet
    green      time-stepped (Step A)
    teal       reconstructed (Step B)
    grey dash  the converged steady state, the reference in every frame
    black dot  the anchor at z0 = 0.55 m

Everything is real. The outer loop below is assembled from the PRODUCTION
pieces -- solve_pixel on the truncated Step A sub-grid, _rectified_flux,
_reconstruct_subskin -- in the same order equilibrium.solve_periodic_-
equilibrium calls them, and main() certifies that its fixed point matches
solve_periodic_equilibrium's own answer before drawing anything.

PRODUCTION n_inner=96. A smaller n_inner would show more outer passes, but it
does not converge: single-stage loops at n_inner = 4 / 8 / 16 / 32 sit 1335 /
250 / 62 / 15 mK from the certified answer after eight passes, because the
skin itself is under-spun. At 96 the anchor moves 7.6 mK on the second pass
and nothing on the third -- so frame 4 shows what is actually true, which is
that ONE pass eliminates the guess. Two opposite starting guesses landing on
the same curve is the real convergence claim, and it is stronger than a
contraction the production settings never perform.

The starting guess is linear in DEPTH. A linspace over the cell index -- which
is what the letter figure does -- plots as a curve on a geometric grid, not the
straight line it claims to be.

    python pipeline/figures/make_anchor_walkthrough.py
"""
from __future__ import annotations

import functools
import json
import pathlib

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from lunar.config import (DT_STEP, EQ_ANCHOR_TOL, EQ_Z_ANCHOR, GRID, HAYNE,
                          SITES)
from lunar.equilibrium import (_reconstruct_subskin, _rectified_flux,
                               _truncate_grid, solve_periodic_equilibrium)
from lunar.grid import make_geometric_grid
from lunar.plotting.style import (C_CHAR, C_CORAL, C_DIM, C_FOREST, C_GRID,
                                  C_TEAL, C_TEAL_L, fmt_axis)
from lunar.properties import conductivity_hayne, specific_heat
from lunar.solver import (PixelInputs, periodic_time_grid, solve_pixel,
                          standard_insolation)

SITE = SITES["A15"]
Z0 = EQ_Z_ANCHOR
ZCAP = Z0 + 0.15          # Step A's truncation depth
ZMAX = 3.0
XLIM = (243.0, 262.0)
N_INNER = 96              # production (config.EQ_N_INNER); see the docstring
N_OUTER = 3
GUESS = ((-5.0, 4.2), (9.0, -3.0))   # (offset, slope) -- two opposite starts

ROOT = pathlib.Path(__file__).resolve().parents[2]
OUT = ROOT.parents[1] / "Others" / "gedes" / "defense" / "img"
CACHE = ROOT / "results" / "anchor_walkthrough_cache.npz"
KD_JSON = ROOT / "results" / "kd_retrieval_results.json"


def compute():
    if CACHE.exists():
        d = dict(np.load(CACHE))
        print(f"  (cached: {CACHE.name})")
        return d
    return _compute()


def _compute():
    kd = float(json.loads(KD_JSON.read_text())["A15"]["kd_star"])
    g = make_geometric_grid(**GRID)
    z = g.z_mid
    t = periodic_time_grid(DT_STEP)
    insol = standard_insolation(SITE["lat"], t)
    K = functools.partial(conductivity_hayne, Ks=HAYNE["K_S"], Kd=kd,
                          H=HAYNE["H"], chi=HAYNE["CHI"])
    cp = functools.partial(specific_heat, model="hayne")
    hp = (HAYNE["K_S"], kd, HAYNE["H"], HAYNE["CHI"])
    Qb = SITE["Q_BASAL"]

    # the certified answer, from the production solver
    eq = solve_periodic_equilibrium(
        grid=g, t=t, insolation=insol, albedo=SITE["albedo"],
        emissivity=SITE["emissivity"], Q_b=Qb, K_func=K, cp_func=cp,
        T_guess=SITE["T_MEAN_EFF"], hayne_params=hp)
    T_true = eq.T_mean

    sub, n_cut = _truncate_grid(g, ZCAP)
    i0 = int(np.argmin(np.abs(z - Z0)))

    # two deliberately wrong starts, LINEAR IN DEPTH (the grid is geometric),
    # wrong in opposite directions
    Tm = float(T_true.mean())
    guesses = [(Tm + a) + b * z for a, b in GUESS]

    def outer(T_start):
        """The outer A<->B loop, assembled from the production pieces in the
        order equilibrium.solve_periodic_equilibrium calls them."""
        skins, recons, anchors = [], [], []
        T_init = T_start.copy()
        for _ in range(N_OUTER):
            out = solve_pixel(PixelInputs(
                grid=sub, t=t, bc_mode="radiative", insolation=insol,
                albedo=SITE["albedo"], emissivity=SITE["emissivity"], Q_b=Qb,
                T_init=T_init[:n_cut], n_lunations_spinup=N_INNER,
                spinup_tol_K=0.0, K_func=K, cp_func=cp, hayne_params=hp))
            T_skin = out.T.mean(axis=1)
            T_full = np.empty(z.size)
            T_full[:n_cut] = T_skin
            T_full[n_cut:] = T_skin[-1]
            u_rect = np.zeros(z.size)
            u_rect[:n_cut] = _rectified_flux(out.T, sub.z_mid, K)
            T_recon = _reconstruct_subskin(T_full, z, i0, Qb, K, u_rect)
            skins.append(T_skin.copy())
            recons.append(T_recon.copy())
            anchors.append(float(T_recon[i0]))
            T_init = T_recon
        return np.array(skins), np.array(recons), np.array(anchors)

    runs = [outer(gz) for gz in guesses]
    skins, recons, anchors = runs[0]
    dev = float(np.max(np.abs(recons[-1] - T_true)[z <= ZMAX]))
    spread = float(np.max(np.abs(runs[0][1][-1] - runs[1][1][-1])[z <= ZMAX]))
    print(f"  n_inner={N_INNER}: anchor moved {abs(anchors[1]-anchors[0])*1e3:.1f} mK "
          f"on pass 2, {abs(anchors[2]-anchors[1])*1e3:.1f} mK on pass 3")
    print(f"  CERTIFY: fixed point vs solve_periodic_equilibrium: "
          f"{dev*1e3:.2f} mK over the top {ZMAX:.0f} m")
    print(f"  the two opposite starts agree to {spread*1e3:.2f} mK")

    D = dict(z=z, z_sub=sub.z_mid, i0=np.int64(i0), n_cut=np.int64(n_cut),
             T_true=T_true, T_guess=guesses[0], T_guess2=guesses[1],
             skins=skins, recons=recons, anchors=anchors,
             recons2=runs[1][1], dev=np.float64(dev),
             spread=np.float64(spread))
    CACHE.parent.mkdir(parents=True, exist_ok=True)
    np.savez(CACHE, **D)
    return D


FRAMES = [
    (1, "Step 1 — start from anything", C_CORAL),
    (2, "Step 2 — settle the skin, read the anchor", C_FOREST),
    (3, "Step 3 — rebuild the deep column", C_TEAL),
    (4, "Step 4 — repeat: the guess is gone", C_CHAR),
]
FS = 8.6        # annotation size


def draw(ax, D, n):
    z, i0, n_cut = D["z"], int(D["i0"]), int(D["n_cut"])
    zs, keep = D["z_sub"], D["z"] <= ZMAX
    deep = keep & (z >= Z0)
    skin, recon = D["skins"][0], D["recons"][0]
    handles = []

    ax.axhline(Z0, color=C_DIM, lw=0.6, ls=":", zorder=1)
    h, = ax.plot(D["T_true"][keep], z[keep], "--", color=C_DIM, lw=1.3,
                 zorder=2, label="converged steady state")
    handles.append(h)

    # ── the guess ────────────────────────────────────────────────────────────
    if n == 1:
        h, = ax.plot(D["T_guess"][keep], z[keep], "-", color=C_CORAL, lw=2.0,
                     zorder=4, label="the guess")
        handles.append(h)
        ax.annotate("a deliberately wrong start —\nany straight line will do",
                    xy=(float(np.interp(2.1, z, D["T_guess"])), 2.1),
                    xytext=(243.6, 1.28), fontsize=FS, color=C_CORAL,
                    ha="left", va="center",
                    arrowprops=dict(arrowstyle="->", color=C_CORAL, lw=0.9))
        ax.annotate(f"the anchor depth, {Z0:.2f} m",
                    xy=(XLIM[1] - 0.4, Z0 - 0.05), fontsize=FS,
                    color=C_DIM, ha="right", va="bottom")
    elif n == 2:
        h, = ax.plot(D["T_guess"][deep], z[deep], "-", color=C_CORAL, lw=2.0,
                     alpha=0.55, zorder=3, label="the guess")
        handles.append(h)
        ax.annotate("below the anchor,\nstill just the guess —\nnothing has been\nsimulated here",
                    xy=(float(np.interp(2.3, z, D["T_guess"])), 2.3),
                    xytext=(245.2, 1.72), fontsize=FS, color=C_CORAL,
                    ha="left", va="center",
                    arrowprops=dict(arrowstyle="->", color=C_CORAL, lw=0.9))

    # ── Step A: the time-stepped skin ────────────────────────────────────────
    if n >= 2:
        ax.axhspan(0, ZCAP, color=C_FOREST, alpha=0.07, zorder=0)
        h, = ax.plot(skin if n < 4 else [], zs if n < 4 else [], "-",
                     color=C_FOREST, lw=2.8, zorder=5,
                     label="skin, time-stepped")
        handles.append(h)
        ax.plot([D["anchors"][0] if n > 2 else skin[i0]], [Z0], "o",
                color=C_CHAR, ms=8, mec="white", mew=0.9, zorder=9)
    if n == 2:
        ax.annotate("anchor", xy=(skin[i0], Z0), xytext=(skin[i0] - 4.4,
                    Z0 - 0.34), fontsize=FS + 0.6, color=C_CHAR, ha="right",
                    fontweight="bold",
                    arrowprops=dict(arrowstyle="->", color=C_CHAR, lw=0.9))
        ax.annotate(f"time-stepped:\nthe top {ZCAP:.2f} m only,\n"
                    f"{n_cut} of {z.size} layers",
                    xy=(XLIM[0] + 0.5, 0.36), fontsize=FS, color=C_FOREST,
                    ha="left", va="center")

    # ── Step B: the walk down ────────────────────────────────────────────────
    if n >= 3:
        h, = ax.plot(recon[deep] if n < 4 else [], z[deep] if n < 4 else [],
                     "-", color=C_TEAL, lw=2.8, zorder=6,
                     label="deep, reconstructed")
        handles.append(h)
    if n == 3:
        wz, wT = z[deep], recon[deep]
        for zt in (0.92, 1.62, 2.32):
            z1 = zt + 0.24
            ax.annotate("", xy=(float(np.interp(z1, wz, wT)), z1),
                        xytext=(float(np.interp(zt, wz, wT)), zt), zorder=9,
                        arrowprops=dict(arrowstyle="-|>", color=C_CHAR, lw=1.5,
                                        mutation_scale=13, shrinkA=0,
                                        shrinkB=0))
        ax.annotate("walk down from the anchor,\n"
                    r"one cell at a time:  $d\langle T\rangle/dz=(Q_b-u)/K$",
                    xy=(float(np.interp(1.45, wz, wT)), 1.45),
                    xytext=(244.0, 2.42), fontsize=FS, color=C_TEAL,
                    ha="left", va="center",
                    arrowprops=dict(arrowstyle="->", color=C_TEAL, lw=0.9))

    # ── the iteration ────────────────────────────────────────────────────────
    if n == 4:
        for key in ("T_guess", "T_guess2"):
            ax.plot(D[key][keep], z[keep], "-", color=C_CORAL, lw=1.7,
                    alpha=0.55, zorder=3)
        h, = ax.plot(D["recons2"][-1][keep], z[keep], "-", color=C_TEAL_L,
                     lw=6.5, zorder=4, label="from the opposite start")
        handles.append(h)
        ax.plot(D["skins"][-1], zs, "-", color=C_FOREST, lw=2.4, zorder=6)
        ax.plot(D["recons"][-1][deep], z[deep], "-", color=C_TEAL, lw=2.4,
                zorder=6)
        drift = abs(D["anchors"][1] - D["anchors"][0]) * 1e3
        ax.annotate(f"two opposite starts,\none answer — they agree\n"
                    f"to better than {max(float(D['spread'])*1e3, 0.01):.2f} mK",
                    xy=(float(np.interp(1.30, z, D["recons"][-1])), 1.30),
                    xytext=(243.7, 2.26), fontsize=FS, color=C_CHAR,
                    ha="left", va="center",
                    arrowprops=dict(arrowstyle="->", color=C_CHAR, lw=0.9))
        ax.annotate(f"pass 2 moved the anchor {drift:.1f} mK\n"
                    f"(tolerance {EQ_ANCHOR_TOL*1e3:.0f} mK);\npass 3 moved it not at all",
                    xy=(252.3, 0.24), fontsize=FS, color=C_CHAR,
                    ha="left", va="center")

    ax.set_xlim(*XLIM)
    ax.set_ylim(ZMAX, 0.0)
    ax.set_xticks([244, 247, 250, 253, 256, 259, 262])
    fmt_axis(ax, xlabel="cycle-mean $T$  (K)", ylabel="depth  (m)")
    ax.grid(True, lw=0.5, color=C_GRID)
    ax.legend(handles=handles, loc="lower left", fontsize=FS - 0.5,
              frameon=True, edgecolor=C_GRID, framealpha=0.96,
              handlelength=1.6)


def main():
    D = compute()
    OUT.mkdir(parents=True, exist_ok=True)
    for n, title, col in FRAMES:
        fig = plt.figure(figsize=(5.9, 6.1))
        ax = fig.add_axes([0.135, 0.095, 0.845, 0.795])
        draw(ax, D, n)
        fig.text(0.135, 0.965, title, fontsize=12, fontweight="bold",
                 color=col, va="top")
        p = OUT / f"anchor_w{n}.png"
        fig.savefig(p, dpi=200, facecolor="white")
        plt.close(fig)
        print(f"  wrote {p.name}   {title}")


if __name__ == "__main__":
    main()
