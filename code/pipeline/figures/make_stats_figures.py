#!/usr/bin/env python3
"""Teaching figures for the statistics chapter (guidebook "statistics from zero").

Both figures are drawn from the REAL stored bootstrap draws
(results/kd_retrieval_results.json, 1500 samples per site, seed 42):

  fig_stats_bootstrap.pdf -- the two per-site K_d* bootstrap distributions on one
      axis: histogram, median, 95% CI brackets. The small overlap between the
      A15 and A17 clouds IS the "marginal" story, visible before any formula.
  fig_stats_contrast.pdf  -- the paired contrast distribution K_d*(A17)-K_d*(A15):
      the zero line, the shaded <=0 tail whose area is the p-value, the median
      and the 95% CI. Reconstructed as a17_samples - a15_samples (paired by
      draw index; verified to reproduce the stored median/CI/p to all digits).

Run:  python pipeline/figures/make_stats_figures.py
"""
from __future__ import annotations

import json
import pathlib
import sys

import numpy as np
import matplotlib.pyplot as plt

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "src"))
from lunar.plotting.style import (JGR_HALF, C_A15, C_A17, C_PLUM, C_CHAR, C_DIM,
                                  C_GRID, fmt_axis, assert_no_overlap)

ROOT = pathlib.Path(__file__).resolve().parents[2]
OUT = ROOT / "results" / "figures"


def _load():
    d = json.loads((ROOT / "results" / "kd_retrieval_results.json").read_text())
    a15 = np.array(d["A15"]["bootstrap"]["samples"]) * 1e3   # mW/m/K
    a17 = np.array(d["A17"]["bootstrap"]["samples"]) * 1e3
    return d, a15, a17


def fig_bootstrap():
    d, a15, a17 = _load()
    fig, ax = plt.subplots(figsize=(JGR_HALF, 3.3), constrained_layout=True)
    bins = np.linspace(3.5, 9.5, 61)
    ax.hist(a15, bins=bins, color=C_A15, alpha=0.75, label="Apollo 15 (1500 draws)")
    ax.hist(a17, bins=bins, color=C_A17, alpha=0.75, label="Apollo 17 (1500 draws)")
    for s, col in ((a15, C_A15), (a17, C_A17)):
        med = np.median(s)
        lo, hi = np.percentile(s, [2.5, 97.5])
        ax.axvline(med, color=col, lw=1.4, ls="--", ymax=0.78)
        # CI bracket parked under the histograms, clear of the bars
        yb = -14
        ax.plot([lo, hi], [yb, yb], color=col, lw=2.0, clip_on=False)
        for x in (lo, hi):
            ax.plot([x, x], [yb - 4, yb + 4], color=col, lw=2.0, clip_on=False)
    ax.set_ylim(0, 260)
    ax.set_xlim(3.5, 9.5)
    fmt_axis(ax, xlabel=r"bootstrap $K_d^{*}$  (mW m$^{-1}$ K$^{-1}$)",
             ylabel="draws per bin",
             title="the two bootstrap clouds, medians and 95% CIs")
    ax.legend(frameon=True, edgecolor=C_GRID, loc="upper left")
    fig.canvas.draw(); assert_no_overlap(ax)
    OUT.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT / "fig_stats_bootstrap.pdf")
    plt.close(fig)
    print("  -> fig_stats_bootstrap.pdf")


def fig_contrast():
    d, a15, a17 = _load()
    diff = a17 - a15                      # paired by draw index (same seed)
    cb = d["contrast_bootstrap"]
    med, lo, hi = cb["median"] * 1e3, cb["ci_lo"] * 1e3, cb["ci_hi"] * 1e3
    p = cb["p_value"]

    fig, ax = plt.subplots(figsize=(JGR_HALF, 3.3), constrained_layout=True)
    bins = np.linspace(-1.5, 5.5, 71)
    ax.hist(diff[diff > 0], bins=bins, color=C_PLUM, alpha=0.75)
    ax.hist(diff[diff <= 0], bins=bins, color=C_A17, alpha=0.95)
    ax.axvline(0.0, color=C_CHAR, lw=1.4)
    ax.axvline(med, color=C_PLUM, lw=1.4, ls="--", ymax=0.80)
    yb = -7
    ax.plot([lo, hi], [yb, yb], color=C_PLUM, lw=2.0, clip_on=False)
    for x in (lo, hi):
        ax.plot([x, x], [yb - 2, yb + 2], color=C_PLUM, lw=2.0, clip_on=False)
    ax.set_xlim(-1.5, 5.5)
    ax.set_ylim(0, 130)
    fmt_axis(ax, xlabel=r"contrast  $K_d^{*}$(A17) $-$ $K_d^{*}$(A15)  (mW m$^{-1}$ K$^{-1}$)",
             ylabel="draws per bin",
             title="the contrast distribution: the shaded tail IS the p-value")
    n_neg = int(np.sum(diff <= 0))
    ax.text(0.03, 0.92, f"{n_neg} of {diff.size} draws $\\leq 0$\n"
            f"$\\rightarrow$ $p$ = {p:.3f}",
            transform=ax.transAxes, ha="left", va="top", fontsize=8,
            color=C_CHAR)
    ax.text(0.97, 0.92, f"median {med:.2f}\n95% CI [{lo:.2f}, {hi:.2f}]",
            transform=ax.transAxes, ha="right", va="top", fontsize=8,
            color=C_DIM)
    fig.canvas.draw(); assert_no_overlap(ax)
    fig.savefig(OUT / "fig_stats_contrast.pdf")
    plt.close(fig)
    print(f"  -> fig_stats_contrast.pdf  (p={p:.4f}, {n_neg} negative draws)")


def main():
    fig_bootstrap()
    fig_contrast()


if __name__ == "__main__":
    main()
