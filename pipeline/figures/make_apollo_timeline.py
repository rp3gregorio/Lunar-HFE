#!/usr/bin/env python3
"""Build the per-probe Apollo HFE stability-window timeline figure
(``results/figures/fig_apollo_timeline.pdf``, Figure 2.4 of the
guidebook).

For each of the four HFE probes (A15-Probe1, A15-Probe2, A17-Probe1,
A17-Probe2) the figure shows three stacked strips:

  * A label strip above the trace panel. Each documented, mission-wide
    data-quality event (drilling/emplacement transient; ALSEP outages;
    major outage; A17 Probe-2 outage; end-of-mission outage) gets a
    short coral tick over its time span, a thin leader line, and its
    caption placed in clear space ABOVE the trace axes -- never on top
    of the temperature curves.
  * A trace sub-panel: every sensor's raw temperature record, depth-
    graded from warm coral (shallow) to cool teal (deep), on a faint
    per-probe background tint. The same event spans are lightly shaded
    (no text), and the OLS long-term-drift fit on the deepest sensor is
    annotated in a boxed label anchored to empty axes space.
  * A gantt sub-panel: a depth-ordered per-sensor strip. Each sensor's
    accepted stability window (olive green) sits inside its full
    archived record (pale) after the excluded lead-in (coral); the
    kept window is segmented around the event bands. Shallow
    borestem-zone sensors are shown grey and excluded. Each deep
    sensor's T_eq is printed at the right.

Fix history
-----------
2026-07: this figure previously drew each event caption centred on its
coral band *inside the trace panel*, directly over the temperature
curves -- e.g. "Drilling / emplacement transient" sat on top of the
first ~80 days of data in every one of the four panels. The script
that should have produced it was a non-functional stub pointing at a
notebook cell that no longer exists in this checkout. This revision is
a self-contained rebuild in the figure's original warm-palette style
(depth-graded traces, per-probe tint, olive kept-windows, the full
documented event set) whose one substantive change is that every event
caption is moved into a dedicated annotation strip above the trace
axes with a leader line to its span, so no caption overlaps the data.

Run with::

  python3 pipeline/figures/make_apollo_timeline.py

Reads Apollo HFE depth tables via ``lunar.apollo_helpers`` from the
repo's local ``data/apollo/depth/`` cache; no network access required.
"""
from __future__ import annotations
import sys
import pathlib

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import Rectangle
from matplotlib.colors import LinearSegmentedColormap

ROOT        = pathlib.Path(__file__).resolve().parents[2]
LETTER_FIGS = ROOT / "results" / "figures"
LETTER_FIGS.mkdir(parents=True, exist_ok=True)
sys.path.insert(0, str(ROOT / "src"))

from lunar.apollo_helpers import extract_sensor_stability
from lunar.config import SITES

# ---- palette (measured from the original guidebook figure) ---------------
C_CORAL  = "#B85B3A"
C_TEAL   = "#2C6E73"
C_FOREST = "#3D6E4A"
C_PLUM   = "#5A4A6A"
C_CHAR   = "#2A2520"
C_DIM    = "#6E6862"
C_KEPT   = "#6E8F5E"   # olive-green accepted stability window
C_EXCL   = "#DBA883"   # coral-tan excluded lead-in
C_FULL   = "#EFE7DA"   # pale full archived record
C_BORE   = "#C9C4BA"   # grey borestem-zone window
# depth colormap: shallow (warm coral) -> deep (cool teal)
TRACE_CMAP = LinearSegmentedColormap.from_list(
    "depth", ["#C77B54", "#CDA98C", "#8FB0A6", "#3E7D82"])

PROBE_HEADER = {("A15", 1): C_FOREST, ("A15", 2): C_TEAL,
                ("A17", 1): "#8A3A2A", ("A17", 2): C_PLUM}
PANEL_TINT = {C_FOREST: "#F3F6F2", C_TEAL: "#EFF4F4",
              "#8A3A2A": "#FBF2EE", C_PLUM: "#F5F2F6"}

plt.rcParams.update({
    "font.family": "serif",
    "font.serif":  ["Times", "Times New Roman", "DejaVu Serif"],
    "axes.edgecolor": C_CHAR,
    "figure.facecolor": "white", "savefig.facecolor": "white",
    "savefig.dpi": 300, "savefig.bbox": "tight", "savefig.pad_inches": 0.15,
})

X_MAX = 1800  # days axis, shared across probes


def _disturbance_events(site: str):
    """Mission-wide HFE data-quality event windows, as (day_start,
    day_end, caption). Both probes of a mission share the same events.

    IMPORTANT — provenance of the day ranges: these spans were recovered
    by pixel-measuring the coral event bands in the *original* rendered
    figure (whose own plotting source was lost), not from a primary
    dated record. They are therefore approximate reproductions of the
    original figure's bands, accurate to a few days, and are used here
    only to (a) shade the events on the trace panels and (b) segment the
    kept-window rectangles in the gantt strip. They are NOT authoritative
    event dates. The event *identities* (drilling/emplacement transient,
    ALSEP outages, major and end-of-mission outages, A17 Probe-2 outage)
    correspond to the data-quality events discussed for the HFE record in
    Langseth et al. (1976) and Nagihara et al. (2018); if precise dated
    windows are available they should replace the measured ranges below."""
    if site == "A15":
        return [(83, 139,   "Drilling /\nemplacement\ntransient"),
                (269, 304,  "ALSEP\noutage"),
                (1170, 1228, "Major\noutage"),
                (1303, 1395, "End-of-mission\noutage")]
    return [(86, 149,   "Drilling /\nemplacement\ntransient"),
            (520, 532,  "ALSEP\noutage"),
            (678, 705,  "ALSEP\noutage"),
            (782, 905,  "Major\noutage"),
            (992, 1233, "Probe-2\noutage"),
            (1396, 1645, "End-of-mission\noutage")]


def _segment_around(a0, a1, events):
    """Split the interval [a0, a1] by removing every event span, so a
    kept window is drawn as discrete blocks between disturbances."""
    segs = [(a0, a1)]
    for (e0, e1, _lbl) in events:
        out = []
        for (s0, s1) in segs:
            if e1 < s0 or e0 > s1:
                out.append((s0, s1))
            else:
                if s0 < e0:
                    out.append((s0, e0))
                if e1 < s1:
                    out.append((e1, s1))
        segs = out
    return segs


def _draw_probe_block(fig, gs, ri, nrows, site, pn, data):
    pdata = data["probe_data"][pn]
    mind  = SITES[site]["MIN_DEPTH_CM"]
    events = _disturbance_events(site)
    header = PROBE_HEADER[(site, pn)]

    ax_lab = fig.add_subplot(gs[ri * 3, 0])
    ax_tr  = fig.add_subplot(gs[ri * 3 + 1, 0])
    ax_g   = fig.add_subplot(gs[ri * 3 + 2, 0], sharex=ax_tr)
    ax_tr.set_facecolor(PANEL_TINT[header])

    dsorted = sorted(pdata.items(), key=lambda kv: kv[1]["depth_cm"])
    ns = len(dsorted)
    deep = [(n, s) for n, s in dsorted if s["depth_cm"] >= mind]
    teqs = [s["T_eq"] for _, s in deep]
    ylo, yhi = min(teqs) - 2.2, max(teqs) + 2.2

    # --- trace panel: depth-graded raw records ---
    for i, (name, s) in enumerate(dsorted):
        ax_tr.plot(s["t_day"], s["T"], lw=0.45,
                   color=TRACE_CMAP(i / max(ns - 1, 1)), alpha=0.75, zorder=2)
    dn, ds = deep[-1]
    i0 = ds["i_start"]
    yr = (ds["t_day"][i0:] - ds["t_day"][i0]) / 365.25
    sl, ic = np.polyfit(yr, ds["T"][i0:], 1)
    ax_tr.plot(ds["t_day"][i0:], ic + sl * yr, "--", color=C_CHAR, lw=1.3,
               zorder=6)
    for (e0, e1, _l) in events:
        ax_tr.axvspan(e0, e1, color=C_CORAL, alpha=0.12, lw=0, zorder=1)
    ax_tr.set_ylim(ylo, yhi)
    ax_tr.set_xlim(0, X_MAX)
    ax_tr.set_ylabel("$T$ (K)", fontsize=9)
    ax_tr.tick_params(labelbottom=False, labelsize=8)
    for sp in ("top", "right"):
        ax_tr.spines[sp].set_visible(False)
    ax_tr.annotate(
        f"deepest sensor {dn} ($z$={int(ds['depth_cm'])} cm):  "
        f"slope = {sl:+.3f} K yr$^{{-1}}$",
        xy=(0.98, 0.05), xycoords="axes fraction", ha="right", va="bottom",
        fontsize=8, color=C_CHAR,
        bbox=dict(boxstyle="round,pad=0.3", fc="white", ec=header, lw=0.9,
                  alpha=0.97))
    slabel = "Apollo 15" if site == "A15" else "Apollo 17"
    ax_tr.text(0.012, 0.94, f"{slabel} \u2014 Probe {pn}",
               transform=ax_tr.transAxes, ha="left", va="top", fontsize=10.5,
               fontweight="bold", color="white", zorder=7,
               bbox=dict(boxstyle="round,pad=0.35", fc=header, ec="none"))

    # --- label strip: captions off the data, leader to each span ---
    ax_lab.set_xlim(0, X_MAX)
    ax_lab.set_ylim(0, 1)
    ax_lab.axis("off")
    for (e0, e1, label) in events:
        xm = 0.5 * (e0 + e1)
        ax_lab.axvspan(e0, e1, ymin=0, ymax=0.20, color=C_CORAL, alpha=0.32,
                       lw=0)
        ax_lab.plot([xm, xm], [0.20, 0.72], color=C_CORAL, lw=0.7, alpha=0.75)
        ax_lab.text(xm, 0.85, label, ha="center", va="top", fontsize=6.6,
                    color="#7A4530", linespacing=1.1)

    # --- gantt panel: per-sensor windows ---
    for row, (name, s) in enumerate(dsorted):
        y = ns - row
        end = s["t_day"][-1]
        bore = s["depth_cm"] < mind
        ax_g.add_patch(Rectangle((0, y - 0.34), end, 0.68, fc=C_FULL,
                                 ec="none", zorder=1))
        st = s["t_day"][s["i_start"]]
        ax_g.add_patch(Rectangle((0, y - 0.34), st, 0.68, fc=C_EXCL,
                                 ec="none", alpha=0.55, zorder=2))
        if bore:
            ax_g.add_patch(Rectangle((st, y - 0.34), end - st, 0.68,
                                     fc=C_BORE, ec="none", alpha=0.85,
                                     zorder=3))
            rlab = "(borestem)"
        else:
            for (s0, s1) in _segment_around(st, end, events):
                if s1 - s0 > 4:
                    ax_g.add_patch(Rectangle((s0, y - 0.30), s1 - s0, 0.60,
                                             fc=C_KEPT, ec="#4E6B41", lw=0.5,
                                             alpha=0.85, zorder=3))
            rlab = f"$T_{{eq}}$ = {s['T_eq']:.2f} K"
        col = C_DIM if bore else C_CHAR
        st_ = "italic" if bore else "normal"
        ax_g.text(-24, y, name, ha="right", va="center", fontsize=7.2,
                  color=col, style=st_)
        ax_g.text(-150, y, f"{int(s['depth_cm'])} cm", ha="right", va="center",
                  fontsize=7.2, color=col, style=st_)
        ax_g.text(X_MAX + 24, y, rlab, ha="left", va="center", fontsize=7.2,
                  color=col, style=st_)
    ax_g.set_ylim(0.3, ns + 0.7)
    ax_g.set_xlim(0, X_MAX)
    ax_g.set_yticks([])
    for sp in ("top", "right", "left"):
        ax_g.spines[sp].set_visible(False)
    if ri == nrows - 1:
        ax_g.set_xlabel("Days since first archived sample", fontsize=9.5)
    else:
        ax_g.tick_params(labelbottom=False)
    ax_g.tick_params(labelsize=8)


def build_figure():
    d15 = extract_sensor_stability("a15", SITES["A15"]["MIN_DEPTH_CM"])
    d17 = extract_sensor_stability("a17", SITES["A17"]["MIN_DEPTH_CM"])
    data = {"A15": d15, "A17": d17}
    specs = [("A15", 1), ("A15", 2), ("A17", 1), ("A17", 2)]
    nrows = len(specs)

    # Aspect ratio (~1.1 h/w) is chosen to match the original figure so
    # that at \linewidth width the figure+caption fits one guidebook page
    # without overflowing the text block.
    fig = plt.figure(figsize=(9.6, 10.7))
    gs = fig.add_gridspec(nrows * 3, 1,
                          height_ratios=[0.34, 0.92, 1.05] * nrows, hspace=0.16)
    for ri, (site, pn) in enumerate(specs):
        _draw_probe_block(fig, gs, ri, nrows, site, pn, data[site])

    leg = [
        Rectangle((0, 0), 1, 1, fc=C_FULL, label="full record"),
        Rectangle((0, 0), 1, 1, fc=C_EXCL, alpha=0.55,
                  label="excluded interval"),
        Rectangle((0, 0), 1, 1, fc=C_KEPT, alpha=0.85,
                  label="stability window (kept)"),
        Rectangle((0, 0), 1, 1, fc=C_BORE, alpha=0.85,
                  label="borestem-zone window (excluded)"),
        Line2D([0], [0], color=C_CHAR, ls="--", lw=1.3,
               label="OLS slope fit (deepest sensor)"),
    ]
    fig.legend(handles=leg, loc="lower center", ncol=3, frameon=False,
               fontsize=8.3, bbox_to_anchor=(0.5, -0.005))
    return fig


def main():
    out = LETTER_FIGS / "fig_apollo_timeline.pdf"
    fig = build_figure()
    fig.savefig(out)
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
