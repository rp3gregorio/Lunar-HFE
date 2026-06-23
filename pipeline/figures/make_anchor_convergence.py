#!/usr/bin/env python3
"""Anchor-method convergence trace (guidebook Fig., the flux-anchored output).

Runs one real A15 K_d=4.58 flux-anchored solve and plots the per-outer-cycle
convergence captured in ``EquilibriumResult.history``:

  * top  -- the anchor temperature <T>(z0) settling, coloured by anchor stage
            (stage 1 at z0=0.25 m, stage 2 at z0=0.55 m);
  * bottom-- the inter-cycle drift |Delta<T>(z0)| on a log axis, contracting
            geometrically past the two stage tolerances (0.10 K, 0.005 K).

This visualises the *output* of the anchor method: a certified, geometrically
contracting fixed point reached in ~9 outer cycles. Real numbers, not a sketch.

Run:  python pipeline/figures/make_anchor_convergence.py
"""
from __future__ import annotations
import json
import pathlib

import numpy as np
import matplotlib.pyplot as plt

from lunar.plotting.style import (
    JGR_HALF, C_FOREST, C_TEAL, C_CORAL, C_CHAR, C_DIM, C_GRID,
)
from lunar.config import SITES, GRID, S0, T_LUNAR, DT_STEP
from lunar.grid import make_geometric_grid
from lunar.properties import conductivity_hayne
from lunar.equilibrium import solve_periodic_equilibrium

_REPO = pathlib.Path(__file__).resolve().parents[2]
_OUT = _REPO / "results" / "figures"


def _trace(site_key="A15"):
    """Real per-cycle convergence history for the headline solve."""
    res = json.load(open(_REPO / "results" / "kd_retrieval_results.json"))
    kd = res[site_key]["kd_star"]
    s = SITES[site_key]
    grid = make_geometric_grid(**GRID)
    n_t = int(T_LUNAR / DT_STEP) + 1
    t = np.linspace(0.0, T_LUNAR, n_t)
    insol = S0 * np.cos(np.deg2rad(s["lat"])) * np.maximum(0.0, np.cos(2 * np.pi * t / T_LUNAR))
    eq = solve_periodic_equilibrium(
        grid, t, insol, albedo=s["albedo"], emissivity=s["emissivity"],
        Q_b=s["Q_BASAL"], K_func=lambda T, z: conductivity_hayne(T, z, Kd=kd))
    return kd, eq


def main():
    kd, eq = _trace("A15")
    hist = list(eq.history)
    cyc = np.arange(1, len(hist) + 1)
    z0 = np.array([h[0] for h in hist])
    anchor = np.array([h[2] for h in hist])
    drift = np.array([h[3] for h in hist])
    s1 = z0 < 0.40                      # stage 1 (shallow anchor)
    s2 = ~s1                            # stage 2 (deep anchor)

    fig, (axT, axD) = plt.subplots(
        2, 1, figsize=(JGR_HALF, 4.7), sharex=True,
        gridspec_kw=dict(height_ratios=[1.0, 1.0], hspace=0.12),
        constrained_layout=True)

    # ── top: anchor temperature settling ───────────────────────────────────
    axT.plot(cyc, anchor, "-", color=C_DIM, lw=1.3, zorder=1)
    axT.plot(cyc[s1], anchor[s1], "o", color=C_TEAL, ms=7, zorder=3,
             label=r"stage 1: anchor $z_0=0.25$ m")
    axT.plot(cyc[s2], anchor[s2], "s", color=C_FOREST, ms=7, zorder=3,
             label=r"stage 2: anchor $z_0=0.55$ m")
    axT.axhline(anchor[-1], color=C_CHAR, lw=0.8, ls=(0, (1, 2)), zorder=0)
    axT.set_ylabel(r"anchor $\langle T\rangle(z_0)$  [K]")
    axT.set_title("The anchor temperature settles in ~9 outer cycles", loc="left")
    axT.legend(loc="lower right", frameon=True, edgecolor=C_GRID, framealpha=0.97)
    axT.grid(color=C_GRID, lw=0.5)
    axT.set_axisbelow(True)
    # final value annotation, parked in clear space (no overlap with markers)
    axT.annotate(rf"$\to\,{anchor[-1]:.2f}$ K",
                 xy=(cyc[-1], anchor[-1]), xytext=(-2, 8),
                 textcoords="offset points", ha="right", va="bottom",
                 fontsize=9, color=C_CHAR)

    # ── bottom: drift contraction (log) ─────────────────────────────────────
    fin = np.isfinite(drift) & (drift > 0)
    axD.plot(cyc[fin & s1], drift[fin & s1], "o", color=C_TEAL, ms=7, zorder=3)
    axD.plot(cyc[fin & s2], drift[fin & s2], "s-", color=C_FOREST, ms=7, lw=1.3, zorder=3)
    axD.axhline(0.10, color=C_TEAL, lw=1.2, ls="--", zorder=1)
    axD.axhline(0.005, color=C_FOREST, lw=1.2, ls="--", zorder=1)
    axD.set_yscale("log")
    axD.set_xlabel("outer cycle")
    axD.set_ylabel(r"anchor drift  $|\Delta\langle T\rangle(z_0)|$  [K]")
    axD.set_title("Drift contracts geometrically past both tolerances", loc="left")
    axD.grid(color=C_GRID, lw=0.5, which="both")
    axD.set_axisbelow(True)
    axD.set_xticks(cyc)
    # tolerance labels parked at the left edge, above their lines, never on points
    axD.text(cyc[0] - 0.35, 0.10, r"stage-1 tol $0.10$ K", color=C_TEAL,
             fontsize=8.5, va="bottom", ha="left")
    axD.text(cyc[0] - 0.35, 0.005, r"stage-2 tol $0.005$ K", color=C_FOREST,
             fontsize=8.5, va="bottom", ha="left")
    axD.set_ylim(0.002, 0.2)

    _OUT.mkdir(parents=True, exist_ok=True)
    out = _OUT / "fig_anchor_convergence.pdf"
    fig.savefig(out)
    plt.close(fig)
    print(f"  wrote {out}  (kd*={kd*1e3:.3f} mW, {len(hist)} outer cycles, "
          f"final drift {drift[-1]:.4f} K, closure {eq.flux_closure*100:.2f}%)")


if __name__ == "__main__":
    main()
