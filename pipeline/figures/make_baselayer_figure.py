#!/usr/bin/env python3
"""Does the result change with or without a bedrock base layer?

Integrates the steady-state closure d<T>/dz = Q_b/K downward for Apollo 15 and
shows three columns of regolith behaviour against the real deep-sensor data:

  * without bedrock (this study)  -- fixed basal flux, profile rises ~linearly
    at the geothermal gradient Q_b/K and never settles to one value;
  * with a bedrock base below 5 m -- K jumps ~200x, the gradient nearly
    vanishes and the profile flattens toward a constant;
  * Q_b = 0                        -- isothermal (no internal heat; not the Moon).

The Apollo deep sensors (0.8-1.4 m) sit entirely in the regolith, where the two
models are identical -- so a base layer changes only what lies below the data
and leaves K_d unchanged.  Real conductivity (Hayne) + real sensor data.

Output: results/figures/fig_baselayer.pdf
"""
from __future__ import annotations
import sys, pathlib, functools
import numpy as np

_REPO = pathlib.Path(__file__).resolve().parents[1].parent
sys.path.insert(0, str(_REPO)); sys.path.insert(0, str(_REPO / "src"))

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from lunar.config import SITES, HAYNE
from lunar.properties import conductivity_hayne
from lunar.apollo_helpers import extract_sensor_stability
from lunar.plotting.style import (JGR_HALF, C_A15, C_HAYNE, C_A17, C_CHAR, C_DIM, C_GRID)

FIG = _REPO / "results" / "figures"; FIG.mkdir(parents=True, exist_ok=True)
SITE = SITES["A15"]; Qb = SITE["Q_BASAL"]; KD = 4.58e-3
ZBASE, KROCK, T0 = 5.0, 1.7, 251.8       # bedrock below 5 m; real A15 anchor at 0.55 m

Kf = functools.partial(conductivity_hayne, Ks=HAYNE["K_S"], Kd=KD, H=HAYNE["H"], chi=HAYNE["CHI"])
def Kreg(T, z): return float(Kf(np.array([T]), np.array([z]))[0])


def _integrate(z, base, qb=Qb):
    T = np.empty_like(z); T[0] = T0
    for i in range(len(z) - 1):
        K = KROCK if (base and z[i] >= ZBASE) else Kreg(T[i], z[i])
        T[i + 1] = T[i] + qb / K * (z[i + 1] - z[i])
    return T


def main():
    z = np.linspace(0.55, 12.0, 1500)
    T_norock, T_rock, T_q0 = _integrate(z, False), _integrate(z, True), _integrate(z, False, 0.0)

    d = extract_sensor_stability(SITE["mission"], SITE["MIN_DEPTH_CM"])
    mask = np.array(d["deep_mask"])
    z_d = np.array(d["depth_cm_all"])[mask] / 100.0
    T_d = np.array(d["T_eq_all"])[mask]; T_e = np.array(d["T_std_all"])[mask]

    fig, ax = plt.subplots(figsize=(7.0, 5.6))
    ax.axhspan(0.8, 2.4, color=C_DIM, alpha=0.10, zorder=0, label="Apollo deep-sensor band")
    ax.plot(T_norock, z, "-", color=C_A15, lw=2.8, label="without bedrock (this study)")
    ax.plot(T_rock, z, "-", color=C_HAYNE, lw=2.8, label="with bedrock base below 5 m")
    ax.plot(T_q0, z, ":", color=C_DIM, lw=2.0, label=r"$Q_b=0$ (no internal heat)")
    ax.errorbar(T_d, z_d, xerr=T_e, fmt="o", color=C_A17, ms=7, capsize=3, lw=1.2,
                zorder=6, label="Apollo 15 deep sensors")
    ax.axhline(ZBASE, color=C_A17, lw=1.0, ls="--", alpha=0.7)
    ax.text(250.4, ZBASE - 0.12, "regolith / bedrock interface", color=C_A17,
            fontsize=8.5, va="bottom", ha="left")
    ax.annotate(r"$d\langle T\rangle/dz=Q_b/K\approx2.3$ K/m" + "\n(real geothermal gradient)",
                xy=(T_norock[np.argmin(abs(z - 9))], 9), xytext=(252.6, 11.0),
                fontsize=9, color=C_A15, arrowprops=dict(arrowstyle="->", color=C_A15, lw=0.9))
    ax.annotate("bedrock $K$ ~200x higher\n" + r"$\to$ gradient ~vanishes",
                xy=(T_rock[np.argmin(abs(z - 8))], 8), xytext=(265, 6.3),
                fontsize=9, color=C_HAYNE, arrowprops=dict(arrowstyle="->", color=C_HAYNE, lw=0.9))
    ax.invert_yaxis(); ax.set_xlim(250, 282); ax.set_ylim(12, 0)
    ax.set_xlabel("cycle-mean temperature  [K]"); ax.set_ylabel("depth  [m]")
    ax.set_title("With vs without a bedrock base layer  (Apollo 15)",
                 loc="left", fontsize=12, color=C_CHAR, fontweight="bold")
    ax.legend(loc="lower right", fontsize=8.5, frameon=True, edgecolor=C_GRID, framealpha=0.97)
    ax.grid(alpha=0.18)

    axi = ax.inset_axes([0.55, 0.55, 0.42, 0.40])
    axi.axhspan(0.8, 2.4, color=C_DIM, alpha=0.10)
    axi.plot(T_norock, z, "-", color=C_A15, lw=2.4)
    axi.plot(T_rock, z, "-", color=C_HAYNE, lw=2.0, ls=(0, (4, 2)))
    axi.errorbar(T_d, z_d, xerr=T_e, fmt="o", color=C_A17, ms=5, capsize=2, lw=1.0, zorder=6)
    axi.invert_yaxis(); axi.set_xlim(250, 255.5); axi.set_ylim(2.5, 0.4)
    axi.tick_params(labelsize=7)
    axi.set_title("where the data is:\nidentical, both fit", fontsize=8, color=C_CHAR, pad=2)
    for s in axi.spines.values(): s.set_edgecolor(C_DIM)

    fig.tight_layout()
    out = FIG / "fig_baselayer.pdf"
    fig.savefig(out, bbox_inches="tight"); plt.close(fig)
    print(f"  -> {out.relative_to(_REPO)}  "
          f"(T at 12 m: {T_norock[-1]:.1f} K without vs {T_rock[-1]:.1f} K with bedrock; "
          f"{len(z_d)} deep sensors)")


if __name__ == "__main__":
    main()
