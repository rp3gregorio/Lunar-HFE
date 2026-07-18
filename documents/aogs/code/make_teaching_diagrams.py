"""Two teaching diagrams for the guidebook:
  aogs_combinations.pdf   — how the 5 knobs multiply to 162 / 650 runs.
  aogs_cp_vs_coupled.pdf  — the fork (density's two jobs) + the real K_c(rho) line.

Grid values and K_d* are read from the results archive (never hand-typed);
K_s, rho_s, rho_d from lunar.constants. Move-proof paths.
Run:  <repo>/.venv/bin/python make_teaching_diagrams.py
"""
import json
import pathlib
import sys

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches

sys.path.insert(0, str(next(a for a in pathlib.Path(__file__).resolve().parents
                            if (a / "code" / "src" / "lunar").is_dir()) / "code" / "src"))
from lunar.plotting.style import (JGR_FULL, C_A15, C_A17, C_TEAL, C_CHAR, C_DIM,  # noqa: E402
                                  C_GRID, C_FOREST, fmt_axis, assert_no_overlap)
from lunar.constants import RHO_SURFACE, RHO_DEEP, K_SURFACE  # noqa: E402

AOGS = next(a for a in pathlib.Path(__file__).resolve().parents if a.name == "aogs")
OUT = AOGS / "figures" / "diagrams"; OUT.mkdir(parents=True, exist_ok=True)
_d = json.loads((AOGS / "results" / "aogs_density_study.json").read_text())
M = _d["meta"]
RHO1, RHO2, RHO3 = M["rho1"], M["rho2"], M["rho3"]
Z1 = [int(z * 100) for z in M["z1_grid"]]
Z2 = [int(z * 100) for z in M["z2_grid"]]
KD = {s: _d["sites"][s]["kd_star_used"] * 1e3 for s in ("A15", "A17")}
KS, RS, RD = K_SURFACE * 1e3, RHO_SURFACE, RHO_DEEP


# ── Diagram 1 : the counting ────────────────────────────────────────────────
def combinations():
    fig, ax = plt.subplots(figsize=(JGR_FULL, 4.2), constrained_layout=True)
    ax.set_xlim(0, 100); ax.set_ylim(0, 100); ax.axis("off")

    def chip(x, y, label, w=7.2, h=6.2, fc=C_GRID, tc=C_CHAR, fs=9):
        ax.add_patch(mpatches.FancyBboxPatch(
            (x, y), w, h, boxstyle="round,pad=0.15,rounding_size=1.1",
            fc=fc, ec=C_DIM, lw=0.8))
        ax.text(x + w / 2, y + h / 2, label, ha="center", va="center",
                fontsize=fs, color=tc)

    def knob(y, name, vals, unit="", col=C_TEAL):
        ax.text(2, y + 3.1, name, ha="left", va="center", fontsize=10,
                color=col, fontweight="bold")
        x = 15
        for i, v in enumerate(vals):
            if i:
                ax.text(x - 1.4, y + 3.1, "×" if False else "", ha="center")
            chip(x, y, str(int(v)))
            x += 8.4
        ax.text(x + 0.5, y + 3.1, f"({len(vals)})" + (f" {unit}" if unit else ""),
                ha="left", va="center", fontsize=9, color=C_DIM)

    ax.text(2, 96, "One 3-layer profile = five numbers. Here are the choices for each:",
            ha="left", va="center", fontsize=10.5, color=C_CHAR, fontweight="bold")

    # density knobs
    knob(84, r"$\rho_1$  surface", RHO1)
    knob(75, r"$\rho_2$  middle", RHO2)
    knob(66, r"$\rho_3$  deep", RHO3, unit="kg m$^{-3}$")
    # bracket + result
    ax.annotate("", xy=(64, 75), xytext=(58, 75),
                arrowprops=dict(arrowstyle="-|>", color=C_DIM, lw=1.4))
    chip(64, 71.5, r"$3\times2\times3 = 18$ triples", w=30, h=8, fc=C_TEAL_L(), fs=10)
    ax.text(79, 66.5, "all obey $\\rho_1\\!\\leq\\!\\rho_2\\!\\leq\\!\\rho_3$ (denser with depth)",
            ha="center", va="center", fontsize=8, color=C_DIM, style="italic")

    # depth knobs
    knob(50, r"$z_1$  skin$\to$mid", Z1, col=C_FOREST)
    knob(41, r"$z_2$  mid$\to$deep", Z2, unit="cm", col=C_FOREST)
    ax.annotate("", xy=(64, 45.5), xytext=(58, 45.5),
                arrowprops=dict(arrowstyle="-|>", color=C_DIM, lw=1.4))
    chip(64, 42, r"$3\times3 = 9$ boundary pairs", w=30, h=8, fc=C_FOREST_L(), fs=10)

    # combine
    ax.annotate("", xy=(50, 27), xytext=(79, 41.5),
                arrowprops=dict(arrowstyle="-|>", color=C_DIM, lw=1.4,
                                connectionstyle="arc3,rad=0.15"))
    ax.annotate("", xy=(50, 27), xytext=(79, 71),
                arrowprops=dict(arrowstyle="-|>", color=C_DIM, lw=1.4,
                                connectionstyle="arc3,rad=-0.15"))
    ax.add_patch(mpatches.FancyBboxPatch(
        (12, 18), 76, 9, boxstyle="round,pad=0.2,rounding_size=1.4",
        fc="#EAF0F2", ec=C_TEAL, lw=1.4))
    ax.text(50, 22.5, r"$18$ triples $\times\ 9$ pairs $=\ \mathbf{162}$ profiles per site",
            ha="center", va="center", fontsize=13, color=C_CHAR)

    ax.annotate("", xy=(50, 15.5), xytext=(50, 18),
                arrowprops=dict(arrowstyle="-|>", color=C_DIM, lw=1.4))
    ax.add_patch(mpatches.FancyBboxPatch(
        (8, 4), 84, 10, boxstyle="round,pad=0.2,rounding_size=1.4",
        fc=C_GRID, ec=C_DIM, lw=1.0))
    ax.text(50, 9, r"$162 \times 2$ branches (cp, coupled) $\times\ 2$ sites "
            r"$+\ 2$ Hayne baselines $=\ \mathbf{650}$ runs",
            ha="center", va="center", fontsize=12, color=C_CHAR)

    fig.savefig(OUT / "aogs_combinations.pdf")
    plt.close(fig)
    print("wrote", OUT / "aogs_combinations.pdf")


def C_TEAL_L():
    return "#DCE7EB"


def C_FOREST_L():
    return "#DEE9E0"


# ── Diagram 2 : cp vs coupled ───────────────────────────────────────────────
def cp_vs_coupled():
    fig, (axa, axb) = plt.subplots(1, 2, figsize=(JGR_FULL, 3.9),
                                   gridspec_kw={"width_ratios": [1.05, 1]},
                                   constrained_layout=True)

    # ---- panel (a): the fork -------------------------------------------------
    axa.set_xlim(0, 100); axa.set_ylim(0, 100); axa.axis("off")

    def box(ax, x, y, w, h, t, fc, ec, fs=9, bold=False, tc=C_CHAR):
        ax.add_patch(mpatches.FancyBboxPatch(
            (x, y), w, h, boxstyle="round,pad=0.2,rounding_size=1.6",
            fc=fc, ec=ec, lw=1.3))
        ax.text(x + w / 2, y + h / 2, t, ha="center", va="center",
                fontsize=fs, color=tc, fontweight="bold" if bold else "normal")

    axa.text(50, 96, "Density does two jobs — which does each branch use?",
             ha="center", va="center", fontsize=10, color=C_CHAR, fontweight="bold")
    box(axa, 30, 82, 40, 9, "a layer's density  $\\rho$", "#F3EEE9", C_DIM, 10, True)
    # two job boxes
    box(axa, 4, 60, 42, 11, "heat capacity  $\\rho\\,c_p$\n(how much heat it STORES)",
        "#EFEAE4", C_DIM, 8.5)
    box(axa, 54, 60, 42, 11, "conductivity  $K_c$\n(how FAST heat flows)",
        "#EFEAE4", C_DIM, 8.5)
    axa.annotate("", xy=(25, 71), xytext=(44, 82),
                 arrowprops=dict(arrowstyle="-|>", color=C_DIM, lw=1.3))
    axa.annotate("", xy=(75, 71), xytext=(56, 82),
                 arrowprops=dict(arrowstyle="-|>", color=C_DIM, lw=1.3))

    # cp branch (uses only left job)
    box(axa, 4, 34, 42, 10, "cp only", "#E4EEF1", C_TEAL, 10, True, C_TEAL)
    axa.annotate("", xy=(25, 44), xytext=(25, 60),
                 arrowprops=dict(arrowstyle="-|>", color=C_TEAL, lw=2.0))
    axa.annotate("", xy=(58, 44.5), xytext=(70, 60),  # crossed link
                 arrowprops=dict(arrowstyle="-", color=C_DIM, lw=1.0, ls=":"))
    axa.text(78, 52, "K frozen\nat $K_d^{\\star}$", ha="center", va="center",
             fontsize=7.5, color=C_DIM, style="italic")
    box(axa, 4, 18, 42, 10, "weak lever\nfit moves $<0.8$ K", "#F7F5F1", C_TEAL, 8.5,
        False, C_TEAL)
    axa.annotate("", xy=(25, 28), xytext=(25, 34),
                 arrowprops=dict(arrowstyle="-|>", color=C_TEAL, lw=1.6))

    # coupled branch (uses both jobs)
    box(axa, 54, 34, 42, 10, "coupled K", "#F6E7E1", C_A17, 10, True, C_A17)
    axa.annotate("", xy=(75, 44), xytext=(75, 60),
                 arrowprops=dict(arrowstyle="-|>", color=C_A17, lw=2.0))
    axa.annotate("", xy=(58, 44.5), xytext=(40, 60),  # also pulls storage
                 arrowprops=dict(arrowstyle="-|>", color=C_A17, lw=1.4))
    box(axa, 54, 18, 42, 10, "strong lever\nfit moves ${\\sim}4$ K", "#F7F5F1", C_A17,
        8.5, False, C_A17)
    axa.annotate("", xy=(75, 28), xytext=(75, 34),
                 arrowprops=dict(arrowstyle="-|>", color=C_A17, lw=1.6))
    axa.text(50, 6, "cp uses one job; coupled uses both — via the line at right.",
             ha="center", va="center", fontsize=8.5, color=C_CHAR, style="italic")

    # ---- panel (b): the real K_c(rho) line -----------------------------------
    rho = np.linspace(1050, 1960, 200)
    for sk, col in (("A15", C_A15), ("A17", C_A17)):
        kc = KD[sk] - (KD[sk] - KS) * (RD - rho) / (RD - RS)
        axb.plot(rho, kc, color=col, lw=2.4, label=f"coupled: Apollo {sk[1:]}")
        # cp = flat: K does not respond to layer density (stays at K_d*)
        axb.axhline(KD[sk], color=col, lw=1.3, ls=(0, (5, 3)), alpha=0.6)
        # anchors
        axb.plot([RS, RD], [KS, KD[sk]], "o", color="white", mec=col, mew=1.8, ms=7,
                 zorder=5)
    axb.plot(RD, KD["A15"], marker="*", color=C_A15, ms=13, mec=C_CHAR, mew=0.6, zorder=6)
    axb.plot(RD, KD["A17"], marker="*", color=C_A17, ms=13, mec=C_CHAR, mew=0.6, zorder=6)
    axb.text(1930, 1.15, "$\\circ$ = Hayne anchors\n$(\\rho_s,K_s)$ and $(\\rho_d,K_d^{\\star})$",
             fontsize=7.5, color=C_DIM, ha="right", va="bottom")
    axb.text(1300, 5.9, "dashed = cp\n(K ignores $\\rho$)", fontsize=8, color=C_DIM,
             ha="center", va="center", style="italic")
    axb.set_xlim(1050, 1960)
    fmt_axis(axb, xlabel=r"layer density $\rho$ (kg m$^{-3}$)",
             ylabel=r"contact conductivity $K_c$ (mW m$^{-1}$K$^{-1}$)",
             title="The coupling line: $K_c(\\rho)=K_d-(K_d-K_s)\\frac{\\rho_d-\\rho}{\\rho_d-\\rho_s}$")
    axb.legend(loc="upper left", fontsize=8, frameon=True, edgecolor=C_GRID)
    fig.canvas.draw(); assert_no_overlap(axb)

    fig.savefig(OUT / "aogs_cp_vs_coupled.pdf")
    plt.close(fig)
    print("wrote", OUT / "aogs_cp_vs_coupled.pdf")


if __name__ == "__main__":
    combinations()
    cp_vs_coupled()
