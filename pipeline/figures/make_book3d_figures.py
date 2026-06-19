#!/usr/bin/env python3
"""High-end teaching figures for the guidebook (docs/guidebook/guidebook.tex).

These elevate the plain schematics into polished, partly-3D figures that
follow the project design system (lunar/plotting/style.py). Each writes a
PDF into results/figures/.

Run:  python pipeline/figures/make_book3d_figures.py
"""
from __future__ import annotations
import json
import pathlib

import numpy as np
import matplotlib.pyplot as plt
from matplotlib import cm

from lunar.config import (SITES, GRID, HAYNE, S0, T_LUNAR, DT_STEP,
                          EQ_Z_ANCHOR, EQ_N_INNER, EQ_MAX_OUTER, EQ_ANCHOR_TOL)
from lunar.grid import make_geometric_grid
from lunar.properties import conductivity_hayne, specific_heat
from lunar.equilibrium import solve_periodic_equilibrium
from lunar.plotting.style import (ANTH_DIVERGE, C_CORAL, C_TEAL, C_FOREST,
                                  C_CHAR, C_DIM, C_GRID, JGR_FULL)

OUT = pathlib.Path(__file__).resolve().parents[2] / "results" / "figures"
OUT.mkdir(parents=True, exist_ok=True)
_RESULTS = pathlib.Path(__file__).resolve().parents[2] / "results" / "kd_retrieval_results.json"


def _kd_star(tag: str, default: float) -> float:
    try:
        d = json.loads(_RESULTS.read_text())
        return float(d[tag]["kd_star"])
    except Exception:
        return default


def _solve_field(site_tag="A17"):
    """Return (z [m], t_days, T(z,t) [K]) for a site's certified steady state."""
    site = SITES[site_tag]
    kd = _kd_star(site_tag, 8.117e-3)
    grid = make_geometric_grid(**GRID)
    N_t = int(T_LUNAR / DT_STEP) + 1
    t = np.linspace(0.0, T_LUNAR, N_t)
    phase = 2.0 * np.pi * t / T_LUNAR
    insol = S0 * np.cos(np.deg2rad(site["lat"])) * np.maximum(0.0, np.cos(phase))

    def k_func(T, z):
        return conductivity_hayne(T, z, Ks=HAYNE["K_S"], Kd=kd, H=HAYNE["H"],
                                  chi=HAYNE["CHI"])

    def cp_func(T):
        return specific_heat(T, model="hayne")

    eq = solve_periodic_equilibrium(
        grid=grid, t=t, insolation=insol,
        albedo=site["albedo"], emissivity=site["emissivity"],
        Q_b=site["Q_BASAL"], K_func=k_func, cp_func=cp_func,
        T_guess=site["T_MEAN_EFF"], z_anchor=EQ_Z_ANCHOR, n_inner=EQ_N_INNER,
        max_outer=EQ_MAX_OUTER, anchor_tol_K=EQ_ANCHOR_TOL,
    )
    return grid.z_mid, t / 86400.0, eq.out.T


def _clean_3d(ax):
    """Apply the design system to a 3D axis: pale panes, light grid, charcoal text."""
    for axis in (ax.xaxis, ax.yaxis, ax.zaxis):
        axis.pane.set_facecolor("white")
        axis.pane.set_edgecolor(C_GRID)
        axis.pane.set_alpha(1.0)
        axis._axinfo["grid"].update(color=C_GRID, linewidth=0.6)
        axis.line.set_color(C_DIM)
        axis.line.set_linewidth(0.8)
        axis.label.set_color(C_CHAR)
        axis.set_tick_params(colors=C_DIM, labelsize=8)


def fig_thermalwave_3d():
    """3D surface T(z,t): the daily wave on top of the slow deep mean."""
    z, t_days, T = _solve_field("A17")
    zmax = 0.9                                   # show the wave-bearing layer
    sel = z <= zmax
    z_s = z[sel]
    Ts = T[sel]
    # downsample time for a smooth, light surface
    step = 6
    t_d = t_days[::step]
    Ts = Ts[:, ::step]
    TT, ZZ = np.meshgrid(t_d, z_s)               # (N_z, N_t)

    fig = plt.figure(figsize=(JGR_FULL, 5.0))
    ax = fig.add_subplot(111, projection="3d", computed_zorder=False)

    norm = plt.Normalize(Ts.min(), Ts.max())
    ax.plot_surface(
        TT, ZZ, Ts, cmap=ANTH_DIVERGE, norm=norm,
        rcount=len(z_s), ccount=len(t_d),
        linewidth=0, antialiased=True, alpha=0.98, shade=True)

    ax.set_xlabel("time over one lunation  [days]", labelpad=10)
    ax.set_ylabel("depth  $z$  [m]", labelpad=10)
    ax.set_ylim(z_s.max(), z_s.min())            # surface at the front
    ax.set_zlim(Ts.min() - 5, Ts.max() + 5)
    ax.set_xticks([0, 10, 20, 29])
    ax.set_yticks([0.0, 0.3, 0.6, 0.9])
    ax.set_zticks([])                            # temperature read from colorbar
    ax.view_init(elev=18, azim=-62)
    ax.set_box_aspect((1.55, 1.0, 0.72), zoom=1.04)
    _clean_3d(ax)
    # teaching annotations (2D overlay, never overlap the surface)
    ax.text2D(0.015, 0.93, "surface: ~250 K swing every lunation",
              transform=ax.transAxes, fontsize=9, color=C_CORAL,
              fontweight="bold")
    ax.text2D(0.015, 0.87, "below ~0.5 m: nearly constant (the deep mean)",
              transform=ax.transAxes, fontsize=9, color=C_TEAL)

    fig.suptitle("The thermal wave: a fierce daily swing at the surface that "
                 "dies out with depth", x=0.06, y=0.98, ha="left",
                 fontsize=11.5, fontweight="bold", color=C_CHAR)

    cb = fig.colorbar(cm.ScalarMappable(norm=norm, cmap=ANTH_DIVERGE),
                      ax=ax, shrink=0.5, aspect=18, pad=0.0, location="right")
    cb.set_label("temperature  [K]", fontsize=9, color=C_CHAR)
    cb.ax.tick_params(labelsize=8, colors=C_DIM)
    cb.outline.set_edgecolor(C_GRID)

    out = OUT / "fig_book_thermalwave3d.pdf"
    fig.savefig(out, bbox_inches="tight", pad_inches=0.12)
    plt.close(fig)
    print("  ->", out.name)


def fig_skin_waterfall_3d():
    """3D waterfall: T(t) at increasing depths — the daily swing shrinks."""
    z, t_days, T = _solve_field("A17")
    depths = [0.0, 0.025, 0.05, 0.10, 0.20, 0.40, 0.80]
    idx = [int(np.argmin(np.abs(z - d))) for d in depths]
    cmap = ANTH_DIVERGE
    cols = [cmap(v) for v in np.linspace(0.85, 0.15, len(idx))]

    fig = plt.figure(figsize=(JGR_FULL, 4.8))
    ax = fig.add_subplot(111, projection="3d", computed_zorder=False)
    from matplotlib.lines import Line2D
    handles = []
    for k, (i, d, c) in enumerate(zip(idx, depths, cols)):
        y = np.full_like(t_days, d)
        Ti = T[i]
        ax.plot(t_days, y, Ti, color=c, lw=2.0, zorder=10 - k)
        # faint vertical ribbon down to the floor for a depth cue
        ax.add_collection3d(
            plt.matplotlib.collections.PolyCollection(
                [np.column_stack([np.r_[t_days, t_days[::-1]],
                                  np.r_[Ti, np.full_like(Ti, Ti.min())]])],
                facecolors=[c], alpha=0.09),
            zs=d, zdir="y")
        label = "surface" if d == 0 else f"{int(round(d*100))} cm deep"
        handles.append(Line2D([0], [0], color=c, lw=2.4, label=label))
    leg = ax.legend(handles=handles, loc="upper left",
                    bbox_to_anchor=(0.0, 0.93), frameon=True, fontsize=8.5,
                    title="depth", title_fontsize=9, borderpad=0.6,
                    handlelength=1.6, labelspacing=0.35)
    leg.get_frame().set_edgecolor(C_GRID)
    leg.get_title().set_color(C_CHAR)

    ax.set_xlabel("time over one lunation  [days]", labelpad=10)
    ax.set_ylabel("depth  $z$  [m]", labelpad=10)
    ax.set_zlabel("temperature  [K]", labelpad=8)
    ax.set_xticks([0, 10, 20, 29])
    ax.set_yticks([0.0, 0.4, 0.8])
    ax.set_zticks([150, 250, 350])
    ax.set_ylim(0.85, -0.03)
    ax.view_init(elev=20, azim=-66)
    ax.set_box_aspect((1.5, 1.0, 0.7), zoom=1.03)
    ax.zaxis.set_rotate_label(False)
    ax.zaxis.label.set_rotation(90)
    _clean_3d(ax)
    fig.suptitle("Same wave, deeper down: the daily swing collapses within "
                 "the first half-metre", x=0.06, y=0.98, ha="left",
                 fontsize=11.5, fontweight="bold", color=C_CHAR)
    out = OUT / "fig_book_skinwaterfall3d.pdf"
    fig.savefig(out, bbox_inches="tight", pad_inches=0.12)
    plt.close(fig)
    print("  ->", out.name)


def main():
    print("Building high-end 3D book figures:")
    fig_thermalwave_3d()
    fig_skin_waterfall_3d()
    print("done.")


if __name__ == "__main__":
    main()
