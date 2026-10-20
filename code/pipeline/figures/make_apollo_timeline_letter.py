#!/usr/bin/env python3
"""Letter Figure 2: the sensor records and their stability windows.

For each site, one panel with the temperature record of every meter-scale
sensor (below the 80 cm cut) and, under it, one row per sensor: a thin line
where the sensor recorded and a thick bar over its stability window, the
stretch averaged into its equilibrium temperature. Both sites share one time
axis, in UTC, from the first Apollo 15 sample to the last Apollo 17 sample,
and both temperature panels span the same 3.5 K. Black only; every text at the
letter's body size (lunar.plotting.style.use_document_fonts).

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
import matplotlib.dates as mdates
import matplotlib.pyplot as plt

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

from lunar import _bootstrap as boot
boot.ensure_apollo_hfe(mission="a15", probes=())
boot.ensure_apollo_hfe(mission="a17", probes=())
from lunar.apollo_helpers import extract_sensor_stability
from lunar.config import SITES
from lunar.plotting import style
from lunar.plotting.style import C_GRID, assert_no_overlap

OUT = ROOT / ".." / "figures"
T_SPAN = 3.5            # K, the same temperature range in both site panels
GAP_DAYS = 20.0         # a pause longer than this breaks a record line
# layout [in]
LEFT, RIGHT = 1.12, 0.62           # sensor labels on the left, probe labels on the right
TITLE_H, TEMP_H, SEP_H = 0.26, 0.70, 0.10
ROW_H, PROBE_GAP, SITE_GAP, BOTTOM = 0.175, 0.10, 0.22, 0.62


def records(site):
    """Meter-scale sensors of a site, by probe then depth: (name, probe, depth, times, T, i_start)."""
    cfg = SITES[site]
    o = extract_sensor_stability(cfg["mission"], min_depth_cm=cfg["MIN_DEPTH_CM"])
    out = []
    for probe, tab in ((1, o["d1"]), (2, o["d2"])):
        for s in sorted((s for s in o["sensors"] if s["probe"] == probe and s["depth_cm"] >= cfg["MIN_DEPTH_CM"]),
                        key=lambda s: s["depth_cm"]):
            m = np.char.strip(tab["sensor"].astype(str)) == s["sensor"]
            t = np.array([np.datetime64(x[:19]) for x in tab["time_iso"][m]])
            out.append(dict(name=s["sensor"], probe=probe, depth=s["depth_cm"], t=t,
                            T=tab["T"][m].astype(float), i0=o["probe_data"][probe][s["sensor"]]["i_start"]))
    return out


def segments(t):
    """Index ranges of t without a pause longer than GAP_DAYS."""
    brk = np.where(np.diff(t).astype("timedelta64[s]").astype(float) > GAP_DAYS * 86400)[0]
    starts = np.r_[0, brk + 1]
    ends = np.r_[brk, len(t) - 1]
    return list(zip(starts, ends))


def main(out_name="fig_joint_apollo_timeline_probes.pdf", site_figures=False):
    style.use_document_fonts()
    data = {s: records(s) for s in ("A15", "A17")}
    t0 = min(r["t"][0] for r in data["A15"])
    t1 = max(r["t"][-1] for r in data["A17"])
    nrow = {s: len(data[s]) for s in data}
    h = BOTTOM + sum(TITLE_H + TEMP_H + SEP_H + nrow[s] * ROW_H + PROBE_GAP for s in data) + SITE_GAP
    W = style.TEXT_W - 0.04
    fig = plt.figure(figsize=(W, h))
    ax_x, ax_w = LEFT / W, (W - LEFT - RIGHT) / W
    y = h                                                  # running top edge [in]
    axes = []
    for k, site in enumerate(("A15", "A17")):
        rs = data[site]
        # temperature records
        y -= TITLE_H + TEMP_H
        at = fig.add_axes([ax_x, y / h, ax_w, TEMP_H / h])
        for r in rs:
            for a, b in segments(r["t"]):
                at.plot(r["t"][a:b + 1], r["T"][a:b + 1], color="black", lw=0.5)
        Tlo = min(np.percentile(r["T"][r["t"] > r["t"][0] + np.timedelta64(90, "D")], 0.5) for r in rs)
        Thi = max(np.percentile(r["T"][r["t"] > r["t"][0] + np.timedelta64(90, "D")], 99.5) for r in rs)
        mid = 0.5 * (Tlo + Thi)
        at.set_ylim(mid - T_SPAN / 2, mid + T_SPAN / 2)
        at.yaxis.set_major_locator(plt.MultipleLocator(1.0))
        at.set_ylabel("$T$ (K)")
        at.set_title(f"({'ab'[k]})  Apollo {site[1:]}", loc="left")
        # one row per sensor: where it recorded (thin) and its stability window (thick)
        y -= SEP_H + nrow[site] * ROW_H + PROBE_GAP
        ab = fig.add_axes([ax_x, y / h, ax_w, (nrow[site] * ROW_H + PROBE_GAP) / h], sharex=at)
        ypos, labels, yy = [], [], 0.0
        for i, r in enumerate(rs):
            if i and r["probe"] != rs[i - 1]["probe"]:
                yy += PROBE_GAP / ROW_H
            for a, b in segments(r["t"]):
                ab.plot([r["t"][a], r["t"][b]], [yy, yy], color="black", lw=0.6, solid_capstyle="butt")
            tw = r["t"][r["i0"]:]
            for a, b in segments(tw):
                ab.plot([tw[a], tw[b]], [yy, yy], color="black", lw=5.5, solid_capstyle="butt")
            ypos.append(yy); labels.append(f"{r['name']}, {r['depth']:.0f} cm"); yy += 1.0
        ab.set_ylim(yy - 0.4, -0.6)
        ab.set_yticks(ypos, labels)
        ab.tick_params(axis="y", length=0)
        for probe in (1, 2):
            ys = [p for p, r in zip(ypos, rs) if r["probe"] == probe]
            ab.text(1.01, 0.5 * (min(ys) + max(ys)), f"probe {probe}", transform=ab.get_yaxis_transform(),
                    ha="left", va="center")
        for ax in (at, ab):
            ax.set_xlim(t0, t1)
            ax.grid(axis="x", color=C_GRID, lw=0.6)
            ax.set_axisbelow(True)
        at.tick_params(labelbottom=False)
        if k == 0:
            ab.tick_params(labelbottom=False)
        y -= SITE_GAP
        axes += [at, ab]
    # one UTC axis for both sites: its two ends are the first and the last sample
    years = [np.datetime64(f"{yr}-01-01") for yr in range(1972, 1978)]
    ab = axes[-1]
    ab.set_xticks(years, minor=True)
    ends = [t0.astype("datetime64[D]"), t1.astype("datetime64[D]")]
    major = [ends[0]] + years[1:-1] + [ends[1]]
    fmt = lambda d: d.astype(object).strftime("%-d %b %Y")
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
