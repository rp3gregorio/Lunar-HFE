#!/usr/bin/env python3
"""Concept figures for the study guidebook (paper/primer/guidebook.tex).

These teach ideas, not results. Every figure is built so that NO text
label sits on top of the graphics -- annotations live in dedicated
whitespace, titles, or legends, and the longer explanation goes in the
LaTeX caption.

Outputs (paper/primer/figures/):
  fig_book_conduction.pdf  -- Fourier's law: heat flows down a gradient
  fig_book_numerical.pdf   -- how a continuous equation is computed
  fig_book_bootstrap.pdf   -- resampling, from scratch
  fig_book_mcmc.pdf        -- Bayesian updating + the K_d/Q_b ridge
  fig_book_aicc.pdf        -- overfitting and the AICc penalty

Run:  python scripts/figures/make_book_figures.py
"""
from __future__ import annotations
import json, sys, pathlib

_REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO))
sys.path.insert(0, str(_REPO / "scripts" / "figures"))

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch

from make_results_figures import (   # type: ignore
    C_A15, C_A17, C_HAYNE, C_MS, C_CHAR, C_DIM, C_GRID, C_CORAL, C_TEAL,
    FS_TICK, FS_LABEL, FS_LEGEND, fmt_axis,
)

OUT = _REPO / "paper" / "primer" / "figures"
OUT.mkdir(parents=True, exist_ok=True)
C_HOT = "#C0573B"
C_COLD = "#2A6F8E"


# ══════════════════════════════════════════════════════════════════════════
def fig_conduction():
    """Fourier's law: heat flows from hot to cold, rate = K x steepness."""
    fig, ax = plt.subplots(figsize=(8.6, 3.2))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 4)
    ax.axis("off")

    # the bar, colour graded hot(left) -> cold(right)
    grad = np.linspace(0, 1, 256).reshape(1, -1)
    ax.imshow(grad, extent=[1, 9, 1.2, 2.8], aspect="auto",
              cmap="RdBu", alpha=0.85, zorder=1)
    ax.add_patch(plt.Rectangle((1, 1.2), 8, 1.6, fill=False,
                               edgecolor=C_CHAR, lw=1.3, zorder=2))

    ax.text(1.0, 3.15, "hot end", ha="center", fontsize=FS_TICK, color=C_HOT,
            fontweight="bold")
    ax.text(9.0, 3.15, "cold end", ha="center", fontsize=FS_TICK, color=C_COLD,
            fontweight="bold")

    # heat-flow arrows along the bar
    for x in np.linspace(2.2, 7.8, 4):
        ax.add_patch(FancyArrowPatch((x, 2.0), (x + 1.0, 2.0),
                     arrowstyle="-|>", mutation_scale=14, color="white", lw=2.2,
                     zorder=3))
    ax.text(5.0, 0.55, "heat always flows from hot to cold",
            ha="center", fontsize=FS_TICK, color=C_CHAR)
    ax.text(5.0, 3.55,
            "how fast?   heat rate  =  conductivity $K$  $\\times$  steepness of the "
            "temperature change",
            ha="center", fontsize=FS_LABEL, color=C_CHAR)
    fig.savefig(OUT / "fig_book_conduction.pdf", bbox_inches="tight")
    plt.close(fig)
    print("  -> fig_book_conduction.pdf")


# ══════════════════════════════════════════════════════════════════════════
def fig_numerical():
    """Continuous T(z) -> stacked discrete layers; time in small steps."""
    fig, (axL, axR) = plt.subplots(1, 2, figsize=(9.2, 4.2),
                                   gridspec_kw={"wspace": 0.30})

    z = np.linspace(0, 2.5, 300)
    T = 250 + 6 * (1 - np.exp(-z / 0.5)) + 2.5 * z
    axL.plot(T, z, color=C_TEAL, lw=2.4)
    axL.set_ylim(2.5, 0)
    fmt_axis(axL, xlabel="temperature", ylabel="depth",
             title="(a)  The real world: smooth")
    axL.set_xticks([]); axL.set_yticks([])

    # discretised version
    zf = np.linspace(0, 2.5, 11)
    zc = 0.5 * (zf[:-1] + zf[1:])
    Tc = 250 + 6 * (1 - np.exp(-zc / 0.5)) + 2.5 * zc
    for i in range(len(zc)):
        axR.add_patch(plt.Rectangle((248, zf[i]), Tc[i] - 248,
                      zf[i + 1] - zf[i], facecolor=C_TEAL, alpha=0.25,
                      edgecolor=C_TEAL, lw=0.8))
        axR.plot(Tc[i], zc[i], "o", color=C_TEAL, ms=5, zorder=3)
    axR.plot(T, z, color=C_CHAR, lw=1.0, ls=(0, (3, 2)), alpha=0.6)
    axR.set_ylim(2.5, 0)
    axR.set_xlim(248, 262)
    fmt_axis(axR, xlabel="temperature", ylabel="",
             title="(b)  The computer: thin layers")
    axR.set_xticks([]); axR.set_yticks([])
    axR.annotate("one layer\n($\\Delta z$ thick)", xy=(Tc[5], zc[5]),
                 xytext=(255.5, 1.9), fontsize=FS_TICK - 1, color=C_CHAR,
                 ha="center",
                 arrowprops=dict(arrowstyle="->", color=C_CHAR, lw=0.8))
    fig.savefig(OUT / "fig_book_numerical.pdf", bbox_inches="tight")
    plt.close(fig)
    print("  -> fig_book_numerical.pdf")


# ══════════════════════════════════════════════════════════════════════════
def fig_bootstrap():
    """Resampling explained: data -> many resamples -> spread of answers."""
    fig = plt.figure(figsize=(10.0, 4.4))
    gs = fig.add_gridspec(1, 3, width_ratios=[0.8, 1.0, 1.2], wspace=0.34)
    axA = fig.add_subplot(gs[0])
    axB = fig.add_subplot(gs[1])
    axC = fig.add_subplot(gs[2])

    rng = np.random.default_rng(0)
    # (a) the original sample: 7 dots
    axA.axis("off")
    axA.set_xlim(0, 4); axA.set_ylim(0, 8)
    ids = list("1234567")
    for i, lab in enumerate(ids):
        axA.add_patch(plt.Circle((2, 6.6 - i * 0.85), 0.30, color=C_A15,
                                 alpha=0.85))
        axA.text(2, 6.6 - i * 0.85, lab, ha="center", va="center",
                 color="white", fontsize=FS_TICK - 1, fontweight="bold")
    axA.set_title("(a)  Your 7\nreal sensors", fontsize=FS_LABEL)

    # (b) three example resamples (draw with replacement)
    axB.axis("off")
    axB.set_xlim(0, 6); axB.set_ylim(0, 8)
    for col, x0 in enumerate((0.6, 2.6, 4.6)):
        draw = rng.integers(1, 8, size=7)
        for i, d in enumerate(draw):
            axB.add_patch(plt.Circle((x0 + 0.45, 6.6 - i * 0.85), 0.26,
                          color=C_A17, alpha=0.8))
            axB.text(x0 + 0.45, 6.6 - i * 0.85, str(d), ha="center",
                     va="center", color="white", fontsize=FS_TICK - 2)
        axB.text(x0 + 0.45, 7.5, f"#{col+1}", ha="center", fontsize=FS_TICK - 1,
                 color=C_CHAR)
    axB.set_title("(b)  Redraw 1,500 times\n(repeats allowed)",
                  fontsize=FS_LABEL)
    axB.text(3.0, 0.1, "some sensors appear twice,\nothers not at all",
             ha="center", fontsize=FS_TICK - 1.5, color=C_DIM, style="italic")

    # (c) the resulting spread, from the REAL bootstrap
    d = json.loads((_REPO / "output" / "kd_retrieval_results.json").read_text())
    boot = np.array(d["A15"]["bootstrap"]["samples"]) * 1e3
    lo, hi = np.percentile(boot, [2.5, 97.5])
    axC.hist(boot, bins=np.linspace(boot.min(), boot.max(), 30),
             color=C_A15, alpha=0.6, edgecolor=C_A15, lw=0.4)
    axC.axvspan(lo, hi, color=C_A15, alpha=0.12)
    axC.axvline(np.median(boot), color=C_CHAR, lw=1.6)
    fmt_axis(axC, xlabel="answer for $K_d$ (each redraw)",
             ylabel="how often", title="(c)  The spread = the error bar")
    axC.set_yticks([])
    axC.text(0.97, 0.95, f"95% of answers\nfall in [{lo:.1f}, {hi:.1f}]",
             transform=axC.transAxes, ha="right", va="top",
             fontsize=FS_TICK - 1, color=C_CHAR,
             bbox=dict(boxstyle="round,pad=0.3", facecolor="white",
                       edgecolor=C_GRID))
    fig.savefig(OUT / "fig_book_bootstrap.pdf", bbox_inches="tight")
    plt.close(fig)
    print("  -> fig_book_bootstrap.pdf")


# ══════════════════════════════════════════════════════════════════════════
def fig_mcmc():
    """Bayesian updating (prior x likelihood) + the K_d/Q_b ridge."""
    fig, (axA, axB) = plt.subplots(1, 2, figsize=(9.6, 4.2),
                                   gridspec_kw={"wspace": 0.30})

    # (a) prior x likelihood = posterior
    x = np.linspace(0, 20, 400)
    def g(mu, s): return np.exp(-0.5 * ((x - mu) / s) ** 2)
    prior = 0.6 * g(11, 5)
    like = g(7.5, 1.6)
    post = prior * like
    post /= post.max(); like /= like.max(); prior /= prior.max()
    axA.plot(x, prior, color=C_DIM, lw=2.0, ls=(0, (4, 2)),
             label="prior (what we knew before)")
    axA.plot(x, like, color=C_HAYNE, lw=2.0,
             label="likelihood (what the data say)")
    axA.fill_between(x, 0, post, color=C_CORAL, alpha=0.35)
    axA.plot(x, post, color=C_CORAL, lw=2.4,
             label="posterior (updated belief)")
    fmt_axis(axA, xlabel="value of $K_d$", ylabel="plausibility",
             title="(a)  Bayes' rule: update with data")
    axA.set_yticks([])
    axA.legend(fontsize=FS_LEGEND - 1, loc="upper right", framealpha=0.95)

    # (b) the ridge: K_d and Q_b trade off
    kd = np.linspace(2, 16, 200)
    qb = np.linspace(8, 26, 200)
    KD, QB = np.meshgrid(kd, qb)
    # likelihood high along QB/KD = const (the measured gradient)
    ratio = QB / KD
    L = np.exp(-0.5 * ((ratio - 15 / 8.1) / 0.18) ** 2)
    axB.contourf(KD, QB, L, levels=12, cmap="BuPu", alpha=0.9)
    rng = np.random.default_rng(1)
    # sample points scattered along the ridge
    kds = rng.uniform(4, 13, 220)
    qbs = (15 / 8.1) * kds + rng.normal(0, 0.7, 220)
    m = (qbs > 8) & (qbs < 26)
    axB.plot(kds[m], qbs[m], "o", color=C_CHAR, ms=2.2, alpha=0.5)
    axB.plot(8.1, 15, "*", color=C_CORAL, ms=20, mec="white", mew=1.3)
    fmt_axis(axB, xlabel="conductivity $K_d$",
             ylabel="heat flux $Q_b$",
             title="(b)  Why one borehole can't separate them")
    axB.text(0.04, 0.95, "data fix the ratio\n$Q_b/K_d$, not each one",
             transform=axB.transAxes, ha="left", va="top",
             fontsize=FS_TICK - 1, color=C_CHAR,
             bbox=dict(boxstyle="round,pad=0.3", facecolor="white",
                       edgecolor=C_GRID, alpha=0.9))
    fig.savefig(OUT / "fig_book_mcmc.pdf", bbox_inches="tight")
    plt.close(fig)
    print("  -> fig_book_mcmc.pdf")


# ══════════════════════════════════════════════════════════════════════════
def fig_aicc():
    """Overfitting (under/good/over) + the real AICc model comparison."""
    fig = plt.figure(figsize=(10.0, 4.2))
    gs = fig.add_gridspec(1, 2, width_ratios=[1.5, 1.0], wspace=0.28)
    gsL = gs[0].subgridspec(1, 3, wspace=0.12)
    rng = np.random.default_rng(3)
    xd = np.linspace(0, 1, 9)
    yd = 1.6 * xd + 0.4 + rng.normal(0, 0.12, xd.size)
    titles = ["too simple\n(underfit)", "just right", "too complex\n(overfit)"]
    for k, (deg, ttl) in enumerate(zip((0, 1, 8), titles)):
        ax = fig.add_subplot(gsL[k])
        ax.plot(xd, yd, "o", color=C_A15, ms=5, zorder=3)
        xx = np.linspace(0, 1, 200)
        c = np.polyfit(xd, yd, deg)
        ax.plot(xx, np.polyval(c, xx), color=C_CORAL, lw=2.0)
        ax.set_title(ttl, fontsize=FS_TICK)
        ax.set_xticks([]); ax.set_yticks([])
        ax.set_ylim(yd.min() - 0.4, yd.max() + 0.4)
        for sp in ax.spines.values():
            sp.set_edgecolor(C_GRID)
    fig.text(0.31, 0.015, "(a)  More wiggles always fit the dots better "
             "— but chase noise, not truth",
             ha="center", fontsize=FS_TICK - 0.5, color=C_CHAR)

    # (b) real model comparison bars
    axB = fig.add_subplot(gs[1])
    m = json.loads((_REPO / "output" / "uniform_kd_test.json").read_text())
    labels = ["M1\nper-site $K_d$", "M3\nshared $K_d$", "M2\nshared, free $Q_b$"]
    vals = [m["M1_variable_kd"]["delta_aicc"],
            m["M3_uniform_kd_fixed_qb"]["delta_aicc"],
            m["M2_uniform_kd_free_qb"]["delta_aicc"]]
    cols = [C_TEAL, C_DIM, C_DIM]
    bars = axB.bar(labels, vals, color=cols, alpha=0.8, edgecolor=cols, lw=0.8)
    for b, v in zip(bars, vals):
        axB.text(b.get_x() + b.get_width() / 2, v + 0.12, f"{v:.1f}",
                 ha="center", fontsize=FS_TICK, color=C_CHAR)
    fmt_axis(axB, xlabel="", ylabel="AICc score gap\n(lower = better)",
             title="(b)  Our 3 models scored")
    axB.set_ylim(0, max(vals) * 1.3 + 0.5)
    axB.text(0.5, 0.92, "M1 wins", transform=axB.transAxes, ha="center",
             fontsize=FS_TICK, color=C_TEAL, fontweight="bold")
    fig.savefig(OUT / "fig_book_aicc.pdf", bbox_inches="tight")
    plt.close(fig)
    print("  -> fig_book_aicc.pdf")


def main():
    print("Building guidebook concept figures:")
    fig_conduction()
    fig_numerical()
    fig_bootstrap()
    fig_mcmc()
    fig_aicc()
    print("done.")


if __name__ == "__main__":
    main()
