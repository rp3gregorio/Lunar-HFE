#!/usr/bin/env python3
"""Explainer figures for the thesis (three, all from real pipeline data).

1. fig_window_anatomy.pdf  -- the stability-window rule operating on two
     real Apollo 15 sensors: TG12B (139 cm) accepts at the first
     candidate (trend_flat, +0.065 K/yr), TR12A (101 cm) rejects all 13
     candidates and takes the final-quarter fallback (+0.22 K/yr).
2. fig_epoch_map.pdf       -- the Apollo 17 retained sensors' stability
     windows on a shared day axis: the depth-aligned mid-1977 vs 1974
     epoch split behind the common-epoch systematic.
3. fig_urect_explainer.pdf -- what the rectified flux is: correlated
     K(t) and gradient oscillations (a), the mean-of-product vs
     product-of-means gap (b), and the u_rect(z)/Q_b decay profile (c).

Sensors, windows, and slopes come from lunar.apollo_helpers; the
rectified-flux panels come from one converged A17 equilibrium solve at
the certified K_d* = 7.08 mW/m/K. Nothing is hand-entered.

Run: python code/pipeline/figures/make_explainer_figures.py
"""
from __future__ import annotations
import datetime
import pathlib
import sys

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

_REPO = pathlib.Path(__file__).resolve().parents[1].parent
sys.path.insert(0, str(_REPO / "src"))

from lunar.apollo_helpers import extract_sensor_stability, iso_to_seconds
from lunar.config import (SITES, GRID, HAYNE, S0, T_LUNAR, DT_STEP,
                          EQ_Z_ANCHOR, EQ_N_INNER, EQ_MAX_OUTER,
                          EQ_ANCHOR_TOL)
from lunar.grid import make_geometric_grid
from lunar.properties import conductivity_hayne, specific_heat
from lunar.solver import periodic_time_grid
from lunar.equilibrium import solve_periodic_equilibrium, _rectified_flux
from lunar.plotting.style import (JGR_HALF, JGR_FULL, C_A15, C_A17, C_TEAL,
                                  C_CORAL, C_FOREST, C_CHAR, C_DIM, C_GRID,
                                  C_CORAL_L, fmt_axis, assert_no_overlap)

OUT = _REPO / ".." / "figures"

THRESH = 0.08          # K/yr, the acceptance threshold of the window rule
CAND_FRACS = np.linspace(0.55, 0.80, 13)


def _ols_slope(t_day, T, i0):
    """OLS slope in K/yr over the tail starting at index i0."""
    t_yr = (t_day[i0:] - t_day[i0]) / 365.25
    return np.polyfit(t_yr, T[i0:], 1)


def fig_window_anatomy():
    r = extract_sensor_stability("a15", 80)
    pd = r["probe_data"][1]

    fig, (axA, axB) = plt.subplots(2, 1, figsize=(JGR_HALF, 4.3),
                                   sharex=True, constrained_layout=True)
    for ax, name, title in ((axA, "TG12B", "(a)  TG12B, 139 cm: accepted"),
                            (axB, "TR12A", "(b)  TR12A, 101 cm: fallback")):
        s = pd[name]
        t, T, i0 = s["t_day"], s["T"], s["i_start"]
        n = len(T)
        dec = slice(None, None, 8)          # visual decimation only
        ax.plot(t[dec], T[dec], color=C_DIM, lw=0.7, alpha=0.8, zorder=2)
        # the 13 candidate start points
        cand_i = (CAND_FRACS * n).astype(int)
        ax.plot(t[cand_i], T[cand_i], "|", color=C_CHAR, ms=9, mew=1.2,
                zorder=4)
        if name == "TG12B":
            # accepted at the first candidate: shade + fitted trend
            ax.axvspan(t[i0], t[-1], color=C_FOREST, alpha=0.14, lw=0)
            m, b = _ols_slope(t, T, i0)
            ty = (t[i0:] - t[i0]) / 365.25
            ax.plot(t[i0:], m * ty + b, color=C_FOREST, lw=1.8, zorder=5)
            ax.annotate(f"first candidate already flat:\n"
                        f"$+{m:.3f}$ K yr$^{{-1}} < {THRESH}$, accepted",
                        xy=(t[i0] + 30, 254.45), fontsize=7.2,
                        color=C_FOREST, ha="left", va="top",
                        linespacing=1.35)
        else:
            # every candidate rejected: show first-candidate trend + fallback
            m1, b1 = _ols_slope(t, T, cand_i[0])
            ty1 = (t[cand_i[0]:] - t[cand_i[0]]) / 365.25
            ax.plot(t[cand_i[0]:], m1 * ty1 + b1, color=C_CORAL, lw=1.6,
                    ls="--", zorder=5)
            ax.axvspan(t[i0], t[-1], color=C_CORAL, alpha=0.14, lw=0)
            m2, b2 = _ols_slope(t, T, i0)
            ty2 = (t[i0:] - t[i0]) / 365.25
            ax.plot(t[i0:], m2 * ty2 + b2, color=C_CORAL, lw=1.8, zorder=5)
            ax.annotate(f"all 13 candidates trend $> {THRESH}$ K yr$^{{-1}}$\n"
                        f"(first: $+{m1:.2f}$); fallback = final quarter,\n"
                        f"residual $+{m2:.2f}$ K yr$^{{-1}}$",
                        xy=(60, 254.75), fontsize=7.2, color=C_CORAL,
                        ha="left", va="top", linespacing=1.35)
            print(f"  TR12A candidate-1 slope {m1:+.3f}, fallback {m2:+.3f}")
        fmt_axis(ax, ylabel="$T$  (K)", title=title,
                 xlabel="days since first archived sample"
                 if name == "TR12A" else None)
        ax.set_xlim(-30, 1470)
    axA.set_ylim(252.8, 254.8)
    axB.set_ylim(252.4, 255.2)
    fig.canvas.draw()
    assert_no_overlap(axA)
    assert_no_overlap(axB)
    fig.savefig(OUT / "fig_window_anatomy.pdf")
    plt.close(fig)
    print("  -> fig_window_anatomy.pdf")


def fig_epoch_map():
    r = extract_sensor_stability("a17", 80)
    # calendar year marks from the real first timestamp
    t0 = iso_to_seconds(r["d1"]["time_iso"][:1])[0]
    d0 = datetime.datetime.fromtimestamp(t0, tz=datetime.timezone.utc)
    year_marks = []
    for yr in range(d0.year + 1, 1979):
        dt = datetime.datetime(yr, 1, 1, tzinfo=datetime.timezone.utc)
        day = (dt.timestamp() - t0) / 86400.0
        year_marks.append((day, yr))

    fig, ax = plt.subplots(figsize=(JGR_HALF, 3.1), constrained_layout=True)
    for s in r["sensors"]:
        if s["depth_cm"] < 80:
            continue
        pdrec = r["probe_data"][s["probe"]][s["sensor"]]
        t, i0 = pdrec["t_day"], pdrec["i_start"]
        color = C_CHAR if s["stype"] == "TG" else C_DIM
        ax.plot([t[i0], t[-1]], [s["depth_cm"]] * 2, color=color, lw=3.2,
                solid_capstyle="round", alpha=0.9, zorder=3)
    for day, yr in year_marks:
        ax.axvline(day, color=C_GRID, lw=0.7, zorder=1)
        ax.text(day, 118, str(yr), ha="center", fontsize=6.8, color=C_DIM)
    ax.invert_yaxis()
    ax.set_xlim(-40, 1780)
    ax.set_ylim(245, 112)
    ax.annotate("shallow TG pairs:\nwindows run to mid-1977",
                xy=(1450, 152), fontsize=7.2, color=C_CHAR, ha="center",
                linespacing=1.35)
    ax.annotate("TR pairs and everything deeper:\nrecords end in 1974",
                xy=(1330, 220), fontsize=7.2, color=C_DIM, ha="center",
                linespacing=1.35)
    fmt_axis(ax, xlabel="days since first archived sample",
             ylabel="sensor depth  (cm)",
             title="Apollo 17 stability windows by depth")
    fig.canvas.draw()
    assert_no_overlap(ax)
    fig.savefig(OUT / "fig_epoch_map.pdf")
    plt.close(fig)
    print("  -> fig_epoch_map.pdf")


def fig_urect_explainer():
    site = SITES["A17"]
    kd = 7.08e-3                               # certified headline K_d*
    g = make_geometric_grid(**GRID)
    z = g.z_mid
    t = periodic_time_grid(DT_STEP)
    insol = S0 * np.cos(np.deg2rad(site["lat"])) * np.maximum(
        0.0, np.cos(2 * np.pi * t / T_LUNAR))
    kf = lambda T, zz: conductivity_hayne(T, zz, Ks=HAYNE["K_S"], Kd=kd,
                                          H=HAYNE["H"], chi=HAYNE["CHI"])
    cf = lambda T: specific_heat(T, model="hayne")
    eq = solve_periodic_equilibrium(
        grid=g, t=t, insolation=insol, albedo=site["albedo"],
        emissivity=site["emissivity"], Q_b=site["Q_BASAL"], K_func=kf,
        cp_func=cf, T_guess=site["T_MEAN_EFF"], z_anchor=EQ_Z_ANCHOR,
        n_inner=EQ_N_INNER, max_outer=EQ_MAX_OUTER,
        anchor_tol_K=EQ_ANCHOR_TOL)
    Tc = eq.out.T                              # (N_z, N_t) periodic cycle
    Qb = site["Q_BASAL"]
    iz = int(np.argmin(np.abs(z - 0.15)))
    n_t = Tc.shape[1]
    tt = np.linspace(0.0, T_LUNAR / 86400.0, n_t)

    K_t = kf(Tc[iz], z[iz]) * 1e3              # mW/m/K at the chosen depth
    dTdz_t = np.gradient(Tc, z, axis=0)[iz]    # K/m at the chosen depth
    total = float(np.mean(kf(Tc[iz], z[iz]) * dTdz_t)) * 1e3
    Tm = Tc.mean(axis=1)
    meanfield = float(kf(Tm[iz], z[iz]) * np.gradient(Tm, z)[iz]) * 1e3
    u = _rectified_flux(Tc, z, kf)
    zc = z[iz] * 100
    print(f"  at {zc:.0f} cm: total {total:.1f}, mean-field {meanfield:.1f}, "
          f"u_rect {total - meanfield:.1f} mW/m2 "
          f"({(total - meanfield) / (Qb * 1e3) * 100:.0f}% of Q_b)")

    fig, (axA, axB, axC) = plt.subplots(1, 3, figsize=(JGR_FULL, 2.85),
                                        constrained_layout=True)
    # (a) the two oscillating factors, axes color-coded (no legend needed)
    axA.plot(tt, K_t, color=C_TEAL, lw=1.8)
    axA2 = axA.twinx()
    axA2.plot(tt, dTdz_t, color=C_CORAL, lw=1.8)
    axA2.set_ylabel(r"$\partial_z T$  (K m$^{-1}$)", fontsize=9,
                    color=C_CORAL)
    axA2.tick_params(axis="y", labelsize=7.5, colors=C_CORAL)
    axA2.spines["right"].set_visible(True)
    axA2.spines["right"].set_color(C_CORAL)
    fmt_axis(axA, xlabel="time over one lunation  (days)",
             ylabel="$K$  (mW m$^{-1}$ K$^{-1}$)",
             title=f"(a)  correlated factors at {zc:.0f} cm")
    axA.yaxis.label.set_color(C_TEAL)
    axA.tick_params(axis="y", colors=C_TEAL, labelsize=7.5)

    # (b) the covariance cancels most of the mean-field flux
    bars = [meanfield, total]
    labels = [r"$K(\langle T\rangle)\,\partial_z\langle T\rangle$",
              r"$\langle K\,\partial_z T\rangle$"]
    colors = [C_CORAL, C_TEAL]
    for i, (v, c) in enumerate(zip(bars, colors)):
        axB.bar(i, v, width=0.55, color=c, alpha=0.85, zorder=3)
        y_lab = max(v, Qb * 1e3) + max(bars) * 0.03
        axB.text(i, y_lab, f"{v:.0f}", ha="center",
                 fontsize=7.6, color=C_CHAR)
    axB.axhline(Qb * 1e3, color=C_DIM, ls="--", lw=1.1, zorder=2)
    axB.text(-0.52, Qb * 1e3 + max(bars) * 0.03, "$Q_b$", ha="left",
             fontsize=7.4, color=C_DIM)
    axB.annotate("", xy=(1.42, total), xytext=(1.42, meanfield),
                 arrowprops=dict(arrowstyle="<->", color=C_CHAR, lw=1.2))
    axB.text(1.52, (total + meanfield) / 2, r"$u_{\rm rect}$",
             fontsize=8.2, color=C_CHAR, va="center")
    axB.set_xticks([0, 1], labels, fontsize=7.4)
    axB.set_xlim(-0.6, 2.05)
    axB.set_ylim(0, max(bars) * 1.22)
    fmt_axis(axB, ylabel="cycle-mean flux  (mW m$^{-2}$)",
             title="(b)  the covariance correction")

    # (c) the decay profile
    sel = z <= 1.2
    axC.semilogx(np.abs(u[sel]) / Qb * 100.0, z[sel], color=C_TEAL, lw=2.0,
                 zorder=3)
    axC.axvline(1.0, color=C_DIM, ls="--", lw=1.1, zorder=2)
    i0 = int(np.argmin(np.abs(z - EQ_Z_ANCHOR)))
    axC.plot([abs(u[i0]) / Qb * 100.0], [EQ_Z_ANCHOR], "o", color=C_CHAR,
             ms=6, zorder=4)
    axC.text(1.25, 0.06, "1%", fontsize=7.4, color=C_DIM)
    axC.annotate("anchor", xy=(abs(u[i0]) / Qb * 100.0, EQ_Z_ANCHOR),
                 xytext=(8.0, 0.66), fontsize=7.2, color=C_CHAR,
                 va="center",
                 arrowprops=dict(arrowstyle="-", lw=0.8, color=C_DIM))
    axC.invert_yaxis()
    axC.set_xlim(3e-3, 400)
    fmt_axis(axC, xlabel=r"$|u_{\rm rect}|\,/\,Q_b$  (%)",
             ylabel="depth  (m)", title="(c)  decay with depth")

    fig.canvas.draw()
    assert_no_overlap(axA)
    assert_no_overlap(axC)
    fig.savefig(OUT / "fig_urect_explainer.pdf")
    plt.close(fig)
    print("  -> fig_urect_explainer.pdf")


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    fig_window_anatomy()
    fig_epoch_map()
    fig_urect_explainer()


if __name__ == "__main__":
    main()
