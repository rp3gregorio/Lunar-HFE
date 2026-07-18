#!/usr/bin/env python
"""AOGS poster — single-source layout spec + preview renderer.

Classic boxed conference-poster grammar (user reference: EMS-2023 style):
logo header + centered title + conference line, then TWO columns of
bordered section boxes with teal pill headers and bold "Figure N."
captions. Emits layout.json (consumed by build_pptx.py) and preview.png.
All geometry in mm on an A0 portrait page (841 x 1189). Content is
cursor-stacked inside each box; a pairwise assert guards the rest.
Numbers come from poster_numbers.tex (audit-verified 2026-07-12).
"""
import json, textwrap
from PIL import Image
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import fitz

import os; SCRATCH = os.path.dirname(os.path.abspath(__file__))
FIGS = f"{SCRATCH}/figs"
# canva_build now lives at deliverables/documents/aogs/poster/canva_build → 5 up to repo root
REPO = os.path.abspath(f"{SCRATCH}/../../../../..")
POSTER = f"{REPO}/deliverables/documents/aogs/poster"

# render every figure panel from its vector PDF at print resolution (3600 px wide)
os.makedirs(FIGS, exist_ok=True)
SOURCES = {
    "flowchart": f"{REPO}/deliverables/documents/aogs/talk_figures/aogs_pipeline_flowchart.pdf",
    "schematic": f"{REPO}/deliverables/documents/aogs/talk_figures/aogs_model_schematic.pdf",
    **{k: f"{POSTER}/figures/{k}.pdf"
       for k in ["poster_sites", "poster_profiles", "poster_density",
                 "poster_leverage", "poster_transfer"]},
}
for name, pdf in SOURCES.items():
    pg = fitz.open(pdf)[0]
    pix = pg.get_pixmap(matrix=fitz.Matrix(3600 / pg.rect.width, 3600 / pg.rect.width), alpha=False)
    pix.save(f"{FIGS}/{name}.png")

TEAL, CORAL, FOREST = "#2A6478", "#B85B3A", "#3D6E4A"
CHAR, CREAM, TINT, MUT = "#2A2520", "#F7F5F1", "#E9EFF2", "#6B6259"
PAGE_W, PAGE_H, M = 841, 1189, 16
CW = 398                       # column width
LX, RX = M, 427                # column x
COL_TOP, COL_BOT = 146, 1150   # column band
PAD = 8                        # box inner padding
GAP = 9                        # gap between boxes

def aspect(p):
    im = Image.open(p); return im.size[1] / im.size[0]

F = {k: f"{FIGS}/{k}.png" for k in
     ["poster_sites", "poster_profiles", "poster_density", "poster_leverage",
      "poster_transfer", "flowchart", "schematic"]}
A = {k: aspect(v) for k, v in F.items()}

E = []  # elements
def add(kind, x, y, w, h, layer=0, **kw):
    E.append(dict(kind=kind, x=x, y=y, w=w, h=h, layer=layer, **kw))
    return y + h

class Box:
    """Bordered section box with a centered teal pill header.

    Content is cursor-stacked via .image/.text/.table; close() draws the
    border rect (layer -1, so builders z-order it behind the content)."""
    def __init__(self, x, y_top, title, pill_frac=0.6):
        self.x, self.y0 = x, y_top
        pw = pill_frac * CW
        add("rect", x + (CW - pw) / 2, y_top + 5, pw, 15, fill=TEAL,
            rounded=True, layer=-1)
        add("text", x + (CW - pw) / 2, y_top + 7.2, pw, 11, text=title,
            size=28, bold=True, color="#FFFFFF", align="center")
        self.y = y_top + 5 + 15 + 5
    def image(self, key, w):
        h = w * A[key]
        self.y = add("image", self.x + (CW - w) / 2, self.y, w, h,
                     path=F[key]) + 4
    def image_pair(self, key1, w1, key2, w2):
        h1, h2 = w1 * A[key1], w2 * A[key2]
        gap = CW - 2 * PAD - w1 - w2
        add("image", self.x + PAD, self.y, w1, h1, path=F[key1])
        add("image", self.x + PAD + w1 + gap, self.y, w2, h2, path=F[key2])
        self.y += max(h1, h2) + 4
    def text(self, txt, h, size=22, **kw):
        self.y = add("text", self.x + PAD, self.y, CW - 2 * PAD, h, text=txt,
                     size=size, color=kw.pop("color", CHAR),
                     align="left", **kw) + 4
    def table(self, rows, col_w, h):
        self.y = add("table", self.x + PAD, self.y, CW - 2 * PAD, h,
                     rows=rows, col_w=col_w) + 4
    def close(self):
        h = self.y - self.y0 + 2
        # layer -2: the box border must sit BELOW the pill/tile rects
        # (layer -1), or its white fill covers them
        add("rect", self.x, self.y0, CW, h, fill="#FFFFFF", line=TEAL,
            lw=0.6, rounded=True, layer=-2)
        return self.y0 + h + GAP

# ---------------- header (logos + title + conference line) ----------------
for lx in (M, PAGE_W - M - 58):
    add("rect", lx, 18, 58, 58, fill=TINT, rounded=True, layer=-1)
    add("text", lx + 4, 42, 50, 10, text="[logo]", size=18, color=MUT,
        align="center")
add("text", 90, 16, PAGE_W - 180, 50,
    text="Discrete Layer Thermal Modeling of Lunar Landing Sites\nwith Topographic Shadowing",
    size=60, bold=True, color=CHAR, align="center")
# AOGS rule: presenter's name UNDERLINED + bold. The whole line is bold;
# runs carry the underline flag so only the presenter is underlined.
add("text", 90, 72, PAGE_W - 180, 12,
    text="Ramón III P. Gregorio¹ · Richard Larsson¹ · Yasuko Kasai²",
    runs=[["Ramón III P. Gregorio¹", True],
          [" · Richard Larsson¹ · Yasuko Kasai²", False]],
    size=26, bold=True, color=CHAR, align="center")
add("text", 90, 86, PAGE_W - 180, 18,
    text=("¹Institute of Science Tokyo, Japan\n"
          "²Institute of Science Tokyo, Transdisciplinary Science & Engineering, "
          "School of Environment and Society, Japan"),
    size=17, color=CHAR, align="center")
add("text", 90, 107, PAGE_W - 180, 10,
    text="rp3gregorio@gmail.com · Abstract ID: [ID] · Poster session: [window]",
    size=17, color=MUT, align="center")
add("text", 90, 121, PAGE_W - 180, 11,
    text="AOGS 2026 — 23rd Annual Meeting of the Asia Oceania Geosciences Society · [dates] · [venue]",
    size=22, bold=True, color=TEAL, align="center")
add("rect", M, 138, PAGE_W - 2 * M, 0.8, fill=TEAL, layer=-1)

# ---------------- left column ----------------
b = Box(LX, COL_TOP, "Introduction")
b.text(("The only in-situ subsurface ground truth on the Moon: Apollo 15/17 Heat Flow "
        "Experiment temperatures (Langseth et al. 1976; Nagihara et al. 2018).\n"
        "We add two advances to a certified flux-anchored 1-D solver: discrete density "
        "layers (Hayne et al. 2017 form — no new constants) and ray-traced horizon "
        "shadowing (LOLA DEM; Smith et al. 2010).\n"
        "650 layered configurations, each solved to certified periodic equilibrium and "
        "scored against the deep sensors.\n"
        "Output: thermal predictions for landing-site assessment and physical "
        "constraints on regolith properties."), 86, bullets=True)
y = b.close()

b = Box(LX, y, "The model & methods")
b.image("schematic", 296)
b.text(
    "Governing 1-D heat diffusion (depth- and temperature-dependent properties):\n"
    "     ρ(z) c_p(T) ∂T/∂t  =  ∂/∂z [ K(T,z) ∂T/∂z ]\n"
    "Conductivity — Hayne et al. (2017), contact + radiative:\n"
    "     K(T,z) = K_c(z)·[1 + χ(T/350 K)³] ,   K_c(z) = K_d − (K_d − K_s) e^(−z/H)\n"
    "     K_s = 7.4×10⁻⁴ W m⁻¹ K⁻¹ ,   H = 6 cm ,   χ = 2.7\n"
    "Boundaries — surface: (1−A)·S_shadowed(t) = ε σ T_s⁴ + conduction ;   base:\n"
    "     K ∂T/∂z = Q_b = 21 / 16 mW m⁻² (A15 / A17; Langseth et al. 1976)\n"
    "Flux-anchored solver — anchor ⟨T⟩ below the rectification zone (z₀ = 55 cm),\n"
    "     where  d⟨T⟩/dz = (Q_b − u_rect)/K :  periodic equilibrium in ~0.6 s/solve,\n"
    "     ~20× faster than brute-force time-stepping.\n"
    "Data — HFE deep-sensor equilibria: restored 1971–77 record, quiet late-mission\n"
    "     window; sensors above 80 cm excluded (borestem conducts the surface wave down).",
    82, size=16)
y = b.close()

b = Box(LX, y, "The pipeline — 650 configurations")
b.image("flowchart", 190)
y = b.close()

b = Box(LX, y, "Sites, horizons, the lost sunlight")
b.image("poster_sites", 238)
b.text(("Figure 1.  DEM relief and ray-traced horizons; dotted = the sun's path over a "
        "lunation, squares = terrain-blocked. The Apennine front raises the A15 horizon "
        "to 14.0° (1.16% insolation loss); the North Massif gives A17 a 10.1° peak "
        "(0.18% — a lower bound at 16 ppd)."), 24, size=17)
y = b.close()
assert y - GAP <= COL_BOT, f"left column overflows: {y - GAP:.0f} > {COL_BOT}"
print(f"left column ends {y - GAP:.0f} / {COL_BOT}")

# ---------------- right column ----------------
b = Box(RX, COL_TOP, "Validation against Apollo HFE")
b.image("poster_profiles", 286)
b.table([["RMSE at deep sensors (K)", "homog.", "Hayne cont.", "best cp", "best coupled"],
         ["Apollo 15", "2.31", "2.03", "1.74", "0.90"],
         ["Apollo 17", "3.76", "0.54", "0.39", "0.36"]],
        [118, 58, 72, 60, 74], 42)
b.text(("Figure 2 + table.  Mean T(z) against the HFE deep sensors. All 650 configurations "
        "converged on the anchor criterion; the winning configurations close the flux budget "
        "to ≤ 0.7% and agree to ≤ 35 mK when re-run at the production spin-up (n = 96)."), 24,
       size=17)
y = b.close()

b = Box(RX, y, "Sensitivity — the lever is conductivity")
b.image("poster_leverage", 320)
b.text(("Figure 3.  RMSE spread of all 162 configurations per branch (dashed = Hayne "
        "continuous): heat capacity alone moves the fit ≤ 0.7 K; density, through the "
        "conductivity it implies, spans ~4 K. Best boundaries sit high (z₂ = 30 cm)."), 24,
       size=17)
ty = b.y
tw = (CW - 2 * PAD - 10) / 2
for dx, big, sub in [(0, "2.6×", "vs homogeneous at Apollo 15\n0.90 K vs 2.31 K"),
                     (tw + 10, "10×", "vs homogeneous at Apollo 17\n0.36 K vs 3.76 K")]:
    add("rect", RX + PAD + dx, ty, tw, 52, fill=TINT, rounded=True, layer=-1)
    add("text", RX + PAD + dx + 4, ty + 3, tw - 8, 20, text=big, size=46,
        bold=True, color=TEAL, align="center")
    add("text", RX + PAD + dx + 4, ty + 27, tw - 8, 22, text=sub, size=17,
        color=CHAR, align="center")
b.y = ty + 52 + 4
y = b.close()

b = Box(RX, y, "What transfers, what the regolith prefers")
b.image_pair("poster_density", 224, "poster_transfer", 116)
b.text(("Figure 4.  Left: retrieved columns — both sites prefer a surface denser than "
        "Hayne et al. (1300–1500 vs 1100 kg m⁻³). Right: structures moved across sites "
        "degrade gracefully and still beat homogeneous; the winning triples are degenerate "
        "(13% bootstrap stability at A15) — the robust result is the improvement."), 24,
       size=17)
y = b.close()

b = Box(RX, y, "Conclusions")
b.text(("Topography enters twice, with opposing signs: shadow cooling at the deep sensors "
        "(2.2 K at A15, 0.5 K at A17) vs (1−SVF) terrain-IR warming (+1.3/+0.7 K) — at A17 "
        "the warming wins. Both should be standard practice.\n"
        "A 3-layer column reproduces the HFE record; density matters through the "
        "conductivity it implies, not through heat capacity.\n"
        "Site-specific calibration stays physical: cross-site transfer degrades gracefully "
        "and parameter differences track the known geology — physics, not curve-fitting.\n"
        "The same pipeline extends to landing-site assessment, regolith property "
        "constraints, and any airless body with high-resolution topography."), 84,
       size=19, bullets=True)
b.text(("Caveats — the 16 ppd DEM (~1.9 km/px) under-resolves A17's near massifs, so its "
        "horizons are a lower bound; solar declination is fixed at 0°; the (1−SVF) "
        "terrain-radiation channel is a diagnostic, not yet folded into the fits."),
       22, size=15, italic=True, color=MUT)
y = b.close()
assert y - GAP <= COL_BOT, f"right column overflows: {y - GAP:.0f} > {COL_BOT}"
print(f"right column ends {y - GAP:.0f} / {COL_BOT}")

# ---------------- references (full-width line) ----------------
add("text", M, COL_BOT + 6, PAGE_W - 2 * M, 14, size=13, color=MUT, align="left", text=(
    "References:  [1] Hayne et al., JGR: Planets 122, 2017.  [2] Langseth et al., Proc. Lunar Sci. Conf. 7, 1976.  "
    "[3] Nagihara et al., JGR: Planets 123, 2018.  [4] Saito et al., Adv. Space Res. 40, 2007.  "
    "[5] Smith et al., GRL 37, 2010.      Code + archives: github.com/rp3gregorio/Lunar-HFE"))

# ---------------- overlap guard ----------------
def overlaps(a, b):
    return not (a["x"] + a["w"] <= b["x"] + .1 or b["x"] + b["w"] <= a["x"] + .1 or
                a["y"] + a["h"] <= b["y"] + .1 or b["y"] + b["h"] <= a["y"] + .1)
base = [e for e in E if e["layer"] == 0]
bad = [(base[i]["kind"], base[j]["kind"], round(base[i]["y"]), round(base[j]["y"]))
       for i in range(len(base)) for j in range(i + 1, len(base))
       if overlaps(base[i], base[j])]
assert not bad, f"overlapping elements: {bad}"
print(f"{len(E)} elements, no overlaps")

json.dump(dict(page=[PAGE_W, PAGE_H], elements=E), open(f"{SCRATCH}/layout.json", "w"), indent=1)

# ---------------- preview ----------------
fig = plt.figure(figsize=(PAGE_W / 25.4, PAGE_H / 25.4), dpi=42)
ax = fig.add_axes([0, 0, 1, 1]); ax.set_xlim(0, PAGE_W); ax.set_ylim(PAGE_H, 0); ax.axis("off")
for e in sorted(E, key=lambda e: e["layer"]):
    if e["kind"] == "rect":
        ax.add_patch(mpatches.FancyBboxPatch(
            (e["x"], e["y"]), e["w"], e["h"],
            boxstyle="round,pad=0,rounding_size=3" if e.get("rounded") else "square,pad=0",
            fc=e["fill"], ec=e.get("line", "none"), lw=e.get("lw", 0) * 2.8))
    elif e["kind"] == "image":
        ax.imshow(Image.open(e["path"]), extent=(e["x"], e["x"] + e["w"], e["y"] + e["h"], e["y"]),
                  aspect="auto", zorder=2)
    elif e["kind"] == "table":
        rh = e["h"] / len(e["rows"])
        for r, row in enumerate(e["rows"]):
            cx = e["x"]
            for c, cell in enumerate(row):
                wcell = e["col_w"][c]
                ax.add_patch(mpatches.Rectangle((cx, e["y"] + r * rh), wcell, rh, fc=TINT if r == 0 else "white",
                                                ec=MUT, lw=.5, zorder=2))
                ax.text(cx + wcell / 2, e["y"] + r * rh + rh / 2, cell, size=13, ha="center",
                        va="center", zorder=3, color=CHAR, weight="bold" if r == 0 or c == 0 else "normal")
                cx += wcell
    else:
        cw_mm = 0.185 * e["size"]  # approx char width
        lines = []
        for para in e["text"].split("\n"):
            pre = "•  " if e.get("bullets") else ""
            wrapped = textwrap.wrap(pre + para, max(8, int(e["w"] / cw_mm))) or [""]
            lines += wrapped
        ha = e["align"]; x = dict(left=e["x"], center=e["x"] + e["w"] / 2, right=e["x"] + e["w"])[ha]
        ax.text(x, e["y"] + 1, "\n".join(lines), size=e["size"] * .72, ha=ha, va="top",
                color=e["color"], weight="bold" if e.get("bold") else "normal",
                style="italic" if e.get("italic") else "normal", zorder=3, linespacing=1.15)
fig.savefig(f"{SCRATCH}/preview.png", facecolor="white")
print("preview written")
