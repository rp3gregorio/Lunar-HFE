"""Why the anchor sits at 0.55 m (guidebook, slope-method chapter).

Two panels from a real Apollo 17 solve:
 (a) the diurnal temperature amplitude fading with depth, and
 (b) the rectified-flux correction u_rect as a percentage of Q_b.
Both collapse below the daily skin, which is why the production anchor is placed
deep (0.55 m) rather than at the cheap-but-biased shallow stage (0.25 m).
Real solver output only (no invented numbers); house style module.
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
                                  C_CHAR, C_CORAL_L, fmt_axis, legend_below)

OUT = pathlib.Path(__file__).resolve().parents[2] / "results" / "figures"
Z_STAGE1 = 0.25                                   # shallow (stage-1) anchor


def main():
    site = SITES["A17"]
    kd = 7.160e-3
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
    Tcyc = eq.out.T                                   # (N_z, N_t) periodic cycle
    amp = 0.5 * (Tcyc.max(axis=1) - Tcyc.min(axis=1))  # diurnal amplitude [K]
    Qb = site["Q_BASAL"]
    urect_pct = np.abs(_rectified_flux(Tcyc, z, kf)) / Qb * 100.0

    for zq in (0.05, Z_STAGE1, EQ_Z_ANCHOR):
        i = int(np.argmin(np.abs(z - zq)))
        print(f"  z={z[i]:.2f} m   amp={amp[i]:8.3g} K   |u_rect|={urect_pct[i]:7.3g} % of Q_b")

    sel = z <= 1.0
    fig, (axL, axR) = plt.subplots(1, 2, figsize=(JGR_HALF, 3.2),
                                   constrained_layout=True)
    for ax in (axL, axR):
        ax.axvspan(0.0, 0.30, color=C_CORAL_L, alpha=0.5, lw=0)     # diurnal skin
        ax.axvline(Z_STAGE1, color=C_DIM, ls=":", lw=1.3)
        ax.axvline(EQ_Z_ANCHOR, color=C_CHAR, ls="--", lw=1.3)
        ax.set_yscale("log")

    axL.plot(z[sel], amp[sel], color=C_A17, lw=2.0, zorder=3)
    fmt_axis(axL, xlabel="depth  (m)", ylabel="diurnal amplitude  (K)",
             title="(a)  the daily wave fades")
    axR.plot(z[sel], urect_pct[sel], color=C_TEAL, lw=2.0, zorder=3)
    fmt_axis(axR, xlabel="depth  (m)", ylabel=r"$|u_{\rm rect}|$  (% of $Q_b$)",
             title="(b)  so does the rectification")

    handles = [
        Line2D([0], [0], color=C_DIM, ls=":", lw=1.3,
               label="stage-1 anchor (0.25 m)"),
        Line2D([0], [0], color=C_CHAR, ls="--", lw=1.3,
               label="production anchor (0.55 m)"),
        Patch(facecolor=C_CORAL_L, alpha=0.5, label="diurnal skin"),
    ]
    legend_below(fig, handles, [h.get_label() for h in handles])

    OUT.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT / "fig_anchor_placement.pdf")
    plt.close(fig)
    print("wrote", OUT / "fig_anchor_placement.pdf")


if __name__ == "__main__":
    main()
