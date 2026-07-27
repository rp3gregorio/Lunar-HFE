#!/usr/bin/env python3
"""Build the per-probe Apollo HFE stability-window timeline figure
(``../figures/fig_apollo_timeline_probes.pdf`` -- the LETTER's
Figure 3). RESTORED 2026-07-04 from the canonical Lunar-HFE repo at the
user's request: the letter keeps this information-dense original design
(all sensors, event bands, per-sensor Gantt windows), while the guidebook
uses the slim redesign in make_apollo_timeline.py. The two documents share
a symlinked figures/ directory, hence the distinct filename.

The figure shows, for each of the four HFE probes (A15-Probe1,
A15-Probe2, A17-Probe1, A17-Probe2):

  * Upper sub-panel: every sensor's raw temperature record -- kept
    (sub-borestem) sensors depth-coloured, borestem-zone sensors as a
    pale grey underlay -- with documented data-quality events shown as
    translucent coral bands annotated with the cause (drilling /
    emplacement transient; ALSEP telemetry outages; the probe-2 and
    end-of-mission gaps).  Sources: Langseth et al. (1976); Grott et al.
    (2010); Nagihara et al. (2018).  The OLS-fit long-term drift on the
    deepest sensor's window is drawn dashed and annotated.
  * Lower sub-panel: per-sensor Gantt strip showing each sensor's
    selected stability window inside its full archived record (borestem
    sensors grayed and excluded; kept sensors labeled with their
    window-mean T_eq).

PROVENANCE (2026-07-04): the drawing code for this figure originally
lived in a notebook cell (notebooks/phase1_letter.ipynb) that no longer
exists in the canonical repo or on disk; only the rendered PDF survived
(fetched from Lunar-HFE@main:results/figures/fig_apollo_timeline.pdf
and archived at docs/assets/fig_apollo_timeline_probes_archived.pdf).

REIMPLEMENTED (2026-07-05): this script now redraws the figure from the
live data, faithfully to the archived original.  Layout geometry, axis
limits, the depth colormap, and the event-band intervals were measured
from the archived PDF's vector content (PyMuPDF); every physical number
(T_eq, OLS slopes, depths, record extents, window starts) comes from
``lunar.apollo_helpers.extract_sensor_stability`` at build time.  All
values reproduce the archive except one label the original got wrong:
the archived A17-Probe2 row "TR21A" repeats probe-1's T_eq (255.67 K);
the correct window mean for TR21A is 256.24 K and is what this script
prints.  The figure is DATA-ONLY (no solver output).

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
from matplotlib.collections import LineCollection
from matplotlib.colors import LinearSegmentedColormap
from matplotlib.lines import Line2D
from matplotlib.patches import Patch
from matplotlib.transforms import blended_transform_factory

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

from lunar import _bootstrap as boot
boot.ensure_lunar(extra=("spiceypy", "scipy"))
boot.ensure_apollo_hfe(mission="a15", probes=())
boot.ensure_apollo_hfe(mission="a17", probes=())
from lunar.apollo_helpers import extract_sensor_stability
from lunar.config import SITES
from lunar.plotting.style import (C_CORAL, C_CORAL_L, C_TEAL, C_FOREST,
                                  C_PLUM, C_CHAR, assert_no_overlap)

OUT = ROOT / ".." / "figures"

# ─── archive-measured design constants ───────────────────────────────
# The letter's original predates lunar.plotting.style; the tones below do
# not exist in the module and were measured from the archived original
# (docs/assets/fig_apollo_timeline_probes_archived.pdf, vector content).
# Everything the style module does cover (palette block colors, fonts via
# the imported rcParams) is taken from the module above.
C_CREAM_KEPT = "#F1ECE5"   # full-record bar, kept-sensor rows
C_CREAM_BORE = "#EFEAE3"   # full-record bar, borestem rows
C_BORE_BAR = "#D8D4CC"     # borestem-zone window bar
C_BORE_EDGE = "#A89F95"
C_BORE_LBL = "#8E8780"     # borestem row labels / "(borestem)" tags
C_TRACE_BORE = "#D6D2CC"   # borestem traces (pale grey underlay)
C_GRIDLINE = "#EDE9E2"     # faint gridlines over the tinted panels
C_LEG_TAN = "#E0CDB4"      # legend swatch for "stability window (kept)"

# Depth colormap: anchors measured from the archived original's kept-sensor
# traces/bars (one per kept depth, both missions -- they interleave on a
# single map).  Normalised over the global sensor depth range (14-234 cm).
_DEPTH_ANCHORS = [
    (84, "#8EB6BD"), (87, "#93BAC0"), (91, "#9CBFC4"), (97, "#A7C2C1"),
    (101, "#AEC3BF"), (129, "#E0CCB3"), (130, "#E0CBB2"), (131, "#E0CAB1"),
    (140, "#E2C0A6"), (167, "#E4A688"), (169, "#E1A284"), (177, "#DB9879"),
    (178, "#DA9778"), (185, "#D58D6E"), (186, "#D48C6D"), (195, "#CD8161"),
    (196, "#CC8060"), (223, "#B04C38"), (224, "#AF4B37"), (233, "#A53728"),
    (234, "#A43527"),
]

# Panel geometry measured from the archived page (624.5 x 684.4 pt canvas):
# (upper y0, upper y1, gantt y0, gantt y1) in pt from the TOP of the page,
# plus the hand-set axis window (ylim, yticks) of each upper panel.  The
# upper limits match [p0.1-0.5, p99+0.75] of the kept-sensor data to within
# measurement error, but the archive values are kept verbatim.
_PAGE_W, _PAGE_H = 624.5, 684.4
_AX_X0, _AX_W = 99.7, 449.7
_BLOCKS = [
    dict(site="A15", probe=1, color=C_FOREST, tint="#F4F8F4",
         upper=(22.0, 63.8), gantt=(69.0, 131.7),
         ylim=(251.41, 254.32), yticks=(252, 254)),
    dict(site="A15", probe=2, color=C_TEAL, tint="#F1F5F7",
         upper=(181.1, 225.5), gantt=(229.4, 262.8),
         ylim=(250.00, 252.03), yticks=(251, 252)),
    dict(site="A17", probe=1, color=C_CORAL, tint="#FAF2EE",
         upper=(312.2, 353.2), gantt=(359.0, 435.9),
         ylim=(254.53, 257.39), yticks=(255, 256, 257)),
    dict(site="A17", probe=2, color=C_PLUM, tint="#F5F2F6",
         upper=(485.2, 526.2), gantt=(532.1, 608.9),
         ylim=(255.50, 257.65), yticks=(256, 257)),
]
_XLIM = (0, 1800)
_XTICKS = range(0, 1801, 200)
_BAR_H = 0.61          # Gantt bar height in row units
_ROW_PAD = 0.1         # Gantt ylim margin beyond first/last row


def _disturbance_events():
    """Documented Apollo HFE data-quality events used to annotate the
    timeline.  Sources: Langseth et al. (1976); Grott et al. (2010);
    Nagihara et al. (2018).  Day offsets from each mission's first
    archived sample.

    Intervals re-measured 2026-07-05 from the archived original figure
    (docs/assets/fig_apollo_timeline_probes_archived.pdf) and cross-
    checked against the archived records: the A15 end-of-mission band and
    the A17 probe-2 / end-of-mission bands (and the late edge of the A17
    major outage) coincide day-for-day with telemetry gaps in the TG
    sensor records; the drilling transients and ALSEP outages are
    documented operational events with no gap in the restored data.
    """
    return {
        "A15": [
            (0, 60, "Drilling /\nemplacement\ntransient",
             "drilling heat dissipating into the regolith"),
            (193, 228, "ALSEP\noutage",
             "ALSEP central-station telemetry outage"),
            (1108, 1171, "Major\noutage",
             "extended telemetry outage"),
            (1246, 1340, "End-of-mission\noutage",
             "gap in the archived TG records before the final segment"),
        ],
        "A17": [
            (0, 71, "Drilling /\nemplacement\ntransient",
             "drilling heat dissipating into the regolith"),
            (444, 461, "ALSEP\noutage",
             "ALSEP central-station telemetry outage"),
            (610, 637, "ALSEP\noutage",
             "ALSEP central-station telemetry outage"),
            (715, 840, "Major\noutage",
             "extended outage; TG records gap 750-840"),
            (930, 1174, "Probe-2\noutage",
             "gap in the archived TG records (restored data)"),
            (1342, 1595, "End-of-mission\noutage",
             "gap in the archived TG records before the final segment"),
        ],
    }


def _subtract_bands(t0, t1, bands):
    """Split [t0, t1] into the segments outside the event bands."""
    segs = [(t0, t1)]
    for b0, b1 in bands:
        nxt = []
        for s0, s1 in segs:
            if b1 <= s0 or b0 >= s1:
                nxt.append((s0, s1))
                continue
            if s0 < b0:
                nxt.append((s0, b0))
            if b1 < s1:
                nxt.append((b1, s1))
        segs = nxt
    return [(s0, s1) for s0, s1 in segs if s1 - s0 > 0]


def _rect(y0, y1):
    """Measured pt box (from page top) -> figure-fraction rect."""
    return [_AX_X0 / _PAGE_W, 1.0 - y1 / _PAGE_H,
            _AX_W / _PAGE_W, (y1 - y0) / _PAGE_H]


def _style_panel(ax, color, grid_axis):
    for name in ("left", "bottom"):
        ax.spines[name].set_color(color)
        ax.spines[name].set_linewidth(1.0)
    ax.grid(axis=grid_axis, color=C_GRIDLINE, lw=0.4)
    ax.set_axisbelow(True)
    ax.set_xlim(*_XLIM)
    ax.set_xticks(list(_XTICKS))


def _draw_block(fig, blk, res, events, cmap, dnorm, xlabel=False):
    site, probe, color = blk["site"], blk["probe"], blk["color"]
    min_depth = SITES[site]["MIN_DEPTH_CM"]
    sensors = [s for s in res["sensors"] if s["probe"] == probe]  # depth-sorted
    pdata = res["probe_data"][probe]
    bands = [(e[0], e[1]) for e in events[site]]

    up = fig.add_axes(_rect(*blk["upper"]), facecolor=blk["tint"])
    gz = fig.add_axes(_rect(*blk["gantt"]), facecolor=blk["tint"])
    # Transparent overlay for the title pill and event-band labels: the
    # archive design lets these small labels sit over the pale context
    # traces, so they live on a line-free axes and the text-on-data guard
    # polices the data axes' own annotation (the slope box) strictly.
    ov = fig.add_axes(_rect(*blk["upper"]), facecolor="none")
    ov.set_xlim(*_XLIM)
    ov.set_ylim(0, 1)
    ov.axis("off")

    up_h = blk["upper"][1] - blk["upper"][0]          # panel height [pt]

    # ── upper sub-panel: traces ─────────────────────────────────────
    for t0, t1, *_ in events[site]:
        up.axvspan(t0, t1, fc=C_CORAL_L, alpha=0.18, ec=C_CORAL, lw=0.5,
                   zorder=1.2)
    bore_segs = [np.column_stack([pdata[s["sensor"]]["t_day"],
                                  pdata[s["sensor"]]["T"]])
                 for s in sensors if s["depth_cm"] < min_depth]
    up.add_collection(LineCollection(bore_segs, colors=C_TRACE_BORE, lw=0.5,
                                     alpha=0.4, zorder=1.6))
    kept = [s for s in sensors if s["depth_cm"] >= min_depth]
    for k, s in enumerate(kept):                      # shallow -> deep on top
        pd = pdata[s["sensor"]]
        up.plot(pd["t_day"], pd["T"], color=cmap(dnorm(s["depth_cm"])),
                lw=1.0, alpha=0.95, zorder=2.0 + 0.01 * k)

    # OLS drift fit on the deepest sensor's stability window
    deep = kept[-1]
    pd = pdata[deep["sensor"]]
    t_tail = pd["t_day"][pd["i_start"]:]
    coef = np.polyfit(t_tail, pd["T"][pd["i_start"]:], 1)     # K per day
    xf = np.array([t_tail[0], t_tail[-1]])
    up.plot(xf, np.polyval(coef, xf), ls="--", lw=1.7, color=color,
            alpha=0.95, zorder=3.6)
    up.text(0.985, 2.5 / up_h,
            f"deepest sensor {deep['sensor']} ($z$={deep['depth_cm']:.0f} cm):"
            f"  slope = {deep['tail_slope_Kyr']:+.3f} K yr$^{{-1}}$",
            transform=up.transAxes, ha="right", va="bottom", fontsize=8.0,
            color=color, zorder=5,
            bbox=dict(boxstyle="square,pad=0.25", fc="white", ec=color,
                      lw=0.4, alpha=0.90))

    _style_panel(up, color, grid_axis="both")
    up.tick_params(labelbottom=False)
    up.tick_params(axis="y", labelsize=8.5)
    up.set_ylim(*blk["ylim"])
    up.set_yticks(list(blk["yticks"]))
    up.set_ylabel("$T$ (K)", fontsize=9.5)

    # ── overlay: title pill + event labels ──────────────────────────
    # Plain colored text (no filled pill) — the section header reads as text
    # in the panel's own site color; its spine/trace color carry the panel
    # identity, so the solid backdrop is redundant.
    ov.text(0.5, 1.0 + 6.4 / up_h, f"Apollo {site[1:]} — Probe {probe}",
            transform=ov.transAxes, ha="center", va="center", fontsize=10.5,
            color=color, fontweight="bold")
    for t0, t1, label, _note in events[site]:
        ov.text(0.5 * (t0 + t1), 0.998, label, ha="center", va="top",
                fontsize=6.2, color=C_CORAL, linespacing=0.87, clip_on=False)

    # ── lower sub-panel: per-sensor Gantt strip ─────────────────────
    # bands sit BELOW the opaque full-record bars (the archive's striped
    # look: coral shows in the row gaps, cream rows mask it)
    n = len(sensors)
    for t0, t1, *_ in events[site]:
        gz.axvspan(t0, t1, fc=C_CORAL_L, alpha=0.22, ec=C_CORAL, lw=0.5,
                   zorder=1.2)
    tr_right = blended_transform_factory(gz.transAxes, gz.transData)
    labels = []
    for i, s in enumerate(sensors):
        pd = pdata[s["sensor"]]
        t = pd["t_day"]
        yc = i + 0.5
        borestem = s["depth_cm"] < min_depth
        gz.barh(yc, t[-1] - t[0], left=t[0], height=_BAR_H,
                color=C_CREAM_BORE if borestem else C_CREAM_KEPT,
                edgecolor="none", zorder=1.5)
        for s0, s1 in _subtract_bands(t[pd["i_start"]], t[-1], bands):
            if borestem:
                gz.barh(yc, s1 - s0, left=s0, height=_BAR_H, color=C_BORE_BAR,
                        alpha=0.45, edgecolor=C_BORE_EDGE, lw=0.4, zorder=3)
            else:
                gz.barh(yc, s1 - s0, left=s0, height=_BAR_H,
                        color=cmap(dnorm(s["depth_cm"])), alpha=0.95,
                        edgecolor=color, lw=0.7, zorder=3)
        labels.append(f"{s['sensor']:>6s} {s['depth_cm']:>4.0f} cm")
        if borestem:
            gz.text(1.005, yc, "(borestem)", transform=tr_right, ha="left",
                    va="center", fontsize=7.5, family="monospace",
                    color=C_BORE_LBL)
        else:
            gz.text(1.005, yc, f"$T_{{eq}}$ = {s['T_eq']:.2f} K",
                    transform=tr_right, ha="left", va="center", fontsize=7.5,
                    family="monospace", color=C_CHAR)

    _style_panel(gz, color, grid_axis="x")
    gz.set_ylim(n + _ROW_PAD, -_ROW_PAD)
    gz.set_yticks(np.arange(n) + 0.5)
    gz.set_yticklabels(labels)
    for tick, s in zip(gz.get_yticklabels(), sensors):
        tick.set_fontfamily("monospace")
        tick.set_fontsize(8.0)
        if s["depth_cm"] < min_depth:
            tick.set_color(C_BORE_LBL)
            tick.set_fontstyle("italic")
    gz.tick_params(axis="y", length=0)
    gz.tick_params(axis="x", labelsize=9.0)
    if xlabel:
        gz.set_xlabel("Days since first archived sample", fontsize=10.5)

    return up, gz, ov


def main():
    res = {site: extract_sensor_stability(SITES[site]["mission"],
                                          SITES[site]["MIN_DEPTH_CM"])
           for site in ("A15", "A17")}
    events = _disturbance_events()

    depths = np.concatenate([res[s]["depth_cm_all"] for s in ("A15", "A17")])
    dmin, dmax = depths.min(), depths.max()
    def dnorm(d):
        return (d - dmin) / (dmax - dmin)
    fracs = [dnorm(d) for d, _ in _DEPTH_ANCHORS]
    cmap = LinearSegmentedColormap.from_list(
        "hfe_depth",
        [(0.0, _DEPTH_ANCHORS[0][1])]
        + [(f, c) for f, (_, c) in zip(fracs, _DEPTH_ANCHORS)]
        + ([(1.0, _DEPTH_ANCHORS[-1][1])] if fracs[-1] < 1.0 else []))

    fig = plt.figure(figsize=(_PAGE_W / 72.0, _PAGE_H / 72.0))
    axes = []
    for j, blk in enumerate(_BLOCKS):
        axes.extend(_draw_block(fig, blk, res[blk["site"]], events, cmap,
                                dnorm, xlabel=(j == len(_BLOCKS) - 1)))

    handles = [
        Patch(fc=C_CREAM_KEPT, ec="none"),
        Patch(fc=C_CORAL_L, ec=C_CORAL, lw=0.4),
        Patch(fc=C_LEG_TAN, ec=C_FOREST, lw=0.6),
        Patch(fc=C_BORE_BAR, ec=C_BORE_EDGE, lw=0.4),
        Line2D([], [], ls="--", lw=1.5, color=C_CHAR),
    ]
    fig.legend(handles,
               ["full record", "excluded interval", "stability window (kept)",
                "borestem-zone window (excluded)",
                "OLS slope fit (deepest sensor)"],
               loc="lower center", bbox_to_anchor=(0.5, 0.018), ncols=5,
               frameon=False, fontsize=9.0, handlelength=1.6, handleheight=0.7,
               handletextpad=0.8, columnspacing=1.3, borderaxespad=0.0)

    fig.canvas.draw()
    for ax in axes:
        assert_no_overlap(ax)
    OUT.mkdir(parents=True, exist_ok=True)
    dst = OUT / "fig_apollo_timeline_probes.pdf"
    fig.savefig(dst)
    plt.close(fig)
    print(f"  -> {dst.name} (redrawn from live data; faithful to the "
          "archived original, see module docstring)")

    # per-site half-figures for the thesis (letter/abstract keep the full one)
    for site in ("A15", "A17"):
        _render_site(site, res, events, cmap, dnorm)


def _render_site(site, res, events, cmap, dnorm):
    """Two-block (one-site) variant sharing every style element with the
    full four-block figure; y coordinates shifted so the site's blocks
    start at the top of a shorter page."""
    global _PAGE_H
    blocks = [dict(b) for b in _BLOCKS if b["site"] == site]
    shift = blocks[0]["upper"][0] - 22.0
    for b in blocks:
        b["upper"] = (b["upper"][0] - shift, b["upper"][1] - shift)
        b["gantt"] = (b["gantt"][0] - shift, b["gantt"][1] - shift)
    old_h = _PAGE_H
    _PAGE_H = blocks[-1]["gantt"][1] + 75.5
    fig = plt.figure(figsize=(_PAGE_W / 72.0, _PAGE_H / 72.0))
    axes = []
    for j, blk in enumerate(blocks):
        axes.extend(_draw_block(fig, blk, res[blk["site"]], events, cmap,
                                dnorm, xlabel=(j == len(blocks) - 1)))
    handles = [
        Patch(fc=C_CREAM_KEPT, ec="none"),
        Patch(fc=C_CORAL_L, ec=C_CORAL, lw=0.4),
        Patch(fc=C_LEG_TAN, ec=C_FOREST, lw=0.6),
        Patch(fc=C_BORE_BAR, ec=C_BORE_EDGE, lw=0.4),
        Line2D([], [], ls="--", lw=1.5, color=C_CHAR),
    ]
    fig.legend(handles,
               ["full record", "excluded interval", "stability window (kept)",
                "borestem-zone window (excluded)",
                "OLS slope fit (deepest sensor)"],
               loc="lower center", bbox_to_anchor=(0.5, 0.012), ncols=3,
               frameon=False, fontsize=8.6, handlelength=1.5, handleheight=0.7,
               handletextpad=0.7, columnspacing=1.2, borderaxespad=0.0)
    fig.canvas.draw()
    for ax in axes:
        assert_no_overlap(ax)
    dst = OUT / f"fig_apollo_timeline_{site.lower()}.pdf"
    fig.savefig(dst)
    plt.close(fig)
    _PAGE_H = old_h
    print(f"  -> {dst.name}")


if __name__ == "__main__":
    main()
