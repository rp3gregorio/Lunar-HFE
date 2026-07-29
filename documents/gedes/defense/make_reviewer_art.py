#!/usr/bin/env python3
"""Three teaching figures for DEFENSE_REVIEWER.tex.

These exist because three questions in the reviewer are hard to answer in words
alone: why a one-sided tail of 0.031 and a two-sided 95% interval that contains
zero are not in conflict; why n_inner had to go to 96; and where the error
budget actually comes from. All three are drawn from the real result JSONs.

Run:  python documents/gedes/defense/make_reviewer_art.py
Out:  img/rev_*.pdf
"""
from __future__ import annotations
import json
import pathlib
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = pathlib.Path(__file__).resolve().parent
OUT = HERE / "img"
REPO = HERE.parents[2]
R = REPO / "code" / "results"

CHAR, CORAL, TEAL = "#2A2520", "#B85B3A", "#2A6478"
FOREST, DIM, GRID = "#3D6E4A", "#6E6862", "#E8E5E0"
WHITE, TINT = "#FFFFFF", "#F7F5F2"

plt.rcParams.update({
    "font.family": "serif",
    "font.serif": ["Times New Roman", "Times", "DejaVu Serif"],
    "text.color": CHAR, "axes.labelcolor": CHAR,
    "xtick.color": CHAR, "ytick.color": CHAR,
    "axes.edgecolor": CHAR, "savefig.facecolor": WHITE,
    "figure.facecolor": WHITE, "axes.titlelocation": "left",
})


def fmt(ax, xlabel=None, ylabel=None, title=None):
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    ax.grid(color=GRID, lw=0.6)
    ax.set_axisbelow(True)
    ax.tick_params(labelsize=9)
    if xlabel:
        ax.set_xlabel(xlabel, fontsize=10)
    if ylabel:
        ax.set_ylabel(ylabel, fontsize=10)
    if title:
        ax.set_title(title, fontsize=11, fontweight="bold", pad=8)


def save(fig, name):
    fig.savefig(OUT / f"{name}.pdf", bbox_inches="tight", facecolor=WHITE)
    plt.close(fig)
    print("  ", name)


# ------------------------------------------------- Q: one-sided vs two-sided
def fig_tails():
    """The single most confusing number in the thesis, drawn.

    Same distribution, two different cuts: the tail proportion is ONE-sided
    (0.031); the 95% interval is TWO-sided (2.5% per end). Zero sits inside the
    interval precisely because 0.031 > 0.025."""
    d = json.loads((R / "kd_retrieval_results.json").read_text())
    a = np.asarray(d["A15"]["bootstrap"]["samples"]) * 1e3
    b = np.asarray(d["A17"]["bootstrap"]["samples"]) * 1e3
    diff = b - a                       # paired, draw by draw
    lo, hi = np.percentile(diff, [2.5, 97.5])
    p = (diff <= 0).mean()

    fig, axes = plt.subplots(2, 1, figsize=(6.4, 5.0), sharex=True)

    for ax, mode in zip(axes, ("one", "two")):
        n, bins, patches = ax.hist(diff, bins=60, color=TINT,
                                   edgecolor=DIM, lw=0.4)
        peak = n.max()
        if mode == "one":
            for pa, left in zip(patches, bins[:-1]):
                if left < 0:
                    pa.set_facecolor(CORAL)
                    pa.set_edgecolor(CORAL)
            ax.axvline(0, color=CHAR, lw=1.6)
            ax.annotate(f"$P_{{\\rm boot}}(\\Delta K_d \\leq 0) = {p:.3f}$\n"
                        f"{int((diff<=0).sum())} of 1500 draws",
                        xy=(-0.35, peak * 0.10), xytext=(1.15, peak * 0.78),
                        fontsize=9.5, color=CORAL, ha="left",
                        arrowprops=dict(arrowstyle="-|>", color=CORAL, lw=1.2))
            fmt(ax, title="(a)  The tail proportion is ONE-sided")
            ax.text(0.06, peak * 1.02, "zero", fontsize=9, color=CHAR)
        else:
            for pa, left, right in zip(patches, bins[:-1], bins[1:]):
                if right < lo or left > hi:
                    pa.set_facecolor(TEAL)
                    pa.set_edgecolor(TEAL)
            ax.axvline(0, color=CHAR, lw=1.6)
            for x in (lo, hi):
                ax.axvline(x, color=TEAL, lw=1.4, ls=(0, (4, 3)))
            ax.annotate("2.5% cut\nfrom EACH end", xy=(lo, peak * 0.06),
                        xytext=(-2.4, peak * 0.72), fontsize=9.5, color=TEAL,
                        ha="left",
                        arrowprops=dict(arrowstyle="-|>", color=TEAL, lw=1.2))
            ax.text(hi + 0.12, peak * 0.62,
                    f"95% interval\n[{lo:.2f}, {hi:.2f}]\nzero is INSIDE it",
                    fontsize=9.5, color=TEAL, va="center")
            fmt(ax, xlabel="inter-site contrast  $\\Delta K_d = K_d$(A17) $-$ "
                           "$K_d$(A15)   (mW m$^{-1}$ K$^{-1}$)",
                title="(b)  The confidence interval is TWO-sided")
        ax.set_yticks([])
        ax.set_ylabel("how often", fontsize=10)
        ax.set_xlim(-3.0, 6.0)

    fig.text(0.5, -0.03,
             "For zero to fall OUTSIDE a two-sided 95% interval the lower tail "
             "would have to be below 0.025.\nOurs is 0.031. Since "
             "$0.031 > 0.025$, zero is inside — necessarily, and with no "
             "tension at all.",
             ha="center", fontsize=9.5, color=CHAR, linespacing=1.5)
    fig.tight_layout(h_pad=1.8)
    save(fig, "rev_tails")


# ------------------------------------------------------- Q: why n_inner = 96
def fig_convergence():
    """Why the inner spin-up had to go to 96 lunations, and which site forced
    it. Apollo 15 is the slower site: lower K means lower diffusivity."""
    d = json.loads((R / "convergence_scan.json").read_text())
    n = np.asarray(d["n_inner"])
    s = d["series"]

    # plotted against INDEX, not against n: a log axis here puts matplotlib's
    # minor decade labels straight on top of the custom tick labels
    x = np.arange(len(n))
    fig, axes = plt.subplots(1, 2, figsize=(7.0, 3.0))

    ax = axes[0]
    for key, col, lab in [("A15_new", FOREST, "Apollo 15"),
                          ("A17_new", CORAL, "Apollo 17")]:
        k = np.asarray(s[key]["kd_star"])
        ax.plot(x, k - k[-1], "o-", color=col, lw=1.8, ms=5, label=lab,
                mec=WHITE, mew=0.8)
    ax.axhspan(-0.005, 0.005, color=GRID, alpha=0.9, zorder=0)
    ax.axhline(0, color=CHAR, lw=1.0)
    ax.axvline(x[-1], color=DIM, lw=1.2, ls=(0, (4, 3)))
    # both labels parked inside the axes, low and right, where neither curve
    # goes: at the embedded size they collided with the data and the x-label
    ax.text(x[-1] - 0.12, 0.245, "production\n$n_{\\rm inner}=96$",
            fontsize=8.5, color=DIM, ha="right", va="top", linespacing=1.4)
    ax.text(x[-1] - 0.12, 0.115, "shaded: $\\pm0.005$ mW\ncertification band",
            fontsize=8.5, color=DIM, ha="right", va="top", linespacing=1.4)
    ax.set_xticks(x)
    ax.set_xticklabels([str(v) for v in n])
    fmt(ax, xlabel="inner lunations per outer cycle",
        ylabel="$K_d^{*}$ error vs converged  (mW)",
        title="(a)  $K_d^{*}$ is still moving at 12")
    ax.legend(fontsize=9, frameon=True, edgecolor=GRID, loc="upper right")

    ax = axes[1]
    for key, col, lab in [("A15_new", FOREST, "Apollo 15"),
                          ("A17_new", CORAL, "Apollo 17")]:
        ax.plot(x, s[key]["closure_pct"], "o-", color=col, lw=1.8, ms=5,
                mec=WHITE, mew=0.8, label=lab)
    ax.set_yscale("log")
    ax.set_xticks(x)
    ax.set_xticklabels([str(v) for v in n])
    fmt(ax, xlabel="inner lunations per outer cycle",
        ylabel="flux-closure error  (% of $Q_b$)",
        title="(b)  and so is the flux closure")
    fig.tight_layout(w_pad=2.2)
    save(fig, "rev_convergence")


# ------------------------------------------------------ Q: the error budget
def fig_budget():
    """Where the uncertainty actually comes from, per site. The dominant term
    is DIFFERENT at the two sites, which is the honest headline."""
    d = json.loads((R / "kd_error_budget.json").read_text())
    rows = [("basal flux $Q_b$", "sigma_Qb"),
            ("surface albedo $A$", "sigma_A"),
            ("surface conductivity $K_s$", "sigma_Ks"),
            ("statistical (bootstrap)", "sigma_stat"),
            ("common epoch", "sigma_epoch"),
            ("density $\\rho$", "sigma_rho"),
            ("sensor depth", "sigma_zb"),
            ("solver numerics", "sigma_solver")]

    fig, axes = plt.subplots(1, 2, figsize=(6.9, 3.1), sharey=True)
    for ax, site, col in zip(axes, ("A15", "A17"), (FOREST, CORAL)):
        vals = [d[site][k] for _, k in rows]
        y = np.arange(len(rows))[::-1]
        ax.barh(y, vals, height=0.62, color=col, alpha=0.85)
        for yy, v in zip(y, vals):
            ax.text(v + 0.06, yy, f"{v:.2f}", va="center", fontsize=8.5,
                    color=CHAR)
        ax.set_yticks(y)
        ax.set_yticklabels([lab for lab, _ in rows], fontsize=9)
        ax.set_xlim(0, 3.5)
        fmt(ax, xlabel="1$\\sigma$ contribution  (mW m$^{-1}$ K$^{-1}$)",
            title=f"({'ab'[site=='A17']})  "
                  f"{'Apollo 15' if site=='A15' else 'Apollo 17'}"
                  f"   total {d[site]['total_quadrature']:.2f}")
        ax.grid(axis="y", visible=False)
    fig.tight_layout(rect=[0, 0.20, 1, 1])
    fig.text(0.5, 0.055,
             "The dominant term differs by site: the basal flux at Apollo 15, "
             "the surface albedo at Apollo 17.\nThe $\\chi$ conditionality "
             "(3.60 and 17.92 mW) is NOT in these totals — it is quoted "
             "separately, because it is a\nconditionality on a fixed published "
             "constant rather than a random error.",
             ha="center", va="bottom", fontsize=9, color=CHAR, linespacing=1.5)
    save(fig, "rev_budget")


if __name__ == "__main__":
    print("reviewer figures:")
    fig_tails()
    fig_convergence()
    fig_budget()
    print("done ->", OUT)
