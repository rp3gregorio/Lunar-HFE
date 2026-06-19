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


_FIELD_CACHE: dict = {}


def _solve_field(site_tag="A17"):
    """Return (z [m], t_days, T(z,t) [K]) for a site's certified steady state."""
    if site_tag in _FIELD_CACHE:
        return _FIELD_CACHE[site_tag]
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
    res = (grid.z_mid, t / 86400.0, eq.out.T)
    _FIELD_CACHE[site_tag] = res
    return res


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


def fig_lunar_forcing_3d():
    """3D illustration: the Sun drives a day/night cycle at the HFE borehole."""
    C_SUN = "#D9952B"
    fig = plt.figure(figsize=(JGR_FULL, 4.7))
    ax = fig.add_subplot(111, projection="3d", computed_zorder=False)

    # the Moon (unit sphere); subsolar direction is +x
    u = np.linspace(0, 2 * np.pi, 160)
    v = np.linspace(0, np.pi, 90)
    x = np.outer(np.cos(u), np.sin(v))
    y = np.outer(np.sin(u), np.sin(v))
    z = np.outer(np.ones_like(u), np.cos(v))
    tcol = (x + 1.0) / 2.0                          # night(-x)=0 cold, day(+x)=1 hot
    ax.plot_surface(x, y, z, facecolors=ANTH_DIVERGE(tcol),
                    rstride=1, cstride=1, linewidth=0, antialiased=True,
                    shade=False, zorder=1)

    # terminator (the x=0 great circle: day/night boundary)
    th = np.linspace(0, 2 * np.pi, 160)
    ax.plot(np.zeros_like(th), np.cos(th), np.sin(th),
            color=C_CHAR, lw=1.1, ls=(0, (4, 3)), zorder=6)

    # incoming sunlight: parallel rays striking the day side
    for yy, zz in [(-0.55, 0.55), (0.0, 0.75), (0.55, 0.45),
                   (0.0, -0.45), (-0.5, -0.15), (0.5, 0.0)]:
        ax.quiver(1.85, yy, zz, -1.0, 0.0, 0.0, color=C_SUN, lw=1.7,
                  arrow_length_ratio=0.16, length=0.62, zorder=8)
    ax.text(1.55, 0.15, 1.18, "sunlight  $S_0$", color=C_SUN, fontsize=10,
            fontweight="bold", ha="center")

    # the HFE borehole site (lat 26 N, on the day side) + a probe stick inward
    lat, lon = np.deg2rad(26.0), np.deg2rad(38.0)
    sx = np.cos(lat) * np.cos(lon)
    sy = np.cos(lat) * np.sin(lon)
    sz = np.sin(lat)
    ax.plot([sx, sx * 0.8], [sy, sy * 0.8], [sz, sz * 0.8],
            color=C_CHAR, lw=2.4, zorder=10)
    ax.scatter([sx], [sy], [sz], color=C_FOREST, s=44, depthshade=False,
               edgecolor="white", linewidth=0.8, zorder=11)
    ax.text(sx * 1.25, sy * 1.25, sz * 1.35, "HFE\nborehole", color=C_FOREST,
            fontsize=9, fontweight="bold", ha="center", va="bottom")

    # day / night annotations
    ax.text(0.75, 0.55, 1.18, "day side  (~390 K)", color=C_CORAL, fontsize=9,
            fontweight="bold")
    ax.text(-1.25, -0.2, 0.95, "night side  (~100 K)", color=C_TEAL, fontsize=9,
            fontweight="bold")
    ax.set_box_aspect((1, 1, 1), zoom=1.25)
    ax.set_xlim(-1.1, 1.5); ax.set_ylim(-1.25, 1.25); ax.set_zlim(-1.1, 1.2)
    ax.view_init(elev=16, azim=-52)
    ax.set_axis_off()
    fig.suptitle("The lunar forcing: one hot day, one cold night, every "
                 "lunation", x=0.06, y=0.97, ha="left",
                 fontsize=11.5, fontweight="bold", color=C_CHAR)
    out = OUT / "fig_book_lunarforcing3d.pdf"
    fig.savefig(out, bbox_inches="tight", pad_inches=0.05)
    plt.close(fig)
    print("  ->", out.name)


def fig_borehole_column_3d():
    """3D cutaway: the HFE probe in the regolith column, real sensor depths,
    the skin / borestem / deep zones, and the certified T(z) profile."""
    from mpl_toolkits.mplot3d.art3d import Poly3DCollection
    from lunar.apollo_helpers import extract_sensor_stability
    z, _, T = _solve_field("A17")
    Tmean = T.mean(axis=1)
    info = extract_sensor_stability("a17", 80.0)
    sd = np.asarray(info["depth_cm_all"], float) / 100.0
    deep = np.asarray(info["deep_mask"], bool)

    ZMAX = 2.45
    W = 1.0                                   # column footprint width
    DP = 0.55                                 # 3D depth (y extent)

    def face(x0, x1, z0, z1, y, color, alpha, ec="none"):
        verts = [[(x0, y, z0), (x1, y, z0), (x1, y, z1), (x0, y, z1)]]
        p = Poly3DCollection(verts, facecolor=color, alpha=alpha,
                             edgecolor=ec, linewidths=0.7)
        ax.add_collection3d(p)

    fig = plt.figure(figsize=(JGR_FULL, 5.4))
    ax = fig.add_subplot(111, projection="3d", computed_zorder=False)

    # regolith block: back/side faces + a top surface, in pale warm grey
    face(0, W, 0, ZMAX, DP, "#EFEAE2", 1.0)                  # back wall
    face(0, 0, 0, ZMAX, DP, "#EFEAE2", 1.0)                  # side wall (x=0 plane via y)
    top = [[(0, 0, 0), (W, 0, 0), (W, DP, 0), (0, DP, 0)]]
    ax.add_collection3d(Poly3DCollection(top, facecolor="#D9C7B6",
                        alpha=1.0, edgecolor="#B9A88E", linewidths=0.8))
    # depth-zone bands on the front face (y=0)
    face(0, W, 0.0, 0.40, 0.0, C_CORAL, 0.16)               # skin (daily wave)
    face(0, W, 0.0, 0.80, 0.0, C_DIM, 0.0, ec=C_DIM)        # borestem outline
    for zz in np.linspace(0.05, 0.78, 8):                   # borestem hatch
        ax.plot([0, W], [0, 0], [zz, zz], color=C_DIM, lw=0.4, alpha=0.45)
    face(0, W, 0.80, ZMAX, 0.0, C_TEAL, 0.13)               # deep retrieval zone
    face(0, W, 0, ZMAX, 0.0, "#000000", 0.0, ec=C_DIM)      # front frame

    # the probe + sensors at real depths
    ax.plot([0.5, 0.5], [0, 0], [0, ZMAX], color=C_CHAR, lw=2.6, zorder=8)
    ax.scatter([0.5] * (~deep).sum(), [0] * (~deep).sum(), sd[~deep],
               facecolor="white", edgecolor=C_DIM, s=26, lw=1.0, zorder=9)
    ax.scatter([0.5] * deep.sum(), [0] * deep.sum(), sd[deep],
               color=C_FOREST, edgecolor="white", s=34, lw=0.8, zorder=10)

    # certified T(z) profile, drawn to the right of the column (T -> x offset)
    sel = z <= 2.3
    xT = 1.20 + 0.85 * (Tmean[sel] - Tmean[sel].min()) / np.ptp(Tmean[sel])
    ax.plot(xT, np.zeros(sel.sum()), z[sel], color=C_CORAL, lw=2.2, zorder=7)
    ax.text(2.15, 0, 1.1, r"mean $T(z)$", color=C_CORAL, fontsize=8.5,
            fontweight="bold")

    # labels
    ax.text(0.5, 0, -0.16, "surface", color=C_CHAR, fontsize=9, ha="center",
            fontweight="bold")
    ax.text(1.04, 0, 0.22, "skin: daily wave", color=C_CORAL, fontsize=8.5,
            ha="left", va="center")
    ax.text(1.04, 0, 0.62, "borestem excluded\n($z<80$ cm)", color=C_DIM,
            fontsize=8, ha="left", va="center")
    ax.text(1.04, 0, 1.7, "deep sensors $\\rightarrow K_d$", color=C_FOREST,
            fontsize=8.5, ha="left", va="center", fontweight="bold")

    ax.set_zlim(ZMAX + 0.05, -0.25)          # surface at the top
    ax.set_xlim(-0.05, 2.3); ax.set_ylim(0, DP + 0.1)
    ax.set_zticks([0, 0.5, 1.0, 1.5, 2.0])
    ax.set_zlabel("depth  $z$  [m]", labelpad=6)
    ax.set_xticks([]); ax.set_yticks([])
    ax.xaxis.line.set_color("none"); ax.yaxis.line.set_color("none")
    for axis in (ax.xaxis, ax.yaxis, ax.zaxis):
        axis.pane.set_visible(False)
    ax.zaxis.line.set_color(C_DIM)
    ax.zaxis.set_tick_params(colors=C_DIM, labelsize=8)
    ax.zaxis.label.set_color(C_CHAR)
    ax.view_init(elev=8, azim=-60)
    ax.set_box_aspect((1.6, 0.7, 1.7), zoom=1.18)
    fig.suptitle("Inside the borehole: which sensors become data, and why",
                 x=0.06, y=0.97, ha="left", fontsize=11.5, fontweight="bold",
                 color=C_CHAR)
    out = OUT / "fig_book_borehole3d.pdf"
    fig.savefig(out, bbox_inches="tight", pad_inches=0.1)
    plt.close(fig)
    print("  ->", out.name)


def fig_grid_3d():
    """3D illustration of the geometric depth grid: mm at top, decimetres below."""
    from mpl_toolkits.mplot3d.art3d import Poly3DCollection
    from lunar.plotting.style import ANTH_SEQ
    grid = make_geometric_grid(**GRID)
    zf = np.asarray(grid.z_face, float)
    dz = np.asarray(grid.dz, float)
    ZMAX = 2.5
    nshow = int(np.searchsorted(zf, ZMAX))
    W, DP = 1.0, 0.5
    norm = plt.Normalize(np.log10(dz[:nshow].min()), np.log10(dz[:nshow].max()))

    fig = plt.figure(figsize=(JGR_FULL, 5.2))
    ax = fig.add_subplot(111, projection="3d", computed_zorder=False)
    for i in range(nshow):
        z0, z1 = zf[i], zf[i + 1]
        c = ANTH_SEQ(norm(np.log10(dz[i])))
        ax.add_collection3d(Poly3DCollection(   # front face (y=0)
            [[(0, 0, z0), (W, 0, z0), (W, 0, z1), (0, 0, z1)]],
            facecolor=c, edgecolor="white", linewidths=0.35, alpha=0.98))
        ax.add_collection3d(Poly3DCollection(   # side face (x=W) for 3D depth
            [[(W, 0, z0), (W, DP, z0), (W, DP, z1), (W, 0, z1)]],
            facecolor=c, edgecolor="white", linewidths=0.25, alpha=0.7))
    ax.add_collection3d(Poly3DCollection(       # top surface
        [[(0, 0, 0), (W, 0, 0), (W, DP, 0), (0, DP, 0)]],
        facecolor="#D9C7B6", edgecolor="#B9A88E", linewidths=0.6))

    # short value callouts just right of the column (kept clear of the depth axis)
    i1 = int(np.searchsorted(zf, 1.0))
    i2 = int(np.searchsorted(zf, 2.0))
    def callout(z, txt):
        ax.text(1.12, 0, z, txt, color=C_CHAR, fontsize=8.5, ha="left", va="center")
        ax.plot([1.08, 1.01], [0, 0], [z, z], color=C_DIM, lw=0.7)
    callout(0.0, f"{dz[0]*1000:.0f} mm")
    callout(1.0, f"$\\sim${dz[i1]*100:.0f} cm")
    callout(2.0, f"$\\sim${dz[i2]*100:.0f} cm")
    # descriptive notes to the LEFT of the column (empty space; no overlap)
    ax.text(-0.12, 0, 0.16, "fine: resolves\nthe daily wave", color=C_CORAL,
            fontsize=8, ha="right", va="center")
    ax.text(-0.12, 0, 1.9, "coarse: cheap\nwhere $T$ is flat", color=C_TEAL,
            fontsize=8, ha="right", va="center")
    ax.text(-0.12, 0, 1.0, r"each cell $\sim$8% thicker", color=C_DIM,
            fontsize=8, ha="right", va="center", style="italic")

    ax.set_zlim(ZMAX + 0.05, -0.22)             # surface at the top
    ax.set_xlim(-1.35, 1.9); ax.set_ylim(0, DP + 0.1)
    ax.set_zticks([0, 0.5, 1.0, 1.5, 2.0, 2.5])
    ax.set_zlabel("depth  $z$  [m]", labelpad=6)
    ax.set_xticks([]); ax.set_yticks([])
    ax.xaxis.line.set_color("none"); ax.yaxis.line.set_color("none")
    for axis in (ax.xaxis, ax.yaxis, ax.zaxis):
        axis.pane.set_visible(False)
    ax.zaxis.line.set_color(C_DIM)
    ax.zaxis.set_tick_params(colors=C_DIM, labelsize=8)
    ax.zaxis.label.set_color(C_CHAR)
    ax.view_init(elev=10, azim=-62)
    ax.set_box_aspect((1.7, 0.7, 1.7), zoom=1.16)
    fig.suptitle("The geometric grid: millimetres at the surface, decimetres "
                 "below ($\\sim$69 cells to 5 m)", x=0.06, y=0.97, ha="left",
                 fontsize=11.5, fontweight="bold", color=C_CHAR)
    out = OUT / "fig_book_grid3d.pdf"
    fig.savefig(out, bbox_inches="tight", pad_inches=0.22)
    plt.close(fig)
    print("  ->", out.name)


def main():
    print("Building high-end 3D book figures:")
    fig_lunar_forcing_3d()
    fig_grid_3d()
    fig_borehole_column_3d()
    fig_thermalwave_3d()
    fig_skin_waterfall_3d()
    print("done.")


if __name__ == "__main__":
    main()
