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

OUT = pathlib.Path(__file__).resolve().parents[2] / "results" / "figures"


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

    # (a) profile anatomy ---------------------------------------------------
    axL.axhspan(0.0, 0.30, color=C_CORAL_L, alpha=0.55, lw=0)      # skin (Step A)
    axL.axhspan(0.80, 2.40, color=C_GRID, alpha=0.20, lw=0)        # sensors
    axL.plot(Tm[sel], z[sel], color=C_A17, lw=2.0, zorder=3)
    axL.plot([Tm[i0]], [z0], "o", color=C_CHAR, ms=6, zorder=4)
    axL.invert_yaxis()
    fmt_axis(axL, xlabel=r"$\langle T\rangle$  (K)", ylabel="depth  (m)",
             title="(a)  one converged solve")
    handles = [
        Line2D([0], [0], color=C_A17, lw=2, label=r"$\langle T\rangle(z)$"),
        Line2D([0], [0], marker="o", color="none", markerfacecolor=C_CHAR,
               markersize=6, label=r"anchor $z_0$"),
        Patch(facecolor=C_CORAL_L, alpha=0.55, label="skin (Step A)"),
        Patch(facecolor=C_GRID, alpha=0.20, label="sensors"),
    ]
    axL.legend(handles=handles, frameon=True, edgecolor=C_GRID, fontsize=6.5,
               loc="lower left")

    # (b) the constant-flux foundation -------------------------------------
    axR.axhspan(0.0, 0.30, color=C_CORAL_L, alpha=0.55, lw=0)      # skin (Step A)
    axR.plot(total[sel] * 1e3, z[sel], color=C_TEAL, lw=2.0, zorder=3,
             label="cycle-mean flux")
    axR.axvline(Qb * 1e3, color=C_DIM, ls="--", lw=1.2, label=r"$Q_b$")
    axR.plot([total[i0] * 1e3], [z0], "o", color=C_CHAR, ms=6, zorder=4)
    axR.invert_yaxis()
    axR.set_xlim(0, Qb * 1e3 * 1.6)
    fmt_axis(axR, xlabel=r"flux  (mW m$^{-2}$)", ylabel="",
             title=r"(b)  below the skin, flux $=Q_b$")
    axR.legend(frameon=True, edgecolor=C_GRID, fontsize=6.5, loc="lower right")

    OUT.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT / "fig_anchor_anatomy.pdf")
    plt.close(fig)
    print("wrote", OUT / "fig_anchor_anatomy.pdf")


if __name__ == "__main__":
    main()
