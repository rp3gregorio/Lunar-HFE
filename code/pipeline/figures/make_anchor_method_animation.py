#!/usr/bin/env python3
"""Explainer animation, act 2 -- THE METHOD: the flux-anchored solve.

Walks the whole two-stage method phase by phase on real Apollo 15 physics:

  1. initial guess           -- a rough linear profile; skin and deep wrong
  2. Step A: settle the skin -- time-step ONLY the shallow column
  3. read the anchor         -- <T>(z0) at z0 = 0.55 m, below the wave
  4. Step B: walk down       -- add slope*dz node by node,
                                d<T>/dz = (Q_b - u_rect)/K
  5. repeat A <-> B          -- feed the rebuilt column back in
  6. converged               -- the anchor stops moving; this IS the
                                periodic steady state

Design (2026-07-17 redesign): fixed banner with a step counter and a
one-sentence explainer per phase (no jumping suptitle), a static legend
fully outside the axes, larger type, and holds at each phase change.
Right panel: the REAL per-outer-cycle anchor drift from
EquilibriumResult.history, contracting to the 0.005 K tolerance.

Outputs (filenames unchanged -- notebook 02 and the guidebook embed them):
  figures/anim/anchor_method_steps.gif
  figures/anchor_method_filmstrip.pdf
Run: python code/pipeline/figures/make_anchor_method_animation.py
"""
from __future__ import annotations
import functools
import pathlib
import sys

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation, PillowWriter
from matplotlib.lines import Line2D

_REPO = pathlib.Path(__file__).resolve().parents[1].parent
sys.path.insert(0, str(_REPO))
sys.path.insert(0, str(_REPO / "src"))

from lunar.config import SITES, GRID, HAYNE, DT_STEP
from lunar.grid import make_geometric_grid
from lunar.properties import conductivity_hayne, specific_heat
from lunar.solver import standard_insolation, periodic_time_grid
from lunar.equilibrium import solve_periodic_equilibrium
from lunar.plotting.style import (JGR_FULL, C_A15, C_HAYNE, C_CORAL, C_CHAR,
                                  C_DIM, C_GRID, C_FOREST)

ANIM = _REPO / ".." / "figures" / "anim"
FIG = _REPO / ".." / "figures"
SITE = SITES["A15"]
KD = 4.60e-3
Z0 = 0.55
ZMAX = 3.0
TOL = 0.005
XLIM = (242.0, 262.0)


# ── real data: one A15 solve, the slope walk, and the drift history ──────────
def _compute():
    g = make_geometric_grid(**GRID)
    z, dz = g.z_mid, g.dz
    t = periodic_time_grid(DT_STEP)
    insol = standard_insolation(SITE["lat"], t)
    K = functools.partial(conductivity_hayne, Ks=HAYNE["K_S"], Kd=KD,
                          H=HAYNE["H"], chi=HAYNE["CHI"])
    cp = functools.partial(specific_heat, model="hayne")
    Qb = SITE["Q_BASAL"]
    # n_inner=4 exposes the outer-loop geometric contraction cycle by cycle
    # (~9 drift points); production n_inner=96 converges in ~2 cycles, which
    # hides the A<->B iteration this teaching animation is about. Same
    # certified attractor either way.
    eq = solve_periodic_equilibrium(
        grid=g, t=t, insolation=insol, albedo=SITE["albedo"],
        emissivity=SITE["emissivity"], Q_b=Qb, K_func=K, cp_func=cp,
        T_guess=SITE["T_MEAN_EFF"], n_inner=4)
    T_target = eq.T_mean

    i0 = int(np.argmin(np.abs(z - Z0)))
    # Step B: walk the deep column down from the anchor by the slope rule
    T_walk = T_target.copy()
    for i in range(i0, z.size - 1):
        slope = Qb / float(K(np.array([T_walk[i]]), np.array([z[i]]))[0])
        T_walk[i + 1] = T_walk[i] + slope * dz[i]

    # a deliberately-wrong initial guess spanning the plotted window
    T_guess = np.linspace(float(T_target.mean()) - 4.0,
                          float(T_target.mean()) + 7.0, z.size)

    drift = np.array([h[3] for h in eq.history], dtype=float)
    drift = drift[np.isfinite(drift) & (drift > 0)]

    slope_anch = Qb / float(K(np.array([T_target[i0]]), np.array([z[i0]]))[0])
    return dict(z=z, dz=dz, i0=i0, T_target=T_target, T_walk=T_walk,
                T_guess=T_guess, drift=drift, Qb=Qb, K=K, slope=slope_anch)


# ── the six phases: (step number, name, explainer, kind, hold frames) ────────
PHASES = [
    (1, "start from a rough guess",
     "a straight-line column; the skin and the deep are both wrong",
     "guess", 6),
    (2, "Step A: settle the skin",
     "time-step ONLY the thin shallow column -- it is fast; the deep is left alone",
     "stepA", 10),          # morph frames
    (3, "read the anchor",
     "at $z_0=0.55$ m the daily wave is dead: the settled $\\langle T\\rangle(z_0)$ is trustworthy",
     "anchor", 5),
    (4, "Step B: walk down from the anchor",
     "no time-stepping: each next node is $T + (Q_b/K)\\,\\Delta z$ -- energy conservation",
     "stepB", 16),          # walk frames
    (5, "repeat A $\\leftrightarrow$ B",
     "the rebuilt deep column nudges the skin; iterate until nothing moves",
     "repeat", 5),
    (6, "converged",
     "the anchor drift is below 0.005 K -- this IS the periodic steady state",
     "done", 9),
]


def _script():
    seq = []
    for num, name, expl, kind, hold in PHASES:
        for h in range(hold):
            prog = h / max(1, hold - 1)
            seq.append((num, name, expl, kind, prog))
    return seq


def _draw_column(ax, D, kind, prog, arrow_holder):
    """Draw the left panel for one frame (axes cleared by caller)."""
    z, i0 = D["z"], D["i0"]
    m = z <= ZMAX
    sk = z <= Z0
    deep_idx = [i for i in range(i0, z.size) if z[i] <= ZMAX]

    ax.plot(D["T_target"][m], z[m], "--", color=C_DIM, lw=1.5)

    if kind == "guess":
        ax.plot(D["T_guess"][m], z[m], "-", color=C_CORAL, lw=2.6)
    elif kind == "stepA":
        Tsk = (1 - prog) * D["T_guess"] + prog * D["T_target"]
        cur = D["T_guess"].copy(); cur[sk] = Tsk[sk]
        ax.plot(cur[sk], z[sk], "-", color=C_FOREST, lw=3.2)
        ax.plot(cur[m & ~sk], z[m & ~sk], "-", color=C_CORAL, lw=1.8, alpha=0.45)
    else:
        ax.plot(D["T_target"][sk], z[sk], "-", color=C_FOREST, lw=3.2)

    if kind in ("anchor", "stepB", "repeat", "done"):
        ax.plot(D["T_target"][i0], Z0, "o", color=C_CHAR, ms=11, zorder=6,
                mec="white", mew=1.0)
        ax.annotate("anchor", xy=(D["T_target"][i0], Z0),
                    xytext=(D["T_target"][i0] - 5.5, Z0 - 0.28),
                    fontsize=10, color=C_CHAR, ha="right", fontweight="bold",
                    arrowprops=dict(arrowstyle="->", color=C_CHAR, lw=1.0))

    if kind == "stepB":
        k = deep_idx[min(int(round(prog * (len(deep_idx) - 1))), len(deep_idx) - 1)]
        built = (z >= Z0) & (z <= z[k])
        ax.plot(D["T_walk"][built], z[built], "-", color=C_HAYNE, lw=3.4)
        if k < z.size - 1:                     # slope vector at the build front
            slope = D["Qb"] / float(D["K"](np.array([D["T_walk"][k]]),
                                           np.array([z[k]]))[0])
            dzz = 0.24
            ax.annotate("", xy=(D["T_walk"][k] + slope * dzz, z[k] + dzz),
                        xytext=(D["T_walk"][k], z[k]),
                        arrowprops=dict(arrowstyle="-|>", color=C_A15, lw=2.8),
                        zorder=7)
    elif kind in ("repeat", "done"):
        built = (z >= Z0) & m
        ax.plot(D["T_walk"][built], z[built], "-", color=C_HAYNE, lw=3.4)

    if kind in ("stepB", "repeat", "done"):
        ax.text(0.965, 0.06,
                r"$\dfrac{d\langle T\rangle}{dz}=\dfrac{Q_b}{K}\approx$"
                f"{D['slope']:.1f} K/m",
                transform=ax.transAxes, fontsize=10.5, color=C_A15,
                ha="right", va="bottom",
                bbox=dict(boxstyle="round,pad=0.38", fc="white", ec=C_A15, lw=1.1))

    ax.set_xlim(*XLIM)
    ax.set_ylim(ZMAX, 0)
    ax.axhline(Z0, color=C_DIM, lw=0.6, ls=":")
    ax.set_xlabel("cycle-mean temperature  [K]", fontsize=10.5)
    ax.set_ylabel("depth  [m]", fontsize=10.5)
    ax.set_title("(a)  building the temperature column", fontsize=11,
                 color=C_CHAR, loc="left")
    ax.grid(alpha=0.20)


def _draw_drift(ax, D, frac, kind):
    drift = D["drift"]
    n_show = max(1, int(round(frac * len(drift))))
    xs = np.arange(1, n_show + 1)
    ax.plot(np.arange(1, len(drift) + 1), drift, "-", color=C_FOREST,
            alpha=0.20, lw=1.2)                          # ghost of full path
    ax.plot(xs, drift[:n_show], "-o", color=C_FOREST, ms=7, lw=1.8,
            mec="white", mew=0.9, zorder=3)
    ax.axhline(TOL, color=C_CORAL, ls="--", lw=1.4)
    ax.text(0.8, TOL * 0.86, "tolerance 0.005 K", color=C_CORAL,
            fontsize=9, ha="left", va="top")
    if kind == "done":
        ax.text(0.96, 0.90, "converged", transform=ax.transAxes,
                fontsize=11.5, color=C_FOREST, ha="right", fontweight="bold")
    ax.set_yscale("log")
    ax.set_xlim(0.5, len(drift) + 0.5)
    ax.set_ylim(min(drift.min() * 0.6, TOL * 0.5), drift.max() * 1.7)
    ax.set_xlabel("outer iteration (one A $\\leftrightarrow$ B round)", fontsize=10.5)
    ax.set_ylabel("anchor drift  [K]", fontsize=10.5)
    ax.set_title("(b)  proof: the anchor stops moving", fontsize=11,
                 color=C_CHAR, loc="left")
    ax.grid(True, which="both", color=C_GRID, lw=0.4, alpha=0.5)


def main():
    D = _compute()
    seq = _script()

    fig, (axL, axR) = plt.subplots(1, 2, figsize=(9.8, 5.0),
                                   gridspec_kw={"width_ratios": [1.3, 1.0]})
    fig.subplots_adjust(top=0.72, bottom=0.115, left=0.075, right=0.975,
                        wspace=0.28)

    # fixed banner: title + step line + explainer line (positions never move)
    fig.text(0.075, 0.950, "The flux-anchored method",
             fontsize=15, fontweight="bold", color=C_CHAR, ha="left")
    step_txt = fig.text(0.075, 0.878, "", fontsize=12, color=C_A15,
                        ha="left", fontweight="bold")
    expl_txt = fig.text(0.075, 0.818, "", fontsize=10, color=C_DIM, ha="left")

    # static legend fully outside the axes (top right)
    handles = [
        Line2D([], [], color=C_CORAL, lw=2.4, label="initial guess"),
        Line2D([], [], color=C_FOREST, lw=2.8, label="skin (Step A)"),
        Line2D([], [], color=C_CHAR, marker="o", lw=0, ms=8, label="anchor"),
        Line2D([], [], color=C_HAYNE, lw=2.8, label="deep (Step B walk)"),
        Line2D([], [], color=C_DIM, lw=1.4, ls="--", label="true steady state"),
    ]
    fig.legend(handles=handles, loc="upper right", bbox_to_anchor=(0.975, 1.0),
               ncols=2, frameon=True, edgecolor=C_GRID, framealpha=0.95,
               fontsize=8.4, columnspacing=1.1, handlelength=1.6)

    arrow_holder = {}

    def update(si):
        num, name, expl, kind, prog = seq[si]
        axL.clear(); axR.clear()
        _draw_column(axL, D, kind, prog, arrow_holder)
        _draw_drift(axR, D, (si + 1) / len(seq), kind)
        step_txt.set_text(f"Step {num} of 6 — {name}")
        expl_txt.set_text(expl)
        return []

    anim = FuncAnimation(fig, update, frames=len(seq), blit=False)
    ANIM.mkdir(parents=True, exist_ok=True)
    out = ANIM / "anchor_method_steps.gif"
    anim.save(str(out), writer=PillowWriter(fps=6), dpi=100)
    plt.close(fig)
    print(f"  -> {out.relative_to(_REPO)}  ({len(seq)/6:.1f} s, "
          f"slope {D['slope']:.1f} K/m, {len(D['drift'])} drift points)")

    _filmstrip(D)


def _filmstrip(D):
    """4-panel LaTeX still: guess -> Step A -> Step B walk -> converged."""
    frames = [("1. rough guess", "guess", 0.0),
              ("2. Step A: skin settles", "stepA", 1.0),
              ("3-4. Step B: walk down", "stepB", 0.62),
              ("5-6. converged", "done", 1.0)]
    fig = plt.figure(figsize=(JGR_FULL, 3.6))
    gs = fig.add_gridspec(1, 4, wspace=0.30, left=0.06, right=0.985,
                          top=0.78, bottom=0.16)
    for j, (ttl, kind, prog) in enumerate(frames):
        ax = fig.add_subplot(gs[0, j])
        _draw_column(ax, D, kind, prog, {})
        ax.set_title(ttl, fontsize=9.5, color=C_CHAR, loc="left")
        ax.set_xlabel("temperature  [K]", fontsize=9)
        if j == 0:
            ax.set_ylabel("depth  [m]", fontsize=9)
        else:
            ax.set_ylabel(""); ax.set_yticklabels([])
    fig.suptitle("The flux-anchored method, step by step "
                 "(Apollo 15, $K_d = 4.60$ mW m$^{-1}$K$^{-1}$)",
                 fontsize=11.5, color=C_CHAR, fontweight="bold", y=0.945)
    out = FIG / "anchor_method_filmstrip.pdf"
    fig.savefig(out)
    plt.close(fig)
    print(f"  -> {out.relative_to(_REPO)}")


if __name__ == "__main__":
    main()
