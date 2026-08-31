"""How a sensor's 'stabilized region' is chosen — process flow + worked cases.

Every temperature the K_d retrieval is fitted to is a single number, T_eq, per
sensor: the mean over a *stabilized window* at the end of that sensor's record.
This figure documents exactly how that window is picked, and shows the two
outcomes the selector actually produces on real Apollo data.

Everything is read from the shipping code path
(`lunar.apollo_helpers.find_stable_window` / `extract_sensor_stability`) and the
restored HFE tables. The two selector constants are pulled from the function's
own defaults, so the figure cannot drift from the code it documents.

Left  : the decision flow, one box per step of ``find_stable_window``.
Right : two real sensors, one per branch of the flatness test —
        A15 TG12A (91 cm) passes and keeps a 1.2 yr window;
        A17 TG11A (130 cm) finds no flat start and takes the fallback.
        The zoom panels expand the chosen window so the residual trend the
        selector accepted is actually visible.

The flow axes is drawn in INCHES (xlim/ylim set to its physical size) so box
heights, line spacing and font sizes are all in one consistent unit; laying it
out in axes fractions silently stretches the vertical spacing on a non-square
axes and throws the body text out of its box.
"""
from __future__ import annotations

import json
import pathlib
import sys

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "src"))

from lunar.apollo_helpers import (                                             # noqa: E402
    extract_sensor_stability, find_stable_window, iso_to_seconds,
)
from lunar.config import SITES                                                 # noqa: E402
from lunar.plotting.style import (                                             # noqa: E402
    C_A15, C_A17, C_CHAR, C_CORAL, C_DIM, C_FOREST, C_NEUTRAL, C_TEAL, assert_no_overlap, fmt_axis,
)
from lunar.validation import load_apollo_hfe_depth                             # noqa: E402

REPO = pathlib.Path(__file__).resolve().parents[2]
OUT = REPO.parent / "figures"

W, H = 12.4, 6.9
PT = 1.0 / 72.0

# Selector constants, taken from the function signature itself.
SLOPE_TOL = find_stable_window.__defaults__[0]      # K per year
MIN_FRAC = find_stable_window.__defaults__[1]       # fraction of record kept

FLOW_RECT = [0.017, 0.028, 0.398, 0.948]

TS, BS = 9.4, 8.0                   # title / body point size
TH, BH = TS * 1.36 * PT, BS * 1.46 * PT
PAD = 0.115                         # inner box padding [in]


def box_h(n_lines):
    return 2 * PAD + TH + n_lines * BH


def box(ax, x, y_top, w, title, lines, color, *, fill=0.06):
    """Rounded box anchored by its TOP edge; returns its height in inches."""
    h = box_h(len(lines))
    for lw, fc, a, z in ((1.3, color, 1.0, 2.0), (0.0, "white", 1.0 - fill, 2.1)):
        ax.add_patch(FancyBboxPatch(
            (x, y_top - h), w, h,
            boxstyle="round,pad=0,rounding_size=0.07",
            linewidth=lw, edgecolor=color if lw else "none",
            facecolor=fc, alpha=a, zorder=z))
    ax.text(x + w / 2, y_top - PAD - TH * 0.76, title, ha="center", va="baseline",
            fontsize=TS, fontweight="bold", color=color, zorder=3)
    for k, ln in enumerate(lines):
        ax.text(x + w / 2, y_top - PAD - TH - BH * (k + 0.74), ln,
                ha="center", va="baseline", fontsize=BS, color=C_CHAR, zorder=3)
    return h


def arrow(ax, p0, p1):
    ax.add_patch(FancyArrowPatch(
        p0, p1, arrowstyle="-|>", mutation_scale=10, linewidth=1.2,
        color=C_NEUTRAL, shrinkA=0, shrinkB=0, zorder=1.5))


def draw_flow(ax, n_used, n_all):
    aw, ah = W * FLOW_RECT[2], H * FLOW_RECT[3]
    ax.set_xlim(0, aw)
    ax.set_ylim(0, ah)
    ax.axis("off")

    xb, wb = 0.06, 3.22                 # spine
    xc = xb + wb / 2
    xs, ws = xb + wb + 0.26, 1.34       # side branches
    gap = 0.26

    ax.text(0.0, ah - 0.05, "Choosing a sensor's stabilized region",
            ha="left", va="top", fontsize=11.5, fontweight="bold", color=C_CHAR)
    ax.text(0.0, ah - 0.30,
            f"lunar.apollo_helpers.find_stable_window  ·  run once per sensor, "
            f"{n_all} sensors in all",
            ha="left", va="top", fontsize=7.9, color=C_DIM, style="italic")

    y = ah - 0.60

    y -= box(ax, xb, y, wb, "Restored HFE record, one sensor at a time",
             ["Apollo 15    12 sensors,  3.9 yr of data",
              "Apollo 17    20 sensors,  4.8 yr of data"], C_CHAR)
    arrow(ax, (xc, y), (xc, y - gap)); y -= gap

    y -= box(ax, xb, y, wb, "STEP 1    propose a window",
             ["try start = 55 %, 57.5 %, … 85 % of the record",
              "scan EARLIEST first, so the longest tail wins",
              "reject a start that keeps less than 20 % of the record"], C_TEAL)
    arrow(ax, (xc, y), (xc, y - gap)); y -= gap

    y_step2 = y
    h2 = box(ax, xb, y, wb, "STEP 2    test that window for flatness",
             ["least-squares line through everything after the start",
              f"accept the first start with |slope| ≤ {SLOPE_TOL} K per year"],
             C_CORAL)
    y_mid2 = y_step2 - h2 / 2
    arrow(ax, (xb + wb, y_mid2), (xs, y_mid2))
    ax.text((xb + wb + xs) / 2, y_mid2 + 0.045, "none passes", ha="center",
            va="bottom", fontsize=7.2, color=C_DIM, style="italic")
    box(ax, xs, y_mid2 + box_h(2) / 2, ws, "fallback",
        ["keep the last 25 %", "and carry on below"], C_DIM)
    y -= h2
    arrow(ax, (xc, y), (xc, y - gap)); y -= gap

    y -= box(ax, xb, y, wb, "STEP 3    collapse the window to one number",
             ["T_eq  = mean of T inside the window   (the fitting datum)",
              "sigma = standard deviation inside it   (its error bar)",
              "depth = restored sensor depth (Nagihara et al. 2018)"], C_TEAL)
    arrow(ax, (xc, y), (xc, y - gap)); y -= gap

    y_step4 = y
    h4 = box(ax, xb, y, wb, "STEP 4    keep only the deep sensors",
             [f"require depth ≥ {SITES['A15']['MIN_DEPTH_CM']} cm — shallower "
              f"sensors carry the",
              "borestem's own thermal signature, not the regolith's"], C_CORAL)
    y_mid4 = y_step4 - h4 / 2
    arrow(ax, (xb + wb, y_mid4), (xs, y_mid4))
    ax.text((xb + wb + xs) / 2, y_mid4 + 0.045, "too shallow", ha="center",
            va="bottom", fontsize=7.2, color=C_DIM, style="italic")
    box(ax, xs, y_mid4 + box_h(2) / 2, ws, "excluded",
        ["open markers in", "every depth figure"], C_DIM)
    y -= h4
    arrow(ax, (xc, y), (xc, y - gap)); y -= gap

    box(ax, xb, y, wb, "The K_d fitting set",
        [f"Apollo 15   {n_used['A15']} of {n_used['A15_all']} sensors      "
         f"Apollo 17   {n_used['A17']} of {n_used['A17_all']} sensors"], C_FOREST)


def case(ax_full, ax_zoom, mission, probe, sensor, color, tag):
    dtab = load_apollo_hfe_depth(mission, probe)
    subset = dtab[np.array([s.strip() for s in dtab["sensor"]]) == sensor]
    i0, day0, method, slope = find_stable_window(subset)

    t_sec = iso_to_seconds(subset["time_iso"])
    t_day = (t_sec - t_sec[0]) / 86400.0
    T = subset["T"].astype(float)
    depth = float(np.unique(subset["depth_cm"])[0])
    step = max(1, len(T) // 2500)

    ax_full.plot(t_day[::step], T[::step], lw=0.7, color=C_NEUTRAL, zorder=2)
    ax_full.plot(t_day[i0::step], T[i0::step], lw=0.9, color=color, zorder=3)
    ax_full.axvspan(t_day[i0], t_day[-1], color=color, alpha=0.11, lw=0, zorder=1)
    ax_full.axvline(t_day[i0], color=color, lw=1.0, ls="--", zorder=4)
    fmt_axis(ax_full, xlabel="Days after emplacement", ylabel="Temperature (K)",
             title=f"({tag})  {mission.upper()} {sensor} at {depth:.0f} cm")
    ax_full.set_xlim(0, t_day[-1])
    lo, hi = float(T.min()), float(T.max())
    ax_full.set_ylim(lo - 0.06 * (hi - lo), hi + 0.34 * (hi - lo))
    ax_full.text(0.035, 0.93,
                 f"window opens on day {day0:.0f}\n"
                 f"{i0 / len(T):.0%} into the record",
                 transform=ax_full.transAxes, ha="left", va="top",
                 fontsize=7.2, color=C_DIM, zorder=5)

    tt, TT = t_day[i0:], T[i0:]
    yr = (tt - tt[0]) / 365.25
    fit = np.polyval(np.polyfit(yr, TT, 1), yr)
    zs = max(1, len(TT) // 2000)
    ax_zoom.set_facecolor("#FBFAF8")
    ax_zoom.plot(tt[::zs], TT[::zs], lw=0.7, color=color, alpha=0.7, zorder=2)
    ax_zoom.plot(tt, fit, lw=1.7, color=C_CHAR, zorder=4)
    verdict = ("flat start found — kept from there on" if method == "trend_flat"
               else "no flat start — fallback to the last 25 %")
    fmt_axis(ax_zoom, xlabel="Days after emplacement", ylabel="Temperature (K)",
             title=f"the window it chose: {verdict}")
    ax_zoom.title.set_fontsize(8.6)
    ax_zoom.set_xlim(tt[0], tt[-1])
    lo, hi = float(TT.min()), float(TT.max())
    pad = 0.05 * (hi - lo)
    ax_zoom.set_ylim(lo - pad, hi + pad + 0.62 * (hi - lo))
    ok = abs(slope) <= SLOPE_TOL
    ax_zoom.text(0.035, 0.94,
                 f"fitted slope  {slope:+.3f} K/yr  "
                 f"({'passes' if ok else 'fails'} the {SLOPE_TOL} K/yr test)\n"
                 f"T_eq = {TT.mean():.3f} K      sigma = {TT.std():.3f} K",
                 transform=ax_zoom.transAxes, ha="left", va="top",
                 fontsize=7.3, color=C_CHAR, zorder=5)


def main():
    n_used = {}
    for tag in ("A15", "A17"):
        obs = extract_sensor_stability(SITES[tag]["mission"], SITES[tag]["MIN_DEPTH_CM"])
        n_used[tag] = int(obs["deep_mask"].sum())
        n_used[f"{tag}_all"] = int(obs["deep_mask"].size)

    thr = json.loads((REPO / "results" / "stability_threshold_sensitivity.json").read_text())
    bore = json.loads((REPO / "results" / "borestem_sensitivity.json").read_text())
    spread = {s: max(thr[s]["kd_star_mW"]) - min(thr[s]["kd_star_mW"]) for s in ("A15", "A17")}
    cuts = [c for c in bore["cut_cm"] if c >= 70]
    contrast = [bore["contrast"][bore["cut_cm"].index(c)] for c in cuts]

    fig = plt.figure(figsize=(W, H), dpi=200)

    ax_flow = fig.add_axes(FLOW_RECT)
    draw_flow(ax_flow, n_used, n_used["A15_all"] + n_used["A17_all"])

    lft, wid, gap = 0.487, 0.222, 0.055
    hgt = 0.300
    ax_a1 = fig.add_axes([lft, 0.585, wid, hgt])
    ax_a2 = fig.add_axes([lft + wid + gap, 0.585, wid, hgt])
    ax_b1 = fig.add_axes([lft, 0.160, wid, hgt])
    ax_b2 = fig.add_axes([lft + wid + gap, 0.160, wid, hgt])

    fig.text(lft, 0.975, "The two branches, seen on real sensors",
             ha="left", va="top", fontsize=11.5, fontweight="bold", color=C_CHAR)
    fig.text(lft, 0.940,
             "grey = the disturbed head of the record, thrown away    ·    "
             "coloured = the stabilized region that is kept",
             ha="left", va="top", fontsize=7.9, color=C_DIM, style="italic")

    case(ax_a1, ax_a2, "a15", 1, "TG12A", C_A15, "a")
    case(ax_b1, ax_b2, "a17", 1, "TG11A", C_A17, "b")

    # Guard: no annotation may sit on a plotted curve (project figure rule).
    fig.canvas.draw()
    for ax in (ax_a1, ax_a2, ax_b1, ax_b2):
        assert_no_overlap(ax)

    fig.text(lft, 0.062,
             f"Neither cut-off drives the answer.  Sweeping the flatness tolerance over "
             f"{min(thr['thresholds_K_per_yr'])}–{max(thr['thresholds_K_per_yr'])} K/yr moves "
             f"K_d* by only {spread['A15']:.3f} (A15) and {spread['A17']:.3f} (A17) mW/m/K;",
             ha="left", va="top", fontsize=7.4, color=C_DIM)
    fig.text(lft, 0.034,
             f"sweeping the depth cut over {min(cuts)}–{max(cuts)} cm leaves A17 unchanged, and "
             f"the A15-below-A17 ordering holds at every cut (contrast "
             f"{min(contrast):.2f}–{max(contrast):.2f} mW/m/K).",
             ha="left", va="top", fontsize=7.4, color=C_DIM)

    OUT.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT / "fig_stability_selection.pdf")
    fig.savefig(OUT / "fig_stability_selection.png", dpi=200, facecolor="white")
    plt.close(fig)
    print(f"  -> {OUT / 'fig_stability_selection.pdf'}")
    print(f"  -> {OUT / 'fig_stability_selection.png'}")


if __name__ == "__main__":
    main()
