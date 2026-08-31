#!/usr/bin/env python3
"""What the anchor method costs, in two pictures -- the missing half of the
anchor stills.

The four anchor stills show a green line being drawn, and drawing a line looks
free no matter how it was made. Nothing in them says the coral half cost
minutes and the green half cost a millisecond. This figure puts the price on.

LEFT -- cost is area. One rectangle = every (layer x lunar month) the brute
force must time-step. It splits into three:
    solid green   the work the anchor method actually does (time-stepping)
    pale green    months it never runs, because the skin settles in ~200
    pale teal     the deep column, reconstructed instead of time-stepped
The solid block is ~4 % of the rectangle, which is where the certified 21x
per-solve speed-up comes from. Layer counts (not depth) are the y axis on
purpose: cost scales with CELLS, and the geometric grid puts 44 of 69 of them
in the top 0.7 m, so a depth axis would overstate the saving. Not drawn: the
3 closing full-column lunations solve_periodic_equilibrium runs for
diagnostics -- 2 % of the anchored method's own cost, 0.1 % of the x axis, a
sub-pixel sliver.

RIGHT -- the same thing as wall clock, on a log axis, one sweep of 61 solves:
26.6 h, then /21 for not simulating the deep column, then /117 for the
compiled kernel, landing at 39 s. Naming both factors is the honest way to
quote 2465x: it is a product of an algorithmic and an implementation saving,
not one number.

Every figure on this page comes from results/speedup_benchmark.json; the
iteration counts come from a live production solve.

    python pipeline/figures/make_cost_figure.py
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
from lunar.equilibrium import _truncate_grid, solve_periodic_equilibrium
from lunar.grid import make_geometric_grid
from lunar.plotting.style import (C_CHAR, C_CORAL, C_DIM, C_FOREST, C_GRID,
                                  C_PLUM, C_TEAL, fmt_axis)
from lunar.properties import conductivity_hayne, specific_heat
from lunar.solver import periodic_time_grid, standard_insolation

SITE = SITES["A15"]
ZSPLIT = EQ_Z_ANCHOR + 0.15          # Step A's truncation depth
STAGE_N_INNER = {0.25: 4}            # stage 1 is fixed at 4 (equilibrium.py)
N_FINAL_LUN = 3                      # the closing full-column diagnostic run

ROOT = pathlib.Path(__file__).resolve().parents[2]
OUT = ROOT.parents[1] / "Others" / "gedes" / "defense" / "img"
BENCH = ROOT / "results" / "speedup_benchmark.json"
KD_JSON = ROOT / "results" / "kd_retrieval_results.json"


def counts():
    """Layer and lunation counts, from a live production solve."""
    from lunar.config import EQ_N_INNER
    kd = float(json.loads(KD_JSON.read_text())["A15"]["kd_star"])
    g = make_geometric_grid(**GRID)
    _, n_cut = _truncate_grid(g, ZSPLIT)
    t = periodic_time_grid(DT_STEP)
    K = functools.partial(conductivity_hayne, Ks=HAYNE["K_S"], Kd=kd,
                          H=HAYNE["H"], chi=HAYNE["CHI"])
    eq = solve_periodic_equilibrium(
        grid=g, t=t, insolation=standard_insolation(SITE["lat"], t),
        albedo=SITE["albedo"], emissivity=SITE["emissivity"],
        Q_b=SITE["Q_BASAL"], K_func=K,
        cp_func=functools.partial(specific_heat, model="hayne"),
        T_guess=SITE["T_MEAN_EFF"],
        hayne_params=(HAYNE["K_S"], kd, HAYNE["H"], HAYNE["CHI"]))
    # every outer iteration time-steps stage["n_in"] lunations on the sub-grid
    skin_lun = sum(STAGE_N_INNER.get(float(h[0]), EQ_N_INNER)
                   for h in eq.history)
    print(f"  {g.n_layers} layers, Step A on {n_cut} of them ({ZSPLIT} m); "
          f"{len(eq.history)} outer iterations = {skin_lun} lunations "
          f"+ {N_FINAL_LUN} full-column")
    return dict(n_layers=g.n_layers, n_cut=n_cut, skin_lun=skin_lun)


def draw_area(ax, C, b):
    """Left panel: every (layer x lunar month) the brute force pays for."""
    n, cut, brute = C["n_layers"], C["n_cut"], b["N_converge_lun"]
    skin = C["skin_lun"]

    # what brute force must do, split into what the anchor method keeps and
    # the two blocks it drops
    ax.add_patch(plt.Rectangle((0, cut), brute, n - cut, fc=C_TEAL,
                               alpha=0.13, ec="none", zorder=1))
    ax.add_patch(plt.Rectangle((skin, 0), brute - skin, cut, fc=C_FOREST,
                               alpha=0.15, ec="none", zorder=1))
    ax.add_patch(plt.Rectangle((0, 0), skin, cut, fc=C_FOREST, alpha=0.90,
                               ec="none", zorder=3))
    ax.add_patch(plt.Rectangle((0, 0), brute, n, fc="none", ec=C_CHAR,
                               lw=1.2, zorder=4))
    ax.axhline(cut, color=C_CHAR, lw=1.0, ls=":", zorder=5)

    ax.set_xlim(-60, brute * 1.04)
    ax.set_ylim(n, 0)
    fmt_axis(ax, xlabel="lunar months simulated", ylabel="model layers")
    ax.grid(False)
    ax.set_xticks([0, 1000, 2000, 3000])
    ax.tick_params(labelsize=10)
    ax.xaxis.label.set_size(11.5)
    ax.yaxis.label.set_size(11.5)


TICKS = [(10, "10 s"), (60, "1 min"), (600, "10 min"),
         (3600, "1 h"), (36000, "10 h")]


def draw_clock(ax, b):
    """Right panel: the same saving as wall clock, both factors named."""
    t_brute = b["sweep_brute_h"] * 3600.0
    t_anch = b["sweep_anchored_min"] * 60.0
    t_fast = b["sweep_fast_min"] * 60.0
    lv = [t_brute, t_anch, t_fast]

    for i, (t, col) in enumerate(zip(lv, (C_DIM, C_FOREST, C_CHAR))):
        ax.plot([i - 0.34, i + 0.34], [t, t], lw=4.0, color=col, zorder=4,
                solid_capstyle="butt")
        ax.annotate(_fmt(t), xy=(i, t), xytext=(0, 9),
                    textcoords="offset points", ha="center", fontsize=12,
                    fontweight="bold", color=col, zorder=6)
    for i, (col, fac) in enumerate(((C_TEAL, b["speedup_per_solve"]),
                                    (C_PLUM, b["speedup_kernel_over_generic"]))):
        ax.annotate("", xy=(i + 0.34, lv[i + 1]), xytext=(i + 0.34, lv[i]),
                    zorder=5,
                    arrowprops=dict(arrowstyle="-|>", lw=2.2, color=col,
                                    fc=col, mutation_scale=18, shrinkA=0,
                                    shrinkB=0))
        ax.annotate(f"÷{fac:.0f}", xy=(i + 0.34, np.sqrt(lv[i] * lv[i + 1])),
                    xytext=(7, 0), textcoords="offset points", va="center",
                    fontsize=12, fontweight="bold", color=col, zorder=6)

    ax.set_yscale("log")
    ax.set_ylim(t_fast / 3.0, t_brute * 3.0)
    ax.set_xlim(-0.55, 2.75)
    ax.set_yticks([t for t, _ in TICKS])
    ax.set_yticklabels([s for _, s in TICKS])
    ax.set_xticks([0, 1, 2])
    ax.set_xticklabels(["brute\nforce", "anchor\nmethod", "+ compiled\nkernel"])
    fmt_axis(ax, xlabel="", ylabel="time for one K$_d$ sweep")
    ax.grid(False)
    ax.grid(True, axis="y", which="major", lw=0.5, color=C_GRID)
    ax.tick_params(labelsize=10)
    ax.yaxis.label.set_size(11.5)


def _fmt(s):
    if s >= 3600:
        return f"{s/3600:.1f} h"
    if s >= 120:
        return f"{s/60:.0f} min"
    return f"{s:.0f} s"


def main():
    b = json.loads(BENCH.read_text())
    C = counts()
    OUT.mkdir(parents=True, exist_ok=True)
    fig = plt.figure(figsize=(10.4, 5.2))
    gs = fig.add_gridspec(1, 2, width_ratios=[1.25, 1.0], left=0.075,
                          right=0.975, top=0.855, bottom=0.135, wspace=0.26)
    draw_area(fig.add_subplot(gs[0]), C, b)
    draw_clock(fig.add_subplot(gs[1]), b)
    fig.text(0.075, 0.955, "What the shortcut is worth", fontsize=13,
             fontweight="bold", color=C_TEAL, va="top")
    p = OUT / "anchor_cost.png"
    fig.savefig(p, dpi=200, facecolor="white")
    plt.close(fig)
    print(f"  wrote {p}")


if __name__ == "__main__":
    main()
