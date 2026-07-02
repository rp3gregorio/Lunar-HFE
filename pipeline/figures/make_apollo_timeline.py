#!/usr/bin/env python3
"""Build the per-probe Apollo HFE stability-window timeline figure
(``results/figures/fig_apollo_timeline.pdf``, Figure 2.3 of the
guidebook).

The figure shows, for each of the four HFE probes (A15-Probe1,
A15-Probe2, A17-Probe1, A17-Probe2):

  * A label strip above the trace panel: each documented data-quality
    event (drilling/emplacement transient; A15 probe-1 heater pulse;
    A15 power-system anomaly; A17 tape-recorder digitizer drop-outs;
    A17 cable disturbance) gets a short coral tick over its time span,
    a thin leader line, and its caption placed in clear space ABOVE the
    trace axes -- never on top of the temperature curves. Sources:
    Langseth et al. (1976); Grott et al. (2010); Nagihara et al. (2018).
  * Trace sub-panel: every sensor's raw temperature record, depth-
    coloured, with the same event spans lightly shaded (no text) and
    the OLS long-term-drift fit on the deepest sensor annotated in a
    boxed label anchored to empty axes space.
  * Gantt sub-panel: per-sensor strip showing each sensor's selected
    stability window inside its full archived record.

Fix history
-----------
2026-07: the previous revision of this figure (and this script, which
was previously a stub pointing at a notebook cell that no longer
exists in this checkout) drew each event caption centred on its
coral band *inside the trace panel*, directly over the temperature
curves -- e.g. "Drilling / emplacement transient" sat on top of the
first ~80 days of data in every one of the four panels. This revision
moves every event caption into a dedicated annotation strip above the
trace axes (see ``_disturbance_events`` for the event table and the
``ax_lab`` block in ``build_figure`` for the leader-line rendering),
and is a fully self-contained, runnable script (previously the file
only printed instructions pointing at a missing notebook).

Run with::

  python3 pipeline/figures/make_apollo_timeline.py

Reads Apollo HFE depth tables via ``lunar.apollo_helpers`` from the
repo's local ``data/apollo/depth/`` cache; no network access or extra
bootstrap packages are required.
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

ROOT        = pathlib.Path(__file__).resolve().parents[2]
LETTER_FIGS = ROOT / "results" / "figures"
LETTER_FIGS.mkdir(parents=True, exist_ok=True)
sys.path.insert(0, str(ROOT / "src"))

from lunar.apollo_helpers import extract_sensor_stability
from lunar.config import SITES  # single source of truth

# Anthropic-aligned palette
C_CORAL       = "#B85B3A"
C_TEAL        = "#2A6478"
C_FOREST      = "#3D6E4A"
C_PLUM        = "#5A4A6A"
C_CHAR        = "#2A2520"
C_DIM         = "#6E6862"
C_GRID        = "#E8E5E0"
C_EXCLUDE     = "#E8A87C"
C_STABLE_A15  = "#8FA876"
C_STABLE_A17  = "#B85B3A"
C_BORESTEM    = "#C7C2B8"
C_EVENT_TEXT  = "#7A4530"

PROBE_HEADER_COLORS = {
    ("A15", 1): C_FOREST, ("A15", 2): C_TEAL,
    ("A17", 1): "#8A3A2A", ("A17", 2): C_PLUM,
}

FS_BASE, FS_LABEL, FS_TICK = 10.0, 10.5, 9.0
plt.rcParams.update({
    "font.family":        "serif",
    "font.serif":         ["Times", "Times New Roman", "DejaVu Serif"],
    "font.size":          FS_BASE,
    "axes.titlesize":     11.5, "axes.titleweight": "bold",
    "axes.labelsize":     FS_LABEL, "axes.linewidth": 0.9,
    "axes.spines.top":    False, "axes.spines.right": False,
    "axes.edgecolor":     C_CHAR, "axes.labelcolor": C_CHAR,
    "xtick.labelsize":    FS_TICK, "ytick.labelsize": FS_TICK,
    "xtick.color":        C_CHAR, "ytick.color": C_CHAR,
    "figure.facecolor":   "white", "savefig.facecolor": "white",
    "figure.dpi":         150, "savefig.dpi": 300,
    "savefig.bbox":       "tight", "savefig.pad_inches": 0.15,
    "grid.color":         C_GRID, "grid.linewidth": 0.6,
})


def _disturbance_events():
    """Documented Apollo HFE data-quality events used to annotate the
    timeline.  Sources: Langseth et al. (1976); Grott et al. (2010);
    Nagihara et al. (2018).  Day offsets from each mission's first
    archived sample.  Only events with a citable physical cause are
    included here -- deliberately narrower than the previous
    hand-drawn figure, which also carried "ALSEP outage" / "Major
    outage" / "Probe-2 outage" / "End-of-mission outage" bands that
    have no corresponding entry anywhere in this repository's data or
    documentation and could not be reproduced from source.
    """
    return {
        "A15": [
            (40, 80, "Drilling / emplacement\ntransient"),
            (489, 521, "Probe-1 heater\nexperiment"),
            (1310, 1340, "Power-system\nanomaly"),
        ],
        "A17": [
            (35, 65, "Drilling / emplacement\ntransient"),
            (520, 545, "Tape-recorder\nglitch"),
            (1100, 1150, "Cable\ndisturbance"),
        ],
    }


def build_figure():
    events = _disturbance_events()
    sites_data = {
        "A15": extract_sensor_stability("a15", SITES["A15"]["MIN_DEPTH_CM"]),
        "A17": extract_sensor_stability("a17", SITES["A17"]["MIN_DEPTH_CM"]),
    }

    panel_specs = [("A15", 1), ("A15", 2), ("A17", 1), ("A17", 2)]
    n_rows = len(panel_specs)
    xmax = 1800

    fig = plt.figure(figsize=(9.0, 16.0))
    gs = fig.add_gridspec(
        nrows=n_rows * 3, ncols=1,
        height_ratios=[0.55, 1.35, 1.15] * n_rows,
        hspace=0.15,
    )

    for row_i, (site, probe_num) in enumerate(panel_specs):
        d = sites_data[site]
        ax_lab   = fig.add_subplot(gs[row_i * 3, 0])
        ax_trace = fig.add_subplot(gs[row_i * 3 + 1, 0])
        ax_gantt = fig.add_subplot(gs[row_i * 3 + 2, 0], sharex=ax_trace)

        pdata = d["probe_data"][probe_num]
        deepest_name = max(pdata, key=lambda k: pdata[k]["depth_cm"])
        deepest = pdata[deepest_name]

        # y-window sized to the deep (kept) sensors, so the diurnal
        # swing of shallow/borestem sensors doesn't dominate the axes.
        deep_names = [n for n, s in pdata.items()
                      if s["depth_cm"] >= SITES[site]["MIN_DEPTH_CM"]]
        deep_teqs = [pdata[n]["T_eq"] for n in deep_names]
        ylo, yhi = min(deep_teqs) - 2.0, max(deep_teqs) + 2.0

        depths_sorted = sorted(pdata.items(), key=lambda kv: kv[1]["depth_cm"])
        n_sensors = len(depths_sorted)
        for i, (name, s) in enumerate(depths_sorted):
            color = plt.cm.viridis(0.15 + 0.7 * i / max(n_sensors - 1, 1))
            ax_trace.plot(s["t_day"], s["T"], lw=0.5, color=color, alpha=0.7)

        t_day, T, i0 = deepest["t_day"], deepest["T"], deepest["i_start"]
        sl, ic = np.polyfit((t_day[i0:] - t_day[i0]) / 365.25, T[i0:], 1)
        fit_T = ic + sl * (t_day[i0:] - t_day[i0]) / 365.25
        ax_trace.plot(t_day[i0:], fit_T, "--", color=C_CHAR, lw=1.3, zorder=5)
        ax_trace.set_ylim(ylo, yhi)
        ax_trace.annotate(
            f"deepest sensor {deepest_name} (z={int(deepest['depth_cm'])} cm):"
            f"  slope = {sl:+.3f} K yr$^{{-1}}$",
            xy=(0.98, 0.04), xycoords="axes fraction", ha="right", va="bottom",
            fontsize=8.0, color=C_CHAR,
            bbox=dict(boxstyle="round,pad=0.3", fc="white", ec="#D4CFC4",
                      lw=0.8, alpha=0.96),
        )

        ax_trace.set_xlim(0, xmax)
        ax_trace.set_ylabel("$T$ (K)", fontsize=9.5)
        ax_trace.tick_params(labelbottom=False)
        for spine in ("top", "right"):
            ax_trace.spines[spine].set_visible(False)

        # Event spans are shaded on the trace panel but carry NO text
        # here -- the caption lives in the strip above (ax_lab).
        for (d0, d1, _label) in events[site]:
            ax_trace.axvspan(d0, d1, color=C_CORAL, alpha=0.15, lw=0)

        header_color = PROBE_HEADER_COLORS[(site, probe_num)]
        site_label = "Apollo 15" if site == "A15" else "Apollo 17"
        ax_trace.text(
            0.5, 1.16, f"{site_label} — Probe {probe_num}",
            transform=ax_trace.transAxes, ha="center", va="bottom",
            fontsize=11, fontweight="bold", color="white",
            bbox=dict(boxstyle="round,pad=0.4", fc=header_color, ec="none"),
        )

        # --- fix: event captions in a dedicated strip, off the data ---
        ax_lab.set_xlim(0, xmax)
        ax_lab.set_ylim(0, 1)
        ax_lab.axis("off")
        for (d0, d1, label) in events[site]:
            xm = 0.5 * (d0 + d1)
            ax_lab.axvspan(d0, d1, ymin=0.0, ymax=0.22, color=C_CORAL,
                            alpha=0.35, lw=0)
            ax_lab.plot([xm, xm], [0.22, 0.80], color=C_CORAL, lw=0.8,
                        alpha=0.8)
            ax_lab.text(xm, 0.92, label, ha="center", va="top", fontsize=7.2,
                        color=C_EVENT_TEXT, linespacing=1.15)

        sensors_sorted = sorted(pdata.items(), key=lambda kv: kv[1]["depth_cm"])
        n = len(sensors_sorted)
        for row, (name, s) in enumerate(sensors_sorted):
            y = n - row
            full_end = s["t_day"][-1]
            is_borestem = s["depth_cm"] < SITES[site]["MIN_DEPTH_CM"]
            ax_gantt.add_patch(Rectangle((0, y - 0.35), full_end, 0.7,
                                          fc="#F2EEE6", ec="none", zorder=1))
            stable_start = s["t_day"][s["i_start"]]
            ax_gantt.add_patch(Rectangle((0, y - 0.35), stable_start, 0.7,
                                          fc=C_EXCLUDE, ec="none", alpha=0.5,
                                          zorder=2))
            if is_borestem:
                ax_gantt.add_patch(Rectangle(
                    (stable_start, y - 0.35), full_end - stable_start, 0.7,
                    fc=C_BORESTEM, ec="none", alpha=0.85, zorder=3))
                label_txt = "(borestem)"
            else:
                stable_color = C_STABLE_A15 if site == "A15" else C_STABLE_A17
                ax_gantt.add_patch(Rectangle(
                    (stable_start, y - 0.35), full_end - stable_start, 0.7,
                    fc=stable_color, ec="none", alpha=0.75, zorder=3))
                label_txt = f"$T_{{eq}}$ = {s['T_eq']:.2f} K"
            style = "italic" if is_borestem else "normal"
            color = C_DIM if is_borestem else C_CHAR
            ax_gantt.text(-30, y, name, ha="right", va="center", fontsize=7.6,
                          color=color, style=style)
            ax_gantt.text(-160, y, f"{int(s['depth_cm'])} cm", ha="right",
                          va="center", fontsize=7.6, color=color, style=style)
            ax_gantt.text(xmax + 30, y, label_txt, ha="left", va="center",
                          fontsize=7.6, color=color, style=style)

        ax_gantt.set_ylim(0.3, n + 0.7)
        ax_gantt.set_xlim(0, xmax)
        ax_gantt.set_yticks([])
        for spine in ("top", "right", "left"):
            ax_gantt.spines[spine].set_visible(False)
        if row_i == n_rows - 1:
            ax_gantt.set_xlabel("Days since first archived sample", fontsize=10)
        else:
            ax_gantt.tick_params(labelbottom=False)

    legend_elems = [
        Rectangle((0, 0), 1, 1, fc="#F2EEE6", label="full record"),
        Rectangle((0, 0), 1, 1, fc=C_EXCLUDE, alpha=0.5, label="excluded interval"),
        Rectangle((0, 0), 1, 1, fc=C_STABLE_A15, alpha=0.75,
                   label="stability window (kept)"),
        Rectangle((0, 0), 1, 1, fc=C_BORESTEM, alpha=0.85,
                   label="borestem-zone window (excluded)"),
        Line2D([0], [0], color=C_CHAR, ls="--", lw=1.3,
               label="OLS slope fit (deepest sensor)"),
    ]
    fig.legend(handles=legend_elems, loc="lower center", ncol=3, frameon=False,
               fontsize=8.5, bbox_to_anchor=(0.5, -0.01))
    return fig


def main():
    out = LETTER_FIGS / "fig_apollo_timeline.pdf"
    fig = build_figure()
    fig.savefig(out)
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
