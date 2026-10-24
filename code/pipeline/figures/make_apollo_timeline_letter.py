#!/usr/bin/env python3
"""Letter Figure 1: the sensor records, their stability windows and the gaps.

For each site, one panel with the temperature record of every meter-scale
sensor (below the 80 cm cut) and, under it, one row per sensor: a thin line
where the sensor recorded and a thick bar over its stability window, the
stretch averaged into its equilibrium temperature. Both sites share one time
axis, in UTC, from the first Apollo 15 sample to the last Apollo 17 sample,
and both temperature panels span the same 3.5 K.

Colours are those of the earlier design of this figure: each sensor is shaded
in its site's hue, light (C_FOREST_L, C_CORAL_L) for the shallowest sensor
and dark (C_FOREST, C_CORAL) for the deepest, and a window bar is outlined in
its probe's colour (probe 1 C_FOREST / C_CORAL, probe 2 C_A15_2 / C_A17_2).
The texture of a window bar gives the thermometer type: solid for a
gradient bridge (TG), dotted for a ring bridge (TR): a row of greyish-white
dots along the bar, one per bar height (an X would read as "crossed out").
The no-data bands keep the diagonal hatch.
The sensors above the 80 cm cut, in the borestem zone and not used, get
gray rows without a window and no temperature trace (their daily swings
would swamp the shared 3.5 K scale): five resistance thermometers at
Apollo 15 and the four thermocouples (TC) on the Apollo 17 probe cables,
14-67 cm, read to December 1974. The Apollo 15 thermocouples are not in
the record.
A black bracket groups each probe's rows on the right, and a
dashed line marks where the Apollo 17 record starts (the shared axis starts
with Apollo 15). Text is black, at the letter's body size.

Hatched bands mark where a site has no data, with what happened written in
the band (CAUSE; Nagihara et al., 2018, Sections 2-3): no tapes survive for
January-March 1975 and July 1975-February 1976 (both sites); the Apollo 15
instrument overheated from February 1976 and was switched off in January
1977; from August 1976 to April 1977 the Apollo 17 data channel was used by
the Lunar Seismic Profiling Experiment. A note marks the Apollo 15 TG11B
record, whose window falls in 1975: its 1971-1974 values, faulty in the
original archive (Nagihara et al., 2018) and corrected in the record used
here (St. Clair et al., 2020), are drawn dashed. The band edges
are the gaps found in the record itself (GAP_DAYS).

Reads the Apollo record through lunar.apollo_helpers (the same windows as
results/stability_windows.json). Data only, no model output.

Run with::

  python3 pipeline/figures/make_apollo_timeline_letter.py
"""
from __future__ import annotations
import sys
import pathlib

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.colors import to_rgb
from matplotlib.patches import Rectangle
from matplotlib.transforms import blended_transform_factory

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

from lunar import _bootstrap as boot
boot.ensure_apollo_hfe(mission="a15", probes=())
boot.ensure_apollo_hfe(mission="a17", probes=())
from lunar.apollo_helpers import A15_TG11_FIRST_VALID, A15_TG11_SENSORS, extract_sensor_stability
from lunar.config import SITES
from lunar.plotting import style
from lunar.plotting.style import (C_A15_2, C_A17_2, C_CHAR, C_CORAL, C_CORAL_L, C_NEUTRAL,
                                  C_DIM, C_FOREST, C_FOREST_L, C_GRID, assert_no_overlap)

OUT = ROOT / ".." / "figures"
T_SPAN = 3.5            # K, the same temperature range in both site panels
GAP_DAYS = 20.0         # a pause longer than this breaks a record line
RAMP = {"A15": (C_FOREST_L, C_FOREST), "A17": (C_CORAL_L, C_CORAL)}   # shallow -> deep
EDGE = {("A15", 1): C_FOREST, ("A15", 2): C_A15_2, ("A17", 1): C_CORAL, ("A17", 2): C_A17_2}
BAR_H = 0.46                       # window-bar height, in rows
DOTTED = {"TR"}                    # thermometer types whose window bar is dotted (TG bars stay solid)
DOT_COLOR = tuple(0.5 + 0.5 * np.array(to_rgb(C_GRID)))     # the dots: greyish white (C_GRID halfway to white)
DOT_MS = 2.1                       # dot diameter [pt], about 40% of the bar height
LS_UNUSED = (0, (3.0, 1.6))        # TG11B before 1975: dashed, not in its window
# layout [in]
LEFT, RIGHT = 1.12, 0.72           # sensor labels on the left, probe brackets and labels on the right
TITLE_H, TEMP_H, SEP_H = 0.24, 0.56, 0.08
ROW_H, PROBE_GAP, SITE_GAP, BOTTOM = 0.162, 0.08, 0.16, 0.60


def records(site):
    """Sensors of a site, by probe then depth.

    Returns (used, shallow): the sensors below the cut, as (name, probe, depth, times, T, i_start), and
    those above it, in the borestem zone and not used, as (name, probe, depth, times): resistance
    thermometers (TG, TR) and thermocouples (TC).
    """
    cfg = SITES[site]
    o = extract_sensor_stability(cfg["mission"], min_depth_cm=cfg["MIN_DEPTH_CM"])
    out, shallow = [], []
    for probe, tab in ((1, o["d1"]), (2, o["d2"])):
        names = np.char.strip(tab["sensor"].astype(str))
        for s in sorted((s for s in o["sensors"] if s["probe"] == probe and s["depth_cm"] >= cfg["MIN_DEPTH_CM"]),
                        key=lambda s: s["depth_cm"]):
            m = names == s["sensor"]
            t = np.array([np.datetime64(x[:19]) for x in tab["time_iso"][m]])
            out.append(dict(name=s["sensor"], probe=probe, depth=s["depth_cm"], t=t,
                            T=tab["T"][m].astype(float), i0=o["probe_data"][probe][s["sensor"]]["i_start"]))
        for name in sorted(set(names)):
            m = names == name
            depth = float(tab["depth_cm"][m][0])
            if name[:2] in ("TG", "TR", "TC") and depth < cfg["MIN_DEPTH_CM"]:
                t = np.array([np.datetime64(x[:19]) for x in tab["time_iso"][m]])
                shallow.append(dict(name=name, probe=probe, depth=depth, t=t, shallow=True))
    return out, shallow


def shade(site, depth, depths):
    """The site's hue, light for the shallowest of its sensors and dark for the deepest."""
    light, dark = (np.array(to_rgb(c)) for c in RAMP[site])
    f = (depth - min(depths)) / (max(depths) - min(depths))       # 0 shallow .. 1 deep
    return tuple((1 - f) * light + f * dark)


def segments(t):
    """Index ranges of t without a pause longer than GAP_DAYS."""
    brk = np.where(np.diff(t).astype("timedelta64[s]").astype(float) > GAP_DAYS * 86400)[0]
    starts = np.r_[0, brk + 1]
    ends = np.r_[brk, len(t) - 1]
    return list(zip(starts, ends))


def site_gaps(rs):
    """Pauses longer than GAP_DAYS in which no sensor of the site recorded: [(start, end)]."""
    t = np.unique(np.concatenate([r["t"] for r in rs]))
    return [(t[a], t[b]) for (_, a), (b, _) in zip(segments(t)[:-1], segments(t)[1:])]


def no_data_bands(data, t1):
    """The numbered no-data bands of each site (see the module docstring)."""
    g15, g17 = site_gaps(data["A15"]), site_gaps(data["A17"])
    end15 = max(r["t"][-1] for r in data["A15"])
    day = lambda a, b: abs((a - b).astype("timedelta64[s]").astype(float)) < 86400
    assert len(g15) == 1 and len(g17) == 3 and day(g15[0][0], g17[0][0]) and day(g15[0][1], g17[0][1]), (g15, g17)
    assert day(g17[1][0], end15)              # both sites stop on the same day in 1975
    return {"A15": [(*g15[0], "lost"), (end15, g17[1][1], "lost"), (g17[1][1], t1, "off")],
            "A17": [(*g17[0], "lost"), (*g17[1], "lost"), (*g17[2], "lspe")]}


# what happened in each no-data band (Nagihara et al., 2018, Sections 2-3), and how it is set:
# "v" upright in the middle of the sensor rows, "h" across the lower part of a wide band
CAUSE = {"lost": ("tapes lost", "v"),
         "off": ("instrument\nfailing; off\nfrom Jan 1977", "h"),
         "lspe": ("data channel used by the\nLunar Seismic Profiling Experiment", "v")}
TG11_NOTE = "TG11B: only its\n1975 readings used;\n1971–74 excluded"


def unused(site, r, t_end):
    """True for the A15 TG11 values before 1975, outside TG11B's window (drawn dotted)."""
    return site == "A15" and r["name"] in A15_TG11_SENSORS and t_end < np.datetime64(A15_TG11_FIRST_VALID)


def fmt(d):
    """A day as it is printed on the figure, e.g. 31 Jul 1971."""
    return d.astype(object).strftime("%-d %b %Y")


def cause(ax, a, b, key):
    """Write what happened in the band [a, b] of the sensor-row panel ax, on a white patch over the hatch."""
    text, how = CAUSE[key]
    x = a + (b - a) / 2
    tr = blended_transform_factory(ax.transData, ax.transAxes)
    ax.text(x, 0.5 if how == "v" else 0.22, text, transform=tr, rotation=90 if how == "v" else 0,
            ha="center", va="center", multialignment="center", color=C_CHAR, zorder=6,
            bbox=dict(boxstyle="square,pad=0.06", fc="white", ec="none"))


def main(out_name="fig_joint_apollo_timeline_probes.pdf", site_figures=False):
    style.use_document_fonts()
    got = {s: records(s) for s in ("A15", "A17")}
    data = {s: got[s][0] for s in got}                     # the sensors used: temperature panels, bands
    rows = {s: sorted(got[s][0] + got[s][1], key=lambda r: (r["probe"], r["depth"])) for s in got}
    t0 = min(r["t"][0] for r in data["A15"])
    t1 = max(r["t"][-1] for r in data["A17"])
    bands = no_data_bands(data, t1)
    nrow = {s: len(rows[s]) for s in rows}
    h = BOTTOM + sum(TITLE_H + TEMP_H + SEP_H + nrow[s] * ROW_H + PROBE_GAP for s in data) + SITE_GAP
    W = style.TEXT_W - 0.04
    fig = plt.figure(figsize=(W, h))
    ax_x, ax_w = LEFT / W, (W - LEFT - RIGHT) / W
    # spacing of the dots in a dotted window bar [days]: one bar height on the page
    dot_dx = BAR_H * ROW_H / (W - LEFT - RIGHT) * ((t1 - t0) / np.timedelta64(1, "D"))
    y = h                                                  # running top edge [in]
    axes = []
    for k, site in enumerate(("A15", "A17")):
        rs = data[site]
        # temperature records
        y -= TITLE_H + TEMP_H
        at = fig.add_axes([ax_x, y / h, ax_w, TEMP_H / h])
        dep = [r["depth"] for r in rs]
        for r in sorted(rs, key=lambda r: r["depth"]):          # deep traces drawn last, on top
            for a, b in segments(r["t"]):
                at.plot(r["t"][a:b + 1], r["T"][a:b + 1], color=shade(site, r["depth"], dep), lw=0.7,
                        ls=LS_UNUSED if unused(site, r, r["t"][b]) else "-")
        Tlo = min(np.percentile(r["T"][r["t"] > r["t"][0] + np.timedelta64(90, "D")], 0.5) for r in rs)
        Thi = max(np.percentile(r["T"][r["t"] > r["t"][0] + np.timedelta64(90, "D")], 99.5) for r in rs)
        mid = 0.5 * (Tlo + Thi)
        at.set_ylim(mid - T_SPAN / 2, mid + T_SPAN / 2)
        at.yaxis.set_major_locator(plt.MultipleLocator(1.0))
        at.set_ylabel("$T$ (K)")
        at.set_title(f"({'ab'[k]})  Apollo {site[1:]}", loc="left")
        # one row per sensor: where it recorded (thin) and its stability window (thick, outlined by probe)
        y -= SEP_H + nrow[site] * ROW_H + PROBE_GAP
        ab = fig.add_axes([ax_x, y / h, ax_w, (nrow[site] * ROW_H + PROBE_GAP) / h], sharex=at)
        ypos, labels, yy = [], [], 0.0
        rr = rows[site]
        for i, r in enumerate(rr):
            if i and r["probe"] != rr[i - 1]["probe"]:
                yy += PROBE_GAP / ROW_H
            if r.get("shallow"):     # above the cut, in the borestem zone: gray, no window
                for a, b in segments(r["t"]):
                    ab.plot([r["t"][a], r["t"][b]], [yy, yy], color=C_NEUTRAL, lw=0.9, solid_capstyle="butt")
                ypos.append(yy); labels.append(f"{r['name']}, {r['depth']:.0f} cm"); yy += 1.0
                continue
            c = shade(site, r["depth"], dep)
            for a, b in segments(r["t"]):
                ab.plot([r["t"][a], r["t"][b]], [yy, yy], color=c, lw=1.1 if unused(site, r, r["t"][b]) else 0.9,
                        ls=LS_UNUSED if unused(site, r, r["t"][b]) else "-", solid_capstyle="butt")
            tw = r["t"][r["i0"]:]
            for a, b in segments(tw):
                x0, x1 = mdates.date2num(tw[a]), mdates.date2num(tw[b])
                bar = Rectangle((x0, yy - BAR_H / 2), x1 - x0, BAR_H, facecolor=c, edgecolor=EDGE[site, r["probe"]],
                                lw=0.8, zorder=3)
                ab.add_patch(bar)
                if r["name"][:2] in DOTTED:
                    # a row of dots along the bar's middle, one bar height apart, starting half a step in
                    # (a matplotlib hatch is anchored to the page, so each row would show a different slice of it)
                    xd = np.arange(x0 + 0.5 * dot_dx, x1, dot_dx)
                    dots, = ab.plot(xd, np.full_like(xd, yy), ls="none", marker="o", ms=DOT_MS, mew=0,
                                    color=DOT_COLOR, zorder=3.5)
                    dots.set_clip_path(bar)
            ypos.append(yy); labels.append(f"{r['name']}, {r['depth']:.0f} cm"); yy += 1.0
        ab.set_ylim(yy - 0.4, -0.6)
        ab.set_yticks(ypos, labels)
        ab.tick_params(axis="y", length=0)
        for lab, r in zip(ab.get_yticklabels(), rr):
            if r.get("shallow"):
                lab.set_color(C_DIM)
        # a black bracket spans each probe's rows, named beside it
        ax_w_in = W - LEFT - RIGHT
        bx0, bx1, lx = (1 + d / ax_w_in for d in (0.04, 0.09, 0.13))
        for probe in (1, 2):
            ys = [p for p, r in zip(ypos, rr) if r["probe"] == probe]
            y0, y1 = min(ys) - 0.38, max(ys) + 0.38
            ab.plot([bx0, bx1, bx1, bx0], [y0, y0, y1, y1], color=C_CHAR, lw=1.2,
                    transform=ab.get_yaxis_transform(), clip_on=False, solid_joinstyle="miter")
            ab.text(lx, 0.5 * (y0 + y1), f"probe {probe}", transform=ab.get_yaxis_transform(),
                    ha="left", va="center")
        if site == "A17":   # the shared axis starts with Apollo 15: mark where Apollo 17 begins
            t_start = min(r["t"][0] for r in rs)
            for ax in (at, ab):
                ax.axvline(t_start, color=C_CHAR, lw=0.8, ls=(0, (3, 2)), zorder=1)
            at.annotate(f"record starts\n{fmt(t_start.astype('datetime64[D]'))}", xy=(mdates.date2num(t_start), 0.5),
                        xycoords=at.get_xaxis_transform(), xytext=(-4, 0), textcoords="offset points",
                        ha="right", va="center", multialignment="right", color=C_CHAR, zorder=6,
                        bbox=dict(boxstyle="square,pad=0.06", fc="white", ec="none"))
        # where the site has no data: hatched, with what happened written in the sensor rows
        for a, b, key in bands[site]:
            for ax in (at, ab):
                band = ax.axvspan(a, b, fill=False, hatch="//", ec=C_NEUTRAL, lw=0.5, zorder=0.5)
                if hasattr(band, "set_hatch_linewidth"):        # matplotlib >= 3.10
                    band.set_hatch_linewidth(0.5)
            cause(ab, a, b, key)
        if site == "A15":   # the TG11 bridge: its 1971-74 values, and why its window is in 1975
            a, b, _ = bands[site][-1]
            r = next(r for r in rr if r["name"] == "TG11B")
            ab.annotate(TG11_NOTE, xy=(r["t"][-1], ypos[rr.index(r)]), xytext=(a + (b - a) / 2, -0.45),
                        ha="center", va="top", multialignment="center", color=C_CHAR, zorder=6,
                        bbox=dict(boxstyle="square,pad=0.06", fc="white", ec="none"),
                        arrowprops=dict(arrowstyle="-|>", color=C_CHAR, lw=0.6, shrinkA=2, shrinkB=2,
                                        relpos=(0.0, 0.85)))
        for ax in (at, ab):
            ax.set_xlim(t0, t1)
            ax.set_axisbelow(True)
        at.tick_params(labelbottom=False)
        if k == 0:
            ab.tick_params(labelbottom=False)
        y -= SITE_GAP
        axes += [at, ab]
    # one UTC axis for both sites: its two ends are the first and the last sample
    years = [np.datetime64(f"{yr}-01-01") for yr in range(1972, 1978)]
    ab = axes[-1]
    ends = [t0.astype("datetime64[D]"), t1.astype("datetime64[D]")]
    major = [ends[0]] + years[1:-1] + [ends[1]]
    ab.set_xticks(major, [fmt(ends[0])] + [str(d)[:4] for d in years[1:-1]] + [fmt(ends[1])])
    for lab, ha in zip(ab.get_xticklabels()[::len(major) - 1], ("left", "right")):
        lab.set_horizontalalignment(ha)
    ab.set_xlabel("Date (UTC)")
    for ax in axes:
        ax.set_xticks(major)
        ax.set_xticks(years, minor=True)
        ax.grid(axis="x", which="both", color=C_GRID, lw=0.6)
    fig.canvas.draw()
    for ax in axes:
        assert_no_overlap(ax)
    OUT.mkdir(parents=True, exist_ok=True)
    dst = OUT / out_name
    fig.savefig(dst)
    plt.close(fig)
    print(f"wrote {dst.resolve()}  ({W:.2f} x {h:.2f} in)")


if __name__ == "__main__":
    main()
