#!/usr/bin/env python3
"""Teaching figures for the beginner's primer (paper/primer/primer.tex).

Produces three conceptual figures that do not appear in the letter:

  fig_primer_heatflow.pdf  -- schematic: how heat enters and leaves the
                              regolith column, the diurnal skin, the
                              steady deep zone, and the sensors.
  fig_primer_retrieval.pdf -- how a conductivity number is extracted:
                              a flowchart plus the real RMSE-vs-K_d bowl.
  fig_primer_anchorfix.pdf -- the bug and the fix, computed from the
                              real solver: old short spin-up depends on
                              the starting guess; the equilibrium solver
                              does not.

Run with:
    python scripts/figures/make_primer_figures.py
"""
from __future__ import annotations
import json, sys, pathlib

_REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO))
sys.path.insert(0, str(_REPO / "scripts" / "figures"))
sys.path.insert(0, str(_REPO / "scripts" / "pipeline"))

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

from make_results_figures import (   # type: ignore
    C_A15, C_A17, C_HAYNE, C_MS, C_CHAR, C_DIM, C_GRID, C_CORAL, C_TEAL,
    FS_TICK, FS_LABEL, FS_LEGEND, fmt_axis,
)

OUT = _REPO / "paper" / "primer" / "figures"
OUT.mkdir(parents=True, exist_ok=True)

C_SUN = "#E8A33D"
C_SKIN = "#F4D6CB"
C_DEEP = "#D8E5E3"


# ══════════════════════════════════════════════════════════════════════════
# Figure P1 -- heat-flow schematic
# ══════════════════════════════════════════════════════════════════════════
def fig_heatflow():
    fig, (axL, axR) = plt.subplots(
        1, 2, figsize=(9.2, 5.4), gridspec_kw={"width_ratios": [1.5, 1.0],
                                               "wspace": 0.32})

    # ---- left: the column -------------------------------------------------
    ax = axL
    ax.set_xlim(0, 10)
    ax.set_ylim(250, -45)          # depth downward; headroom for the Sun
    col_l, col_r = 3.2, 7.2

    # regolith column zones
    ax.add_patch(plt.Rectangle((col_l, 0), col_r - col_l, 50,
                               facecolor=C_SKIN, edgecolor="none", zorder=1))
    ax.add_patch(plt.Rectangle((col_l, 50), col_r - col_l, 200,
                               facecolor=C_DEEP, edgecolor="none", zorder=1))
    ax.add_patch(plt.Rectangle((col_l, 0), col_r - col_l, 250,
                               fill=False, edgecolor=C_CHAR, lw=1.3, zorder=4))

    # Sun + day/night heating arrows
    ax.scatter([1.5], [-30], s=520, marker="o", color=C_SUN, zorder=3)
    ax.text(1.5, -30, "Sun", ha="center", va="center", fontsize=FS_TICK,
            color="white", fontweight="bold", zorder=4)
    for x in np.linspace(col_l + 0.5, col_r - 0.5, 4):
        ax.add_patch(FancyArrowPatch((x, -18), (x, -2),
                     arrowstyle="-|>", mutation_scale=12,
                     color=C_SUN, lw=1.6, zorder=3))
    ax.text((col_l + col_r) / 2, -40,
            "sunlight heats the surface\n(day) / it cools by glowing (night)",
            ha="center", va="center", fontsize=FS_TICK - 1, color=C_CHAR)

    # zone labels
    ax.text((col_l + col_r) / 2, 25,
            "diurnal skin\ntemperature swings\nday$\\leftrightarrow$night",
            ha="center", va="center", fontsize=FS_TICK - 0.5, color=C_CORAL,
            fontweight="bold", zorder=5)
    ax.text(col_l + 1.15, 135,
            "meter-scale\nregolith\nsteady $T$,\nset by\n$K_d$ and $Q_b$",
            ha="center", va="center", fontsize=FS_TICK - 0.5, color=C_TEAL,
            fontweight="bold", zorder=5)

    # borestem boundary
    ax.plot([col_l, col_r], [80, 80], ls=(0, (4, 2)), color=C_CHAR,
            lw=1.0, zorder=5)

    # sensors (A15 deep depths, illustrative)
    for z in (84, 91, 101, 129, 139):
        ax.scatter([col_r - 0.7], [z], s=34, marker="s", color=C_A15,
                   edgecolor="white", lw=0.6, zorder=6)
    ax.annotate("buried\nthermometers", xy=(col_r - 0.7, 110),
                xytext=(col_r + 1.4, 150), ha="center", va="center",
                fontsize=FS_TICK - 1.5, color=C_A15,
                arrowprops=dict(arrowstyle="-", color=C_A15, lw=0.8))

    # heat from below
    for x in np.linspace(col_l + 0.5, col_r - 0.5, 4):
        ax.add_patch(FancyArrowPatch((x, 248), (x, 224),
                     arrowstyle="-|>", mutation_scale=12,
                     color=C_CORAL, lw=1.8, zorder=3))
    ax.text((col_l + col_r) / 2, 214,
            "heat flux $Q_b$ from the\nMoon's hot interior",
            ha="center", va="center", fontsize=FS_TICK - 1, color=C_CORAL)

    ax.set_yticks([0, 50, 80, 100, 150, 200, 250])
    ax.set_ylabel("Depth below surface (cm)", fontsize=FS_LABEL)
    ax.set_xticks([])
    ax.set_title("(a)  Heat in, heat out, and what is in between",
                 fontsize=FS_LABEL, loc="left")
    for sp in ("top", "right", "bottom"):
        ax.spines[sp].set_visible(False)

    # ---- right: amplitude dies out with depth ----------------------------
    ax = axR
    z = np.linspace(0, 250, 400)
    delta = 12.0                      # illustrative skin depth (cm)
    amp = np.exp(-z / delta)
    ax.plot(amp, z, color=C_CORAL, lw=2.4)
    ax.fill_betweenx(z, 0, amp, color=C_SKIN, alpha=0.6)
    ax.axhline(80, ls=(0, (4, 2)), color=C_CHAR, lw=1.0)
    ax.text(0.55, 40, "big daily\nswing near\nthe surface", fontsize=FS_TICK - 1,
            color=C_CORAL, ha="center")
    ax.text(0.5, 150, "swing has\ndied away\n($<$ noise)", fontsize=FS_TICK - 1,
            color=C_TEAL, ha="center")
    ax.set_ylim(250, 0)
    ax.set_xlim(0, 1.05)
    ax.set_xlabel("Size of the daily\ntemperature swing", fontsize=FS_LABEL)
    ax.set_ylabel("Depth (cm)", fontsize=FS_LABEL)
    ax.set_title("(b)  Why deep sensors\n      see a steady temperature",
                 fontsize=FS_LABEL, loc="left")
    ax.tick_params(labelsize=FS_TICK)
    ax.grid(True, color=C_GRID, lw=0.4, alpha=0.6)
    ax.set_axisbelow(True)

    fig.savefig(OUT / "fig_primer_heatflow.pdf", bbox_inches="tight")
    plt.close(fig)
    print("  -> fig_primer_heatflow.pdf")


# ══════════════════════════════════════════════════════════════════════════
# Figure P2 -- retrieval flowchart + real RMSE bowl
# ══════════════════════════════════════════════════════════════════════════
def fig_retrieval():
    fig, (axL, axR) = plt.subplots(
        1, 2, figsize=(10.2, 4.6), gridspec_kw={"width_ratios": [1.05, 1.0],
                                                "wspace": 0.22})

    # ---- left: flowchart --------------------------------------------------
    ax = axL
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 10)
    ax.axis("off")
    boxes = [
        (8.7, "1. Apollo sensors: the real\ntemperature at each depth", C_A15),
        (6.7, "2. Simulate the Moon with a\nguessed $K_d$ $\\rightarrow$ predicted $T(z)$", C_TEAL),
        (4.7, "3. Compare prediction with data\n(root-mean-square error, RMSE)", C_CHAR),
        (2.7, "4. Try many values of $K_d$", C_MS),
        (0.7, "5. Best match $=$ retrieved $K_d^{*}$", C_CORAL),
    ]
    for y, txt, col in boxes:
        ax.add_patch(FancyBboxPatch((1.2, y - 0.62), 7.6, 1.24,
                     boxstyle="round,pad=0.1,rounding_size=0.18",
                     facecolor="white", edgecolor=col, lw=1.6))
        ax.text(5.0, y, txt, ha="center", va="center", fontsize=FS_TICK,
                color=C_CHAR)
    for y0, y1 in ((8.7, 6.7), (6.7, 4.7), (4.7, 2.7), (2.7, 0.7)):
        ax.add_patch(FancyArrowPatch((5.0, y0 - 0.66), (5.0, y1 + 0.66),
                     arrowstyle="-|>", mutation_scale=14, color=C_DIM, lw=1.4))
    # feedback arrow 4 -> 2
    ax.add_patch(FancyArrowPatch((1.2, 2.7), (1.2, 6.7),
                 connectionstyle="arc3,rad=-0.55",
                 arrowstyle="-|>", mutation_scale=12, color=C_DIM, lw=1.2,
                 ls=(0, (3, 2))))
    ax.text(0.35, 4.7, "repeat", rotation=90, ha="center", va="center",
            fontsize=FS_TICK - 1.5, color=C_DIM)
    ax.set_title("(a)  How a conductivity number is extracted",
                 fontsize=FS_LABEL, loc="left")

    # ---- right: real RMSE bowl --------------------------------------------
    ax = axR
    d = json.loads((_REPO / "output" / "kd_retrieval_results.json").read_text())
    for name, col in (("A15", C_A15), ("A17", C_A17)):
        kd = np.array(d[name]["kd_grid"]) * 1e3
        rmse = np.array(d[name]["rmse_curve"])
        kd_star = d[name]["kd_star"] * 1e3
        rmse_star = d[name]["rmse_star"]
        ax.plot(kd, rmse, "-", color=col, lw=2.2,
                label=f"{name}:  best $K_d^{{*}} = {kd_star:.1f}$")
        ax.plot(kd_star, rmse_star, "*", color=col, ms=20, mec="white",
                mew=1.3, zorder=5)
    ax.axvline(3.4, color=C_CHAR, ls="--", lw=1.0, alpha=0.6)
    ax.text(3.4, ax.get_ylim()[1] * 0.93, "  one global value\n  (Hayne 2017)",
            fontsize=FS_TICK - 1.5, color=C_CHAR, va="top")
    fmt_axis(ax, xlabel=r"guessed $K_d$  (mW m$^{-1}$ K$^{-1}$)",
             ylabel="mismatch with data, RMSE (K)",
             title="(b)  The best fit is the bottom of the bowl")
    ax.set_xlim(0, 16)
    ax.legend(fontsize=FS_LEGEND, loc="upper right", framealpha=0.95)

    fig.savefig(OUT / "fig_primer_retrieval.pdf", bbox_inches="tight")
    plt.close(fig)
    print("  -> fig_primer_retrieval.pdf")


# ══════════════════════════════════════════════════════════════════════════
# Figure P3 -- the bug and the fix, from the real solver
# ══════════════════════════════════════════════════════════════════════════
def fig_anchorfix():
    import scripts.pipeline.retrieve_kd as pap
    from lunar.equilibrium import solve_periodic_equilibrium
    from lunar.grid import make_geometric_grid
    from lunar.solver import PixelInputs, solve_pixel
    from lunar.properties import conductivity_hayne, specific_heat
    from lunar.apollo_helpers import extract_sensor_stability

    cfg = pap.SITES["A15"]
    kd = 4.58e-3
    grid_ = make_geometric_grid(**pap.GRID)
    z = grid_.z_mid
    N_t = int(pap.T_LUNAR / pap.DT_STEP) + 1
    t = np.linspace(0.0, pap.T_LUNAR, N_t)
    insol = (pap.S0 * np.cos(np.deg2rad(cfg["lat"]))
             * np.maximum(0.0, np.cos(2 * np.pi * t / pap.T_LUNAR)))
    kf = lambda T, zz: conductivity_hayne(T, zz, Ks=pap.HAYNE["K_S"], Kd=kd,
                                          H=pap.HAYNE["H"], chi=pap.HAYNE["CHI"])
    cpf = lambda T: specific_heat(T, model="hayne")

    guesses = [245.0, 250.0, 255.0]
    cols = [C_TEAL, C_CHAR, C_CORAL]

    # observed deep sensors (real data)
    obs = extract_sensor_stability(cfg["mission"], min_depth_cm=80)
    z_obs = np.array(obs["depth_cm_all"])
    T_obs = np.array(obs["T_eq_all"])
    deep = np.array(obs["deep_mask"], dtype=bool)

    old_curves, new_curves = {}, {}
    for g in guesses:
        K0 = kf(np.full_like(z, g), z)
        T_init = g + cfg["Q_BASAL"] * np.cumsum(grid_.dz / K0)
        out = solve_pixel(PixelInputs(
            grid=grid_, t=t, bc_mode="radiative", insolation=insol,
            albedo=cfg["albedo"], emissivity=cfg["emissivity"],
            Q_b=cfg["Q_BASAL"], T_init=T_init,
            n_lunations_spinup=30, spinup_tol_K=0.05,
            K_func=kf, cp_func=cpf))
        old_curves[g] = out.T.mean(axis=1)
        eq = solve_periodic_equilibrium(
            grid=grid_, t=t, insolation=insol, albedo=cfg["albedo"],
            emissivity=cfg["emissivity"], Q_b=cfg["Q_BASAL"],
            K_func=kf, cp_func=cpf, T_guess=g)
        new_curves[g] = eq.T_mean
        print(f"     guess {g:.0f} K done", flush=True)

    fig, (axL, axR) = plt.subplots(1, 2, figsize=(9.6, 5.0),
                                   gridspec_kw={"wspace": 0.26})
    fig.subplots_adjust(bottom=0.24, top=0.88)
    for ax, curves, title in (
            (axL, old_curves, "(a)  Old method (short spin-up):\n      answers fan out with the guess"),
            (axR, new_curves, "(b)  New method (equilibrium):\n      all guesses give one answer")):
        for g, col in zip(guesses, cols):
            ax.plot(curves[g], z * 100, "-", color=col, lw=2.4,
                    label=f"started from {g:.0f} K")
        ax.errorbar(T_obs[deep], z_obs[deep], fmt="o", ms=6, color=C_A15,
                    mec="white", mew=0.8, zorder=5,
                    label="real sensor data")
        ax.axhspan(0, 80, color=C_SKIN, alpha=0.5, zorder=0)
        ax.set_ylim(220, 0)
        ax.set_xlim(246, 260)
        fmt_axis(ax, xlabel="predicted temperature (K)",
                 ylabel="Depth (cm)" if ax is axL else "", title=title)

    h, l = axL.get_legend_handles_labels()
    fig.legend(h, l, loc="lower center", bbox_to_anchor=(0.5, 0.0), ncols=4,
               frameon=True, edgecolor=C_GRID, framealpha=0.97,
               fontsize=FS_LEGEND - 0.5, handlelength=1.8)

    fig.savefig(OUT / "fig_primer_anchorfix.pdf", bbox_inches="tight")
    plt.close(fig)
    print("  -> fig_primer_anchorfix.pdf")


def main():
    print("Building primer teaching figures:")
    fig_heatflow()
    fig_retrieval()
    fig_anchorfix()
    print("done.")


if __name__ == "__main__":
    main()
