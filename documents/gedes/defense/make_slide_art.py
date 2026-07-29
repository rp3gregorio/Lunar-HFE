#!/usr/bin/env python3
"""Purpose-built slide artwork for the GEDES defense (lay audience).

Built to the briefs in SLIDE_PROMPTS.md. Read that file before changing
anything here; it is the contract and this is only the implementation.

THE CANVAS CONTRACT (SLIDE_PROMPTS.md sec 0.3)
    Every hero image is drawn on a FIXED 12.00 x 4.98 in canvas (2.41:1) at
    dpi 200 and saved with bbox_inches=None. The old `tight` save let each
    figure choose its own aspect, which is why the deck used to float its
    pictures in a white gutter. Compose inside the canvas; never let the
    saver crop.

    Coordinates inside `hero()` are INCHES: xlim 0..12, ylim 0..4.98. A font
    size in points on this canvas is very nearly a font size in points on the
    slide, because the art box is 11.90 in wide. Type floor: 12 pt.

Every NUMBER shown is a certified project value; the register is
SLIDE_PROMPTS.md sec 0.7. Sources: code/results/*.json,
documents/aogs/results/*.json, code/src/lunar/config.py.

Output: img/*.png and img/*.gif
Run:    python documents/gedes/defense/make_slide_art.py
"""
from __future__ import annotations
import json
import pathlib
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import (FancyBboxPatch, FancyArrowPatch, Circle,
                                Rectangle, Polygon)
import matplotlib.animation as anim

HERE = pathlib.Path(__file__).resolve().parent
OUT = HERE / "img"
OUT.mkdir(parents=True, exist_ok=True)
REPO = HERE.parents[2]
RESULTS = REPO / "code" / "results"
AOGS = REPO / "documents" / "aogs" / "results"

CHAR, CORAL, TEAL = "#2A2520", "#B85B3A", "#2A6478"
FOREST, DIM, GRID = "#3D6E4A", "#6E6862", "#E8E5E0"
TINT, WHITE, GOLD = "#F7F5F2", "#FFFFFF", "#C9A227"
CORAL_L, FOREST_L, TEAL_L = "#FBEFEA", "#E9F0EA", "#E6EEF1"

plt.rcParams.update({
    "font.family": "sans-serif",
    "font.sans-serif": ["Helvetica Neue", "Helvetica", "Arial", "DejaVu Sans"],
    "text.color": CHAR, "axes.labelcolor": CHAR,
    "xtick.color": CHAR, "ytick.color": CHAR,
    "axes.edgecolor": CHAR, "savefig.facecolor": WHITE,
    "figure.facecolor": WHITE,
    # STIX sans has full Greek and math coverage and sits beside Helvetica
    # without looking like a different document. matplotlib's default math
    # font is a serif that clashes with every label in this deck.
    "mathtext.fontset": "stixsans",
})

W, H = 12.00, 4.98                 # the canvas contract, in inches
DPI = 200
FS_HEAD, FS_LAB, FS_ANN = 17.0, 14.5, 13.0     # in-art type scale
FS_BIG = 34.0                                   # hero numerals


# --------------------------------------------------------------- scaffolding
def hero():
    """A fixed-canvas figure plus a full-bleed axes measured in inches."""
    fig = plt.figure(figsize=(W, H), dpi=DPI)
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, W)
    ax.set_ylim(0, H)
    ax.axis("off")
    return fig, ax


def data_axes(fig, left, bottom, width, height):
    """A plotting axes placed in figure fractions inside the same canvas."""
    ax = fig.add_axes([left, bottom, width, height])
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    ax.grid(color=GRID, lw=0.8)
    ax.set_axisbelow(True)
    ax.tick_params(labelsize=12.5)
    return ax


def save(fig, name):
    """Fixed canvas, no tight-cropping. See the canvas contract above."""
    fig.savefig(OUT / f"{name}.png", dpi=DPI, facecolor=WHITE)
    plt.close(fig)
    px = int(W * DPI), int(H * DPI)
    print(f"   {name:22s} {px[0]}x{px[1]}")


def card(ax, x, y, w, h, face=TINT, edge=GRID, lw=1.2, rail=None):
    """A rounded card, optionally with a coloured rail down its left edge."""
    ax.add_patch(FancyBboxPatch((x, y), w, h,
                                boxstyle="round,pad=0,rounding_size=0.08",
                                facecolor=face, edgecolor=edge, lw=lw, zorder=2))
    if rail:
        ax.add_patch(Rectangle((x, y + 0.06), 0.065, h - 0.12,
                               facecolor=rail, edgecolor="none", zorder=3))


def chevron(ax, x, y, size=0.34, color=GRID):
    """One forward chevron: the only connector allowed in fig_pipeline."""
    ax.add_patch(Polygon([[x, y + size], [x + size * 0.85, y],
                          [x, y - size], [x + size * 0.30, y - size],
                          [x + size * 1.15, y], [x + size * 0.30, y + size]],
                         closed=True, facecolor=color, edgecolor="none", zorder=2))


# ------------------------------------------------- published-figure exports
# Slides 5, 8, 12 and the slide-4 inset show REAL published figures rather than
# lay redraws, at the user's request. They are rendered here so the deck build
# stays a single reproducible command.
GUIDEBOOK_TIKZ = REPO / "documents" / "jgr" / "guidebook" / "figures-tikz"
FIGURES = REPO / "figures"

# Guidebook TikZ flowcharts used in the deck. The guidebook has 34; these are
# the ones that answer a question a panel actually asks. Presented slides take
# the first two; the rest are the method-in-depth backup block.
GB_FLOWCHARTS = [
    "pipeline",           # Fig 2.1 — the roadmap (slide 5)
    "dataenters_slide",   # the model runs blind (slide 8)
    "costnesting",        # the three nested loops (slide 9)
    "windowflow",         # one sensor -> one temperature
    "pde2odeflow",        # five moves: heat PDE -> closure ODE
    "anchormethod_slide",  # brute force vs anchor, side by side
    "deepprofile_slide",  # why the deep column is almost free
    "stepsAB_flow",       # Step A / Step B in full
    "anchorflow",         # the outer loop and its convergence test
    "certflow",           # the three certification checks
    "marchflow",          # one Crank-Nicolson time step
    "gridcells",          # the geometric grid
    "bootflow",           # one bootstrap draw, in full
    "mcmcflow",           # the Bayesian cross-check
    "crosschecks",        # three disjoint slices of physics, one answer
    "threebugs",          # the three bugs found, and what each cost
    "inputflow",          # how a number earns its way into the model
    "makeflow",           # reproducing the whole chain
]

PDF_EXPORTS = [
    # (source pdf, output name, dpi, clip rect in points or None)
    # thesis Fig 5.5, cropped to the two meter-scale panels + legend: those are
    # the panels that carry the claim, and the crop lands near aspect 2.3
    (FIGURES / "fig_thermal_profiles.pdf", "th_profiles", 300, (0, 158, 525.9, 410.1)),
    # thesis Fig 1.2(a): the Clementine albedo globe with both sites marked
    (FIGURES / "fig_context_globes.pdf", "moon_globe", 460, (14, 26, 147, 168)),
    (FIGURES / "fig_holdout.pdf", "holdout", 300, None),
    (FIGURES / "fig_posterior_compare.pdf", "posterior", 300, None),
] + [(GUIDEBOOK_TIKZ / f"{n}_standalone.pdf", f"gb_{n}", 300, None)
     for n in GB_FLOWCHARTS]


def export_pdfs():
    import fitz
    for src, name, dpi, clip in PDF_EXPORTS:
        if not src.exists():
            print(f"   !! missing {src}")
            continue
        page = fitz.open(src)[0]
        rect = fitz.Rect(*clip) if clip else None
        page.get_pixmap(dpi=dpi, clip=rect).save(OUT / f"{name}.png")
        from PIL import Image
        im = Image.open(OUT / f"{name}.png")
        print(f"   {name:22s} {im.width}x{im.height}  <- {src.name}")


def load_bootstrap():
    d = json.loads((RESULTS / "kd_retrieval_results.json").read_text())
    out = {}
    for s in ("A15", "A17"):
        b = d[s]["bootstrap"]
        out[s] = dict(samples=np.asarray(b["samples"]) * 1e3,
                      lo=b["ci_lo"] * 1e3, hi=b["ci_hi"] * 1e3,
                      star=d[s]["kd_star"] * 1e3)
    return out


# ================================================================= SLIDE 3
def fig_gap():
    """One number, fitted from orbit, never tested underground.

    The two big numerals 3.4 and 0 are the whole slide; the third beat
    (2 places) is the handoff into slide 4."""
    fig, ax = hero()

    # --- the Moon, carrying the single global value ---------------------
    cx, cy, r = 2.05, 2.72, 1.52
    ax.add_patch(Circle((cx, cy), r, facecolor=TINT, edgecolor=DIM, lw=1.6, zorder=1))
    rng = np.random.default_rng(7)
    for _ in range(30):
        a, rr = rng.uniform(0, 2 * np.pi), rng.uniform(0, r * 0.87)
        ax.add_patch(Circle((cx + rr * np.cos(a), cy + rr * np.sin(a)),
                            rng.uniform(0.05, 0.17), facecolor="#EDE9E4",
                            edgecolor="#DBD5CE", lw=0.6, zorder=2))
    ax.text(cx, cy, "$K_d = 3.4$", fontsize=42, fontweight="bold", color=CORAL,
            ha="center", va="center", zorder=4)
    ax.text(cx, 0.78, "one value, applied to all\n38 million square kilometres",
            fontsize=FS_ANN, color=DIM, ha="center", va="top", style="italic")

    ax.add_patch(FancyArrowPatch((3.78, cy), (4.60, cy), arrowstyle="-|>",
                                 mutation_scale=22, lw=2.2, color=CHAR))
    ax.text(4.19, cy + 0.26, "but", fontsize=FS_ANN, color=DIM,
            ha="center", style="italic")

    # --- three beats, two of which carry a hero numeral ------------------
    beats = [
        ("Calibrated from orbit",
         "satellites only feel the top few centimetres", None),
        ("Never tested at depth",
         "subsurface measurements that have checked it", "0"),
        ("Only two places can test it",
         "Apollo 15 and 17 — the boreholes in this thesis", "2"),
    ]
    for i, (head, sub, num) in enumerate(beats):
        y = 4.10 - i * 1.32
        ax.add_patch(Circle((5.15, y), 0.10, color=CORAL, zorder=3))
        ax.text(5.45, y + 0.16, head, fontsize=FS_HEAD, fontweight="bold",
                color=CHAR, va="center")
        ax.text(5.45, y - 0.22, sub, fontsize=FS_ANN, color=DIM, va="center")
        if num:
            ax.text(11.85, y - 0.02, num, fontsize=FS_BIG, fontweight="bold",
                    color=CORAL, ha="right", va="center")
    save(fig, "lay_gap")


# ================================================================= SLIDE 4
def fig_boreholes():
    """Two boreholes to scale, the excluded top 80 cm, and the scarcity."""
    a15 = [84, 87, 91, 97, 101, 129, 139]
    a17 = [130, 131, 140, 140, 167, 169, 177, 178, 185, 186, 195, 196,
           223, 224, 233, 234]
    fig, ax = hero()

    TOP, SCALE = 4.24, 0.0145                     # y of surface; inches per cm
    ycm = lambda d: TOP - d * SCALE               # noqa: E731

    # --- depth ruler -----------------------------------------------------
    ax.plot([1.30, 1.30], [ycm(0), ycm(240)], color=GRID, lw=1.4)
    for d in (0, 50, 100, 150, 200):
        ax.plot([1.30, 1.44], [ycm(d), ycm(d)], color=DIM, lw=1.2)
        ax.text(1.22, ycm(d), f"{d}", fontsize=12.5, color=DIM,
                ha="right", va="center")
    ax.text(0.52, ycm(120), "depth below the surface  (cm)", fontsize=FS_ANN,
            color=DIM, ha="center", va="center", rotation=90)

    # --- the two stems ---------------------------------------------------
    ax.plot([1.75, 6.55], [TOP, TOP], color=CHAR, lw=2.4, zorder=4)
    ax.text(1.75, TOP + 0.13, "lunar surface", fontsize=12.5, color=CHAR)
    for x0, depths, col, name, tot in [(2.60, a15, FOREST, "Apollo 15", 140),
                                       (5.30, a17, CORAL, "Apollo 17", 234)]:
        ax.add_patch(Rectangle((x0 - 0.17, ycm(tot + 7)), 0.34, (tot + 7) * SCALE,
                               facecolor=TINT, edgecolor=DIM, lw=1.3, zorder=2))
        ax.add_patch(Rectangle((x0 - 0.17, ycm(80)), 0.34, 80 * SCALE,
                               facecolor="#F4D6CB", edgecolor="none", zorder=3))
        ax.plot([x0 - 0.17, x0 + 0.17], [ycm(80), ycm(80)], color=CORAL,
                lw=1.5, ls=(0, (4, 3)), zorder=5)
        # zig-zag every sensor, not just exact duplicates: several depths sit
        # within a couple of centimetres and would otherwise merge into a blob,
        # making the count uncountable
        for j, d in enumerate(sorted(depths)):
            off = (-0.13, 0.13)[j % 2]
            ax.plot([x0 + off], [ycm(d)], "o", ms=10, color=col,
                    mec=WHITE, mew=1.5, zorder=6)
        ax.text(x0, TOP + 0.46, name, fontsize=FS_HEAD, fontweight="bold",
                color=col, ha="center")
        ax.text(x0, ycm(tot) - 0.16, f"{tot/100:.1f} m deep\n{len(depths)} sensors used",
                fontsize=12.5, color=DIM, ha="center", va="top")

    # the exclusion label sits in the clear channel between the two stems,
    # level with the zone it names, so it needs no leader line
    ax.text(3.95, ycm(30), "top 80 cm\nexcluded", fontsize=12.5, color=CORAL,
            fontweight="bold", ha="center", va="center", zorder=7,
            linespacing=1.35)
    ax.text(3.95, ycm(72), "disturbed by\nthe drilling", fontsize=11.5,
            color=DIM, ha="center", va="center", zorder=7, linespacing=1.35)

    # --- scarcity facts + a locator disc ---------------------------------
    ax.plot([7.25, 7.25], [0.35, 4.55], color=GRID, lw=1.2)

    # the real Moon from the manuscript (thesis Fig 1.2a, Clementine albedo)
    # rather than a drawn disc: it is recognisably the Moon and it is the same
    # figure the examiners have already seen in the thesis
    globe = OUT / "moon_globe.png"
    gcx, gcy, gr = 8.55, 2.95, 1.30
    if globe.exists():
        ax.imshow(plt.imread(globe),
                  extent=[gcx - gr, gcx + gr, gcy - gr, gcy + gr], zorder=3)
    # a key BELOW the globe, not labels on it: the globe is mid-grey, so no
    # text colour reads against it
    for i, (c, nm) in enumerate([(FOREST, "Apollo 15"), (CORAL, "Apollo 17")]):
        x = gcx - 0.95 + i * 1.30
        ax.add_patch(Circle((x, gcy - gr - 0.26), 0.09, color=c, zorder=4))
        ax.text(x + 0.18, gcy - gr - 0.26, nm, fontsize=12, color=CHAR,
                va="center", zorder=4)
    ax.text(gcx, gcy + gr + 0.16, "the only two sites ever drilled",
            fontsize=12.5, color=DIM, ha="center", va="bottom")

    facts = [("6 years", "of record, 1971–1977"),
             ("23 sensors", "below the 80 cm cut"),
             ("2 sites", "no more are coming")]
    for i, (big, sub) in enumerate(facts):
        y = 3.35 - i * 1.10
        ax.text(10.35, y, big, fontsize=22, fontweight="bold", color=CHAR, va="center")
        ax.text(10.35, y - 0.34, sub, fontsize=11.5, color=DIM, va="center")
    save(fig, "lay_boreholes")


# ============================================= SLIDE 5  (guidebook Fig 2.1)
def fig_pipeline():
    """The roadmap: guidebook Fig 2.1 translated for a projector.

    Three inputs, three steps, three results. No equations, no Greek, and
    exactly two connectors. The one free knob is tagged in place rather than
    pointed at with an arrow (SLIDE_PROMPTS.md sec 0.1)."""
    fig, ax = hero()

    cols = [(0.18, 3.50, "WHAT WE HAVE", TEAL),
            (4.28, 3.30, "WHAT WE DO", CHAR),
            (8.32, 3.50, "WHAT WE GET", CHAR)]
    for x, w, head, col in cols:
        ax.text(x, 4.70, head, fontsize=13.5, fontweight="bold", color=col,
                va="center", family="sans-serif")
    ax.plot([0.18, 11.82], [4.50, 4.50], color=GRID, lw=1.0)

    ys = [2.98, 1.66, 0.34]                       # three rows, top to bottom
    CH = 1.18

    # --- column 1: the inputs -------------------------------------------
    inputs = [
        ("23 thermometers", "Apollo 15 and 17, buried 0.8 to 2.3 m, 1971–77", False),
        # one line only: this card carries a third, coral line as well, and
        # four text lines do not fit in a 1.18 in card
        ("A formula for heat flow", "how conductivity varies with depth and temperature", True),
        ("Heat from the interior", "21 and 16 mW m$^{-2}$, measured by Apollo", False),
    ]
    for (head, sub, knob), y in zip(inputs, ys):
        card(ax, 0.18, y, 3.50, CH, face=WHITE,
             edge=CORAL if knob else GRID, lw=1.6 if knob else 1.2,
             rail=CORAL if knob else TEAL)
        ax.text(0.42, y + CH - 0.32, head, fontsize=15, fontweight="bold",
                color=CHAR, va="center", zorder=4)
        if knob:
            # carried by the card's own text, not by a floating tag: a tag
            # anywhere in this card collides with either the headline or the
            # sub-line, and the dependency only needs stating once
            ax.text(0.42, y + 0.58, sub, fontsize=11.0, color=DIM, va="center",
                    zorder=4)
            ax.text(0.42, y + 0.24, "the only unknown in the whole study",
                    fontsize=12.0, fontweight="bold", color=CORAL, va="center",
                    zorder=5)
        else:
            ax.text(0.42, y + 0.46, sub, fontsize=12.0, color=DIM, va="top",
                    zorder=4, linespacing=1.35)

    chevron(ax, 3.80, 1.66 + CH / 2, size=0.40, color="#D8D3CD")

    # --- column 2: what we do -------------------------------------------
    steps = [("Pick the steady stretch",
              "six years of drift become\none temperature per sensor"),
             ("Simulate the ground",
              "until it repeats the same\nmonth forever"),
             ("Try every candidate value",
              "keep the one that fits the\nthermometers best")]
    for i, ((head, sub), y) in enumerate(zip(steps, ys)):
        card(ax, 4.28, y, 3.30, CH, face=TINT, edge=GRID)
        ax.add_patch(Circle((4.60, y + CH - 0.32), 0.19, color=CHAR, zorder=4))
        ax.text(4.60, y + CH - 0.32, str(i + 1), fontsize=12.5, fontweight="bold",
                color=WHITE, ha="center", va="center", zorder=5)
        ax.text(4.90, y + CH - 0.32, head, fontsize=14, fontweight="bold",
                color=CHAR, va="center", zorder=4)
        ax.text(4.52, y + 0.50, sub, fontsize=11.5, color=DIM, va="top",
                zorder=4, linespacing=1.35)

    chevron(ax, 7.84, 1.66 + CH / 2, size=0.40, color="#D8D3CD")

    # --- column 3: the results ------------------------------------------
    res = [("Apollo 15", "4.60", FOREST, FOREST_L),
           ("Apollo 17", "7.08", CORAL, CORAL_L),
           ("The global value", "3.4", DIM, TINT)]
    for (lab, val, col, face), y in zip(res, ys):
        card(ax, 8.32, y, 3.50, CH, face=face, edge=col, lw=1.5)
        ax.text(8.58, y + CH / 2 + 0.20, lab, fontsize=13, fontweight="bold",
                color=col, va="center", zorder=4)
        ax.text(8.58, y + CH / 2 - 0.28, "mW m$^{-1}$ K$^{-1}$",
                fontsize=11.5, color=DIM, va="center", zorder=4)
        ax.text(11.58, y + CH / 2, val, fontsize=32, fontweight="bold",
                color=col, ha="right", va="center", zorder=4)
    save(fig, "lay_pipeline")


# ================================================================= SLIDE 6
def fig_window():
    """The automatic stability rule, on a real-looking record, plus the rule
    itself stated in three plain lines."""
    fig, ax = hero()
    dx = data_axes(fig, 0.085, 0.145, 0.515, 0.735)

    rng = np.random.default_rng(3)
    t = np.linspace(0, 1500, 1400)
    T = 253.6 - 1.5 * np.exp(-t / 260) + 0.00006 * t + rng.normal(0, 0.016, t.size)
    dx.plot(t, T, lw=1.4, color=DIM, alpha=0.85)
    m = t > 980
    dx.plot(t[m], T[m], lw=2.8, color=FOREST)
    dx.axvspan(0, 420, color=CORAL, alpha=0.10)
    dx.axvspan(980, 1500, color=FOREST, alpha=0.09)
    dx.axhline(T[m].mean(), xmin=0.60, color=FOREST, lw=1.7, ls=(0, (4, 3)))
    dx.text(210, 251.86, "contaminated\ndrilling heat, disturbances",
            fontsize=12.5, color=CORAL, ha="center", va="bottom", fontweight="bold")
    dx.text(1240, 251.86, "the stability window\nflat, so we average here",
            fontsize=12.5, color=FOREST, ha="center", va="bottom", fontweight="bold")
    dx.text(1490, T[m].mean() + 0.07, "one temperature\nper sensor", fontsize=12.5,
            color=FOREST, ha="right", va="bottom", fontweight="bold")
    dx.set_xlabel("days since the experiment started", fontsize=FS_LAB)
    dx.set_ylabel("temperature  (K)", fontsize=FS_LAB)
    dx.set_ylim(251.7, 254.1)
    dx.set_title("Apollo 15, sensor at 139 cm", fontsize=13.5, color=DIM,
                 loc="left", pad=10)

    # --- the rule, stated ------------------------------------------------
    card(ax, 7.62, 1.28, 4.20, 3.10, face=TINT, edge=GRID, rail=TEAL)
    ax.text(7.92, 4.02, "THE RULE", fontsize=13, fontweight="bold", color=TEAL,
            va="center", zorder=4)
    rules = ["keep the longest flat tail",
             "reject it if the drift is worse\nthan 0.08 K per year",
             "carry whatever drift is left\nas an error, do not discard it"]
    for i, r in enumerate(rules):
        y = 3.62 - i * 0.70
        ax.text(7.95, y, f"{i+1}", fontsize=16, fontweight="bold", color=TEAL,
                va="top", zorder=4)
        ax.text(8.32, y, r, fontsize=FS_ANN, color=CHAR, va="top",
                zorder=4, linespacing=1.35)
    ax.plot([7.92, 11.52], [1.52, 1.52], color=GRID, lw=1.0, zorder=4)
    ax.text(7.92, 1.36, "23 of the deep sensors qualify.\nNothing is chosen by hand.",
            fontsize=12.5, color=DIM, va="top", style="italic", zorder=4,
            linespacing=1.4)
    save(fig, "lay_window")


# ================================================================= SLIDE 7
def fig_model():
    """Sun in, heat out, trickle from below, one unknown in the middle.

    Carries the GOVERNING EQUATIONS, each placed next to the thing it governs:
    the surface balance by the surface arrows, the basal Neumann condition by
    the bottom arrow, the heat equation and the Hayne conductivity beside the
    column. Forms taken verbatim from the code -
    solver.surface_energy_balance_residual, properties.conductivity_hayne,
    equilibrium._reconstruct_subskin."""
    fig, ax = hero()

    # Each equation card sits at the SAME height as the depth it governs, so
    # every leader is a straight horizontal line and no two can cross
    # (lunar-figures connector rule: fix the layout, not the arrow).
    L, R = 1.66, 3.26                    # column left / right
    TOPY, BOTY = 4.22, 0.92              # z = 0 and z = 5 m
    depth_y = lambda z: TOPY - (z / 5.0) * (TOPY - BOTY)      # noqa: E731
    XEQ = 4.78                           # equation column left edge

    # --- the regolith column ---------------------------------------------
    grad = np.linspace(0, 1, 256).reshape(-1, 1)
    ax.imshow(grad, extent=[L, R, BOTY, TOPY], aspect="auto", zorder=1,
              vmin=0, vmax=1,
              cmap=matplotlib.colors.LinearSegmentedColormap.from_list(
                  "reg", ["#DED4C9", "#F5F1EC"]))
    rng = np.random.default_rng(4)
    ax.scatter(rng.uniform(L + 0.04, R - 0.04, 460),
               rng.uniform(BOTY + 0.04, TOPY - 0.04, 460),
               s=rng.uniform(0.5, 4.5, 460), color="#B3A697", alpha=0.45,
               linewidths=0, zorder=2)
    ax.add_patch(Rectangle((L, BOTY), R - L, TOPY - BOTY, facecolor="none",
                           edgecolor=CHAR, lw=1.5, zorder=4))
    ax.plot([L - 0.12, R + 0.12], [TOPY, TOPY], color=CHAR, lw=2.8, zorder=5)

    for z in range(6):
        y = depth_y(z)
        ax.plot([L - 0.10, L], [y, y], color=DIM, lw=1.1, zorder=5)
        # bare numerals, with the unit given once above: "5 m" is wide enough
        # to slide under the density panel on its left
        ax.text(L - 0.16, y, str(z), fontsize=11.5, color=DIM,
                ha="right", va="center")
    # one line above the density-panel title, which shares this corner
    ax.text(L - 0.16, TOPY + 0.42, "depth (m)", fontsize=11,
            color=DIM, ha="right", va="bottom")
    # --- the density profile, sharing the same depth axis ------------------
    # rho(z) from lunar.properties.density_hayne: 1100 -> 1800 kg/m3 with the
    # same e^{-z/H}, H = 6 cm compaction shape that appears in K_c. Drawn on a
    # linear 0-5 m axis on purpose: the near-vertical rise IS the message, that
    # all the structure lives in the top 20 cm.
    try:
        from lunar.properties import density_hayne
    except ImportError:                       # published form, Hayne 2017
        def density_hayne(z, rho_s=1100.0, rho_d=1800.0, H=0.06):
            return rho_d - (rho_d - rho_s) * np.exp(-z / H)

    dp = fig.add_axes([0.26 / W, BOTY / H, 0.90 / W, (TOPY - BOTY) / H])
    zz = np.linspace(0, 5, 600)
    rr = density_hayne(zz)
    dp.fill_betweenx(zz, 1040, rr, color=TEAL, alpha=0.13, lw=0)
    dp.plot(rr, zz, color=TEAL, lw=2.2, solid_capstyle="round")
    dp.set_ylim(5, 0)
    dp.set_xlim(1040, 1980)
    dp.set_xticks([])
    dp.set_yticks([])
    for s in ("top", "right"):
        dp.spines[s].set_visible(False)
    dp.spines["left"].set_color(GRID)
    dp.spines["bottom"].set_color(GRID)
    dp.plot([1100], [0], "o", ms=5, color=TEAL, mec=WHITE, mew=1.2,
            clip_on=False, zorder=5)
    dp.text(1150, 0.16, "1100", fontsize=10, color=TEAL, va="top",
            fontweight="bold")
    dp.text(1760, 4.72, "1800", fontsize=10, color=TEAL, ha="right",
            va="bottom", fontweight="bold")
    ax.text(0.71, TOPY + 0.14, "density  $\\rho(z)$", fontsize=11.5,
            color=TEAL, ha="center", va="bottom", fontweight="bold")
    ax.text(0.71, 0.60, "kg m$^{-3}$\ncompaction done\nby 20 cm",
            fontsize=9.5, color=DIM, ha="center", va="center", linespacing=1.45)

    # sun; both surface arrows are GOLD because together they ARE the surface
    # energy balance. Coral stays reserved for K_d across the whole deck.
    scx, scy = 1.92, 4.62
    ax.add_patch(Circle((scx, scy), 0.17, color=GOLD, zorder=6))
    for a in np.linspace(0, 2 * np.pi, 12, endpoint=False):
        ax.plot([scx + 0.24 * np.cos(a), scx + 0.32 * np.cos(a)],
                [scy + 0.24 * np.sin(a), scy + 0.32 * np.sin(a)],
                color=GOLD, lw=1.6, solid_capstyle="round", zorder=6)
    ax.add_patch(FancyArrowPatch((2.20, 4.48), (2.44, TOPY + 0.05),
                                 arrowstyle="-|>", mutation_scale=15, lw=2.1,
                                 color=GOLD, zorder=6))
    ax.add_patch(FancyArrowPatch((2.82, TOPY + 0.05), (3.08, 4.54),
                                 arrowstyle="-|>", mutation_scale=15, lw=2.1,
                                 color=GOLD, zorder=6))
    ax.text(3.22, 4.58, "sunlight in, heat out", fontsize=11,
            color="#8F7412", fontweight="bold", va="center")
    ax.add_patch(FancyArrowPatch((2.46, 0.50), (2.46, BOTY - 0.05),
                                 arrowstyle="-|>", mutation_scale=15, lw=2.1,
                                 color=TEAL, zorder=6))
    ax.text(2.62, 0.56, "$Q_b$", fontsize=13, color=TEAL, ha="left",
            va="center", fontweight="bold")

    # where the thermometers actually sit, so the physics slide still shows
    # which part of the column the data constrains
    ax.add_patch(Rectangle((L, depth_y(2.34)), R - L,
                           depth_y(0.80) - depth_y(2.34), facecolor=FOREST,
                           alpha=0.13, edgecolor="none", zorder=3))
    ax.text(R - 0.08, depth_y(1.55), "the 23 sensors\nsit in here",
            fontsize=10, color=FOREST, ha="right", va="center", zorder=6,
            fontweight="bold", linespacing=1.35)

    card(ax, L + 0.12, depth_y(3.90), 1.36, 0.66, face=CORAL_L, edge=CORAL,
         lw=1.5)
    ax.text(L + 0.80, depth_y(3.90) + 0.43, "$K_d = ?$", fontsize=18,
            fontweight="bold", color=CORAL, ha="center", va="center", zorder=6)
    ax.text(L + 0.80, depth_y(3.90) + 0.17, "the only unknown", fontsize=10,
            color=CHAR, ha="center", va="center", zorder=6)

    # --- the governing equations, each level with the depth it governs ----
    ax.text(XEQ, 4.80, "THE GOVERNING EQUATIONS", fontsize=12.5,
            fontweight="bold", color=TEAL, va="center")
    ax.plot([XEQ, 11.86], [4.60, 4.60], color=GRID, lw=1.0)

    eqs = [
        (0.0, "at the top  ·  surface energy balance", GOLD,
         r"$(1-A)\,S=\varepsilon\sigma T_s^{\,4}"
         r"+K\,\partial T/\partial z\;$ at $z=0$"),
        (1.6, "inside the column  ·  heat conduction", CHAR,
         r"$\rho(z)\,c_p(T)\,\dfrac{\partial T}{\partial t}"
         r"=\dfrac{\partial}{\partial z}\left[K(T,z)\,"
         r"\dfrac{\partial T}{\partial z}\right]$"),
        (3.4, "the material law  ·  conductivity, Hayne (2017)", CORAL,
         r"$K(T,z)=\left[K_d-(K_d-K_s)\,e^{-z/H}\right]"
         r"\left[1+\chi\,(T/T_{\mathrm{ref}})^{3}\right]$"),
        (5.0, "at the bottom  ·  fixed geothermal flux", TEAL,
         r"$K\,\partial T/\partial z=Q_b=21\ /\ 16\;$"
         r"mW m$^{-2}$ at $z_{\mathrm{max}}$"),
    ]
    # the leader lands ON the colour chip, and the chip sits on the label's
    # baseline: arriving between the label and the equation reads as a line
    # ending in mid-air
    for z, lab, col, eq in eqs:
        y = depth_y(z)
        ax.plot([R + 0.50, XEQ - 0.06], [y, y], color=col, lw=1.1,
                alpha=0.5, zorder=3)
        ax.plot([R + 0.50], [y], "o", ms=5.5, color=col, zorder=4)
        ax.add_patch(Rectangle((XEQ, y - 0.065), 0.15, 0.13, color=col, zorder=4))
        ax.text(XEQ + 0.27, y, lab, fontsize=11.5, color=col,
                fontweight="bold", va="center")
        ax.text(XEQ, y - 0.44, eq, fontsize=15, color=CHAR, va="center")

    ax.plot([XEQ, 11.86], [0.34, 0.34], color=GRID, lw=1.0)
    ax.text(XEQ, 0.06, "Four equations, five fixed constants, and exactly one "
                       "unknown:  $K_d$.",
            fontsize=12.5, color=DIM, va="bottom", style="italic")
    save(fig, "lay_model")


# ================================================================= SLIDE 8
def fig_solver():
    """The contribution, drawn as geometry rather than as repetition.

    Both halves show the SAME 5 m column, so the difference the audience must
    see - how much of it is time-stepped - is a visible area, not a caption."""
    fig, ax = hero()
    ax.plot([6.00, 6.00], [0.90, 4.50], color=GRID, lw=1.2)

    CTOP, CBOT, CW = 4.30, 1.62, 1.05       # column top (0 m), bottom (5 m)
    depth_y = lambda z: CTOP - (z / 5.0) * (CTOP - CBOT)      # noqa: E731

    def column(x0, hatch_to, col):
        """The same 5 m column on both sides. The only difference the audience
        has to see is how much of it is hatched, so the hatch does the work."""
        ax.add_patch(Rectangle((x0, CBOT), CW, CTOP - CBOT, facecolor=WHITE,
                               edgecolor=CHAR, lw=1.6, zorder=3))
        ax.add_patch(Rectangle((x0, depth_y(hatch_to)), CW,
                               depth_y(0) - depth_y(hatch_to), facecolor=col,
                               edgecolor="none", alpha=0.30, zorder=2))
        for yy in np.arange(depth_y(hatch_to), CTOP - 0.01, 0.075):
            ax.plot([x0, x0 + CW], [yy, yy], color=col, lw=0.7, alpha=0.95, zorder=4)
        for z, lab in [(0, "0"), (5, "5 m")]:
            ax.text(x0 - 0.12, depth_y(z), lab, fontsize=12.5, color=DIM,
                    ha="right", va="center")

    # --- left: the old way ------------------------------------------------
    ax.text(3.00, 4.66, "THE OLD WAY", fontsize=15, fontweight="bold",
            color=DIM, ha="center")
    column(1.00, 5.0, DIM)
    ax.text(2.35, 3.70, "every cell, every hour,\nall the way down",
            fontsize=FS_ANN, color=CHAR, va="top", linespacing=1.45)
    ax.text(2.35, 2.62, "× ~3000 lunations", fontsize=FS_LAB, color=DIM,
            va="center", fontweight="bold")
    ax.text(2.35, 2.20, "before it settles", fontsize=12.5, color=DIM, va="center")
    ax.text(3.00, 1.26, "27 hours", fontsize=30, fontweight="bold",
            color=DIM, ha="center", va="center")
    ax.text(3.00, 0.94, "for one experiment", fontsize=12.0, color=DIM,
            ha="center", va="center")

    # --- right: the anchored solver ---------------------------------------
    ax.text(9.00, 4.66, "THE FLUX-ANCHORED SOLVER", fontsize=15,
            fontweight="bold", color=FOREST, ha="center")
    x0 = 6.55
    column(x0, 0.70, FOREST)
    # the region below the anchor is reconstructed, not stepped: say that with
    # an area and one straight arrow rather than a curve crossing the box
    ax.add_patch(Rectangle((x0, CBOT), CW, depth_y(0.70) - CBOT,
                           facecolor=FOREST, edgecolor="none", alpha=0.09, zorder=2))
    ax.add_patch(FancyArrowPatch((x0 + CW / 2, depth_y(1.15)),
                                 (x0 + CW / 2, depth_y(4.70)),
                                 arrowstyle="-|>", mutation_scale=18, lw=1.8,
                                 color=FOREST, linestyle=(0, (4, 3)), zorder=5))
    ya = depth_y(0.55)
    ax.plot([x0 + CW / 2], [ya], "o", ms=13, color=CORAL, mec=WHITE, mew=2.0,
            zorder=6)

    # one combined label: the skin and the anchor are physically the same
    # place, so two separate callouts here can only collide
    ax.plot([x0 + CW, 7.98], [depth_y(0.35), depth_y(0.35)], color=DIM,
            lw=1.0, zorder=5)
    ax.text(8.06, depth_y(0.35), "time-stepped: only the top 0.7 m,\n"
                                 "with the anchor at 0.55 m",
            fontsize=12.5, color=FOREST, va="center", fontweight="bold",
            linespacing=1.45)
    ax.plot([x0 + CW, 7.98], [depth_y(3.0), depth_y(3.0)], color=DIM,
            lw=1.0, zorder=5)
    ax.text(8.06, depth_y(3.0), "everything below is rebuilt from\n"
                                "one equation, never simulated",
            fontsize=12.5, color=CHAR, va="center", linespacing=1.45)
    ax.text(9.00, 1.26, "under 1 minute", fontsize=30, fontweight="bold",
            color=FOREST, ha="center", va="center")
    ax.text(9.00, 0.94, "≈ 2500× faster, same answer to better than 0.01 mW",
            fontsize=12.0, color=FOREST, ha="center", va="center",
            fontweight="bold")

    # the one equation that makes the method work. Sign convention is the
    # project canon: MINUS u_rect (equilibrium._reconstruct_subskin).
    ax.plot([1.20, 10.80], [0.78, 0.78], color=GRID, lw=1.0)
    ax.text(6.00, 0.62, "the closure that replaces the deep simulation",
            fontsize=11.5, color=DIM, ha="center", va="center", style="italic")
    ax.text(6.00, 0.08,
            r"$\frac{d\langle T\rangle}{dz}"
            r"=\frac{Q_b-u_{\mathrm{rect}}}{K(\langle T\rangle,\,z)}$"
            "     below the skin $u_{\\mathrm{rect}}$ is under 1% of $Q_b$,"
            r"  so the deep slope is just $\frac{Q_b}{K}$",
            fontsize=14, color=CHAR, ha="center", va="bottom")
    save(fig, "lay_solver")


# ================================================================= SLIDE 9
def fig_bowl():
    """Try every value, keep the best. The 3.4 line foreshadows the result."""
    fig, ax = hero()
    dx = data_axes(fig, 0.075, 0.165, 0.885, 0.735)

    k = np.linspace(1.5, 12, 400)
    # each site label is parked in a pocket where only its OWN curve is near:
    # placed next to the minimum, "Apollo 17" landed on the Apollo 15 curve
    for kstar, rm, col, lab, lx, ly, lha in [
            (4.60, 1.00, FOREST, "Apollo 15", 8.80, 2.55, "center"),
            (7.08, 0.40, CORAL, "Apollo 17", 11.60, 1.62, "right")]:
        dx.plot(k, rm + 0.055 * (k - kstar) ** 2, lw=3.5, color=col)
        dx.plot([kstar], [rm], "o", ms=16, color=col, mec=WHITE, mew=2.4, zorder=6)
        dx.annotate(f"{kstar:.2f}", xy=(kstar, rm), xytext=(kstar, rm - 0.52),
                    fontsize=17, fontweight="bold", color=col, ha="center",
                    zorder=7,
                    bbox=dict(boxstyle="round,pad=0.22", facecolor=WHITE,
                              edgecolor=col, lw=1.2))
        dx.text(lx, ly, lab, fontsize=FS_LAB, color=col, fontweight="bold",
                va="center", ha=lha)

    dx.axvline(3.4, color=DIM, lw=1.6, ls=(0, (5, 4)), zorder=2)
    dx.text(3.28, 3.02, "the global value\neveryone used: 3.4", fontsize=12.5,
            color=DIM, ha="right", va="top", linespacing=1.4)
    # the only guaranteed-empty pocket is under both curves on the right; at
    # y=1.35 and y=2.10 this callout sat on the Apollo 17 site label
    dx.annotate("lowest point = best answer", xy=(7.40, 0.46), xytext=(9.95, 0.12),
                fontsize=FS_ANN, color=CHAR, fontweight="bold", ha="center",
                va="center",
                arrowprops=dict(arrowstyle="-|>", color=CHAR, lw=1.5,
                                shrinkA=8, shrinkB=4))

    dx.set_xlabel("candidate deep conductivity  $K_d$   (mW m$^{-1}$ K$^{-1}$)",
                  fontsize=FS_LAB)
    dx.set_ylabel("how badly the model misses\nthe real thermometers",
                  fontsize=FS_LAB, linespacing=1.4)
    dx.set_yticks([])
    dx.set_ylim(-0.20, 3.30)
    dx.set_xlim(1.5, 12)
    dx.annotate("", xy=(1.72, 0.35), xytext=(1.72, 1.35),
                arrowprops=dict(arrowstyle="-|>", color=DIM, lw=1.4))
    dx.text(1.86, 0.85, "better", fontsize=12.5, color=DIM, rotation=90,
            va="center", ha="center")
    save(fig, "lay_bowl")


# ================================================================ SLIDE 10
def fig_results():
    """The headline. Two measurements as bars; the global value as a
    reference line, because it is not a measurement of these sites."""
    fig, ax = hero()
    dx = data_axes(fig, 0.115, 0.335, 0.845, 0.560)

    rows = [(1, "Apollo 15", 4.60, 4.18, 6.96, FOREST),
            (0, "Apollo 17", 7.08, 6.16, 8.07, CORAL)]
    for y, name, v, lo, hi, col in rows:
        dx.barh([y], [v], height=0.46, color=col, zorder=3)
        dx.errorbar([v], [y], xerr=[[v - lo], [hi - v]], fmt="none", ecolor=CHAR,
                    elinewidth=2.2, capsize=8, capthick=2.2, zorder=4)
        # solid backing in the bar colour: the lower whisker arm runs under
        # this numeral and would otherwise read as a strikethrough
        dx.text(v - 0.16, y, f"{v:.2f}", va="center", ha="right", fontsize=28,
                fontweight="bold", color=WHITE, zorder=6,
                bbox=dict(boxstyle="square,pad=0.14", facecolor=col,
                          edgecolor="none"))
        dx.text(hi + 0.22, y, f"95% range  {lo:.2f} – {hi:.2f}", va="center",
                fontsize=12.5, color=DIM, zorder=5)

    dx.axvline(3.4, color=DIM, lw=1.8, ls=(0, (5, 4)), zorder=2)
    dx.text(3.52, 1.98, "the global value everyone uses: 3.4", fontsize=12.5,
            color=DIM, ha="left", va="center")
    dx.annotate("", xy=(4.60, 0.5), xytext=(7.08, 0.5),
                arrowprops=dict(arrowstyle="<|-|>", color=CHAR, lw=1.6))
    dx.text(5.84, 0.60, "1.5×", fontsize=17, fontweight="bold", color=CHAR,
            ha="center", va="bottom")

    dx.set_yticks([1, 0])
    dx.set_yticklabels(["Apollo 15", "Apollo 17"], fontsize=FS_HEAD,
                       fontweight="bold")
    dx.get_yticklabels()[0].set_color(FOREST)
    dx.get_yticklabels()[1].set_color(CORAL)
    dx.set_xlim(0, 10.4)
    dx.set_ylim(-0.55, 2.20)
    dx.grid(axis="y", visible=False)
    dx.set_xlabel("deep conductivity  (mW m$^{-1}$ K$^{-1}$)   —   higher = lets heat "
                  "through more easily", fontsize=FS_LAB)

    for i, (lab, val, col) in enumerate([
            ("mismatch at Apollo 15", "1.09  $\\rightarrow$  1.00 K", FOREST),
            ("mismatch at Apollo 17", "0.89  $\\rightarrow$  0.40 K", CORAL),
            ("global value vs fitted value", "both sites sit above 3.4", DIM)]):
        x = 0.18 + i * 3.92
        card(ax, x, 0.16, 3.72, 0.90, face=TINT, edge=GRID, rail=col)
        ax.text(x + 0.28, 0.78, lab.upper(), fontsize=11.5, fontweight="bold",
                color=col, va="center", zorder=4)
        ax.text(x + 0.28, 0.42, val, fontsize=FS_LAB, color=CHAR, va="center",
                zorder=4)
    save(fig, "lay_results")


# ================================================================ SLIDE 11
def fig_bootstrap():
    """Resampling, taught rather than reported. Real draws from
    code/results/kd_retrieval_results.json."""
    b = load_bootstrap()
    fig, ax = hero()

    # --- left: what one draw looks like -----------------------------------
    ax.text(0.18, 4.62, "ONE DRAW", fontsize=13.5, fontweight="bold", color=TEAL)
    ax.text(0.18, 4.24, "leave some sensors out at random,\nnudge the rest up or down by 2.5 cm",
            fontsize=12.5, color=DIM, va="top", linespacing=1.4)
    # 23 dots per row: the real sensor count, 7 at Apollo 15 then 16 at 17
    rng = np.random.default_rng(11)
    for r in range(4):
        y = 3.30 - r * 0.52
        for i in range(23):
            x = 0.34 + i * 0.132 + rng.uniform(-0.022, 0.022)
            keep = rng.random() > 0.32
            col = FOREST if i < 7 else CORAL
            ax.plot([x], [y], "o", ms=7,
                    color=col if keep else WHITE,
                    mec=col if keep else DIM, mew=1.2, alpha=1.0 if keep else 0.8)
        ax.text(3.56, y, f"draw {r+1}", fontsize=12, color=DIM, va="center")
    ax.text(0.34, 1.10, ".\n.\n.", fontsize=13, color=DIM,
            ha="center", va="center", linespacing=0.75)
    ax.add_patch(FancyBboxPatch((0.30, 0.30), 3.55, 0.56,
                                boxstyle="round,pad=0,rounding_size=0.08",
                                facecolor=TEAL_L, edgecolor=TEAL, lw=1.4))
    ax.text(2.07, 0.58, "repeat 1500 times", fontsize=FS_HEAD, fontweight="bold",
            color=TEAL, ha="center", va="center", zorder=4)

    # --- right: the spread it produces ------------------------------------
    dx = data_axes(fig, 0.395, 0.155, 0.565, 0.700)
    peak = 0.0
    for s, col in [("A15", FOREST), ("A17", CORAL)]:
        n, _, _ = dx.hist(b[s]["samples"], bins=44, color=col, alpha=0.72,
                          edgecolor="none", zorder=3)
        peak = max(peak, n.max())
    for s, col, lab in [("A15", FOREST, "Apollo 15"), ("A17", CORAL, "Apollo 17")]:
        dx.text(b[s]["star"], peak * 1.03, lab, fontsize=FS_LAB, color=col,
                fontweight="bold", ha="center", va="bottom")
    for i, (s, col) in enumerate([("A15", FOREST), ("A17", CORAL)]):
        y = -peak * (0.10 + i * 0.09)
        dx.plot([b[s]["lo"], b[s]["hi"]], [y, y], color=col, lw=6,
                solid_capstyle="butt", zorder=4)
        dx.text(b[s]["hi"] + 0.12, y, f"{b[s]['lo']:.2f} – {b[s]['hi']:.2f}",
                fontsize=12.5, color=col, va="center", fontweight="bold")
    dx.text(3.46, -peak * 0.145, "95% range", fontsize=12.5, color=DIM,
            ha="left", va="center", style="italic")
    dx.set_xlabel("deep conductivity from each draw  (mW m$^{-1}$ K$^{-1}$)",
                  fontsize=FS_LAB)
    dx.set_yticks([])
    dx.set_ylabel("how often", fontsize=FS_LAB)
    dx.set_xlim(3.4, 10.0)
    dx.set_ylim(-peak * 0.26, peak * 1.62)
    dx.grid(axis="y", visible=False)
    # anchored top-right so the leader descends through the empty valley
    # between the two humps and crosses neither direct label
    dx.annotate("the two spreads barely overlap —\nthis is why the ORDERING is solid",
                xy=(6.30, peak * 0.42), xytext=(9.95, peak * 1.38),
                fontsize=FS_ANN, color=CHAR, fontweight="bold", ha="right",
                va="center", linespacing=1.4,
                arrowprops=dict(arrowstyle="-|>", color=CHAR, lw=1.4,
                                shrinkA=8, shrinkB=2))
    save(fig, "lay_bootstrap")


# ================================================================ SLIDE 12
def fig_seesaw():
    """The degeneracy, drawn. Two different grounds can tilt the beam the
    same way, which is exactly what the thermometers cannot separate."""
    fig, ax = hero()

    def beam(cx, cy, span, tilt, wl, wr, ghost=False):
        a = np.deg2rad(tilt)
        dxx, dyy = span * np.cos(a), span * np.sin(a)
        al = 0.30 if ghost else 1.0
        ax.plot([cx - dxx, cx + dxx], [cy - dyy, cy + dyy], color=CHAR,
                lw=4.0, solid_capstyle="round", alpha=al, zorder=4)
        ax.add_patch(Polygon([[cx - 0.30, cy - 0.62], [cx + 0.30, cy - 0.62],
                              [cx, cy - 0.04]], closed=True, facecolor=CHAR,
                             alpha=al, zorder=3))
        for sgn, w, col, lab in [(-1, wl, TEAL, "heat from below\n$Q_b$"),
                                 (+1, wr, FOREST, "conductivity\n$K_d$")]:
            bx, by = cx + sgn * dxx, cy + sgn * dyy
            ax.add_patch(FancyBboxPatch((bx - w / 2, by + 0.06), w, w * 0.62,
                                        boxstyle="round,pad=0,rounding_size=0.06",
                                        facecolor=col, edgecolor="none",
                                        alpha=al, zorder=5))
            if not ghost:
                ax.text(bx, by - 0.30, lab, fontsize=12.5, color=col,
                        fontweight="bold", ha="center", va="top", linespacing=1.35)

    beam(2.55, 3.35, 1.55, -11, 0.62, 0.62)
    beam(2.55, 1.35, 1.55, -11, 0.92, 0.92, ghost=True)
    ax.text(2.55, 4.62, "the thermometers only see the TILT", fontsize=FS_LAB,
            fontweight="bold", color=CHAR, ha="center")
    ax.text(2.55, 0.62, "double both, and the tilt is identical",
            fontsize=FS_ANN, color=DIM, ha="center", style="italic")
    ax.text(2.55, 0.20, "steepness  =  $Q_b\\ /\\ K_d$", fontsize=13.5,
            color=DIM, ha="center")

    ax.plot([5.55, 5.55], [0.55, 4.45], color=GRID, lw=1.2)
    boxes = [("What is solid", FOREST, FOREST_L,
              "Apollo 17 is the more conductive site. This holds in\n"
              "more than 99% of the tested cases, including when the\n"
              "assumed heat flow is allowed to vary by four times\n"
              "its published spread."),
             ("What is not settled", CORAL, CORAL_L,
              "The exact size of the gap, and whether the difference\n"
              "is conductivity or heat from below. The 95% range on\n"
              "the difference, [−0.12, 3.56], still touches zero.")]
    for i, (head, col, face, body) in enumerate(boxes):
        y = 2.56 - i * 2.10
        card(ax, 6.00, y, 5.82, 1.94, face=face, edge=col, lw=1.6)
        ax.text(6.30, y + 1.56, head, fontsize=FS_HEAD, fontweight="bold",
                color=col, va="center", zorder=4)
        ax.text(6.30, y + 1.20, body, fontsize=12.5, color=CHAR, va="top",
                zorder=4, linespacing=1.55)
    save(fig, "lay_seesaw")


# ================================================================ SLIDE 15
def fig_global():
    """Two dots today, a map at the end. The Y1/Y2/Y3 ticks rhyme with the
    plan slide on purpose."""
    fig, ax = hero()
    R = 1.42
    c1, c2, cy = 2.20, 9.80, 2.80

    ax.add_patch(Circle((c1, cy), R, facecolor=TINT, edgecolor=DIM, lw=1.6))
    for (dx_, dy_), c in [((-0.30, 0.52), FOREST), ((0.40, 0.26), CORAL)]:
        ax.add_patch(Circle((c1 + dx_, cy + dy_), 0.13, color=c, zorder=4))
    ax.text(c1, cy - R - 0.24, "TODAY", fontsize=FS_HEAD, fontweight="bold",
            color=DIM, ha="center", va="top")
    ax.text(c1, cy - R - 0.62, "2 measured points", fontsize=FS_ANN, color=DIM,
            ha="center", va="top")

    ax.add_patch(FancyArrowPatch((4.10, cy), (7.90, cy), arrowstyle="-|>",
                                 mutation_scale=26, lw=2.6, color=CHAR))
    for i, (lab, col) in enumerate([("Y1", FOREST), ("Y2", TEAL), ("Y3", CORAL)]):
        x = 4.75 + i * 1.20
        ax.plot([x, x], [cy - 0.16, cy + 0.16], color=col, lw=3.0,
                solid_capstyle="round", zorder=4)
        ax.text(x, cy + 0.32, lab, fontsize=13.5, fontweight="bold", color=col,
                ha="center", va="bottom")
    ax.text(6.00, cy - 0.42, "three-year plan", fontsize=FS_ANN, color=CHAR,
            ha="center", va="top", fontweight="bold")

    n = 420
    g = np.linspace(-1, 1, n)
    GX, GY = np.meshgrid(g, g)
    rr = np.hypot(GX, GY)
    field = np.cos(np.arcsin(np.clip(GY, -1, 1))) ** 0.25
    field += 0.035 * np.sin(5.0 * GX) * np.cos(4.0 * GY)
    ax.imshow(np.where(rr <= 1.0, field, np.nan),
              extent=[c2 - R, c2 + R, cy - R, cy + R], origin="lower",
              cmap="RdYlBu_r", vmin=0.78, vmax=1.01, interpolation="bilinear",
              zorder=2)
    ax.add_patch(Circle((c2, cy), R, facecolor="none", edgecolor=DIM, lw=1.6,
                        zorder=3))
    ax.text(c2, cy - R - 0.24, "GOAL", fontsize=FS_HEAD, fontweight="bold",
            color=CHAR, ha="center", va="top")
    ax.text(c2, cy - R - 0.62, "a Moon-wide subsurface map,\nand where ice can survive",
            fontsize=FS_ANN, color=CHAR, ha="center", va="top", linespacing=1.4)
    save(fig, "lay_global")


# ================================================================ SLIDE 17
def fig_cpvc():
    """Which property controls the answer, and does layering transfer?

    Both panels share one x scale (0-4 K) so the two experiments cannot be
    misread against each other. Numbers: documents/aogs/results/
    aogs_density_study.json and aogs_crossite.json."""
    fig, ax = hero()
    XMAX = 4.0

    # --- left: storage only vs storage + conductivity ---------------------
    dl = data_axes(fig, 0.105, 0.265, 0.310, 0.455)
    pairs = [("Apollo 15", 1.744, 0.904, FOREST), ("Apollo 17", 0.395, 0.362, CORAL)]
    for i, (nm, a, bb, col) in enumerate(pairs):
        y = 1 - i
        dl.plot([a, bb], [y, y], color=col, lw=3.0, alpha=0.45, zorder=3)
        dl.plot([a], [y], "o", ms=13, color=WHITE, mec=col, mew=2.6, zorder=4)
        dl.plot([bb], [y], "o", ms=13, color=col, mec=WHITE, mew=1.8, zorder=5)
        dl.text(a, y + 0.30, f"{a:.2f}", fontsize=12.5, color=DIM, ha="center")
        dl.text(bb, y - 0.38, f"{bb:.2f}", fontsize=12.5, color=col, ha="center",
                fontweight="bold")
    dl.set_yticks([1, 0])
    dl.set_yticklabels(["Apollo 15", "Apollo 17"], fontsize=FS_LAB, fontweight="bold")
    dl.get_yticklabels()[0].set_color(FOREST)
    dl.get_yticklabels()[1].set_color(CORAL)
    dl.set_xlim(0, XMAX)
    dl.set_ylim(-0.75, 1.75)
    dl.grid(axis="y", visible=False)
    dl.set_xlabel("mismatch against the thermometers  (K)", fontsize=12.5)
    ax.text(0.18, 4.72, "DENSITY DOES TWO JOBS", fontsize=13.5, fontweight="bold",
            color=TEAL, va="center")
    ax.text(0.18, 4.34, "hollow = density sets heat storage only        "
                        "filled = it also sets the conductivity",
            fontsize=12.0, color=DIM, va="center")
    ax.text(0.18, 0.42, "At Apollo 15 the coupling halves the error. At Apollo 17\n"
                        "the site already fits, so it changes little.",
            fontsize=12.5, color=CHAR, va="center", linespacing=1.45)

    # --- right: does the layered physics travel? --------------------------
    dr = data_axes(fig, 0.585, 0.265, 0.370, 0.455)
    cfg = [("uniform ground", DIM, 2.308, 3.762),
           ("the other site's setup", TEAL, 1.635, 1.727),
           ("its own best setup", None, 0.904, 0.362)]
    hgt = 0.24
    for j, (lab, col, v15, v17) in enumerate(cfg):
        for i, (v, site_col) in enumerate([(v15, FOREST), (v17, CORAL)]):
            y = (1 - i) + (1 - j) * hgt - hgt
            dr.barh([y], [v], height=hgt * 0.86,
                    color=(col or site_col), zorder=3)
            dr.text(v + 0.07, y, f"{v:.2f}", fontsize=11.5,
                    color=(col or site_col), va="center", fontweight="bold")
    dr.set_yticks([1, 0])
    dr.set_yticklabels(["Apollo 15", "Apollo 17"], fontsize=FS_LAB, fontweight="bold")
    dr.get_yticklabels()[0].set_color(FOREST)
    dr.get_yticklabels()[1].set_color(CORAL)
    dr.set_xlim(0, XMAX)
    dr.set_ylim(-0.75, 1.75)
    dr.grid(axis="y", visible=False)
    dr.set_xlabel("mismatch against the thermometers  (K)   —   lower is better",
                  fontsize=12.5)
    ax.text(6.55, 4.72, "LAYERED BEATS UNIFORM", fontsize=13.5, fontweight="bold",
            color=FOREST, va="center")
    for x, lab, cols in [(6.55, "uniform ground", (DIM,)),
                         (8.20, "the other site's setup", (TEAL,)),
                         (10.25, "its own best setup", (FOREST, CORAL))]:
        # the third bar is drawn in the site's own colour, so its key needs
        # both swatches rather than a neutral one that appears nowhere
        for j, c in enumerate(cols):
            ax.add_patch(Rectangle((x + j * 0.11, 4.28), 0.10 if len(cols) > 1 else 0.20,
                                   0.12, color=c, zorder=3))
        ax.text(x + 0.28, 4.34, lab, fontsize=11.0, color=CHAR, va="center")
    ax.text(6.55, 0.42, "2.6× better than uniform at Apollo 15,  10× at Apollo 17.",
            fontsize=12.5, color=CHAR, va="center", fontweight="bold")
    save(fig, "lay_cpvc")


# ================================================================ SLIDE 21
def fig_planflow():
    """The doctoral plan as a flow, not as three parallel cards.

    Left: what already exists (the three finished pieces, so the plan visibly
    starts from work rather than from a wish). Middle: Y1 -> Y2 -> Y3 on one
    spine. Right: the deliverable each year hands to the next.

    Connector discipline (lunar-figures): one arrow style, every arrow lands
    flush on its own two boxes, no arrow crosses another, and nothing is drawn
    that the box text already states."""
    fig, ax = hero()

    XA, XB, XC = 0.18, 3.90, 8.32          # column left edges
    WA, WB, WC = 3.00, 3.70, 3.50
    ys = [3.28, 1.94, 0.60]                # three rows, top to bottom
    RH = 1.16

    ax.text(XA, 4.68, "ALREADY BUILT", fontsize=12.5, fontweight="bold",
            color=FOREST, va="center")
    ax.text(XB, 4.68, "THE THREE YEARS", fontsize=12.5, fontweight="bold",
            color=CHAR, va="center")
    ax.text(XC, 4.68, "WHAT EACH YEAR HANDS OVER", fontsize=12.5,
            fontweight="bold", color=CORAL, va="center")
    ax.plot([XA, 11.82], [4.48, 4.48], color=GRID, lw=1.0)

    have = ["the fast solver,\nverified",
            "real terrain shading,\npresented at AOGS",
            "the controlling parameter,\nalready identified"]
    for txt, y in zip(have, ys):
        card(ax, XA, y, WA, RH, face=FOREST_L, edge=FOREST, lw=1.3)
        ax.text(XA + WA / 2, y + RH / 2, txt, fontsize=12.0, color=CHAR,
                ha="center", va="center", zorder=4, linespacing=1.45)

    years = [("Y1", "Get the physics right",
              "go beyond the standard formula;\ntest against both boreholes", FOREST),
             ("Y2", "Go global",
              "terrain shading Moon-wide;\na profile for every point", TEAL),
             ("Y3", "Answer the question",
              "where subsurface ice survives;\nfeed the sounding missions", CORAL)]
    for (tag, head, sub, col), y in zip(years, ys):
        card(ax, XB, y, WB, RH, face=WHITE, edge=col, lw=1.7)
        ax.add_patch(Circle((XB + 0.36, y + RH - 0.30), 0.21, color=col, zorder=4))
        ax.text(XB + 0.36, y + RH - 0.30, tag, fontsize=12, fontweight="bold",
                color=WHITE, ha="center", va="center", zorder=5)
        ax.text(XB + 0.68, y + RH - 0.30, head, fontsize=13.5, fontweight="bold",
                color=CHAR, va="center", zorder=4)
        ax.text(XB + 0.20, y + 0.30, sub, fontsize=11.5, color=DIM,
                va="center", zorder=4, linespacing=1.4)

    deliv = [("a validated property model", FOREST),
             ("a Moon-wide temperature map", TEAL),
             ("an ice-survivability map", CORAL)]
    for (txt, col), y in zip(deliv, ys):
        card(ax, XC, y, WC, RH, face=TINT, edge=col, lw=1.5, rail=col)
        ax.text(XC + 0.30, y + RH / 2 + 0.16, "DELIVERABLE", fontsize=10.5,
                fontweight="bold", color=col, va="center", zorder=4)
        ax.text(XC + 0.30, y + RH / 2 - 0.22, txt, fontsize=13.0, color=CHAR,
                va="center", zorder=4)

    arr = dict(arrowstyle="-|>", mutation_scale=16, lw=1.6, color=DIM)
    for y in ys:                                   # have -> year, year -> deliverable
        ax.add_patch(FancyArrowPatch((XA + WA, y + RH / 2), (XB, y + RH / 2), **arr))
        ax.add_patch(FancyArrowPatch((XB + WB, y + RH / 2), (XC, y + RH / 2), **arr))
    for a, b in zip(ys[:-1], ys[1:]):              # the year spine, top to bottom
        ax.add_patch(FancyArrowPatch((XB + WB / 2, a), (XB + WB / 2, b + RH),
                                     arrowstyle="-|>", mutation_scale=16,
                                     lw=2.0, color=CHAR))
    save(fig, "lay_planflow")


# ============================================================== ANIMATIONS
def gif_hook():
    """SLIDE 2. Cross-section of lunar soil colour-coded by temperature, the
    Sun tracking overhead across one lunation, and two live readouts: the
    surface, which never stops moving, and one metre down, which never starts.

    Depth uses a square-root scale so the top few centimetres are visible;
    the tick labels carry the true depths. Damped thermal wave
    T(z,t)=T0+A e^{-z/d} sin(wt - z/d); illustrative, not a site solve."""
    T0, A, d = 250.0, 140.0, 5.0                 # K, K, cm skin depth
    ZMAX = 130.0
    u = np.linspace(0.0, np.sqrt(ZMAX), 260)
    zz = u ** 2
    UMAX, SKY = float(u[-1]), -4.6

    fig = plt.figure(figsize=(W, H), dpi=100)     # -> 1200 x 498 px
    sc = fig.add_axes([0.045, 0.155, 0.545, 0.80])
    # aligned under the GROUND (x 0..10 of the widened scene), not under the
    # whole scene axes, which now also carries the label margins
    cb = fig.add_axes([0.105, 0.075, 0.315, 0.042])     # temperature key
    rd = fig.add_axes([0.655, 0.075, 0.330, 0.88])
    rd.axis("off")
    # the ground occupies x 0..10; the margins outside it hold the depth ticks
    # and the layer labels, so no label ever has to read against hot regolith
    sc.set_xlim(-1.9, 15.4)
    sc.set_ylim(UMAX, SKY)
    sc.axis("off")

    # --- temperature colour bar -------------------------------------------
    grad = np.linspace(100, 395, 256)[None, :]
    cb.imshow(grad, aspect="auto", cmap="RdYlBu_r", vmin=100, vmax=395,
              extent=[100, 395, 0, 1])
    cb.set_yticks([])
    cb.set_xticks([100, 200, 300, 395])
    cb.set_xticklabels(["100 K", "200 K", "300 K", "395 K"])
    cb.tick_params(labelsize=11, length=0, pad=2)
    for s in ("top", "right", "left", "bottom"):
        cb.spines[s].set_visible(False)
    cb.text(1.012, 0.5, "ground temperature", transform=cb.transAxes,
            fontsize=11, color=DIM, va="center", ha="left")

    sc.add_patch(Rectangle((0, SKY), 10, -SKY, facecolor="#0B0A10", zorder=1))
    rng = np.random.default_rng(5)
    stars = [sc.plot(rng.uniform(0.2, 9.8), rng.uniform(SKY + 0.35, -0.55),
                     marker="*", ms=rng.uniform(1.8, 4.0), color="#8D8D9E",
                     zorder=2)[0] for _ in range(34)]
    sun, = sc.plot([], [], marker="o", ms=19, color="#FFC93C",
                   mec="#FFE9A8", mew=2.0, zorder=5, linestyle="none")

    im = sc.imshow(np.tile(np.full_like(u, T0)[:, None], (1, 2)),
                   extent=[0, 10, UMAX, 0], origin="upper", aspect="auto",
                   cmap="RdYlBu_r", vmin=100, vmax=395,
                   interpolation="bilinear", zorder=3)
    sc.plot([0, 10], [0, 0], color=WHITE, lw=2.6, zorder=6)

    # --- the regolith layering, static, labelled on the right -------------
    # depths from lunar.config / properties: H = 6 cm compaction depth, the
    # diurnal wave is gone by ~20 cm, the borestem cut is 80 cm.
    # labels kept short: matplotlib does not clip text to the axes, so a long
    # label here runs straight into the readout column on the right
    layers = [(6.0, "fines compact", DIM),
              (20.0, "daily wave gone", DIM),
              (80.0, "disturbed zone ends", CORAL),
              (100.0, "1 metre down", CHAR)]
    for dd, lab, col in layers:
        u = np.sqrt(dd)
        sc.plot([0, 10.35], [u, u], color=col, lw=1.3,
                ls="-" if dd == 100 else (0, (4, 3)), alpha=0.9, zorder=6)
        sc.text(10.55, u, f"{dd:.0f} cm  {lab}", fontsize=10.5, color=col,
                ha="left", va="center", zorder=7,
                fontweight="bold" if dd >= 80 else "normal")
    sc.text(10.55, np.sqrt(118.0), "the measured zone", fontsize=11,
            color=FOREST, fontweight="bold", va="center", ha="left", zorder=7)
    for dd in (5, 20, 50, 130):
        sc.text(-0.18, np.sqrt(dd), f"{dd} cm", fontsize=10.5, color=DIM,
                ha="right", va="center", zorder=7)

    day = rd.text(0.0, 0.99, "", fontsize=13.5, color=DIM, va="top",
                  fontweight="bold", family="monospace", transform=rd.transAxes)
    rd.text(0.0, 0.845, "AT THE SURFACE", fontsize=13, color=CORAL,
            va="top", fontweight="bold", transform=rd.transAxes)
    v_top = rd.text(0.0, 0.775, "", fontsize=38, color=CHAR, va="top",
                    fontweight="bold", transform=rd.transAxes)
    rd.text(0.0, 0.565, "swings 100 to 390 K\nevery month", fontsize=12.5,
            color=DIM, va="top", linespacing=1.4, transform=rd.transAxes)
    rd.text(0.0, 0.375, "ONE METRE DOWN", fontsize=13, color=FOREST,
            va="top", fontweight="bold", transform=rd.transAxes)
    v_bot = rd.text(0.0, 0.305, "", fontsize=38, color=CHAR, va="top",
                    fontweight="bold", transform=rd.transAxes)
    rd.text(0.0, 0.095, "± 0.0 K all month", fontsize=12.5,
            color=DIM, va="top", transform=rd.transAxes)

    N = 48                                        # 48 frames @ 12 fps = 4 s

    def upd(i):
        f = (i / N + 0.25) % 1.0                  # frame 0 = lunar noon
        ph = 2 * np.pi * f
        T = T0 + A * np.exp(-zz / d) * np.sin(ph - zz / d)
        im.set_data(np.tile(T[:, None], (1, 2)))
        elev = np.sin(ph)
        if elev > 0.02:
            sun.set_data([0.6 + 8.8 * (f / 0.5)], [-0.7 - 3.3 * elev])
            for st in stars:
                st.set_alpha(max(0.0, 0.85 - 3.2 * elev))
        else:
            sun.set_data([], [])
            for st in stars:
                st.set_alpha(0.85)
        day.set_text(f"day {f * 29.5:4.1f} of 29.5")
        v_top.set_text(f"{T[0]:.0f} K")
        v_bot.set_text(f"{T0 + A * np.exp(-100 / d) * np.sin(ph - 100 / d):.1f} K")
        return im, sun, day, v_top, v_bot

    a = anim.FuncAnimation(fig, upd, frames=N, blit=False)
    a.save(OUT / "anim_hook.gif", writer=anim.PillowWriter(fps=12), dpi=100)
    plt.close(fig)
    print("   anim_hook.gif")


def gif_race():
    """BACKUP. The old method crawls toward the answer over thousands of
    cycles; the anchored solver arrives in four."""
    fig = plt.figure(figsize=(W, H), dpi=100)
    ax = fig.add_axes([0.085, 0.145, 0.885, 0.735])
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    target = 253.0
    n = np.arange(1, 3001)
    brute = target - 22.0 * np.exp(-n / 620.0)
    ax.axhline(target, color=CHAR, lw=1.7, ls=(0, (5, 4)))
    ax.text(3060, target + 0.8, "true answer", fontsize=13, color=CHAR, ha="right")
    lb, = ax.plot([], [], lw=3.2, color=DIM, label="old way: simulate every cycle")
    la, = ax.plot([], [], lw=0, marker="o", ms=15, color=FOREST, mec=WHITE, mew=2.2,
                  label="flux-anchored solver: 4 cycles")
    ax.set_xlim(0, 3100)
    ax.set_ylim(228, 258)
    ax.set_xlabel("month-long cycles simulated", fontsize=FS_LAB)
    ax.set_ylabel("deep temperature  (K)", fontsize=FS_LAB)
    ax.tick_params(labelsize=12.5)
    ax.grid(color=GRID, lw=0.8)
    ax.set_axisbelow(True)
    leg = ax.legend(fontsize=12.5, frameon=True, edgecolor=GRID, loc="lower right")
    leg.get_frame().set_facecolor(WHITE)
    ttl = ax.set_title("", fontsize=FS_LAB, color=CHAR, loc="left", pad=12)
    N = 48

    def upd(i):
        k = int((i / (N - 1)) ** 1.7 * 2999) + 1
        lb.set_data(n[:k], brute[:k])
        if i >= 3:
            la.set_data([4], [target])
        ttl.set_text(f"cycles simulated: {k:,}      anchored solver: 4")
        return lb, la, ttl

    a = anim.FuncAnimation(fig, upd, frames=N, blit=False)
    a.save(OUT / "anim_race.gif", writer=anim.PillowWriter(fps=12), dpi=100)
    plt.close(fig)
    print("   anim_race.gif")


# ------------------------------------------------------------------ driver
# fig_pipeline is deliberately NOT built: the deck now shows guidebook Fig 2.1
# itself (exported as gb_pipeline) rather than a lay redraw of it.
STATIC = [fig_gap, fig_boreholes, fig_window, fig_model,
          fig_solver, fig_bowl, fig_results, fig_bootstrap, fig_seesaw,
          fig_global, fig_cpvc, fig_planflow]

if __name__ == "__main__":
    print("published figures (exported as-is):")
    export_pdfs()
    print("static art (all 2400x996):")
    for f in STATIC:
        f()
    print("animations (1200x498):")
    gif_hook()
    gif_race()
    print("done ->", OUT)
