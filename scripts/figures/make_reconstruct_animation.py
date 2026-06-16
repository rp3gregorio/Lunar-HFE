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

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation, PillowWriter

from lunar.config import SITES, GRID, HAYNE, S0, T_LUNAR, DT_STEP
from lunar.grid import make_geometric_grid
from lunar.properties import conductivity_hayne, specific_heat
from lunar.equilibrium import solve_periodic_equilibrium
from lunar.plotting.style import C_A15, C_HAYNE, C_CHAR, C_DIM

DOC = _REPO / "docs" / "justification"
SITE = SITES["A15"]; KD = 4.58e-3; Z0 = 0.55; ZMAX = 3.0


def main():
    g = make_geometric_grid(**GRID); z = g.z_mid; dz = g.dz
    t = np.arange(0, T_LUNAR, DT_STEP)
    insol = S0 * (1 - SITE["albedo"]) * np.clip(np.cos(2 * np.pi * t / T_LUNAR), 0, None)
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


if __name__ == "__main__":
    main()
