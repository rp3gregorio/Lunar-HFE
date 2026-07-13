#!/usr/bin/env python3
"""Stability-window timeline, redesigned (2026-07-03).

One slim panel per probe, showing ONLY what the retrieval actually uses:
the probe's DEEPEST sensor record, the ALGORITHMIC stability window chosen
by ``apollo_helpers.find_stable_window`` (shaded), and the trailing linear
fit whose slope certifies the window (dashed).

Design history: the previous version stacked every sensor of every probe
(up to 8 traces/panel), added a per-sensor T_eq micro-table, and shaded
mission "disturbance events" whose day-ranges had been PIXEL-MEASURED from
a lost original figure (non-authoritative — see git history). All three
layers are gone: this figure now contains only data that comes from the
archived record and the selection algorithm itself.

Writes results/figures/fig_apollo_timeline.pdf.
Run: python pipeline/figures/make_apollo_timeline.py
"""
from __future__ import annotations

import pathlib
import sys

import numpy as np
import matplotlib.pyplot as plt

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from lunar.apollo_helpers import extract_sensor_stability
from lunar.config import SITES
from lunar.plotting.style import (JGR_FULL, C_A15, C_A17, C_CHAR, C_DIM,
                                  C_GRID, C_FOREST_L, C_CORAL_L,
                                  fmt_axis, assert_no_overlap)

OUT = ROOT / "results" / "figures"


def _deepest(pdata):
    """The probe's deepest sensor: (name, sensor-dict)."""
    return max(pdata.items(), key=lambda kv: kv[1]["depth_cm"])


def main():
    d15 = extract_sensor_stability("a15", SITES["A15"]["MIN_DEPTH_CM"])
    d17 = extract_sensor_stability("a17", SITES["A17"]["MIN_DEPTH_CM"])
    rows = [("Apollo 15", 1, d15, C_A15, C_FOREST_L),
            ("Apollo 15", 2, d15, C_A15, C_FOREST_L),
            ("Apollo 17", 1, d17, C_A17, C_CORAL_L),
            ("Apollo 17", 2, d17, C_A17, C_CORAL_L)]

    # NOT sharex: the archived A15 deep record spans ~1430 d, A17 only ~750 d
    # -- a shared 1800-day axis would waste most of the A17 panels.
    fig, axes = plt.subplots(4, 1, figsize=(JGR_FULL, 5.8),
                             constrained_layout=True)
    for ax, (slabel, pn, data, col, col_l) in zip(axes, rows):
        name, s = _deepest(data["probe_data"][pn])
        t, T, i0 = s["t_day"], s["T"], s["i_start"]

        # the algorithmic stability window (authoritative: find_stable_window)
        ax.axvspan(t[i0], t[-1], color=col_l, alpha=0.5, lw=0, zorder=1)
        ax.plot(t, T, lw=0.9, color=col, zorder=3)

        # trailing linear fit inside the window -> the certified slope
        yr = (t[i0:] - t[i0]) / 365.25
        sl, ic = np.polyfit(yr, T[i0:], 1)
        ax.plot(t[i0:], ic + sl * yr, "--", color=C_CHAR, lw=1.1, zorder=4)

        # tight y around the SETTLED regime: the drilling-heat transient
        # (up to ~320 K) deliberately exits the top of the panel -- the story
        # is the settling, not the spike
        teq = float(s["T_eq"])
        ax.set_ylim(teq - 1.0, teq + 2.5)
        ax.set_xlim(0, float(t[-1]) * 1.02)

        # stats line lives in the panel TITLE, outside the axes, so no text
        # ever sits on the trace or the window band
        fmt_axis(ax, ylabel="$T$ (K)",
                 title=f"{slabel} — Probe {pn} · deepest {name} "
                       f"({int(s['depth_cm'])} cm) · slope {sl:+.3f} K/yr · "
                       f"$T_{{\\rm eq}}$ {s['T_eq']:.2f} K")
        ax.title.set_fontsize(8)
        ax.tick_params(labelsize=7)

    axes[-1].set_xlabel("days since first archived sample")
    axes[1].set_xlabel("days since first archived sample", fontsize=8)
    # one shared legend below, never on the data
    from matplotlib.lines import Line2D
    from matplotlib.patches import Patch
    handles = [Line2D([0], [0], color=C_DIM, lw=0.9, label="deepest-sensor record"),
               Patch(fc=C_FOREST_L, alpha=0.5, label="stability window (algorithmic)"),
               Line2D([0], [0], color=C_CHAR, lw=1.1, ls="--",
                      label="trailing fit (slope $<$ 0.08 K/yr)")]
    fig.legend(handles=handles, ncol=3, loc="lower center", frameon=True,
               edgecolor=C_GRID, fontsize=7.5, bbox_to_anchor=(0.5, -0.055))

    fig.canvas.draw()
    for ax in axes:
        assert_no_overlap(ax)
    OUT.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT / "fig_apollo_timeline.pdf", bbox_inches="tight")
    plt.close(fig)
    print("  -> fig_apollo_timeline.pdf (redesigned: 4 slim panels, "
          "algorithmic window only)")


if __name__ == "__main__":
    main()
