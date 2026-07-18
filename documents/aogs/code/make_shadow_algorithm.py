"""DETAILED step-by-step illustration of the DEM shadowing algorithm
(real Apollo 15 data), 6 panels with the exact conditions at each step:
  1  cast 90 rays (one every 4 deg) over the DEM
  2  sample the DEM per step: 1-km steps, bilinear interpolation of the grid
  3  subtract the sphere-curvature drop; angle to each sample; horizon = max
  4  all 90 azimuths -> the skyline
  5  the blocking condition: Sun below the skyline -> beam = 0
  6  the parameters/conditions, as run

Writes illus_shadow_algorithm.{pdf,png} in aogs/illustrations/.
Move-proof paths. Run:  <repo>/.venv/bin/python make_shadow_algorithm.py
"""
import pathlib
import sys

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.colors import LightSource
from matplotlib.gridspec import GridSpec

_root = next(a for a in pathlib.Path(__file__).resolve().parents
             if (a / "code" / "src" / "lunar").is_dir())
sys.path.insert(0, str(_root / "code" / "src"))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[0] / "compute"))
from lunar.plotting.style import (C_A15, C_CHAR, C_DIM, C_GRID, C_CORAL,  # noqa: E402
                                  C_TEAL, C_PLUM, fmt_axis)
from lunar.config import SITES, DT_STEP  # noqa: E402
from lunar.solver import periodic_time_grid  # noqa: E402
import s1_sensitivity as aogs  # noqa: E402

AOGS = next(a for a in pathlib.Path(__file__).resolve().parents if a.name == "aogs")
OUT = AOGS / "figures" / "drafts"; OUT.mkdir(exist_ok=True)
R = aogs.R_MOON_KM


def main():
    s = SITES["A15"]; lat0, lon0 = s["lat"], s["lon"]
    dem, ppd = aogs.load_dem()
    km_per_px = 2 * np.pi * R / 360.0 / ppd
    az, hor = aogs.horizon_profile(dem, ppd, lat0, lon0)
    a_deg = float(az[np.argmax(hor)]); a = np.radians(a_deg)

    dr = min(1.0, km_per_px)
    r = np.arange(dr, 60.0 + dr, dr)
    dlat = np.degrees((r / R) * np.cos(a))
    dlon = np.degrees((r / R) * np.sin(a) / max(np.cos(np.radians(lat0)), 1e-6))
    h0 = float(aogs._dem_sample(dem, ppd, lat0, lon0))
    hh = np.asarray(aogs._dem_sample(dem, ppd, lat0 + dlat, lon0 + dlon))
    drop = r ** 2 / (2.0 * R)
    ang = np.degrees(np.arctan2(hh - h0 - drop, r))
    ih = int(np.argmax(ang))

    t = periodic_time_grid(DT_STEP)
    elev, A = aogs.sun_track(lat0, t)
    hor_at = np.interp(A, az, hor, period=360.0)
    days = np.asarray(t) / 86400.0
    up = elev >= 0
    blk = up & (elev <= hor_at)

    fig = plt.figure(figsize=(14.5, 9.4))
    gs = GridSpec(2, 3, figure=fig, hspace=0.72, wspace=0.30,
                  left=0.045, right=0.985, top=0.915, bottom=0.055)
    fig.suptitle("The shadowing algorithm, step by step (real Apollo 15 terrain)",
                 fontsize=15.5, fontweight="bold", x=0.045, ha="left")

    def cond(ax, txt):                      # a small condition tag under a panel
        ax.text(0.0, -0.22, txt, transform=ax.transAxes, ha="left", va="top",
                fontsize=7.8, color=C_DIM)

    # ---- 1. cast rays -------------------------------------------------------
    ax1 = fig.add_subplot(gs[0, 0])
    half = 1.4
    r0 = int((90 - lat0 - half) * ppd); r1 = int((90 - lat0 + half) * ppd)
    c0 = int((lon0 + 180 - half) * ppd); c1 = int((lon0 + 180 + half) * ppd)
    crop = dem[r0:r1, c0:c1] * aogs.DEM_SCALE_KM
    shaded = LightSource(azdeg=315, altdeg=40).shade(
        crop, cmap=plt.get_cmap("gist_earth"), blend_mode="soft", vert_exag=25)
    ax1.imshow(shaded, extent=(lon0 - half, lon0 + half, lat0 - half, lat0 + half),
               origin="upper")
    for aa in np.radians(np.arange(0, 360, 12)):
        rr = np.linspace(0, 55, 30)
        ax1.plot(lon0 + np.degrees((rr / R) * np.sin(aa) / np.cos(np.radians(lat0))),
                 lat0 + np.degrees((rr / R) * np.cos(aa)), "-", color="white",
                 lw=0.6, alpha=0.55)
    ax1.plot(lon0 + dlon, lat0 + dlat, "-", color=C_CORAL, lw=2.0)
    ax1.plot(lon0, lat0, "o", color="white", mec=C_A15, mew=2.2, ms=11)
    ax1.plot(lon0 + dlon[ih], lat0 + dlat[ih], "*", color=C_PLUM, ms=15, mec=C_CHAR,
             mew=0.6)
    fmt_axis(ax1, xlabel="longitude (°E)", ylabel="latitude (°N)",
             title="1 · cast 90 rays from the site")
    cond(ax1, "one ray every 360°/90 = 4°, from North; marched out to 150 km")

    # ---- 2. per-step DEM sampling (bilinear) --------------------------------
    ax2 = fig.add_subplot(gs[0, 1])
    hz = 4.6 / ppd                       # ~4.6 px each way
    latc, lonc = lat0 + dlat[6], lon0 + dlon[6]
    rr0 = int((90 - latc - hz) * ppd); rr1 = int((90 - latc + hz) * ppd)
    cc0 = int((lonc + 180 - hz) * ppd); cc1 = int((lonc + 180 + hz) * ppd)
    zc = dem[rr0:rr1, cc0:cc1] * aogs.DEM_SCALE_KM
    ext = (lonc - hz, lonc + hz, latc - hz, latc + hz)
    ax2.imshow(zc, extent=ext, origin="upper", cmap="gist_earth", aspect="auto")
    # pixel-boundary grid
    for k in range(cc0, cc1 + 1):
        ax2.axvline((k / ppd) - 180.0, color="white", lw=0.5, alpha=0.6)
    for k in range(rr0, rr1 + 1):
        ax2.axhline(90.0 - (k / ppd), color="white", lw=0.5, alpha=0.6)
    msk = (lon0 + dlon > ext[0]) & (lon0 + dlon < ext[1]) & \
          (lat0 + dlat > ext[2]) & (lat0 + dlat < ext[3])
    ax2.plot(lon0 + dlon[msk], lat0 + dlat[msk], "-", color=C_CORAL, lw=1.8)
    ax2.plot(lon0 + dlon[msk], lat0 + dlat[msk], ".", color=C_CHAR, ms=6)  # 1-km samples
    # one sample + its 4 bilinear pixel centres
    si = np.where(msk)[0][len(np.where(msk)[0]) // 2]
    ps, pl = lon0 + dlon[si], lat0 + dlat[si]
    cf = (ps + 180) * ppd - 0.5; rf = (90 - pl) * ppd - 0.5
    for dcc in (0, 1):
        for drr in (0, 1):
            pxc = (int(np.floor(cf)) + dcc + 0.5) / ppd - 180
            pyc = 90 - (int(np.floor(rf)) + drr + 0.5) / ppd
            ax2.plot(pxc, pyc, "s", color=C_PLUM, ms=7, mfc="none", mew=1.6)
    ax2.plot(ps, pl, "*", color=C_PLUM, ms=14, mec=C_CHAR, mew=0.6)
    ax2.set_xlim(ext[0], ext[1]); ax2.set_ylim(ext[2], ext[3])
    fmt_axis(ax2, xlabel="longitude (°E)", ylabel="latitude (°N)",
             title="2 · sample the DEM at each step")
    cond(ax2, f"1-km steps (16 ppd ≈ {km_per_px:.1f} km/px); height = bilinear interp of the 4 nearest pixels (□)")

    # ---- 3. curvature drop + angle -----------------------------------------
    ax3 = fig.add_subplot(gs[0, 2])
    ax3.fill_between(r, 0, hh - h0, color=C_GRID, lw=0, zorder=1)
    ax3.plot(r, hh - h0, color=C_DIM, lw=1.4, zorder=2, label="terrain above site")
    ax3.plot(r, drop, color=C_TEAL, lw=1.6, ls=(0, (5, 3)), zorder=2,
             label=r"drop $r^2/2R$")
    sight = np.tan(np.radians(ang[ih])) * r + drop
    mm = sight < (hh[ih] - h0) * 1.15
    ax3.plot(r[mm], sight[mm], color=C_PLUM, lw=1.8, zorder=3,
             label=fr"horizon  $\theta_h={ang[ih]:.1f}°$")
    ax3.plot(r[ih], hh[ih] - h0, "*", color=C_PLUM, ms=14, mec=C_CHAR, mew=0.6, zorder=4)
    ax3.plot(0, 0, "o", color=C_A15, ms=7, zorder=4)
    ax3.set_xlim(0, r.max())
    ax3.set_ylim(min(0, (hh - h0).min()) - 0.05, (hh - h0).max() * 1.28)
    fmt_axis(ax3, xlabel="distance r (km)", ylabel="height above site (km)",
             title="3 · curvature drop, then angle")
    ax3.legend(loc="upper left", fontsize=7.5, frameon=True, edgecolor=C_GRID)
    cond(ax3, r"$\theta(r)=\arctan\dfrac{h(r)-h_0-r^2/2R}{r}$;   "
              r"$\theta_h=\max_r\theta$, floored at 0")

    # ---- 4. skyline ---------------------------------------------------------
    ax4 = fig.add_subplot(gs[1, 0], projection="polar")
    azr = np.radians(az)
    ax4.plot(np.append(azr, azr[0]), np.append(hor, hor[0]), color=C_A15, lw=2.2)
    ax4.fill(np.append(azr, azr[0]), np.append(hor, hor[0]), color=C_A15, alpha=0.18)
    ax4.plot(np.radians(A[up]), elev[up], color=C_DIM, lw=1.0, ls=":", label="Sun path")
    ax4.plot(np.radians(A[blk]), elev[blk], "s", color=C_PLUM, ms=4, label="blocked")
    ax4.set_theta_zero_location("N"); ax4.set_theta_direction(-1)
    ax4.set_rmax(1.3 * float(hor.max())); ax4.set_rlabel_position(202)
    ax4.tick_params(labelsize=6.5)
    ax4.set_title("4 · all 90 rays = skyline (radius = °)", fontsize=10, pad=12)
    ax4.legend(loc="lower center", bbox_to_anchor=(0.5, -0.20), fontsize=7.5, ncols=2,
               frameon=True, edgecolor=C_GRID)

    # ---- 5. blocking condition ---------------------------------------------
    ax5 = fig.add_subplot(gs[1, 1])
    ax5.plot(days[up], elev[up], color=C_CORAL, lw=2.2, label=r"Sun elevation $e(t)$")
    ax5.plot(days[up], hor_at[up], color=C_A15, lw=1.8, ls=(0, (5, 3)),
             label=r"skyline $\theta_h$ at Sun az.")
    ax5.fill_between(days, 0, elev, where=blk, color=C_PLUM, alpha=0.30, lw=0,
                     label="blocked")
    ax5.set_ylim(0, None)
    fmt_axis(ax5, xlabel="time (Earth days)", ylabel="angle above horizon (°)",
             title="5 · Sun below skyline = shadow")
    ax5.legend(loc="upper right", fontsize=7.5, frameon=True, edgecolor=C_GRID)
    cond(ax5, r"keep beam if $e(t)>\theta_h(A(t))$, else $S=0$;  "
              r"$S=S_0\sin e$ on the lit dayside")

    # ---- 6. the conditions, listed -----------------------------------------
    ax6 = fig.add_subplot(gs[1, 2]); ax6.axis("off")
    ax6.add_patch(mpatches.FancyBboxPatch((0, 0), 1, 1, transform=ax6.transAxes,
                  boxstyle="round,pad=0.0,rounding_size=0.02", fc="#F5F3EF",
                  ec=C_TEAL, lw=1.2, clip_on=False))
    ax6.text(0.05, 0.95, "6 · the conditions, as run", transform=ax6.transAxes,
             fontsize=11, fontweight="bold", color=C_TEAL, va="top")
    lines = [
        (r"$\bullet$ 90 rays, one every $4°$, from North", None),
        (r"$\bullet$ each ray: $r = 1 \to 150$ km in $1$-km steps", None),
        (r"$\bullet$ DEM = LOLA 16 ppd $\approx 1.9$ km/pixel", None),
        (r"$\bullet$ height $h(r)$ = bilinear interp of the DEM", None),
        (r"$\bullet$ offsets on the sphere ($R=1737.4$ km):", None),
        (r"    $\Delta\varphi=\frac{r}{R}\cos a,\ \Delta\lambda=\frac{r}{R}\frac{\sin a}{\cos\varphi_0}$", None),
        (r"$\bullet$ curvature drop $=r^2/2R$", None),
        (r"$\bullet$ angle $\theta(r)=\arctan\frac{h-h_0-r^2/2R}{r}$", None),
        (r"$\bullet$ horizon $\theta_h=\max_r\theta$, floored at $0$", None),
        (r"$\bullet$ Sun: declination $0$; $e(t),A(t)$ over 29.5 d", None),
        (r"$\bullet$ blocked when $e(t)\leq\theta_h(A(t))$", None),
    ]
    y = 0.85
    for txt, _ in lines:
        ax6.text(0.06, y, txt, transform=ax6.transAxes, fontsize=9, color=C_CHAR,
                 va="top")
        y -= 0.078

    fig.savefig(OUT / "illus_shadow_algorithm.pdf")
    fig.savefig(OUT / "illus_shadow_algorithm.png", dpi=300)
    plt.close(fig)
    print("wrote", OUT / "illus_shadow_algorithm.pdf", "+ .png",
          f"| az {a_deg:.0f}°, horizon {ang[ih]:.1f}°, {km_per_px:.2f} km/px")


if __name__ == "__main__":
    main()
