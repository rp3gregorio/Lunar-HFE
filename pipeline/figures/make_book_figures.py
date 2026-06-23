#!/usr/bin/env python3
"""Concept figures for the study guidebook (docs/guidebook/guidebook.tex).

These teach ideas, not results. Every figure is built so that NO text
label sits on top of the graphics -- annotations live in dedicated
whitespace, titles, or legends, and the longer explanation goes in the
LaTeX caption.

Outputs (results/figures/):
  fig_book_conduction.pdf  -- Fourier's law: heat flows down a gradient
  fig_book_numerical.pdf   -- how a continuous equation is computed
  fig_book_f1_bug.pdf      -- why 30 lunations looked converged but was not
  fig_book_bootstrap.pdf   -- resampling, from scratch
  fig_book_mcmc.pdf        -- Bayesian updating + the K_d/Q_b ridge
  fig_book_mcmc_corner.pdf -- quantile-based K_d/Q_b corner reconstruction
  fig_book_aicc.pdf        -- overfitting and the AICc penalty

Run:  python pipeline/figures/make_book_figures.py
"""
from __future__ import annotations
import json, sys, pathlib

_REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO / "src"))
sys.path.insert(0, str(_REPO / "pipeline" / "figures"))

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch

from lunar.plotting.style import (   # type: ignore
    C_A15, C_A17, C_HAYNE, C_MS, C_CHAR, C_DIM, C_GRID, C_CORAL, C_TEAL,
    FS_TICK, FS_LABEL, FS_LEGEND, fmt_axis,
)

OUT = _REPO / "results" / "figures"
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
    """Resampling explained: data -> many resamples -> spread of answers.

    No text overlays inside the panel data areas; all explanatory text
    lives in the LaTeX caption + figdesc box that follows the figure
    in the guidebook.
    """
    fig = plt.figure(figsize=(10.0, 5.0))
    gs = fig.add_gridspec(1, 3, width_ratios=[0.7, 0.95, 1.0],
                          wspace=0.30, top=0.86, bottom=0.14)
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
    axA.set_title("(a)  The 7 deep sensors", fontsize=FS_LABEL, pad=8)

    # (b) three example resamples (draw with replacement) — labels for the
    # mini-columns go ABOVE the panel as text annotations of the title.
    axB.axis("off")
    axB.set_xlim(0, 6); axB.set_ylim(0, 8)
    for col, x0 in enumerate((0.6, 2.6, 4.6)):
        draw = rng.integers(1, 8, size=7)
        for i, d in enumerate(draw):
            axB.add_patch(plt.Circle((x0 + 0.45, 6.6 - i * 0.85), 0.26,
                          color=C_A17, alpha=0.8))
            axB.text(x0 + 0.45, 6.6 - i * 0.85, str(d), ha="center",
                     va="center", color="white", fontsize=FS_TICK - 2)
        axB.text(x0 + 0.45, 7.55, f"#{col+1}", ha="center",
                 fontsize=FS_TICK - 1, color=C_CHAR)
    axB.set_title("(b)  Three example redraws", fontsize=FS_LABEL, pad=8)

    # (c) the resulting spread, from the REAL bootstrap — clean legend
    # in an outer frame, no inline annotations.
    d = json.loads((_REPO / "results" / "kd_retrieval_results.json").read_text())
    boot = np.array(d["A15"]["bootstrap"]["samples"]) * 1e3
    lo, hi = np.percentile(boot, [2.5, 97.5])
    med = np.median(boot)
    axC.hist(boot, bins=np.linspace(boot.min(), boot.max(), 30),
             color=C_A15, alpha=0.55, edgecolor=C_A15, lw=0.4,
             label="1500 re-fits")
    axC.axvspan(lo, hi, color=C_A15, alpha=0.15,
                label=f"95% CI [{lo:.2f}, {hi:.2f}]")
    axC.axvline(med, color=C_CHAR, lw=1.6,
                label=f"median {med:.2f}")
    fmt_axis(axC, xlabel="recovered $K_d^*$ (mW m$^{-1}$ K$^{-1}$)",
             ylabel="frequency",
             title="(c)  Distribution of $K_d^*$ over the redraws")
    axC.set_yticks([])
    axC.legend(loc="upper right", frameon=True, framealpha=0.97,
               edgecolor=C_GRID, fontsize=FS_TICK - 1,
               labelspacing=0.35, borderpad=0.45)
    fig.savefig(OUT / "fig_book_bootstrap.pdf", bbox_inches="tight")
    plt.close(fig)
    print("  -> fig_book_bootstrap.pdf")


# ══════════════════════════════════════════════════════════════════════════
def fig_f1_bug_schematic():
    """Why the fixed 30-lunation spin-up looked converged but was still wrong."""
    fig, (axA, axB) = plt.subplots(1, 2, figsize=(10.2, 4.0),
                                   gridspec_kw={"wspace": 0.30})

    lun = np.linspace(1, 1000, 600)
    apparent = 0.7 * np.exp(-lun / 7.5) + 0.0012
    deep_error = 40.0 * np.exp(-lun / 360.0) + 0.025
    axA.semilogy(lun, apparent, color=C_TEAL, lw=2.2,
                 label="cycle-to-cycle $\\Delta T$")
    axA.semilogy(lun, deep_error, color=C_CORAL, lw=2.2,
                 label="deep-profile error")
    axA.axhline(0.01, color=C_DIM, lw=1.0, ls=(0, (3, 2)),
                label="old 0.01 K tolerance")
    axA.axvline(30, color=C_CHAR, lw=1.0, ls=":",
                label="30-lunation cut-off")
    fmt_axis(axA, xlabel="spin-up length  [lunations]",
             ylabel="temperature scale  [K]",
             title="(a)  Apparent convergence is the wrong diagnostic")
    axA.set_xlim(1, 1000)
    axA.set_ylim(8e-4, 70)
    # Park the legend in the empty mid-band (between the flat teal line and the
    # declining coral line) so its opaque box never covers a curve.
    axA.legend(fontsize=FS_LEGEND - 1, loc="center left",
               bbox_to_anchor=(0.30, 0.40),
               frameon=True, framealpha=0.97, edgecolor=C_GRID)

    z = np.linspace(0, 2.5, 300)
    true = 252.0 + 4.0 * z + 2.0 * (1 - np.exp(-z / 0.35))
    old_240 = true - 12.0 * (1 - np.exp(-z / 0.45))
    old_260 = true + 10.0 * (1 - np.exp(-z / 0.45))
    fixed = true + 0.025 * np.sin(4 * z)
    axB.plot(old_240, z, color=C_CORAL, lw=1.8,
             label="30-lunation from 240 K")
    axB.plot(old_260, z, color=C_CORAL, lw=1.8, ls=(0, (5, 2)),
             label="30-lunation from 260 K")
    axB.plot(fixed, z, color=C_TEAL, lw=2.4,
             label="flux-anchored fix")
    axB.plot(true, z, color=C_CHAR, lw=1.7, ls=(0, (4, 2)),
             label="true steady state", zorder=5)
    axB.axhspan(0.8, 2.4, color=C_TEAL, alpha=0.08,
                label="Apollo deep-sensor zone")
    axB.invert_yaxis()
    fmt_axis(axB, xlabel="cycle-mean temperature  [K]",
             ylabel="depth  [m]",
             title="(b)  The deep profile has not arrived")
    axB.legend(fontsize=FS_LEGEND - 1.6, loc="lower right",
               frameon=True, framealpha=0.97, edgecolor=C_GRID)
    fig.savefig(OUT / "fig_book_f1_bug.pdf", bbox_inches="tight")
    plt.close(fig)
    print("  -> fig_book_f1_bug.pdf")


# ══════════════════════════════════════════════════════════════════════════
def fig_mcmc():
    """Bayes' rule: prior x likelihood = posterior, illustrated on K_d.

    Single-panel figure.  The K_d-Q_b degeneracy panel that used to sit
    next to this one is now Fig 8.1; keeping two copies confused readers
    about which chapter owned the idea.
    """
    fig, axA = plt.subplots(figsize=(6.4, 3.6))

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
             title="Bayes' rule: prior $\\times$ likelihood $=$ posterior")
    axA.set_yticks([])
    axA.legend(fontsize=FS_LEGEND - 1, loc="upper right", framealpha=0.95)

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
    m = json.loads((_REPO / "results" / "uniform_kd_test.json").read_text())
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


# ══════════════════════════════════════════════════════════════════════════
def fig_raw_record():
    """One Apollo 15 deep sensor's multi-year T(t) trace with the stable-window
    tail highlighted; the mean of that tail is T_eq.  Closes the 'we never
    show what raw data looks like' gap.

    Two panels: (a) full record showing the drilling-heat transient + the
    multi-year settling, (b) zoom on the stable window plateau to make the
    annual oscillation visible.
    """
    from lunar.apollo_helpers import extract_sensor_stability
    blob = extract_sensor_stability("a15", min_depth_cm=80.0)
    # deepest sensor at A15 = probe 1's bottom sensor (the iconic ~139 cm one).
    target = max(blob["sensors"], key=lambda s: s["depth_cm"])
    name = target["sensor"]
    probe = target["probe"]
    series = blob["probe_data"][probe][name]
    t_yr = series["t_day"] / 365.25
    T = series["T"]
    i_start = series["i_start"]
    T_eq = float(target["T_eq"])
    depth = float(target["depth_cm"])
    t_start_yr = t_yr[i_start]

    fig, (axA, axB) = plt.subplots(
        1, 2, figsize=(10.2, 3.6),
        gridspec_kw={"width_ratios": [1.0, 1.1], "wspace": 0.28})

    # ---- (a) full record ----
    axA.plot(t_yr, T, color=C_DIM, lw=0.5, alpha=0.7,
             label="raw record")
    axA.plot(t_yr[i_start:], T[i_start:], color=C_A15, lw=0.9,
             label="stable window")
    axA.axvline(t_start_yr, color=C_CHAR, lw=0.8, ls=":")
    axA.text(t_start_yr, axA.get_ylim()[1] * 0.985,
             f"  window start\n  ({t_start_yr:.1f} yr)",
             fontsize=FS_TICK - 1.5, color=C_CHAR, va="top", ha="left")
    fmt_axis(axA, xlabel="years since 1971-07-31",
             ylabel="temperature (K)",
             title=f"(a)  Full record -- drilling transient + settling")
    axA.legend(fontsize=FS_LEGEND - 1.5, loc="upper right", framealpha=0.95)

    # ---- (b) zoom on stable window ----
    sl = slice(i_start, None)
    axB.plot(t_yr[sl], T[sl], color=C_A15, lw=0.7)
    axB.axhline(T_eq, color=C_CORAL, lw=1.2, ls="--",
                label=f"$T_{{\\rm eq}}={T_eq:.2f}$ K  (mean of window)")
    # show the trend-flatness threshold band: ±0.08 K/yr * window length
    window_yrs = t_yr[-1] - t_start_yr
    pad = max(0.08 * window_yrs * 0.5, 0.05)
    axB.fill_between(t_yr[sl], T_eq - pad, T_eq + pad,
                     color=C_CORAL, alpha=0.10,
                     label=f"$\\pm 0.08$ K/yr drift envelope")
    fmt_axis(axB, xlabel="years since 1971-07-31",
             ylabel="temperature (K)",
             title=f"(b)  Zoom on the stable window -- $T_{{\\rm eq}}$ extracted here")
    axB.legend(fontsize=FS_LEGEND - 1.5, loc="lower right", framealpha=0.95)

    fig.suptitle(f"Apollo 15 probe {probe}, sensor {name} at $z={depth:.0f}$ cm",
                 y=1.02, fontsize=FS_LABEL, color=C_CHAR)
    fig.savefig(OUT / "fig_book_raw_record.pdf", bbox_inches="tight")
    plt.close(fig)
    print("  -> fig_book_raw_record.pdf")


# ══════════════════════════════════════════════════════════════════════════
def fig_mcmc_posterior():
    """The actual MCMC result: per-site K_d marginal + contrast distribution.

    Built from results/bayesian_crosscheck_samples.json (quantiles only --
    raw chains aren't committed).  Each marginal is drawn as a skew-normal
    fit through the (q025, q16, q50, q84, q975) tuple so the shape matches
    the chain summary even without the chain itself.
    """
    d = json.loads(
        (_REPO / "results" / "bayesian_crosscheck_samples.json").read_text())

    fig, (axL, axR) = plt.subplots(
        1, 2, figsize=(10.0, 3.8), gridspec_kw={"wspace": 0.30})

    def _fit_marginal(q):
        """Smooth marginal through the MCMC quantiles, in mW/(m K).

        We have (q025, q16, q50, q84, q975) but not the raw chain.  Build a
        smooth curve by mixing two half-Gaussians on either side of the
        median, with widths sigma_left=(q50-q16)/0.9945 and
        sigma_right=(q84-q50)/0.9945 (the 1-sigma distance for a Gaussian).
        That captures the asymmetric tails the quantile summary implies
        without pretending we have more information than we do.
        """
        q025, q16, q50, q84, q975 = q
        sigL = max((q50 - q16) / 0.9945, 1e-3)
        sigR = max((q84 - q50) / 0.9945, 1e-3)
        lo = q025 - 0.3 * sigL
        hi = q975 + 0.3 * sigR
        x = np.linspace(lo, hi, 600)
        pdf = np.where(x < q50,
                       np.exp(-0.5 * ((x - q50) / sigL) ** 2),
                       np.exp(-0.5 * ((x - q50) / sigR) ** 2))
        if pdf.max() > 0:
            pdf /= pdf.max()
        return x, pdf

    # ---- left: K_d marginals for both sites ----
    for site, color, label in (("A15", C_A15, "Apollo 15"),
                                ("A17", C_A17, "Apollo 17")):
        s = d[site]
        x, pdf = _fit_marginal((s["kd_q025"], s["kd_q16"],
                                s["kd_q50"], s["kd_q84"], s["kd_q975"]))
        axL.fill_between(x, 0, pdf, color=color, alpha=0.30)
        axL.plot(x, pdf, color=color, lw=1.8, label=label)
        axL.axvline(s["kd_q50"], color=color, lw=0.9, ls=":")
    fmt_axis(axL, xlabel="$K_d$  (mW m$^{-1}$ K$^{-1}$)",
             ylabel="posterior density",
             title="(a)  Joint $(K_d, Q_b)$ MCMC: marginal posteriors of $K_d$")
    axL.set_yticks([])
    axL.legend(fontsize=FS_LEGEND - 0.5, loc="upper right", framealpha=0.95)
    axL.set_xlim(0, 14)

    # ---- right: contrast distribution + P(A17>A15) ----
    c = d["contrast"]
    x, pdf = _fit_marginal((c["q025"], c["q16"], c["median"],
                            c["q84"], c["q975"]))
    axR.fill_between(x, 0, pdf, where=(x > 0), color=C_TEAL, alpha=0.35)
    axR.fill_between(x, 0, pdf, where=(x < 0), color=C_DIM, alpha=0.22)
    axR.plot(x, pdf, color=C_CHAR, lw=1.6)
    axR.axvline(0, color=C_CHAR, lw=0.8)
    axR.axvline(c["median"], color=C_CORAL, lw=1.4)
    fmt_axis(axR, xlabel="$\\Delta K_d \\equiv K_d({\\rm A17}) - K_d({\\rm A15})$",
             ylabel="density",
             title="(b)  Posterior contrast")
    axR.set_yticks([])
    # left side: label the negative-tail
    axR.text(0.03, 0.55, "no\ncontrast", transform=axR.transAxes,
             ha="left", va="center", fontsize=FS_TICK - 1.5,
             color=C_DIM, style="italic")
    # right side: the headline number
    axR.text(0.97, 0.55,
             "A17 more\nconductive",
             transform=axR.transAxes, ha="right", va="center",
             fontsize=FS_TICK - 1, color=C_TEAL, style="italic")
    # consolidated stats box, top-centre
    axR.text(0.5, 0.97,
             f"P$(\\Delta K_d > 0) = {c['p_gt']:.3f}$,"
             f"  median $= {c['median']:.2f}$,"
             f"  95% CI $[{c['q025']:.2f},\\, {c['q975']:.2f}]$",
             transform=axR.transAxes, ha="center", va="top",
             fontsize=FS_TICK - 1, color=C_CHAR,
             bbox=dict(boxstyle="round,pad=0.3", facecolor="white",
                       edgecolor=C_GRID, alpha=0.92))

    fig.savefig(OUT / "fig_book_mcmc_posterior.pdf", bbox_inches="tight")
    plt.close(fig)
    print("  -> fig_book_mcmc_posterior.pdf")


def fig_mcmc_corner():
    """Quantile-based 2x2 corner reconstructions for the joint K_d/Q_b posteriors."""
    d = json.loads(
        (_REPO / "results" / "bayesian_crosscheck_samples.json").read_text())

    def _sigma(lo, med, hi):
        return max(0.5 * ((hi - med) + (med - lo)) / 0.9945, 1e-3)

    def _normal_pdf(x, mu, sig):
        y = np.exp(-0.5 * ((x - mu) / sig) ** 2)
        return y / y.max()

    fig = plt.figure(figsize=(10.2, 4.8))
    outer = fig.add_gridspec(1, 2, wspace=0.28)

    for block, site, color in [(outer[0], "A15", C_A15), (outer[1], "A17", C_A17)]:
        s = d[site]
        gs = block.subgridspec(2, 2, width_ratios=[1, 1], height_ratios=[1, 1],
                               wspace=0.08, hspace=0.08)
        ax_k = fig.add_subplot(gs[0, 0])
        ax_blank = fig.add_subplot(gs[0, 1])
        ax_joint = fig.add_subplot(gs[1, 0])
        ax_q = fig.add_subplot(gs[1, 1])
        ax_blank.axis("off")

        kd_mu = s["kd_q50"]
        qb_mu = s["qb_q50"]
        kd_sig = _sigma(s["kd_q16"], s["kd_q50"], s["kd_q84"])
        qb_sig = _sigma(s["qb_q16"], s["qb_q50"], s["qb_q84"])
        rho = 0.92

        kd = np.linspace(s["kd_q025"], s["kd_q975"], 220)
        qb = np.linspace(max(0.1, qb_mu - 2.6 * qb_sig), qb_mu + 2.6 * qb_sig, 220)
        ax_k.fill_between(kd, 0, _normal_pdf(kd, kd_mu, kd_sig),
                          color=color, alpha=0.34)
        ax_k.plot(kd, _normal_pdf(kd, kd_mu, kd_sig), color=color, lw=1.8)
        ax_k.axvline(kd_mu, color=C_CHAR, lw=0.8, ls=":")
        ax_k.set_yticks([])
        ax_k.set_xticklabels([])
        ax_k.set_title(f"{site}: reconstructed posterior", fontsize=FS_LABEL,
                       color=C_CHAR, loc="left")

        K, Q = np.meshgrid(kd, qb)
        X = (K - kd_mu) / kd_sig
        Y = (Q - qb_mu) / qb_sig
        Z = np.exp(-(X**2 - 2 * rho * X * Y + Y**2) / (2 * (1 - rho**2)))
        levels = np.exp(-0.5 * np.array([4.0, 2.30, 1.0]))
        ax_joint.contourf(K, Q, Z, levels=[levels[0], levels[1], levels[2], 1.0],
                          colors=[color], alpha=0.18)
        ax_joint.contour(K, Q, Z, levels=levels, colors=[color], linewidths=1.2)
        ax_joint.plot(kd_mu, qb_mu, "o", ms=4.5, color=C_CHAR)
        fmt_axis(ax_joint, xlabel="$K_d$  [mW m$^{-1}$ K$^{-1}$]",
                 ylabel="$Q_b$  [mW m$^{-2}$]")

        ax_q.fill_betweenx(qb, 0, _normal_pdf(qb, qb_mu, qb_sig),
                           color=color, alpha=0.34)
        ax_q.plot(_normal_pdf(qb, qb_mu, qb_sig), qb, color=color, lw=1.8)
        ax_q.axhline(qb_mu, color=C_CHAR, lw=0.8, ls=":")
        ax_q.set_xticks([])
        ax_q.set_yticklabels([])
        for ax in (ax_k, ax_q):
            for sp in ax.spines.values():
                sp.set_color(C_GRID)
        ax_k.text(0.97, 0.86, f"$K_d$ med. {kd_mu:.2f}",
                  transform=ax_k.transAxes, ha="right", va="top",
                  fontsize=FS_TICK - 1, color=C_CHAR)
        ax_q.text(0.10, 0.92, f"$Q_b$ med.\n{qb_mu:.1f}",
                  transform=ax_q.transAxes, ha="left", va="top",
                  fontsize=FS_TICK - 1, color=C_CHAR)

    fig.savefig(OUT / "fig_book_mcmc_corner.pdf", bbox_inches="tight")
    plt.close(fig)
    print("  -> fig_book_mcmc_corner.pdf")


def main():
    print("Building guidebook concept figures:")
    fig_conduction()
    fig_numerical()
    fig_raw_record()
    fig_f1_bug_schematic()
    fig_bootstrap()
    fig_mcmc()
    fig_mcmc_posterior()
    fig_mcmc_corner()
    fig_aicc()
    print("done.")


if __name__ == "__main__":
    main()
