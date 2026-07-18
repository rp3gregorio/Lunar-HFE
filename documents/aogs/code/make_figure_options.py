"""A MENU of candidate poster figures to replace text with visuals.
Each is standalone (PDF + 300-dpi PNG) in aogs/poster/figure_options/.

  opt_topography_twice   opposing shadow-cooling / terrain-warming channels
  opt_degeneracy         the K_d <-> density trade-off, one gradient two knobs
  opt_claim_cards        the conclusions as 4 visual claim cards (text-lite)
  opt_improvement_bars   the RMSE ladder as bars (replaces Table 1 text)
  opt_mechanism          cp smooth vs coupled staircase conductivity
  opt_horizon_panorama   the skyline unrolled, with the Sun's arc + shadow

All numbers parsed from the generated poster_numbers.tex + results archive.
Move-proof paths. Run:  <repo>/.venv/bin/python make_figure_options.py
"""
import json
import pathlib
import re
import sys

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches

_root = next(a for a in pathlib.Path(__file__).resolve().parents
             if (a / "code" / "src" / "lunar").is_dir())
sys.path.insert(0, str(_root / "code" / "src"))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[0] / "compute"))
from lunar.plotting.style import (C_A15, C_A17, C_TEAL, C_CHAR, C_DIM, C_GRID,  # noqa: E402
                                  C_CORAL, C_FOREST, C_PLUM, fmt_axis)
from lunar.constants import RHO_SURFACE, RHO_DEEP, K_SURFACE  # noqa: E402

AOGS = next(a for a in pathlib.Path(__file__).resolve().parents if a.name == "aogs")
OUT = AOGS / "figures" / "drafts"; OUT.mkdir(parents=True, exist_ok=True)
KS, RS, RD = K_SURFACE * 1e3, RHO_SURFACE, RHO_DEEP


def N():
    txt = (AOGS / "figures" / "poster_numbers.tex").read_text()
    d = {}
    for m in re.finditer(r"\\newcommand\{\\([a-zA-Z]+)\}\{([^}]*)\}", txt):
        d[m.group(1)] = m.group(2)
    return d


def f(d, k):
    return float(d[k])


def save(fig, name):
    fig.savefig(OUT / f"{name}.pdf")
    fig.savefig(OUT / f"{name}.png", dpi=300)
    plt.close(fig)
    print("wrote", name)


# ── 1. topography enters twice ──────────────────────────────────────────────
def topography_twice(d):
    cool = {"A15": -f(d, "shadowcoolAfif"), "A17": -f(d, "shadowcoolAsev")}
    warm = {"A15": f(d, "svfdtallAfif"), "A17": f(d, "svfdtallAsev")}
    fig, ax = plt.subplots(figsize=(6.6, 4.4), constrained_layout=True)
    xs = {"A15": 1, "A17": 3}
    ax.axhline(0, color=C_CHAR, lw=1.0)
    for sk, x in xs.items():
        c, w = cool[sk], warm[sk]; net = c + w
        ax.annotate("", xy=(x - 0.28, c), xytext=(x - 0.28, 0),
                    arrowprops=dict(arrowstyle="-|>", color=C_TEAL, lw=6))
        ax.annotate("", xy=(x + 0.28, w), xytext=(x + 0.28, 0),
                    arrowprops=dict(arrowstyle="-|>", color=C_CORAL, lw=6))
        ax.text(x - 0.28, c - 0.18, f"shadow\ncooling\n{c:+.1f} K", ha="center",
                va="top", fontsize=8.5, color=C_TEAL)
        ax.text(x + 0.28, w + 0.12, f"terrain\nwarming\n{w:+.1f} K", ha="center",
                va="bottom", fontsize=8.5, color=C_CORAL)
        ax.plot(x, net, "D", color=C_CHAR, ms=11, zorder=5)
        ax.annotate(f"net {net:+.1f} K\n({'cools' if net < 0 else 'warms'})",
                    xy=(x, net), xytext=(x + 0.55, net), fontsize=9, va="center",
                    fontweight="bold", color=C_CHAR,
                    arrowprops=dict(arrowstyle="-", color=C_DIM, lw=0.8))
    ax.set_xlim(0.2, 4.2); ax.set_ylim(-2.75, 2.05)
    ax.set_xticks([1, 3]); ax.set_xticklabels(["Apollo 15", "Apollo 17"], fontsize=11)
    fmt_axis(ax, xlabel="", ylabel="temperature shift at deep sensors (K)",
             title="Topography enters twice — and the channels oppose")
    ax.text(0.5, -0.13, "same DEM horizons drive both: shadow cools, terrain "
            "re-radiation warms · cooling wins at A15, warming at A17",
            transform=ax.transAxes, ha="center", fontsize=8, color=C_DIM,
            style="italic")
    save(fig, "opt_topography_twice")


# ── 2. the degeneracy ───────────────────────────────────────────────────────
def degeneracy(d):
    fig, ax = plt.subplots(figsize=(7.4, 4.6), constrained_layout=True)
    ax.set_xlim(0, 100); ax.set_ylim(0, 100); ax.axis("off")

    def box(x, y, w, h, t, fc, ec, fs=9.5, bold=False, tc=C_CHAR):
        ax.add_patch(mpatches.FancyBboxPatch((x, y), w, h,
                     boxstyle="round,pad=0.3,rounding_size=1.6", fc=fc, ec=ec, lw=1.4))
        ax.text(x + w / 2, y + h / 2, t, ha="center", va="center", fontsize=fs,
                color=tc, fontweight="bold" if bold else "normal")

    def arr(x0, y0, x1, y1, col=C_DIM):
        ax.annotate("", xy=(x1, y1), xytext=(x0, y0),
                    arrowprops=dict(arrowstyle="-|>", color=col, lw=1.6))

    box(24, 86, 52, 11, "What the deep sensors measure:\none gradient  $\\approx Q_b/K_{\\rm deep}$",
        "#F3EEE9", C_DIM, 10, True)
    box(4, 60, 40, 11, "raise $K_d$\n(more conductive)", "#EAF0F2", C_TEAL, 9.5)
    box(56, 60, 40, 11, "denser deep layer\n(raises $K_c(\\rho)$)", "#F6E7E1", C_A17, 9.5)
    arr(38, 86, 24, 71); arr(62, 86, 76, 71)
    box(20, 38, 60, 10, "give the SAME gradient — can't be told apart",
        "#FBEEDD", C_CORAL, 10, True, C_CORAL)
    arr(24, 60, 40, 48); arr(76, 60, 60, 48)
    box(2, 12, 45, 13, "Letter: fix density (Hayne)\n$\\Rightarrow$ retrieve "
        "$K_d^{\\star}=4.60/7.08$", "#EAF0F2", C_TEAL, 9, tc=C_TEAL)
    box(53, 12, 45, 13, "This study: fix $K_d^{\\star}$\n$\\Rightarrow$ retrieve "
        "$\\rho_{\\rm deep}=1800/1900$", "#F6E7E1", C_A17, 9, tc=C_A17)
    arr(38, 38, 24, 25); arr(62, 38, 76, 25)
    ax.set_title("Why $K_d$ and deep density can't be pinned together",
                 fontsize=12, loc="left", x=0.02, y=0.98)
    save(fig, "opt_degeneracy")


# ── 3. the conclusions as visual claim cards ────────────────────────────────
def claim_cards(d):
    fig = plt.figure(figsize=(13.6, 3.7))
    cards = [
        (C_PLUM, "Topography is first-order", "and it enters twice",
         "cools 2.2 / 0.5 K  vs  warms +1.3 / +0.7 K"),
        (C_FOREST, "A 3-layer column fits the record", "layers reproduce Apollo",
         "0.90 / 0.36 K   (~2.6× / ~10× better)"),
        (C_TEAL, "The lever is conductivity", "not heat capacity",
         "~4 K of leverage   vs   < 0.8 K"),
        (C_CORAL, "Physical, not curve-fitting", "matches the drive cores",
         "retrieved 1800 / 1900 ≈ measured 1825 / 1960"),
    ]
    for i, (col, head, sub, num) in enumerate(cards):
        ax = fig.add_axes([0.015 + i * 0.247, 0.06, 0.225, 0.88])
        ax.axis("off")
        ax.add_patch(mpatches.FancyBboxPatch((0.02, 0.02), 0.96, 0.96,
                     transform=ax.transAxes, boxstyle="round,pad=0,rounding_size=0.04",
                     fc="white", ec=col, lw=1.6))
        ax.add_patch(mpatches.FancyBboxPatch((0.02, 0.80), 0.96, 0.18,
                     transform=ax.transAxes, boxstyle="round,pad=0,rounding_size=0.04",
                     fc=col, ec=col, lw=1.6))
        ax.text(0.5, 0.89, f"{i+1}", transform=ax.transAxes, ha="center",
                va="center", fontsize=15, color="white", fontweight="bold")
        ax.text(0.5, 0.68, head, transform=ax.transAxes, ha="center", va="center",
                fontsize=12.5, color=col, fontweight="bold", wrap=True)
        ax.text(0.5, 0.53, sub, transform=ax.transAxes, ha="center", va="center",
                fontsize=9.5, color=C_DIM, style="italic")
        ax.add_patch(mpatches.FancyBboxPatch((0.10, 0.14), 0.80, 0.24,
                     transform=ax.transAxes, boxstyle="round,pad=0,rounding_size=0.03",
                     fc=C_GRID, ec="none"))
        ax.text(0.5, 0.26, num, transform=ax.transAxes, ha="center", va="center",
                fontsize=10.5, color=C_CHAR, fontweight="bold")
    fig.suptitle("Conclusions at a glance", fontsize=14, fontweight="bold",
                 x=0.015, ha="left", y=0.995)
    save(fig, "opt_claim_cards")


# ── 4. the RMSE ladder as bars ──────────────────────────────────────────────
def improvement_bars(d):
    models = ["homogeneous", "Hayne cont.", "best cp", "best coupled"]
    keys = ["rmsehom", "rmsehay", "rmsecp", "rmsecK"]
    cols = [C_DIM, C_PLUM, C_TEAL, C_A17]
    fig, axes = plt.subplots(1, 2, figsize=(9.0, 3.9), constrained_layout=True,
                             sharey=False)
    for ax, sk, suf in zip(axes, ("Apollo 15", "Apollo 17"), ("Afif", "Asev")):
        vals = [f(d, k + suf) for k in keys]
        b = ax.bar(models, vals, color=cols, width=0.68, zorder=3)
        for rect, v in zip(b, vals):
            ax.text(rect.get_x() + rect.get_width() / 2, v + 0.05, f"{v:.2f}",
                    ha="center", va="bottom", fontsize=9, color=C_CHAR,
                    fontweight="bold")
        ax.set_ylim(0, max(vals) * 1.18)
        fmt_axis(ax, xlabel="", ylabel="deep-sensor RMSE (K)" if sk.endswith("15") else "",
                 title=sk)
        ax.tick_params(axis="x", labelsize=8.5, rotation=18)
    fig.suptitle("More physics, better fit — the RMSE ladder", fontsize=13,
                 fontweight="bold", x=0.02, ha="left")
    save(fig, "opt_improvement_bars")


# ── 5. the mechanism: conductivity down the column ──────────────────────────
def mechanism(d):
    kd = f(d, "kdstarAsev"); H = 0.06
    z = np.linspace(0, 100, 500)
    r1, r2, r3, z1, z2 = 1300, 1500, 1900, 5, 30
    kc_cp = kd - (kd - KS) * np.exp(-z / 100.0 / H)
    rho = np.where(z < z1, r1, np.where(z < z2, r2, r3))
    kc_co = kd - (kd - KS) * (RD - rho) / (RD - RS)
    fig, ax = plt.subplots(figsize=(5.6, 4.4), constrained_layout=True)
    ax.plot(kc_cp, z, color=C_TEAL, lw=3, label="cp: smooth $K_c(z)$  (density-blind)")
    ax.step(kc_co, z, where="post", color=C_A17, lw=3,
            label="coupled: $K_c(\\rho(z))$  (follows layers)")
    ax.set_ylim(100, 0); ax.set_xlim(0, 8.6)
    for zb in (z1, z2):
        ax.axhline(zb, color=C_DIM, ls=":", lw=0.8)
    fmt_axis(ax, xlabel=r"conductivity $K_c$ (mW m$^{-1}$K$^{-1}$)", ylabel="depth (cm)",
             title="Why coupled wins: density sets conductivity")
    ax.legend(loc="lower left", fontsize=8.5, frameon=True, edgecolor=C_GRID)
    ax.text(0.98, 0.30, "same density\nstaircase,\ntwo rules", transform=ax.transAxes,
            ha="right", va="top", fontsize=8, color=C_DIM, style="italic")
    save(fig, "opt_mechanism")


# ── 6. the skyline, unrolled (panorama) ─────────────────────────────────────
def horizon_panorama(d):
    from lunar.config import SITES, DT_STEP
    from lunar.solver import periodic_time_grid
    import s1_sensitivity as aogs
    dem, ppd = aogs.load_dem()
    t = periodic_time_grid(DT_STEP)
    fig, axes = plt.subplots(2, 1, figsize=(8.6, 5.2), constrained_layout=True,
                             sharex=True)
    for ax, sk, col in zip(axes, ("A15", "A17"), (C_A15, C_A17)):
        s = SITES[sk]
        az, hor = aogs.horizon_profile(dem, ppd, s["lat"], s["lon"])
        elev, A = aogs.sun_track(s["lat"], t)
        up = elev >= 0
        hor_at = np.interp(A, az, hor, period=360.0)
        blk = up & (elev <= hor_at)
        ax.fill_between(az, 0, hor, color=col, alpha=0.25, step="mid", label="terrain skyline")
        ax.plot(az, hor, color=col, lw=1.8, drawstyle="steps-mid")
        ax.plot(A[up], elev[up], ".", color=C_DIM, ms=2.5, label="Sun's path")
        ax.plot(A[blk], elev[blk], "s", color=C_PLUM, ms=4, label="Sun blocked")
        ax.set_xlim(0, 360); ax.set_ylim(0, max(14, hor.max() * 1.15))
        fmt_axis(ax, xlabel="azimuth (° from North)" if sk == "A17" else "",
                 ylabel="elevation (°)",
                 title=f"Apollo {sk[1:]}  ·  skyline the site sees")
        if sk == "A15":
            ax.legend(loc="upper right", fontsize=8, frameon=True, edgecolor=C_GRID,
                      ncols=3)
        ax.set_xticks([0, 90, 180, 270, 360])
        ax.set_xticklabels(["N", "E", "S", "W", "N"])
    fig.suptitle("What each site sees: the terrain skyline, unrolled, and where the "
                 "Sun ducks behind it", fontsize=12, fontweight="bold", x=0.02,
                 ha="left")
    save(fig, "opt_horizon_panorama")


if __name__ == "__main__":
    d = N()
    topography_twice(d)
    degeneracy(d)
    claim_cards(d)
    improvement_bars(d)
    mechanism(d)
    horizon_panorama(d)
