"""Two figures about the stability-window selector.

fig_window_process.pdf
    The process, five boxes, nothing else. Left to right.

fig_window_criteria_robustness.pdf
    The defence: every free choice in the selector swept through the FULL
    retrieval, plotted against the site contrast it would have to close to
    matter. Reads from results/window_criteria_sensitivity.json (written by
    pipeline/compute/compute_window_criteria_sensitivity.py) -- no numbers are
    typed in here.
"""
from __future__ import annotations

import json
import pathlib
import sys

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "src"))

from lunar.plotting.style import (                                   # noqa: E402
    C_A15, C_A17, C_CHAR, C_DIM, C_GRID, C_NEUTRAL, C_TEAL, fmt_axis,
)

REPO = pathlib.Path(__file__).resolve().parents[2]
OUT = REPO.parent / "figures"
DATA = json.loads((REPO / "results" / "window_criteria_sensitivity.json").read_text())

PT = 1.0 / 72.0


# ==========================================================================
# 1. the process, five boxes
# ==========================================================================
def fig_process():
    # Sized so it stays legible when scaled to \textwidth on A4 portrait
    # (6.46 in): at 10.0 in wide the scale factor is 0.65, so the 13 pt box
    # titles land at ~8.4 pt on the page. A 12 in canvas dropped them to 5.7 pt.
    W, H = 10.0, 3.05
    fig = plt.figure(figsize=(W, H), dpi=200)
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, W)
    ax.set_ylim(0, H)
    ax.axis("off")

    n_used = {s: DATA["sweeps"]["depth"][s]["N_deep"][
        DATA["sweeps"]["depth"]["values"].index(DATA["adopted"]["depth"])]
        for s in ("A15", "A17")}

    steps = [
        ("1", "One sensor's record", ["3.9 to 4.8 years", "of temperatures"], C_NEUTRAL),
        ("2", "Cut off the bad head", ["drilling heated it;", "wait for it to flatten"], C_TEAL),
        ("3", "Average what is left", ["that mean is T_eq,", "the number we fit"], C_TEAL),
        ("4", "Drop shallow sensors", ["depth ≥ 80 cm, clear", "of the borestem"], C_A17),
        ("5", "The fitting set",
         [f"Apollo 15    {n_used['A15']}", f"Apollo 17    {n_used['A17']}"], C_A15),
    ]

    m, gapx = 0.18, 0.24
    bw = (W - 2 * m - 4 * gapx) / 5
    by, bh = 0.80, 1.50

    ax.text(m, H - 0.16, "How one temperature gets made", ha="left", va="top",
            fontsize=15.5, fontweight="bold", color=C_CHAR)

    for k, (num, title, lines, col) in enumerate(steps):
        x = m + k * (bw + gapx)
        for lw, fc, a, z in ((1.5, col, 1.0, 2.0), (0, "white", 0.93, 2.1)):
            ax.add_patch(FancyBboxPatch(
                (x, by), bw, bh, boxstyle="round,pad=0,rounding_size=0.09",
                linewidth=lw, edgecolor=col if lw else "none",
                facecolor=fc, alpha=a, zorder=z))
        ax.text(x + bw / 2, by + bh - 0.27, num, ha="center", va="center",
                fontsize=15, fontweight="bold", color=col, alpha=0.45, zorder=3)
        ax.text(x + bw / 2, by + bh - 0.64, title, ha="center", va="center",
                fontsize=12.4, fontweight="bold", color=col, zorder=3)
        for j, ln in enumerate(lines):
            ax.text(x + bw / 2, by + bh - 0.99 - 0.27 * j, ln, ha="center",
                    va="center", fontsize=10.4, color=C_CHAR, zorder=3)
        if k < 4:
            ax.add_patch(FancyArrowPatch(
                (x + bw + 0.045, by + bh / 2), (x + bw + gapx - 0.045, by + bh / 2),
                arrowstyle="-|>", mutation_scale=13, linewidth=1.6,
                color=C_NEUTRAL, shrinkA=0, shrinkB=0, zorder=1.5))

    ax.text(m, by - 0.20, "flat  =  the line through the tail rises less than "
            "0.08 K per year.      If nothing is ever flat, take the last 25 % "
            "of the record.", ha="left", va="top", fontsize=10.0,
            color=C_DIM, style="italic")

    fig.savefig(OUT / "fig_window_process.pdf")
    fig.savefig(OUT / "fig_window_process.png", dpi=200, facecolor="white")
    plt.close(fig)
    print(f"  -> {OUT / 'fig_window_process.png'}")


# ==========================================================================
# 2. the robustness proof
# ==========================================================================
def fig_robustness():
    knobs = ["slope", "floor", "fallback", "depth"]
    nice = {"slope": "(a)  flatness bar", "floor": "(b)  earliest window start",
            "fallback": "(c)  fallback window start", "depth": "(d)  depth cut"}
    xlab = {"slope": "K per year", "floor": "% into the record",
            "fallback": "% into the record", "depth": "cm"}
    scale = {"slope": 1, "floor": 100, "fallback": 100, "depth": 1}

    fig, axes = plt.subplots(1, 4, figsize=(12.0, 3.75), dpi=200, sharey=True)

    # The claim, fixed in every panel: the gap between the two sites at the
    # adopted settings. A knob only matters if it can visibly close this.
    iad = DATA["sweeps"]["slope"]["values"].index(DATA["adopted"]["slope"])
    kd15 = DATA["sweeps"]["slope"]["A15"]["kd_star_mW"][iad]
    kd17 = DATA["sweeps"]["slope"]["A17"]["kd_star_mW"][iad]
    adopted_gap = kd17 - kd15

    for ax, knob in zip(axes, knobs):
        sw = DATA["sweeps"][knob]
        x = np.array(sw["values"], dtype=float) * scale[knob]
        xa = DATA["adopted"][knob] * scale[knob]

        ax.fill_between([-1e9, 1e9], [kd15] * 2, [kd17] * 2,
                        color=C_GRID, alpha=0.75, lw=0, zorder=0)

        for site, col in (("A15", C_A15), ("A17", C_A17)):
            y = np.array(sw[site]["kd_star_mW"], dtype=float)
            ax.plot(x, y, "-o", color=col, lw=2.0, ms=5.2, mec="white",
                    mew=0.8, zorder=3, label=f"Apollo {site[1:]}")
            ia = int(np.argmin(np.abs(x - xa)))
            ax.plot([x[ia]], [y[ia]], "o", ms=10, mfc="none", mec=col,
                    mew=1.8, zorder=4)

        ax.axvline(xa, color=C_DIM, lw=0.9, ls=":", zorder=1)
        fmt_axis(ax, xlabel=xlab[knob],
                 ylabel="Retrieved K_d*  (mW/m/K)" if knob == "slope" else "",
                 title=nice[knob])
        pad = 0.08 * (x.max() - x.min())
        ax.set_xlim(x.min() - pad, x.max() + pad)
        ax.set_xticks(x)
        sp15 = sw["A15"]["spread_mW"]
        sp17 = sw["A17"]["spread_mW"]
        ax.text(0.5, 0.045,
                f"largest swing:  A15 {sp15:.3f}    A17 {sp17:.3f}",
                transform=ax.transAxes, ha="center", va="bottom",
                fontsize=8.4, color=C_DIM, zorder=5)

    axes[0].set_ylim(3.95, 8.75)
    axes[0].legend(frameon=True, edgecolor=C_GRID, fontsize=8.6, loc="upper left")

    fig.suptitle("Every free choice in the window selector, swept through the "
                 "full retrieval", x=0.008, y=0.995, ha="left",
                 fontsize=13.5, fontweight="bold", color=C_CHAR)
    fig.text(0.008, 0.928,
             f"Grey band = the site difference being claimed ({adopted_gap:.2f} mW/m/K).  "
             f"A choice only matters if it can visibly close that band.  "
             f"Ring marks the adopted value.  Only the depth cut does anything — and only "
             f"at 60 cm, where the borestem-contaminated sensors it exists to remove get back in.",
             ha="left", va="top", fontsize=8.5, color=C_DIM, style="italic")
    fig.subplots_adjust(left=0.062, right=0.992, top=0.772, bottom=0.148, wspace=0.10)

    fig.savefig(OUT / "fig_window_criteria_robustness.pdf")
    fig.savefig(OUT / "fig_window_criteria_robustness.png", dpi=200, facecolor="white")
    plt.close(fig)
    print(f"  -> {OUT / 'fig_window_criteria_robustness.png'}")


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    fig_process()
    fig_robustness()


if __name__ == "__main__":
    main()
