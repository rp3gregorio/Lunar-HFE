#!/usr/bin/env python3
"""Animate the flux-anchored ("anchor") method, step by step (improved).

The story, one move per frame:
  START          -- a deliberately wrong flat guess (240 K).
  STEP A  settle -- time-step only the SKIN; it settles into its diurnal cycle
                    (shown as an envelope). Read the cycle-mean anchor T.
  STEP B  recon  -- from the anchor, integrate dT/dz = Q_b/K straight DOWN,
                    drawing the deep profile (no time-stepping).
  TWO STAGES     -- stage 1 primes with a shallow anchor (0.25 m, cheap/rough);
                    stage 2 drops the anchor to 0.55 m (below the wiggle zone)
                    and polishes to the true steady state.
  BONUS          -- the whole lunar cycle is stored, so ANY single hour is in
                    hand for free (e.g. the profile at lunar noon).

Everything is a real solve of the A15 column at K_d*=4.60 (lunar.equilibrium),
so the two-stage schedule, anchor depths and n_inner match production (config).

Outputs:
  docs/guidebook/newmethod.gif
  results/figures/newmethod_filmstrip.pdf
Run from the repo root.
"""
from __future__ import annotations
import sys, pathlib, functools
import numpy as np

_REPO = pathlib.Path(__file__).resolve().parents[1].parent
sys.path.insert(0, str(_REPO)); sys.path.insert(0, str(_REPO / "src"))

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation, PillowWriter
from matplotlib.lines import Line2D
from matplotlib.patches import Patch

from lunar.config import (SITES, GRID, HAYNE, S0, T_LUNAR, DT_STEP,
                          EQ_N_INNER, EQ_Z_ANCHOR)
from lunar.grid import make_geometric_grid
from lunar.properties import conductivity_hayne, specific_heat
from lunar.solver import PixelInputs, solve_pixel, standard_insolation, periodic_time_grid
from lunar.equilibrium import (solve_periodic_equilibrium,
                               _rectified_flux, _reconstruct_subskin)
from lunar.plotting.style import (C_CORAL, C_FOREST, C_CHAR, C_DIM, C_GRID,
                                  C_CORAL_L, C_FOREST_L)

DOC = _REPO / ".." / "figures" / "anim"
FIG = _REPO / ".." / "figures"; FIG.mkdir(parents=True, exist_ok=True)
SITE = SITES["A15"]; KD = 4.60e-3; GUESS = 240.0; ZMAX = 3.0
XLIM = (150, 320)
import json as _json
_BENCH = _json.loads((_REPO / "results" / "speedup_benchmark.json").read_text())
BRUTE_S = round(_BENCH["t_brute_s"])       # measured archive (benchmark_speedup.py)
ANCHOR_S = round(_BENCH["t_anchored_s"])


def _capture():
    g = make_geometric_grid(**GRID); z = g.z_mid
    t = periodic_time_grid(DT_STEP)   # commensurate lunation grid (audit 2026-07-03)
    insol = standard_insolation(SITE["lat"], t)   # raw flux; solver applies (1-A)
    K = functools.partial(conductivity_hayne, Ks=HAYNE["K_S"], Kd=KD, H=HAYNE["H"], chi=HAYNE["CHI"])
    cp = functools.partial(specific_heat, model="hayne")
    Qb = SITE["Q_BASAL"]

    eq = solve_periodic_equilibrium(grid=g, t=t, insolation=insol, albedo=SITE["albedo"],
            emissivity=SITE["emissivity"], Q_b=Qb, K_func=K, cp_func=cp, T_guess=SITE["T_MEAN_EFF"])
    T_target = eq.T_mean
    Tcyc = eq.out.T                              # (N_z, N_t): the stored lunar cycle
    Tmin, Tmax = Tcyc.min(axis=1), Tcyc.max(axis=1)
    T_noon = Tcyc[:, int(np.argmax(Tcyc[0, :]))]  # hottest surface hour = lunar noon

    def spin(T_init, n):
        return solve_pixel(PixelInputs(grid=g, t=t, bc_mode="radiative", insolation=insol,
            albedo=SITE["albedo"], emissivity=SITE["emissivity"], Q_b=Qb,
            T_init=T_init, n_lunations_spinup=n, spinup_tol_K=0.0, K_func=K, cp_func=cp))

    stages = [dict(z0=0.25, n_in=4, max_it=4, tol=0.10),
              dict(z0=EQ_Z_ANCHOR, n_in=EQ_N_INNER, max_it=20, tol=0.005)]
    T_init = np.full(z.size, GUESS)
    frames = [dict(kind="start", z0=0.25, prof=T_init.copy(), stage=0,
                   title="Start", sub="a deliberately wrong flat guess (240 K)")]
    for si, st in enumerate(stages, 1):
        i_s = int(np.argmin(np.abs(z - st["z0"]))); anchor_prev = np.inf; first = True
        for it in range(1, st["max_it"] + 1):
            out = spin(T_init, st["n_in"]); Tm = out.T.mean(axis=1)
            frames.append(dict(kind="settle", z0=st["z0"], prof=Tm.copy(), stage=si,
                env=(Tmin, Tmax) if first else None,
                title=f"Step A · settle the skin   (stage {si}, anchor {st['z0']:.2f} m)",
                sub=f"time-step {st['n_in']} lunations — only the skin — then read the cycle-mean anchor T"))
            u = _rectified_flux(out.T, z, K); Trec = _reconstruct_subskin(Tm, z, i_s, Qb, K, u)
            frames.append(dict(kind="recon", z0=st["z0"], prof=Trec.copy(), stage=si,
                title="Step B · reconstruct the deep",
                sub="integrate  dT/dz = Q_b / K  straight down from the anchor — no stepping"))
            drift = abs(Tm[i_s] - anchor_prev)
            if drift < st["tol"] and it >= 2:
                break
            anchor_prev = Tm[i_s]; T_init = Trec; first = False
    frames.append(dict(kind="done", z0=EQ_Z_ANCHOR, prof=frames[-1]["prof"].copy(), stage=2,
        title="Converged — the same steady state brute force reaches",
        sub=f"~{ANCHOR_S} s per solve   vs   brute force ~{BRUTE_S} s (~1000 lunations)"))
    frames.append(dict(kind="instant", z0=EQ_Z_ANCHOR, prof=T_target.copy(), inst=T_noon, stage=2,
        title="Bonus: any single hour is already in hand",
        sub="the full lunar cycle is stored — e.g. the profile at lunar noon (skin hot, deep unmoved)"))
    return z, T_target, frames


def _panel(ax, z, T_target, fr, *, small=False):
    ax.clear()
    m = z <= ZMAX; z0 = fr["z0"]; kind = fr["kind"]
    lw = 2.2 if small else 2.7
    ax.axhspan(0, z0, color=C_CORAL_L, alpha=0.55, lw=0)
    ax.axhspan(z0, ZMAX, color=C_FOREST_L, alpha=0.45, lw=0)
    ax.plot(T_target[m], z[m], "--", color=C_CHAR, lw=1.6, zorder=3)
    if kind == "start":
        ax.plot(fr["prof"][m], z[m], "-", color=C_DIM, lw=lw, zorder=4)
    elif kind == "settle":
        if fr.get("env") is not None:
            Tmn, Tmx = fr["env"]; sk = z <= max(z0 * 1.6, 0.4)
            ax.fill_betweenx(z[sk], Tmn[sk], Tmx[sk], color=C_CORAL, alpha=0.20, lw=0, zorder=2)
        ax.plot(fr["prof"][m], z[m], "-", color=C_CORAL, lw=lw, zorder=4)
    elif kind == "recon":
        sk = (z <= z0) & m; dp = (z >= z0) & m
        ax.plot(fr["prof"][sk], z[sk], "-", color=C_CORAL, lw=lw, zorder=4)
        ax.plot(fr["prof"][dp], z[dp], "-", color=C_FOREST, lw=lw + 0.2, zorder=5)
    elif kind == "done":
        ax.plot(fr["prof"][m], z[m], "-", color=C_FOREST, lw=lw + 0.2, zorder=4)
    elif kind == "instant":
        ax.plot(fr["prof"][m], z[m], "-", color=C_CHAR, lw=1.4, alpha=0.45, zorder=3)
        ax.plot(fr["inst"][m], z[m], "-", color=C_CORAL, lw=lw, zorder=5)
    ax.axhline(z0, color=C_DIM, ls=":", lw=1.1, zorder=3)
    if kind in ("settle", "recon", "done"):
        ax.plot([fr["prof"][int(np.argmin(np.abs(z - z0)))]], [z0], "o",
                color=C_CHAR, ms=(5.5 if small else 7), zorder=6)
    ax.annotate(f"anchor $z_0={z0:.2f}$ m", xy=(XLIM[1] - 3, z0), ha="right", va="bottom",
                fontsize=(7 if small else 8.5), color=C_DIM)
    ax.invert_yaxis(); ax.set_xlim(*XLIM); ax.set_ylim(ZMAX, 0)
    ax.set_xlabel("temperature  [K]")
    if not small:
        ax.set_ylabel("depth  [m]")
        ax.set_title(f"{fr['title']}\n{fr['sub']}", loc="left", fontsize=10.5,
                     color=C_CHAR, fontweight="bold")
        ax.annotate(f"anchor method: ~{ANCHOR_S}s   ·   brute force: ~{BRUTE_S}s",
                    xy=(0.97, 0.045), xycoords="axes fraction", ha="right", va="bottom",
                    fontsize=8.5, color=C_DIM)
    else:
        ax.set_title(fr["short"], fontsize=9.5, color=C_CHAR)


def _legend_handles():
    return ([Line2D([0], [0], ls="--", color=C_CHAR, lw=1.6),
             Patch(fc=C_CORAL_L, ec="none"), Patch(fc=C_FOREST_L, ec="none"),
             Line2D([0], [0], marker="o", color="none", mfc=C_CHAR, ms=7)],
            ["true steady state", "skin (time-stepped, Step A)",
             "deep (reconstructed, Step B)", "anchor $z_0$"])


def main():
    print("Capturing the flux-anchored iterations (real solves)...")
    z, T_target, frames = _capture()
    print(f"  {len(frames)} frames captured")

    # ----- GIF: start -> A -> B (stage 1) -> A (stage 2) -> converged -> instant
    idx = lambda k, s=None: next(i for i, f in enumerate(frames)
                                 if f["kind"] == k and (s is None or f.get("stage") == s))
    last_recon = max(i for i, f in enumerate(frames) if f["kind"] == "recon")
    order = ([idx("start"), idx("settle", 1), idx("recon", 1), idx("settle", 2),
              last_recon, idx("done"), idx("done"), idx("instant"), idx("instant")])

    fig, ax = plt.subplots(figsize=(7.8, 5.4))
    h, l = _legend_handles()

    def update(k):
        _panel(ax, z, T_target, frames[order[k]])
        ax.legend(h, l, loc="upper left", fontsize=8.2, frameon=True,
                  edgecolor=C_GRID, framealpha=0.95)
        fig.suptitle("The anchor method: settle the skin, reconstruct the deep",
                     fontsize=12.5, color=C_CHAR, fontweight="bold")
        fig.tight_layout(rect=[0, 0, 1, 0.95]); return []

    anim = FuncAnimation(fig, update, frames=len(order), blit=False)
    anim.save(str(DOC / "newmethod.gif"), writer=PillowWriter(fps=1.15))
    plt.close(fig); print(f"  -> {(DOC / 'newmethod.gif').relative_to(_REPO)}")

    # ----- filmstrip: 5 stills (start, settle+envelope, reconstruct, converged, one hour)
    picks = [(idx("start"), "start: wrong guess"),
             (idx("settle", 1), "Step A: settle skin"),
             (idx("recon", 1), "Step B: reconstruct"),
             (idx("done"), "converged"),
             (idx("instant"), "any one hour (noon)")]
    fig, axes = plt.subplots(1, 5, figsize=(13.5, 3.5), sharey=True)
    for ax, (k, short) in zip(axes, picks):
        fr = dict(frames[k]); fr["short"] = short
        _panel(ax, z, T_target, fr, small=True)
        ax.grid(alpha=0.15)
    axes[0].set_ylabel("depth  [m]")
    fig.suptitle("The anchor method as snapshots — settle the skin (Step A), reconstruct the deep "
                 "(Step B), reach the true steady state; the whole lunar cycle is stored for free",
                 fontsize=10.5, color=C_CHAR)
    fig.tight_layout(rect=[0, 0.15, 1, 0.93])
    hh, ll = _legend_handles()
    fig.legend(hh, ll, loc="lower center", ncol=4, fontsize=9, frameon=True,
               edgecolor=C_GRID, bbox_to_anchor=(0.5, 0.02))
    fig.savefig(FIG / "newmethod_filmstrip.pdf", bbox_inches="tight")
    plt.close(fig); print(f"  -> {(FIG / 'newmethod_filmstrip.pdf').relative_to(_REPO)}")


if __name__ == "__main__":
    main()
