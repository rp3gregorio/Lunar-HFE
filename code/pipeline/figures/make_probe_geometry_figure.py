#!/usr/bin/env python3
"""Build the Apollo HFE probe-placement figure for the main guidebook
(``results/figures/fig_probe_geometry.pdf``).

Two panels:
  (a) Physical layout of the two Apollo 15 heat-flow boreholes at Hadley
      Rille -- Probe 1 (8 sensors, to 139 cm) and Probe 2 (4 sensors,
      to 97 cm) -- with real sensor depths and names read from the
      restored Nagihara (2018) record via ``lunar.apollo_helpers``.
      Shallow (borestem-excluded) sensors are drawn as open circles,
      deep (retrieval-feeding) sensors as filled circles, split at the
      z = 80 cm cut used throughout the pipeline.
  (b) What one HFE sensor physically is: two platinum-resistance
      bridges ~50 cm apart on the probe tube, whose temperature
      difference divided by their separation gives the local gradient
      dT/dz, which Fourier's law turns into a heat flux.

Motivation
----------
The main guidebook (docs/guidebook/guidebook.tex) describes Apollo
probe emplacement only in prose (Ch. 2, Step 1) and shows a global
landing-site map (Fig. 1.1) and a per-sensor timeline (Fig. 2.3), but
never the physical borehole geometry itself. A borehole-geometry
figure and a sensor schematic exist as pre-rendered PDFs
(fig_book_probelayout.pdf, fig_book_sensor.pdf) referenced only from
the *extended* edition (docs/guidebook/reference/guidebook-extended.tex)
-- and neither has a reproducible source script anywhere in this
repository. This script is a new, fully-sourced replacement that
covers the same content from real per-sensor data already in the repo
(``data/apollo/depth/a15p*_depth.tab`` via ``lunar.apollo_helpers``),
sized and captioned for inclusion in the main guidebook.

Run with::

  python3 pipeline/figures/make_probe_geometry_figure.py

No network access required; reads the local Apollo HFE depth cache.
"""
from __future__ import annotations
import sys
import pathlib

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, FancyBboxPatch, Circle
from matplotlib.lines import Line2D

ROOT        = pathlib.Path(__file__).resolve().parents[2]
LETTER_FIGS = ROOT / "results" / "figures"
LETTER_FIGS.mkdir(parents=True, exist_ok=True)
sys.path.insert(0, str(ROOT / "src"))

from lunar.apollo_helpers import extract_sensor_stability
from lunar.config import SITES

C_CORAL, C_TEAL, C_FOREST = "#B85B3A", "#2A6478", "#3D6E4A"
C_CHAR, C_DIM, C_GRID = "#2A2520", "#6E6862", "#E8E5E0"

plt.rcParams.update({
    "font.family":      "serif",
    "font.serif":       ["Times", "Times New Roman", "DejaVu Serif"],
    "font.size":        10.0,
    "axes.edgecolor":   C_CHAR,
    "figure.facecolor": "white", "savefig.facecolor": "white",
    "figure.dpi":       150, "savefig.dpi": 300,
    "savefig.bbox":     "tight", "savefig.pad_inches": 0.12,
})

# probes ~8.8 m apart at Hadley Rille; the schematic below is a
# not-to-horizontal-scale sketch of the vertical geometry, as noted in
# its own caption.
PROBE_SEPARATION_NOTE = "Not to horizontal scale (probes ~8.8 m apart in reality)"


def _probe_sensor_list(site: str, probe_num: int, min_depth_cm: float):
    """Return [(depth_cm, name, is_shallow), ...] sorted by depth for one
    probe, read from the restored Apollo HFE record."""
    data = extract_sensor_stability(site.lower(), min_depth_cm)
    pdata = data["probe_data"][probe_num]
    rows = [(s["depth_cm"], name, s["depth_cm"] < min_depth_cm)
            for name, s in pdata.items()]
    return sorted(rows, key=lambda r: r[0])


def _draw_borehole_panel(ax, site="a15"):
    tag = site.upper()
    min_depth = SITES[tag]["MIN_DEPTH_CM"]
    probe1 = _probe_sensor_list(tag, 1, min_depth)
    probe2 = _probe_sensor_list(tag, 2, min_depth)

    z_max = max(max(d for d, _, _ in probe1), max(d for d, _, _ in probe2)) + 20
    ax.set_xlim(-5, 105)
    ax.set_ylim(z_max, -22)
    ax.axis("off")

    # continuous compaction-gradient background (light tan -> warm brown)
    n_slice = 100
    edges = np.linspace(-22, z_max, n_slice + 1)
    for k in range(n_slice):
        f = k / (n_slice - 1)
        r, g, b = 0.96 - 0.22 * f, 0.91 - 0.24 * f, 0.84 - 0.26 * f
        ax.add_patch(Rectangle((-5, edges[k]), 110, edges[k + 1] - edges[k],
                                facecolor=(r, g, b), edgecolor="none", zorder=0))
    ax.plot([-5, 105], [0, 0], color=C_CHAR, lw=1.6, zorder=3)
    ax.text(-3, -6, "lunar surface", fontsize=8.5, style="italic", color=C_CHAR)

    ax.axhspan(0, min_depth, color=C_CORAL, alpha=0.08, zorder=1)
    ax.plot([-5, 105], [min_depth, min_depth], color=C_CORAL, ls="--", lw=1.1,
            zorder=3)
    ax.text(103, min_depth - 3, f"z = {int(min_depth)} cm\n(borestem cut)",
            ha="right", va="bottom", fontsize=7.3, color=C_CORAL,
            style="italic")

    def draw_probe(cx, sensors, label, color, side):
        ax.add_patch(FancyBboxPatch(
            (cx - 3, -14), 6, z_max - 14 + 6,
            boxstyle="round,pad=0,rounding_size=1.0",
            facecolor="#D9D2C6", edgecolor=C_DIM, lw=1.0, zorder=2))
        ax.text(cx, -17, label, ha="center", fontsize=9, fontweight="bold",
                color=C_CHAR)
        for depth, name, shallow in sensors:
            if shallow:
                ax.add_patch(Circle((cx, depth), 2.6, facecolor="white",
                                     edgecolor=C_DIM, lw=1.3, zorder=4))
            else:
                ax.add_patch(Circle((cx, depth), 2.6, facecolor=color,
                                     edgecolor="white", lw=1.0, zorder=4))
            xtext = cx + side * 24
            ax.annotate(f"{name} ({int(depth)} cm)", xy=(cx + side * 3, depth),
                        xytext=(xtext, depth), fontsize=6.9,
                        color=C_DIM if shallow else C_CHAR, va="center",
                        ha="left" if side > 0 else "right",
                        arrowprops=dict(arrowstyle="-", color=C_DIM, lw=0.6))

    draw_probe(25, probe1, "Probe 1", C_FOREST, side=-1)
    draw_probe(75, probe2, "Probe 2", C_TEAL, side=+1)
    ax.text(50, -20, "HFE electronics box", ha="center", fontsize=7.8,
            style="italic", color=C_DIM)

    handles = [
        Line2D([0], [0], marker="o", color="white", markerfacecolor="white",
               markeredgecolor=C_DIM, mew=1.3, ms=7, lw=0,
               label="shallow (excluded)"),
        Line2D([0], [0], marker="o", color="white", markerfacecolor=C_FOREST,
               mew=0, ms=7, lw=0, label="deep (sets $K_d$)"),
    ]
    ax.legend(handles=handles, loc="lower center", bbox_to_anchor=(0.5, -0.10),
              ncol=2, frameon=True, fontsize=7.5, edgecolor=C_GRID)
    ax.text(50, z_max - 3, PROBE_SEPARATION_NOTE, ha="center", fontsize=7.0,
            style="italic", color=C_DIM)

    site_label = "Apollo 15" if tag == "A15" else "Apollo 17"
    site_desc = "Hadley Rille" if tag == "A15" else "Taurus\u2013Littrow"
    ax.set_title(f"(a)  {site_label} borehole geometry ({site_desc})",
                 fontsize=10.5, fontweight="bold", pad=10, loc="left")


def _draw_sensor_panel(ax):
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 8)
    ax.axis("off")
    ax.add_patch(FancyBboxPatch((4.3, 0.5), 1.4, 7.0,
                                 boxstyle="round,pad=0,rounding_size=0.3",
                                 facecolor="#D9D2C6", edgecolor=C_DIM, lw=1.2,
                                 zorder=2))
    y_upper, y_lower = 5.5, 2.5
    for y, lbl, col in [(y_upper, "$T_\\mathrm{upper}$", C_TEAL),
                         (y_lower, "$T_\\mathrm{lower}$", C_FOREST)]:
        ax.plot([2.0, 8.0], [y, y], color=col, lw=2.2, zorder=4)
        ax.add_patch(Circle((5.0, y), 0.22, facecolor=col, edgecolor="white",
                             lw=1.0, zorder=5))
        ax.text(1.7, y, lbl, ha="right", va="center", fontsize=9.5, color=col)
        ax.text(8.3, y, "platinum-resistance\nbridge", ha="left", va="center",
                fontsize=7.3, color=C_DIM)
    ax.annotate("", xy=(1.1, y_upper), xytext=(1.1, y_lower),
                arrowprops=dict(arrowstyle="<->", color=C_CHAR, lw=1.0))
    ax.text(0.75, (y_upper + y_lower) / 2, "$\\Delta z \\approx 50$ cm",
            ha="right", va="center", fontsize=8.5, color=C_CHAR, rotation=90)
    ax.text(5.0, 0.9,
            r"$\dfrac{\partial T}{\partial z} \approx "
            r"\dfrac{T_\mathrm{lower}-T_\mathrm{upper}}{\Delta z}$"
            "   " r"$q = -K\,\dfrac{\partial T}{\partial z}$",
            ha="center", va="center", fontsize=9.8, color=C_CHAR,
            bbox=dict(boxstyle="round,pad=0.4", fc="#F4F1EC", ec=C_GRID))
    ax.set_title("(b)  One HFE sensor: a gradient bridge", fontsize=10.5,
                 fontweight="bold", pad=10, loc="left")


def build_figure():
    fig = plt.figure(figsize=(10.5, 6.2))
    gs = fig.add_gridspec(1, 2, width_ratios=[1.15, 1.0], wspace=0.28)
    ax1 = fig.add_subplot(gs[0])
    ax2 = fig.add_subplot(gs[1])
    _draw_borehole_panel(ax1, site="a15")
    _draw_sensor_panel(ax2)
    return fig


def main():
    out = LETTER_FIGS / "fig_probe_geometry.pdf"
    fig = build_figure()
    fig.savefig(out)
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
