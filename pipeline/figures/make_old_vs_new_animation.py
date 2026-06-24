#!/usr/bin/env python3
"""One animation that compares the two ways of reaching steady state, with the
flux-anchored anchor+slope-walk as the centrepiece.

Two persistent panels:
  LEFT  -- the old brute-force spin-up crawling down (real solver, ~1000 lun);
  RIGHT -- the new flux-anchored method: settle the skin, drop the anchor at
           z0 = 0.55 m, then walk the closure slope (Q_b - u_rect)/K downward to
           fill the deep column, converging in ~9 short cycles.

All curves are real solver output (src/lunar/solver.py, equilibrium.py); the
wall-clock numbers match the measured ~80x of guidebook S3.13 (one solve:
~700 s brute vs ~9 s flux-anchored).

Outputs:
  docs/guidebook/old_vs_new.gif                 -- the animation (talks/web)
  results/figures/old_vs_new_filmstrip.pdf      -- 6 stills for the PDF book

No MP4: ffmpeg is not installed here; convert the GIF if you need MP4.
Run from the repo root.  (~3-4 min: it integrates ~1000 lunations once.)
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

from lunar.config import SITES, GRID, HAYNE, S0, T_LUNAR, DT_STEP
from lunar.grid import make_geometric_grid
from lunar.properties import conductivity_hayne, specific_heat
from lunar.solver import PixelInputs, solve_pixel
from lunar.equilibrium import (solve_periodic_equilibrium,
                               _rectified_flux, _reconstruct_subskin)
from lunar.plotting.style import C_A15, C_A17, C_HAYNE, C_CHAR, C_DIM, C_GRID

DOC = _REPO / "docs" / "guidebook"
FIG = _REPO / "results" / "figures"; FIG.mkdir(parents=True, exist_ok=True)

SITE = SITES["A15"]; KD = 4.58e-3; GUESS = 240.0
Z0 = 0.55; ZMAX = 3.0; PROBE_Z = 1.0
TLIM = (150, 320)
SEC_PER_LUN = 0.23          # measured (~700 s for ~3000 lunations); guidebook S3.13


def _setup():
    g = make_geometric_grid(**GRID); z = g.z_mid; dz = g.dz
    t = np.arange(0, T_LUNAR, DT_STEP)
    insol = S0 * (1 - SITE["albedo"]) * np.clip(np.cos(2 * np.pi * t / T_LUNAR), 0, None)
    K = functools.partial(conductivity_hayne, Ks=HAYNE["K_S"], Kd=KD, H=HAYNE["H"], chi=HAYNE["CHI"])
    cp = functools.partial(specific_heat, model="hayne")
    Qb = SITE["Q_BASAL"]
    eq = solve_periodic_equilibrium(grid=g, t=t, insolation=insol, albedo=SITE["albedo"],
            emissivity=SITE["emissivity"], Q_b=Qb, K_func=K, cp_func=cp, T_guess=SITE["T_MEAN_EFF"])
    return dict(g=g, z=z, dz=dz, t=t, insol=insol, K=K, cp=cp, Qb=Qb, T_target=eq.T_mean,
                ip=int(np.argmin(np.abs(z - PROBE_Z))), i0=int(np.argmin(np.abs(z - Z0))))


def _brute_frames(S):
    """Real brute-force spin-up: cumulative solve_pixel to ~1000 lunations."""
    deltas = [2] * 15 + [5] * 14 + [25] * 36           # -> 30, 100, 1000
    T_init = np.full(S["z"].size, GUESS)
    frames = [dict(lun=0, mean=T_init.copy(), lo=T_init.copy(), hi=T_init.copy())]
    cum = 0
    for d in deltas:
        out = solve_pixel(PixelInputs(grid=S["g"], t=S["t"], bc_mode="radiative", insolation=S["insol"],
            albedo=SITE["albedo"], emissivity=SITE["emissivity"], Q_b=S["Qb"],
            T_init=T_init, n_lunations_spinup=d, spinup_tol_K=0.0, K_func=S["K"], cp_func=S["cp"]))
        cum += d; T_init = out.T[:, -1]
        frames.append(dict(lun=cum, mean=out.T.mean(axis=1),
                           lo=out.T.min(axis=1), hi=out.T.max(axis=1)))
    return frames


def _flux_anchored(S):
    """Real flux-anchored solve: settle skin (12 lun), anchor at z0, walk down."""
    out = solve_pixel(PixelInputs(grid=S["g"], t=S["t"], bc_mode="radiative", insolation=S["insol"],
        albedo=SITE["albedo"], emissivity=SITE["emissivity"], Q_b=S["Qb"],
        T_init=np.full(S["z"].size, GUESS), n_lunations_spinup=12, spinup_tol_K=0.0,
        K_func=S["K"], cp_func=S["cp"]))
    Tm = out.T.mean(axis=1)
    u = _rectified_flux(out.T, S["z"], S["K"])
    T_rec = _reconstruct_subskin(Tm, S["z"], S["i0"], S["Qb"], S["K"], u)
    return dict(settle=Tm, u=u, T_rec=T_rec)


def main():
    print("Setup + target (one equilibrium solve)...")
    S = _setup()
    print("Brute-force capture (~1-2 min, integrates ~1000 lunations)...")
    bf = _brute_frames(S)
    print(f"  {len(bf)} brute frames; target T(1m)={S['T_target'][S['ip']]:.2f} K")
    fa = _flux_anchored(S)

    z, dz, Tt, K, Qb = S["z"], S["dz"], S["T_target"], S["K"], S["Qb"]
    i0, ip = S["i0"], S["ip"]
    m = z <= ZMAX
    z0_T = fa["settle"][i0]                    # anchor temperature (real)
    walk_cells = [i for i in range(i0, z.size) if z[i] <= ZMAX]

    # ---- frame plan: each spec drives both panels + caption ----------------
    OLD_FINAL = bf[-1]
    specs = []
    # Act 1: old animates (subsample), new = flat start
    bf_sub = bf[::2] + [bf[-1]] * 2
    for fr in bf_sub:
        note = None
        if fr["lun"] == 30:
            note = "literature cut-off\nlooks converged"
        specs.append(dict(act=1, old=fr, new=("start", None),
                          cap="Old way: brute-force spin-up — the skin snaps fast, the deep column crawls"))
    # Act 2: old frozen, new animates
    specs += [dict(act=2, old=OLD_FINAL, new=("settle", None),
                   cap="New way · Step A: a short run (~12 lunations) settles the fast surface skin")] * 6
    specs += [dict(act=2, old=OLD_FINAL, new=("anchor", None),
                   cap="Drop the anchor at z = 0.55 m -- the cycle-mean temperature there is known")] * 8
    for k in walk_cells[::1]:
        specs.append(dict(act=2, old=OLD_FINAL, new=("walk", k),
                          cap="Step B: walk the closure slope (Q_b - u_rect)/K downward -- the deep column draws itself"))
    specs += [dict(act=2, old=OLD_FINAL, new=("converged", None),
                   cap="A few refine cycles polish it -- converged in ~9 cycles, ~9 s")] * 4
    # Act 3: comparison hold
    specs += [dict(act=3, old=OLD_FINAL, new=("converged", None), badge=True,
                   cap="Same steady state, ~80x faster: ~700 s brute force  vs  ~9 s flux-anchored")] * 18

    fig, (axO, axN) = plt.subplots(1, 2, figsize=(11.0, 5.2), sharey=True)

    def axes_common(ax):
        ax.invert_yaxis(); ax.set_xlim(*TLIM); ax.set_ylim(ZMAX, 0)
        ax.set_xlabel("cycle-mean temperature  [K]")
        ax.axhspan(0.8, 2.4, color=C_DIM, alpha=0.07, zorder=0)

    def draw_old(fr, frozen):
        axO.clear(); axes_common(axO); axO.set_ylabel("depth  [m]")
        axO.fill_betweenx(z[m], fr["lo"][m], fr["hi"][m], color=C_A15, alpha=0.12)
        axO.plot(Tt[m], z[m], "--", color=C_CHAR, lw=1.8)
        axO.plot(fr["mean"][m], z[m], "-", color=C_A15, lw=2.8)
        err = abs(fr["mean"][ip] - Tt[ip])
        axO.set_title("Old — brute-force spin-up", loc="left", fontsize=12,
                      color=C_CHAR, fontweight="bold")
        # readouts, fixed top-left corner (never on the curve)
        axO.text(0.04, 0.16, f"lunation  {fr['lun']:>4d}\ndeep error  {err:4.1f} K\nwall-clock  ~{max(fr['lun'],1)*SEC_PER_LUN:,.0f} s",
                 transform=axO.transAxes, fontsize=10, color=C_DIM, va="top", family="monospace")
        if frozen:
            axO.text(0.04, 0.40, "still drifting —\n~3000 lunations\n(~700 s) to settle",
                     transform=axO.transAxes, fontsize=10.5, color=C_A17, va="top", fontweight="bold")

    def draw_new(kind, k, badge):
        axN.clear(); axes_common(axN)
        axN.plot(Tt[m], z[m], "--", color=C_CHAR, lw=1.8, label="true steady state")
        axN.set_title("New — flux-anchored (anchor + slope walk)", loc="left",
                      fontsize=12, color=C_HAYNE, fontweight="bold")
        if kind == "start":
            axN.plot(np.full(m.sum(), GUESS), z[m], "-", color=C_DIM, lw=2.2, alpha=0.6)
            axN.text(0.04, 0.10, "start: a flat\nwrong guess (240 K)", transform=axN.transAxes,
                     fontsize=10.5, color=C_DIM, va="top")
            return
        prof = fa["settle"]
        skin = z <= Z0
        axN.plot(prof[skin], z[skin], "-", color=C_DIM, lw=2.4, alpha=0.7)
        if kind in ("anchor", "walk", "converged"):
            axN.plot(z0_T, Z0, "o", color=C_HAYNE, ms=12, zorder=6)
            axN.annotate("anchor\n(known mean-T\nat z = 0.55 m)",
                         xy=(z0_T, Z0), xycoords="data",
                         xytext=(0.04, 0.55), textcoords="axes fraction",
                         fontsize=10, color=C_HAYNE, fontweight="bold", va="center", ha="left",
                         arrowprops=dict(arrowstyle="->", color=C_HAYNE, lw=1.2))
        if kind == "settle":
            axN.plot(prof[skin], z[skin], "-", color=C_A15, lw=2.8)
            axN.text(0.04, 0.10, "Step A — settle skin\n(~12 lunations)", transform=axN.transAxes,
                     fontsize=10.5, color=C_CHAR, va="top", fontweight="bold")
        if kind == "walk":
            built = (z >= Z0) & (z <= z[k])
            axN.plot(fa["T_rec"][built], z[built], "-", color=C_HAYNE, lw=3.2)
            axN.plot(fa["T_rec"][k], z[k], "o", color=C_HAYNE, ms=8, zorder=6)
            slope = Qb / float(K(np.array([fa["T_rec"][k]]), np.array([z[k]]))[0])
            axN.text(0.04, 0.10,
                     "Step B — slope walk\n"
                     r"$\frac{d\langle T\rangle}{dz}=\frac{Q_b-u_{\rm rect}}{K}$"
                     f"\n≈ {slope:.1f} K/m here",
                     transform=axN.transAxes, fontsize=10.5, color=C_HAYNE, va="top")
        if kind == "converged":
            axN.plot(Tt[m], z[m], "-", color=C_HAYNE, lw=3.0)
            axN.text(0.04, 0.10, "converged\n~9 cycles · ~9 s", transform=axN.transAxes,
                     fontsize=11, color=C_HAYNE, va="top", fontweight="bold")
        if badge:
            axN.text(0.96, 0.93, "≈ 80× faster", transform=axN.transAxes,
                     fontsize=15, color=C_A17, ha="right", va="top", fontweight="bold",
                     bbox=dict(boxstyle="round,pad=0.4", fc="white", ec=C_A17, lw=1.4))

    fig.suptitle("Reaching steady state: brute force vs the flux-anchored anchor",
                 fontsize=13.5, color=C_CHAR, fontweight="bold", y=0.985)
    cap_text = fig.text(0.5, 0.025, "", ha="center", va="bottom", fontsize=11,
                        color=C_DIM, style="italic")          # one artist, updated per frame
    fig.subplots_adjust(left=0.065, right=0.985, top=0.88, bottom=0.13, wspace=0.10)

    def update(i):
        sp = specs[i]
        draw_old(sp["old"], frozen=(sp["act"] >= 2))
        draw_new(sp["new"][0], sp["new"][1], sp.get("badge", False))
        cap_text.set_text(sp["cap"]); return []

    print(f"Encoding GIF ({len(specs)} frames)...")
    anim = FuncAnimation(fig, update, frames=len(specs), blit=False)
    gif = DOC / "old_vs_new.gif"
    anim.save(str(gif), writer=PillowWriter(fps=8), dpi=100)
    plt.close(fig)
    print(f"  -> {gif.relative_to(_REPO)}  ({gif.stat().st_size/1e6:.1f} MB)")

    # ---- static 6-panel filmstrip for the PDF book ------------------------
    bf30 = min(bf, key=lambda f: abs(f["lun"] - 30))
    kmid = walk_cells[len(walk_cells) // 2]
    cols = [
        ("old", bf30, None, "old: 30 lunations\n(deep NOT settled)"),
        ("old", OLD_FINAL, None, "old: ~1000 lunations\n(still creeping)"),
        ("new", "settle", None, "new A: settle skin"),
        ("new", "anchor", None, "new: drop anchor (0.55 m)"),
        ("new", "walk", kmid, "new B: slope walk down"),
        ("new", "converged", None, "new: converged (~9 s)"),
    ]
    fig, axes = plt.subplots(1, 6, figsize=(15.5, 3.6), sharey=True)
    for ax, (which, a, k, lab) in zip(axes, cols):
        ax.invert_yaxis(); ax.set_xlim(*TLIM); ax.set_ylim(ZMAX, 0)
        ax.axhspan(0.8, 2.4, color=C_DIM, alpha=0.07, zorder=0)
        ax.plot(Tt[m], z[m], "--", color=C_CHAR, lw=1.4)
        if which == "old":
            ax.fill_betweenx(z[m], a["lo"][m], a["hi"][m], color=C_A15, alpha=0.12)
            ax.plot(a["mean"][m], z[m], "-", color=C_A15, lw=2.2)
        else:
            skin = z <= Z0
            ax.plot(fa["settle"][skin], z[skin], "-", color=C_DIM, lw=2.0, alpha=0.7)
            if a in ("anchor", "walk", "converged"):
                ax.plot(z0_T, Z0, "o", color=C_HAYNE, ms=8, zorder=5)
            if a == "settle":
                ax.plot(fa["settle"][skin], z[skin], "-", color=C_A15, lw=2.4)
            if a == "walk":
                b = (z >= Z0) & (z <= z[k]); ax.plot(fa["T_rec"][b], z[b], "-", color=C_HAYNE, lw=2.8)
            if a == "converged":
                ax.plot(Tt[m], z[m], "-", color=C_HAYNE, lw=2.6)
        ax.set_title(lab, fontsize=9.5, color=C_CHAR, pad=5)
        ax.set_xlabel("T [K]", fontsize=9); ax.grid(alpha=0.18)
    axes[0].set_ylabel("depth [m]", fontsize=11)
    fig.suptitle("Reaching steady state: brute force (~1000 lunations) vs the flux-anchored anchor + slope walk (~9 s)",
                 fontsize=12, color=C_CHAR, fontweight="bold")
    fig.tight_layout(rect=[0, 0, 1, 0.92])
    out = FIG / "old_vs_new_filmstrip.pdf"
    fig.savefig(out, bbox_inches="tight"); plt.close(fig)
    print(f"  -> {out.relative_to(_REPO)}")


if __name__ == "__main__":
    main()
