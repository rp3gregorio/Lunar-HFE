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
    # maths in the Times-matched STIX face (not DejaVu Sans), and fonts embedded
    # as TrueType (Type 42) rather than Type 3 -- AGU asks for embedded fonts
    "mathtext.fontset": "stix",
    "pdf.fonttype": 42,
    "ps.fonttype": 42,
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
C_MS = "#6C4CA6"  # Martinez violet
C_LAB = C_PLUM

# measurement roles (letter Fig. 3: what constrains A and K_d), kept apart from
# the site (forest / coral) and model (teal / violet) hues
C_OCHRE = "#A8822E"      # meter-scale sensor temperatures
C_OCHRE_L = "#EADBB8"
C_BLUE = "#3E5C99"       # annual-wave diffusivity
C_BLUE_L = "#B4C3E0"
C_OBS_T, C_OBS_KAPPA, C_OBS_TS = C_OCHRE, C_BLUE, C_DIM   # ... and the surface mean
C_CONTRAST = C_CHAR      # inter-site contrast: belongs to neither site

# ── semantic roles: one colour and line style per concept in every letter
#    figure (agreed with the author 2026-10-05) ──────────────────────────────
C_A15_2 = "#6F9A78"      # second probe at Apollo 15 (Fig. 2)
C_A17_2 = "#D48A6C"      # second probe at Apollo 17 (Fig. 2)
C_HAYNE_FIT, LS_HAYNE_FIT = C_TEAL, "-"            # Hayne form at the joint fit
C_HAYNE_GLOBAL, LS_HAYNE_GLOBAL = C_TEAL_L, "--"   # Hayne form at the global K_d
C_GLOBAL_REF, LS_GLOBAL_REF = C_TEAL, ":"          # the global value 3.4 as a reference line
LS_MS = ":"                                        # Martinez & Siegler (colour C_MS)
C_EXCL_FILL, C_EXCL_EDGE = "#ECE8E2", C_NEUTRAL    # borestem / excluded zone

WARM_DIVERGE = LinearSegmentedColormap.from_list(
    "warm_diverge",
    ["#2A6478", "#7CA3B0", "#F5F1EA", "#E5A88A", "#B85B3A", "#7A2F18"])
NEUTRAL_SEQ = LinearSegmentedColormap.from_list(
    "neutral_seq", ["#F7F5F2", "#D9D4CD", "#A8A29A"])
WARM_SEQ = LinearSegmentedColormap.from_list(
    "warm_seq",
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


LEGEND_KW = dict(frameon=False, fontsize=9.0, handlelength=1.6, handleheight=0.7,
                 handletextpad=0.8, columnspacing=1.3, borderaxespad=0.0)


def legend_below(fig, handles, labels, *, ncols="auto", pad_in=0.10, **kw):
    """Shared legend in a reserved strip below all axes; grows the figure
    downward so no axis label is ever overlapped. Styled like the letter's
    Fig. 2 (no frame, 9 pt, compact handles), the house legend since
    2026-10-05; keyword arguments override LEGEND_KW.

    ncols="auto" (default) uses the FEWEST rows that fit the figure width,
    then spreads the entries evenly over those rows (no lonely half-row), and
    orders them to read left to right, row by row.
    """
    import math
    fig.canvas.draw()
    style = {**LEGEND_KW, **kw}
    handles, labels = list(handles), list(labels)
    n = len(handles)
    if ncols == "auto":
        avail = fig.get_size_inches()[0] * fig.dpi * 0.97
        nc = 1
        for c in range(n, 0, -1):
            trial = fig.legend(handles, labels, loc="lower center", bbox_to_anchor=(0.5, 0.0),
                               ncols=c, **style)
            fig.canvas.draw()
            w = trial.get_window_extent().width
            trial.remove()
            if w <= avail:
                nc = c
                break
        rows = math.ceil(n / nc)
        ncols = math.ceil(n / rows)
    # matplotlib fills a legend column by column; reorder so it reads row by row
    rows = math.ceil(n / ncols)
    order = [k * ncols + j for j in range(ncols) for k in range(rows) if k * ncols + j < n]
    handles = [handles[i] for i in order]
    labels = [labels[i] for i in order]
    leg = fig.legend(handles, labels, loc="lower center",
                     bbox_to_anchor=(0.5, 0.0), ncols=ncols, **style)
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


def assert_no_overlap(ax, *, tol_px=1.0, densify=400):
    """Programmatic text-on-data guard for one Axes.

    Raises ``AssertionError`` if the legend or ANY annotation/text box in ``ax``
    sits on top of a plotted line or marker. Call it AFTER the final draw and
    BEFORE ``savefig`` (constrained_layout finalises legend positions on draw):

        fig.canvas.draw(); assert_no_overlap(axL); assert_no_overlap(axR)
        fig.savefig(...)

    This catches the legend/annotation collisions that a low-DPI eyeball misses.
    Lines are densified so a segment crossing a text box (with no vertex inside)
    is still flagged; scatter offsets are included. A failure means: move the box
    to verified-empty space or outside the axes (see the skill's placement rules).
    """
    import numpy as np
    fig = ax.figure
    fig.canvas.draw()
    boxes = []
    leg = ax.get_legend()
    if leg is not None:
        boxes.append(("legend", leg.get_window_extent()))
    from matplotlib.text import Text as _Text
    for t in ax.texts:
        if t.get_text().strip():
            # text box ONLY — Annotation.get_window_extent() unions in the arrow,
            # and an arrow legitimately points AT a data marker; police the text.
            try:
                bb = _Text.get_window_extent(t)
            except Exception:
                bb = t.get_window_extent()
            boxes.append((repr(t.get_text()[:20]), bb))
    if not boxes:
        return
    pts = []
    for ln in ax.get_lines():
        xy = ln.get_xydata()
        if len(xy) < 1:
            continue
        if len(xy) >= 2:
            src = np.linspace(0.0, 1.0, len(xy))
            dst = np.linspace(0.0, 1.0, max(densify, len(xy)))
            xy = np.column_stack([np.interp(dst, src, xy[:, 0]),
                                  np.interp(dst, src, xy[:, 1])])
        pts.append(ax.transData.transform(xy))
    for col in ax.collections:
        off = np.asarray(col.get_offsets())
        if off.size:
            pts.append(ax.transData.transform(off))
    if not pts:
        return
    P = np.vstack(pts)
    bad = [name for name, bb in boxes
           if ((P[:, 0] > bb.x0 - tol_px) & (P[:, 0] < bb.x1 + tol_px)
               & (P[:, 1] > bb.y0 - tol_px) & (P[:, 1] < bb.y1 + tol_px)).any()]
    if bad:
        raise AssertionError(
            "TEXT-ON-DATA in '%s': %s covers plotted data — move it to "
            "verified-empty space or outside the axes."
            % (ax.get_title() or "axes", ", ".join(bad)))


# ── user style overrides (self-serve; no code knowledge needed) ──────────────
# If lunar/plotting/style_overrides.py defines any of the names above
# (FS_LEGEND, C_A15, ...) or calls plt.rcParams.update(...), it wins.
# Edit that file, re-run a generator, done. See
# deliverables/documents/notes/FIGURE_STYLING.md for the how-to.
try:
    from lunar.plotting import style_overrides as _ov
    for _name in dir(_ov):
        if not _name.startswith("_"):
            globals()[_name] = getattr(_ov, _name)
except ImportError:
    pass
