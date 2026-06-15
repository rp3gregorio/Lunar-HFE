#!/usr/bin/env python3
"""Solver-certification figure for the supporting information.

Demonstrates the two convergence properties claimed in manuscript
Sec. 2.3 for the flux-anchored periodic-equilibrium driver
(lunar/equilibrium.py):

  (a) initial-guess independence: converged mean profiles from
      T_guess = 240 K and 260 K agree to <~0.03 K at every depth;
  (b) honest-run drift: a 120-lunation fixed-forcing integration
      started from the converged profile moves < 0.1 K at the
      sensor depths (i.e. the returned state is a true fixed point).

Writes output/figures/fig_equilibrium_certification.pdf and
output/equilibrium_certification.json.

Run with:
    python scripts/figures/make_equilibrium_certification.py
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

from lunar.equilibrium import solve_periodic_equilibrium
from lunar.grid import make_geometric_grid
from lunar.solver import PixelInputs, solve_pixel
from lunar.properties import conductivity_hayne, specific_heat
from scripts.pipeline.retrieve_kd import SITES, HAYNE, GRID, S0, T_LUNAR, DT_STEP

from lunar.plotting.style import (   # type: ignore
    JGR_FULL, FS_TICK, FS_LEGEND, FS_LABEL,
    C_A15, C_A17, C_CHAR, C_DIM, C_GRID, fmt_axis,
)

KD_STAR = {"A15": 4.583e-3, "A17": 8.117e-3}   # converged retrievals


def certify(site):
    cfg = SITES[site]
    grid_ = make_geometric_grid(**GRID)
    n_t = int(T_LUNAR / DT_STEP) + 1
    t = np.linspace(0.0, T_LUNAR, n_t)
    insol = (S0 * np.cos(np.deg2rad(cfg["lat"]))
             * np.maximum(0.0, np.cos(2 * np.pi * t / T_LUNAR)))
    kf = lambda T, z: conductivity_hayne(
        T, z, Ks=HAYNE["K_S"], Kd=KD_STAR[site], H=HAYNE["H"],
        chi=HAYNE["CHI"])
    cpf = lambda T: specific_heat(T, model="hayne")

    eqs = {}
    for guess in (240.0, 260.0):
        eqs[guess] = solve_periodic_equilibrium(
            grid=grid_, t=t, insolation=insol, albedo=cfg["albedo"],
            emissivity=cfg["emissivity"], Q_b=cfg["Q_BASAL"],
            K_func=kf, cp_func=cpf, T_guess=guess)
    dprof = eqs[260.0].T_mean - eqs[240.0].T_mean

    out = solve_pixel(PixelInputs(
        grid=grid_, t=t, bc_mode="radiative", insolation=insol,
        albedo=cfg["albedo"], emissivity=cfg["emissivity"],
        Q_b=cfg["Q_BASAL"], T_init=eqs[240.0].T_mean,
        n_lunations_spinup=120, spinup_tol_K=0.0,
        K_func=kf, cp_func=cpf))
    drift = out.T.mean(axis=1) - eqs[240.0].T_mean
    return grid_.z_mid, dprof, drift


def main():
    fig, axes = plt.subplots(1, 2, figsize=(JGR_FULL, 4.0),
                             gridspec_kw={"wspace": 0.26})
    fig.subplots_adjust(left=0.09, right=0.985, top=0.92, bottom=0.27)

    summary = {}
    for site, color in (("A15", C_A15), ("A17", C_A17)):
        z, dprof, drift = certify(site)
        band = (z >= 0.6) & (z <= 2.5)
        summary[site] = dict(
            guess_independence_max_K=float(np.abs(dprof).max()),
            drift_120lun_sensorband_max_K=float(np.abs(drift[band]).max()),
            kd_star_W_m_K=KD_STAR[site])
        axes[0].plot(np.abs(dprof) * 1e3, z * 100, color=color, lw=1.8,
                     label=f"{site} (max {np.abs(dprof).max()*1e3:.0f} mK)")
        axes[1].plot(np.abs(drift) * 1e3, z * 100, color=color, lw=1.8,
                     label=f"{site} (max {np.abs(drift[band]).max()*1e3:.0f} mK"
                           " in sensor band)")

    for ax, xlab, title in (
            (axes[0], r"$|\langle T\rangle_{260} - \langle T\rangle_{240}|$  (mK)",
             "(a)  Initial-guess independence"),
            (axes[1], r"$|\Delta\langle T\rangle|$ after 120 lunations  (mK)",
             "(b)  Fixed-point drift test")):
        ax.axhspan(80, 234, color=C_GRID, alpha=0.30, zorder=0)
        ax.text(0.97, 0.55, "sensor depths\n(80–234 cm)",
                transform=ax.transAxes, ha="right", va="center",
                fontsize=FS_TICK - 1.5, color=C_DIM, style="italic")
        fmt_axis(ax, xlabel=xlab,
                 ylabel="Depth (cm)" if ax is axes[0] else "", title=title)
        ax.set_ylim(500, 0)
        ax.set_xlim(left=0)

    h, l = axes[0].get_legend_handles_labels()
    h2, l2 = axes[1].get_legend_handles_labels()
    fig.legend(h + h2, l + l2, loc="lower center",
               bbox_to_anchor=(0.5, 0.0), ncols=2, frameon=True,
               edgecolor=C_GRID, framealpha=0.97, fontsize=FS_LEGEND,
               handlelength=1.8, borderpad=0.5)

    out_fig = _REPO / "output" / "figures" / "fig_equilibrium_certification.pdf"
    fig.savefig(out_fig)
    plt.close(fig)
    out_json = _REPO / "output" / "equilibrium_certification.json"
    out_json.write_text(json.dumps(summary, indent=2))
    print(f"wrote {out_fig}")
    print(f"wrote {out_json}")
    print(json.dumps(summary, indent=1))


if __name__ == "__main__":
    main()
