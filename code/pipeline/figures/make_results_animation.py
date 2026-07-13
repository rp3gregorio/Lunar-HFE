#!/usr/bin/env python3
"""Results-explainer animation: how the headline K_d* contrast is made.

Three acts, every number from results/kd_retrieval_results.json (never
hardcoded):

  1. the per-site RMSE(K_d) sweep curves draw in (kd_grid, rmse_curve);
  2. the vertex stars land on the minima with their K_d* labels;
  3. the bootstrap histograms accumulate sample-by-sample (the stored
     1500-draw samples), the 95% CI whiskers appear, and the final hold
     annotates the contrast median + CI.

Outputs (per the lunar-figures conventions: GIF only, no ffmpeg, plus a
static filmstrip PDF because LaTeX cannot embed a GIF):
  results/anim/results_explainer.gif          (~12 s, dpi 100, <1200 px)
  results/figures/fig_results_explainer_filmstrip.pdf

Run: python pipeline/figures/make_results_animation.py
"""
from __future__ import annotations

import json
import pathlib
import sys

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation, PillowWriter

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from lunar.plotting.style import (C_A15, C_A17, C_CHAR, C_DIM, C_GRID,
                                  fmt_axis, assert_no_overlap)

ANIM_OUT = ROOT / ".." / "figures" / "anim"
FIG_OUT = ROOT / ".." / "figures"

N_SWEEP = 40      # frames: curves drawing in
N_STAR = 14       # frames: stars + labels
N_BOOT = 56       # frames: histograms accumulating
N_HOLD = 16       # frames: final annotated hold
N_TOTAL = N_SWEEP + N_STAR + N_BOOT + N_HOLD
FPS = 10

BINS = np.linspace(3.4, 9.2, 44)


def _load():
    d = json.loads((ROOT / "results" / "kd_retrieval_results.json").read_text())
    out = {}
    for s in ("A15", "A17"):
        out[s] = dict(
            kd=np.array(d[s]["kd_grid"]) * 1e3,
            rmse=np.array(d[s]["rmse_curve"]),
            star=d[s]["kd_star"] * 1e3,
            rmse_star=d[s]["rmse_star"],
            samples=np.array(d[s]["bootstrap"]["samples"]) * 1e3,
        )
    cb = d["contrast_bootstrap"]
    out["contrast"] = dict(median=cb["median"] * 1e3, lo=cb["ci_lo"] * 1e3,
                           hi=cb["ci_hi"] * 1e3)
    return out


def _draw(axL, axR, frame, D, hist_ymax):
    """Draw the state at `frame` onto cleared axes (shared by GIF and
    filmstrip so the two can never drift apart)."""
    colors = {"A15": C_A15, "A17": C_A17}

    # ── left: the sweep ──────────────────────────────────────────────────────
    reveal = min(1.0, (frame + 1) / N_SWEEP)          # fraction of curve drawn
    for s in ("A15", "A17"):
        e = D[s]
        m = e["kd"] <= 16.0
        kd, rm = e["kd"][m], e["rmse"][m]
        k = max(2, int(round(reveal * len(kd))))
        axL.plot(kd[:k], rm[:k], color=colors[s], lw=2.2)
    if frame >= N_SWEEP:                              # stars + labels land
        # labels sit high above the bowls (the A15 curve crosses y~1.3-1.7
        # over the A17 bowl, so a merely star-adjacent label collides;
        # placement verified by assert_no_overlap on the filmstrip)
        label_xy = {"A15": (D["A15"]["star"], 2.55),
                    "A17": (D["A17"]["star"] + 0.9, 2.15)}
        for s in ("A15", "A17"):
            e = D[s]
            axL.plot(e["star"], e["rmse_star"], "*", ms=16, color=colors[s],
                     mec="white", mew=0.8, zorder=5)
            axL.annotate(f"{s}  $K_d^*$ = {e['star']:.2f}",
                         (e["star"], e["rmse_star"]),
                         xytext=label_xy[s],
                         ha="center", fontsize=9, color=colors[s],
                         arrowprops=dict(arrowstyle="-", color=C_DIM, lw=0.6))
    fmt_axis(axL, xlabel=r"deep conductivity $K_d$  (mW m$^{-1}$ K$^{-1}$)",
             ylabel="deep-sensor RMSE  (K)",
             title="1.  Sweep $K_d$, keep the best fit")
    axL.set_xlim(0, 16)
    axL.set_ylim(0, 4)

    # ── right: the bootstrap ─────────────────────────────────────────────────
    bframe = frame - (N_SWEEP + N_STAR)
    n_show = 0 if bframe < 0 else int(min(1.0, (bframe + 1) / N_BOOT) ** 1.6
                                      * len(D["A15"]["samples"]))
    for s in ("A15", "A17"):
        e = D[s]
        if n_show > 1:
            axR.hist(e["samples"][:n_show], bins=BINS, color=colors[s],
                     alpha=0.55, edgecolor="white", lw=0.2)
    if bframe >= 0:
        axR.text(0.02, 0.97, f"resamples: {n_show}", transform=axR.transAxes,
                 va="top", ha="left", fontsize=8.5, color=C_DIM)
    if n_show >= len(D["A15"]["samples"]):            # CI whiskers + verdict
        y_w = hist_ymax * 1.06
        for s in ("A15", "A17"):
            sm = D[s]["samples"]
            lo, hi = np.percentile(sm, [2.5, 97.5])
            axR.plot([lo, hi], [y_w, y_w], color=colors[s], lw=2.4,
                     solid_capstyle="butt")
            axR.plot(D[s]["star"], y_w, "*", ms=11, color=colors[s],
                     mec="white", mew=0.7)
            y_w *= 1.075
        c = D["contrast"]
        axR.text(0.98, 0.985,
                 f"contrast A17 $-$ A15 = {c['median']:.1f}\n"
                 f"95% CI [{c['lo']:.1f}, {c['hi']:.1f}] "
                 r"mW m$^{-1}$ K$^{-1}$",
                 transform=axR.transAxes, va="top", ha="right",
                 fontsize=9, color=C_CHAR)
    fmt_axis(axR, xlabel=r"bootstrap $K_d^*$  (mW m$^{-1}$ K$^{-1}$)",
             ylabel="resamples per bin",
             title="2.  Resample the sensors, read the spread")
    axR.set_xlim(BINS[0], BINS[-1])
    axR.set_ylim(0, hist_ymax * 1.58)                 # headroom: whiskers, then text above them


def main():
    D = _load()
    # fixed histogram ceiling so bars grow within a stable frame
    hist_ymax = max(np.histogram(D[s]["samples"], bins=BINS)[0].max()
                    for s in ("A15", "A17"))

    fig, (axL, axR) = plt.subplots(1, 2, figsize=(11.0, 4.4))
    fig.subplots_adjust(left=0.07, right=0.98, top=0.88, bottom=0.15,
                        wspace=0.26)

    def update(frame):
        axL.clear(); axR.clear()
        _draw(axL, axR, frame, D, hist_ymax)
        return []

    anim = FuncAnimation(fig, update, frames=N_TOTAL, blit=False)
    ANIM_OUT.mkdir(parents=True, exist_ok=True)
    gif = ANIM_OUT / "results_explainer.gif"
    anim.save(gif, writer=PillowWriter(fps=FPS), dpi=100)
    plt.close(fig)
    print(f"  -> {gif}  ({N_TOTAL / FPS:.1f} s)")

    # ── filmstrip: 4 key frames, overlap-guarded ─────────────────────────────
    key_frames = [N_SWEEP - 1, N_SWEEP + N_STAR - 1,
                  N_SWEEP + N_STAR + N_BOOT // 2, N_TOTAL - 1]
    fs, axes = plt.subplots(4, 2, figsize=(11.0, 16.0))
    for row, kf in enumerate(key_frames):
        _draw(axes[row, 0], axes[row, 1], kf, D, hist_ymax)
    fs.subplots_adjust(left=0.07, right=0.98, top=0.97, bottom=0.04,
                       hspace=0.55, wspace=0.26)
    fs.canvas.draw()
    for row in range(4):
        assert_no_overlap(axes[row, 0])
        assert_no_overlap(axes[row, 1])
    out = FIG_OUT / "fig_results_explainer_filmstrip.pdf"
    fs.savefig(out)
    plt.close(fs)
    print(f"  -> {out}")


if __name__ == "__main__":
    main()
