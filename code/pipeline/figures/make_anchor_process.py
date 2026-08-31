#!/usr/bin/env python3
"""The anchor method's process, in four frames. Nothing else.

    step1  simulate only the top
    step2  read one temperature there
    step3  add your way down
    step4  run it again -- nothing moves. Done.

One column, drawn identically in all four, so the series reads as one picture
filling in. No legend, no second panel, no side story: this file answers the
question "what do you actually do?" and nothing else.

Real numbers throughout: the temperatures are the production solve's own
cycle-mean profile at Apollo 15, K_d* from results/kd_retrieval_results.json,
and the pass-1/pass-2 anchor values come from running the production Step A
twice, the way solve_periodic_equilibrium does.

    python pipeline/figures/make_anchor_process.py
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
from lunar.equilibrium import (_reconstruct_subskin, _rectified_flux,
                               _truncate_grid, solve_periodic_equilibrium)
from lunar.grid import make_geometric_grid
from lunar.plotting.style import (C_CHAR, C_DIM, C_FOREST, C_NEUTRAL, C_TEAL,
                                  fmt_axis)
from lunar.properties import conductivity_hayne, specific_heat
from lunar.solver import (PixelInputs, periodic_time_grid, solve_pixel,
                          standard_insolation)

SITE = SITES["A15"]
Z0 = EQ_Z_ANCHOR
ZCAP = Z0 + 0.15
ZBOT = 3.55
LEVELS = (0.55, 1.0, 1.5, 2.0, 2.5, 3.0)
COL_L, COL_R = 0.14, 0.56
COL_FILL = "#F0EEEA"

ROOT = pathlib.Path(__file__).resolve().parents[2]
OUT = ROOT.parents[1] / "Others" / "gedes" / "defense" / "img"
CACHE = ROOT / "results" / "anchor_process_cache.npz"
KD_JSON = ROOT / "results" / "kd_retrieval_results.json"


def compute():
    if CACHE.exists():
        print(f"  (cached: {CACHE.name})")
        return dict(np.load(CACHE))

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

    eq = solve_periodic_equilibrium(
        grid=g, t=t, insolation=insol, albedo=SITE["albedo"],
        emissivity=SITE["emissivity"], Q_b=Qb, K_func=K, cp_func=cp,
        T_guess=SITE["T_MEAN_EFF"], hayne_params=hp)

    # two production passes, to measure how much the second one moves
    sub, n_cut = _truncate_grid(g, ZCAP)
    i0 = int(np.argmin(np.abs(z - Z0)))
    T_init = SITE["T_MEAN_EFF"] + 3.0 * z
    anchors = []
    from lunar.config import EQ_N_INNER
    for _ in range(2):
        out = solve_pixel(PixelInputs(
            grid=sub, t=t, bc_mode="radiative", insolation=insol,
            albedo=SITE["albedo"], emissivity=SITE["emissivity"], Q_b=Qb,
            T_init=T_init[:n_cut], n_lunations_spinup=EQ_N_INNER,
            spinup_tol_K=0.0, K_func=K, cp_func=cp, hayne_params=hp))
        Ts = out.T.mean(axis=1)
        full = np.empty(z.size)
        full[:n_cut] = Ts
        full[n_cut:] = Ts[-1]
        u = np.zeros(z.size)
        u[:n_cut] = _rectified_flux(out.T, sub.z_mid, K)
        T_init = _reconstruct_subskin(full, z, i0, Qb, K, u)
        anchors.append(float(T_init[i0]))
    print(f"  anchor after pass 1: {anchors[0]:.3f} K, "
          f"after pass 2: {anchors[1]:.3f} K "
          f"({abs(anchors[1]-anchors[0])*1e3:.1f} mK)")

    D = dict(z=z, z_face=g.z_face, T=eq.T_mean, anchors=np.array(anchors))
    CACHE.parent.mkdir(parents=True, exist_ok=True)
    np.savez(CACHE, **D)
    return D


def at(D, depth):
    return float(D["T"][int(np.argmin(np.abs(D["z"] - depth)))])


STEPS = [
    (1, "Step 1", "Simulate only the top", C_FOREST),
    (2, "Step 2", "Read one temperature there", C_CHAR),
    (3, "Step 3", "Add your way down", C_TEAL),
    (4, "Step 4", "Run it again — nothing moves", C_TEAL),
]


def draw(D, n, label, title, col):
    fig = plt.figure(figsize=(7.2, 6.8))
    ax = fig.add_axes([0.115, 0.06, 0.87, 0.80])

    ax.add_patch(plt.Rectangle((COL_L, 0.0), COL_R - COL_L, ZBOT,
                               fc=COL_FILL, ec="none", zorder=1))
    for zf in D["z_face"][D["z_face"] <= ZBOT]:
        ax.plot([COL_L, COL_R], [zf, zf], lw=0.35, color=C_NEUTRAL,
                alpha=0.22, zorder=2)
    ax.plot([COL_L, COL_R], [0, 0], lw=2.2, color=C_CHAR, zorder=8)

    # the simulated skin, from step 1 onward
    ax.add_patch(plt.Rectangle((COL_L, 0.0), COL_R - COL_L, ZCAP,
                               fc=C_FOREST, alpha=0.22, ec="none", zorder=3))
    ax.annotate("simulated", xy=(COL_L + 0.02, 0.22), fontsize=13,
                fontweight="bold", color=C_FOREST, ha="left", va="center",
                zorder=9)
    if n == 1:
        ax.annotate("not simulated", xy=(COL_L + 0.02, 1.1), fontsize=13,
                    fontweight="bold", color=C_DIM, ha="left", va="center",
                    zorder=9)
    if n >= 3:
        ax.add_patch(plt.Rectangle((COL_L, ZCAP), COL_R - COL_L, ZBOT - ZCAP,
                                   fc=C_TEAL, alpha=0.14, ec="none", zorder=3))
        ax.annotate("added up,\nnever simulated", xy=(COL_L + 0.02, 1.28),
                    fontsize=13, fontweight="bold", color=C_TEAL, ha="left",
                    va="center", zorder=9)

    xr = COL_R + 0.06
    if n >= 2:
        ax.plot([COL_L, COL_R], [Z0, Z0], lw=1.0, ls=":", color=C_CHAR,
                zorder=5)
        ax.plot([0.5 * (COL_L + COL_R)], [Z0], "o", ms=11, color=C_CHAR,
                mec="white", mew=1.8, zorder=9)
        ax.annotate(f"{at(D, Z0):.1f} K", xy=(xr, Z0), fontsize=17,
                    fontweight="bold", color=C_CHAR, ha="left", va="center")
    if n == 2:
        ax.annotate("this one number", xy=(xr, Z0 + 0.30), fontsize=13,
                    color=C_DIM, ha="left", va="center")

    if n >= 3:
        prev = (Z0, at(D, Z0))
        for lv in LEVELS[1:]:
            T = at(D, lv)
            ax.plot([COL_L, COL_R], [lv, lv], lw=1.0, ls=":", color=C_DIM,
                    zorder=5)
            ax.annotate(f"+ {T - prev[1]:.2f}",
                        xy=(xr + 0.01, 0.5 * (lv + prev[0])), fontsize=14,
                        color=C_TEAL, ha="left", va="center")
            ax.annotate(f"{T:.1f} K", xy=(xr, lv), fontsize=17,
                        fontweight="bold", color=C_TEAL, ha="left",
                        va="center")
            prev = (lv, T)

    if n == 4:
        d = abs(float(D["anchors"][1]) - float(D["anchors"][0]))
        ax.annotate(f"second pass moves\nthis by {d*1e3:.0f} thousandths\n"
                    f"of a degree — stop", xy=(0.5 * (COL_L + COL_R), Z0),
                    xytext=(COL_L + 0.02, 0.95), fontsize=13, color=C_CHAR,
                    ha="left", va="center", zorder=9,
                    arrowprops=dict(arrowstyle="->", color=C_CHAR, lw=1.2))

    ax.set_xlim(0.0, 1.0)
    ax.set_ylim(3.72, -0.12)
    ax.set_xticks([])
    ax.set_yticks([0, 1, 2, 3])
    fmt_axis(ax, xlabel="", ylabel="depth  (m)")
    ax.grid(False)
    ax.spines["bottom"].set_visible(False)
    ax.spines["left"].set_bounds(0, 3)
    ax.tick_params(labelsize=12)
    ax.yaxis.label.set_size(13)

    fig.text(0.115, 0.975, label, fontsize=13, fontweight="bold", color=col,
             va="top")
    fig.text(0.115, 0.930, title, fontsize=19, fontweight="bold", color=col,
             va="top")

    OUT.mkdir(parents=True, exist_ok=True)
    p = OUT / f"step{n}.png"
    fig.savefig(p, dpi=200, facecolor="white")
    plt.close(fig)
    print(f"  wrote {p.name}   {title}")


def main():
    D = compute()
    for n, label, title, col in STEPS:
        draw(D, n, label, title, col)


if __name__ == "__main__":
    main()
