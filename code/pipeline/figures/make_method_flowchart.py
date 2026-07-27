#!/usr/bin/env python3
"""The flux-anchored outer loop as a single-cycle flowchart (thesis fig:methodflow).

Step A (skin forward solve) -> Step B (closure reconstruction) -> a drift
test that either stops or reseeds Step A. Three boxes, three connectors:
  A -> B          hand off the anchor mean and the rectified flux
  B -> reseed A   coral loop-back ("set T_init = T_recon, repeat")
  B -> Stop       grey "check each cycle" drop to the convergence test

Every label is the certified method: n_inner skin lunations, closure
d<T>/dz = (Q_b - u_rect)/K, anchor drift tolerance 0.005 K, ~4 outer
cycles (2 primer at z0 = 0.25 m + 2 production at z0 = 0.55 m).

The coral reseed label sits in the empty band ABOVE the loop-back line,
never on it.

Output: figures/fig_method_fluxanchored.pdf
Run:    python code/pipeline/figures/make_method_flowchart.py
"""
from __future__ import annotations
import pathlib
import sys

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.path import Path
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

_REPO = pathlib.Path(__file__).resolve().parents[1].parent
sys.path.insert(0, str(_REPO / "src"))

from lunar.plotting.style import JGR_FULL, C_CHAR, C_DIM, C_CORAL, C_FOREST

OUT = _REPO / ".." / "figures"

TITLE_FS = 10.0
BODY_FS = 8.6
ARROW_FS = 8.6


def rounded_path(pts, r=0.16):
    """Polyline through pts with quadratic-Bezier rounded corners."""
    pts = [np.asarray(p, float) for p in pts]
    verts = [tuple(pts[0])]
    codes = [Path.MOVETO]
    for i in range(1, len(pts) - 1):
        p0, p1, p2 = pts[i - 1], pts[i], pts[i + 1]
        v0, v1 = p0 - p1, p2 - p1
        l0, l1 = np.linalg.norm(v0), np.linalg.norm(v1)
        rr = min(r, l0 / 2, l1 / 2)
        a = p1 + v0 / l0 * rr
        b = p1 + v1 / l1 * rr
        verts += [tuple(a), tuple(p1), tuple(b)]
        codes += [Path.LINETO, Path.CURVE3, Path.CURVE3]
    verts.append(tuple(pts[-1]))
    codes.append(Path.LINETO)
    return Path(verts, codes)


def arrow(ax, pts, color, r=0.16):
    fa = FancyArrowPatch(
        path=rounded_path(pts, r=r), arrowstyle="-|>", mutation_scale=13,
        lw=1.4, color=color, capstyle="round", joinstyle="round",
        shrinkA=0, shrinkB=0, zorder=2,
    )
    ax.add_patch(fa)


def box(ax, x0, y0, x1, y1, edge):
    ax.add_patch(FancyBboxPatch(
        (x0, y0), x1 - x0, y1 - y0,
        boxstyle="round,pad=0,rounding_size=0.06",
        facecolor="white", edgecolor=edge, lw=1.3, zorder=3,
    ))


def two_color(ax, renderer, x, y, prefix, value):
    """Grey prefix ('Consumes:' ...) then charcoal value on the same line."""
    t = ax.text(x, y, prefix, color=C_DIM, fontsize=BODY_FS, ha="left",
                va="baseline", family="serif", zorder=4)
    bb = t.get_window_extent(renderer=renderer)
    x2 = ax.transData.inverted().transform((bb.x1, bb.y0))[0]
    ax.text(x2, y, "  " + value, color=C_CHAR, fontsize=BODY_FS, ha="left",
            va="baseline", family="serif", zorder=4)


def main():
    fig, ax = plt.subplots(figsize=(JGR_FULL, 3.05))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 4.2)
    ax.axis("off")

    # --- boxes ---
    box(ax, 0.15, 2.60, 4.25, 4.10, C_CHAR)     # Step A
    box(ax, 5.75, 2.60, 9.85, 4.10, C_CHAR)     # Step B
    box(ax, 2.40, 0.30, 7.60, 1.70, C_FOREST)   # Stop

    # --- connectors ---
    arrow(ax, [(4.25, 3.55), (5.75, 3.55)], C_CHAR)                       # A -> B
    arrow(ax, [(6.00, 2.60), (6.00, 2.05), (2.30, 2.05), (2.30, 2.60)],   # B -> reseed A
          C_CORAL)
    arrow(ax, [(6.90, 2.60), (6.90, 1.70)], C_DIM)                        # B -> Stop

    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()

    # --- Step A text ---
    ax.text(0.35, 3.86, "Step A: forward solve", fontweight="bold",
            fontsize=TITLE_FS, family="serif", color=C_CHAR, zorder=4)
    two_color(ax, renderer, 0.35, 3.52, "Consumes:", r"$T_{\rm init}(z)$")
    two_color(ax, renderer, 0.35, 3.22, "Action:",
              r"run $n_{\rm inner}$ lunations on the skin")
    ax.text(0.35, 2.94, "(Crank–Nicolson + Newton + Thomas)", fontsize=BODY_FS,
            family="serif", color=C_CHAR, va="baseline", zorder=4)
    two_color(ax, renderer, 0.35, 2.68, "Produces:",
              r"$\langle T\rangle_{\rm skin},\ \langle T\rangle(z_0),\ u_{\rm rect}$")

    # --- Step B text ---
    ax.text(5.95, 3.86, "Step B: closure reconstruction", fontweight="bold",
            fontsize=TITLE_FS, family="serif", color=C_CHAR, zorder=4)
    two_color(ax, renderer, 5.95, 3.52, "Consumes:",
              r"$\langle T\rangle(z_0),\ u_{\rm rect}$")
    two_color(ax, renderer, 5.95, 3.22, "Action:",
              r"integrate $d\langle T\rangle/dz=(Q_b-u_{\rm rect})/K$")
    ax.text(5.95, 2.94, "downward from the anchor (RK2)", fontsize=BODY_FS,
            family="serif", color=C_CHAR, va="baseline", zorder=4)
    two_color(ax, renderer, 5.95, 2.68, "Produces:",
              r"$T_{\rm recon}(z)\ \ (z>z_0)$")

    # --- Stop text (centered in the wide box) ---
    ax.text(5.00, 1.44, "Stop when converged", fontweight="bold",
            fontsize=TITLE_FS, family="serif", color=C_CHAR, ha="center",
            va="baseline", zorder=4)
    ax.text(5.00, 1.10,
            r"$|\langle T\rangle(z_0)^{(k)}-\langle T\rangle(z_0)^{(k-1)}|<0.005$ K",
            fontsize=BODY_FS, family="serif", color=C_CHAR, ha="center",
            va="baseline", zorder=4)
    ax.text(5.00, 0.78, "Typical: 4 outer cycles", fontsize=BODY_FS,
            family="serif", color=C_CHAR, ha="center", va="baseline", zorder=4)
    ax.text(5.00, 0.52, "(2 primer at $z_0=0.25$ m + 2 production at $z_0=0.55$ m)",
            fontsize=BODY_FS, family="serif", color=C_DIM, ha="center",
            va="baseline", zorder=4)

    # --- connector labels ---
    ax.text(5.00, 3.70, r"$\langle T\rangle(z_0),\ u_{\rm rect}$",
            fontsize=ARROW_FS, family="serif", color=C_CHAR, ha="center",
            va="bottom", zorder=4)
    # coral reseed label: in the clear band ABOVE the loop-back line (y=2.05),
    # below the box bottoms (y=2.60) — never on the arrow.
    ax.text(4.15, 2.33, r"set $T_{\rm init}=T_{\rm recon}$, repeat",
            fontsize=ARROW_FS, family="serif", color=C_CORAL, ha="center",
            va="center", style="italic", zorder=4)
    ax.text(7.85, 2.18, "check each cycle", fontsize=ARROW_FS, family="serif",
            color=C_DIM, ha="center", va="center", style="italic", zorder=4)

    OUT.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT / "fig_method_fluxanchored.pdf", bbox_inches="tight")
    plt.close(fig)


if __name__ == "__main__":
    main()
