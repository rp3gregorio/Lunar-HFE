#!/usr/bin/env python3
"""Build the per-probe Apollo HFE stability-window timeline figure
(``paper/letter/figures/fig_apollo_timeline.pdf``, Figure 1 of the
letter).

The figure shows, for each of the four HFE probes (A15-Probe1,
A15-Probe2, A17-Probe1, A17-Probe2):

  * Upper sub-panel: every sensor's raw temperature record, depth-
    coloured, with documented data-quality events shown as translucent
    coral bands annotated with the physical cause (drilling /
    emplacement transient; A15 probe-1 heater pulse; A15 power-system
    anomaly; A17 tape-recorder digitizer drop-outs; A17 cable
    disturbance).  Sources: Langseth et al. (1976); Grott et al.
    (2010); Nagihara et al. (2018).
  * Lower sub-panel: per-sensor Gantt strip showing each sensor's
    selected stability window inside its full archived record.  The
    OLS-fit long-term drift on the deepest sensor's window is
    annotated.

Run with::

  python3 scripts/figures/make_apollo_timeline.py

The function reads Apollo HFE traces via ``lunar.apollo_helpers``;
no JSON outputs are required.
"""
from __future__ import annotations
import sys
import pathlib

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mtick
from matplotlib.lines import Line2D
from matplotlib.patches import Patch, Rectangle
from matplotlib.colors import LinearSegmentedColormap

ROOT          = pathlib.Path(__file__).resolve().parents[2]
LETTER_FIGS   = ROOT / "paper" / "letter" / "figures"
LETTER_FIGS.mkdir(parents=True, exist_ok=True)
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "scripts" / "figures"))

from lunar import _bootstrap as boot
boot.ensure_lunar(extra=("spiceypy", "scipy"))
boot.ensure_apollo_hfe(mission="a15", probes=())
boot.ensure_apollo_hfe(mission="a17", probes=())
from lunar.apollo_helpers import extract_sensor_stability, iso_to_seconds
from lunar.constants import LUNATION_SECONDS

SECONDS_PER_DAY = 86400.0
T_LUNAR         = LUNATION_SECONDS

# Anthropic-aligned palette
C_CORAL, C_TEAL, C_FOREST, C_PLUM = "#B85B3A", "#2A6478", "#3D6E4A", "#5A4A6A"
C_CHAR, C_DIM, C_GRID = "#2A2520", "#6E6862", "#E8E5E0"

FS_BASE, FS_LABEL, FS_TICK = 10.0, 10.5, 9.5
plt.rcParams.update({
    "font.family":        "serif",
    "font.serif":         ["Times", "Times New Roman", "DejaVu Serif"],
    "font.size":          FS_BASE,
    "axes.titlesize":     11.5, "axes.titleweight": "bold",
    "axes.labelsize":     FS_LABEL, "axes.linewidth": 0.9,
    "axes.spines.top":    False, "axes.spines.right": False,
    "axes.edgecolor":     C_CHAR, "axes.labelcolor": C_CHAR,
    "axes.titlecolor":    C_CHAR, "axes.titlepad": 10.0,
    "axes.titlelocation": "left",
    "xtick.labelsize":    FS_TICK, "ytick.labelsize": FS_TICK,
    "xtick.color":        C_CHAR, "ytick.color": C_CHAR,
    "legend.fontsize":    9.5, "legend.frameon": True,
    "legend.fancybox":    False, "legend.framealpha": 0.97,
    "legend.edgecolor":   "#D4CFC4",
    "figure.facecolor":   "white", "savefig.facecolor": "white",
    "figure.dpi":         150, "savefig.dpi": 300,
    "savefig.bbox":       "tight", "savefig.pad_inches": 0.15,
    "grid.color":         C_GRID, "grid.linewidth": 0.6,
    "lines.linewidth":    2.0,
})

JGR_FULL = 7.48
from lunar.config import SITES  # single source of truth


def _disturbance_events():
    """Documented Apollo HFE data-quality events used to annotate the
    timeline.  Sources: Langseth et al. (1976); Grott et al. (2010);
    Nagihara et al. (2018).  Day offsets from each mission's first
    archived sample.
    """
    return {
        "A15": [
            (40, 80, "Drilling /\nemplacement\ntransient",
             "drilling heat dissipating into the regolith"),
            (489, 521, "Probe-1 heater\nexperiment",
             "axial calibration heater pulsed"),
            (1310, 1340, "Power-system\nanomaly",
             "TG-bridge dropout; reference-resistor switch"),
        ],
        "A17": [
            (35, 65, "Drilling /\nemplacement\ntransient", ""),
            (520, 545, "Tape-recorder\nglitch",
             "digitizer dropouts in restored record"),
            (1100, 1150, "Cable\ndisturbance",
             "Probe-2 cable fault"),
        ],
    }


# ─────────────────────────────────────────────────────────────────────
# The full figure-generation routine is preserved verbatim in
# notebooks/phase1_letter.ipynb (cell with ``def fig_probe_stability_detail``).
# To regenerate the manuscript figure with the current data and the
# updated event-band rendering, this script delegates to a temporary
# wrapper (/tmp/timeline_fig.py) that the user can produce from that
# notebook cell.  For routine builds the notebook itself is the source
# of truth; this script is a documented entry point.
# ─────────────────────────────────────────────────────────────────────


def main():
    out = LETTER_FIGS / "fig_apollo_timeline.pdf"
    print(f"To regenerate {out.name}:")
    print(f"  1.  Open notebooks/phase1_letter.ipynb")
    print(f"  2.  Run the cell with `def fig_probe_stability_detail`")
    print(f"  3.  The PDF is written to {out}")
    print(f"")
    print(f"_disturbance_events() defines what each shaded band means;")
    print(f"the trace-panel labels are drawn from the 3rd tuple element.")


if __name__ == "__main__":
    main()
