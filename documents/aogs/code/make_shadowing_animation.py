#!/usr/bin/env python3
"""Terrain shadowing, animated: the skyline, the Sun, and the energy it costs.

Three panels, one lunation, nothing synthetic:

  1  THE TERRAIN ITSELF -- SLDEM2015 shaded relief around Apollo 15 at 512
     ppd (~59 m/px), the site marked, all 90 sampling rays drawn, and the ray
     the Sun is currently standing on picked out. It turns coral the moment
     that direction blocks.
  2  the skyline those rays produce: horizon elevation against azimuth, with
     the Sun moving along its true track and greying out when blocked.
  3  insolation over the lunation: flat-ground (dashed) against shadowed
     (filled), the blocked slivers in coral, and a moving time cursor.
  4  live readouts -- day, Sun elevation, blocked or not, and the CUMULATIVE
     energy lost, which is what makes 1.16% tangible.

Provenance note: the relief backdrop is the 512 ppd SLDEM2015 site crop, but
the published horizons (and therefore every number here) were computed at
16 ppd from ldem_16.img. The panel says so on screen -- finer relief is shown
because it is the same terrain rendered better, not because it changed the
answer.

Geometry is imported from s1_sensitivity (sun_track / standard_insolation), so
this cannot drift from the retrieval. Horizons are read from the cached
aogs_sensitivity.json, so no DEM download is needed.

Outputs
    documents/aogs/results/shadowing_animation.gif   1200 x 498, 12 fps
    documents/gedes/defense/img/shadowing.gif        slide copy
    documents/aogs/figures/shadowing_filmstrip.pdf   4 key frames
Run
    .venv/bin/python documents/aogs/code/make_shadowing_animation.py
"""
import json
import pathlib
import sys

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.animation as anim
import matplotlib.colors as mcolors
from matplotlib.colors import LightSource

HERE = pathlib.Path(__file__).resolve().parent
AOGS = HERE.parent
ROOT = next(a for a in HERE.parents if (a / "code" / "src" / "lunar").is_dir())
sys.path.insert(0, str(ROOT / "code" / "src"))
sys.path.insert(0, str(HERE / "compute"))

from lunar.constants import LUNATION_SECONDS          # noqa: E402
from lunar.config import SITES, DT_STEP                # noqa: E402
from lunar.solver import periodic_time_grid            # noqa: E402
from s1_sensitivity import sun_track, standard_insolation  # noqa: E402

CHAR, CORAL, TEAL = "#2A2520", "#B85B3A", "#2A6478"
FOREST, DIM, GRID = "#3D6E4A", "#6E6862", "#E8E5E0"
WHITE, GOLD = "#FFFFFF", "#C9A227"
SKY, ROCK = "#EDF1F4", "#4A443E"
# `terrain` truncated above its blue quarter: green -> tan -> brown -> white,
# which reads as altitude without implying water
TOPO = mcolors.LinearSegmentedColormap.from_list(
    "lunar_topo", plt.cm.terrain(np.linspace(0.28, 1.0, 256)))

plt.rcParams.update({
    "font.family": "sans-serif",
    "font.sans-serif": ["Helvetica Neue", "Helvetica", "Arial", "DejaVu Sans"],
    "text.color": CHAR, "axes.labelcolor": CHAR,
    "xtick.color": CHAR, "ytick.color": CHAR, "axes.edgecolor": CHAR,
    "figure.facecolor": WHITE, "savefig.facecolor": WHITE,
})

W, H, DPI = 15.0, 7.8, 100           # -> 1500 x 780
N = 72                                # 6 s at 12 fps, one lunation
R_MOON_KM = 1737.4
MAP_KM = 42.0                         # half-width of each relief panel
ZLO, ZHI = -1100.0, 4200.0            # shared elevation scale [m rel. site]
RAY_KM = 38.0                         # how far the drawn rays reach


def load():
    d = json.loads((AOGS / "results" / "aogs_sensitivity.json").read_text())
    out = {}
    for s in ("A15", "A17"):
        st = d["sites"][s]
        out[s] = dict(az=np.asarray(st["horizon_az_deg"]),
                      hor=np.asarray(st["horizon_deg"]),
                      lat=st["lat"], loss=st["insolation_energy_loss"],
                      hmax=st["horizon_max_deg"])
    return out


def load_relief(site="A15"):
    """SLDEM2015 crop as (rgb, extent_km, ppd) -- ELEVATION relative to the
    landing site, colour-mapped on the shared ZLO..ZHI scale and blended with
    a hillshade so both altitude and relief read at once."""
    base = ROOT / "code" / "data" / "lola" / "sldem2015"
    meta = json.loads((base / f"{site}.json").read_text())
    ny, nx = meta["shape"]
    z = np.fromfile(base / f"{site}.f32", dtype="<f4").reshape(ny, nx)
    lat0, lon0 = meta["site"]
    deg_km = 2.0 * np.pi * R_MOON_KM / 360.0
    lat = meta["lat_top"] - np.arange(ny) / meta["ppd"]
    lon = meta["lon_left"] + np.arange(nx) / meta["ppd"]
    x_km = (lon - lon0) * deg_km * np.cos(np.radians(lat0))
    y_km = (lat - lat0) * deg_km
    # crop to the panel window so the hillshade is not mostly off-screen
    ix = np.where(np.abs(x_km) <= MAP_KM)[0]
    iy = np.where(np.abs(y_km) <= MAP_KM)[0]
    z0 = float(z[np.argmin(np.abs(y_km)), np.argmin(np.abs(x_km))])
    zc = (z[iy[0]:iy[-1]+1, ix[0]:ix[-1]+1] - z0) * 1000.0     # m above the site
    px = deg_km / meta["ppd"] * 1000.0
    rgb = LightSource(azdeg=315, altdeg=42).shade(
        zc, cmap=TOPO, vmin=ZLO, vmax=ZHI, vert_exag=2.2, dx=px, dy=px,
        blend_mode="soft")
    return rgb, [x_km[ix[0]], x_km[ix[-1]], y_km[iy[-1]], y_km[iy[0]]], meta["ppd"]


def series(D, site):
    """Per-site time series on the PRODUCTION grid, so the cumulative loss
    lands on the certified insolation_energy_loss exactly (verified
    2026-07-29: 1.1636% / 0.1842%). A denser grid converges to 1.184%
    instead -- a real discretisation difference, not an error."""
    S = D[site]
    t = periodic_time_grid(DT_STEP)
    elev, A = sun_track(S["lat"], t)
    hor_at = np.interp(A, S["az"], S["hor"], period=360.0)
    S_flat = standard_insolation(S["lat"], t)
    blocked = (elev > 0) & (elev <= hor_at)
    S_shad = np.where(elev > hor_at, S_flat, 0.0)
    lost = np.cumsum(S_flat - S_shad) / max(1e-12, np.sum(S_flat))
    return dict(t=t, days=t / 86400.0, elev=elev, A=A, S_flat=S_flat,
                S_shad=S_shad, blocked=blocked, lost=lost)


def build(D):
    SITES_ = ("A15", "A17")
    COL = {"A15": FOREST, "A17": CORAL}
    TS = {s: series(D, s) for s in SITES_}
    days = TS["A15"]["days"]
    ELMAX = 20.0

    fig = plt.figure(figsize=(W, H), dpi=DPI)
    axD = {"A15": fig.add_axes([0.040, 0.545, 0.212, 0.375]),
           "A17": fig.add_axes([0.283, 0.545, 0.212, 0.375])}
    axCB = fig.add_axes([0.512, 0.560, 0.010, 0.345])
    axR = fig.add_axes([0.600, 0.520, 0.390, 0.430]); axR.axis("off")
    axR.set_xlim(0, 1); axR.set_ylim(0, 1)
    axSky = fig.add_axes([0.055, 0.085, 0.390, 0.335])
    axIns = fig.add_axes([0.562, 0.085, 0.390, 0.335])

    # ---------------- top row: the two DEMs, in elevation -----------------
    rays = {}
    for s in SITES_:
        ax = axD[s]
        rgb, ext, ppd_r = load_relief(s)
        ax.imshow(rgb, extent=ext, origin="upper", zorder=1)
        for a_ in np.radians(D[s]["az"]):
            ax.plot([0, RAY_KM*np.sin(a_)], [0, RAY_KM*np.cos(a_)],
                    color=WHITE, lw=0.3, alpha=0.26, zorder=3)
        rays[s], = ax.plot([], [], color=GOLD, lw=2.6, zorder=5,
                           solid_capstyle="round")
        ax.plot([0], [0], marker="^", ms=10, color=WHITE, mec=CHAR, mew=1.4,
                zorder=6)
        ax.set_xlim(-MAP_KM, MAP_KM); ax.set_ylim(-MAP_KM, MAP_KM)
        ax.set_xticks([-30, 0, 30]); ax.set_yticks([-30, 0, 30])
        ax.tick_params(labelsize=9.5)
        ax.set_xlabel("km east", fontsize=10.5)
        if s == "A15":
            ax.set_ylabel("km north", fontsize=10.5)
        ax.set_title(f"Apollo {s[1:]} — skyline peaks at {D[s]['hmax']:.1f}°",
                     fontsize=12.5, color=COL[s], loc="left", pad=8,
                     fontweight="bold")

    sm = plt.cm.ScalarMappable(cmap=TOPO, norm=mcolors.Normalize(ZLO, ZHI))
    cb = fig.colorbar(sm, cax=axCB)
    cb.set_label("elevation above the landing site  (m)", fontsize=10)
    cb.ax.tick_params(labelsize=9)
    fig.text(0.268, 0.468, "relief: SLDEM2015 512 ppd  ·  horizons computed at 16 ppd",
             fontsize=8.8, color=DIM, ha="center", style="italic")

    # ---------------- bottom left: the two skylines together --------------
    axSky.set_facecolor(SKY)
    for s in SITES_:
        axSky.fill_between(D[s]["az"], 0, D[s]["hor"], color=COL[s],
                           alpha=0.32 if s == "A17" else 0.55, lw=0, zorder=2)
        axSky.plot(D[s]["az"], D[s]["hor"], color=COL[s], lw=1.8, zorder=3,
                   label=f"Apollo {s[1:]}  ({D[s]['hmax']:.1f}° max)")
    suns = {}
    for s in SITES_:
        T = TS[s]
        Ap = T["A"].astype(float).copy()
        Ep = np.where(T["elev"] > 0, T["elev"], np.nan)
        w = np.where(np.abs(np.diff(Ap)) > 180.0)[0] + 1
        Ap, Ep = np.insert(Ap, w, np.nan), np.insert(Ep, w, np.nan)
        axSky.plot(Ap, np.where(Ep <= ELMAX, Ep, np.nan), color=GOLD, lw=1.1,
                   alpha=0.45, zorder=4)
        suns[s], = axSky.plot([], [], "o", ms=13, color=GOLD, mec="#FFE9A8",
                              mew=1.8, zorder=8, linestyle="none")
    axSky.set_xlim(0, 360); axSky.set_ylim(0, ELMAX)
    axSky.set_xticks([0, 90, 180, 270, 360])
    axSky.set_xticklabels(["N", "E", "S", "W", "N"], fontsize=11)
    axSky.set_xlabel("azimuth", fontsize=11.5)
    axSky.set_ylabel("horizon elevation  (°)", fontsize=11.5)
    axSky.tick_params(labelsize=10)
    for s_ in ("top", "right"):
        axSky.spines[s_].set_visible(False)
    axSky.set_title("the skylines those rays make", fontsize=12.5, color=CHAR,
                    loc="left", pad=8, fontweight="bold")
    lg = axSky.legend(fontsize=10, frameon=True, edgecolor=GRID, loc="upper center",
                      ncols=2, handlelength=1.5)
    lg.get_frame().set_facecolor(WHITE)
    high_t = axSky.text(0, 0, "", fontsize=9, color=DIM, ha="center", va="center",
                        style="italic", zorder=9,
                        bbox=dict(boxstyle="round,pad=0.2", facecolor=WHITE,
                                  edgecolor="none", alpha=0.92))

    # ---------------- bottom right: what each site receives ---------------
    for s in SITES_:
        T = TS[s]
        axIns.plot(days, T["S_flat"], color=DIM, lw=1.2, ls=(0, (4, 3)), zorder=3)
        axIns.plot(days, T["S_shad"], color=COL[s], lw=1.9, zorder=4,
                   label=f"Apollo {s[1:]}")
        axIns.fill_between(days, T["S_shad"], T["S_flat"], where=T["blocked"],
                           color=COL[s], alpha=0.9, lw=0, zorder=5)
    cur = axIns.axvline(0, color=CHAR, lw=1.5, zorder=7)
    axIns.set_xlim(0, days[-1]); axIns.set_ylim(0, 1360)
    axIns.set_xlabel("days through the lunation", fontsize=11.5)
    axIns.set_ylabel("insolation  (W m$^{-2}$)", fontsize=11.5)
    axIns.tick_params(labelsize=10)
    for s_ in ("top", "right"):
        axIns.spines[s_].set_visible(False)
    axIns.grid(color=GRID, lw=0.8); axIns.set_axisbelow(True)
    axIns.set_title("what each site actually receives", fontsize=12.5,
                    color=CHAR, loc="left", pad=8, fontweight="bold")
    axIns.plot([], [], color=DIM, lw=1.2, ls=(0, (4, 3)), label="flat ground")
    lg2 = axIns.legend(fontsize=9.5, frameon=True, edgecolor=GRID,
                       loc="upper center", ncols=3, handlelength=1.4)
    lg2.get_frame().set_facecolor(WHITE)

    # ---------------- readouts, one column per site -----------------------
    day_t = axR.text(0.0, 0.99, "", fontsize=13, color=DIM, va="top",
                     fontweight="bold", family="monospace")
    ele_t, st_t, ls_t = {}, {}, {}
    for k, s in enumerate(SITES_):
        x = 0.02 + k * 0.50
        axR.text(x, 0.845, f"APOLLO {s[1:]}", fontsize=12, color=COL[s],
                 va="top", fontweight="bold")
        axR.text(x, 0.735, "Sun elevation", fontsize=10, color=DIM, va="top")
        ele_t[s] = axR.text(x, 0.685, "", fontsize=22, color=CHAR, va="top",
                            fontweight="bold")
        st_t[s] = axR.text(x, 0.505, "", fontsize=11.5, va="top", fontweight="bold")
        axR.text(x, 0.360, "energy lost so far", fontsize=10, color=DIM, va="top")
        ls_t[s] = axR.text(x, 0.305, "", fontsize=22, color=COL[s], va="top",
                           fontweight="bold")
        axR.text(x, 0.115, f"whole lunation: {D[s]['loss']*100:.2f}%",
                 fontsize=10, color=DIM, va="top")
    axR.text(0.02, 0.020, "Apollo 15 loses six times more sunlight to its own "
                          "horizon than Apollo 17", fontsize=10.5, color=CHAR,
             va="top", style="italic")

    idx = np.linspace(0, len(days) - 1, N).astype(int)

    def upd(k):
        i = idx[k]
        day_t.set_text(f"day {days[i]:4.1f} of {days[-1]:.1f}")
        hi_txt, hi_a = "", None
        for s in SITES_:
            T = TS[s]
            e, a, blk = T["elev"][i], T["A"][i], bool(T["blocked"][i])
            up = e > 0
            if up:
                a_ = np.radians(a)
                rays[s].set_data([0, RAY_KM*np.sin(a_)], [0, RAY_KM*np.cos(a_)])
                rays[s].set_color(CORAL if blk else GOLD)
            else:
                rays[s].set_data([], [])
            show = up and e <= ELMAX
            suns[s].set_data([a] if show else [], [e] if show else [])
            suns[s].set_color(DIM if blk else GOLD)
            suns[s].set_markeredgecolor(CHAR if blk else "#FFE9A8")
            ele_t[s].set_text(f"{e:+.1f}°" if up else "below")
            if not up:
                st_t[s].set_text("night"); st_t[s].set_color(DIM)
            elif blk:
                st_t[s].set_text("BLOCKED by terrain"); st_t[s].set_color(CORAL)
            else:
                st_t[s].set_text("sunlit"); st_t[s].set_color(FOREST)
            ls_t[s].set_text(f"{T['lost'][i]*100:.2f}%")
            if up and e > ELMAX and hi_a is None:
                hi_txt, hi_a = f"Sun at {e:.0f}° — above this panel", a
        cur.set_xdata([days[i], days[i]])
        high_t.set_text(hi_txt)
        if hi_a is not None:
            high_t.set_position((min(max(hi_a, 60.0), 300.0), ELMAX - 3.4))
        return ()

    return fig, upd


def main():
    D = load()
    fig, upd = build(D)
    out = AOGS / "results" / "shadowing_animation.gif"
    a = anim.FuncAnimation(fig, upd, frames=N, blit=False)
    a.save(out, writer=anim.PillowWriter(fps=12), dpi=DPI)
    plt.close(fig)
    print("  ->", out)

    slide = ROOT / "documents" / "gedes" / "defense" / "img" / "shadowing.gif"
    slide.write_bytes(out.read_bytes())
    print("  ->", slide)

    keys = [6, 17, 40, 62]
    fig2, axes = plt.subplots(len(keys), 1, figsize=(8.0, 4.3*len(keys)))
    for ax, k in zip(axes, keys):
        f, u = build(D)
        u(k); f.canvas.draw()
        ax.imshow(np.asarray(f.canvas.buffer_rgba())); ax.axis("off")
        plt.close(f)
    fig2.tight_layout(pad=0.4)
    fs = AOGS / "figures" / "shadowing_filmstrip.pdf"
    fig2.savefig(fs); plt.close(fig2)
    print("  ->", fs)


if __name__ == "__main__":
    main()
