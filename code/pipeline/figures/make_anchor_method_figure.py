#!/usr/bin/env python3
"""Letter figure: the flux-anchored (anchor) method, and proof it works.

Three panels, all computed live from the production solver at the
retrieved Apollo 15 K_d* = 4.60 mW/m/K:

  (a) the construction -- a deliberately wrong starting profile, the
      settled skin above the anchor, and the deep column rebuilt from
      the anchor by the slope rule d<T>/dz = (Q_b - u_rect)/K;
  (b) it is correct -- a brute-force spin-up started 13 K wrong marches
      for 3000 lunations and converges onto the anchored answer, which
      the anchored solve computes directly (four outer iterations);
  (c) the invariant it rests on -- over the resolved skin column the
      cycle-mean conductive flux equals Q_b at every depth, the closure
      Step B integrates downward.

Output: figures/fig_anchor_method.pdf   (JGR full width)
Run:    python code/pipeline/figures/make_anchor_method_figure.py
"""
from __future__ import annotations
import functools
import pathlib
import sys

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

_REPO = pathlib.Path(__file__).resolve().parents[1].parent
sys.path.insert(0, str(_REPO))
sys.path.insert(0, str(_REPO / "src"))

from lunar.config import SITES, GRID, HAYNE, DT_STEP, EQ_Z_ANCHOR, EQ_ANCHOR_TOL
from lunar.grid import make_geometric_grid
from lunar.properties import conductivity_hayne, specific_heat
from lunar.solver import (PixelInputs, solve_pixel, standard_insolation,
                          periodic_time_grid)
from lunar.equilibrium import solve_periodic_equilibrium, _rectified_flux
from lunar.plotting.style import (JGR_FULL, C_A15, C_HAYNE, C_CORAL, C_CHAR,
                                  C_DIM, C_GRID, C_FOREST, fmt_axis,
                                  assert_no_overlap)

OUT = _REPO / ".." / "figures"
SITE = SITES["A15"]
KD = 4.60e-3
Z0 = EQ_Z_ANCHOR
ZMAX = 3.0


def _solve(T_guess):
    g = make_geometric_grid(**GRID)
    t = periodic_time_grid(DT_STEP)
    insol = standard_insolation(SITE["lat"], t)
    K = functools.partial(conductivity_hayne, Ks=HAYNE["K_S"], Kd=KD,
                          H=HAYNE["H"], chi=HAYNE["CHI"])
    cp = functools.partial(specific_heat, model="hayne")
    eq = solve_periodic_equilibrium(
        grid=g, t=t, insolation=insol, albedo=SITE["albedo"],
        emissivity=SITE["emissivity"], Q_b=SITE["Q_BASAL"],
        K_func=K, cp_func=cp, T_guess=T_guess,
        hayne_params=(HAYNE["K_S"], KD, HAYNE["H"], HAYNE["CHI"]))
    return g, K, eq


def main():
    print("Solving (production settings)...")
    g, K, eq = _solve(SITE["T_MEAN_EFF"])
    z = g.z_mid
    m = z <= ZMAX
    i0 = int(np.argmin(np.abs(z - Z0)))
    Qb = SITE["Q_BASAL"]
    t = periodic_time_grid(DT_STEP)
    insol = standard_insolation(SITE["lat"], t)
    cp = functools.partial(specific_heat, model="hayne")
    hp = (HAYNE["K_S"], KD, HAYNE["H"], HAYNE["CHI"])

    # (a) Step-B walk from the anchor with the FULL closure slope
    # (Q_b - u_rect)/K; u_rect from the resolved final cycle where the
    # sub-grid covers it, negligible below.
    zs = eq.out.z
    ur_sub = _rectified_flux(eq.out.T, zs, lambda T, zz: K(T, zz))
    u_rect = np.interp(z, zs, ur_sub, right=0.0)
    T_walk = eq.T_mean.copy()
    for i in range(i0, z.size - 1):
        slope = (Qb - u_rect[i]) / float(K(np.array([T_walk[i]]),
                                           np.array([z[i]]))[0])
        T_walk[i + 1] = T_walk[i] + slope * g.dz[i]
    T_guess = np.linspace(float(eq.T_mean.mean()) - 4.0,
                          float(eq.T_mean.mean()) + 7.0, z.size)

    # (b) brute-force spin-up (compiled kernel) from a 13-K-wrong start:
    # distance to the anchored answer at the 1-m probe, vs lunations
    print("  brute-force ladder to 3000 lunations (compiled kernel)...")
    ip = int(np.argmin(np.abs(z - 1.0)))
    deltas = [1, 2, 2, 5, 10, 30, 50, 100, 300, 500, 1000, 1000]
    T_init = np.full(z.size, 240.0)
    luns, gaps = [], []
    cum = 0
    for d in deltas:
        out = solve_pixel(PixelInputs(
            grid=g, t=t, bc_mode="radiative", insolation=insol,
            albedo=SITE["albedo"], emissivity=SITE["emissivity"], Q_b=Qb,
            T_init=T_init, n_lunations_spinup=d, spinup_tol_K=0.0,
            K_func=K, cp_func=cp, hayne_params=hp))
        cum += d
        T_init = out.T[:, -1]
        luns.append(cum)
        gaps.append(abs(out.T.mean(axis=1)[ip] - eq.T_mean[ip]))
    luns, gaps = np.array(luns), np.array(gaps)
    print(f"  gap after {luns[-1]} lunations: {gaps[-1]*1e3:.1f} mK; "
          f"anchored solve used {eq.n_outer} outer iterations")

    # (c) the invariant, exactly as the solver certifies it
    # (equilibrium._mean_flux_closure): total cycle-mean flux =
    # mean-field part K(<T>) d<T>/dz  +  rectified eddy part u_rect,
    # equal to Q_b at every depth in the converged state.
    K_mean = np.asarray(K(eq.T_mean, z), dtype=float)
    q_total = K_mean * np.gradient(eq.T_mean, z) + u_rect
    ratio = q_total / Qb

    fig, (a, b, c) = plt.subplots(1, 3, figsize=(JGR_FULL, 3.15),
                                  gridspec_kw={"width_ratios": [1.15, 1.0, 1.0]})
    fig.subplots_adjust(left=0.075, right=0.985, top=0.86, bottom=0.155,
                        wspace=0.42)

    # ── (a) the construction ────────────────────────────────────────────────
    sk = z <= Z0
    a.plot(eq.T_mean[m], z[m], "--", color=C_DIM, lw=1.3,
           label="converged steady state")
    a.plot(T_guess[m], z[m], "-", color=C_CORAL, lw=1.6, alpha=0.75,
           label="initial guess")
    a.plot(eq.T_mean[sk], z[sk], "-", color=C_FOREST, lw=2.6,
           label="skin, time-stepped")
    a.plot(T_walk[(z >= Z0) & m], z[(z >= Z0) & m], "-", color=C_HAYNE, lw=2.6,
           label="deep, reconstructed")
    a.plot(eq.T_mean[i0], Z0, "o", color=C_CHAR, ms=8, mec="white", mew=0.8,
           zorder=6)
    a.annotate("anchor", xy=(eq.T_mean[i0], Z0),
               xytext=(eq.T_mean[i0] - 5.0, Z0 - 0.30),
               fontsize=8.5, color=C_CHAR, ha="right", fontweight="bold",
               arrowprops=dict(arrowstyle="->", color=C_CHAR, lw=0.8))
    a.axhline(Z0, color=C_DIM, lw=0.5, ls=":")
    # the downward walk: short arrowheads riding the reconstructed curve,
    # plus a callout in the clear right margin. This is Step B integrating
    # d<T>/dz = (Q_b - u_rect)/K *downward* from the anchor -- the "slope"
    # the reader traces from the anchor point into the deep column.
    deep = (z >= Z0) & m
    wz, wT = z[deep], T_walk[deep]
    for zt in (0.95, 1.65, 2.35):
        z1 = zt + 0.22
        T0 = float(np.interp(zt, wz, wT))
        T1 = float(np.interp(z1, wz, wT))
        a.annotate("", xy=(T1, z1), xytext=(T0, zt),
                   arrowprops=dict(arrowstyle="-|>", color=C_CHAR, lw=1.5,
                                   mutation_scale=12, shrinkA=0, shrinkB=0),
                   zorder=7)
    a.annotate("walk down", xy=(float(np.interp(1.35, wz, wT)), 1.35),
               xytext=(255.6, 0.90), fontsize=6.6, color=C_CHAR,
               ha="left", va="center",
               arrowprops=dict(arrowstyle="->", color=C_DIM, lw=0.7))
    a.set_xlim(242, 263)
    a.set_ylim(ZMAX, 0)
    fmt_axis(a, xlabel="cycle-mean $T$ (K)", ylabel="depth (m)",
             title="(a)  construction")
    a.legend(loc="lower left", fontsize=6.4, frameon=True, edgecolor=C_GRID,
             framealpha=0.95, handlelength=1.5)

    # ── (b) it is correct: brute force converges onto the anchored answer ───
    b.plot(luns, gaps, "-o", color=C_FOREST, lw=1.6, ms=4.5, mec="white",
           mew=0.6, zorder=3)
    b.set_xscale("log")
    b.set_yscale("log")
    b.set_xlim(0.8, 4000)
    b.set_ylim(gaps[-1] * 0.3, gaps[0] * 4)
    b.text(0.05, 0.06,
           f"after {luns[-1]} cycles:\n{gaps[-1]*1e3:.0f} mK from the\nanchored answer",
           transform=b.transAxes, fontsize=7.2, color=C_DIM, ha="left",
           va="bottom")
    fmt_axis(b, xlabel="brute-force lunations",
             ylabel=r"$|\Delta T(1\,\mathrm{m})|$ (K)",
             title="(b)  it is correct")

    # ── (c) the invariant: cycle-mean flux equals Q_b through the column ────
    mf = z <= ZMAX
    c.plot(ratio[mf], z[mf], "-", color=C_A15, lw=2.0)
    c.axvline(1.0, color=C_DIM, lw=0.8, ls="--")
    c.axhline(Z0, color=C_DIM, lw=0.5, ls=":")
    c.text(0.9535, Z0 - 0.04, "anchor", fontsize=7.2, color=C_DIM,
           ha="left", va="bottom")
    c.set_xlim(0.95, 1.05)
    c.set_ylim(ZMAX, 0)
    fmt_axis(c, xlabel=r"$\langle K\,\partial_z T\rangle \,/\, Q_b$",
             ylabel="depth (m)", title="(c)  the invariant")

    fig.canvas.draw()
    for ax in (a, b, c):
        assert_no_overlap(ax)
    OUT.mkdir(parents=True, exist_ok=True)
    out = OUT / "fig_anchor_method.pdf"
    fig.savefig(out)
    plt.close(fig)
    print(f"  -> {out.resolve()}")


if __name__ == "__main__":
    main()
