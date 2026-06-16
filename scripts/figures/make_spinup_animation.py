#!/usr/bin/env python3
"""Animate a brute-force spin-up so 'the brute-force line' is obvious:
watch the temperature diffuse down into the regolith lunation by lunation,
and see that at 30 lunations the deep part has NOT yet reached steady state.

Outputs:
  docs/justification/spinup.gif              -- the animation (play it)
  docs/justification/figures/spinup_filmstrip.pdf  -- 5 stills for the PDF

Run from the repo root.  (~1-2 min: it integrates ~1000 lunations once.)
"""
from __future__ import annotations
import sys, pathlib
import numpy as np

_REPO = pathlib.Path(__file__).resolve().parents[1].parent
sys.path.insert(0, str(_REPO))

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation, PillowWriter
import functools

from lunar.config import SITES, GRID, HAYNE, S0, T_LUNAR, DT_STEP
from lunar.grid import make_geometric_grid
from lunar.properties import conductivity_hayne, specific_heat
from lunar.solver import PixelInputs, solve_pixel
from lunar.equilibrium import solve_periodic_equilibrium
from lunar.plotting.style import C_A15, C_A17, C_HAYNE, C_CHAR, C_DIM

DOC = _REPO / "docs" / "justification"
FIG = DOC / "figures"
FIG.mkdir(parents=True, exist_ok=True)

SITE = SITES["A15"]; KD = 4.58e-3
GUESS = 240.0          # deliberately-wrong flat start, so the evolution is visible
ZMAX_PLOT = 3.0        # show the top 3 m
PROBE_Z = 1.0


def _capture():
    g = make_geometric_grid(**GRID); z = g.z_mid
    t = np.arange(0, T_LUNAR, DT_STEP)
    insol = S0 * (1 - SITE["albedo"]) * np.clip(np.cos(2 * np.pi * t / T_LUNAR), 0, None)
    K = functools.partial(conductivity_hayne, Ks=HAYNE["K_S"], Kd=KD, H=HAYNE["H"], chi=HAYNE["CHI"])
    cp = functools.partial(specific_heat, model="hayne")
    ip = int(np.argmin(np.abs(z - PROBE_Z)))

    # target: the converged steady state for this K_d
    eq = solve_periodic_equilibrium(grid=g, t=t, insolation=insol, albedo=SITE["albedo"],
            emissivity=SITE["emissivity"], Q_b=SITE["Q_BASAL"], K_func=K, cp_func=cp,
            T_guess=SITE["T_MEAN_EFF"])
    T_target = eq.T_mean

    # brute-force continuation, dense early then coarse
    deltas = [2]*15 + [5]*14 + [25]*36          # cumulative -> 30, 100, 1000
    T_init = np.full(z.size, GUESS)
    frames = [dict(lun=0, mean=T_init.copy(), lo=T_init.copy(), hi=T_init.copy(), probe=GUESS)]
    cum = 0
    for d in deltas:
        out = solve_pixel(PixelInputs(grid=g, t=t, bc_mode="radiative", insolation=insol,
            albedo=SITE["albedo"], emissivity=SITE["emissivity"], Q_b=SITE["Q_BASAL"],
            T_init=T_init, n_lunations_spinup=d, spinup_tol_K=0.0, K_func=K, cp_func=cp))
        cum += d; Tm = out.T.mean(axis=1); T_init = out.T[:, -1]
        frames.append(dict(lun=cum, mean=Tm.copy(),
                           lo=out.T.min(axis=1), hi=out.T.max(axis=1), probe=Tm[ip]))
    return z, T_target, frames, ip


def _draw(ax1, ax2, z, T_target, frames, k, ip):
    ax1.clear(); ax2.clear()
    fr = frames[k]
    m = z <= ZMAX_PLOT
    # left: profile vs depth
    ax1.fill_betweenx(z[m], fr["lo"][m], fr["hi"][m], color=C_A15, alpha=0.15,
                      label="daily temperature swing")
    ax1.plot(T_target[m], z[m], "--", color=C_CHAR, lw=2, label="true steady state (target)")
    ax1.plot(fr["mean"][m], z[m], "-", color=C_A15, lw=2.6, label="brute force so far")
    ax1.axhline(PROBE_Z, color=C_DIM, lw=0.7, ls=":")
    ax1.invert_yaxis(); ax1.set_xlim(150, 320); ax1.set_ylim(ZMAX_PLOT, 0)
    ax1.set_xlabel("temperature  [K]"); ax1.set_ylabel("depth  [m]")
    ax1.set_title(f"lunation {fr['lun']:>4d}  of the spin-up", loc="left",
                  fontsize=12, color=C_CHAR, fontweight="bold")
    ax1.legend(loc="lower left", fontsize=8, frameon=False)
    ax1.text(305, 0.12, "Sun heats\nthe surface", fontsize=8, color=C_DIM, ha="right", va="top")
    if fr["lun"] == 30:
        ax1.text(0.5, 0.5, "30 lunations:\ndeep part NOT settled", transform=ax1.transAxes,
                 fontsize=11, color=C_A17, ha="center", fontweight="bold")

    # right: probe temperature vs lunation
    luns = [f["lun"] for f in frames[:k + 1]]
    probes = [f["probe"] for f in frames[:k + 1]]
    ax2.plot([f["lun"] for f in frames], [f["probe"] for f in frames], "-", color=C_A15, alpha=0.25, lw=1.2)
    ax2.plot(luns, probes, "-", color=C_A15, lw=2.2)
    ax2.plot(luns[-1], probes[-1], "o", color=C_A15, ms=7)
    ax2.axhline(T_target[ip], ls="--", color=C_CHAR, lw=1.5, label="target")
    ax2.axvline(30, ls=":", color=C_A17, lw=1.5)
    ax2.text(33, 165, "old method\nstopped here", fontsize=8.5, color=C_A17)
    ax2.set_xscale("symlog", linthresh=10)
    ax2.set_xlim(0, 1000); ax2.set_ylim(160, 260)
    ax2.set_xlabel("lunations (lunar days) simulated")
    ax2.set_ylabel(f"temperature at {PROBE_Z:.0f} m  [K]")
    ax2.set_title("the deep temperature creeps toward the target", loc="left",
                  fontsize=11, color=C_CHAR)
    ax2.legend(loc="lower right", fontsize=8, frameon=False)
    ax2.grid(alpha=0.25)


def main():
    print("Capturing spin-up (this integrates ~1000 lunations once)...")
    z, T_target, frames, ip = _capture()
    print(f"  {len(frames)} frames; target T(1m) = {T_target[ip]:.2f} K")

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 4.8))
    def update(k):
        _draw(ax1, ax2, z, T_target, frames, k, ip)
        fig.suptitle("Brute-force spin-up: how heat slowly diffuses into the regolith",
                     fontsize=13, color=C_CHAR, fontweight="bold")
        fig.tight_layout(rect=[0, 0, 1, 0.95]); return []
    anim = FuncAnimation(fig, update, frames=len(frames), blit=False)
    gif = DOC / "spinup.gif"
    anim.save(str(gif), writer=PillowWriter(fps=10))
    plt.close(fig)
    print(f"  -> {gif.relative_to(_REPO)}")

    # filmstrip of 5 stills for the PDF
    picks = [0, 30, 100, 300, 1000]
    idx = [min(range(len(frames)), key=lambda i: abs(frames[i]["lun"] - p)) for p in picks]
    fig, axes = plt.subplots(1, 5, figsize=(13, 3.4), sharey=True)
    m = z <= ZMAX_PLOT
    for ax, k in zip(axes, idx):
        fr = frames[k]
        ax.fill_betweenx(z[m], fr["lo"][m], fr["hi"][m], color=C_A15, alpha=0.15)
        ax.plot(T_target[m], z[m], "--", color=C_CHAR, lw=1.6)
        ax.plot(fr["mean"][m], z[m], "-", color=C_A15, lw=2.2)
        ax.invert_yaxis(); ax.set_xlim(150, 320); ax.set_ylim(ZMAX_PLOT, 0)
        ax.set_title(f"{fr['lun']} lunations", fontsize=10,
                     color=(C_A17 if fr["lun"] == 30 else C_CHAR),
                     fontweight=("bold" if fr["lun"] == 30 else "normal"))
        ax.set_xlabel("T [K]", fontsize=9); ax.grid(alpha=0.2)
    axes[0].set_ylabel("depth [m]")
    axes[-1].plot([], [], "--", color=C_CHAR, lw=1.6, label="target")
    axes[-1].plot([], [], "-", color=C_A15, lw=2.2, label="brute force")
    axes[-1].legend(fontsize=8, frameon=False, loc="lower left")
    fig.suptitle("Brute-force spin-up: the deep profile is still far from the target at 30 lunations; "
                 "it only settles after hundreds", fontsize=11, color=C_CHAR)
    fig.tight_layout(rect=[0, 0, 1, 0.94])
    fig.savefig(FIG / "spinup_filmstrip.pdf", bbox_inches="tight")
    plt.close(fig)
    print(f"  -> {(FIG / 'spinup_filmstrip.pdf').relative_to(_REPO)}")


if __name__ == "__main__":
    main()
