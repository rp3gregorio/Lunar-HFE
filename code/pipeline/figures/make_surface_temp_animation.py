#!/usr/bin/env python3
"""Lunar surface-temperature animation over one lunar day (presentation style).

A fixed nearside view of the Moon, textured with the REAL surface — the
Clementine albedo mosaic combined with LOLA shaded relief, so craters and
maria give the shape — with the model surface temperature draped over it as
a heat layer. The Sun orbits the disk and the terminator sweeps across the
fixed geography; each place heats from a ~100 K night to a ~390 K noon and
cools again. The Apollo 15 and 17 heat-flow sites are marked and read out
live.

The temperature field is real model output: `T_surface(lat, local_time)`
from `lunar.solver.solve_pixel` at a ladder of latitudes, cached to
`results/surface_temp_diurnal_field.json`. Surface texture:
`figures/moon_global.png` (Clementine albedo, USGS/NASA) and
`aogs/data/lola/ldem_16.img` (LOLA LDEM).

Outputs (illustrative/outreach, not a letter figure):
  figures/anim/lunar_surface_temperature.gif
  figures/anim/lunar_surface_temperature_filmstrip.pdf

Run:  python pipeline/figures/make_surface_temp_animation.py
"""
from __future__ import annotations

import json
import pathlib
import sys

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import cm
from matplotlib.colors import Normalize, LightSource
from matplotlib.image import imread
from matplotlib.animation import FuncAnimation, PillowWriter

ROOT = pathlib.Path(__file__).resolve().parents[2]           # code/
sys.path.insert(0, str(ROOT / "src"))
from lunar.plotting import style  # noqa: F401,E402  (house rcParams: serif fonts)
from lunar.plotting.style import C_A15, C_A17, C_CHAR, C_DIM, C_GRID  # noqa: E402
from lunar.config import SITES  # noqa: E402

OUT = ROOT.parent / "figures" / "anim"
FIELD = ROOT / "results" / "surface_temp_diurnal_field.json"
ALBEDO = ROOT.parent / "figures" / "moon_global.png"
DEM = ROOT.parent / "aogs" / "data" / "lola" / "ldem_16.img"

# --- presentation palette (light background) -------------------------
BG      = "#F4F2ED"       # warm light neutral background
PANEL   = "#FBFAF7"
INK     = C_CHAR          # near-black serif text
SUN_C   = "#E7A63A"       # warm sun
CMAP    = cm.inferno      # perceptual cold->hot temperature ramp
TMIN, TMAX = 90.0, 390.0  # K color range (night -> subsolar noon)

NY = NX = 440             # disk raster resolution
N_FRAMES = 132            # one lunar day
FPS = 20
VIEW_LAT, VIEW_LON = 7.0, 0.0    # nearside, slight tilt


# ---------------------------------------------------------------------
def load_field():
    if not FIELD.exists():
        _compute_field()
    d = json.loads(FIELD.read_text())
    return np.asarray(d["lat_deg"]), np.asarray(d["T_surface_K"])


def _compute_field():
    from lunar.config import HAYNE, GRID, DT_STEP
    from lunar.constants import Q_B_EQUATORIAL
    from lunar.grid import make_geometric_grid
    from lunar.solver import (solve_pixel, PixelInputs, standard_insolation,
                              periodic_time_grid)
    g = make_geometric_grid(**GRID)
    t = periodic_time_grid(DT_STEP)
    Ks, H, chi = HAYNE["K_S"], HAYNE["H"], HAYNE["CHI"]
    A = float(np.mean([SITES[s]["albedo"] for s in ("A15", "A17")]))
    lats = np.array([0., 10., 20., 30., 40., 50., 60., 70., 80., 89.])
    field = []
    for lat in lats:
        insol = standard_insolation(float(lat), t)
        out = solve_pixel(PixelInputs(
            grid=g, t=t, bc_mode="radiative", insolation=insol, albedo=A,
            emissivity=0.95, Q_b=Q_B_EQUATORIAL, n_lunations_spinup=80,
            spinup_tol_K=0.05, spinup_depth_m=0.15,
            hayne_params=(Ks, 0.0034, H, chi)))
        skin = out.T_surface if out.T_surface is not None else out.T[0]
        field.append(np.asarray(skin, float))
    FIELD.write_text(json.dumps(
        {"lat_deg": lats.tolist(), "n_t": int(np.shape(field)[1]),
         "T_surface_K": np.array(field).round(2).tolist(),
         "note": "diurnal surface skin T(lat,local_time) from solve_pixel; "
                 "t=0 is local noon"}))


def load_basemap():
    """Grayscale relief basemap (equirect): Clementine albedo x LOLA hillshade."""
    alb = imread(str(ALBEDO))
    alb = alb[..., :3].mean(-1) if alb.ndim == 3 else alb    # -> gray [0,1]
    H, W = alb.shape
    # LOLA hillshade at the albedo resolution
    if DEM.exists():
        dem = np.fromfile(DEM, dtype="<i2").reshape(2880, 5760).astype(float) * 0.5
        # coarsen to the albedo grid
        fy, fx = 2880 // H, 5760 // W
        dem = dem[:fy * H:fy, :fx * W:fx][:H, :W]
        hs = LightSource(azdeg=300, altdeg=42).hillshade(
            dem, vert_exag=90, dx=1.0, dy=1.0)
    else:
        hs = np.full_like(alb, 0.6)
    # combine: maria/highlands from albedo, crater shape from hillshade
    base = 0.45 * (alb / max(alb.max(), 1e-6)) + 0.55 * hs
    base = np.clip(0.35 + 0.75 * (base - base.min()) / (np.ptp(base) + 1e-9), 0, 1)
    return base                                              # [H,W] in [0,1]


def _sample_equirect(field, lat, lon):
    H, W = field.shape
    row = np.clip(((90 - lat) / 180 * (H - 1)).astype(int), 0, H - 1)
    col = np.clip(((lon + 180) / 360 * (W - 1)).astype(int), 0, W - 1)
    return field[row, col]


def _ortho_grid(lat0, lon0):
    """Inverse orthographic: screen (X,Y) in [-1,1] -> (lat,lon), mask, mu."""
    xs = np.linspace(-1, 1, NX)
    ys = np.linspace(1, -1, NY)
    X, Y = np.meshgrid(xs, ys)
    rho = np.sqrt(X ** 2 + Y ** 2)
    mask = rho <= 1.0
    rho_s = np.where(rho == 0, 1e-9, rho)
    c = np.arcsin(np.clip(rho, 0, 1))
    la0 = np.deg2rad(lat0)
    lat = np.rad2deg(np.arcsin(np.cos(c) * np.sin(la0)
                               + Y * np.sin(c) * np.cos(la0) / rho_s))
    lon = lon0 + np.rad2deg(np.arctan2(
        X * np.sin(c),
        rho_s * np.cos(c) * np.cos(la0) - Y * np.sin(c) * np.sin(la0)))
    lon = ((lon + 180) % 360) - 180
    mu = np.cos(c)                                            # limb darkening
    return lat, lon, mask, mu


def _forward_ortho(lat, lon, lat0, lon0):
    la, lo = np.deg2rad(lat), np.deg2rad(lon)
    la0, lo0 = np.deg2rad(lat0), np.deg2rad(lon0)
    cosc = np.sin(la0) * np.sin(la) + np.cos(la0) * np.cos(la) * np.cos(lo - lo0)
    X = np.cos(la) * np.sin(lo - lo0)
    Y = np.cos(la0) * np.sin(la) - np.sin(la0) * np.cos(la) * np.cos(lo - lo0)
    return X, Y, cosc > 0


def temp_at(lat_deg, hourangle_deg, lat_ladder, T_field):
    n_t = T_field.shape[1]
    frac = np.mod(hourangle_deg, 360.0) / 360.0
    ti = frac * n_t
    i0 = np.floor(ti).astype(int) % n_t
    i1 = (i0 + 1) % n_t
    w = ti - np.floor(ti)
    al = np.abs(lat_deg)
    li = np.interp(al, lat_ladder, np.arange(lat_ladder.size))
    l0 = np.floor(li).astype(int)
    l1 = np.minimum(l0 + 1, lat_ladder.size - 1)
    wl = li - l0
    g0 = (1 - w) * T_field[l0, i0] + w * T_field[l0, i1]
    g1 = (1 - w) * T_field[l1, i0] + w * T_field[l1, i1]
    return (1 - wl) * g0 + wl * g1


# ---------------------------------------------------------------------
class Scene:
    def __init__(self):
        self.lat_ladder, self.T_field = load_field()
        self.base = load_basemap()
        self.lat, self.lon, self.mask, self.mu = _ortho_grid(VIEW_LAT, VIEW_LON)
        self.base_disk = _sample_equirect(self.base, self.lat, self.lon)
        self.norm = Normalize(TMIN, TMAX)
        # Apollo site screen positions (fixed geography)
        self.sites = {}
        for k in ("A15", "A17"):
            la, lo = SITES[k]["lat"], SITES[k]["lon"]
            X, Y, fr = _forward_ortho(la, lo, VIEW_LAT, VIEW_LON)
            self.sites[k] = dict(lat=la, lon=lo, X=float(X), Y=float(Y),
                                 front=bool(fr),
                                 color=C_A15 if k == "A15" else C_A17)

    def frame_rgba(self, sslon):
        """RGBA disk image at subsolar longitude ``sslon`` (deg)."""
        H = self.lon - sslon                                 # hour angle past noon
        T = temp_at(self.lat, H, self.lat_ladder, self.T_field)
        col = CMAP(self.norm(T))[..., :3]
        shade = 0.42 + 0.58 * self.base_disk                 # relief modulation
        limb = 0.60 + 0.40 * np.clip(self.mu, 0, 1)          # sphere shape
        # faint cool "earthshine" so night-side craters stay visible
        ambient = 0.06 * self.base_disk[..., None] * np.array([0.55, 0.68, 1.0])
        rgb = np.clip(col * shade[..., None] * limb[..., None]
                      + ambient * limb[..., None], 0, 1)
        rgba = np.zeros((NY, NX, 4))
        rgba[..., :3] = rgb
        rgba[..., 3] = self.mask.astype(float)
        return rgba, T

    def site_temp(self, k, sslon):
        s = self.sites[k]
        return float(temp_at(np.array([s["lat"]]),
                             np.array([s["lon"] - sslon]),
                             self.lat_ladder, self.T_field)[0])


def _sun_screen(sslon):
    """Screen position + front flag of the Sun (subsolar direction projected).

    When the subsolar point is near the disk centre (full/new Moon) the Sun
    lies on the view axis and has no screen direction — park it at the top,
    and let the front flag set its prominence (in front = lighting the near
    side; behind = the near side is in night)."""
    X, Y, fr = _forward_ortho(0.0, sslon, VIEW_LAT, VIEW_LON)
    r = float(np.hypot(X, Y))
    R = 1.24
    if r < 0.18:
        return 0.0, R, fr
    return R * X / r, R * Y / r, fr


def build():
    sc = Scene()
    fig = plt.figure(figsize=(8.6, 6.4), dpi=100)
    fig.patch.set_facecolor(BG)

    ax = fig.add_axes([0.045, 0.235, 0.60, 0.66])            # globe
    ax.set_facecolor(BG); ax.set_aspect("equal"); ax.set_axis_off()
    ax.set_xlim(-1.5, 1.5); ax.set_ylim(-1.35, 1.35)

    cax = fig.add_axes([0.70, 0.30, 0.020, 0.52])            # colorbar
    dax = fig.add_axes([0.10, 0.075, 0.52, 0.115])           # diurnal strip
    iax = fig.add_axes([0.775, 0.30, 0.205, 0.52])           # readout panel
    iax.set_facecolor(BG); iax.set_axis_off()
    iax.set_xlim(0, 1); iax.set_ylim(0, 1)

    # limb ring + soft ground shadow for a seated, 3-D feel
    ring = plt.Circle((0, 0), 1.0, fill=False, ec=C_DIM, lw=1.0, zorder=5)
    for rr, aa in ((1.05, "#0000000A"), (1.03, "#0000000A")):   # faint soft halo
        ax.add_patch(plt.Circle((0.02, -0.02), rr, color=aa, zorder=0))
    ax.add_patch(ring)

    rgba0, _ = sc.frame_rgba(0.0)
    im = ax.imshow(rgba0, extent=(-1, 1, -1, 1), origin="upper",
                   interpolation="bilinear", zorder=2)

    # Sun glyph (halo + core + rays), updated each frame
    halo = ax.scatter([], [], s=2600, c=SUN_C, alpha=0.14, zorder=1,
                      edgecolors="none")
    core = ax.scatter([], [], s=430, c=SUN_C, alpha=1.0, zorder=6,
                      edgecolors="white", linewidths=0.8)
    rays = [ax.plot([], [], color=SUN_C, lw=1.4, alpha=0.5, zorder=1)[0]
            for _ in range(12)]
    sun_txt = ax.text(0, 0, "Sun", color="#B8801F", fontsize=10,
                      ha="center", va="center", zorder=7)

    # Apollo markers (static positions) + leader-free readout panel
    marks = {}
    for k, s in sc.sites.items():
        (mk,) = ax.plot([s["X"]], [s["Y"]], "o", ms=9, mfc=s["color"],
                        mec="white", mew=1.4, zorder=8,
                        visible=s["front"])
        marks[k] = mk

    # colorbar
    sm = cm.ScalarMappable(norm=sc.norm, cmap=CMAP)
    cb = fig.colorbar(sm, cax=cax)
    cb.set_label("Surface temperature  (K)", fontsize=10.5, color=INK)
    cb.set_ticks([100, 150, 200, 250, 300, 350])
    cax.tick_params(colors=INK, labelsize=9)
    cb.outline.set_edgecolor(C_DIM)

    # readout panel text (site temps + phase), updated each frame
    iax.text(0.0, 0.98, "Heat-flow sites", fontsize=10.5, color=INK,
             fontweight="bold", va="top")
    site_txt = {}
    yy = 0.86
    for k in ("A15", "A17"):
        col = sc.sites[k]["color"]
        iax.text(0.0, yy, f"Apollo {k[1:]}", fontsize=10, color=col,
                 fontweight="bold", va="top")
        site_txt[k] = iax.text(0.0, yy - 0.075, "", fontsize=13, color=INK,
                               va="top")
        yy -= 0.20
    phase_txt = iax.text(0.0, 0.30, "", fontsize=10, color=C_DIM, va="top")

    # diurnal strip: each site's own real diurnal curve + moving marker
    n_t = sc.T_field.shape[1]
    lt_h = np.linspace(0, 24, n_t, endpoint=False)
    dcurve = {}
    for k in ("A15", "A17"):
        la = sc.sites[k]["lat"]
        curve = temp_at(np.full(n_t, la), lt_h / 24.0 * 360.0,
                        sc.lat_ladder, sc.T_field)
        clock = (lt_h + 12) % 24
        o = np.argsort(clock)
        dax.plot(clock[o], curve[o], color=sc.sites[k]["color"], lw=1.8,
                 label=f"Apollo {k[1:]}")
        dcurve[k] = (clock[o], curve[o])
    dmark = {k: dax.plot([], [], "o", color=sc.sites[k]["color"], mec="white",
                         mew=1.0, ms=8, zorder=6)[0] for k in ("A15", "A17")}
    dax.set_xlim(0, 24); dax.set_ylim(TMIN, TMAX)
    dax.set_xticks([0, 6, 12, 18, 24])
    dax.set_xticklabels(["midnight", "sunrise", "noon", "sunset", "midnight"],
                        fontsize=8.5)
    dax.set_ylabel("T (K)", fontsize=9, color=INK)
    dax.tick_params(colors=INK, labelsize=8.5)
    for sp in ("top", "right"):
        dax.spines[sp].set_visible(False)
    for sp in ("left", "bottom"):
        dax.spines[sp].set_color(C_DIM)
    dax.grid(True, color=C_GRID, lw=0.6)
    dax.legend(loc="upper right", fontsize=8, frameon=True, edgecolor=C_GRID,
               handlelength=1.4, borderpad=0.4)

    # titles (figure coords, clear of the disk)
    fig.text(0.045, 0.955, "How the Sun drives the Moon's surface temperature",
             fontsize=15, fontweight="bold", color=INK)
    fig.text(0.045, 0.915, "one lunar day — model skin temperature draped "
             "on Clementine albedo and LOLA relief", fontsize=10, color=C_DIM)

    phases = ["Noon over 0°E", "afternoon", "sunset terminator",
              "night on the near side", "before dawn", "sunrise terminator"]

    def update(frame):
        sslon = 360.0 * frame / N_FRAMES
        rgba, _ = sc.frame_rgba(sslon)
        im.set_data(rgba)
        # sun glyph
        sx, sy, fr = _sun_screen(sslon)
        core.set_offsets([[sx, sy]]); halo.set_offsets([[sx, sy]])
        core.set_sizes([430 if fr else 150])
        core.set_alpha(1.0 if fr else 0.4)
        halo.set_alpha(0.16 if fr else 0.05)
        sun_txt.set_position((sx, sy - 0.17)); sun_txt.set_alpha(1.0 if fr else 0.4)
        for i, r in enumerate(rays):
            a = 2 * np.pi * i / len(rays)
            r.set_data([sx, sx + 0.10 * np.cos(a)], [sy, sy + 0.10 * np.sin(a)])
            r.set_alpha(0.5 if fr else 0.15)
        # site markers + readouts
        for k in ("A15", "A17"):
            Tk = sc.site_temp(k, sslon)
            site_txt[k].set_text(f"{Tk:.0f} K")
            marks[k].set_visible(sc.sites[k]["front"])
            cl, cv = dcurve[k]
            clock = (( (sc.sites[k]["lon"] - sslon) / 360.0 * 24.0) + 12) % 24
            dmark[k].set_data([clock], [np.interp(clock, cl, cv)])
        phase_txt.set_text(phases[int(frame / N_FRAMES * len(phases)) % len(phases)])
        return [im]

    return fig, update


def render():
    OUT.mkdir(parents=True, exist_ok=True)
    fig, update = build()
    anim = FuncAnimation(fig, update, frames=N_FRAMES, interval=1000 / FPS,
                         blit=False)
    gif = OUT / "lunar_surface_temperature.gif"
    # dpi=100 overrides the house savefig.dpi=300 so the GIF stays ~900 px
    # wide and a sane file size (300 dpi ballooned it to 70+ MB).
    anim.save(str(gif), writer=PillowWriter(fps=FPS), dpi=100)
    # re-quantize to a 128-colour optimized palette to shrink the file
    try:
        from PIL import Image, ImageSequence
        im = Image.open(gif)
        frames = [f.convert("RGB").quantize(colors=128, method=Image.MEDIANCUT)
                  for f in ImageSequence.Iterator(im)]
        frames[0].save(gif, save_all=True, append_images=frames[1:],
                       loop=0, duration=int(1000 / FPS), optimize=True,
                       disposal=2)
    except Exception as e:  # noqa: BLE001
        print(f"  (palette optimize skipped: {e})")
    print(f"  -> {gif}  ({gif.stat().st_size/1e6:.1f} MB)")

    # filmstrip: 4 phases
    sc = Scene()
    fig_fs, axes = plt.subplots(1, 4, figsize=(7.48, 2.35), dpi=200)
    fig_fs.patch.set_facecolor(BG)
    for a, f in zip(axes, (0.0, 0.25, 0.5, 0.75)):
        sslon = 360.0 * f
        rgba, _ = sc.frame_rgba(sslon)
        a.set_facecolor(BG); a.set_aspect("equal"); a.set_axis_off()
        a.add_patch(plt.Circle((0, 0), 1.0, fill=False, ec=C_DIM, lw=0.8))
        a.imshow(rgba, extent=(-1, 1, -1, 1), origin="upper",
                 interpolation="bilinear")
        for k in ("A15", "A17"):
            s = sc.sites[k]
            if s["front"]:
                a.plot([s["X"]], [s["Y"]], "o", ms=6, mfc=s["color"],
                       mec="white", mew=1.0)
        a.set_xlim(-1.15, 1.15); a.set_ylim(-1.15, 1.15)
        lab = {0.0: "noon", 0.25: "sunset", 0.5: "night", 0.75: "sunrise"}[f]
        a.set_title(lab, color=INK, fontsize=9)
    fig_fs.subplots_adjust(left=0.01, right=0.99, top=0.9, bottom=0.02, wspace=0.05)
    strip = OUT / "lunar_surface_temperature_filmstrip.pdf"
    fig_fs.savefig(strip, facecolor=BG)
    plt.close(fig_fs)
    print(f"  -> {strip}")
    plt.close(fig)


if __name__ == "__main__":
    render()
