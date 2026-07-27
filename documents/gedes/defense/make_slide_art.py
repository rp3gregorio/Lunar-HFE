#!/usr/bin/env python3
"""Purpose-built slide artwork for the GEDES defense (lay audience).

The thesis figures are journal-density. A 12-minute talk to non-specialists
needs bigger type, fewer marks, and one idea per image. Everything here is
drawn for projection: large fonts, high contrast, generous whitespace.

Every NUMBER shown is a certified project value (results/*.json, config.py):
  K_d* 4.60 / 7.08, global 3.4, RMSE 1.09->1.00 and 0.89->0.40 K,
  Q_b 21 / 16 mW m^-2, depths 1.4 / 2.3 m, cut 80 cm, 0.08 K/yr,
  ~2500x speed-up, ~3000 lunations brute force, 4 outer cycles anchored.

Output: img/*.png  and  img/*.gif
Run:    python documents/gedes/defense/make_slide_art.py
"""
from __future__ import annotations
import pathlib
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch, Circle, Rectangle, Wedge
from matplotlib.collections import LineCollection
import matplotlib.animation as anim

OUT = pathlib.Path(__file__).resolve().parent / "img"
OUT.mkdir(parents=True, exist_ok=True)

CHAR, CORAL, TEAL = "#2A2520", "#B85B3A", "#2A6478"
FOREST, DIM, GRID = "#3D6E4A", "#6E6862", "#E8E5E0"
TINT, WHITE, GOLD = "#F7F5F2", "#FFFFFF", "#C9A227"

plt.rcParams.update({
    "font.family": "sans-serif",
    "font.sans-serif": ["Helvetica Neue", "Helvetica", "Arial", "DejaVu Sans"],
    "text.color": CHAR, "axes.labelcolor": CHAR,
    "xtick.color": CHAR, "ytick.color": CHAR,
    "axes.edgecolor": CHAR, "savefig.facecolor": WHITE,
    "figure.facecolor": WHITE,
})
FS_T, FS_L, FS_A = 17, 14, 13


def clean(ax, keep=()):
    for s in ("top", "right", "bottom", "left"):
        ax.spines[s].set_visible(s in keep)
    if "bottom" not in keep:
        ax.set_xticks([])
    if "left" not in keep:
        ax.set_yticks([])


def save(fig, name):
    fig.savefig(OUT / f"{name}.png", dpi=200, bbox_inches="tight",
                facecolor=WHITE, pad_inches=0.15)
    plt.close(fig)
    print("  ", name)


# ----------------------------------------------------------------- 1. WHY
def fig_why():
    """Surface swings wildly; a metre down it is dead steady. That steady
    value is what decides whether ice survives."""
    fig, ax = plt.subplots(figsize=(10.5, 5.0))
    z = np.linspace(0, 200, 400)                    # cm
    delta = 5.0
    for ph, col, lab in [(0.0, CORAL, "lunar noon"), (np.pi, TEAL, "lunar night")]:
        T = 250 + 140 * np.exp(-z / delta) * np.cos(ph)
        ax.plot(T, z, lw=3.5, color=col, label=lab, solid_capstyle="round")
    ax.axhspan(80, 150, color=FOREST, alpha=0.07)
    ax.axhline(80, color=FOREST, lw=1.6, ls=(0, (5, 4)))
    ax.text(103, 116, "THE MEASURED ZONE\nsteady all month, every month",
            fontsize=FS_A, color=FOREST, fontweight="bold", ha="left", va="center")
    ax.text(394, 4, "surface swings\n100 K  to  390 K", fontsize=FS_A,
            color=CORAL, ha="right", va="top", fontweight="bold")
    ax.text(262, 44, "by 80 cm down,\nthe swing is gone", fontsize=12.5,
            color=CHAR, ha="left", va="center")
    ax.set_xlim(90, 400)
    ax.set_ylim(150, -5)
    ax.set_xlabel("temperature  (K)", fontsize=FS_L)
    ax.set_ylabel("depth below surface  (cm)", fontsize=FS_L)
    ax.tick_params(labelsize=12)
    clean(ax, keep=("bottom", "left"))
    ax.grid(axis="x", color=GRID, lw=0.8)
    ax.set_axisbelow(True)
    leg = ax.legend(fontsize=FS_A, frameon=True, edgecolor=GRID, loc="lower right")
    leg.get_frame().set_facecolor(WHITE)
    save(fig, "lay_why")


# ----------------------------------------------------------------- 2. GAP
def fig_gap():
    """Everyone uses ONE number for the whole Moon. It was never checked below
    the surface, and it can only be checked in two places."""
    fig, ax = plt.subplots(figsize=(10.5, 4.6))
    ax.set_xlim(0, 10); ax.set_ylim(0, 4.4); ax.axis("off")

    moon = Circle((2.15, 2.2), 1.65, facecolor=TINT, edgecolor=DIM, lw=1.6, zorder=1)
    ax.add_patch(moon)
    rng = np.random.default_rng(7)
    for _ in range(26):                                     # craters
        a = rng.uniform(0, 2 * np.pi); r = rng.uniform(0, 1.42)
        ax.add_patch(Circle((2.15 + r * np.cos(a), 2.2 + r * np.sin(a)),
                            rng.uniform(0.05, 0.17), facecolor="#EDE9E4",
                            edgecolor="#DBD5CE", lw=0.6, zorder=2))
    ax.text(2.15, 2.2, "$K_d = 3.4$", fontsize=25, fontweight="bold",
            color=CORAL, ha="center", va="center", zorder=4)
    ax.text(2.15, 0.25, "one value, applied to the entire Moon",
            fontsize=FS_A, color=DIM, ha="center", style="italic")

    ax.add_patch(FancyArrowPatch((4.15, 2.2), (5.35, 2.2), arrowstyle="-|>",
                                 mutation_scale=22, lw=2.2, color=CHAR))
    ax.text(4.75, 2.45, "but", fontsize=FS_A, color=DIM, ha="center", style="italic")

    lines = [
        ("Calibrated from orbit", "satellites only feel the top few centimetres"),
        ("Never tested at depth", "no subsurface measurement has ever checked it"),
        ("Only 2 places can test it", "Apollo 15 and 17 — the boreholes in this thesis"),
    ]
    for i, (h, sub) in enumerate(lines):
        y = 3.55 - i * 1.05
        ax.add_patch(Circle((5.75, y), 0.10, color=CORAL, zorder=3))
        ax.text(6.05, y + 0.13, h, fontsize=15, fontweight="bold", color=CHAR, va="center")
        ax.text(6.05, y - 0.20, sub, fontsize=12.5, color=DIM, va="center")
    save(fig, "lay_gap")


# ----------------------------------------------------------- 3. BOREHOLES
def fig_boreholes():
    """Two boreholes, real sensor depths, the excluded shallow zone."""
    a15 = [84, 87, 91, 97, 101, 129, 139]
    a17 = [130, 131, 140, 140, 167, 169, 177, 178, 185, 186, 195, 196,
           223, 224, 233, 234]
    fig, ax = plt.subplots(figsize=(10.5, 5.2))
    ax.set_xlim(0, 10); ax.set_ylim(250, -28); ax.axis("off")

    for x0, depths, col, name, tot in [(2.9, a15, FOREST, "Apollo 15", 140),
                                       (6.6, a17, CORAL, "Apollo 17", 234)]:
        ax.add_patch(Rectangle((x0 - 0.20, 0), 0.40, tot, facecolor=TINT,
                               edgecolor=DIM, lw=1.3, zorder=2))
        ax.add_patch(Rectangle((x0 - 0.20, 0), 0.40, 80, facecolor="#F4D6CB",
                               edgecolor="none", zorder=3))
        seen = {}
        for d in depths:                       # fan out duplicate depths
            k = seen.get(d, 0); seen[d] = k + 1
            ax.plot([x0 + (0.17 if k else -0.17 if depths.count(d) > 1 else 0)],
                    [d], "o", ms=10, color=col, mec=WHITE, mew=1.5, zorder=5)
        ax.text(x0, -20, name, fontsize=16, fontweight="bold", color=col, ha="center")
        ax.text(x0, tot + 14, f"{tot/100:.1f} m deep\n{len(depths)} sensors used",
                fontsize=12.5, color=DIM, ha="center", va="top")

    ax.plot([1.3, 8.3], [0, 0], color=CHAR, lw=2.5, zorder=1)
    ax.text(1.25, -8, "lunar surface", fontsize=12.5, color=CHAR, ha="left", va="bottom")
    ax.plot([3.35, 4.45], [45, 108], color=CORAL, lw=1.1, zorder=3)
    ax.add_patch(Rectangle((4.45, 92), 1.75, 52, facecolor="#FBEFEA",
                           edgecolor=CORAL, lw=1.2, zorder=4))
    ax.text(5.33, 118, "top 80 cm\nexcluded\n(drill damage)",
            fontsize=11.5, color=CORAL, ha="center", va="center",
            fontweight="bold", zorder=6)
    for d in (50, 100, 150, 200):
        ax.text(0.95, d, f"{d} cm", fontsize=11.5, color=DIM, ha="right", va="center")
        ax.plot([1.05, 1.15], [d, d], color=GRID, lw=1.2)
    save(fig, "lay_boreholes")


# --------------------------------------------------------------- 4. WINDOW
def fig_window():
    """Raw record is contaminated early; we automatically take the flat tail."""
    rng = np.random.default_rng(3)
    t = np.linspace(0, 1500, 1400)
    T = 253.6 - 1.5 * np.exp(-t / 260) + 0.00006 * t + rng.normal(0, 0.016, t.size)
    fig, ax = plt.subplots(figsize=(10.5, 4.7))
    ax.plot(t, T, lw=1.4, color=DIM, alpha=0.85)
    m = t > 980
    ax.plot(t[m], T[m], lw=2.6, color=FOREST)
    ax.axvspan(980, 1500, color=FOREST, alpha=0.09)
    ax.axvspan(0, 420, color=CORAL, alpha=0.10)
    ax.text(210, 251.85, "contaminated\ndrill heat, disturbances", fontsize=12.5,
            color=CORAL, ha="center", va="bottom", fontweight="bold")
    ax.text(1240, 251.85, "the stability window\nflat, so we average here",
            fontsize=12.5, color=FOREST, ha="center", va="bottom", fontweight="bold")
    ax.axhline(T[m].mean(), xmin=0.63, color=FOREST, lw=1.6, ls=(0, (4, 3)))
    ax.text(1500, T[m].mean() + 0.06, "one temperature\nper sensor", fontsize=12.5,
            color=FOREST, ha="right", va="bottom")
    ax.set_xlabel("days since the experiment started", fontsize=FS_L)
    ax.set_ylabel("temperature  (K)", fontsize=FS_L)
    ax.tick_params(labelsize=12)
    ax.set_ylim(251.7, 254.1)
    clean(ax, keep=("bottom", "left"))
    ax.grid(color=GRID, lw=0.8); ax.set_axisbelow(True)
    ax.set_title("automatic rule:  keep the longest flat tail  (drift < 0.08 K per year)",
                 fontsize=13.5, color=DIM, loc="left", pad=12)
    save(fig, "lay_window")


# ---------------------------------------------------------------- 5. MODEL
def fig_model():
    """The physics in one picture: sun in, radiation out, heat from below."""
    fig, ax = plt.subplots(figsize=(9.6, 5.2))
    ax.set_xlim(0, 10); ax.set_ylim(0, 5.6); ax.axis("off")
    col = Rectangle((3.3, 0.45), 3.4, 3.5, facecolor=TINT, edgecolor=CHAR, lw=1.8)
    ax.add_patch(col)
    for i, yy in enumerate(np.linspace(0.45, 3.95, 11)[1:-1]):
        ax.plot([3.3, 6.7], [yy, yy], color=GRID, lw=1.0)
    ax.add_patch(Circle((1.55, 4.75), 0.42, color=GOLD, zorder=3))
    for a in np.linspace(0, 2 * np.pi, 12, endpoint=False):
        ax.plot([1.55 + 0.55 * np.cos(a), 1.55 + 0.76 * np.cos(a)],
                [4.75 + 0.55 * np.sin(a), 4.75 + 0.76 * np.sin(a)],
                color=GOLD, lw=2.2, solid_capstyle="round")
    ax.add_patch(FancyArrowPatch((2.25, 4.42), (4.05, 4.05), arrowstyle="-|>",
                                 mutation_scale=20, lw=2.4, color=GOLD))
    ax.text(2.35, 4.62, "sunlight in", fontsize=13.5, color="#9A7B12", fontweight="bold")
    ax.add_patch(FancyArrowPatch((5.9, 4.05), (6.75, 4.95), arrowstyle="-|>",
                                 mutation_scale=20, lw=2.4, color=CORAL))
    ax.text(6.9, 4.9, "heat radiated\nback to space", fontsize=13.5, color=CORAL,
            va="center", fontweight="bold")
    ax.add_patch(FancyArrowPatch((5.0, 0.02), (5.0, 0.85), arrowstyle="-|>",
                                 mutation_scale=20, lw=2.4, color=TEAL))
    ax.text(5.25, 0.18, "heat from the Moon's interior  $Q_b$", fontsize=13.5,
            color=TEAL, va="center", fontweight="bold")
    ax.text(5.0, 4.18, "lunar surface", fontsize=12.5, color=CHAR, ha="center")
    ax.text(1.35, 2.2, "the column\nwe simulate", fontsize=14, color=CHAR,
            ha="center", va="center", fontweight="bold")
    ax.annotate("", xy=(3.2, 2.2), xytext=(2.25, 2.2),
                arrowprops=dict(arrowstyle="-|>", color=CHAR, lw=1.6))
    ax.text(8.15, 2.2, "how easily heat\nmoves through it\n= $K_d$\n\nthis is the\nunknown",
            fontsize=13.5, color=FOREST, ha="center", va="center", fontweight="bold")
    ax.annotate("", xy=(6.8, 2.2), xytext=(7.35, 2.2),
                arrowprops=dict(arrowstyle="-|>", color=FOREST, lw=1.6))
    save(fig, "lay_model")


# --------------------------------------------------------------- 6. SOLVER
def fig_solver():
    """Old way: simulate 3000 month-long cycles. New way: solve the skin, then
    jump straight to the deep answer."""
    fig, axes = plt.subplots(1, 2, figsize=(11.0, 4.5))
    for ax in axes:
        ax.set_xlim(0, 10); ax.set_ylim(0, 6); ax.axis("off")

    ax = axes[0]
    ax.text(5, 5.6, "THE OLD WAY", fontsize=15, fontweight="bold", color=DIM, ha="center")
    for i in range(9):
        x = 0.7 + i * 1.0
        ax.add_patch(FancyBboxPatch((x, 3.55), 0.72, 0.95,
                                    boxstyle="round,pad=0.02,rounding_size=0.08",
                                    facecolor=TINT, edgecolor=DIM, lw=1.2))
    ax.text(5.0, 3.10, "simulate ~3000 month-long cycles\nand wait for it to settle",
            fontsize=13, color=DIM, ha="center", va="top")
    ax.text(5.0, 1.20, "27 hours", fontsize=25, fontweight="bold", color=DIM, ha="center")
    ax.text(5.0, 0.72, "for one experiment", fontsize=13, color=DIM, ha="center")

    ax = axes[1]
    ax.text(5, 5.6, "THE FLUX-ANCHORED SOLVER", fontsize=15, fontweight="bold",
            color=FOREST, ha="center")
    ax.add_patch(FancyBboxPatch((0.9, 4.05), 8.2, 0.82,
                                boxstyle="round,pad=0.02,rounding_size=0.08",
                                facecolor="#E9F0EA", edgecolor=FOREST, lw=1.6))
    ax.text(5.0, 4.46, "1.  solve only the thin sun-baked skin", fontsize=12,
            color=FOREST, ha="center", va="center", fontweight="bold")
    ax.add_patch(FancyArrowPatch((5.0, 4.0), (5.0, 3.55), arrowstyle="-|>",
                                 mutation_scale=18, lw=2.0, color=FOREST))
    ax.add_patch(FancyBboxPatch((0.9, 2.68), 8.2, 0.82,
                                boxstyle="round,pad=0.02,rounding_size=0.08",
                                facecolor="#E9F0EA", edgecolor=FOREST, lw=1.6))
    ax.text(5.0, 3.09, "2.  rebuild the deep part below it", fontsize=12,
            color=FOREST, ha="center", va="center", fontweight="bold")
    ax.text(5.0, 2.28, "the deep column is never simulated",
            fontsize=13, color=FOREST, ha="center", va="top")
    ax.text(5.0, 1.20, "under 1 minute", fontsize=25, fontweight="bold",
            color=FOREST, ha="center")
    ax.text(5.0, 0.72, "about 2500x faster", fontsize=13, color=FOREST,
            ha="center", fontweight="bold")
    save(fig, "lay_solver")


# ----------------------------------------------------------------- 7. BOWL
def fig_bowl():
    """How the answer is found: try many values, keep the best."""
    fig, ax = plt.subplots(figsize=(9.8, 4.8))
    k = np.linspace(1.5, 12, 400)
    for kstar, rm, col, lab in [(4.60, 1.00, FOREST, "Apollo 15"),
                                (7.08, 0.40, CORAL, "Apollo 17")]:
        curve = rm + 0.055 * (k - kstar) ** 2
        ax.plot(k, curve, lw=3.2, color=col, label=lab)
        ax.plot([kstar], [rm], "o", ms=15, color=col, mec=WHITE, mew=2.2, zorder=5)
        ax.annotate(f"{kstar:.2f}", xy=(kstar, rm), xytext=(kstar, rm - 0.42),
                    fontsize=15, fontweight="bold", color=col, ha="center")
    ax.set_xlabel("candidate conductivity  $K_d$", fontsize=FS_L)
    ax.set_ylabel("how badly it misses\nthe measurements", fontsize=FS_L)
    ax.set_ylim(-0.15, 3.2); ax.set_xlim(1.5, 12)
    ax.tick_params(labelsize=12)
    clean(ax, keep=("bottom", "left"))
    ax.grid(color=GRID, lw=0.8); ax.set_axisbelow(True)
    ax.text(9.6, 0.95, "lowest point = best answer", fontsize=13, color=CHAR,
            ha="center", fontweight="bold")
    ax.annotate("", xy=(7.25, 0.5), xytext=(8.55, 0.88),
                arrowprops=dict(arrowstyle="-|>", color=CHAR, lw=1.5))
    leg = ax.legend(fontsize=FS_A, frameon=True, edgecolor=GRID, loc="upper left")
    leg.get_frame().set_facecolor(WHITE)
    save(fig, "lay_bowl")


# -------------------------------------------------------------- 8. RESULTS
def fig_results():
    """The headline, as a bar chart a non-expert reads instantly."""
    fig, ax = plt.subplots(figsize=(10.5, 4.4))
    names = ["The global value\neveryone uses", "Apollo 15\n(this work)", "Apollo 17\n(this work)"]
    vals = [3.4, 4.60, 7.08]
    errs = [[0, 0.42, 0.92], [0, 2.36, 0.99]]
    cols = [DIM, FOREST, CORAL]
    y = np.arange(3)[::-1]
    ax.barh(y, vals, height=0.52, color=cols, zorder=3)
    ax.errorbar(vals[1:], y[1:], xerr=[errs[0][1:], errs[1][1:]], fmt="none",
                ecolor=CHAR, elinewidth=2.0, capsize=7, capthick=2.0, zorder=4)
    for yy, v in zip(y, vals):
        ax.text(v - 0.18, yy, f"{v:.2f}" if v != 3.4 else "3.4", va="center",
                ha="right", fontsize=19, fontweight="bold", color=WHITE, zorder=5)
    ax.set_yticks(y); ax.set_yticklabels(names, fontsize=14)
    ax.set_xlabel("deep conductivity  (mW m$^{-1}$ K$^{-1}$)   —   higher = lets heat through more easily",
                  fontsize=13)
    ax.set_xlim(0, 9.6)
    ax.tick_params(labelsize=12)
    clean(ax, keep=("bottom", "left"))
    ax.grid(axis="x", color=GRID, lw=0.8); ax.set_axisbelow(True)
    ax.axvline(3.4, color=DIM, lw=1.4, ls=(0, (4, 3)), zorder=2)
    ax.text(9.5, y[0] - 0.46, "both sites are MORE conductive than the global value",
            fontsize=13, color=CHAR, ha="right", style="italic")
    save(fig, "lay_results")


# -------------------------------------------------------------- 9. SEESAW
def fig_seesaw():
    """The honest caveat: the thermometers see a ratio, not K_d alone."""
    fig, ax = plt.subplots(figsize=(10.2, 4.6))
    ax.set_xlim(0, 10); ax.set_ylim(0, 5.2); ax.axis("off")
    ax.text(5, 4.85, "What the thermometers actually measure",
            fontsize=16, fontweight="bold", color=CHAR, ha="center")
    ax.text(5, 4.25, "the STEEPNESS of the temperature rise with depth",
            fontsize=13.5, color=DIM, ha="center", style="italic")
    ax.text(5.0, 2.95, r"steepness  =  $\dfrac{Q_b\ \ \mathrm{(heat\ from\ below)}}"
                       r"{K_d\ \ \mathrm{(conductivity)}}$",
            fontsize=21, color=CHAR, ha="center", va="center")
    ax.add_patch(FancyBboxPatch((0.55, 0.35), 4.15, 1.55,
                                boxstyle="round,pad=0.03,rounding_size=0.1",
                                facecolor="#E9F0EA", edgecolor=FOREST, lw=1.6))
    ax.text(2.62, 1.55, "What is solid", fontsize=14, fontweight="bold",
            color=FOREST, ha="center")
    ax.text(2.62, 0.95, "Apollo 17 is the more\nconductive site — this holds\nin ≥99% of the tested cases",
            fontsize=12.5, color=CHAR, ha="center", va="center")
    ax.add_patch(FancyBboxPatch((5.3, 0.35), 4.15, 1.55,
                                boxstyle="round,pad=0.03,rounding_size=0.1",
                                facecolor="#FBEFEA", edgecolor=CORAL, lw=1.6))
    ax.text(7.37, 1.55, "What is not settled", fontsize=14, fontweight="bold",
            color=CORAL, ha="center")
    ax.text(7.37, 0.95, "the exact size of the gap —\nand whether the difference is\nconductivity or heat from below",
            fontsize=12.5, color=CHAR, ha="center", va="center")
    save(fig, "lay_seesaw")


# ------------------------------------------------------------ 10. GLOBAL
def fig_global():
    """Doctoral vision: two dots today, a full map at the end."""
    fig, ax = plt.subplots(figsize=(10.5, 4.4))
    ax.set_xlim(0, 10); ax.set_ylim(0, 4.4); ax.axis("off")
    ax.add_patch(Circle((2.0, 2.1), 1.5, facecolor=TINT, edgecolor=DIM, lw=1.6))
    for (dx, dy), c in [((-0.30, 0.55), FOREST), ((0.42, 0.28), CORAL)]:
        ax.add_patch(Circle((2.0 + dx, 2.1 + dy), 0.13, color=c, zorder=4))
    ax.text(2.0, 0.42, "TODAY\n2 measured points", fontsize=13.5, color=DIM,
            ha="center", va="top", fontweight="bold")

    ax.add_patch(FancyArrowPatch((3.85, 2.1), (5.6, 2.1), arrowstyle="-|>",
                                 mutation_scale=24, lw=2.6, color=CHAR))
    ax.text(4.72, 2.42, "3-year plan", fontsize=13, color=CHAR, ha="center",
            fontweight="bold")

    # plausible mean-temperature field: warm equator, cold poles, mild texture
    R, n = 1.5, 420
    g = np.linspace(-1, 1, n)
    GX, GY = np.meshgrid(g, g)
    rr = np.hypot(GX, GY)
    lat = np.arcsin(np.clip(GY, -1.0, 1.0))
    field = np.cos(lat) ** 0.25
    field += 0.035 * np.sin(5.0 * GX) * np.cos(4.0 * GY)
    field = np.where(rr <= 1.0, field, np.nan)
    ax.imshow(field, extent=[7.45 - R, 7.45 + R, 2.1 - R, 2.1 + R],
              origin="lower", cmap="RdYlBu_r", vmin=0.78, vmax=1.01,
              interpolation="bilinear", zorder=2)
    ax.add_patch(Circle((7.45, 2.1), R, facecolor="none", edgecolor=DIM, lw=1.6, zorder=3))
    ax.text(7.45, 0.42, "GOAL\nMoon-wide subsurface map,\nand where ice can survive",
            fontsize=13.5, color=CHAR, ha="center", va="top", fontweight="bold")
    save(fig, "lay_global")


# ============================================================== ANIMATIONS
def gif_wave():
    """The daily heat wave dies out with depth — why deep sensors are usable."""
    z = np.linspace(0, 100, 260)
    delta = 5.0
    fig, ax = plt.subplots(figsize=(7.6, 4.6))
    fig.subplots_adjust(left=0.16, right=0.97, top=0.86, bottom=0.16)
    line, = ax.plot([], [], lw=3.4, color=CORAL, solid_capstyle="round")
    ax.axhspan(80, 100, color=FOREST, alpha=0.10)
    ax.axhline(80, color=FOREST, lw=1.5, ls=(0, (5, 4)))
    ax.text(376, 90, "sensors here", fontsize=12, color=FOREST,
            ha="right", va="center", fontweight="bold")
    ax.set_xlim(95, 400); ax.set_ylim(100, -3)
    ax.set_xlabel("temperature (K)", fontsize=13)
    ax.set_ylabel("depth (cm)", fontsize=13)
    ax.tick_params(labelsize=11)
    clean(ax, keep=("bottom", "left"))
    ax.grid(axis="x", color=GRID, lw=0.8); ax.set_axisbelow(True)
    ttl = ax.set_title("", fontsize=14, color=CHAR, loc="left", pad=10)
    N = 48

    def upd(i):
        ph = 2 * np.pi * i / N
        T = 250 + 140 * np.exp(-z / delta) * np.cos(ph)
        line.set_data(T, z)
        frac = (i / N) % 1.0
        when = ("lunar noon" if frac < 0.12 or frac > 0.88 else
                "afternoon" if frac < 0.37 else
                "lunar night" if frac < 0.62 else "before dawn")
        ttl.set_text(f"one month on the Moon — {when}")
        line.set_color(CORAL if np.cos(ph) > 0 else TEAL)
        return line, ttl

    a = anim.FuncAnimation(fig, upd, frames=N, blit=False)
    a.save(OUT / "anim_wave.gif", writer=anim.PillowWriter(fps=12), dpi=100)
    plt.close(fig)
    print("   anim_wave.gif")


def gif_hook():
    """THE HOOK. Not a graph - a picture of the ground.

    Cross-section of lunar soil colour-coded by temperature, the sun tracking
    overhead across one lunar month, and two thermometers: one at the surface
    swinging violently, one a metre down that never moves.

    Depth uses a square-root scale so the top few centimetres - where all the
    action is - are actually visible; the tick labels carry the true depths.
    Standard damped thermal wave T(z,t)=T0+A e^{-z/d} sin(wt - z/d);
    illustrative, not a site-specific solve."""
    T0, A, d = 250.0, 140.0, 5.0                 # K, K, cm skin depth
    ZMAX = 130.0
    u = np.linspace(0.0, np.sqrt(ZMAX), 260)     # uniform in sqrt(depth)
    zz = u ** 2
    UMAX, SKY = float(u[-1]), -4.6

    fig = plt.figure(figsize=(8.6, 4.7))
    sc = fig.add_axes([0.075, 0.06, 0.60, 0.88])
    rd = fig.add_axes([0.71, 0.06, 0.275, 0.88]); rd.axis("off")
    sc.set_xlim(0, 10); sc.set_ylim(UMAX, SKY); sc.axis("off")

    sc.add_patch(Rectangle((0, SKY), 10, -SKY, facecolor="#0B0A10", zorder=1))
    rng = np.random.default_rng(5)
    stars = [sc.plot(rng.uniform(0.2, 9.8), rng.uniform(SKY + 0.35, -0.55),
                     marker="*", ms=rng.uniform(1.6, 3.6), color="#8D8D9E",
                     zorder=2)[0] for _ in range(34)]
    sun, = sc.plot([], [], marker="o", ms=17, color="#FFC93C",
                   mec="#FFE9A8", mew=2.0, zorder=5, linestyle="none")

    im = sc.imshow(np.tile(np.full_like(u, T0)[:, None], (1, 2)),
                   extent=[0, 10, UMAX, 0], origin="upper", aspect="auto",
                   cmap="RdYlBu_r", vmin=100, vmax=395,
                   interpolation="bilinear", zorder=3)
    sc.plot([0, 10], [0, 0], color=WHITE, lw=2.4, zorder=6)
    sc.axhline(np.sqrt(100.0), color=CHAR, lw=1.5, ls=(0, (5, 4)), zorder=6)
    sc.text(9.8, np.sqrt(100.0) + 0.30, "1 metre down", fontsize=11.5,
            color=CHAR, ha="right", va="top", fontweight="bold", zorder=7)
    for dd in (5, 20, 50, 130):
        sc.text(0.16, np.sqrt(dd) + 0.16, f"{dd} cm", fontsize=9.5, color=CHAR,
                alpha=0.75, ha="left", va="top", zorder=7)

    day = rd.text(0.0, 0.99, "", fontsize=12.5, color=DIM, va="top",
                  fontweight="bold", transform=rd.transAxes)
    rd.text(0.0, 0.855, "AT THE SURFACE", fontsize=11.5, color=CORAL,
            va="top", fontweight="bold", transform=rd.transAxes)
    v_top = rd.text(0.0, 0.785, "", fontsize=30, color=CHAR, va="top",
                    fontweight="bold", transform=rd.transAxes)
    rd.text(0.0, 0.585, "swings 110 to 390 K\nevery month", fontsize=11,
            color=DIM, va="top", transform=rd.transAxes)
    rd.text(0.0, 0.40, "ONE METRE DOWN", fontsize=11.5, color=TEAL,
            va="top", fontweight="bold", transform=rd.transAxes)
    v_bot = rd.text(0.0, 0.33, "", fontsize=30, color=CHAR, va="top",
                    fontweight="bold", transform=rd.transAxes)
    rd.text(0.0, 0.135, "does not move at all", fontsize=11,
            color=DIM, va="top", transform=rd.transAxes)

    N = 54

    def upd(i):
        f = i / N                                  # 0 sunrise, .25 noon, .5 sunset
        ph = 2 * np.pi * f
        T = T0 + A * np.exp(-zz / d) * np.sin(ph - zz / d)
        im.set_data(np.tile(T[:, None], (1, 2)))
        elev = np.sin(ph)
        if elev > 0.02:
            sun.set_data([0.6 + 8.8 * (f / 0.5)], [-0.7 - 3.3 * elev])
            for st in stars: st.set_alpha(max(0.0, 0.85 - 3.2 * elev))
        else:
            sun.set_data([], [])
            for st in stars: st.set_alpha(0.85)
        lbl = ("sunrise" if f < 0.05 else "morning" if f < 0.19 else
               "noon" if f < 0.32 else "afternoon" if f < 0.45 else
               "sunset" if f < 0.55 else "night")
        day.set_text(f"day {int(f * 29.5) + 1} of 29   ·   {lbl}")
        v_top.set_text(f"{T[0]:.0f} K")
        v_bot.set_text(f"{T0 + A * np.exp(-100 / d) * np.sin(ph - 100 / d):.1f} K")
        return im, sun, day, v_top, v_bot

    a = anim.FuncAnimation(fig, upd, frames=N, blit=False)
    a.save(OUT / "anim_hook.gif", writer=anim.PillowWriter(fps=13), dpi=105)
    plt.close(fig)
    print("   anim_hook.gif")


def gif_race():
    """Old method crawls toward the answer; the new one arrives immediately."""
    fig, ax = plt.subplots(figsize=(7.8, 4.4))
    fig.subplots_adjust(left=0.14, right=0.96, top=0.85, bottom=0.18)
    target = 253.0
    n = np.arange(1, 3001)
    brute = target - 22.0 * np.exp(-n / 620.0)
    ax.axhline(target, color=CHAR, lw=1.6, ls=(0, (5, 4)))
    ax.text(3050, target + 0.7, "true answer", fontsize=12, color=CHAR, ha="right")
    lb, = ax.plot([], [], lw=3.0, color=DIM, label="old way: simulate every cycle")
    la, = ax.plot([], [], lw=0, marker="o", ms=13, color=FOREST, mec=WHITE, mew=2,
                  label="flux-anchored solver")
    ax.set_xlim(0, 3100); ax.set_ylim(228, 258)
    ax.set_xlabel("month-long cycles simulated", fontsize=13)
    ax.set_ylabel("deep temperature (K)", fontsize=13)
    ax.tick_params(labelsize=11)
    clean(ax, keep=("bottom", "left"))
    ax.grid(color=GRID, lw=0.8); ax.set_axisbelow(True)
    leg = ax.legend(fontsize=11.5, frameon=True, edgecolor=GRID, loc="lower right")
    leg.get_frame().set_facecolor(WHITE)
    ttl = ax.set_title("", fontsize=14, color=CHAR, loc="left", pad=10)
    N = 44

    def upd(i):
        k = int((i / (N - 1)) ** 1.7 * 2999) + 1
        lb.set_data(n[:k], brute[:k])
        if i >= 3:
            la.set_data([4], [target])
        ttl.set_text(f"cycles simulated: {k:,}    —    anchored solver: 4")
        return lb, la, ttl

    a = anim.FuncAnimation(fig, upd, frames=N, blit=False)
    a.save(OUT / "anim_race.gif", writer=anim.PillowWriter(fps=10), dpi=100)
    plt.close(fig)
    print("   anim_race.gif")


if __name__ == "__main__":
    print("static art:")
    fig_why(); fig_gap(); fig_boreholes(); fig_window(); fig_model()
    fig_solver(); fig_bowl(); fig_results(); fig_seesaw(); fig_global()
    print("animations:")
    gif_hook(); gif_wave(); gif_race()
    print("done ->", OUT)
