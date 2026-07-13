#!/usr/bin/env python3
"""Step-by-step animation of the WHOLE flux-anchored method.

Emulates the guidebook's worked "sample problem" (the Step-B slope walk,
make_reconstruct_animation) but embeds it in the complete two-stage story
so a viewer sees how the method actually runs, phase by phase:

  1. initial guess           — a rough linear profile; skin and deep wrong
  2. Step A: settle the skin — time-step ONLY the shallow column to its
                               cycle-mean (the deep column is left alone)
  3. read the anchor         — <T>(z0) at z0 = 0.55 m, below the wave
  4. Step B: walk down       — from the anchor, add slope*step at every
                               node using dT/dz = (Q_b - u_rect)/K  ← the
                               sample problem, animated node by node
  5. repeat A <-> B          — set T_init <- T_recon and iterate
  6. converged               — the anchor stops moving; this IS the
                               periodic steady state

Left panel: the temperature column being built. Right panel: the REAL
per-outer-cycle anchor drift from EquilibriumResult.history, accumulating
to the 0.005 K tolerance (geometric contraction).

Outputs (GIF + a LaTeX-embeddable filmstrip, per the figure conventions):
  results/anim/anchor_method_steps.gif
  docs/guidebook/figures/anchor_method_filmstrip.pdf
Run: python pipeline/figures/make_anchor_method_animation.py
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

ANIM = _REPO / "results" / "anim"
FIG = _REPO / "results" / "figures"
SITE = SITES["A15"]
KD = 4.60e-3
Z0 = 0.55
ZMAX = 3.0
TOL = 0.005


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
    # (~9 drift points, 46 -> 5 mK); production n_inner=96 converges in ~2
    # cycles because each cycle over-relaxes the skin, which hides the
    # iteration mechanism this teaching animation is about. Same certified
    # attractor either way; only the number of visible outer steps differs.
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

    # a deliberately-wrong initial guess: a straight isothermal-ish ramp
    # across the whole column (both the flat skin and the steep deep
    # gradient of the true profile are absent) -- clearly visible as the
    # "before" the two stages fix, spanning the plotted 242-262 K window
    T_guess = np.linspace(float(T_target.mean()) - 4.0,
                          float(T_target.mean()) + 7.0, z.size)

    # real per-outer-cycle anchor drift (geometric contraction to TOL)
    drift = np.array([h[3] for h in eq.history], dtype=float)
    drift = drift[np.isfinite(drift) & (drift > 0)]

    slope_anch = Qb / float(K(np.array([T_target[i0]]), np.array([z[i0]]))[0])
    return dict(z=z, dz=dz, i0=i0, T_target=T_target, T_walk=T_walk,
                T_guess=T_guess, drift=drift, Qb=Qb, K=K, slope=slope_anch)


# ── phase script: (label, kind, progress-0..1) per frame ─────────────────────
def _frames(n_deep):
    seq = []
    seq += [("1.  initial guess: a rough linear profile (skin and deep both wrong)",
             "guess", 0.0)] * 5
    for a in np.linspace(0, 1, 10):
        seq.append(("2.  Step A: time-step ONLY the skin until its cycle-mean settles",
                    "stepA", a))
    seq += [(r"3.  read the anchor $\langle T\rangle(z_0)$ at $z_0=0.55$ m "
             "(below the diurnal wave)", "anchor", 1.0)] * 4
    for k in range(0, n_deep, 2):
        seq.append((r"4.  Step B: from the anchor, walk down using "
                    r"$d\langle T\rangle/dz=(Q_b-u_{\rm rect})/K$", "stepB",
                    k / max(1, n_deep - 1)))
    seq += [(r"5.  set $T_{\rm init}\leftarrow T_{\rm recon}$ and repeat "
             r"Step A $\leftrightarrow$ Step B", "repeat", 1.0)] * 4
    seq += [("6.  converged: the anchor stops moving — this IS the periodic steady state",
             "done", 1.0)] * 6
    return seq


def _draw(axL, axR, phase, D, seq, si):
    z, i0, dz = D["z"], D["i0"], D["dz"]
    m = z <= ZMAX
    deep_idx = [i for i in range(i0, z.size) if z[i] <= ZMAX]
    label, kind, prog = phase
    axL.clear(); axR.clear()

    # target always faint (the goal)
    axL.plot(D["T_target"][m], z[m], "--", color=C_DIM, lw=1.4,
             label="true steady state (goal)")

    sk = z <= Z0
    if kind == "guess":
        axL.plot(D["T_guess"][m], z[m], "-", color=C_CORAL, lw=2.4,
                 label="current profile (guess)")
    elif kind == "stepA":
        # skin morphs guess -> true; deep stays at the (still wrong) guess
        Tsk = (1 - prog) * D["T_guess"] + prog * D["T_target"]
        cur = D["T_guess"].copy(); cur[sk] = Tsk[sk]
        axL.plot(cur[sk], z[sk], "-", color=C_FOREST, lw=3,
                 label="skin, settling (Step A)")
        axL.plot(cur[m & ~sk], z[m & ~sk], "-", color=C_CORAL, lw=1.6,
                 alpha=0.5, label="deep, not yet rebuilt")
    else:
        # skin is settled from here on
        axL.plot(D["T_target"][sk], z[sk], "-", color=C_FOREST, lw=3,
                 label="skin (settled, Step A)")

    if kind in ("anchor", "stepB", "repeat", "done"):
        axL.plot(D["T_target"][i0], Z0, "o", color=C_CHAR, ms=10, zorder=6)
        axL.annotate("anchor", xy=(D["T_target"][i0], Z0),
                     xytext=(D["T_target"][i0] - 10.5, Z0 - 0.12),
                     fontsize=9, color=C_CHAR, ha="right",
                     arrowprops=dict(arrowstyle="->", color=C_CHAR, lw=0.9))

    if kind == "stepB":
        k = deep_idx[min(int(round(prog * (len(deep_idx) - 1))), len(deep_idx) - 1)]
        built = (z >= Z0) & (z <= z[k])
        axL.plot(D["T_walk"][built], z[built], "-", color=C_HAYNE, lw=3.2,
                 label="deep profile, built by the slope rule")
        if k < z.size - 1:                       # slope vector at the build front
            slope = D["Qb"] / float(D["K"](np.array([D["T_walk"][k]]),
                                           np.array([z[k]]))[0])
            dzz = 0.22
            axL.annotate("", xy=(D["T_walk"][k] + slope * dzz, z[k] + dzz),
                         xytext=(D["T_walk"][k], z[k]),
                         arrowprops=dict(arrowstyle="-|>", color=C_A15, lw=2.6),
                         zorder=7)
        # slope rule parked in the empty top-right (shallow, high-T)
        axL.text(0.965, 0.055,
                 r"$\dfrac{d\langle T\rangle}{dz}=\dfrac{Q_b}{K}\approx$"
                 f"{D['slope']:.1f} K/m",
                 transform=axL.transAxes, fontsize=10, color=C_A15,
                 ha="right", va="bottom",
                 bbox=dict(boxstyle="round,pad=0.35", fc="white", ec=C_A15, lw=1))
    elif kind in ("repeat", "done"):
        built = (z >= Z0) & m
        axL.plot(D["T_walk"][built], z[built], "-", color=C_HAYNE, lw=3.2,
                 label="deep profile (reconstructed)")

    axL.set_xlim(242, 262)
    axL.set_ylim(ZMAX, 0)
    axL.axhline(Z0, color=C_DIM, lw=0.6, ls=":")
    axL.set_xlabel("cycle-mean temperature  [K]", fontsize=10)
    axL.set_ylabel("depth  [m]", fontsize=10)
    axL.set_title("(a)  building the temperature column", fontsize=11,
                  color=C_CHAR, loc="left")
    axL.legend(loc="lower left", fontsize=8.2, frameon=True, edgecolor=C_GRID,
               framealpha=0.95)

    # ── right: real drift, accumulating with overall progress ────────────────
    drift = D["drift"]
    frac = (si + 1) / len(seq)
    n_show = max(1, int(round(frac * len(drift))))
    xs = np.arange(1, n_show + 1)
    axR.plot(xs, drift[:n_show], "-o", color=C_FOREST, ms=6, lw=1.6,
             mec="white", mew=0.8, zorder=3)
    axR.axhline(TOL, color=C_CORAL, ls="--", lw=1.3)
    axR.text(len(drift), TOL * 1.15, "tolerance 0.005 K", color=C_CORAL,
             fontsize=8.5, ha="right", va="bottom")
    axR.set_yscale("log")
    axR.set_xlim(0.5, len(drift) + 0.5)
    axR.set_ylim(min(drift.min() * 0.6, TOL * 0.5), drift.max() * 1.6)
    axR.set_xlabel("outer iteration (Step A + Step B)", fontsize=10)
    axR.set_ylabel("anchor drift  [K]", fontsize=10)
    axR.set_title("(b)  the anchor stops moving", fontsize=11,
                  color=C_CHAR, loc="left")
    axR.grid(True, which="both", color=C_GRID, lw=0.4, alpha=0.5)

    return label


def main():
    D = _compute()
    deep_idx = [i for i in range(D["i0"], D["z"].size) if D["z"][i] <= ZMAX]
    seq = _frames(len(deep_idx))

    fig, (axL, axR) = plt.subplots(1, 2, figsize=(JGR_FULL, 4.7),
                                   gridspec_kw={"width_ratios": [1.35, 1.0]})
    fig.subplots_adjust(left=0.075, right=0.975, top=0.85, bottom=0.135,
                        wspace=0.28)
    suptitle = fig.suptitle("", fontsize=12, color=C_CHAR, fontweight="bold",
                            y=0.965)

    def update(si):
        label = _draw(axL, axR, seq[si], D, seq, si)
        suptitle.set_text(label)
        return []

    anim = FuncAnimation(fig, update, frames=len(seq), blit=False)
    ANIM.mkdir(parents=True, exist_ok=True)
    out = ANIM / "anchor_method_steps.gif"
    anim.save(str(out), writer=PillowWriter(fps=7), dpi=100)
    plt.close(fig)
    print(f"  -> {out.relative_to(_REPO)}  ({len(seq)/7:.1f} s, "
          f"slope {D['slope']:.1f} K/m, {len(D['drift'])} drift points)")

    _filmstrip(D, seq)


def _filmstrip(D, seq):
    """4-panel LaTeX still: guess -> Step A -> Step B walk -> converged."""
    from lunar.plotting.style import assert_no_overlap
    picks = [("guess", 4), ("stepA", None), ("stepB", None), ("done", -1)]
    # choose representative frame indices per kind
    idx = {}
    for i, ph in enumerate(seq):
        idx.setdefault(ph[1], []).append(i)
    chosen = [idx["guess"][-1], idx["stepA"][-1],
              idx["stepB"][int(len(idx["stepB"]) * 0.6)], idx["done"][0]]

    fig = plt.figure(figsize=(JGR_FULL, 3.5))
    gs = fig.add_gridspec(1, 4, wspace=0.30, left=0.06, right=0.985,
                          top=0.80, bottom=0.16)
    titles = ["1. rough guess", "2. Step A: skin settles",
              "3-4. Step B: walk down", "5-6. converged"]
    for j, (ci, ttl) in enumerate(zip(chosen, titles)):
        ax = fig.add_subplot(gs[0, j])
        dummy = fig.add_subplot(gs[0, j]); dummy.remove()   # keep gridspec tidy
        _draw_panel(ax, seq[ci], D, ttl, sharey=(j == 0))
    fig.suptitle("The flux-anchored method, step by step "
                 "(Apollo 15, $K_d = 4.60$ mW m$^{-1}$K$^{-1}$)",
                 fontsize=11.5, color=C_CHAR, fontweight="bold", y=0.955)
    fig.canvas.draw()
    out = FIG / "anchor_method_filmstrip.pdf"
    fig.savefig(out)
    plt.close(fig)
    print(f"  -> {out.relative_to(_REPO)}")


def _draw_panel(ax, phase, D, title, sharey):
    """One filmstrip panel (profile only; no right-hand drift axis)."""
    z, i0 = D["z"], D["i0"]
    m = z <= ZMAX
    deep_idx = [i for i in range(i0, z.size) if z[i] <= ZMAX]
    _, kind, prog = phase
    sk = z <= Z0
    ax.plot(D["T_target"][m], z[m], "--", color=C_DIM, lw=1.3)
    if kind == "guess":
        ax.plot(D["T_guess"][m], z[m], "-", color=C_CORAL, lw=2.2)
    elif kind == "stepA":
        Tsk = (1 - prog) * D["T_guess"] + prog * D["T_target"]
        cur = D["T_guess"].copy(); cur[sk] = Tsk[sk]
        ax.plot(cur[sk], z[sk], "-", color=C_FOREST, lw=2.6)
        ax.plot(cur[m & ~sk], z[m & ~sk], "-", color=C_CORAL, lw=1.4, alpha=0.5)
    else:
        ax.plot(D["T_target"][sk], z[sk], "-", color=C_FOREST, lw=2.6)
        ax.plot(D["T_target"][i0], Z0, "o", color=C_CHAR, ms=7, zorder=6)
    if kind == "stepB":
        k = deep_idx[min(int(round(prog * (len(deep_idx) - 1))), len(deep_idx) - 1)]
        built = (z >= Z0) & (z <= z[k])
        ax.plot(D["T_walk"][built], z[built], "-", color=C_HAYNE, lw=2.8)
        slope = D["Qb"] / float(D["K"](np.array([D["T_walk"][k]]),
                                       np.array([z[k]]))[0])
        dzz = 0.26
        ax.annotate("", xy=(D["T_walk"][k] + slope * dzz, z[k] + dzz),
                    xytext=(D["T_walk"][k], z[k]),
                    arrowprops=dict(arrowstyle="-|>", color=C_A15, lw=2.2))
    elif kind in ("repeat", "done"):
        built = (z >= Z0) & m
        ax.plot(D["T_walk"][built], z[built], "-", color=C_HAYNE, lw=2.8)
    ax.set_xlim(242, 262)
    ax.set_ylim(ZMAX, 0)
    ax.axhline(Z0, color=C_DIM, lw=0.5, ls=":")
    ax.set_xlabel("temperature  [K]", fontsize=9)
    if sharey:
        ax.set_ylabel("depth  [m]", fontsize=9)
    else:
        ax.set_yticklabels([])
    ax.set_title(title, fontsize=9.5, color=C_CHAR, loc="left")


if __name__ == "__main__":
    main()
