"""Anatomy of one flux-anchored solve (guidebook §The key insight).

Two panels, both from a real Apollo 17 solve at K_d*=7.16:
 (a) the converged cycle-mean profile, split into the time-stepped skin (Step A)
     and the reconstructed deep column (Step B) below the anchor;
 (b) the cycle-mean conductive flux, flat on Q_b at every depth -- the constant-
     flux fact the whole method rests on.
Real data only (lunar.*); no text on the data; house style module.
"""
import pathlib
import sys

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import Patch
from matplotlib.lines import Line2D

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "src"))
from lunar.config import (SITES, GRID, HAYNE, S0, T_LUNAR, DT_STEP,
                          EQ_Z_ANCHOR, EQ_N_INNER, EQ_MAX_OUTER, EQ_ANCHOR_TOL)
from lunar.grid import make_geometric_grid
from lunar.properties import conductivity_hayne, specific_heat
from lunar.solver import periodic_time_grid
from lunar.equilibrium import solve_periodic_equilibrium, _rectified_flux
from lunar.plotting.style import (JGR_HALF, C_A17, C_TEAL, C_DIM, C_GRID,
                                  C_CHAR, C_CORAL_L, fmt_axis)

OUT = pathlib.Path(__file__).resolve().parents[2] / ".." / "figures"


def main():
    site = SITES["A17"]
    kd = 7.160e-3                                   # A17 retrieved K_d* [W/m/K]
    g = make_geometric_grid(**GRID)
    z = g.z_mid
    t = periodic_time_grid(DT_STEP)   # commensurate lunation grid (audit 2026-07-03)
    insol = S0 * np.cos(np.deg2rad(site["lat"])) * np.maximum(
        0.0, np.cos(2 * np.pi * t / T_LUNAR))
    kf = lambda T, zz: conductivity_hayne(T, zz, Ks=HAYNE["K_S"], Kd=kd,
                                          H=HAYNE["H"], chi=HAYNE["CHI"])
    cf = lambda T: specific_heat(T, model="hayne")

    eq = solve_periodic_equilibrium(
        grid=g, t=t, insolation=insol, albedo=site["albedo"],
        emissivity=site["emissivity"], Q_b=site["Q_BASAL"], K_func=kf, cp_func=cf,
        T_guess=site["T_MEAN_EFF"], z_anchor=EQ_Z_ANCHOR, n_inner=EQ_N_INNER,
        max_outer=EQ_MAX_OUTER, anchor_tol_K=EQ_ANCHOR_TOL)
    Tm = eq.T_mean
    u_rect = _rectified_flux(eq.out.T, z, kf)
    total = kf(Tm, z) * np.gradient(Tm, z) + u_rect       # cycle-mean flux
    Qb = site["Q_BASAL"]
    z0 = EQ_Z_ANCHOR
    i0 = int(np.argmin(np.abs(z - z0)))

    sel = z <= 3.0
    fig, (axL, axR) = plt.subplots(1, 2, figsize=(JGR_HALF, 3.4),
                                   constrained_layout=True)

    # (a) profile anatomy: the curve split into its two constructions ------
    above = sel & (z <= z0)
    below = sel & (z >= z0)
    axL.axhspan(0.0, 0.30, color=C_CORAL_L, alpha=0.55, lw=0)      # skin (Step A)
    axL.axhspan(0.80, 2.40, color=C_GRID, alpha=0.20, lw=0)        # sensors
    axL.plot(Tm[above], z[above], color=C_A17, lw=2.2, zorder=3)
    axL.plot(Tm[below], z[below], color=C_TEAL, lw=2.2, zorder=3)
    axL.plot([Tm[i0]], [z0], "o", color=C_CHAR, ms=6, zorder=4)
    axL.invert_yaxis()
    fmt_axis(axL, xlabel=r"$\langle T\rangle$  (K)", ylabel="depth  (m)",
             title="(a)  one converged solve")
    handles = [
        Line2D([0], [0], color=C_A17, lw=2.2, label="time-stepped (Step A)"),
        Line2D([0], [0], color=C_TEAL, lw=2.2, label="reconstructed (Step B)"),
        Line2D([0], [0], marker="o", color="none", markerfacecolor=C_CHAR,
               markersize=6, label=r"anchor $z_0$"),
        Patch(facecolor=C_CORAL_L, alpha=0.55, label="skin"),
        Patch(facecolor=C_GRID, alpha=0.20, label="sensors"),
    ]
    axL.legend(handles=handles, frameon=True, edgecolor=C_GRID, fontsize=6.5,
               loc="lower left")

    # (b) the constant-flux invariant, shown as deviation from Q_b ---------
    # A bare flux-vs-depth line hides how flat "flat" is; plotting the
    # percent deviation makes the invariant quantitative: large in the
    # rectification zone, inside +-1% of Q_b at and below the anchor.
    dev = (total / Qb - 1.0) * 100.0
    # mask the top cells whose rectified flux is off scale by an order of
    # magnitude; otherwise matplotlib draws a spurious line across z=0
    dev_plot = dev.copy()
    dev_plot[np.abs(dev_plot) > 100.0] = np.nan
    axR.axhspan(0.0, 0.30, color=C_CORAL_L, alpha=0.55, lw=0)      # skin (Step A)
    axR.axvspan(-1.0, 1.0, color=C_TEAL, alpha=0.14, lw=0)         # +-1% band
    axR.axvline(0.0, color=C_DIM, ls="--", lw=1.2)
    axR.plot(dev_plot[sel], z[sel], color=C_TEAL, lw=2.2, zorder=3)
    axR.plot([dev[i0]], [z0], "o", color=C_CHAR, ms=6, zorder=4)
    axR.invert_yaxis()
    axR.set_xlim(-4, 14)
    fmt_axis(axR, xlabel=r"flux deviation from $Q_b$  (%)", ylabel="",
             title=r"(b)  the invariant, quantified")
    handles_r = [
        Line2D([0], [0], color=C_TEAL, lw=2.2,
               label=r"$\langle$flux$\rangle/Q_b - 1$"),
        Patch(facecolor=C_TEAL, alpha=0.14, label=r"$\pm1\%$ of $Q_b$"),
        Line2D([0], [0], marker="o", color="none", markerfacecolor=C_CHAR,
               markersize=6, label=r"anchor $z_0$"),
    ]
    axR.legend(handles=handles_r, frameon=True, edgecolor=C_GRID,
               fontsize=6.5, loc="lower right")
    print(f"  surface deviation {dev[0]:+.1f}%, at anchor {dev[i0]:+.2f}%, "
          f"max below anchor {np.abs(dev[(z >= z0) & sel]).max():+.2f}%")

    OUT.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT / "fig_anchor_anatomy.pdf")
    plt.close(fig)
    print("wrote", OUT / "fig_anchor_anatomy.pdf")


if __name__ == "__main__":
    main()
