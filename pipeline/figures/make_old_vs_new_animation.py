#!/usr/bin/env python3
"""One animation comparing the two ways of reaching steady state, with the
flux-anchored anchor + downward slope-walk as the centrepiece.

Two persistent panels (all curves real solver output):
  LEFT  -- brute-force spin-up crawling down (~1000 lunations, still drifting);
  RIGHT -- Step A settles the skin, the anchor drops at z0 = 0.55 m, then the
           closure slope (Q_b - u_rect)/K is walked downward to fill the deep
           column; converged in ~9 cycles, ~9 s.

Each panel carries a zoomed deep inset (0.5-2.5 m, T ~ 248-260 K) with a live
deep-error gauge, so the ~1 K gap that brute force still has at 1000 lunations
is visible (it looks converged at full scale -- the F1 trap). A wall-clock bar
shows the measured ~80x (one solve: ~700 s brute vs ~9 s flux-anchored).

Outputs:
  docs/guidebook/old_vs_new.gif                 -- the animation (talks/web)
  docs/guidebook/old_vs_new.mp4                 -- only if ffmpeg is on PATH
  results/figures/old_vs_new_filmstrip.pdf      -- stills for the PDF book

Run from the repo root.  (~3-4 min: it integrates ~1000 lunations once.)
"""
from __future__ import annotations
import sys, pathlib, functools, shutil
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
ZOOM_Z = (2.5, 0.45)          # inverted (top=0.45 m, bottom=2.5 m)
ZOOM_T = (248, 260)
SEC_PER_LUN = 0.23            # measured; guidebook S3.13
T_BRUTE_FULL = 700.0          # one brute solve to convergence (~3000 lun)
T_ANCHORED = 9.0


def _setup():
    g = make_geometric_grid(**GRID); z = g.z_mid; dz = g.dz
    t = np.arange(0, T_LUNAR, DT_STEP)
    insol = S0 * (1 - SITE["albedo"]) * np.clip(np.cos(2 * np.pi * t / T_LUNAR), 0, None)
    K = functools.partial(conductivity_hayne, Ks=HAYNE["K_S"], Kd=KD, H=HAYNE["H"], chi=HAYNE["CHI"])
    cp = functools.partial(specific_heat, model="hayne")
    eq = solve_periodic_equilibrium(grid=g, t=t, insolation=insol, albedo=SITE["albedo"],
            emissivity=SITE["emissivity"], Q_b=SITE["Q_BASAL"], K_func=K, cp_func=cp, T_guess=SITE["T_MEAN_EFF"])
    return dict(g=g, z=z, dz=dz, t=t, insol=insol, K=K, cp=cp, Qb=SITE["Q_BASAL"],
                T_target=eq.T_mean, ip=int(np.argmin(np.abs(z - PROBE_Z))),
                i0=int(np.argmin(np.abs(z - Z0))))


def _brute_frames(S):
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
    z0_T = fa["settle"][i0]
    walk_cells = [i for i in range(i0, z.size) if z[i] <= ZMAX]
    OLD_FINAL = bf[-1]

    # ---- frame plan (act, panel states, wall-clock, anchor pulse) ----------
    specs = []
    for fr in bf[::2] + [bf[-1]] * 2:
        cap = "Old way: brute-force spin-up -- the skin snaps fast, the deep column crawls"
        specs.append(dict(act=1, old=fr, new=("start", None), pulse=0,
                          old_t=fr["lun"] * SEC_PER_LUN, new_t=0.0, cap=cap))
    specs += [dict(act=2, old=OLD_FINAL, new=("settle", None), pulse=0, old_t=230, new_t=3.0,
                   cap="New way - Step A: a short run (~12 lunations) settles the fast surface skin")] * 6
    for j in range(12):
        specs.append(dict(act=2, old=OLD_FINAL, new=("anchor", None), pulse=min(j, 6), old_t=230, new_t=4.0,
                          cap="Drop the anchor at z = 0.55 m -- its cycle-mean temperature is known"))
    for wi, k in enumerate(walk_cells):
        specs.append(dict(act=2, old=OLD_FINAL, new=("walk", k), pulse=6,
                          old_t=230, new_t=4.0 + 4.0 * wi / max(len(walk_cells) - 1, 1),
                          cap="Step B: walk the closure slope (Q_b - u_rect)/K downward -- the deep column draws itself"))
    specs += [dict(act=2, old=OLD_FINAL, new=("walk", walk_cells[-1]), pulse=6, old_t=230, new_t=8.0,
                   cap="Step B: walk the closure slope (Q_b - u_rect)/K downward -- the deep column draws itself")] * 3
    specs += [dict(act=2, old=OLD_FINAL, new=("converged", None), pulse=6, old_t=230, new_t=9.0,
                   cap="A few refine cycles polish it -- converged in ~9 cycles, ~9 s")] * 4
    specs += [dict(act=3, old=OLD_FINAL, new=("converged", None), badge=True, pulse=6, old_t=230, new_t=9.0,
                   cap="Same steady state, ~80x faster: ~700 s brute force  vs  ~9 s flux-anchored")] * 18

    # ---- figure: 2 panels + a wall-clock bar strip -------------------------
    fig = plt.figure(figsize=(11.0, 6.2))
    gs = fig.add_gridspec(2, 2, height_ratios=[5.4, 1.0], width_ratios=[1, 1],
                          left=0.065, right=0.985, top=0.90, bottom=0.10, hspace=0.55, wspace=0.10)
    axO = fig.add_subplot(gs[0, 0]); axN = fig.add_subplot(gs[0, 1], sharey=axO)
    axBar = fig.add_subplot(gs[1, :])
    # NB: insets are created *inside* the draw functions each frame, because
    # ax.clear() removes child inset axes.

    def base(ax):
        ax.invert_yaxis(); ax.set_xlim(*TLIM); ax.set_ylim(ZMAX, 0)
        ax.set_xlabel("cycle-mean temperature  [K]")
        ax.axhspan(0.8, 2.4, color=C_DIM, alpha=0.07, zorder=0)

    def zoom(ax, err, col):
        ax.set_xlim(*ZOOM_T); ax.set_ylim(*ZOOM_Z)
        ax.axhspan(0.8, 2.4, color=C_DIM, alpha=0.10, zorder=0)
        ax.tick_params(labelsize=7); ax.set_title(f"deep zoom · error {err:.1f} K",
                                                  fontsize=8.5, color=col, pad=2)
        for s in ax.spines.values(): s.set_edgecolor(C_DIM)

    def draw_old(fr, frozen):
        axO.clear(); base(axO); axO.set_ylabel("depth  [m]")
        axO.fill_betweenx(z[m], fr["lo"][m], fr["hi"][m], color=C_A15, alpha=0.12)
        axO.plot(Tt[m], z[m], "--", color=C_CHAR, lw=1.8)
        axO.plot(fr["mean"][m], z[m], "-", color=C_A15, lw=2.8)
        axO.set_title("Old - brute-force spin-up", loc="left", fontsize=12, color=C_CHAR, fontweight="bold")
        err = abs(fr["mean"][ip] - Tt[ip])
        axO.text(0.04, 0.17, f"lunation  {fr['lun']:>4d}\ndeep error  {err:4.1f} K",
                 transform=axO.transAxes, fontsize=10, color=C_DIM, va="top", family="monospace")
        if frozen:
            axO.text(0.04, 0.40, "still drifting --\n~3000 lunations\nto fully settle",
                     transform=axO.transAxes, fontsize=10, color=C_A17, va="top", fontweight="bold")
        axoi = axO.inset_axes([0.66, 0.30, 0.31, 0.60]); zoom(axoi, err, C_A17)
        axoi.plot(Tt, z, "--", color=C_CHAR, lw=1.6)
        axoi.plot(fr["mean"], z, "-", color=C_A15, lw=2.4)

    def draw_new(kind, k, pulse, badge):
        axN.clear(); base(axN)
        axN.plot(Tt[m], z[m], "--", color=C_CHAR, lw=1.8)
        axN.set_title("New - flux-anchored (anchor + slope walk)", loc="left",
                      fontsize=12, color=C_HAYNE, fontweight="bold")
        skin = z <= Z0
        prof_err = 99.0
        if kind == "start":
            axN.plot(np.full(m.sum(), GUESS), z[m], "-", color=C_DIM, lw=2.2, alpha=0.6)
            axN.text(0.04, 0.12, "start: a flat\nwrong guess (240 K)", transform=axN.transAxes,
                     fontsize=10.5, color=C_DIM, va="top")
        else:
            axN.plot(fa["settle"][skin], z[skin], "-", color=C_DIM, lw=2.4, alpha=0.7)
            ms = 10 + 2.0 * pulse if kind == "anchor" else 13
            axN.plot(z0_T, Z0, "o", color=C_HAYNE, ms=ms, zorder=6)
            axN.annotate("anchor\n(known mean-T\nat z = 0.55 m)", xy=(z0_T, Z0), xycoords="data",
                         xytext=(0.04, 0.52), textcoords="axes fraction", fontsize=10, color=C_HAYNE,
                         fontweight="bold", va="center", ha="left",
                         arrowprops=dict(arrowstyle="->", color=C_HAYNE, lw=1.2))
            if kind == "settle":
                axN.plot(fa["settle"][skin], z[skin], "-", color=C_A15, lw=2.8)
                axN.text(0.04, 0.12, "Step A - settle skin\n(~12 lunations)", transform=axN.transAxes,
                         fontsize=10.5, color=C_CHAR, va="top", fontweight="bold")
            if kind == "walk":
                built = (z >= Z0) & (z <= z[k])
                axN.plot(fa["T_rec"][built], z[built], "-", color=C_HAYNE, lw=3.2)
                axN.plot(fa["T_rec"][k], z[k], "o", color=C_HAYNE, ms=7, zorder=6)
                slope = Qb / float(K(np.array([fa["T_rec"][k]]), np.array([z[k]]))[0])
                axN.text(0.04, 0.12, "Step B - slope walk\n"
                         r"$\frac{d\langle T\rangle}{dz}=\frac{Q_b-u_{\rm rect}}{K}$"
                         f"\n≈ {slope:.1f} K/m here", transform=axN.transAxes,
                         fontsize=10.5, color=C_HAYNE, va="top")
                prof_err = abs(fa["T_rec"][ip] - Tt[ip]) if z[k] >= PROBE_Z else 99.0
            if kind == "converged":
                axN.plot(Tt[m], z[m], "-", color=C_HAYNE, lw=3.0)
                axN.text(0.04, 0.12, "converged\n~9 cycles · ~9 s", transform=axN.transAxes,
                         fontsize=11, color=C_HAYNE, va="top", fontweight="bold")
                prof_err = 0.0
        if badge:
            axN.text(0.97, 0.15, "≈ 80× faster", transform=axN.transAxes, fontsize=15, color=C_A17,
                     ha="right", va="bottom", fontweight="bold",
                     bbox=dict(boxstyle="round,pad=0.4", fc="white", ec=C_A17, lw=1.4))
        # new deep-zoom inset (+ build-point slope vector when walking)
        if kind != "start":
            axni = axN.inset_axes([0.66, 0.30, 0.31, 0.60])
            zoom(axni, prof_err if prof_err < 50 else 0.0, C_HAYNE)
            axni.plot(Tt, z, "--", color=C_CHAR, lw=1.6)
            if kind in ("settle", "anchor"):
                axni.plot(fa["settle"][skin], z[skin], "-", color=C_DIM, lw=2.2, alpha=0.7)
                axni.plot(z0_T, Z0, "o", color=C_HAYNE, ms=7, zorder=6)
            if kind == "walk":
                built = (z >= Z0) & (z <= z[k])
                axni.plot(fa["T_rec"][built], z[built], "-", color=C_HAYNE, lw=3.0)
                if ZOOM_Z[1] <= z[k] <= ZOOM_Z[0]:
                    slope = Qb / float(K(np.array([fa["T_rec"][k]]), np.array([z[k]]))[0])
                    dd = 0.35
                    axni.annotate("", xy=(fa["T_rec"][k] + slope * dd, z[k] + dd), xytext=(fa["T_rec"][k], z[k]),
                                  arrowprops=dict(arrowstyle="-|>", color=C_A17, lw=2.4))
                    axni.plot(fa["T_rec"][k], z[k], "o", color=C_HAYNE, ms=6, zorder=7)
            if kind == "converged":
                axni.plot(Tt, z, "-", color=C_HAYNE, lw=2.8)

    def draw_bar(old_t, new_t, frozen):
        axBar.clear()
        axBar.barh([1], [min(old_t, 230)], color=C_A17, height=0.55, zorder=3)
        if frozen:
            axBar.barh([1], [T_BRUTE_FULL - 230], left=230, color=C_A17, height=0.55,
                       alpha=0.30, hatch="//", zorder=2)
        axBar.barh([0], [max(new_t, 0.1)], color=C_HAYNE, height=0.55, zorder=3)
        axBar.set_xlim(0, 720); axBar.set_ylim(-0.7, 1.7)
        axBar.set_yticks([0, 1]); axBar.set_yticklabels(["flux-anchored", "brute force"], fontsize=9)
        axBar.set_xlabel("wall-clock per solve  [s]", fontsize=9)
        axBar.tick_params(labelsize=8)
        for s in ("top", "right", "left"): axBar.spines[s].set_visible(False)
        if frozen:
            axBar.text(224, 1, "230 s", va="center", ha="right", fontsize=8, color="white", fontweight="bold")
            axBar.text(700, 1.55, "~700 s to fully settle", va="center", ha="right", fontsize=8, color=C_A17)
        else:
            axBar.text(min(old_t, 230) + 8, 1, f"~{int(round(old_t))} s", va="center", fontsize=8.5, color=C_CHAR)
        axBar.text(max(new_t, 0.1) + 8, 0, f"~{int(round(new_t))} s", va="center", fontsize=8.5, color=C_HAYNE)

    fig.suptitle("Reaching steady state: brute force vs the flux-anchored anchor",
                 fontsize=13.5, color=C_CHAR, fontweight="bold", y=0.985)
    cap_text = fig.text(0.5, 0.005, "", ha="center", va="bottom", fontsize=11, color=C_DIM, style="italic")

    def update(i):
        sp = specs[i]; frozen = sp["act"] >= 2
        draw_old(sp["old"], frozen)
        draw_new(sp["new"][0], sp["new"][1], sp.get("pulse", 0), sp.get("badge", False))
        draw_bar(sp["old_t"], sp["new_t"], frozen)
        cap_text.set_text(sp["cap"]); return []

    print(f"Encoding GIF ({len(specs)} frames)...")
    anim = FuncAnimation(fig, update, frames=len(specs), blit=False)
    gif = DOC / "old_vs_new.gif"
    anim.save(str(gif), writer=PillowWriter(fps=8), dpi=100)
    print(f"  -> {gif.relative_to(_REPO)}  ({gif.stat().st_size/1e6:.1f} MB)")

    if shutil.which("ffmpeg"):
        from matplotlib.animation import FFMpegWriter
        mp4 = DOC / "old_vs_new.mp4"
        anim.save(str(mp4), writer=FFMpegWriter(fps=8, bitrate=2400), dpi=110)
        print(f"  -> {mp4.relative_to(_REPO)}  ({mp4.stat().st_size/1e6:.1f} MB)")
    else:
        print("  (no ffmpeg on PATH -> MP4 skipped; GIF only)")
    plt.close(fig)

    # ---- static filmstrip: full-scale row + deep-zoom row ------------------
    bf30 = min(bf, key=lambda f: abs(f["lun"] - 30))
    kmid = walk_cells[len(walk_cells) // 2]
    cols = [("old", bf30, None, "old: 30 lunations"),
            ("old", OLD_FINAL, None, "old: ~1000 lunations"),
            ("new", "settle", None, "new A: settle skin"),
            ("new", "anchor", None, "new: drop anchor"),
            ("new", "walk", kmid, "new B: slope walk"),
            ("new", "converged", None, "new: converged (~9 s)")]
    fig, axes = plt.subplots(2, 6, figsize=(15.5, 5.4),
                             gridspec_kw=dict(height_ratios=[2.1, 1.0], hspace=0.32))
    skin = z <= Z0
    for c, (which, a, k, lab) in enumerate(cols):
        top, bot = axes[0, c], axes[1, c]
        for ax, lo, hi in ((top, TLIM, (ZMAX, 0)), (bot, ZOOM_T, ZOOM_Z)):
            ax.set_xlim(*lo); ax.set_ylim(*hi)
            ax.axhspan(0.8, 2.4, color=C_DIM, alpha=0.08, zorder=0)
            ax.plot(Tt, z, "--", color=C_CHAR, lw=1.3)
        if which == "old":
            top.fill_betweenx(z[m], a["lo"][m], a["hi"][m], color=C_A15, alpha=0.12)
            for ax in (top, bot): ax.plot(a["mean"], z, "-", color=C_A15, lw=2.2)
            err = abs(a["mean"][ip] - Tt[ip]); bot.set_title(f"error {err:.1f} K", fontsize=8.5, color=C_A17, pad=2)
        else:
            for ax in (top, bot): ax.plot(fa["settle"][skin], z[skin], "-", color=C_DIM, lw=1.8, alpha=0.7)
            if a in ("anchor", "walk", "converged"):
                for ax in (top, bot): ax.plot(z0_T, Z0, "o", color=C_HAYNE, ms=6, zorder=5)
            if a == "settle":
                top.plot(fa["settle"][skin], z[skin], "-", color=C_A15, lw=2.2)
            if a == "walk":
                b = (z >= Z0) & (z <= z[k])
                for ax in (top, bot): ax.plot(fa["T_rec"][b], z[b], "-", color=C_HAYNE, lw=2.6)
            if a == "converged":
                for ax in (top, bot): ax.plot(Tt, z, "-", color=C_HAYNE, lw=2.4)
                bot.set_title("error 0.0 K", fontsize=8.5, color=C_HAYNE, pad=2)
        top.set_title(lab, fontsize=9.5, color=C_CHAR, pad=5)
        top.invert_yaxis(); top.set_xlabel("T [K]", fontsize=8); top.grid(alpha=0.18); top.tick_params(labelsize=8)
        bot.set_xlabel("T [K]", fontsize=7.5); bot.tick_params(labelsize=7); bot.grid(alpha=0.15)
    axes[0, 0].set_ylabel("depth [m]", fontsize=10); axes[1, 0].set_ylabel("deep zoom", fontsize=9)
    fig.suptitle("Reaching steady state: brute force (~1000 lunations, still ~1 K off) vs the "
                 "flux-anchored anchor + slope walk (~9 s)  ·  bottom row = deep zoom",
                 fontsize=11.5, color=C_CHAR, fontweight="bold")
    fig.tight_layout(rect=[0, 0, 1, 0.94])
    out = FIG / "old_vs_new_filmstrip.pdf"
    fig.savefig(out, bbox_inches="tight"); plt.close(fig)
    print(f"  -> {out.relative_to(_REPO)}")


if __name__ == "__main__":
    main()
