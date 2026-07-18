#!/usr/bin/env python3
"""Explainer animation, act 1 -- THE PROBLEM: brute-force spin-up.

Start the column at a wrong flat temperature and march it one lunar cycle
at a time. The skin settles within ~10 cycles; the metre-deep column
creeps for ~1000. The old cycle-to-cycle stop test declared "converged"
at 30 lunations while the deep column was still kelvins from the truth.

Design (2026-07-17 redesign): fixed banner text (no jumping suptitle),
axes zoomed on the cycle-MEAN profile (the story), a static legend
outside the axes, persistent artists updated per frame (no clear/redraw
flicker), and holds at the two story beats (lunation 30, the end).

Outputs (filenames unchanged -- notebook 02 and the guidebook embed them):
  figures/anim/spinup.gif
  figures/spinup_filmstrip.pdf

Run from the repo root. (~5 min: it integrates ~1000 lunations once.)
"""
from __future__ import annotations
import sys, pathlib
import numpy as np

_REPO = pathlib.Path(__file__).resolve().parents[1].parent
sys.path.insert(0, str(_REPO))
sys.path.insert(0, str(_REPO / "src"))

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation, PillowWriter
from matplotlib.lines import Line2D
import functools

from lunar.config import SITES, GRID, HAYNE, DT_STEP
from lunar.grid import make_geometric_grid
from lunar.properties import conductivity_hayne, specific_heat
from lunar.solver import (PixelInputs, solve_pixel, standard_insolation,
                          periodic_time_grid)
from lunar.equilibrium import solve_periodic_equilibrium
from lunar.plotting.style import (C_A15, C_CORAL, C_CHAR, C_DIM, C_GRID,
                                  C_FOREST)

ANIM = _REPO / ".." / "figures" / "anim"
FIG = _REPO / ".." / "figures"
FIG.mkdir(parents=True, exist_ok=True)

SITE = SITES["A15"]; KD = 4.60e-3
GUESS = 240.0          # deliberately-wrong flat start, so the evolution is visible
ZMAX_PLOT = 3.0        # show the top 3 m
PROBE_Z = 1.0
XLIM = (238.0, 258.0)  # zoomed on the cycle MEAN (the story), not the daily swing


def _capture():
    g = make_geometric_grid(**GRID); z = g.z_mid
    t = periodic_time_grid(DT_STEP)   # commensurate lunation grid (audit 2026-07-03)
    insol = standard_insolation(SITE["lat"], t)   # raw flux; solver applies (1-A)
    K = functools.partial(conductivity_hayne, Ks=HAYNE["K_S"], Kd=KD, H=HAYNE["H"], chi=HAYNE["CHI"])
    cp = functools.partial(specific_heat, model="hayne")

    # target: the converged steady state for this K_d
    eq = solve_periodic_equilibrium(grid=g, t=t, insolation=insol, albedo=SITE["albedo"],
            emissivity=SITE["emissivity"], Q_b=SITE["Q_BASAL"], K_func=K, cp_func=cp,
            T_guess=SITE["T_MEAN_EFF"])
    T_target = eq.T_mean

    # brute-force continuation: dense early, coarse later (hits 30 and 1000 exactly)
    deltas = [5]*6 + [14]*5 + [60]*15
    T_init = np.full(z.size, GUESS)
    frames = [dict(lun=0, mean=T_init.copy(), probe=GUESS)]
    cum = 0
    for d in deltas:
        out = solve_pixel(PixelInputs(grid=g, t=t, bc_mode="radiative", insolation=insol,
            albedo=SITE["albedo"], emissivity=SITE["emissivity"], Q_b=SITE["Q_BASAL"],
            T_init=T_init, n_lunations_spinup=d, spinup_tol_K=0.0, K_func=K, cp_func=cp))
        cum += d; Tm = out.T.mean(axis=1); T_init = out.T[:, -1]
        frames.append(dict(lun=cum, mean=Tm.copy(), probe=Tm[np.argmin(np.abs(z - PROBE_Z))]))
    return z, T_target, frames, int(np.argmin(np.abs(z - PROBE_Z)))


# ── the animation ────────────────────────────────────────────────────────────
def _build_fig(z, T_target, frames, ip):
    m = z <= ZMAX_PLOT
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(9.8, 4.7))
    fig.subplots_adjust(top=0.74, bottom=0.115, left=0.075, right=0.975, wspace=0.28)

    # fixed banner (never moves, never jumps)
    fig.text(0.075, 0.945, "The problem: brute-force spin-up",
             fontsize=15, fontweight="bold", color=C_CHAR, ha="left")
    sub = fig.text(0.075, 0.875, "", fontsize=11.5, color=C_DIM, ha="left")
    note = fig.text(0.075, 0.815, "", fontsize=10, color=C_CORAL, ha="left",
                    style="italic")

    # static legend, fully outside the axes (top right, under nothing)
    handles = [
        Line2D([], [], color=C_A15, lw=2.6, label="brute force so far (cycle mean)"),
        Line2D([], [], color=C_CHAR, lw=1.8, ls="--", label="true steady state (target)"),
        Line2D([], [], color=C_A15, marker="o", lw=0, ms=7, label=f"temperature at {PROBE_Z:.0f} m"),
    ]
    fig.legend(handles=handles, loc="upper right", bbox_to_anchor=(0.975, 1.0),
               frameon=True, edgecolor=C_GRID, framealpha=0.95, fontsize=8.6)

    # (a) the column: cycle-mean profile, zoomed
    ax1.plot(T_target[m], z[m], "--", color=C_CHAR, lw=1.8)
    ln_mean, = ax1.plot([], [], "-", color=C_A15, lw=2.6)
    dot_a, = ax1.plot([], [], "o", color=C_A15, ms=8, mec="white", mew=0.8, zorder=5)
    ax1.axhline(PROBE_Z, color=C_DIM, lw=0.7, ls=":")
    ax1.set_xlim(*XLIM); ax1.set_ylim(ZMAX_PLOT, 0)
    ax1.set_xlabel("cycle-mean temperature  [K]", fontsize=10.5)
    ax1.set_ylabel("depth  [m]", fontsize=10.5)
    ax1.set_title("(a)  the column, cycle by cycle", loc="left", fontsize=11, color=C_CHAR)
    ax1.grid(alpha=0.22)

    # (b) the deep creep: T(1 m) vs lunations
    luns_all = [f["lun"] for f in frames]
    probes_all = [f["probe"] for f in frames]
    ax2.plot(luns_all, probes_all, "-", color=C_A15, alpha=0.22, lw=1.2)   # ghost of full path
    ln_probe, = ax2.plot([], [], "-", color=C_A15, lw=2.4)
    dot_b, = ax2.plot([], [], "o", color=C_A15, ms=8, mec="white", mew=0.8, zorder=5)
    ax2.axhline(T_target[ip], ls="--", color=C_CHAR, lw=1.8)
    ax2.axvline(30, ls=":", color=C_CORAL, lw=1.6)
    # label for the 30-lunation line: inside the axes, upper-left region,
    # which stays empty for the whole animation (target line is at 253)
    ax2.text(34, 255.6, "old stop test:\nlunation 30", fontsize=8.6,
             color=C_CORAL, ha="left", va="top")
    ax2.set_xscale("symlog", linthresh=30)
    ax2.set_xlim(0, 1000); ax2.set_ylim(238, 256)
    ax2.set_xlabel("lunations simulated  (log scale)", fontsize=10.5)
    ax2.set_ylabel(f"temperature at {PROBE_Z:.0f} m  [K]", fontsize=10.5)
    ax2.set_title("(b)  the deep column creeps for ~1000 cycles", loc="left",
                  fontsize=11, color=C_CHAR)
    ax2.grid(alpha=0.22)

    return fig, (ax1, ax2), (ln_mean, dot_a, ln_probe, dot_b, sub, note), m


def _script(frames, T_target, ip):
    """(frame_index, subline, coral_note) sequence with holds at story beats."""
    seq = []
    for k, fr in enumerate(frames):
        lun = fr["lun"]
        err = abs(fr["probe"] - T_target[ip])
        subline = (f"lunation {lun:>4d}   |   T(1 m) is {err:4.1f} K from the target"
                   if lun else "start from a wrong, flat 240 K column")
        note = ""
        hold = 1
        if lun == 0:
            hold = 5
        elif lun == 30:
            note = ("at 30 lunations the old cycle-to-cycle test said “converged” "
                    f"— still {err:.1f} K wrong at depth")
            hold = 7
        elif k == len(frames) - 1:
            note = "the anchor method (next notebook section) skips this wait entirely"
            hold = 8
        seq += [(k, subline, note)] * hold
    return seq


def main():
    print("Capturing spin-up (integrates ~1000 lunations once)...")
    z, T_target, frames, ip = _capture()
    print(f"  {len(frames)} snapshots; target T(1m) = {T_target[ip]:.2f} K")

    fig, axes, (ln_mean, dot_a, ln_probe, dot_b, sub, note), m = _build_fig(
        z, T_target, frames, ip)
    seq = _script(frames, T_target, ip)

    luns = [f["lun"] for f in frames]
    probes = [f["probe"] for f in frames]

    def update(si):
        k, subline, ntext = seq[si]
        fr = frames[k]
        ln_mean.set_data(fr["mean"][m], z[m])
        dot_a.set_data([fr["mean"][ip]], [z[ip]])
        ln_probe.set_data(luns[:k + 1], probes[:k + 1])
        dot_b.set_data([luns[k]], [probes[k]])
        sub.set_text(subline)
        note.set_text(ntext)
        return []

    anim = FuncAnimation(fig, update, frames=len(seq), blit=False)
    ANIM.mkdir(parents=True, exist_ok=True)
    gif = ANIM / "spinup.gif"
    anim.save(str(gif), writer=PillowWriter(fps=6), dpi=100)
    plt.close(fig)
    print(f"  -> {gif.relative_to(_REPO)}  ({len(seq)/6:.1f} s)")

    _filmstrip(z, T_target, frames, ip)


def _filmstrip(z, T_target, frames, ip):
    """5 stills for the PDF, in the same zoomed style."""
    picks = [0, 30, 100, 300, 1000]
    idx = [min(range(len(frames)), key=lambda i: abs(frames[i]["lun"] - p)) for p in picks]
    m = z <= ZMAX_PLOT
    fig, axes = plt.subplots(1, 5, figsize=(12.5, 3.9), sharey=True)
    fig.subplots_adjust(top=0.80, bottom=0.15, left=0.06, right=0.985, wspace=0.14)
    for ax, k in zip(axes, idx):
        fr = frames[k]
        ax.plot(T_target[m], z[m], "--", color=C_CHAR, lw=1.5)
        ax.plot(fr["mean"][m], z[m], "-", color=C_A15, lw=2.2)
        ax.set_xlim(*XLIM); ax.set_ylim(ZMAX_PLOT, 0)
        is_30 = fr["lun"] == 30
        ax.set_title(f"{fr['lun']} lunations", fontsize=11.5,
                     color=(C_CORAL if is_30 else C_CHAR),
                     fontweight=("bold" if is_30 else "normal"), pad=5)
        if is_30:
            ax.set_xlabel("T [K]\n(old test: “converged”)", fontsize=9, color=C_CORAL)
        else:
            ax.set_xlabel("T [K]", fontsize=9.5)
        ax.grid(alpha=0.2); ax.tick_params(labelsize=8.5)
    axes[0].set_ylabel("depth [m]", fontsize=10.5)
    axes[-1].plot([], [], "--", color=C_CHAR, lw=1.5, label="true steady target")
    axes[-1].plot([], [], "-", color=C_A15, lw=2.2, label="brute force so far")
    axes[-1].legend(fontsize=8.5, frameon=True, framealpha=0.95,
                    edgecolor=C_GRID, loc="lower left")
    fig.suptitle("Brute-force spin-up: the deep column is the slow part",
                 fontsize=12.5, color=C_CHAR, fontweight="bold")
    fig.savefig(FIG / "spinup_filmstrip.pdf", bbox_inches="tight")
    plt.close(fig)
    print(f"  -> {(FIG / 'spinup_filmstrip.pdf').relative_to(_REPO)}")


if __name__ == "__main__":
    main()
