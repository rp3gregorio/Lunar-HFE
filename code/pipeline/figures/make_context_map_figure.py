#!/usr/bin/env python3
"""Context figure for the Apollo Heat-Flow Experiment landing sites.

Four panels: the top row places the two sites on two GLOBAL data layers —
(a) LOLA topography (shaded relief) and (b) the modeled mean surface
temperature — and the bottom row zooms into each borehole on LOLA shaded
relief so the local terrain (Apennine front at Apollo 15, Taurus-Littrow
massifs at Apollo 17) reads directly.

Data
  figures/moon_global.png          Clementine albedo (fallback basemap)
  aogs/data/lola/ldem_16.img       LOLA LDEM, 16 ppd (topography)
  data/lola_relief/{A15,A17}.npy   pre-cut relief crops for the zooms
  results/abstract_mean_surface_T.json  mean skin T vs latitude (real solver)

Writes figures/fig_context_map.pdf.
"""
from __future__ import annotations
import json
import pathlib
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import cm
from matplotlib.image import imread
from matplotlib.lines import Line2D
from matplotlib.patches import Rectangle
from matplotlib.colors import LightSource, Normalize

# Shared design tokens
JGR_FULL = 7.48
C_A15   = "#3D6E4A"
C_A17   = "#B85B3A"
SITE_COLOR = {"A15": C_A15, "A17": C_A17}
C_CHAR  = "#2A2520"
C_DIM   = "#6E6862"
C_GRID  = "#E8E5E0"
C_PAPER = "#FBFAF8"
FS_LABEL = 9.5
FS_TICK  = 8.5
FS_TITLE = 10.5
FS_SITE  = 9.0

plt.rcParams.update({
    "font.family": "serif",
    "font.serif": ["Latin Modern Roman", "Times New Roman", "DejaVu Serif"],
    "mathtext.fontset": "cm",
    "axes.edgecolor": C_DIM,
    "axes.labelcolor": C_CHAR,
    "text.color": C_CHAR,
    "xtick.color": C_CHAR,
    "ytick.color": C_CHAR,
    "axes.linewidth": 0.8,
})

ROOT = pathlib.Path(__file__).resolve().parents[2]
OUT  = ROOT / ".." / "figures"
MOON_PNG = OUT / "moon_global.png"
DEM = ROOT.parent / "aogs" / "data" / "lola" / "ldem_16.img"
MEANT = ROOT / "results" / "abstract_mean_surface_T.json"
RELIEF_DIR = ROOT / "data" / "lola_relief"

from lunar.config import SITES  # single source of truth  # noqa: E402

ZOOM_DLON = 15.0
ZOOM_DLAT = 10.0
TOPO_CMAP = plt.get_cmap("gist_earth")
TEMP_CMAP = plt.get_cmap("inferno")


# ---------------------------------------------------------------------
def _load_topo():
    """Global LOLA topography: (elevation km, hillshaded RGB, vmin, vmax)."""
    dem = np.fromfile(DEM, dtype="<i2").reshape(2880, 5760).astype(float)
    dem = dem[::4, ::4] * 0.5e-3                       # -> 720x1440, km
    vmin, vmax = np.percentile(dem, [1, 99])
    ls = LightSource(azdeg=315, altdeg=45)
    rgb = ls.shade(dem, cmap=TOPO_CMAP, blend_mode="soft", vert_exag=55,
                   dx=1.0, dy=1.0, vmin=vmin, vmax=vmax)
    return dem, rgb, vmin, vmax


def _temp_field():
    """Mean surface-T equirectangular field (K); lat-banded (global values)."""
    d = json.loads(MEANT.read_text())
    lats = np.asarray(d["lat_deg"]); tmean = np.asarray(d["T_mean_K"])
    grid_lat = np.linspace(90, -90, 361)              # rows N->S (origin upper)
    col = np.interp(np.abs(grid_lat), lats, tmean)
    return np.tile(col[:, None], (1, 720)), float(tmean.min()), float(tmean.max())


def _mark_sites(ax, callout=False, rects=False):
    for name, s in SITES.items():
        ax.plot(s["lon"], s["lat"], marker="o", color=SITE_COLOR[name],
                ms=6.5, mec="white", mew=1.2, zorder=5)
        if callout:
            dx = 30 if name == "A17" else -30
            ax.annotate(
                s["label"], xy=(s["lon"], s["lat"]),
                xytext=(s["lon"] + dx, s["lat"] + 26),
                fontsize=FS_SITE, color=C_CHAR, fontweight="bold",
                ha="left" if name == "A17" else "right", va="bottom",
                bbox=dict(boxstyle="round,pad=0.2", facecolor="white",
                          edgecolor=SITE_COLOR[name], linewidth=0.8, alpha=0.95),
                arrowprops=dict(arrowstyle="-", color=SITE_COLOR[name], lw=0.9),
                zorder=6)
        if rects:
            ax.add_patch(Rectangle(
                (s["lon"] - ZOOM_DLON, s["lat"] - ZOOM_DLAT),
                2 * ZOOM_DLON, 2 * ZOOM_DLAT, facecolor="none",
                edgecolor=SITE_COLOR[name], linewidth=0.9,
                linestyle=(0, (4, 2)), alpha=0.9, zorder=4))


def _global_axes(ax):
    for lat in (-60, -30, 0, 30, 60):
        ax.axhline(lat, color="white", lw=0.3, alpha=0.25, zorder=2)
    for lon in range(-150, 151, 30):
        ax.axvline(lon, color="white", lw=0.3, alpha=0.25, zorder=2)
    ax.set_xticks([-180, -90, 0, 90, 180])
    ax.set_xticklabels(["180°W", "90°W", "0°", "90°E", "180°E"], fontsize=FS_TICK)
    ax.set_yticks([-60, 0, 60])
    ax.set_yticklabels(["60°S", "0°", "60°N"], fontsize=FS_TICK)
    ax.set_xlim(-180, 180); ax.set_ylim(-90, 90)


def draw_global_topo(ax):
    dem, rgb, vmin, vmax = _load_topo()
    ax.imshow(rgb, extent=(-180, 180, -90, 90), origin="upper",
              aspect="auto", zorder=1, interpolation="bilinear")
    _global_axes(ax); _mark_sites(ax, callout=True, rects=True)
    ax.set_title("(a)  Topography (LOLA)", fontsize=FS_TITLE,
                 fontweight="bold", pad=4)
    sm = cm.ScalarMappable(norm=Normalize(vmin, vmax), cmap=TOPO_CMAP)
    return sm


def draw_global_temp(ax):
    field, tmin, tmax = _temp_field()
    ax.imshow(field, extent=(-180, 180, -90, 90), origin="upper",
              aspect="auto", zorder=1, cmap=TEMP_CMAP, vmin=tmin, vmax=tmax,
              interpolation="bilinear")
    _global_axes(ax); _mark_sites(ax, callout=False, rects=False)
    ax.set_yticklabels([])                    # same latitude axis as (a)
    ax.set_title("(b)  Mean surface temperature", fontsize=FS_TITLE,
                 fontweight="bold", pad=4)
    return cm.ScalarMappable(norm=Normalize(tmin, tmax), cmap=TEMP_CMAP)


def draw_zoom(ax, site_key, panel):
    """Regional zoom: +/-ZOOM_DLON lon, +/-ZOOM_DLAT lat on LOLA shaded relief."""
    s = SITES[site_key]
    lon0, lat0 = s["lon"], s["lat"]
    extent = (lon0 - ZOOM_DLON, lon0 + ZOOM_DLON,
              lat0 - ZOOM_DLAT, lat0 + ZOOM_DLAT)
    relief = RELIEF_DIR / f"{site_key}.npy"
    if relief.exists():
        dem = np.load(relief)
        shaded = LightSource(azdeg=315, altdeg=30).shade(
            dem, cmap=plt.get_cmap("gray"), blend_mode="soft",
            vert_exag=55, dx=1.0, dy=1.0)
        ax.imshow(shaded, extent=extent, origin="upper", aspect="equal",
                  interpolation="bilinear", zorder=1)
    ax.set_xlim(extent[0], extent[1]); ax.set_ylim(extent[2], extent[3])
    for lat in np.arange(round(extent[2] / 5) * 5, round(extent[3] / 5) * 5 + 1, 5):
        ax.axhline(lat, color="white", lw=0.3, alpha=0.28, zorder=2)
    for lon in np.arange(round(extent[0] / 5) * 5, round(extent[1] / 5) * 5 + 1, 5):
        ax.axvline(lon, color="white", lw=0.3, alpha=0.28, zorder=2)
    ax.plot(lon0, lat0, marker="o", color=SITE_COLOR[site_key], ms=10,
            mec="white", mew=1.5, zorder=5)
    ax.tick_params(labelsize=FS_TICK - 0.5)
    ax.set_xlabel("Longitude (°E)", fontsize=FS_LABEL - 0.5)
    if site_key == "A15":
        ax.set_ylabel("Latitude (°N)", fontsize=FS_LABEL - 0.5)
    ax.set_title(rf"({panel})  {s['label']} "
                 rf"({s['lat']:.1f}$^\circ$N, {s['lon']:.1f}$^\circ$E)",
                 fontsize=FS_TITLE - 0.5, fontweight="bold", pad=4,
                 color=SITE_COLOR[site_key])


def main():
    fig = plt.figure(figsize=(JGR_FULL, 6.0))
    gs = fig.add_gridspec(
        2, 4, width_ratios=[1.0, 0.045, 1.0, 0.045],
        height_ratios=[1.0, 1.18],
        left=0.06, right=0.925, top=0.93, bottom=0.12,
        hspace=0.42, wspace=0.16)
    ax_topo = fig.add_subplot(gs[0, 0]); cax_topo = fig.add_subplot(gs[0, 1])
    ax_temp = fig.add_subplot(gs[0, 2]); cax_temp = fig.add_subplot(gs[0, 3])
    ax_a15 = fig.add_subplot(gs[1, 0])
    ax_a17 = fig.add_subplot(gs[1, 2])

    sm_topo = draw_global_topo(ax_topo)
    sm_temp = draw_global_temp(ax_temp)
    draw_zoom(ax_a15, "A15", "c")
    draw_zoom(ax_a17, "A17", "d")

    cb1 = fig.colorbar(sm_topo, cax=cax_topo)
    cb1.set_label("Elevation (km)", fontsize=FS_LABEL - 1)
    cb1.ax.tick_params(labelsize=FS_TICK - 1.5)
    cb2 = fig.colorbar(sm_temp, cax=cax_temp)
    cb2.set_label("Mean surface T (K)", fontsize=FS_LABEL - 1)
    cb2.ax.tick_params(labelsize=FS_TICK - 1.5)
    for cb in (cb1, cb2):
        cb.outline.set_edgecolor(C_DIM)

    a15_h = Line2D([0], [0], marker="o", color="white", lw=0, ms=8,
                   mec="white", mew=1.2, markerfacecolor=C_A15,
                   label="Apollo 15 (HFE)")
    a17_h = Line2D([0], [0], marker="o", color="white", lw=0, ms=8,
                   mec="white", mew=1.2, markerfacecolor=C_A17,
                   label="Apollo 17 (HFE)")
    zoom_h = Line2D([0], [0], color=C_DIM, ls=(0, (4, 2)), lw=0.9,
                    label=r"Zoom region ($\pm$"
                          rf"{int(ZOOM_DLON)}$^\circ$, $\pm$"
                          rf"{int(ZOOM_DLAT)}$^\circ$) on (a)")
    fig.legend(handles=[a15_h, a17_h, zoom_h], loc="lower center",
               bbox_to_anchor=(0.5, 0.005), ncols=3, frameon=True,
               edgecolor=C_GRID, framealpha=0.97, fontsize=FS_TICK,
               handlelength=2.2, borderpad=0.5, columnspacing=2.0)

    out = OUT / "fig_context_map.pdf"
    fig.savefig(out)
    plt.close(fig)
    print(f"  -> {out}")


if __name__ == "__main__":
    main()
