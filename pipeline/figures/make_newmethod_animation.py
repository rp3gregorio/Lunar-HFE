#!/usr/bin/env python3
"""Animate the NEW (flux-anchored) method, as a direct counterpart to
make_spinup_animation.py. It alternates two moves and converges in a handful
of steps instead of ~1000 lunations:

  * SETTLE  -- a short spin-up settles the fast surface skin and reads the
               anchor temperature;
  * RECONSTRUCT -- from the anchor, integrate dT/dz = Q_b/K straight down,
               snapping the deep profile onto the steady gradient.

Outputs:
  docs/justification/newmethod.gif
  docs/justification/figures/newmethod_filmstrip.pdf

Same site / K_d / target as the brute-force animation, so the two are
directly comparable. Run from the repo root.
"""
from __future__ import annotations
import sys, pathlib, functools
import numpy as np

_REPO = pathlib.Path(__file__).resolve().parents[1].parent
sys.path.insert(0, str(_REPO))

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation, PillowWriter

from lunar.config import SITES, GRID, HAYNE, S0, T_LUNAR, DT_STEP
from lunar.grid import make_geometric_grid
from lunar.properties import conductivity_hayne, specific_heat
from lunar.solver import PixelInputs, solve_pixel
from lunar.equilibrium import (solve_periodic_equilibrium,
                               _rectified_flux, _reconstruct_subskin)
from lunar.plotting.style import C_A15, C_A17, C_HAYNE, C_CHAR, C_DIM

DOC = _REPO / "docs" / "manuscript"
FIG = DOC / "figures"; FIG.mkdir(parents=True, exist_ok=True)
SITE = SITES["A15"]; KD = 4.58e-3; GUESS = 240.0; ZMAX = 3.0; PROBE_Z = 1.0


def _capture():
    g = make_geometric_grid(**GRID); z = g.z_mid; dz = g.dz
    t = np.arange(0, T_LUNAR, DT_STEP)
    insol = S0 * (1 - SITE["albedo"]) * np.clip(np.cos(2 * np.pi * t / T_LUNAR), 0, None)
    K = functools.partial(conductivity_hayne, Ks=HAYNE["K_S"], Kd=KD, H=HAYNE["H"], chi=HAYNE["CHI"])
    cp = functools.partial(specific_heat, model="hayne")
    Qb = SITE["Q_BASAL"]

    eq = solve_periodic_equilibrium(grid=g, t=t, insolation=insol, albedo=SITE["albedo"],
            emissivity=SITE["emissivity"], Q_b=Qb, K_func=K, cp_func=cp, T_guess=SITE["T_MEAN_EFF"])
    T_target = eq.T_mean

    def spin(T_init, n):
        out = solve_pixel(PixelInputs(grid=g, t=t, bc_mode="radiative", insolation=insol,
            albedo=SITE["albedo"], emissivity=SITE["emissivity"], Q_b=Qb,
            T_init=T_init, n_lunations_spinup=n, spinup_tol_K=0.0, K_func=K, cp_func=cp))
        return out

    # replicate the two-stage flux-anchored loop, capturing every move
    stages = [dict(z0=0.25, n_in=4, max_it=4, tol=0.10),
              dict(z0=0.55, n_in=12, max_it=20, tol=0.005)]
    T_init = np.full(z.size, GUESS)
    frames = [dict(prof=T_init.copy(), kind="start", lab="start: a flat wrong guess (240 K)",
                   work=0, outer=0)]
    work = 0
    for si, st in enumerate(stages, 1):
        i_s = int(np.argmin(np.abs(z - st["z0"])))
        anchor_prev = np.inf
        for it in range(1, st["max_it"] + 1):
            out = spin(T_init, st["n_in"]); work += st["n_in"]
            Tm = out.T.mean(axis=1)
            frames.append(dict(prof=Tm.copy(), kind="settle",
                               lab=f"settle the skin  ({st['n_in']} lunations)  ·  anchor at {st['z0']:.2f} m",
                               work=work, outer=len(frames)))
            u = _rectified_flux(out.T, z, K)
            Trec = _reconstruct_subskin(Tm, z, i_s, Qb, K, u)
            frames.append(dict(prof=Trec.copy(), kind="recon",
                               lab="reconstruct the deep profile:  integrate  dT/dz = Q_b / K  downward",
                               work=work, outer=len(frames)))
            drift = abs(Tm[i_s] - anchor_prev)
            if drift < st["tol"] and it >= 2:
                break
            anchor_prev = Tm[i_s]; T_init = Trec
    n_it = sum(1 for f in frames if f["kind"] == "settle")
    frames[-1]["lab"] = (f"converged after {n_it} short iterations "
                         f"({work} lunations of work, ~{work*0.0865:.0f} s)")
    ip = int(np.argmin(np.abs(z - PROBE_Z)))
    return z, T_target, frames, ip


def _panel(ax, z, T_target, fr, ip):
    ax.clear()
    m = z <= ZMAX
    ax.plot(T_target[m], z[m], "--", color=C_CHAR, lw=2, label="target (true steady state)")
    col = C_HAYNE if fr["kind"] == "recon" else C_A15
    ax.plot(fr["prof"][m], z[m], "-", color=col, lw=2.8, label="new method so far")
    ax.invert_yaxis(); ax.set_xlim(150, 320); ax.set_ylim(ZMAX, 0)
    ax.set_xlabel("temperature  [K]"); ax.set_ylabel("depth  [m]")
    tag = {"start": "START", "settle": "STEP A — SETTLE SKIN",
           "recon": "STEP B — RECONSTRUCT DEEP", }.get(fr["kind"], "")
    ax.set_title(f"{tag}\n{fr['lab']}", loc="left", fontsize=10.5,
                 color=(C_HAYNE if fr["kind"] == "recon" else C_CHAR), fontweight="bold")
    ax.legend(loc="lower left", fontsize=8.5, frameon=False)
    ax.text(0.97, 0.04,
            f"work used: {fr['work']} lunations  (~{max(fr['work'],1)*0.0865:.0f}s)\n"
            f"old method needed ~1000 lunations (~4 min)",
            transform=ax.transAxes, fontsize=8.5, color=C_DIM, ha="right", va="bottom")


def main():
    print("Capturing the flux-anchored iterations...")
    z, T_target, frames, ip = _capture()
    print(f"  {len(frames)} frames; target T(1m) = {T_target[ip]:.2f} K; "
          f"total work = {frames[-1]['work']} lunations")

    fig, ax = plt.subplots(figsize=(7.6, 5.2))
    # show the meaningful moves (one full stage-1 cycle + the snap), then jump
    # to the converged state; the ~10 tiny refinement steps in between add nothing
    # visible, so we skip them and hold the final frame.
    L = len(frames)
    order = [0, 1, 2, 3, 4, L - 1] + [L - 1] * 4
    def update(k):
        _panel(ax, z, T_target, frames[order[k]], ip)
        fig.suptitle("The new method: settle the skin, then impose the deep gradient",
                     fontsize=12.5, color=C_CHAR, fontweight="bold")
        fig.tight_layout(rect=[0, 0, 1, 0.94]); return []
    anim = FuncAnimation(fig, update, frames=len(order), blit=False)
    anim.save(str(DOC / "newmethod.gif"), writer=PillowWriter(fps=1.3))
    plt.close(fig); print(f"  -> {(DOC/'newmethod.gif').relative_to(_REPO)}")

    # filmstrip: start, first settle, first reconstruct, converged
    picks = [0, 1, 2, len(frames) - 1]
    labs = ["start", "settle skin (step A)", "reconstruct deep (step B)", "converged"]
    fig, axes = plt.subplots(1, 4, figsize=(12.5, 3.6), sharey=True)
    m = z <= ZMAX
    for ax, k, lab in zip(axes, picks, labs):
        fr = frames[k]
        col = C_HAYNE if fr["kind"] == "recon" else C_A15
        ax.plot(T_target[m], z[m], "--", color=C_CHAR, lw=1.6)
        ax.plot(fr["prof"][m], z[m], "-", color=col, lw=2.4)
        ax.invert_yaxis(); ax.set_xlim(150, 320); ax.set_ylim(ZMAX, 0)
        ax.set_title(lab, fontsize=10, color=C_CHAR); ax.set_xlabel("T [K]", fontsize=9)
        ax.grid(alpha=0.2)
    axes[0].set_ylabel("depth [m]")
    axes[-1].plot([], [], "--", color=C_CHAR, lw=1.6, label="target")
    axes[-1].plot([], [], "-", color=C_A15, lw=2.4, label="new method")
    axes[-1].legend(fontsize=8, frameon=False, loc="lower left")
    fig.suptitle("The new method reaches the SAME target in a few steps — the 'reconstruct' move "
                 "snaps the deep profile straight onto the steady gradient", fontsize=10.5, color=C_CHAR)
    fig.tight_layout(rect=[0, 0, 1, 0.93])
    fig.savefig(FIG / "newmethod_filmstrip.pdf", bbox_inches="tight")
    plt.close(fig); print(f"  -> {(FIG/'newmethod_filmstrip.pdf').relative_to(_REPO)}")


if __name__ == "__main__":
    main()
