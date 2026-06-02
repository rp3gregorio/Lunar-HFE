#!/usr/bin/env python3
"""Context map of the Apollo Heat-Flow Experiment landing sites.

Layout: a single global equirectangular lunar map on top, with two
zoomed regional crops below (one per site). Same image dataset is
used throughout, so the regional zooms are real lunar terrain rather
than schematic patches.

Top:    global 2D map (longitude -180 to +180 degrees, latitude
        -90 to +90 degrees, Clementine albedo mosaic). Apollo 15 and
        17 borehole locations are overlaid with their ALSEP gazetteer
        coordinates.
Bottom: regional zooms (+/-15 deg longitude, +/-10 deg latitude)
        around each landing site, cropped from the same global map.

Background image: figures/moon_global.png
  Source: https://upload.wikimedia.org/wikipedia/commons/d/db/Moonmap_from_clementine_data.png
  Credit: Clementine global albedo mosaic, USGS/NASA, public domain.
  Re-download with:
    curl -fL -A "Mozilla/5.0" \\
      "https://upload.wikimedia.org/wikipedia/commons/d/db/Moonmap_from_clementine_data.png" \\
      -o paper/letter/figures/moon_global.png

Writes paper/letter/figures/fig_context_map.pdf.
"""
from __future__ import annotations
import pathlib
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.image import imread
from matplotlib.lines import Line2D
from matplotlib.patches import Rectangle

# Shared design tokens
JGR_FULL = 7.48
C_A15   = "#3D6E4A"
C_A17   = "#B85B3A"
C_CHAR  = "#2A2520"
C_DIM   = "#6E6862"
C_GRID  = "#E8E5E0"
C_PAPER = "#FBFAF8"
FS_LABEL = 10.0
FS_TICK  = 9.0
FS_TITLE = 11.0
FS_SITE  = 9.5

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
OUT  = ROOT / "paper" / "letter" / "figures"
MOON_PNG = OUT / "moon_global.png"

# ALSEP gazetteer coordinates (match phase_a_pipeline.py)
SITES = {
    "A15": dict(lat=26.13, lon= 3.63, color=C_A15, label="Apollo 15"),
    "A17": dict(lat=20.19, lon=30.77, color=C_A17, label="Apollo 17"),
}

# Zoom box size for the regional crops (degrees, half-widths)
ZOOM_DLON = 15.0
ZOOM_DLAT = 10.0


def load_moon():
    """Load the global equirectangular Moon mosaic.

    The Clementine mosaic on Wikimedia Commons is stored centred at
    longitude 0 (prime meridian in the middle of the image, nearside
    centred). This is already the standard lunar cartographic
    convention, so no longitude roll is needed.
    """
    if not MOON_PNG.exists():
        raise FileNotFoundError(
            f"Lunar background image not found at {MOON_PNG}. "
            "See module docstring for the curl command."
        )
    return imread(str(MOON_PNG))


def draw_global(ax, img):
    """Top panel: global equirectangular map with site overlays."""
    ax.imshow(img, extent=(-180, 180, -90, 90),
              cmap="gray", origin="upper", aspect="equal", zorder=1,
              interpolation="bilinear")

    # graticule overlay
    for lat in (-60, -30, 0, 30, 60):
        ax.axhline(lat, color="white", lw=0.35, alpha=0.30, zorder=2)
    for lon in (-150, -120, -90, -60, -30, 0, 30, 60, 90, 120, 150):
        ax.axvline(lon, color="white", lw=0.35, alpha=0.30, zorder=2)
    # equator + prime meridian a touch heavier
    ax.axhline(0, color="white", lw=0.6, alpha=0.5, zorder=2)
    ax.axvline(0, color="white", lw=0.6, alpha=0.5, zorder=2)

    # site markers + callouts
    for name, s in SITES.items():
        ax.plot(s["lon"], s["lat"], marker="o", color=s["color"],
                ms=8, mec="white", mew=1.3, zorder=5)
        dx = 28 if name == "A17" else -28
        dy = 22
        ax.annotate(
            s["label"],
            xy=(s["lon"], s["lat"]),
            xytext=(s["lon"] + dx, s["lat"] + dy),
            fontsize=FS_SITE, color=C_CHAR, fontweight="bold",
            ha="left" if name == "A17" else "right",
            va="bottom",
            bbox=dict(boxstyle="round,pad=0.22",
                      facecolor="white", edgecolor=s["color"],
                      linewidth=0.8, alpha=0.95),
            arrowprops=dict(arrowstyle="-",
                            color=s["color"], lw=0.9,
                            connectionstyle="arc3,rad=0.0"),
            zorder=6,
        )
        # show the zoom region used in panel (b) as a faint rectangle
        rect = Rectangle((s["lon"] - ZOOM_DLON, s["lat"] - ZOOM_DLAT),
                          2 * ZOOM_DLON, 2 * ZOOM_DLAT,
                          facecolor="none",
                          edgecolor=s["color"], linewidth=0.9,
                          linestyle=(0, (4, 2)), alpha=0.85, zorder=4)
        ax.add_patch(rect)

    # axis cosmetics: degree ticks
    ax.set_xticks([-180, -120, -60, 0, 60, 120, 180])
    ax.set_xticklabels(["180°W", "120°W", "60°W", "0°", "60°E",
                        "120°E", "180°E"], fontsize=FS_TICK)
    ax.set_yticks([-90, -60, -30, 0, 30, 60, 90])
    ax.set_yticklabels(["90°S", "60°S", "30°S", "0°", "30°N", "60°N",
                        "90°N"], fontsize=FS_TICK)
    ax.set_xlim(-180, 180); ax.set_ylim(-90, 90)
    ax.set_xlabel("Selenographic longitude", fontsize=FS_LABEL)
    ax.set_ylabel("Selenographic latitude", fontsize=FS_LABEL)
    ax.set_title("(a)  Lunar global map — HFE landing-site locations "
                 "(Clementine albedo mosaic)",
                 fontsize=FS_TITLE, fontweight="bold", pad=6)
    ax.set_facecolor(C_PAPER)


def draw_zoom(ax, img, site_key):
    """Regional zoom crop: ±ZOOM_DLON longitude, ±ZOOM_DLAT latitude
    centred on the named site."""
    s = SITES[site_key]
    lon0, lat0 = s["lon"], s["lat"]
    extent = (lon0 - ZOOM_DLON, lon0 + ZOOM_DLON,
              lat0 - ZOOM_DLAT, lat0 + ZOOM_DLAT)
    ax.imshow(img, extent=(-180, 180, -90, 90),
              cmap="gray", origin="upper", aspect="equal",
              interpolation="bilinear", zorder=1)
    ax.set_xlim(extent[0], extent[1])
    ax.set_ylim(extent[2], extent[3])

    # graticule in the zoom (10-deg lon, 5-deg lat)
    for lat in np.arange(round(extent[2]/5)*5,
                          round(extent[3]/5)*5 + 1, 5):
        ax.axhline(lat, color="white", lw=0.35, alpha=0.30, zorder=2)
    for lon in np.arange(round(extent[0]/5)*5,
                          round(extent[1]/5)*5 + 1, 5):
        ax.axvline(lon, color="white", lw=0.35, alpha=0.30, zorder=2)

    # Site marker only -- the site name now appears in the panel
    # title so the in-panel callout box has been removed to keep the
    # terrain unobscured.
    ax.plot(lon0, lat0, marker="o", color=s["color"], ms=11,
            mec="white", mew=1.6, zorder=5)

    # axis cosmetics
    ax.tick_params(labelsize=FS_TICK - 0.5)
    ax.set_xlabel("Longitude (°E)", fontsize=FS_LABEL - 0.5)
    if site_key == "A15":
        ax.set_ylabel("Latitude (°N)", fontsize=FS_LABEL - 0.5)
    panel_label = "b" if site_key == "A15" else "c"
    ax.set_title(rf"({panel_label})  {s['label']} "
                 rf"({s['lat']:.1f}$^\circ$N, {s['lon']:.1f}$^\circ$E)",
                 fontsize=FS_TITLE - 0.5, fontweight="bold", pad=4,
                 color=s["color"])


def main():
    img = load_moon()

    # 2-row layout: top row = wide global map (1.7:1 emphasis); bottom
    # row = two zoom panels. Figure is tall enough to give panel (a)
    # the room it needs without squeezing the regional zooms.
    fig = plt.figure(figsize=(JGR_FULL, 6.6))
    gs = fig.add_gridspec(2, 2, height_ratios=[1.7, 1.0],
                          left=0.08, right=0.985, top=0.93, bottom=0.13,
                          hspace=0.48, wspace=0.18)
    ax_top = fig.add_subplot(gs[0, :])
    ax_a15 = fig.add_subplot(gs[1, 0])
    ax_a17 = fig.add_subplot(gs[1, 1])

    draw_global(ax_top, img)
    draw_zoom(ax_a15, img, "A15")
    draw_zoom(ax_a17, img, "A17")

    # shared legend below
    a15_h = Line2D([0], [0], marker="o", color="white", lw=0,
                   ms=8, mec="white", mew=1.3,
                   markerfacecolor=C_A15, label="Apollo 15 (HFE)")
    a17_h = Line2D([0], [0], marker="o", color="white", lw=0,
                   ms=8, mec="white", mew=1.3,
                   markerfacecolor=C_A17, label="Apollo 17 (HFE)")
    zoom_h = Line2D([0], [0], color=C_DIM, ls=(0, (4, 2)), lw=0.9,
                    label=r"Zoom region ($\pm$"
                          rf"{int(ZOOM_DLON)}$^\circ$ lon, $\pm$"
                          rf"{int(ZOOM_DLAT)}$^\circ$ lat)")
    fig.legend(handles=[a15_h, a17_h, zoom_h],
               loc="lower center", bbox_to_anchor=(0.5, 0.01),
               ncols=3, frameon=True, edgecolor=C_GRID, framealpha=0.97,
               fontsize=FS_TICK, handlelength=2.4, borderpad=0.6,
               columnspacing=2.4)

    out = OUT / "fig_context_map.pdf"
    fig.savefig(out)
    plt.close(fig)
    print(f"  -> {out}")


if __name__ == "__main__":
    main()
