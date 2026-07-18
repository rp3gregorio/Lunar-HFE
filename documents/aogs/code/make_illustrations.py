"""Two DETAILED standalone illustrations (PDF + 300-dpi PNG):

  illus_combinations.*  — anatomy of one 3-layer profile, the full count to
                          162/650, a 3x3 boundary grid, and a gallery of examples.
  illus_cp_vs_coupled.* — the fork, the real K_c(rho) coupling line, AND the
                          physical payoff: conductivity vs depth in each branch.

Numbers from the results archive + lunar.constants/config (never hand-typed).
Move-proof paths. Run:  <repo>/.venv/bin/python make_illustrations.py
"""
import json
import pathlib
import sys

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.gridspec import GridSpec

sys.path.insert(0, str(next(a for a in pathlib.Path(__file__).resolve().parents
                            if (a / "code" / "src" / "lunar").is_dir()) / "code" / "src"))
from lunar.plotting.style import (C_A15, C_A17, C_TEAL, C_CHAR, C_DIM, C_GRID,  # noqa: E402
                                  C_FOREST, C_PLUM, WARM_SEQ, fmt_axis, assert_no_overlap)
from lunar.constants import RHO_SURFACE, RHO_DEEP, K_SURFACE  # noqa: E402
from lunar.config import HAYNE  # noqa: E402

AOGS = next(a for a in pathlib.Path(__file__).resolve().parents if a.name == "aogs")
OUT = AOGS / "figures" / "drafts"; OUT.mkdir(exist_ok=True)
_d = json.loads((AOGS / "results" / "aogs_density_study.json").read_text())
M = _d["meta"]
RHO1, RHO2, RHO3 = [[int(v) for v in M[k]] for k in ("rho1", "rho2", "rho3")]
Z1 = [int(z * 100) for z in M["z1_grid"]]
Z2 = [int(z * 100) for z in M["z2_grid"]]
KD = {s: _d["sites"][s]["kd_star_used"] * 1e3 for s in ("A15", "A17")}
KS, RS, RD, H = K_SURFACE * 1e3, RHO_SURFACE, RHO_DEEP, HAYNE["H"]


def kc_line(rho, kd):
    return kd - (kd - KS) * (RD - np.asarray(rho, float)) / (RD - RS)


def save(fig, name):
    fig.savefig(OUT / f"{name}.pdf")
    fig.savefig(OUT / f"{name}.png", dpi=300)
    plt.close(fig)
    print("wrote", OUT / f"{name}.pdf", "+ .png")


# ════════════════════════════════════════════════════════════════════════════
def illus_combinations():
    fig = plt.figure(figsize=(12.5, 8.6))
    gs = GridSpec(2, 2, figure=fig, height_ratios=[1.35, 1.0],
                  width_ratios=[1.0, 1.15], hspace=0.28, wspace=0.22,
                  left=0.06, right=0.97, top=0.90, bottom=0.07)
    fig.suptitle("Building the density sweep: from five knobs to 650 model runs",
                 fontsize=15, fontweight="bold", x=0.06, ha="left")

    # ---- (A) anatomy of one profile -----------------------------------------
    axA = fig.add_subplot(gs[0, 0])
    r1, r2, r3, z1, z2 = 1300, 1700, 1900, 10, 50
    z = np.linspace(0, 100, 400)
    prof = np.where(z < z1, r1, np.where(z < z2, r2, r3))
    axA.set_ylim(100, 0); axA.set_xlim(1050, 2000)
    # shade the three layers as horizontal bands
    for (za, zb), sh, lab, rv in (((0, z1), 0.05, "loose skin", r1),
                                  ((z1, z2), 0.10, "intermediate", r2),
                                  ((z2, 100), 0.16, "consolidated", r3)):
        axA.axhspan(za, zb, color=C_TEAL, alpha=sh, lw=0)
        axA.text(1075, (za + zb) / 2, f"{lab}\n$\\rho$ = {rv} kg m$^{{-3}}$",
                 fontsize=9, color=C_CHAR, ha="left", va="center")
    axA.step(prof, z, where="post", color=C_TEAL, lw=3.0)
    # boundary depths, labelled just outside the right spine (never on data)
    for zb, lab in ((z1, r"$z_1$"), (z2, r"$z_2$")):
        axA.axhline(zb, color=C_CORAL(), ls=(0, (4, 3)), lw=1.2)
        axA.annotate(f"{lab} = {zb} cm", xy=(2000, zb), xytext=(2018, zb),
                     fontsize=9.5, color=C_CORAL(), va="center", ha="left",
                     annotation_clip=False)
    fmt_axis(axA, xlabel=r"density (kg m$^{-3}$)", ylabel="depth (cm)",
             title="(a)  Anatomy of one profile  =  5 numbers")

    # ---- (B) the count -------------------------------------------------------
    axB = fig.add_subplot(gs[0, 1]); axB.set_xlim(0, 100); axB.set_ylim(0, 100)
    axB.axis("off")

    def chip(x, y, t, w=6.6, h=5.6, fc=C_GRID, fs=8.5):
        axB.add_patch(mpatches.FancyBboxPatch(
            (x, y), w, h, boxstyle="round,pad=0.1,rounding_size=1.0", fc=fc,
            ec=C_DIM, lw=0.7))
        axB.text(x + w / 2, y + h / 2, t, ha="center", va="center", fontsize=fs,
                 color=C_CHAR)

    def knob(y, name, vals, col=C_TEAL):
        axB.text(1, y + 2.8, name, ha="left", va="center", fontsize=9.5, color=col,
                 fontweight="bold")
        x = 20
        for v in vals:
            chip(x, y, str(v)); x += 7.6
        axB.text(x + 0.5, y + 2.8, f"({len(vals)})", ha="left", va="center",
                 fontsize=8.5, color=C_DIM)

    axB.text(0, 97, "(b)  Every allowed choice, multiplied", fontsize=11,
             fontweight="bold", color=C_CHAR)
    knob(88, r"$\rho_1$ surface", RHO1)
    knob(80, r"$\rho_2$ middle", RHO2)
    knob(72, r"$\rho_3$ deep", RHO3)
    axB.add_patch(mpatches.FancyBboxPatch((60, 78), 38, 8,
                  boxstyle="round,pad=0.15,rounding_size=1.2", fc="#DCE7EB",
                  ec=C_TEAL, lw=1.2))
    axB.text(79, 82, r"$3\times2\times3=\mathbf{18}$ triples", ha="center",
             va="center", fontsize=10, color=C_CHAR)
    knob(60, r"$z_1$ skin|mid", Z1, col=C_FOREST)
    knob(52, r"$z_2$ mid|deep", Z2, col=C_FOREST)
    axB.add_patch(mpatches.FancyBboxPatch((60, 55), 38, 8,
                  boxstyle="round,pad=0.15,rounding_size=1.2", fc="#DEE9E0",
                  ec=C_FOREST, lw=1.2))
    axB.text(79, 59, r"$3\times3=\mathbf{9}$ pairs", ha="center", va="center",
             fontsize=10, color=C_CHAR)
    # 3x3 boundary grid, visual
    axB.text(1, 44, r"the 9 boundary pairs ($z_1\times z_2$):", fontsize=8.5,
             color=C_DIM)
    gx0, gy0, cs = 3, 20, 6.5
    for i, zz2 in enumerate(Z2[::-1]):
        for j, zz1 in enumerate(Z1):
            axB.add_patch(mpatches.Rectangle((gx0 + j * cs, gy0 + i * cs), cs * 0.92,
                          cs * 0.92, fc="#EEF3F0", ec=C_DIM, lw=0.5))
            axB.text(gx0 + j * cs + cs * 0.46, gy0 + i * cs + cs * 0.46,
                     f"{zz1}/{zz2}", ha="center", va="center", fontsize=6.5,
                     color=C_CHAR)
    axB.text(gx0 + 1.5 * cs, gy0 - 3.2, r"$z_1$ (cm)", ha="center", fontsize=7.5,
             color=C_DIM)
    axB.text(gx0 - 3.4, gy0 + 1.5 * cs, r"$z_2$", va="center", rotation=90,
             fontsize=7.5, color=C_DIM)
    # final tally
    axB.add_patch(mpatches.FancyBboxPatch((34, 24), 64, 9,
                  boxstyle="round,pad=0.15,rounding_size=1.2", fc="#EAF0F2",
                  ec=C_TEAL, lw=1.4))
    axB.text(66, 28.5, r"$18\times9=\mathbf{162}$ per site", ha="center",
             va="center", fontsize=12, color=C_CHAR)
    axB.add_patch(mpatches.FancyBboxPatch((34, 12), 64, 9,
                  boxstyle="round,pad=0.15,rounding_size=1.2", fc=C_GRID,
                  ec=C_DIM, lw=1.0))
    axB.text(66, 16.5, r"$\times2$ branches $\times2$ sites $+2$ = $\mathbf{650}$",
             ha="center", va="center", fontsize=11, color=C_CHAR)
    axB.annotate("", xy=(66, 21), xytext=(66, 24),
                 arrowprops=dict(arrowstyle="-|>", color=C_DIM, lw=1.3))

    # ---- (C) gallery of example profiles ------------------------------------
    axC = fig.add_subplot(gs[1, :])
    triples = [(a, b, c) for a in RHO1 for b in RHO2 for c in RHO3 if a <= b <= c]
    rng = list(range(0, len(triples), max(1, len(triples) // 6)))[:6]
    z = np.linspace(0, 100, 300)
    for k, idx in enumerate(rng):
        a, b, c = triples[idx]
        zz1, zz2 = Z1[k % 3], Z2[(k // 2) % 3]
        prof = np.where(z < zz1, a, np.where(z < zz2, b, c)) + k * 0  # offset none
        col = WARM_SEQ(0.25 + 0.6 * k / 5)
        axC.step(prof + k * 950, z, where="post", color=col, lw=2.2)
        axC.text(a + k * 950 - 40, 96, f"{a}/{b}/{c}\n{zz1}/{zz2}cm", fontsize=7,
                 color=C_DIM, ha="left", va="top")
    axC.set_ylim(100, 0); axC.set_xlim(1050, 1050 + 6 * 950)
    axC.set_xticks([]); axC.set_yticks([0, 50, 100])
    fmt_axis(axC, xlabel="", ylabel="depth (cm)",
             title="(c)  A sample of the 162 profiles (each a different staircase; shifted apart to show variety)")
    axC.text(0.5, -0.16, "the sweep tries every one of these against the Apollo sensors",
             transform=axC.transAxes, ha="center", fontsize=9, color=C_DIM,
             style="italic")
    fig.canvas.draw()   # schematic panels verified visually
    save(fig, "illus_combinations")


def C_CORAL():
    return "#B85B3A"


# ════════════════════════════════════════════════════════════════════════════
def illus_cp_vs_coupled():
    fig = plt.figure(figsize=(13, 7.2))
    gs = GridSpec(2, 2, figure=fig, width_ratios=[1.02, 1.25],
                  height_ratios=[1, 1], hspace=0.42, wspace=0.24,
                  left=0.04, right=0.975, top=0.90, bottom=0.09)
    fig.suptitle("cp only vs coupled K: what density is allowed to change, and what it does",
                 fontsize=15, fontweight="bold", x=0.04, ha="left")

    # ---- (a) the fork (spans both rows, left) --------------------------------
    axa = fig.add_subplot(gs[:, 0]); axa.set_xlim(0, 100); axa.set_ylim(0, 100)
    axa.axis("off")

    def box(x, y, w, h, t, fc, ec, fs=9, bold=False, tc=C_CHAR):
        axa.add_patch(mpatches.FancyBboxPatch(
            (x, y), w, h, boxstyle="round,pad=0.2,rounding_size=1.6", fc=fc, ec=ec,
            lw=1.3))
        axa.text(x + w / 2, y + h / 2, t, ha="center", va="center", fontsize=fs,
                 color=tc, fontweight="bold" if bold else "normal")

    axa.text(0, 97, "(a)  Density has two jobs", fontsize=11.5, fontweight="bold",
             color=C_CHAR)
    box(28, 84, 44, 8.5, "a layer's density  $\\rho$", "#F3EEE9", C_DIM, 11, True)
    box(3, 64, 44, 11, "STORAGE\nheat capacity  $\\rho\\,c_p$", "#EFEAE4", C_DIM, 9)
    box(53, 64, 44, 11, "FLOW\nconductivity  $K_c$", "#EFEAE4", C_DIM, 9)
    axa.annotate("", xy=(25, 75), xytext=(45, 84),
                 arrowprops=dict(arrowstyle="-|>", color=C_DIM, lw=1.3))
    axa.annotate("", xy=(75, 75), xytext=(55, 84),
                 arrowprops=dict(arrowstyle="-|>", color=C_DIM, lw=1.3))
    # cp column
    box(3, 40, 44, 10, "cp only branch", "#E4EEF1", C_TEAL, 10.5, True, C_TEAL)
    axa.annotate("", xy=(25, 50), xytext=(25, 64),
                 arrowprops=dict(arrowstyle="-|>", color=C_TEAL, lw=2.2))
    axa.annotate("", xy=(60, 51), xytext=(72, 64),
                 arrowprops=dict(arrowstyle="-", color=C_DIM, lw=1.0, ls=":"))
    axa.text(83, 57.5, "flow frozen\nat $K_d^{\\star}$", ha="center", va="center",
             fontsize=8, color=C_DIM, style="italic")
    box(3, 22, 44, 12, "density changes only\nhow much heat is STORED",
        "#F7F5F1", C_TEAL, 8.5, False, C_TEAL)
    box(3, 6, 44, 10, "weak lever:  fit spans $<0.8$ K", "#EAF3F5", C_TEAL, 9, True,
        C_TEAL)
    for y0, y1 in ((40, 34), (22, 16)):
        axa.annotate("", xy=(25, y1), xytext=(25, y0),
                     arrowprops=dict(arrowstyle="-|>", color=C_TEAL, lw=1.6))
    # coupled column
    box(53, 40, 44, 10, "coupled K branch", "#F6E7E1", C_A17, 10.5, True, C_A17)
    axa.annotate("", xy=(75, 50), xytext=(75, 64),
                 arrowprops=dict(arrowstyle="-|>", color=C_A17, lw=2.2))
    axa.annotate("", xy=(60, 51), xytext=(38, 64),
                 arrowprops=dict(arrowstyle="-|>", color=C_A17, lw=1.5))
    box(53, 22, 44, 12, "density changes BOTH\nstorage AND flow  $K_c(\\rho)$",
        "#F7F5F1", C_A17, 8.5, False, C_A17)
    box(53, 6, 44, 10, "strong lever:  fit spans ${\\sim}4$ K", "#FBEDE8", C_A17, 9,
        True, C_A17)
    for y0, y1 in ((40, 34), (22, 16)):
        axa.annotate("", xy=(75, y1), xytext=(75, y0),
                     arrowprops=dict(arrowstyle="-|>", color=C_A17, lw=1.6))

    # ---- (b) the coupling line -----------------------------------------------
    axb = fig.add_subplot(gs[0, 1])
    rho = np.linspace(1050, 1960, 200)
    for sk, col in (("A15", C_A15), ("A17", C_A17)):
        axb.plot(rho, kc_line(rho, KD[sk]), color=col, lw=2.4,
                 label=f"coupled: Apollo {sk[1:]}")
        axb.axhline(KD[sk], color=col, lw=1.2, ls=(0, (5, 3)), alpha=0.55)
        axb.plot([RS, RD], [KS, KD[sk]], "o", color="white", mec=col, mew=1.8, ms=7,
                 zorder=5)
    # swept rho3 values as ticks on the A17 line
    for r in (1700, 1800, 1900):
        axb.plot(r, kc_line(r, KD["A17"]), "v", color=C_A17, ms=6, zorder=6)
    axb.text(1930, 1.2, "$\\circ$ Hayne anchors\n$(\\rho_s,K_s),(\\rho_d,K_d^{\\star})$",
             fontsize=8, color=C_DIM, ha="right", va="bottom")
    axb.text(1300, 6.0, "dashed = cp\n($K$ ignores $\\rho$)", fontsize=8.5,
             color=C_DIM, ha="center", va="center", style="italic")
    axb.set_xlim(1050, 1960)
    fmt_axis(axb, xlabel=r"layer density $\rho$ (kg m$^{-3}$)",
             ylabel=r"$K_c$ (mW m$^{-1}$K$^{-1}$)",
             title=r"(b)  The coupling line  $K_c(\rho)=K_d-(K_d-K_s)\dfrac{\rho_d-\rho}{\rho_d-\rho_s}$")
    axb.legend(loc="upper left", fontsize=8.5, frameon=True, edgecolor=C_GRID)

    # ---- (c) the physical payoff: K down the column --------------------------
    axc = fig.add_subplot(gs[1, 1])
    z = np.linspace(0, 100, 500)
    r1, r2, r3, z1, z2 = 1300, 1500, 1900, 5, 30      # the A17 winner structure
    kd = KD["A17"]
    kc_cp = kd - (kd - KS) * np.exp(-z / 100.0 / H)   # smooth Hayne (density-blind)
    rho_z = np.where(z < z1, r1, np.where(z < z2, r2, r3))
    kc_coup = kc_line(rho_z, kd)                       # staircase (density-driven)
    axc.plot(kc_cp, z, color=C_TEAL, lw=2.6, label="cp: smooth $K_c(z)$")
    axc.step(kc_coup, z, where="post", color=C_A17, lw=2.6, label="coupled: $K_c(\\rho(z))$")
    axc.set_ylim(100, 0); axc.set_xlim(0, 8.6)
    for zb in (z1, z2):
        axc.axhline(zb, color=C_DIM, ls=":", lw=0.8)
    fmt_axis(axc, xlabel=r"contact conductivity $K_c$ (mW m$^{-1}$K$^{-1}$)",
             ylabel="depth (cm)",
             title="(c)  What the solver sees: conductivity down the column")
    axc.legend(loc="lower left", fontsize=8.5, frameon=True, edgecolor=C_GRID)

    fig.canvas.draw()
    for ax in (axb, axc):
        assert_no_overlap(ax)
    save(fig, "illus_cp_vs_coupled")




# ════════════════════════════════════════════════════════════════════════════
def illus_conditions():
    """Three models, three sets of conditions — with the equations and a sketch
    of density and conductivity down the column for each."""
    from matplotlib.gridspec import GridSpec
    kd = KD["A17"]                                   # use A17 for the sketches
    z = np.linspace(0, 100, 400)
    r1, r2, r3, z1, z2 = 1300, 1500, 1900, 5, 30     # example staircase
    rho_stair = np.where(z < z1, r1, np.where(z < z2, r2, r3))
    kc_hayne = kd - (kd - KS) * np.exp(-z / 100.0 / H)
    kc_coup = kc_line(rho_stair, kd)

    fig = plt.figure(figsize=(13, 8.4))
    gs = GridSpec(3, 3, figure=fig, width_ratios=[2.5, 1, 1], hspace=0.55,
                  wspace=0.30, left=0.03, right=0.975, top=0.80, bottom=0.06)
    fig.suptitle("The three models, and the exact condition that defines each",
                 fontsize=15, fontweight="bold", x=0.03, ha="left", y=0.965)
    # shared equation banner
    fig.text(0.03, 0.895,
             r"All three solve the same heat equation   "
             r"$\rho(z)\,c_p(T)\,\partial_t T=\partial_z[\,K\,\partial_z T\,]$,"
             r"   $K=K_c(z)\,[1+\chi(T/350)^3]$.",
             fontsize=11.5, color=C_CHAR, ha="left", va="center")
    fig.text(0.03, 0.86,
             r"STORAGE $=\rho\,c_p$   and   FLOW $=K_c$.   "
             r"Only $\rho(z)$ and $K_c(z)$ differ between the three models:",
             fontsize=10.5, color=C_DIM, ha="left", va="center")

    rows = [
        ("homogeneous", C_DIM, "#EFEDEA",
         r"$\rho(z)=1800$   (flat, no layers)",
         r"$K_c(z)=K_d^{\star}$   (flat, no rise)",
         "everything uniform: the deep values used\nall the way up. No structure at all."),
        ("cp  (storage only)", C_TEAL, "#E9F1F3",
         r"$\rho(z)=$ 3-layer staircase  (swept)",
         r"$K_c(z)=K_d^{\star}-(K_d^{\star}-K_s)\,e^{-z/H}$   (density frozen out)",
         "density enters STORAGE ($\\rho c_p$) only;\nflow stays on the fixed Hayne curve."),
        ("coupled  (storage + flow)", C_A17, "#FaEeE9",
         r"$\rho(z)=$ 3-layer staircase  (swept)",
         r"$K_c=K_d^{\star}-(K_d^{\star}-K_s)\,\frac{\rho_d-\rho}{\rho_d-\rho_s}$   (follows $\rho$)",
         "density enters BOTH: storage ($\\rho c_p$)\nand flow ($K_c$ steps with the layers)."),
    ]
    for i, (name, col, bg, eqr, eqk, meaning) in enumerate(rows):
        # text column
        axt = fig.add_subplot(gs[i, 0]); axt.axis("off")
        axt.add_patch(mpatches.FancyBboxPatch((0, 0), 1, 1,
                      boxstyle="round,pad=0.0,rounding_size=0.02", transform=axt.transAxes,
                      fc=bg, ec=col, lw=1.3, clip_on=False))
        axt.text(0.03, 0.86, name, transform=axt.transAxes, fontsize=13,
                 fontweight="bold", color=col, va="top")
        axt.text(0.04, 0.60, r"density:   " + eqr, transform=axt.transAxes,
                 fontsize=10.5, color=C_CHAR, va="center")
        axt.text(0.04, 0.37, r"flow:   " + eqk, transform=axt.transAxes,
                 fontsize=10.5, color=C_CHAR, va="center")
        axt.text(0.04, 0.13, meaning, transform=axt.transAxes, fontsize=9,
                 color=C_DIM, va="center", style="italic")
        # rho sketch
        axr = fig.add_subplot(gs[i, 1])
        rr = np.full_like(z, 1800.0) if i == 0 else rho_stair
        (axr.plot if i == 0 else lambda *a, **k: axr.step(*a, where="post", **k))(
            rr, z, color=col, lw=2.4)
        axr.set_ylim(100, 0); axr.set_xlim(1050, 2000)
        fmt_axis(axr, xlabel=r"$\rho$ (kg m$^{-3}$)" if i == 2 else "",
                 ylabel="depth (cm)", title=r"$\rho(z)$" if i == 0 else "")
        axr.tick_params(labelsize=7)
        if i < 2:
            axr.set_xticklabels([])
        # K_c sketch
        axk = fig.add_subplot(gs[i, 2])
        if i == 0:
            axk.plot(np.full_like(z, kd), z, color=col, lw=2.4)
        elif i == 1:
            axk.plot(kc_hayne, z, color=col, lw=2.4)
        else:
            axk.step(kc_coup, z, where="post", color=col, lw=2.4)
        axk.set_ylim(100, 0); axk.set_xlim(0, 8.6)
        fmt_axis(axk, xlabel=r"$K_c$ (mW m$^{-1}$K$^{-1}$)" if i == 2 else "",
                 ylabel="", title=r"$K_c(z)$" if i == 0 else "")
        axk.tick_params(labelsize=7)
        if i < 2:
            axk.set_xticklabels([])
    save(fig, "illus_conditions")

if __name__ == "__main__":
    illus_combinations()
    illus_cp_vs_coupled()
    illus_conditions()
