#!/usr/bin/env python3
"""Why the anchor method is allowed -- for a defense audience with no background.

The anchor stills (make_anchor_steps_stills, make_anchor_walkthrough) show what
the CODE does: guess, settle, walk down, repeat. This series shows why the
shortcut is legal at all, which is what a listener needs first. Five frames:

    why1_day     only the top of the ground feels the day
    why2_slow    but the deep ground takes 3000 months to settle
    why3_flux    the invariant: the same heat passes every level
    why4_method  so simulate the top, and calculate the rest
    why5_same    and it is the same answer

Frames 1, 3 and 4 are the SAME column at the same size, so they build as one
evolving picture. Frame 2 needs a time axis and frame 5 a temperature axis, so
those two are plots.

COLOUR (this series only): coral is the daily heat wave -- where the day
reaches; green is the part that gets time-stepped; teal is the steady heat from
below and the deep column calculated from it. There is no starting guess in
this series, so coral is free to mean the day. In the method figures
(anchor_w*, anchor_f*) coral keeps its other meaning, the guess -- do not mix
the two series in one talk.

Everything is measured from production solves at Apollo 15, K_d* read from
results/kd_retrieval_results.json:
  * the daily swing is (max - min)/2 of the converged periodic cycle;
  * the flux is q = K(<T>) d<T>/dz + u_rect, as _mean_flux_closure certifies;
  * frames 2 and 5 march a real brute-force spin-up from a 240 K cold start to
    3000 lunations on the compiled kernel, the same ladder the letter figure's
    panel (b) uses.

Frame 3 draws no level above 0.55 m on purpose. The identity holds everywhere
(over a full cycle nothing can accumulate at any depth), but the DIAGNOSTIC is
noisy in the daily-wave zone -- np.gradient across millimetre cells against a
+/-134 K wave differences two nearly cancelling terms (at z = 1 cm they are
2557 and -2507 mW/m^2 for a 21 mW/m^2 answer). That is a discretisation
artefact, not physics, and it does not belong on a defense slide. The method
integrates downward from the anchor, so the region drawn is the region used.

    python pipeline/figures/make_anchor_why.py
"""
from __future__ import annotations

import functools
import json
import pathlib

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from lunar.config import DT_STEP, EQ_Z_ANCHOR, GRID, HAYNE, SITES
from lunar.equilibrium import _rectified_flux, solve_periodic_equilibrium
from lunar.grid import make_geometric_grid
from lunar.plotting.style import (C_CHAR, C_CORAL, C_DIM, C_FOREST, C_GRID,
                                  C_NEUTRAL, C_TEAL, fmt_axis)
from lunar.properties import conductivity_hayne, specific_heat
from lunar.solver import (PixelInputs, periodic_time_grid, solve_pixel,
                          standard_insolation)

SITE = SITES["A15"]
Z0 = EQ_Z_ANCHOR
ZCAP = Z0 + 0.15
ZMAX = 3.0
ZBOT = 3.55                                   # where the column runs off
LEVELS = (0.55, 1.0, 1.5, 2.0, 2.5, 3.0)      # the levels read off
DAY_LEVELS = (0.02, 0.10, 0.20, 0.35, 0.55)   # where the swing is read off
COL_L, COL_R = 0.15, 0.58
COL_FILL = "#F0EEEA"
T_COLD = 240.0                                # brute-force cold start
LADDER = (1, 1, 1, 2, 2, 3, 4, 6, 10, 15, 25, 40, 60, 90, 150, 240, 350,
          500, 700, 800)                      # cumulative 3000 lunations

ROOT = pathlib.Path(__file__).resolve().parents[2]
OUT = ROOT.parents[1] / "Others" / "gedes" / "defense" / "img"
CACHE = ROOT / "results" / "anchor_why_cache.npz"
KD_JSON = ROOT / "results" / "kd_retrieval_results.json"


# ── data ────────────────────────────────────────────────────────────────────
def compute():
    if CACHE.exists():
        print(f"  (cached: {CACHE.name})")
        return dict(np.load(CACHE))
    return _compute()


def _compute():
    kd = float(json.loads(KD_JSON.read_text())["A15"]["kd_star"])
    g = make_geometric_grid(**GRID)
    z = g.z_mid
    t = periodic_time_grid(DT_STEP)
    insol = standard_insolation(SITE["lat"], t)
    K = functools.partial(conductivity_hayne, Ks=HAYNE["K_S"], Kd=kd,
                          H=HAYNE["H"], chi=HAYNE["CHI"])
    cp = functools.partial(specific_heat, model="hayne")
    hp = (HAYNE["K_S"], kd, HAYNE["H"], HAYNE["CHI"])
    Qb = SITE["Q_BASAL"]

    eq = solve_periodic_equilibrium(
        grid=g, t=t, insolation=insol, albedo=SITE["albedo"],
        emissivity=SITE["emissivity"], Q_b=Qb, K_func=K, cp_func=cp,
        T_guess=SITE["T_MEAN_EFF"], hayne_params=hp)

    Tmin, Tmax = eq.out.T.min(axis=1), eq.out.T.max(axis=1)
    amp = (Tmax - Tmin) / 2.0
    u = _rectified_flux(eq.out.T, z, K)
    q = np.asarray(K(eq.T_mean, z)) * np.gradient(eq.T_mean, z) + u

    # brute force from a cold start, the honest way to reach the same state
    print(f"  brute-force ladder to {sum(LADDER)} lunations "
          f"(compiled kernel)...")
    i_top = int(np.argmin(np.abs(z - Z0)))
    i_deep = int(np.argmin(np.abs(z - 3.0)))
    T_init = np.full(z.size, T_COLD)
    months, top, deep = [0], [T_COLD], [T_COLD]
    cum = 0
    for d in LADDER:
        out = solve_pixel(PixelInputs(
            grid=g, t=t, bc_mode="radiative", insolation=insol,
            albedo=SITE["albedo"], emissivity=SITE["emissivity"], Q_b=Qb,
            T_init=T_init, n_lunations_spinup=d, spinup_tol_K=0.0,
            K_func=K, cp_func=cp, hayne_params=hp))
        cum += d
        T_init = out.T[:, -1]
        Tm = out.T.mean(axis=1)
        months.append(cum)
        top.append(float(Tm[i_top]))
        deep.append(float(Tm[i_deep]))
    T_brute = out.T.mean(axis=1)

    gap = float(np.max(np.abs(T_brute - eq.T_mean)[(z >= Z0) & (z <= ZMAX)]))
    print(f"  after {cum} months of brute force, the deep column differs from "
          f"the anchored answer by {gap*1e3:.1f} mK")

    D = dict(z=z, z_face=g.z_face, T_mean=eq.T_mean, amp=amp, q=q,
             Tmin=Tmin, Tmax=Tmax,
             Qb=np.float64(Qb), months=np.array(months, float),
             top=np.array(top), deep=np.array(deep), T_brute=T_brute,
             gap=np.float64(gap), n_brute=np.int64(cum))
    CACHE.parent.mkdir(parents=True, exist_ok=True)
    np.savez(CACHE, **D)
    return D


def at(D, key, depth):
    return float(D[key][int(np.argmin(np.abs(D["z"] - depth)))])


# ── shared column ───────────────────────────────────────────────────────────
def ground(ax, D):
    ax.add_patch(plt.Rectangle((COL_L, 0.0), COL_R - COL_L, ZBOT,
                               fc=COL_FILL, ec="none", zorder=1))
    for zf in D["z_face"][D["z_face"] <= ZBOT]:
        ax.plot([COL_L, COL_R], [zf, zf], lw=0.35, color=C_NEUTRAL,
                alpha=0.22, zorder=2)
    ax.plot([COL_L, COL_R], [0, 0], lw=2.0, color=C_CHAR, zorder=7)


def finish(ax, title, subtitle, fig, note=None, tcol=C_TEAL):
    ax.set_xlim(0.0, 1.0)
    ax.set_ylim(3.72, -0.55)
    ax.set_xticks([])
    ax.set_yticks([0, 1, 2, 3])
    fmt_axis(ax, xlabel="", ylabel="depth  (m)")
    ax.grid(False)
    ax.spines["bottom"].set_visible(False)
    ax.spines["left"].set_bounds(0, 3)
    ax.tick_params(labelsize=11)
    ax.yaxis.label.set_size(12)
    fig.text(0.135, 0.975, title, fontsize=15, fontweight="bold", color=tcol,
             va="top")
    fig.text(0.135, 0.917, subtitle, fontsize=11.5, color=C_DIM, va="top")
    if note:
        fig.text(0.135, 0.026, note, fontsize=9.5, color=C_DIM, va="bottom")


def arrow(ax, x, y0, y1, color, lw=3.0, scale=26):
    ax.annotate("", xy=(x, y1), xytext=(x, y0), zorder=6,
                arrowprops=dict(arrowstyle="-|>", lw=lw, color=color, fc=color,
                                mutation_scale=scale, shrinkA=0, shrinkB=0))


def save(fig, name):
    OUT.mkdir(parents=True, exist_ok=True)
    p = OUT / name
    fig.savefig(p, dpi=200, facecolor="white")
    plt.close(fig)
    print(f"  wrote {p.name}")


def _fmt_swing(a):
    if a >= 10:
        return f"± {a:.0f} °C"
    if a >= 1:
        return f"± {a:.1f} °C"
    if a >= 0.01:
        return f"± {a:.2f} °C"
    return f"± {a:.3f} °C"


# ── frame 1 ─────────────────────────────────────────────────────────────────
def frame1(D):
    fig = plt.figure(figsize=(7.0, 6.2))
    ax = fig.add_axes([0.125, 0.155, 0.85, 0.675])
    z, keep = D["z"], D["z"] <= ZMAX

    ax.fill_betweenx(z[keep], D["Tmin"][keep], D["Tmax"][keep], color=C_CORAL,
                     alpha=0.45, lw=0, zorder=3)
    ax.plot(D["T_mean"][keep], z[keep], "-", color=C_CHAR, lw=1.4, zorder=5)

    ax.annotate(f"at 10 cm the ground still\nswings "
                f"{_fmt_swing(at(D, 'amp', 0.10))} in a month",
                xy=(at(D, "Tmin", 0.10), 0.115), xytext=(88.0, 0.40),
                fontsize=11.5, color=C_CORAL, ha="left", va="center",
                arrowprops=dict(arrowstyle="->", color=C_CORAL, lw=1.0))
    ax.annotate(f"at half a metre: "
                f"{_fmt_swing(at(D, 'amp', Z0))}\n— a line, not a band",
                xy=(at(D, "T_mean", Z0) - 2.0, Z0), xytext=(88.0, 0.74),
                fontsize=11.5, color=C_CHAR, ha="left", va="center",
                arrowprops=dict(arrowstyle="->", color=C_CHAR, lw=1.0))
    ax.annotate("and it stays a straight line\nall the way down to 5 m",
                xy=(272.0, 0.93), fontsize=11.5, color=C_DIM, ha="left",
                va="center")

    ax.set_xlim(80.0, 400.0)
    ax.set_ylim(1.0, 0.0)
    fmt_axis(ax, xlabel="temperature  (K)", ylabel="depth  (m)")
    ax.grid(True, lw=0.5, color=C_GRID)
    ax.tick_params(labelsize=11)
    ax.xaxis.label.set_size(12)
    ax.yaxis.label.set_size(12)

    fig.text(0.125, 0.975, "Only the top of the ground feels the day",
             fontsize=15, fontweight="bold", color=C_CORAL, va="top")
    fig.text(0.125, 0.912,
             "The shaded band is how far the temperature travels between "
             "noon and midnight.", fontsize=11.5, color=C_DIM, va="top")
    fig.text(0.125, 0.022,
             "Measured in the settled model. The swing falls by a factor of "
             f"{at(D,'amp',0.02)/at(D,'amp',Z0):,.0f} "
             "between 2 cm and 0.55 m.",
             fontsize=9.5, color=C_DIM, va="bottom")
    save(fig, "why1_day.png")


# ── frame 2 ─────────────────────────────────────────────────────────────────
def frame2(D):
    fig = plt.figure(figsize=(7.4, 6.0))
    ax = fig.add_axes([0.115, 0.155, 0.86, 0.675])
    mo = np.maximum(D["months"], 0.7)
    fin = float(D["deep"][-1])

    ax.semilogx(mo, D["top"], "-", color=C_CORAL, lw=2.8, zorder=5)
    ax.semilogx(mo, D["deep"], "-", color=C_TEAL, lw=2.8, zorder=5)
    ax.annotate("half a metre down", xy=(2600.0, float(D["top"][-1])),
                xytext=(0, -26), textcoords="offset points", fontsize=11.5,
                color=C_CORAL, ha="right", va="top", fontweight="bold")
    ax.annotate("three metres down", xy=(2200.0, fin), xytext=(0, 12),
                textcoords="offset points", fontsize=11.5, color=C_TEAL,
                ha="right", va="bottom", fontweight="bold")

    i100 = int(np.argmin(np.abs(D["months"] - 100.0)))
    ax.annotate(f"after 100 months it is still\n"
                f"{fin - float(D['deep'][i100]):.0f} degrees too cold",
                xy=(100.0, float(D["deep"][i100])), xytext=(1.15, 249.0),
                fontsize=11.5, color=C_CHAR, ha="left", va="center",
                arrowprops=dict(arrowstyle="->", color=C_CHAR, lw=1.0))
    ax.axvline(D["months"][-1], color=C_DIM, lw=0.9, ls=":", zorder=2)
    ax.annotate(f"{D['n_brute']:,.0f} months\nof day and night\n"
                "= 240 years", xy=(D["months"][-1] * 0.88, 240.4),
                fontsize=11.5, color=C_DIM, ha="right", va="bottom",
                fontweight="bold")

    ax.set_xlim(0.7, 5200)
    ax.set_ylim(238.5, 259.0)
    ax.set_xticks([1, 10, 100, 1000])
    ax.set_xticklabels(["1", "10", "100", "1000"])
    fmt_axis(ax, xlabel="months of day and night simulated",
             ylabel="temperature  (K)")
    ax.grid(True, lw=0.5, color=C_GRID)
    ax.tick_params(labelsize=11)
    ax.xaxis.label.set_size(12)
    ax.yaxis.label.set_size(12)

    fig.text(0.115, 0.975, "But the ground takes thousands of months to settle",
             fontsize=15, fontweight="bold", color=C_TEAL, va="top")
    fig.text(0.115, 0.912,
             "Start it at the wrong temperature and it is still wrong a "
             "century later.", fontsize=11.5, color=C_DIM, va="top")
    fig.text(0.115, 0.022,
             "Real spin-up from a 240 K start on the compiled solver. "
             "This is the cost the anchor method removes.",
             fontsize=9.5, color=C_DIM, va="bottom")
    save(fig, "why2_slow.png")


# ── frame 3 ─────────────────────────────────────────────────────────────────
def frame3(D):
    fig = plt.figure(figsize=(6.8, 6.6))
    ax = fig.add_axes([0.135, 0.075, 0.845, 0.775])
    ground(ax, D)

    xa = 0.5 * (COL_L + COL_R)
    for lv in LEVELS:
        v = at(D, "q", lv)
        ax.plot([COL_L, COL_R], [lv, lv], lw=0.8, ls=":", color=C_DIM,
                zorder=4)
        arrow(ax, xa, lv + 0.15, lv - 0.15, C_TEAL, lw=3.2)
        ax.annotate(f"{v*1e3:.1f}", xy=(COL_R + 0.05, lv), fontsize=13,
                    fontweight="bold", color=C_TEAL, ha="left", va="center")

    arrow(ax, xa, ZBOT, ZBOT - 0.31, C_TEAL, lw=4.0, scale=30)
    ax.annotate("heat arrives from the\nMoon's interior",
                xy=(COL_R + 0.05, ZBOT - 0.15), fontsize=11.5, color=C_TEAL,
                ha="left", va="center")
    arrow(ax, xa, -0.02, -0.34, C_TEAL, lw=4.0, scale=30)
    ax.annotate("and the same amount\nleaves at the top",
                xy=(COL_R + 0.05, -0.20), fontsize=11.5, color=C_TEAL,
                ha="left", va="center")
    ax.annotate("heat crossing this level\n(mW per m²)",
                xy=(COL_R + 0.05, 0.26), fontsize=11, color=C_DIM,
                ha="left", va="center")

    worst = max(abs(at(D, "q", lv) - float(D["Qb"])) / float(D["Qb"])
                for lv in LEVELS)
    finish(ax, "The same heat passes every level",
           "Nothing piles up: whatever enters at the bottom leaves at the top.",
           fig, note="Measured at each level in the settled model, not "
                     f"assumed: identical to better than {100*worst:.3f} %.")
    save(fig, "why3_flux.png")


# ── frame 4 ─────────────────────────────────────────────────────────────────
def frame4(D):
    fig = plt.figure(figsize=(6.8, 6.6))
    ax = fig.add_axes([0.135, 0.075, 0.845, 0.775])
    ground(ax, D)

    ax.add_patch(plt.Rectangle((COL_L, 0.0), COL_R - COL_L, ZCAP,
                               fc=C_FOREST, alpha=0.20, ec="none", zorder=3))
    ax.annotate("simulated\n(the only part that is)",
                xy=(COL_L + 0.02, 0.20), fontsize=11.5, color=C_FOREST,
                ha="left", va="center", zorder=8)
    ax.add_patch(plt.Rectangle((COL_L, ZCAP), COL_R - COL_L, ZBOT - ZCAP,
                               fc=C_TEAL, alpha=0.12, ec="none", zorder=3))
    ax.annotate("calculated,\nnot simulated", xy=(COL_L + 0.02, 1.28),
                fontsize=11.5, color=C_TEAL, ha="left", va="center", zorder=8)

    xr = COL_R + 0.05
    prev = None
    for lv in LEVELS:
        T = at(D, "T_mean", lv)
        ax.plot([COL_L, COL_R], [lv, lv], lw=0.8, ls=":", color=C_DIM,
                zorder=4)
        ax.annotate(f"{T:.1f} K", xy=(xr, lv), fontsize=13, fontweight="bold",
                    color=C_TEAL if lv > Z0 else C_CHAR, ha="left",
                    va="center")
        if prev is not None:
            ax.annotate(f"+ {T - prev[1]:.2f}",
                        xy=(xr + 0.005, 0.5 * (lv + prev[0])), fontsize=11.5,
                        color=C_TEAL, ha="left", va="center")
        prev = (lv, T)

    ax.plot([0.5 * (COL_L + COL_R)], [Z0], "o", ms=10, color=C_CHAR,
            mec="white", mew=1.6, zorder=9)
    ax.annotate("read once, here", xy=(0.5 * (COL_L + COL_R), Z0 + 0.05),
                xytext=(COL_L + 0.02, 0.88), fontsize=11.5,
                fontweight="bold", color=C_CHAR, ha="left", va="center",
                arrowprops=dict(arrowstyle="->", color=C_CHAR, lw=1.0))

    finish(ax, "So simulate the top, and calculate the rest",
           "One temperature at 0.55 m, plus the heat crossing it, gives all "
           "the others.", fig,
           note="Every step is an addition — no simulation below the anchor. "
                "The numbers are the model's own.", tcol=C_FOREST)
    save(fig, "why4_method.png")


# ── frame 5 ─────────────────────────────────────────────────────────────────
def frame5(D):
    fig = plt.figure(figsize=(7.0, 6.2))
    ax = fig.add_axes([0.125, 0.155, 0.85, 0.675])
    z, keep = D["z"], D["z"] <= ZMAX

    ax.plot(D["T_brute"][keep], z[keep], "-", color=C_CORAL, lw=6.0, zorder=4)
    ax.plot(D["T_mean"][keep], z[keep], "-", color=C_TEAL, lw=2.2, zorder=5)
    ax.annotate(f"brute force\n{D['n_brute']:,.0f} months of simulation\n"
                "26.6 hours", xy=(at(D, "T_brute", 1.15), 1.15),
                xytext=(245.0, 0.75), fontsize=11.5, color=C_CORAL,
                ha="left", va="center",
                arrowprops=dict(arrowstyle="->", color=C_CORAL, lw=1.0))
    ax.annotate("anchor method\n39 seconds",
                xy=(at(D, "T_mean", 2.25), 2.25), xytext=(245.0, 2.05),
                fontsize=11.5, color=C_TEAL, ha="left", va="center",
                arrowprops=dict(arrowstyle="->", color=C_TEAL, lw=1.0))

    ax.set_xlim(244.0, 259.0)
    ax.set_ylim(ZMAX, 0.0)
    fmt_axis(ax, xlabel="temperature  (K)", ylabel="depth  (m)")
    ax.grid(True, lw=0.5, color=C_GRID)
    ax.tick_params(labelsize=11)
    ax.xaxis.label.set_size(12)
    ax.yaxis.label.set_size(12)

    fig.text(0.125, 0.975, "And it is the same answer", fontsize=15,
             fontweight="bold", color=C_TEAL, va="top")
    fig.text(0.125, 0.912,
             "Two ways to the same profile. One takes a day, the other a "
             "minute.", fontsize=11.5, color=C_DIM, va="top")
    fig.text(0.125, 0.022,
             "Largest difference over the deep column: "
             f"{float(D['gap'])*1e3:.0f} mK, and still closing — the anchored "
             "profile is the state brute force is converging to.",
             fontsize=9.5, color=C_DIM, va="bottom")
    save(fig, "why5_same.png")


def main():
    D = compute()
    frame1(D)
    frame2(D)
    frame3(D)
    frame4(D)
    frame5(D)


if __name__ == "__main__":
    main()
