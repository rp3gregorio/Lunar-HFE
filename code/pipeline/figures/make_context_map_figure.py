#!/usr/bin/env python3
"""Context figure for the Apollo Heat-Flow Experiment landing sites.

Six panels: the top row places the two sites on two GLOBAL data layers —
(a) LOLA topography (shaded relief) and (b) the modeled mean surface
temperature — the middle row zooms into each borehole on LOLA shaded
relief so the local terrain (Apennine front at Apollo 15, Taurus-Littrow
massifs at Apollo 17) reads directly, and the bottom row (e, f) shows each
landing site on the LROC NAC mosaic with the EVA traverses, the lunar module,
the ALSEP central station and, in an inset, the two heat-flow probes.

Data
  figures/moon_global.png          Clementine albedo (fallback basemap)
  data/lola/ldem_16.img            LOLA LDEM, 16 ppd (topography)
  data/lola_relief/{A15,A17}.npy   pre-cut relief crops for the zooms
  results/abstract_mean_surface_T.json  mean skin T vs latitude (real solver)
  data/apollo_site_maps/           LROC NAC mosaic + EVA traverse masks
                                   (pipeline/fetch_apollo_site_maps.py)

Writes figures/fig_context_map.pdf.
"""
from __future__ import annotations
import json
import pathlib
import numpy as np
import matplotlib
import matplotlib.patches
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import cm
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
DEM = ROOT / "data" / "lola" / "ldem_16.img"
MEANT = ROOT / "results" / "abstract_mean_surface_T.json"
RELIEF_DIR = ROOT / "data" / "lola_relief"
SITEMAP_DIR = ROOT / "data" / "apollo_site_maps"
R_MOON = 1737.4                                    # km

# Landing-site hardware. LM and ALSEP central station (C/S): LROC coordinates
# (Wagner et al. 2017, Icarus 283; LROC list of 28 July 2016). Heat-flow
# layout relative to the C/S, in m east and north, from the PDS Geosciences
# Node HFE descriptions: electronics box 9 m (A15) / 12.3 m (A17) north of
# the C/S, probe 1 hole 4 / 5.7 m east and probe 2 hole 4.5 / 5.4 m west of it.
SITE_HW = {
    "A15": dict(LM=(26.13239, 3.63330), CS=(26.13406, 3.62991),
                box=(0.0, 9.0), p1=(4.0, 9.0), p2=(-4.5, 9.0)),
    "A17": dict(LM=(20.1911, 30.7723), CS=(20.1923, 30.7655),
                box=(0.0, 12.3), p1=(5.7, 12.3), p2=(-5.4, 12.3)),
}

from lunar.config import SITES  # single source of truth  # noqa: E402

ZOOM_DLON = 15.0
ZOOM_DLAT = 10.0
TOPO_CMAP = plt.get_cmap("gist_earth")
TEMP_CMAP = plt.get_cmap("inferno")


# ---------------------------------------------------------------------
_DEM_CACHE = {}


def _dem():
    """LOLA elevation (km) at 1/4 the LDEM_16 resolution (720x1440), columns
    re-ordered to run from 180 W to 180 E for extent=(-180, 180); cached.

    The LDEM's first column is 0 deg E (PDS label WESTERNMOST_LONGITUDE = 0), so
    it is rolled by half a turn. Until 2026-10-08 it was drawn unrolled, which
    put the far side at the centre of the map."""
    if "d" not in _DEM_CACHE:
        d = np.fromfile(DEM, dtype="<i2").reshape(2880, 5760).astype(float)
        d = np.roll(d, d.shape[1] // 2, axis=1)          # 0..360 E -> -180..180
        _DEM_CACHE["d"] = d[::4, ::4] * 0.5e-3
    return _DEM_CACHE["d"]


def _hillshade():
    """Grayscale LOLA shaded-relief intensity in [0,1] (the 'shape' layer)."""
    return LightSource(azdeg=315, altdeg=45).hillshade(
        _dem(), vert_exag=55, dx=1.0, dy=1.0)


def _load_topo():
    """Global LOLA topography: (elevation km, hillshaded RGB, vmin, vmax)."""
    dem = _dem()
    vmin, vmax = np.percentile(dem, [1, 99])
    rgb = LightSource(azdeg=315, altdeg=45).shade(
        dem, cmap=TOPO_CMAP, blend_mode="soft", vert_exag=55,
        dx=1.0, dy=1.0, vmin=vmin, vmax=vmax)
    return dem, rgb, vmin, vmax


def _temp_field():
    """Mean surface-T (K) draped on LOLA shaded relief: (RGB, tmin, tmax).

    With global values the mean skin temperature is latitude-banded, so the
    color is a function of |lat| only; multiplying by the grayscale hillshade
    adds the real terrain (craters, maria) the same way panel (a) shows it.
    """
    d = json.loads(MEANT.read_text())
    lats = np.asarray(d["lat_deg"]); tmean = np.asarray(d["T_mean_K"])
    hs = _hillshade()                                 # [H, W] in [0,1]
    H, W = hs.shape
    grid_lat = np.linspace(90, -90, H)                # rows N->S (origin upper)
    Tcol = np.interp(np.abs(grid_lat), lats, tmean)
    T = np.tile(Tcol[:, None], (1, W))
    tmin, tmax = float(tmean.min()), float(tmean.max())
    col = TEMP_CMAP((np.clip(T, tmin, tmax) - tmin) / (tmax - tmin))[..., :3]
    shade = 0.45 + 0.55 * hs                           # relief modulation
    rgb = np.clip(col * shade[..., None], 0, 1)
    return rgb, tmin, tmax


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
                 fontweight="bold", pad=4, loc="left")
    sm = cm.ScalarMappable(norm=Normalize(vmin, vmax), cmap=TOPO_CMAP)
    return sm


def draw_global_temp(ax):
    rgb, tmin, tmax = _temp_field()                   # temperature draped on relief
    ax.imshow(rgb, extent=(-180, 180, -90, 90), origin="upper",
              aspect="auto", zorder=1, interpolation="bilinear")
    _global_axes(ax); _mark_sites(ax, callout=False, rects=False)
    ax.set_yticklabels([])                    # same latitude axis as (a)
    ax.set_title("(b)  Mean surface temperature", fontsize=FS_TITLE,
                 fontweight="bold", pad=4, loc="left")
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
                 color=SITE_COLOR[site_key], loc="left")


def _km(site, lat, lon):
    """km east and north of the lunar module (local plane, fine at 10 km)."""
    la0, lo0 = SITE_HW[site]["LM"]
    k = np.pi / 180 * R_MOON
    return ((np.asarray(lon) - lo0) * k * np.cos(np.radians(la0)),
            (np.asarray(lat) - la0) * k)


def _site_extent(site):
    """Valid-data box of the NAC mosaic, in km from the LM, plus the image."""
    from PIL import Image
    meta = json.loads((SITEMAP_DIR / "meta.json").read_text())["sites"][site]
    lon0, lat0, lon1, lat1 = meta["bbox"]
    a = np.asarray(Image.open(SITEMAP_DIR / f"{site}_nac.png")).astype(float)
    gray, valid = a[..., 0], a[..., 1] > 0
    H, W = gray.shape
    r0, r1, c0, c1 = 0, H - 1, 0, W - 1               # trim the emptiest edge until full
    while not valid[r0:r1 + 1, c0:c1 + 1].all():
        v = valid[r0:r1 + 1, c0:c1 + 1]
        bad = {"t": 1 - v[0].mean(), "b": 1 - v[-1].mean(),
               "l": 1 - v[:, 0].mean(), "r": 1 - v[:, -1].mean()}
        e = max(bad, key=bad.get)
        r0, r1 = r0 + (e == "t"), r1 - (e == "b")
        c0, c1 = c0 + (e == "l"), c1 - (e == "r")
    x0, y1 = _km(site, lat1 - (lat1 - lat0) * r0 / H, lon0 + (lon1 - lon0) * c0 / W)
    x1, y0 = _km(site, lat1 - (lat1 - lat0) * (r1 + 1) / H, lon0 + (lon1 - lon0) * (c1 + 1) / W)
    full = (*_km(site, lat0, lon0), *_km(site, lat1, lon1))     # x0, y0, x1, y1 of the image
    return (float(x0), float(x1), float(y0), float(y1)), gray, valid, full


def draw_site(ax, site, panel):
    """Landing site on the LROC NAC mosaic: EVA traverses, LM, ALSEP, probes."""
    from PIL import Image
    from scipy.ndimage import binary_dilation
    (x0, x1, y0, y1), gray, valid, full = _site_extent(site)
    ext = (full[0], full[2], full[1], full[3])
    lo, hi = np.percentile(gray[valid], [1, 99.5])
    g = np.clip((gray - lo) / (hi - lo), 0, 1)
    g = np.where(valid, g, 0.85)
    ax.imshow(g, cmap="gray", vmin=0, vmax=1, extent=ext, origin="upper",
              interpolation="bilinear", zorder=1)
    col = SITE_COLOR[site]
    rgb = np.array(matplotlib.colors.to_rgb(col))
    trav = np.zeros_like(valid)
    for e in (1, 2, 3):
        trav |= np.asarray(Image.open(SITEMAP_DIR / f"{site}_eva{e}.png")) > 0
    k = 4 if site == "A15" else 2                    # ~0.9 pt lines at both scales
    line = binary_dilation(trav, iterations=k)
    halo = binary_dilation(line, iterations=max(1, k // 2))
    for m, c, z in ((halo, (1, 1, 1), 2), (line, rgb, 3)):
        rgba = np.zeros(m.shape + (4,)); rgba[..., :3] = c; rgba[..., 3] = m * 1.0
        ax.imshow(rgba, extent=ext, origin="upper", interpolation="antialiased", zorder=z)
    hw = SITE_HW[site]
    ax.plot(0, 0, marker="^", ms=6, mfc="white", mec=C_CHAR, mew=0.9, zorder=6)
    xc, yc = _km(site, *hw["CS"])
    ax.plot(xc, yc, marker="o", ms=5.5, color=col, mec="white", mew=1.0, zorder=7)
    ax.set_xlim(x0, x1); ax.set_ylim(y0, y1); ax.set_aspect("equal")
    ax.tick_params(labelsize=FS_TICK - 0.5)
    ax.set_xlabel("km east of the lunar module", fontsize=FS_LABEL - 0.5)
    if site == "A15":
        ax.set_ylabel("km north of the lunar module", fontsize=FS_LABEL - 0.5)
    ax.set_title(rf"({panel})  {SITES[site]['label']} landing site",
                 fontsize=FS_TITLE - 0.5, fontweight="bold", pad=4,
                 color=col, loc="left")
    # inset: the ALSEP central station and the two probes, in metres
    ins = ax.inset_axes(INSET_POS[site])
    ins.set_facecolor("white")
    for sp in ins.spines.values():
        sp.set_edgecolor(col); sp.set_linewidth(0.9)
    ins.plot(0, 0, marker="s", ms=5.5, color=C_CHAR, zorder=3)      # central station (legend)
    bx, by = hw["box"]
    ins.plot([hw["p2"][0], hw["p1"][0]], [by, by], color=C_DIM, lw=0.6, ls=":", zorder=2)
    ins.plot(bx, by, marker="s", ms=3.2, mfc="white", mec=C_DIM, mew=0.8, zorder=3)
    for key, lab, side in (("p1", "probe 1", 1), ("p2", "probe 2", -1)):
        px, py = hw[key]
        ins.plot(px, py, marker="o", ms=5.5, color=col, mec="white", mew=0.8, zorder=4)
        ins.text(px - 0.6 * side, py + 2.0, lab, fontsize=6.5, color=col, va="bottom",
                 ha="left" if side > 0 else "right")
    # direction and distance to the LM
    dx_m, dy_m = -xc * 1e3, -yc * 1e3
    d = float(np.hypot(dx_m, dy_m)); ux, uy = dx_m / d, dy_m / d
    tip = (7.0 * ux, 7.0 * uy)
    ins.annotate("", xy=tip, xytext=(2.6 * ux, 2.6 * uy),
                 arrowprops=dict(arrowstyle="-|>", color=C_CHAR, lw=0.7, mutation_scale=7))
    ins.text(tip[0] + 0.6, tip[1], f"LM {d:.0f} m", fontsize=6.5, ha="left", va="center",
             color=C_CHAR)
    ins.plot([-15.0, -10.0], [-3.2, -3.2], color=C_CHAR, lw=1.2)
    ins.text(-12.5, -2.6, "5 m", fontsize=6.5, ha="center", va="bottom", color=C_CHAR)
    # equal metres on both axes: fit the content box (x -16..19, y -4.5..by+5.5)
    # into the inset's physical size, padding whichever axis has room to spare
    ax.apply_aspect()
    pos, fw, fh = ax.get_position(), ax.figure.get_figwidth(), ax.figure.get_figheight()
    w_in = pos.width * fw * INSET_POS[site][2]; h_in = pos.height * fh * INSET_POS[site][3]
    cx0, cx1, cy0, cy1 = -16.0, 21.5, -4.5, by + 5.5
    if (cx1 - cx0) / (cy1 - cy0) > w_in / h_in:
        pad = 0.5 * ((cx1 - cx0) * h_in / w_in - (cy1 - cy0)); cy0 -= pad; cy1 += pad
    else:
        pad = 0.5 * ((cy1 - cy0) * w_in / h_in - (cx1 - cx0)); cx0 -= pad; cx1 += pad
    ins.set_xlim(cx0, cx1); ins.set_ylim(cy0, cy1)
    ins.set_xticks([]); ins.set_yticks([])
    # leader from the ALSEP marker to the inset
    con = matplotlib.patches.ConnectionPatch(
        xyA=(xc, yc), coordsA=ax.transData, xyB=INSET_ANCHOR[site], coordsB=ins.transAxes,
        color=C_CHAR, lw=0.6, ls=(0, (3, 2)), zorder=5)
    ax.add_artist(con)


# inset placement (axes fraction: x, y, w, h) and the inset corner the leader meets
INSET_POS = {"A15": (0.02, 0.02, 0.58, 0.215), "A17": (0.655, 0.02, 0.335, 0.28)}
INSET_ANCHOR = {"A15": (0.5, 1.0), "A17": (0.5, 1.0)}


def main():
    fig = plt.figure(figsize=(JGR_FULL, 8.6))
    gs = fig.add_gridspec(
        2, 4, width_ratios=[1.0, 0.045, 1.0, 0.045],
        height_ratios=[1.0, 1.18],
        left=0.075, right=0.925, top=0.955, bottom=0.44,
        hspace=0.42, wspace=0.16)
    ax_topo = fig.add_subplot(gs[0, 0]); cax_topo = fig.add_subplot(gs[0, 1])
    ax_temp = fig.add_subplot(gs[0, 2]); cax_temp = fig.add_subplot(gs[0, 3])
    ax_a15 = fig.add_subplot(gs[1, 0])
    ax_a17 = fig.add_subplot(gs[1, 2])

    ext15, ext17 = _site_extent("A15")[0], _site_extent("A17")[0]
    w15, w17 = ext15[1] - ext15[0], ext17[1] - ext17[0]
    h15, h17 = ext15[3] - ext15[2], ext17[3] - ext17[2]
    gs2 = fig.add_gridspec(1, 2, width_ratios=[w15 / h15, w17 / h17],
                           left=0.085, right=0.985, top=0.37, bottom=0.115, wspace=0.12)
    ax_s15 = fig.add_subplot(gs2[0, 0]); ax_s17 = fig.add_subplot(gs2[0, 1])
    draw_site(ax_s15, "A15", "e")
    draw_site(ax_s17, "A17", "f")

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
    trav_h = (Line2D([0], [0], color=C_A15, lw=1.6), Line2D([0], [0], color=C_A17, lw=1.6))
    lm_h = Line2D([0], [0], marker="^", color="white", lw=0, ms=7,
                  mfc="white", mec=C_CHAR, mew=0.9)
    cs_h = Line2D([0], [0], marker="s", color="white", lw=0, ms=6, mfc=C_CHAR, mec=C_CHAR)
    from matplotlib.legend_handler import HandlerTuple
    fig.legend(handles=[a15_h, a17_h, zoom_h, trav_h, lm_h, cs_h],
               labels=["Apollo 15 (HFE)", "Apollo 17 (HFE)", zoom_h.get_label(),
                       "EVA traverses (LROC)", "Lunar module", "ALSEP central station"],
               loc="lower center", bbox_to_anchor=(0.5, 0.0), ncols=3, frameon=False,
               fontsize=9, handlelength=2.2, columnspacing=2.0,
               handler_map={tuple: HandlerTuple(ndivide=None, pad=0.3)})

    out = OUT / "fig_context_map.pdf"
    fig.savefig(out, dpi=450)            # keeps the NAC mosaic and the traverse lines sharp
    plt.close(fig)
    print(f"  -> {out}")


if __name__ == "__main__":
    main()
