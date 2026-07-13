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
from lunar.plotting.style import (JGR_HALF, C_A15, C_HAYNE, C_A17, C_CHAR, C_DIM, C_GRID,
                                  assert_no_overlap)

FIG = _REPO / "results" / "figures"; FIG.mkdir(parents=True, exist_ok=True)
SITE = SITES["A15"]; Qb = SITE["Q_BASAL"]; KD = 4.60e-3
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
    # one column to 8 m: the two models are the SAME line until the bedrock,
    # then fork -- the whole argument in a single view.
    z = np.linspace(0.55, 8.0, 1600)
    T_norock, T_rock = _integrate(z, False), _integrate(z, True)

    d = extract_sensor_stability(SITE["mission"], SITE["MIN_DEPTH_CM"])
    mask = np.array(d["deep_mask"])
    z_d = np.array(d["depth_cm_all"])[mask] / 100.0
    T_d = np.array(d["T_eq_all"])[mask]; T_e = np.array(d["T_std_all"])[mask]
    z_deep = float(z_d.max())                          # deepest sensor (~1.39 m)
    T_fork = float(np.interp(ZBASE, z, T_norock))      # where the two models split

    fig, ax = plt.subplots(figsize=(JGR_HALF, 5.4))
    # the two layers, with the interface line
    ax.axhspan(0.0, ZBASE, color=C_A15, alpha=0.06, zorder=0)
    ax.axhspan(ZBASE, 8.0, color=C_HAYNE, alpha=0.08, zorder=0)
    ax.axhline(ZBASE, color=C_CHAR, lw=1.0, ls="--", zorder=1)

    # the two models: ONE line through every sensor, forking only at the bedrock
    ax.plot(T_norock, z, "-", color=C_A15, lw=3.2, zorder=3,
            label="regolith only (no bedrock)")
    ax.plot(T_rock, z, "-", color=C_HAYNE, lw=3.2, zorder=3,
            label="with bedrock below 5 m")
    ax.errorbar(T_d, z_d, xerr=T_e, fmt="o", color=C_A17, ms=8, capsize=3, lw=1.3,
                zorder=6, label="Apollo 15 sensors")
    # mark the depth span the sensors actually occupy, against the 5 m fork
    ax.annotate("", xy=(250.5, ZBASE), xytext=(250.5, z_deep),
                arrowprops=dict(arrowstyle="<->", color=C_CHAR, lw=1.2))
    ax.text(250.8, 0.5 * (z_deep + ZBASE), f"{ZBASE - z_deep:.1f} m\nof regolith,\nno sensor",
            color=C_CHAR, fontsize=8, ha="left", va="center")

    # layer tags. The "regolith" tag previously sat at depth 0.5 (clipping
    # the diagonal curve's own starting point there -- a guessed margin,
    # not a verified one); moved above the curve's start (depth ~0.5) into
    # the empty strip between the axis top and the line/sensors.
    ax.text(250.4, 0.15, "regolith", color=C_A15, fontsize=9.5, ha="left",
            va="center", fontweight="bold")
    ax.text(254.5, 7.3, "bedrock", color=C_HAYNE, fontsize=9.5, ha="left",
            va="center", fontweight="bold")

    # the single load-bearing annotation: they fork only at the bedrock
    ax.annotate("the two models split\nonly here — at the\nbedrock, far below\nevery sensor",
                xy=(T_fork, ZBASE), xytext=(250.6, 6.7),
                fontsize=8.5, color=C_CHAR, ha="left", va="center",
                arrowprops=dict(arrowstyle="->", color=C_CHAR, lw=1.0))

    ax.invert_yaxis(); ax.set_xlim(250, 271); ax.set_ylim(8.0, 0)
    ax.set_xlabel("temperature  [K]"); ax.set_ylabel("depth  [m]")
    ax.set_title("A bedrock layer can't change $K_d$:\n"
                 "the models are one line through every sensor",
                 loc="left", fontsize=12, color=C_CHAR, fontweight="bold")
    ax.legend(loc="upper right", fontsize=9, frameon=True, edgecolor=C_GRID, framealpha=0.97)
    ax.grid(alpha=0.2)
    fig.tight_layout()
    fig.canvas.draw()
    assert_no_overlap(ax)
    out = FIG / "fig_baselayer.pdf"
    fig.savefig(out, bbox_inches="tight"); plt.close(fig)
    print(f"  -> {out.relative_to(_REPO)}  "
          f"(fork at {T_fork:.1f} K, 5 m; T at 8 m: {T_norock[-1]:.1f} K regolith vs "
          f"{T_rock[-1]:.1f} K bedrock; deepest sensor {z_deep:.2f} m; {len(z_d)} sensors)")


if __name__ == "__main__":
    main()
