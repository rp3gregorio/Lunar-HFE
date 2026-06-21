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


def fig_thermal_field():
    """2D heatmap of the field T(z,t): a fierce surface swing fading with depth."""
    z, t_days, T = _solve_field("A17")
    sel = z <= 0.9
    fig, ax = plt.subplots(figsize=(JGR_FULL, 3.4))
    im = ax.pcolormesh(t_days, z[sel], T[sel], cmap=ANTH_DIVERGE,
                       shading="gouraud", rasterized=True)
    ax.contour(t_days, z[sel], T[sel], levels=9, colors="white",
               linewidths=0.4, alpha=0.5)
    ax.invert_yaxis()
    ax.set_xlim(0, t_days[-1])
    ax.set_xlabel("time over one lunation  [days]")
    ax.set_ylabel("depth  $z$  [m]")
    ax.set_title("The thermal field $T(z,t)$: a fierce surface swing that fades "
                 "within tens of centimetres", loc="left", fontsize=10.5,
                 color=C_CHAR)
    for s in ax.spines.values():
        s.set_color(C_CHAR)
    cb = fig.colorbar(im, ax=ax, pad=0.015, aspect=20)
    cb.set_label("temperature  [K]", fontsize=9)
    cb.ax.tick_params(labelsize=8, colors=C_DIM)
    cb.outline.set_edgecolor(C_GRID)
    fig.savefig(OUT / "fig_book_thermalfield.pdf", bbox_inches="tight",
                pad_inches=0.06)
    plt.close(fig)
    print("  -> fig_book_thermalfield.pdf")


def fig_kTz_heatmap():
    """K(T, z) heatmap from the actual Hayne function at the retrieved K_d* = 4.58.
    Shows the deep asymptote K -> K_d and the T^3 radiative rise."""
    from lunar.properties import conductivity_hayne
    from lunar.config import HAYNE
    Kd = 4.58e-3              # A15 retrieved
    T_grid = np.linspace(100, 390, 240)
    z_grid = np.linspace(0.0, 2.0, 200)
    TT, ZZ = np.meshgrid(T_grid, z_grid)
    K = conductivity_hayne(TT, ZZ, Ks=HAYNE['K_S'], Kd=Kd, H=HAYNE['H'],
                           chi=HAYNE['CHI']) * 1e3            # mW/(m K)

    fig, ax = plt.subplots(figsize=(JGR_FULL, 3.8))
    im = ax.pcolormesh(T_grid, z_grid, K, cmap=ANTH_DIVERGE,
                       shading="gouraud", rasterized=True)
    cs = ax.contour(T_grid, z_grid, K, levels=[1, 2, 3, 4, 5, 7, 10, 15],
                    colors="white", linewidths=0.5, alpha=0.7)
    ax.clabel(cs, inline=True, fontsize=7, fmt="%.0f", colors="#FFFFFF")
    ax.invert_yaxis()
    ax.set_xlabel("temperature  $T$  [K]")
    ax.set_ylabel("depth  $z$  [m]")
    ax.set_title(r"$K(T,z)$ at the retrieved Apollo 15 $K_d^*=4.58$ "
                 r"mW m$^{-1}$ K$^{-1}$ — Hayne (2017) form",
                 loc="left", fontsize=10.5, color=C_CHAR)

    # mark the deep asymptote K -> K_d
    ax.axhline(0.30, color=C_TEAL, lw=0.9, ls="--")
    ax.text(108, 0.28, r"below the $H$-folding ($z \sim 5H \approx 30$ cm):  $K \to K_d$",
            color=C_TEAL, fontsize=8, va="bottom")
    # mark the radiative rise
    ax.annotate(r"radiative $T^3$ rise", xy=(380, 1.7), xytext=(220, 1.7),
                fontsize=8, color=C_CORAL, ha="left", va="center",
                arrowprops=dict(arrowstyle="->", color=C_CORAL, lw=0.8))
    for s in ax.spines.values():
        s.set_color(C_CHAR)
    cb = fig.colorbar(im, ax=ax, pad=0.015, aspect=20)
    cb.set_label(r"$K$  [mW m$^{-1}$ K$^{-1}$]", fontsize=9)
    cb.ax.tick_params(labelsize=8, colors=C_DIM)
    cb.outline.set_edgecolor(C_GRID)
    fig.savefig(OUT / "fig_book_kTz.pdf", bbox_inches="tight", pad_inches=0.06)
    plt.close(fig)
    print("  -> fig_book_kTz.pdf")


def fig_skin_wave():
    """2D lines: T(t) at increasing depths — the daily swing collapses."""
    z, t_days, T = _solve_field("A17")
    depths = [0.0, 0.025, 0.05, 0.10, 0.20, 0.40, 0.80]
    idx = [int(np.argmin(np.abs(z - d))) for d in depths]
    cols = [ANTH_DIVERGE(v) for v in np.linspace(0.85, 0.15, len(depths))]
    fig, ax = plt.subplots(figsize=(JGR_FULL, 3.7))
    for i, d, c in zip(idx, depths, cols):
        lab = "surface" if d == 0 else f"{int(round(d*100))} cm"
        ax.plot(t_days, T[i], color=c, lw=2.0, label=lab)
    ax.set_xlim(0, t_days[-1])
    ax.set_xlabel("time over one lunation  [days]")
    ax.set_ylabel("temperature  [K]")
    ax.set_title("Same wave, deeper down: the daily swing collapses within the "
                 "first half-metre", loc="left", fontsize=10.5, color=C_CHAR)
    ax.grid(color=C_GRID, lw=0.5); ax.set_axisbelow(True)
    for s in ax.spines.values():
        s.set_color(C_CHAR)
    leg = ax.legend(title="depth", loc="center left", bbox_to_anchor=(1.01, 0.5),
                    frameon=True, edgecolor=C_GRID, framealpha=0.97, fontsize=8.5,
                    title_fontsize=9, handlelength=1.5, labelspacing=0.4)
    leg.get_title().set_color(C_CHAR)
    fig.savefig(OUT / "fig_book_skinwave.pdf", bbox_inches="tight",
                pad_inches=0.06)
    plt.close(fig)
    print("  -> fig_book_skinwave.pdf")


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


def fig_fourier():
    """2D interpretation of Fourier's law: the gradient IS a slope; flux follows it."""
    from lunar.plotting.style import fmt_axis
    fig, (axA, axB) = plt.subplots(1, 2, figsize=(JGR_FULL, 3.6),
                                   gridspec_kw={"width_ratios": [0.62, 1.0]})
    # (a) the physical picture: a column hot at the surface, cold below
    grad = np.linspace(1, 0, 200).reshape(-1, 1)
    axA.imshow(grad, extent=[0, 1, 0, 1], aspect="auto", cmap=ANTH_DIVERGE,
               origin="upper")
    for yc in (0.72, 0.5, 0.28):
        axA.annotate("", xy=(0.55, yc - 0.1), xytext=(0.55, yc + 0.1),
                     arrowprops=dict(arrowstyle="-|>", color=C_CHAR, lw=2.2))
    axA.text(0.5, 1.05, "hot surface", ha="center", color=C_CORAL, fontsize=9,
             fontweight="bold")
    axA.text(0.5, -0.05, "cold subsurface", ha="center", va="top", color=C_TEAL,
             fontsize=9, fontweight="bold")
    axA.text(0.2, 0.5, "heat\nflux $q$", ha="center", va="center", fontsize=8.5,
             color=C_CHAR)
    axA.set_xlim(0, 1); axA.set_ylim(-0.02, 1.02); axA.axis("off")

    # (b) the same thing as the equation: T vs depth -- the slope is dT/dz
    z = np.linspace(0, 1.6, 200)
    T = 250 + 110 * np.exp(-z / 0.35)            # hot surface, cooling with depth
    axB.plot(T, z, color=C_CHAR, lw=2.4, zorder=3)
    axB.set_ylim(1.6, -0.02)                     # depth downward
    axB.set_xlim(240, 375)
    for z0, lab, col, tx in [(0.16, "steep slope\n$\\Rightarrow$ large flux",
                              C_CORAL, 250),
                             (0.95, "gentle slope\n$\\Rightarrow$ small flux",
                              C_TEAL, 300)]:
        T0 = 250 + 110 * np.exp(-z0 / 0.35)
        slope = -110 / 0.35 * np.exp(-z0 / 0.35)
        dz = 0.24
        axB.plot([T0, T0 + slope * dz], [z0, z0 + dz], color=col, lw=2.4, zorder=4)
        axB.plot([T0, T0 + slope * dz, T0 + slope * dz], [z0, z0, z0 + dz],
                 color=col, lw=0.9, ls=(0, (2, 2)), zorder=4)
        axB.annotate(lab, xy=(T0 + slope * dz, z0 + dz),
                     xytext=(tx, z0 + 0.42), fontsize=8, color=col,
                     ha="center", va="center",
                     arrowprops=dict(arrowstyle="->", color=col, lw=0.8))
    fmt_axis(axB, xlabel="temperature  $T$  [K]", ylabel="depth  $z$")
    axB.set_title(r"(b) the slope of this curve is $\partial T/\partial z$",
                  loc="left", fontsize=9.5, color=C_CHAR)
    fig.suptitle(r"Fourier's law $q=-K\,\partial T/\partial z$: the flux follows "
                 "the steepness of the temperature curve", x=0.02, y=1.02,
                 ha="left", fontsize=11, fontweight="bold", color=C_CHAR)
    fig.savefig(OUT / "fig_book_fourier.pdf", bbox_inches="tight", pad_inches=0.06)
    plt.close(fig)
    print("  -> fig_book_fourier.pdf")


def fig_heateq_cv_3d():
    """3D interpretation of the heat equation: storage = flux in - flux out."""
    from mpl_toolkits.mplot3d.art3d import Poly3DCollection
    fig = plt.figure(figsize=(JGR_FULL, 4.2))
    ax = fig.add_subplot(111, projection="3d", computed_zorder=False)

    def cube(x0, x1, y0, y1, z0, z1, fc, alpha, ec=C_CHAR):
        f = [
            [(x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0)],
            [(x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)],
            [(x0, y0, z0), (x1, y0, z0), (x1, y0, z1), (x0, y0, z1)],
            [(x0, y1, z0), (x1, y1, z0), (x1, y1, z1), (x0, y1, z1)],
            [(x0, y0, z0), (x0, y1, z0), (x0, y1, z1), (x0, y0, z1)],
            [(x1, y0, z0), (x1, y1, z0), (x1, y1, z1), (x1, y0, z1)],
        ]
        ax.add_collection3d(Poly3DCollection(f, facecolor=fc, edgecolor=ec,
                            lw=0.9, alpha=alpha, zorder=4))
    cube(0, 1, 0, 1, 0, 1, C_CORAL, 0.22)        # one regolith cell (warming)
    # short flux arrows sitting ON the faces (in on top, out at the base)
    ax.quiver(0.5, 0.5, 1.5, 0, 0, -0.44, color=C_TEAL, lw=3.0,
              arrow_length_ratio=0.4, zorder=6)
    ax.quiver(0.5, 0.5, -0.04, 0, 0, -0.4, color=C_TEAL, lw=2.0,
              arrow_length_ratio=0.4, zorder=6)
    # labels tie each arrow to a q-term in the equation
    ax.text2D(0.5, 0.95, r"heat in:  $q\left(z-\frac{\Delta z}{2}\right)$  (larger)",
              transform=ax.transAxes, ha="center", color=C_TEAL, fontsize=9.5,
              fontweight="bold")
    ax.text2D(0.5, 0.135, r"heat out:  $q\left(z+\frac{\Delta z}{2}\right)$  (smaller)",
              transform=ax.transAxes, ha="center", color=C_TEAL, fontsize=9.5)
    # the equation gets its own clear footer band, centred and well clear of the cube
    fig.text(0.5, 0.02,
             r"$\rho c_p\,\frac{\partial T}{\partial t}"
             r"=-\frac{\partial q}{\partial z}"
             r"=\frac{\partial}{\partial z}\left(K\frac{\partial T}{\partial z}\right)$",
             ha="center", fontsize=13, color=C_CHAR)
    ax.set_xlim(0, 1.0); ax.set_ylim(0, 1.0); ax.set_zlim(-0.5, 1.5)
    ax.view_init(elev=13, azim=-56)
    ax.set_box_aspect((1, 1, 1.4), zoom=1.05)
    ax.set_axis_off()
    fig.suptitle(r"The heat equation is bookkeeping:  stored = in $-$ out",
                 x=0.5, y=1.0, ha="center", fontsize=11.5, fontweight="bold",
                 color=C_CHAR)
    fig.savefig(OUT / "fig_book_heateq.pdf", bbox_inches="tight", pad_inches=0.05)
    plt.close(fig)
    print("  -> fig_book_heateq.pdf")


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
    # heateq + grid were re-authored as SVG (pipeline/figures/svg -> make_svg_figures).
    fig_fourier()               # 2D equation interpretation (contains a T(z) plot)
    fig_thermal_field()         # 2D data heatmap
    fig_skin_wave()             # 2D data lines
    fig_kTz_heatmap()           # 2D Hayne K(T,z) heatmap
    print("done.")


if __name__ == "__main__":
    main()
