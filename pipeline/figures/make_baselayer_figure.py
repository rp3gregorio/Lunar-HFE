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
    z = np.linspace(0.55, 20.0, 2200)
    T_norock, T_rock, T_q0 = _integrate(z, False), _integrate(z, True), _integrate(z, False, 0.0)

    d = extract_sensor_stability(SITE["mission"], SITE["MIN_DEPTH_CM"])
    mask = np.array(d["deep_mask"])
    z_d = np.array(d["depth_cm_all"])[mask] / 100.0
    T_d = np.array(d["T_eq_all"])[mask]; T_e = np.array(d["T_std_all"])[mask]

    fig, (axL, axR) = plt.subplots(1, 2, figsize=(10.0, 4.8),
                                   gridspec_kw=dict(wspace=0.26))

    # LEFT — the data region: the two models lie on top of each other
    axL.axhspan(0.8, 2.4, color=C_DIM, alpha=0.12, zorder=0)
    axL.plot(T_norock, z, "-", color=C_A15, lw=3.0, label="without bedrock")
    axL.plot(T_rock, z, "--", color=C_HAYNE, lw=2.2, label="with bedrock")
    axL.errorbar(T_d, z_d, xerr=T_e, fmt="o", color=C_A17, ms=9, capsize=3, lw=1.4,
                 zorder=6, label="Apollo 15 sensors")
    axL.invert_yaxis(); axL.set_xlim(250, 256); axL.set_ylim(2.6, 0)
    axL.set_xlabel("temperature  [K]"); axL.set_ylabel("depth  [m]")
    axL.set_title("Where the data is (0–2.4 m):\nthe two models are identical",
                  loc="left", fontsize=12, color=C_CHAR, fontweight="bold")
    axL.legend(loc="lower left", fontsize=10, frameon=False)
    axL.grid(alpha=0.2)

    # RIGHT — the realistic two-layer column (regolith on bedrock), to 20 m
    axR.axhspan(0.0, ZBASE, color=C_A15, alpha=0.06, zorder=0)        # regolith layer
    axR.axhspan(ZBASE, 20, color=C_HAYNE, alpha=0.07, zorder=0)       # bedrock layer
    axR.axhspan(0.8, 2.4, color=C_DIM, alpha=0.16, zorder=0, label="Apollo sensors")
    axR.plot(T_norock, z, "-", color=C_A15, lw=3.0, label="no bedrock (regolith only)")
    axR.plot(T_rock, z, "-", color=C_HAYNE, lw=3.0, label="with bedrock (realistic)")
    axR.axhline(ZBASE, color=C_CHAR, lw=1.0, ls="--")
    axR.text(250.6, ZBASE - 0.4, "regolith (~5 m)", color=C_A15, fontsize=9.5,
             ha="left", va="bottom", fontweight="bold")
    axR.text(250.6, ZBASE + 0.4, "bedrock (solid rock)", color=C_HAYNE, fontsize=9.5,
             ha="left", va="top", fontweight="bold")
    axR.text(263.5, 18.3, "nearly flat in the rock\n(on to the deep interior)",
             color=C_HAYNE, fontsize=9, ha="left", va="center")
    axR.invert_yaxis(); axR.set_xlim(250, 292); axR.set_ylim(20, 0)
    axR.set_xlabel("temperature  [K]")
    axR.set_title("The realistic column (0–20 m):\nthin regolith on deep bedrock",
                  loc="left", fontsize=12, color=C_CHAR, fontweight="bold")
    axR.legend(loc="upper right", fontsize=9.5, frameon=True, edgecolor=C_GRID, framealpha=0.97)
    axR.grid(alpha=0.2)

    fig.suptitle("With or without bedrock, the retrieved $K_d$ is the same — the sensors never reach it",
                 fontsize=13, color=C_CHAR, fontweight="bold", y=1.0)
    fig.tight_layout(rect=[0, 0, 1, 0.93])
    out = FIG / "fig_baselayer.pdf"
    fig.savefig(out, bbox_inches="tight"); plt.close(fig)
    print(f"  -> {out.relative_to(_REPO)}  "
          f"(T at 12 m: {T_norock[-1]:.1f} K without vs {T_rock[-1]:.1f} K with bedrock; "
          f"{len(z_d)} deep sensors)")


if __name__ == "__main__":
    main()
