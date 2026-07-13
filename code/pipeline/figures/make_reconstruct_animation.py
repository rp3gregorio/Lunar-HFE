#!/usr/bin/env python3
"""Animate the ONE idea people find hardest: how the deep profile is
'already calculated' without simulating it.

At steady state the same geothermal heat Q_b flows through every layer, and
Fourier's law says flux = K * dT/dz. So at every depth the SLOPE of the
temperature profile is fixed: dT/dz = Q_b / K. Knowing the temperature at one
anchor point, we just walk downward adding (slope x step) -- the deep profile
draws itself. This GIF shows that walk.

Output: docs/justification/reconstruct.gif   (run from the repo root)
"""
from __future__ import annotations
import sys, pathlib, functools
import numpy as np

_REPO = pathlib.Path(__file__).resolve().parents[1].parent
sys.path.insert(0, str(_REPO))
sys.path.insert(0, str(_REPO / "src"))

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation, PillowWriter

from lunar.config import SITES, GRID, HAYNE, S0, T_LUNAR, DT_STEP
from lunar.grid import make_geometric_grid
from lunar.properties import conductivity_hayne, specific_heat
from lunar.solver import standard_insolation, periodic_time_grid
from lunar.equilibrium import solve_periodic_equilibrium
from lunar.plotting.style import JGR_FULL, C_A15, C_HAYNE, C_CHAR, C_DIM, C_GRID

DOC = _REPO / "results" / "anim"
SITE = SITES["A15"]; KD = 4.60e-3; Z0 = 0.55; ZMAX = 3.0


def main():
    g = make_geometric_grid(**GRID); z = g.z_mid; dz = g.dz
    t = periodic_time_grid(DT_STEP)   # commensurate lunation grid (audit 2026-07-03)
    insol = standard_insolation(SITE["lat"], t)   # raw flux; solver applies (1-A)
    K = functools.partial(conductivity_hayne, Ks=HAYNE["K_S"], Kd=KD, H=HAYNE["H"], chi=HAYNE["CHI"])
    cp = functools.partial(specific_heat, model="hayne")
    Qb = SITE["Q_BASAL"]
    eq = solve_periodic_equilibrium(grid=g, t=t, insolation=insol, albedo=SITE["albedo"],
            emissivity=SITE["emissivity"], Q_b=Qb, K_func=K, cp_func=cp, T_guess=SITE["T_MEAN_EFF"])
    T_target = eq.T_mean

    i0 = int(np.argmin(np.abs(z - Z0)))
    T = T_target.copy()                       # skin (z<z0) is known from Step A
    for i in range(i0, z.size - 1):           # walk downward using the slope rule
        slope = Qb / float(K(np.array([T[i]]), np.array([z[i]]))[0])
        T[i + 1] = T[i] + slope * dz[i]

    m = z <= ZMAX
    deep_idx = [i for i in range(i0, z.size) if z[i] <= ZMAX]
    fig, ax = plt.subplots(figsize=(7.4, 5.4))

    def draw(step):
        ax.clear()
        ax.plot(T_target[m], z[m], "--", color=C_DIM, lw=1.6, label="true steady state (target)")
        # known skin (Step A)
        sk = z <= Z0
        ax.plot(T[sk], z[sk], "-", color=C_DIM, lw=2, alpha=0.5)
        ax.plot(T_target[i0], Z0, "o", color=C_CHAR, ms=9)
        ax.annotate("anchor T\n(from Step A)", xy=(T_target[i0], Z0), xytext=(T_target[i0] + 9, Z0 - 0.15),
                    fontsize=8.5, color=C_CHAR, arrowprops=dict(arrowstyle="->", color=C_CHAR, lw=0.8))
        k = deep_idx[min(step, len(deep_idx) - 1)]
        built = (z >= Z0) & (z <= z[k])
        ax.plot(T[built], z[built], "-", color=C_HAYNE, lw=3, label="deep profile, built by the rule")
        # current slope arrow
        if k < z.size - 1:
            Kk = float(K(np.array([T[k]]), np.array([z[k]]))[0]); slope = Qb / Kk
            dzz = 0.18
            ax.annotate("", xy=(T[k] + slope * dzz, z[k] + dzz), xytext=(T[k], z[k]),
                        arrowprops=dict(arrowstyle="-|>", color=C_A15, lw=2.5))
            ax.text(0.62, 0.30,
                    "at this depth the slope is fixed:\n"
                    r"$\dfrac{dT}{dz}=\dfrac{Q_b}{K}=$ " + f"{slope:.1f} K/m\n\n"
                    "next point = this point + slope x step",
                    transform=ax.transAxes, fontsize=9.5, color=C_CHAR,
                    bbox=dict(boxstyle="round,pad=0.4", fc="white", ec=C_A15, lw=1))
        ax.invert_yaxis(); ax.set_xlim(244, 262); ax.set_ylim(ZMAX, 0)
        ax.axhline(Z0, color=C_DIM, lw=0.6, ls=":")
        ax.set_xlabel("temperature  [K]"); ax.set_ylabel("depth  [m]")
        ax.set_title("Building the deep profile by following the known slope  $Q_b/K$",
                     fontsize=11.5, color=C_CHAR, fontweight="bold", loc="left")
        ax.legend(loc="lower left", fontsize=9, frameon=False)
        fig.tight_layout(); return []

    sub = list(range(0, len(deep_idx), 2)) + [len(deep_idx) - 1] * 5   # snappier + hold end
    anim = FuncAnimation(fig, lambda s: draw(sub[s]), frames=len(sub), blit=False)
    anim.save(str(DOC / "reconstruct.gif"), writer=PillowWriter(fps=8))
    plt.close(fig)
    print(f"  -> {(DOC/'reconstruct.gif').relative_to(_REPO)}  "
          f"(slope at anchor = {Qb/float(K(np.array([T_target[i0]]),np.array([z[i0]]))[0]):.1f} K/m)")


def _compute():
    """Solve the real A15 equilibrium and walk the deep profile down by the
    slope rule. Returns everything the GIF and the filmstrip both need."""
    g = make_geometric_grid(**GRID); z = g.z_mid; dz = g.dz
    t = periodic_time_grid(DT_STEP)   # commensurate lunation grid (audit 2026-07-03)
    insol = standard_insolation(SITE["lat"], t)   # raw flux; solver applies (1-A)
    K = functools.partial(conductivity_hayne, Ks=HAYNE["K_S"], Kd=KD, H=HAYNE["H"], chi=HAYNE["CHI"])
    cp = functools.partial(specific_heat, model="hayne")
    Qb = SITE["Q_BASAL"]
    eq = solve_periodic_equilibrium(grid=g, t=t, insolation=insol, albedo=SITE["albedo"],
            emissivity=SITE["emissivity"], Q_b=Qb, K_func=K, cp_func=cp, T_guess=SITE["T_MEAN_EFF"])
    T_target = eq.T_mean
    i0 = int(np.argmin(np.abs(z - Z0)))
    T = T_target.copy()
    for i in range(i0, z.size - 1):
        slope = Qb / float(K(np.array([T[i]]), np.array([z[i]]))[0])
        T[i + 1] = T[i] + slope * dz[i]
    return z, T, T_target, i0, Qb, K


def filmstrip():
    """Static 4-panel still of the slope walk for the guidebook (LaTeX cannot
    embed the GIF). Placement is collision-free by construction: the slope
    label lives in the empty top-right corner, the legend sits *below* all
    axes, and the two never share space with the diagonal profile."""
    z, T, T_target, i0, Qb, K = _compute()
    m = z <= ZMAX
    deep_idx = [i for i in range(i0, z.size) if z[i] <= ZMAX]
    slope_anch = Qb / float(K(np.array([T_target[i0]]), np.array([z[i0]]))[0])

    fracs = [0.0, 0.45, 0.75, 1.0]
    titles = ["drop the anchor", r"walk down: slope $=Q_b/K$",
              "two-thirds built", "complete deep profile"]
    fig, axes = plt.subplots(1, 4, figsize=(JGR_FULL, 3.3), sharey=True)
    for j, (ax, fr, title) in enumerate(zip(axes, fracs, titles)):
        k = deep_idx[min(int(round(fr * (len(deep_idx) - 1))), len(deep_idx) - 1)]
        ax.plot(T_target[m], z[m], "--", color=C_DIM, lw=1.5, label="target (steady state)")
        sk = z <= Z0
        ax.plot(T[sk], z[sk], "-", color=C_DIM, lw=2, alpha=0.5)
        built = (z >= Z0) & (z <= z[k])
        ax.plot(T[built], z[built], "-", color=C_HAYNE, lw=3, label="reconstructed (slope walk)")
        ax.plot(T_target[i0], Z0, "o", color=C_CHAR, ms=8, label="anchor (known from Step A)")
        if 0 < fr < 1 and k < z.size - 1:                 # slope vector at the build front
            slope = Qb / float(K(np.array([T[k]]), np.array([z[k]]))[0])
            dzz = 0.28
            ax.annotate("", xy=(T[k] + slope * dzz, z[k] + dzz), xytext=(T[k], z[k]),
                        arrowprops=dict(arrowstyle="-|>", color=C_A15, lw=2.2))
        ax.invert_yaxis(); ax.set_xlim(244, 262); ax.set_ylim(ZMAX, 0)
        ax.axhline(Z0, color=C_DIM, lw=0.6, ls=":")
        ax.set_xlabel("temperature  [K]")
        ax.set_title(title, fontsize=10, color=C_CHAR, loc="left")
    axes[0].set_ylabel("depth  [m]")
    # slope rule, parked in the empty top-right of the "walk down" panel
    # (shallow depth + high T is clear of the diagonal profile and the dashed target)
    axes[1].text(0.96, 0.93, r"$\dfrac{dT}{dz}=\dfrac{Q_b}{K}\approx$" + f"{slope_anch:.1f}",
                 transform=axes[1].transAxes, fontsize=9, color=C_A15, ha="right", va="top",
                 bbox=dict(boxstyle="round,pad=0.3", fc="white", ec=C_A15, lw=0.8))
    # shared legend below the row -- never on the data
    h, l = axes[0].get_legend_handles_labels()
    fig.legend(h, l, loc="lower center", ncol=3, frameon=True, edgecolor=C_GRID,
               framealpha=0.97, bbox_to_anchor=(0.5, -0.01))
    fig.suptitle(r"Reconstructing the deep profile: from the anchor, walk down using $dT/dz=Q_b/K$",
                 fontsize=11.5, color=C_CHAR, fontweight="bold")
    fig.tight_layout(rect=[0, 0.08, 1, 0.95])
    out = (_REPO / "results" / "figures") / "reconstruct_filmstrip.pdf"
    fig.savefig(out); plt.close(fig)
    print(f"  -> {out.relative_to(_REPO)}  (slope at anchor {slope_anch:.1f} K/m)")


if __name__ == "__main__":
    filmstrip()
    main()
