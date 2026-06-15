#!/usr/bin/env python3
"""Diagrams for the code-usage guide (docs/code_guide/code_guide.tex).

Two clean box-and-arrow diagrams (no label overlaps): the three-layer
architecture and the physics->number->figure data flow.

Run:  python scripts/figures/make_codeguide_figures.py
"""
from __future__ import annotations
import sys, pathlib

_REPO = pathlib.Path(__file__).resolve().parents[1].parent
sys.path.insert(0, str(_REPO))

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

from lunar.plotting.style import C_A15, C_A17, C_HAYNE, C_CORAL, C_CHAR, C_DIM, C_GRID

OUT = _REPO / "docs" / "code_guide" / "figures"
OUT.mkdir(parents=True, exist_ok=True)


def _box(ax, x, y, w, h, text, fc, ec, fs=9):
    ax.add_patch(FancyBboxPatch((x, y), w, h,
                 boxstyle="round,pad=0.02,rounding_size=0.06",
                 facecolor=fc, edgecolor=ec, lw=1.3))
    ax.text(x + w / 2, y + h / 2, text, ha="center", va="center",
            fontsize=fs, color=C_CHAR)


def fig_architecture():
    fig, ax = plt.subplots(figsize=(9.0, 6.2))
    ax.set_xlim(0, 12); ax.set_ylim(0, 12); ax.axis("off")

    # band tags (kept short + lifted clear of the boxes below them)
    for y, lab in [(11.55, "paper/"), (7.05, "scripts/"), (3.45, "lunar/")]:
        ax.text(0.2, y, lab, fontsize=11, color=C_DIM, fontweight="bold")

    # paper layer
    _box(ax, 1.0, 10.0, 4.3, 1.2, "paper/letter/\nletter.tex", "#EfF3F2", C_HAYNE)
    _box(ax, 6.7, 10.0, 4.3, 1.2, "paper/primer/\nguidebook.tex", "#EfF3F2", C_HAYNE)

    # scripts layer
    _box(ax, 0.8, 5.4, 5.0, 1.5,
         "scripts/pipeline/\nretrieve_kd.py  +  compute_*.py\n(compute -> output/*.json)",
         "#FdEee7", C_A17)
    _box(ax, 6.4, 5.4, 4.8, 1.5,
         "scripts/figures/\nmake_*_figures.py\n(JSON -> PDFs)", "#FdEee7", C_A17)

    # lunar layer (two rows)
    mods1 = [("config.py", 0.6), ("constants.py", 3.0), ("grid.py", 5.6),
             ("properties.py", 7.7)]
    for name, x in mods1:
        _box(ax, x, 2.3, 2.2, 0.95, name, "#EAF1ED", C_A15, fs=8.5)
    _box(ax, 10.1, 2.3, 1.5, 0.95, "plotting/\nstyle.py", "#EAF1ED", C_A15, fs=8)
    mods2 = [("solver.py", 2.0), ("equilibrium.py", 4.5),
             ("apollo_helpers.py", 7.2)]
    for name, x in mods2:
        _box(ax, x, 1.0, 2.4, 0.95, name, "#EAF1ED", C_A15, fs=8.5)

    # downward dependency arrows
    for x0 in (3.3, 8.8):
        ax.add_patch(FancyArrowPatch((x0, 10.0), (x0, 6.95),
                     arrowstyle="-|>", mutation_scale=15, color=C_DIM, lw=1.6))
    for x0 in (3.3, 8.8):
        ax.add_patch(FancyArrowPatch((x0, 5.4), (x0, 3.3),
                     arrowstyle="-|>", mutation_scale=15, color=C_DIM, lw=1.6))
    ax.text(3.55, 8.4, "consume", rotation=90, fontsize=8, color=C_DIM, va="center")
    ax.text(3.55, 4.2, "import", rotation=90, fontsize=8, color=C_DIM, va="center")

    ax.text(6.0, 0.15, "Dependencies point only DOWNWARD — nothing in lunar/ imports a script.",
            ha="center", fontsize=8.5, color=C_CHAR, style="italic")
    ax.set_title("The three-layer architecture", fontsize=12, fontweight="bold",
                 loc="left", color=C_CHAR)
    fig.savefig(OUT / "fig_architecture.pdf", bbox_inches="tight")
    plt.close(fig)
    print("  -> fig_architecture.pdf")


def fig_dataflow():
    fig, ax = plt.subplots(figsize=(9.4, 5.6))
    ax.set_xlim(0, 12); ax.set_ylim(0, 12); ax.axis("off")
    steps = [
        (9.9, "lunar.config + lunar.constants", "SITES, grid, Hayne params", C_A15),
        (8.4, "lunar.grid + lunar.properties", "K(T,z), rho(z), c_p(T)", C_A15),
        (6.9, "lunar.solver + lunar.equilibrium", "settled temperature profile", C_A15),
        (5.4, "retrieve_kd.run_with()", "one profile per trial K_d", C_A17),
        (3.9, "sweep + bootstrap + hold-outs", "output/kd_retrieval_results.json", C_A17),
        (2.4, "scripts/figures/*", "read JSON, draw with plotting.style", C_A17),
        (0.9, "paper/letter/figures/*.pdf", "-> letter.tex", C_HAYNE),
    ]
    for y, title, sub, col in steps:
        _box(ax, 2.3, y, 7.4, 1.05, "", "#F6F4F1", col)
        ax.text(2.6, y + 0.66, title, fontsize=9.5, color=C_CHAR, fontweight="bold")
        ax.text(2.6, y + 0.26, sub, fontsize=8.2, color=C_DIM, style="italic")
    for i in range(len(steps) - 1):
        y0 = steps[i][0]; y1 = steps[i + 1][0]
        ax.add_patch(FancyArrowPatch((6.0, y0), (6.0, y1 + 1.05),
                     arrowstyle="-|>", mutation_scale=14, color=C_DIM, lw=1.5))
    ax.text(6.0, 11.55, "run_with() is the hub: everything calls it.",
            ha="center", fontsize=9, color=C_CHAR, style="italic")
    ax.set_title("Data flow: physics -> number -> figure", fontsize=12,
                 fontweight="bold", loc="left", color=C_CHAR)
    fig.savefig(OUT / "fig_dataflow.pdf", bbox_inches="tight")
    plt.close(fig)
    print("  -> fig_dataflow.pdf")


def main():
    print("Building code-guide diagrams:")
    fig_architecture()
    fig_dataflow()
    print("done.")


if __name__ == "__main__":
    main()
