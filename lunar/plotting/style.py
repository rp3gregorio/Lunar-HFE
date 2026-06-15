"""Publication figure style: JGR:Planets sizes, palette, and helpers.

Single home for what used to live at the top of make_results_figures.py
and be imported across every figure (and even the pipeline) script.
Importing this module applies the rcParams; the names below are meant to
be pulled in with ``from lunar.plotting.style import *``.
"""
from __future__ import annotations

import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap

# ─── JGR:Planets figure widths ───────────────────────────────────────────────
# single 95 mm = 3.74 in, 1.5-col 140 mm = 5.51 in, full 190 mm = 7.48 in.
JGR_FULL = 7.48
JGR_HALF = 5.51
JGR_SINGLE = 3.74

FS_BASE = 10.0
FS_TITLE = 11.5
FS_LABEL = 10.5
FS_TICK = 9.5
FS_LEGEND = 9.5

plt.rcParams.update({
    "font.family": "serif",
    "font.serif": ["Times", "Times New Roman", "DejaVu Serif"],
    "font.size": FS_BASE,
    "axes.titlesize": FS_TITLE,
    "axes.titleweight": "bold",
    "axes.labelsize": FS_LABEL,
    "axes.linewidth": 0.9,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "axes.edgecolor": "#2A2520",
    "axes.labelcolor": "#2A2520",
    "axes.titlecolor": "#2A2520",
    "axes.titlepad": 10.0,
    "axes.titlelocation": "left",
    "xtick.labelsize": FS_TICK,
    "ytick.labelsize": FS_TICK,
    "xtick.color": "#2A2520",
    "ytick.color": "#2A2520",
    "xtick.major.size": 3.5,
    "ytick.major.size": 3.5,
    "xtick.major.width": 0.8,
    "ytick.major.width": 0.8,
    "xtick.minor.size": 2.0,
    "ytick.minor.size": 2.0,
    "legend.fontsize": FS_LEGEND,
    "legend.title_fontsize": FS_LEGEND,
    "legend.frameon": True,
    "legend.fancybox": False,
    "legend.framealpha": 0.97,
    "legend.edgecolor": "#D4CFC4",
    "legend.borderpad": 0.6,
    "legend.handletextpad": 0.7,
    "figure.facecolor": "white",
    "savefig.facecolor": "white",
    "figure.dpi": 150,
    "savefig.dpi": 300,
    "savefig.bbox": "tight",
    "savefig.pad_inches": 0.15,
    "grid.color": "#E8E5E0",
    "grid.linewidth": 0.6,
    "lines.linewidth": 2.0,
})

# ─── palette ─────────────────────────────────────────────────────────────────
C_CORAL = "#B85B3A"
C_CORAL_L = "#E5A88A"
C_TEAL = "#2A6478"
C_TEAL_L = "#7CA3B0"
C_FOREST = "#3D6E4A"
C_FOREST_L = "#94B89C"
C_PLUM = "#5A4A6A"
C_CHAR = "#2A2520"
C_DIM = "#6E6862"
C_NEUTRAL = "#A8A29A"
C_GRID = "#E8E5E0"

# site / source roles
C_A15 = C_FOREST
C_A17 = C_CORAL
C_HAYNE = C_TEAL
C_MS = "#9E2A1F"
C_LAB = C_PLUM

ANTH_DIVERGE = LinearSegmentedColormap.from_list(
    "anth_diverge",
    ["#2A6478", "#7CA3B0", "#F5F1EA", "#E5A88A", "#B85B3A", "#7A2F18"])
ANTH_SEQ = LinearSegmentedColormap.from_list(
    "anth_seq",
    ["#FAF7F2", "#E5D5C8", "#D9A07C", "#B85B3A", "#7A2F18", "#3A1A0A"])


# ─── layout helpers ──────────────────────────────────────────────────────────
def fmt_axis(ax, *, xlabel="", ylabel="", title=""):
    if xlabel:
        ax.set_xlabel(xlabel)
    if ylabel:
        ax.set_ylabel(ylabel)
    if title:
        ax.set_title(title)
    ax.grid(axis="both", color=C_GRID, lw=0.5)
    ax.set_axisbelow(True)
    for s in ax.spines.values():
        s.set_color(C_CHAR)


def legend_outside(ax, *, loc="right", **kwargs):
    """Place a legend outside the data area ('right' or 'bottom')."""
    if loc == "right":
        defaults = dict(bbox_to_anchor=(1.02, 1.0), loc="upper left",
                        borderaxespad=0.0, frameon=True)
    elif loc == "bottom":
        defaults = dict(bbox_to_anchor=(0.5, -0.18), loc="upper center",
                        borderaxespad=0.0, frameon=True, ncols=2)
    else:
        defaults = dict(loc=loc)
    defaults.update(kwargs)
    return ax.legend(**defaults)


def legend_below(fig, handles, labels, *, ncols=3, pad_in=0.10, **kw):
    """Shared legend in a reserved strip below all axes; grows the figure
    downward so no axis label is ever overlapped."""
    fig.canvas.draw()
    leg = fig.legend(handles, labels, loc="lower center",
                     bbox_to_anchor=(0.5, 0.0), ncols=ncols,
                     frameon=True, edgecolor=C_GRID, framealpha=0.97,
                     borderpad=0.6, **kw)
    fig.canvas.draw()
    bb = leg.get_window_extent()
    leg_h_in = bb.height / fig.dpi
    fig_w, fig_h = fig.get_size_inches()
    reserve = leg_h_in + pad_in
    new_h = fig_h + reserve
    fig.set_size_inches(fig_w, new_h)
    frac = reserve / new_h
    for ax in fig.axes:
        p = ax.get_position()
        ax.set_position([p.x0, frac + p.y0 * (1 - frac),
                         p.width, p.height * (1 - frac)])
    leg.set_bbox_to_anchor((0.5, pad_in / new_h / 2), transform=fig.transFigure)
    return leg
