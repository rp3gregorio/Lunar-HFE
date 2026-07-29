#!/usr/bin/env python3
"""Study-phase pack: master flowchart + one reference slide per phase.

Scope corrected 2026-07-29:
  Phase 1 IS the thesis (complete, submitted). The ChaSTE/Chang'E benchmark is
  no longer part of it and has been removed.
  Phase 2 IS the AOGS terrain work — the DEM exists and is applied AT THE TWO
  APOLLO SITES ONLY. Extending it Moon-wide is its own phase, not a loose end
  inside this one.
  Phases 3-5 follow, each scoped to one question and one deliverable.

Every number is certified: code/results/*.json, documents/aogs/results/*.json.

Outputs (documents/gedes/defense/img/):
    study_phases_flow.png / @600
    phase1_slide.png ... phase5_slide.png
Run:
    python documents/gedes/defense/make_phase_slides.py
"""
import pathlib
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch, Circle, Rectangle

OUT = pathlib.Path(__file__).resolve().parent / "img"

CHAR, CORAL, TEAL = "#2A2520", "#B85B3A", "#2A6478"
FOREST, DIM, GRID = "#3D6E4A", "#6E6862", "#E8E5E0"
TINT, WHITE, PLUM = "#F7F5F2", "#FFFFFF", "#5A4A6A"
GOLD = "#9A7B12"
FOREST_L, TEAL_L, CORAL_L, PLUM_L = "#E9F0EA", "#E6EEF1", "#FBEFEA", "#EEEAF2"
GOLD_L = "#F6F1E2"

plt.rcParams.update({
    "font.family": "sans-serif",
    "font.sans-serif": ["Helvetica Neue", "Helvetica", "Arial", "DejaVu Sans"],
    "text.color": CHAR, "figure.facecolor": WHITE, "savefig.facecolor": WHITE,
})
SERIF = ["Cambria", "Georgia", "Times New Roman", "DejaVu Serif"]


def rbox(ax, x, y, w, h, edge, face=WHITE, lw=1.7, z=3, r=0.09):
    ax.add_patch(FancyBboxPatch((x, y), w, h,
                                boxstyle=f"round,pad=0,rounding_size={r}",
                                facecolor=face, edgecolor=edge, lw=lw, zorder=z))


def check(ax, x, y, col, s=0.05):
    ax.plot([x-s, x-0.2*s, x+1.1*s], [y-0.2*s, y-1.1*s, y+0.9*s], color=col,
            lw=1.7, solid_capstyle="round", zorder=6)


def todo(ax, x, y, col):
    ax.add_patch(Circle((x, y), 0.052, facecolor=WHITE, edgecolor=col,
                        lw=1.4, zorder=6))


def chip(ax, xr, y, txt, col, filled=True, fs=7.6):
    tw = 0.0155*fs*len(txt) + 0.28
    rbox(ax, xr-tw, y-0.135, tw, 0.29, col, col if filled else WHITE,
         lw=1.2, z=5, r=0.13)
    ax.text(xr-tw/2, y+0.005, txt, fontsize=fs, fontweight="bold",
            color=WHITE if filled else col, ha="center", va="center", zorder=6)


def arrowp(ax, p0, p1, color=CHAR, lw=2.0, ms=13, z=5):
    ax.add_patch(FancyArrowPatch(p0, p1, arrowstyle="-|>", mutation_scale=ms,
                                 lw=lw, color=color, zorder=z, shrinkA=1, shrinkB=1))


# ---------------------------------------------------------------- content
PHASES = [
    dict(tag="PHASE 1", head="The thesis", col=FOREST, colL=FOREST_L,
         status="COMPLETE", filled=True, frac=1.00, when="submitted · Jul 2026",
         q="Does the model reproduce sub-surface\ntemperature at a point?",
         items=[
             (1, "per-site $K_d$: 4.60 / 7.08\n(misfit 1.09 to 1.00, 0.89 to 0.40 K)"),
             (1, "1500-draw bootstrap, tail 0.031\nMCMC ordering 99.2%"),
             (1, "AICc: A17 −23.2, A15 +2.9\nstated honestly, not hidden"),
             (1, "held-out + Diviner surface\nclosure, both out-of-sample"),
             (1, "error budget audited to source\n(±1.88 / ±3.88, χ conditional)"),
         ],
         val="scored against Apollo HFE · 23 deep sensors",
         deliv="two calibrated ground-truth anchors"),
    dict(tag="PHASE 2", head="Terrain at the Apollo sites", col=TEAL, colL=TEAL_L,
         status="COMPLETE", filled=True, frac=1.00, when="AOGS 2026",
         q="How much does real terrain\nchange the answer?",
         items=[
             (1, "DEM horizon algorithm built\n(16 ppd, 90 azimuths)"),
             (1, "applied at both sites: 14.0° / 10.1°\ninsolation −1.16% / −0.18%"),
             (1, "re-retrieval under shadowing:\n$K_d$ 4.60 to 1.88, 7.08 to 9.69"),
             (1, "650-run density study — density\nsets conductivity, not $c_p$"),
             (1, "layered physics transfers between\nsites (2.31–3.76 to 0.36–0.90 K)"),
         ],
         val="two sites only — deliberately not yet global",
         deliv="a terrain-aware, layered retrieval"),
    dict(tag="PHASE 3", head="Go global", col=GOLD, colL=GOLD_L,
         status="NEXT", filled=True, frac=0.05, when="year 1–2",
         q="Does it hold at many points,\nnot just two?",
         items=[
             (0, "tile the solver over the DEM grid\n(one column ≈ 1 s, so feasible)"),
             (0, "Moon-wide horizons, beyond the\ntwo Apollo neighbourhoods"),
             (0, "sub-surface $T(z)$ everywhere,\nto annual-wave depth"),
             (0, "validate against Diviner global\nbrightness composites"),
             (0, "publish the gridded product"),
         ],
         val="to be scored against Diviner global composites",
         deliv="a validated Moon-wide temperature map"),
    dict(tag="PHASE 4", head="TSUKIMI coupling + ice", col=CORAL, colL=CORAL_L,
         status="PLANNED", filled=False, frac=0.0, when="year 2–3",
         q="Where can subsurface ice\nactually survive?",
         items=[
             (0, "couple $T(z)$ into the TSUKIMI\nradiative-transfer simulator (NICT)"),
             (0, "THz brightness-temperature\nforward model for sounding"),
             (0, "cold traps and permanently\nshadowed regions treated explicitly"),
             (0, "ice stability against depth from\nthe sub-surface field"),
         ],
         val="to be tested against THz observations",
         deliv="an ice-survivability map"),
    dict(tag="PHASE 5", head="Model physics upgrades", col=PLUM, colL=PLUM_L,
         status="HORIZON", filled=False, frac=0.0, when="year 3+",
         q="What would the next-generation\nregolith model add?",
         items=[
             (0, "depth-varying $H(z)$ compaction\n— moderate / medium"),
             (0, "$\\varepsilon(T)$ emissivity for cold PSRs\n— low / medium"),
             (0, "vapor diffusion + latent heat\n— high / high, genuinely new"),
             (0, "doctoral thesis, written from\nthe running system"),
         ],
         val="each weighed by difficulty and impact first",
         deliv="next-generation regolith model"),
]


# ============================================================ MASTER CHART
def master():
    W, H, DPI = 15.2, 7.5, 200
    fig = plt.figure(figsize=(W, H), dpi=DPI)
    ax = fig.add_axes([0, 0, 1, 1]); ax.set_xlim(0, W); ax.set_ylim(0, H); ax.axis("off")

    n = len(PHASES)
    CW_, GAP = 2.72, 0.30
    X0 = (W - (n*CW_ + (n-1)*GAP)) / 2
    CX = [X0 + i*(CW_+GAP) for i in range(n)]
    CY_, CH_, BAND = 1.34, 5.58, 0.56

    for P, x in zip(PHASES, CX):
        col, colL = P["col"], P["colL"]
        rbox(ax, x, CY_, CW_, CH_, col, WHITE, lw=1.8)
        hb = 0.88
        ax.add_patch(FancyBboxPatch((x, CY_+CH_-hb), CW_, hb,
                                    boxstyle="round,pad=0,rounding_size=0.09",
                                    facecolor=colL, edgecolor="none", zorder=4))
        ax.add_patch(Rectangle((x+0.02, CY_+CH_-hb), CW_-0.04, hb/2,
                               facecolor=colL, edgecolor="none", zorder=4))
        ax.text(x+0.20, CY_+CH_-0.26, P["tag"], fontsize=8.6, fontweight="bold",
                color=col, va="center", zorder=6)
        chip(ax, x+CW_-0.15, CY_+CH_-0.26, P["status"], col, P["filled"])
        ax.text(x+0.20, CY_+CH_-0.60, P["head"], fontsize=11.4, fontweight="bold",
                color=CHAR, va="center", zorder=6)

        pb_y = CY_+CH_-hb-0.15
        ax.add_patch(Rectangle((x+0.20, pb_y), CW_-0.76, 0.072, facecolor=GRID,
                               edgecolor="none", zorder=5))
        if P["frac"] > 0:
            ax.add_patch(Rectangle((x+0.20, pb_y), (CW_-0.76)*P["frac"], 0.072,
                                   facecolor=col, edgecolor="none", zorder=6))
        ax.text(x+CW_-0.46, pb_y+0.036, f"{int(P['frac']*100)}%", fontsize=7.8,
                fontweight="bold", color=col, va="center", zorder=6)

        ax.text(x+0.20, pb_y-0.20, P["q"], fontsize=8.4, color=DIM,
                style="italic", va="top", zorder=5, linespacing=1.3)
        yy = pb_y-0.78
        for done, txt in P["items"]:
            (check if done else todo)(ax, x+0.30, yy+0.01, col)
            ax.text(x+0.48, yy, txt, fontsize=8.1, color=CHAR, va="center",
                    zorder=5, linespacing=1.25)
            yy -= 0.38 + 0.23*txt.count("\n")

        ax.plot([x+0.18, x+CW_-0.18], [CY_+BAND+0.38]*2, color=GRID, lw=1.0, zorder=4)
        ax.text(x+CW_/2, CY_+BAND+0.20, P["val"], fontsize=7.4, color=DIM,
                ha="center", va="center", zorder=5, style="italic")
        ax.add_patch(FancyBboxPatch((x, CY_), CW_, BAND,
                                    boxstyle="round,pad=0,rounding_size=0.09",
                                    facecolor=colL, edgecolor="none", zorder=4))
        ax.text(x+CW_/2, CY_+0.385, "DELIVERABLE", fontsize=7.0, fontweight="bold",
                color=col, ha="center", va="center", zorder=5)
        ax.text(x+CW_/2, CY_+0.165, P["deliv"], fontsize=8.8, fontweight="bold",
                color=CHAR, ha="center", va="center", zorder=5)

    for i in range(n-1):
        arrowp(ax, (CX[i]+CW_+0.03, CY_+CH_-0.43), (CX[i+1]-0.03, CY_+CH_-0.43),
               ms=12, lw=1.9)

    # the line between what exists and what is proposed
    xd = (CX[1]+CW_+CX[2])/2
    ax.plot([xd, xd], [CY_-0.62, CY_+CH_+0.26], color=DIM, lw=1.1,
            ls=(0, (3, 3)), zorder=1)
    ax.text(xd-0.12, CY_+CH_+0.42, "DELIVERED", fontsize=9.2, fontweight="bold",
            color=FOREST, ha="right", va="center")
    ax.text(xd+0.12, CY_+CH_+0.42, "PROPOSED", fontsize=9.2, fontweight="bold",
            color=DIM, ha="left", va="center")

    ty = 0.60
    ax.annotate("", xy=(CX[-1]+CW_, ty), xytext=(CX[0], ty),
                arrowprops=dict(arrowstyle="-|>", color=DIM, lw=1.7))
    for P, x in zip(PHASES, CX):
        cx = x + CW_/2
        ax.plot([cx], [ty], marker="D", ms=6.5, color=P["col"], mec=WHITE,
                mew=1.2, zorder=6)
        ax.text(cx, ty-0.25, P["when"], fontsize=8.2, color=P["col"],
                fontweight="bold", ha="center")

    yF = CY_ - 0.17
    ax.plot([CX[4]+CW_/2]*2, [CY_-0.02, yF], color=PLUM, lw=1.3,
            ls=(0, (4, 3)), zorder=2)
    ax.plot([CX[2]+CW_/2, CX[4]+CW_/2], [yF]*2, color=PLUM, lw=1.3,
            ls=(0, (4, 3)), zorder=2)
    arrowp(ax, (CX[2]+CW_/2, yF), (CX[2]+CW_/2, CY_-0.02), color=PLUM,
           lw=1.3, ms=10, z=2)
    ax.text((CX[2]+CX[4]+CW_)/2, yF, "physics upgrades re-run the global products",
            fontsize=8.0, color=PLUM, style="italic", ha="center", va="center",
            zorder=3, bbox=dict(boxstyle="round,pad=0.20", facecolor=WHITE,
                                edgecolor="none"))

    fig.savefig(OUT/"study_phases_flow.png", dpi=DPI)
    fig.savefig(OUT/"study_phases_flow@600.png", dpi=600)
    plt.close(fig)
    print("  study_phases_flow.png")


# ============================================================ SLIDE FRAME
SW, SH, SDPI = 13.333, 7.5, 150
MX, BX = 0.72, 7.35


def slide(P, idx, kicker, title, take, evidence):
    fig = plt.figure(figsize=(SW, SH), dpi=SDPI)
    ax = fig.add_axes([0, 0, 1, 1]); ax.set_xlim(0, SW); ax.set_ylim(0, SH); ax.axis("off")
    ax.text(MX, SH-0.44, kicker.upper(), fontsize=11, fontweight="bold",
            color=P["col"], va="center")
    ax.text(MX, SH-0.98, title, fontsize=25, fontweight="bold", color=CHAR,
            va="center", family=SERIF)
    ax.text(MX, SH-1.50, take, fontsize=13, color=DIM, va="center")
    ax.plot([MX, SW-MX], [SH-1.80]*2, color=GRID, lw=1.2)
    chip(ax, SW-MX, SH-0.44, P["status"], P["col"], P["filled"], fs=9.0)

    col, x, w, top = P["col"], MX, 5.9, 5.45
    ax.text(x, top, P["q"].replace("\n", " "), fontsize=11.5, color=DIM,
            style="italic", va="center")
    yy = top - 0.66
    for done, txt in P["items"]:
        (check if done else todo)(ax, x+0.14, yy+0.01, col)
        ax.text(x+0.40, yy, txt.replace("\n", " "), fontsize=9.8, color=CHAR,
                va="center", zorder=5)
        yy -= 0.54
    ax.plot([x, x+w], [yy+0.08]*2, color=GRID, lw=1.0)
    ax.text(x, yy-0.18, P["val"], fontsize=9.5, color=DIM, style="italic", va="center")
    rbox(ax, x, yy-0.98, w, 0.62, col, P["colL"], lw=1.4)
    ax.text(x+0.24, yy-0.55, "DELIVERABLE", fontsize=8.4, fontweight="bold",
            color=col, va="center", zorder=5)
    ax.text(x+0.24, yy-0.80, P["deliv"], fontsize=11.5, fontweight="bold",
            color=CHAR, va="center", zorder=5)

    evidence(fig, ax, P)
    fig.savefig(OUT/f"phase{idx}_slide.png", dpi=SDPI)
    plt.close(fig)
    print(f"  phase{idx}_slide.png")


def ev1(fig, ax, P):
    ax.text(BX, 5.45, "WHERE IT LANDED", fontsize=10, fontweight="bold", color=P["col"])
    axb = fig.add_axes([BX/SW, 0.425, 5.0/SW, 0.205])
    for y, v, c, nm in [(1, 4.60, FOREST, "Apollo 15"), (0, 7.08, CORAL, "Apollo 17")]:
        axb.barh([y], [v], height=0.52, color=c)
        axb.text(v-0.12, y, f"{v:.2f}", ha="right", va="center", fontsize=12,
                 fontweight="bold", color=WHITE)
        axb.text(0.14, y, nm, fontsize=10, color=WHITE, va="center", fontweight="bold")
    axb.axvline(3.4, color=DIM, lw=1.4, ls=(0, (4, 3)))
    axb.text(3.55, 1.80, "global 3.4", fontsize=9, color=DIM, ha="left")
    axb.set_xlim(0, 8.6); axb.set_ylim(-0.55, 2.15); axb.axis("off")
    for i, (t, c) in enumerate([("bootstrap tail 0.031", FOREST),
                                ("MCMC ordering 99.2%", TEAL),
                                ("AICc: A17 −23.2 · A15 +2.9", CORAL)]):
        rbox(ax, BX, 2.42-i*0.52, 4.9, 0.40, c, WHITE, lw=1.3, r=0.12)
        ax.add_patch(Circle((BX+0.26, 2.62-i*0.52), 0.05, color=c, zorder=6))
        ax.text(BX+0.48, 2.62-i*0.52, t, fontsize=10, color=CHAR, va="center", zorder=6)
    ax.text(BX, 0.66, "on the slide, not hidden: Apollo 15 alone does not justify\n"
                      "a separate fit — the case there rests on the interval",
            fontsize=9.3, color=DIM, style="italic", va="center", linespacing=1.35)


def ev2(fig, ax, P):
    ax.text(BX, 5.45, "WHAT TERRAIN DOES TO THE ANSWER", fontsize=10,
            fontweight="bold", color=P["col"])
    for i, (nm, a, b, c, dl) in enumerate([("Apollo 15", 4.60, 1.88, FOREST, "−2.72"),
                                           ("Apollo 17", 7.08, 9.69, CORAL, "+2.61")]):
        y = 4.66 - i*1.00
        ax.text(BX, y+0.26, nm, fontsize=10.5, fontweight="bold", color=c)
        ax.text(BX+0.05, y-0.16, f"{a:.2f}", fontsize=15, fontweight="bold",
                color=DIM, va="center")
        arrowp(ax, (BX+0.78, y-0.14), (BX+1.46, y-0.14), color=c, lw=1.8, ms=12)
        ax.text(BX+1.60, y-0.16, f"{b:.2f}", fontsize=15, fontweight="bold",
                color=c, va="center")
        ax.text(BX+2.45, y-0.16, f"{dl} mW m⁻¹ K⁻¹", fontsize=9.5, color=DIM, va="center")
        ax.text(BX+2.45, y+0.16, "flat ground to real horizon", fontsize=8.4,
                color=DIM, va="center", style="italic")
    ax.plot([BX, BX+4.9], [2.86]*2, color=GRID, lw=1.0)
    ax.text(BX, 2.52, "the two sites move in OPPOSITE directions —\n"
                      "terrain cannot be averaged away",
            fontsize=10, color=CHAR, va="center", linespacing=1.4, fontweight="bold")
    for i, (t, c) in enumerate([("sky-view factor 0.985 / 0.991", TEAL),
                                ("adding IR self-heating made the fit worse", DIM)]):
        rbox(ax, BX, 1.46-i*0.52, 4.9, 0.40, c, WHITE, lw=1.2, r=0.12)
        ax.add_patch(Circle((BX+0.26, 1.66-i*0.52), 0.05, color=c, zorder=6))
        ax.text(BX+0.48, 1.66-i*0.52, t, fontsize=9.6, color=CHAR, va="center", zorder=6)
    ax.text(BX, 0.58, "presented at AOGS 2026 — built and tested, not proposed",
            fontsize=9.3, color=DIM, style="italic", va="center")


def ev3(fig, ax, P):
    ax.text(BX, 5.45, "WHAT REMAINS", fontsize=10, fontweight="bold", color=P["col"])
    for i, (h, s) in enumerate([("tile the DEM grid", "horizons everywhere"),
                                ("Moon-wide $T(z)$", "to annual-wave depth"),
                                ("Diviner validation", "global brightness")]):
        y = 4.62 - i*1.02
        rbox(ax, BX, y, 4.9, 0.78, P["col"], P["colL"], lw=1.5)
        ax.text(BX+0.26, y+0.51, h, fontsize=11, fontweight="bold", color=CHAR,
                va="center", zorder=6)
        ax.text(BX+0.26, y+0.24, s, fontsize=9, color=DIM, va="center", zorder=6)
        if i < 2:
            arrowp(ax, (BX+2.45, y-0.02), (BX+2.45, y-0.22), color=P["col"], ms=11, lw=1.6)
    rbox(ax, BX, 1.24, 4.9, 0.88, P["col"], WHITE, lw=1.4)
    ax.text(BX+0.26, 1.88, "why it is affordable", fontsize=9.5, fontweight="bold",
            color=P["col"], va="center", zorder=6)
    ax.text(BX+0.26, 1.54, "one column ≈ 1 s — the flux-anchored solver is\n"
                           "≈ 2500× faster than brute force",
            fontsize=9.6, color=CHAR, va="center", zorder=6, linespacing=1.35)
    ax.text(BX, 0.68, "the DEM machinery already exists; this phase is scale,\n"
                      "not new physics",
            fontsize=9.3, color=DIM, style="italic", va="center", linespacing=1.35)


def ev4(fig, ax, P):
    ax.text(BX, 5.45, "THE CHAIN", fontsize=10, fontweight="bold", color=P["col"])
    for i, (h, s, c, cl) in enumerate([
            ("sub-surface $T(z)$ field", "delivered by Phase 3", GOLD, GOLD_L),
            ("TSUKIMI radiative transfer", "NICT terahertz simulator", CORAL, CORAL_L),
            ("THz brightness temperature", "what a sounder would see", CORAL, CORAL_L),
            ("ice-survivability map", "cold traps + PSRs explicit", FOREST, FOREST_L)]):
        y = 4.55 - i*1.02
        rbox(ax, BX, y, 4.9, 0.78, c, cl, lw=1.5)
        ax.text(BX+0.26, y+0.51, h, fontsize=11, fontweight="bold", color=CHAR,
                va="center", zorder=6)
        ax.text(BX+0.26, y+0.24, s, fontsize=9, color=DIM, va="center", zorder=6)
        if i < 3:
            arrowp(ax, (BX+2.45, y-0.02), (BX+2.45, y-0.22), color=P["col"], ms=11, lw=1.6)
    ax.text(BX, 0.66, "THz emission originates below the diurnal skin —\n"
                      "exactly the region this model was built to resolve",
            fontsize=9.3, color=DIM, style="italic", va="center", linespacing=1.35)


def ev5(fig, ax, P):
    ax.text(BX, 5.45, "WEIGHED, NOT WISHED", fontsize=10, fontweight="bold", color=P["col"])
    axs = fig.add_axes([(BX+0.45)/SW, 0.225, 4.1/SW, 0.42])
    for xd, yi, c in [(1.0, 1.0, TEAL), (0.0, 1.0, FOREST), (2.0, 2.0, CORAL)]:
        axs.plot([xd], [yi], "o", ms=13, color=c, mec=WHITE, mew=1.6, zorder=5)
    axs.annotate("$H(z)$ compaction", (1.0, 1.0), (1.0, 0.58), fontsize=9.5,
                 ha="center", color=CHAR)
    axs.annotate("$\\varepsilon(T)$ for PSRs", (0.0, 1.0), (0.05, 1.40),
                 fontsize=9.5, ha="center", color=CHAR)
    axs.annotate("vapor diffusion\n+ latent heat", (2.0, 2.0), (1.92, 1.30),
                 fontsize=9.5, ha="center", color=CHAR, linespacing=1.25)
    axs.set_xticks([0, 1, 2]); axs.set_xticklabels(["low", "moderate", "high"], fontsize=9)
    axs.set_yticks([1, 2]); axs.set_yticklabels(["medium", "high"], fontsize=9)
    axs.set_xlim(-0.55, 2.55); axs.set_ylim(0.35, 2.45)
    axs.set_xlabel("implementation difficulty", fontsize=9.5)
    axs.set_ylabel("scientific impact", fontsize=9.5)
    for s in ("top", "right"):
        axs.spines[s].set_visible(False)
    axs.grid(color=GRID, lw=0.7); axs.set_axisbelow(True)
    ax.text(BX, 0.85, "the vapor-diffusion term is genuinely new physics — high\n"
                      "risk, and precisely why it is scheduled last",
            fontsize=9.3, color=DIM, style="italic", va="center", linespacing=1.35)


SLIDES = [
    (0, 1, "Study phases · Phase 1 · complete",
     "The thesis: two ground-truth anchors, delivered",
     "Both boreholes reproduced, every claim stress-tested, and the limits "
     "stated honestly.", ev1),
    (1, 2, "Study phases · Phase 2 · complete",
     "Real terrain, at the two sites we can check",
     "The DEM machinery is built and applied where ground truth exists — and "
     "terrain turns out to matter a great deal.", ev2),
    (2, 3, "Study phases · Phase 3 · next",
     "From two neighbourhoods to the whole Moon",
     "Same physics, same solver. What remains is scale, and the solver already "
     "makes it affordable.", ev3),
    (3, 4, "Study phases · Phase 4 · planned",
     "Coupling to TSUKIMI: from temperature to ice",
     "The temperature field becomes terahertz brightness, and finally an "
     "ice-survivability map.", ev4),
    (4, 5, "Study phases · Phase 5 · horizon",
     "Beyond: the next-generation regolith model",
     "Three physics upgrades, each weighed by difficulty and scientific impact "
     "before any is attempted.", ev5),
]

if __name__ == "__main__":
    master()
    for pi, idx, k, t, tk, ev in SLIDES:
        slide(PHASES[pi], idx, k, t, tk, ev)
    print("done ->", OUT)
