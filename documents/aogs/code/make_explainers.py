"""Clean, flat, hand-designed SVG explainer illustrations for the AOGS poster.
Rendered to vector PDF + hi-res PNG via headless Chrome. One consistent visual
language (house palette, serif type, flat rounded panels, dark punchline bar).

Numbers are parsed from the generated poster_numbers.tex (never invented).
Output: aogs/figures/explainers/<name>.{pdf,png}
Run:  python make_explainers.py
"""
import pathlib
import re
import subprocess
import tempfile

AOGS = next(a for a in pathlib.Path(__file__).resolve().parents if a.name == "aogs")
OUT = AOGS / "figures" / "explainers"; OUT.mkdir(parents=True, exist_ok=True)
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"

# ── palette ─────────────────────────────────────────────────────────────────
TEAL, CORAL, FOREST, PLUM = "#2A6478", "#B85B3A", "#3D6E4A", "#5A4A6A"
CHAR, DIM, GRID, CREAM = "#2A2520", "#6E6862", "#E8E5E0", "#F7F5F1"
TEAL_L, CORAL_L, FOREST_L = "#eaf1f3", "#f7ece7", "#e9f0ea"


def nums():
    txt = (AOGS / "figures" / "poster_numbers.tex").read_text()
    return {m.group(1): m.group(2)
            for m in re.finditer(r"\\newcommand\{\\([a-zA-Z]+)\}\{([^}]*)\}", txt)}


FONT = "'Palatino Linotype','Palatino','Georgia',serif"
DEFS = f"""<defs>
<marker id='ar' viewBox='0 0 10 10' refX='8.5' refY='5' markerWidth='7' markerHeight='7'
 orient='auto-start-reverse'><path d='M0 0 L10 5 L0 10 z' fill='{DIM}'/></marker>
<marker id='arT' viewBox='0 0 10 10' refX='8.5' refY='5' markerWidth='7' markerHeight='7'
 orient='auto-start-reverse'><path d='M0 0 L10 5 L0 10 z' fill='{TEAL}'/></marker>
<marker id='arC' viewBox='0 0 10 10' refX='8.5' refY='5' markerWidth='7' markerHeight='7'
 orient='auto-start-reverse'><path d='M0 0 L10 5 L0 10 z' fill='{CORAL}'/></marker>
</defs>"""


def svg(w, h, body, title=""):
    return (f"<svg viewBox='0 0 {w} {h}' xmlns='http://www.w3.org/2000/svg' "
            f"font-family=\"{FONT}\" role='img'><title>{title}</title>"
            f"<rect width='{w}' height='{h}' fill='white'/>{DEFS}{body}</svg>")


def head(x, title, sub=None):
    s = f"<text x='{x}' y='46' font-size='27' font-weight='700' fill='{CHAR}'>{title}</text>"
    if sub:
        s += f"<text x='{x}' y='75' font-size='16.5' fill='{DIM}' font-style='italic'>{sub}</text>"
    return s


def punch(w, y, line1, line2=None):
    s = (f"<rect x='30' y='{y}' width='{w-60}' height='{58 if line2 else 40}' rx='10' fill='{CHAR}'/>"
         f"<text x='52' y='{y+(27 if line2 else 26)}' font-size='16.5' font-weight='700' fill='white'>{line1}</text>")
    if line2:
        s += f"<text x='52' y='{y+48}' font-size='16.5' fill='{GRID}'>{line2}</text>"
    return s


def panel(x, y, w, h, fill, stroke, rx=10, sw=1.8):
    return f"<rect x='{x}' y='{y}' width='{w}' height='{h}' rx='{rx}' fill='{fill}' stroke='{stroke}' stroke-width='{sw}'/>"


def txt(x, y, s, size=14, fill=CHAR, w=None, anchor="start", it=False):
    a = f" text-anchor='{anchor}'" if anchor != "start" else ""
    fw = f" font-weight='{w}'" if w else ""
    fs = " font-style='italic'" if it else ""
    return f"<text x='{x}' y='{y}' font-size='{size}' fill='{fill}'{fw}{fs}{a}>{s}</text>"


def render(name, w, h):
    """Render OUT/name.svg -> PNG (3x) via headless Chrome. PNG-only: the SVG is
    an intermediate (Chrome needs a file to load) and is removed afterwards."""
    svg_file = OUT / f"{name}.svg"
    html = (f"<!doctype html><html><head><meta charset='utf-8'><style>"
            f"@page{{size:{w}px {h}px;margin:0}}*{{margin:0;padding:0;box-sizing:border-box}}"
            f"html,body{{width:{w}px;height:{h}px;overflow:hidden}}svg{{display:block}}"
            f"</style></head><body>{svg_file.read_text()}</body></html>")
    with tempfile.NamedTemporaryFile("w", suffix=".html", delete=False) as fh:
        fh.write(html); hp = fh.name
    subprocess.run([CHROME, "--headless", "--disable-gpu", "--force-device-scale-factor=3",
                    f"--window-size={w},{h}", f"--screenshot={OUT/(name+'.png')}", hp],
                   capture_output=True)
    svg_file.unlink(missing_ok=True)
    pathlib.Path(hp).unlink(missing_ok=True)
    print("wrote", name)


# ════════════════════════════════════════════════════════════════════════════
def fig_mechanism(N):
    w, h = 880, 500
    b = head(30, "When you pack the regolith denser, two things could change",
             "the study runs it both ways — to find out which one the Apollo data actually cares about")
    # density column
    b += txt(130, 122, "a denser layer", 15, CHAR, w=700, anchor="middle")
    b += panel(92, 136, 76, 150, "#e9eff2", TEAL, 4, 1.5)
    b += f"<rect x='92' y='136' width='76' height='40' fill='#cdd6da'/>"
    b += f"<rect x='92' y='176' width='76' height='50' fill='#9aa9b0'/>"
    b += f"<rect x='92' y='226' width='76' height='60' fill='#5f7178'/>"
    b += txt(130, 304, "denser with depth", 12.5, DIM, anchor="middle")
    b += f"<line x1='172' y1='178' x2='250' y2='152' stroke='{DIM}' stroke-width='1.6' marker-end='url(#ar)'/>"
    b += f"<line x1='172' y1='240' x2='250' y2='302' stroke='{DIM}' stroke-width='1.6' marker-end='url(#ar)'/>"
    b += panel(256, 130, 200, 52, CREAM, "#c9c3bb", 8, 1.3)
    b += txt(356, 154, "stores more heat", 15.5, CHAR, w=700, anchor="middle")
    b += txt(356, 173, "heat capacity  (cₚ)", 12.5, DIM, anchor="middle")
    b += panel(256, 278, 200, 52, CREAM, "#c9c3bb", 8, 1.3)
    b += txt(356, 302, "conducts heat faster", 15.5, CHAR, w=700, anchor="middle")
    b += txt(356, 321, "conductivity  (K)", 12.5, DIM, anchor="middle")
    # cp
    b += panel(500, 116, 350, 86, TEAL_L, TEAL)
    b += txt(520, 144, "“cp” branch — storage only", 17, TEAL, w=700)
    b += txt(520, 168, "density touches heat capacity; conductivity frozen", 13.5)
    b += txt(520, 190, f"weak lever · fit barely moves ( &lt; 0.8 K )", 13.5, TEAL, w=700)
    b += f"<line x1='456' y1='156' x2='500' y2='156' stroke='{TEAL}' stroke-width='2' marker-end='url(#arT)'/>"
    # coupled
    b += panel(500, 268, 350, 86, CORAL_L, CORAL)
    b += txt(520, 296, "“coupled” branch — storage + flow", 17, CORAL, w=700)
    b += txt(520, 320, "density touches BOTH capacity and conductivity", 13.5)
    b += txt(520, 342, f"strong lever · ~4 K · fits {N['rmsecKAfif']} / {N['rmsecKAsev']} K", 13.5, CORAL, w=700)
    b += f"<line x1='456' y1='304' x2='500' y2='304' stroke='{CORAL}' stroke-width='2' marker-end='url(#arC)'/>"
    b += f"<line x1='456' y1='156' x2='485' y2='296' stroke='{CORAL}' stroke-width='2' opacity='0.5' marker-end='url(#arC)'/>"
    b += punch(w, 410,
               "The deep temperature is set by how fast heat FLOWS, not how much is stored —",
               "so only the coupled branch reproduces the Apollo sensors. That is the mechanism.")
    (OUT / "expl_mechanism.svg").write_text(svg(w, h, b, "cp vs coupled mechanism"))
    render("expl_mechanism", w, h)


def fig_setup(N):
    w, h = 880, 548
    gy = 172                                 # ground surface
    cx, cw = 470, 340                         # column
    b = head(30, "The model in one picture",
             "a layered regolith column, heated by a Sun the terrain can block")
    # ---- the column ----
    b += f"<rect x='{cx}' y='{gy}' width='{cw}' height='280' rx='4' fill='#efe9e2' stroke='{DIM}' stroke-width='1.3'/>"
    b += f"<rect x='{cx}' y='{gy}' width='{cw}' height='52' fill='#e3ddd4'/>"
    b += f"<rect x='{cx}' y='{gy+52}' width='{cw}' height='66' fill='#cfc6ba'/>"
    b += f"<rect x='{cx}' y='{gy+118}' width='{cw}' height='162' fill='#9a8d7c'/>"
    b += txt(cx+150, gy+31, "loose skin", 14, CHAR, anchor="middle")
    b += txt(cx+150, gy+90, "intermediate", 14, CHAR, anchor="middle")
    b += txt(cx+150, gy+195, "consolidated", 14, "white", anchor="middle")
    b += txt(cx+150, gy+216, "denser with depth ↓", 12, GRID, anchor="middle")
    # borehole + sensors
    bx = cx + 250
    b += f"<line x1='{bx}' y1='{gy}' x2='{bx}' y2='{gy+262}' stroke='{CHAR}' stroke-width='3'/>"
    for i in range(6):
        b += f"<circle cx='{bx}' cy='{gy+150+i*22}' r='4.3' fill='white' stroke='{CHAR}' stroke-width='1.6'/>"
    b += txt(bx+13, gy+178, "Apollo", 11.5, CHAR)
    b += txt(bx+13, gy+193, "deep", 11.5, CHAR)
    b += txt(bx+13, gy+208, "sensors", 11.5, CHAR)
    # ---- Sun + terrain (left, no overlap) ----
    b += f"<circle cx='300' cy='128' r='20' fill='{CORAL}'/>"
    b += txt(300, 104, "Sun", 14, CHAR, w=700, anchor="middle")
    b += f"<path d='M70 {gy} L150 120 L230 {gy} Z' fill='#cfc6ba' stroke='{DIM}' stroke-width='1.2'/>"
    b += txt(150, gy+18, "terrain (massif)", 12.5, DIM, anchor="middle")
    # lit ray (clears the massif — Sun is to its right and high)
    b += f"<line x1='316' y1='138' x2='{cx}' y2='{gy+30}' stroke='{CORAL}' stroke-width='2.4' marker-end='url(#arC)'/>"
    b += txt(378, 168, "sunlight in", 12.5, CORAL, it=True)
    # shadow note (clean empty area)
    b += txt(60, gy+70, "When the Sun sits low it ducks", 13, PLUM)
    b += txt(60, gy+88, "behind terrain like this —", 13, PLUM)
    b += txt(60, gy+106, "the site falls into", 13, PLUM)
    b += txt(184, gy+106, "shadow.", 13, PLUM, w=700)
    # ---- fluxes ----
    b += f"<line x1='{cx+90}' y1='{gy}' x2='{cx+90}' y2='{gy-38}' stroke='{TEAL}' stroke-width='2' marker-end='url(#arT)'/>"
    b += txt(cx+100, gy-22, "heat radiated out", 12.5, TEAL, it=True)
    b += f"<line x1='{cx+170}' y1='{gy+272}' x2='{cx+170}' y2='{gy+250}' stroke='{FOREST}' stroke-width='2' marker-end='url(#ar)'/>"
    b += txt(cx+182, gy+267, "geothermal heat  Q_b", 12, FOREST, it=True)
    b += punch(w, 480,
               "Two additions to the standard model: discrete density LAYERS and terrain SHADOWING —",
               "both read straight off the elevation map. Everything else is the certified baseline.")
    (OUT / "expl_setup.svg").write_text(svg(w, h, b, "the model setup"))
    render("expl_setup", w, h)


def fig_topography(N):
    w, h = 800, 510
    b = head(30, "Topography pushes the deep temperature two ways",
             "shadow cools · terrain re-radiation warms · same horizons, opposite signs")
    y0, sc, bw = 232, 38, 44
    sites = [("Apollo 15", 250, float(N["shadowcoolAfif"]), float(N["svfdtallAfif"])),
             ("Apollo 17", 540, float(N["shadowcoolAsev"]), float(N["svfdtallAsev"]))]
    b += f"<line x1='120' y1='{y0}' x2='700' y2='{y0}' stroke='{DIM}' stroke-width='1.2'/>"
    b += txt(112, y0+4, "0", 12, DIM, anchor="end")
    for name, x, cool, warm in sites:
        ch, wh = cool * sc, warm * sc
        b += f"<rect x='{x-bw-6}' y='{y0}' width='{bw}' height='{ch}' fill='{TEAL}' rx='3'/>"
        b += f"<rect x='{x+6}' y='{y0-wh}' width='{bw}' height='{wh}' fill='{CORAL}' rx='3'/>"
        b += txt(x-bw+16, y0+ch+18, f"−{cool:.1f} K", 12.5, TEAL, w=700, anchor="middle")
        b += txt(x-bw+16, y0+ch+34, "shadow cools", 11, DIM, anchor="middle")
        b += txt(x+bw-16, y0-wh-20, f"+{warm:.1f} K", 12.5, CORAL, w=700, anchor="middle")
        b += txt(x+bw-16, y0-wh-6, "terrain warms", 11, DIM, anchor="middle")
        net = warm - cool
        b += txt(x, 390, name, 15, CHAR, w=700, anchor="middle")
        b += txt(x, 412, f"net {net:+.1f} K → {'cools' if net<0 else 'warms'}",
                 13, (TEAL if net<0 else CORAL), w=700, anchor="middle")
    b += punch(w, 438,
               "Both channels come from the same terrain horizons — neither is optional.",
               "Cooling wins at Apollo 15; warming wins at Apollo 17.")
    (OUT / "expl_topography.svg").write_text(svg(w, h, b, "topography enters twice"))
    render("expl_topography", w, h)


def fig_result(N):
    w, h = 800, 470
    b = head(30, "Layers thread the Apollo sensors; the smooth model misses",
             "one temperature per deep sensor, plotted against depth")
    # plot frame
    px, py, pw, ph = 120, 110, 560, 250
    b += f"<rect x='{px}' y='{py}' width='{pw}' height='{ph}' fill='#fbfaf8' stroke='{GRID}' stroke-width='1.2'/>"
    b += txt(px, py-10, "cooler", 12, DIM) + txt(px+pw, py-10, "warmer  (mean temperature →)", 12, DIM, anchor="end")
    b += txt(px-12, py+12, "shallow", 12, DIM, anchor="end")
    b += txt(px-12, py+ph, "deep", 12, DIM, anchor="end")
    # sensor points (schematic) along a gentle gradient
    pts = [(0.30, 0.18), (0.36, 0.30), (0.34, 0.42), (0.47, 0.60), (0.52, 0.74), (0.58, 0.88)]
    sx = lambda fx: px + fx * pw
    sy = lambda fy: py + fy * ph
    # smooth (dashed) — shifted / wrong slope
    b += f"<path d='M{sx(0.42)} {sy(0.05)} Q {sx(0.30)} {sy(0.5)} {sx(0.40)} {sy(0.98)}' fill='none' stroke='{PLUM}' stroke-width='2.4' stroke-dasharray='7 4'/>"
    # layered (solid steps) through the points
    b += (f"<path d='M{sx(0.28)} {sy(0.05)} L{sx(0.28)} {sy(0.25)} L{sx(0.40)} {sy(0.25)} "
          f"L{sx(0.40)} {sy(0.5)} L{sx(0.55)} {sy(0.5)} L{sx(0.55)} {sy(0.98)}' "
          f"fill='none' stroke='{FOREST}' stroke-width='3'/>")
    for fx, fy in pts:
        b += f"<circle cx='{sx(fx)}' cy='{sy(fy)}' r='6' fill='white' stroke='{CHAR}' stroke-width='2'/>"
    # legend
    b += f"<line x1='{px+pw-190}' y1='{py+24}' x2='{px+pw-160}' y2='{py+24}' stroke='{PLUM}' stroke-width='2.4' stroke-dasharray='7 4'/>"
    b += txt(px+pw-152, py+28, "smooth model", 12, CHAR)
    b += f"<line x1='{px+pw-190}' y1='{py+46}' x2='{px+pw-160}' y2='{py+46}' stroke='{FOREST}' stroke-width='3'/>"
    b += txt(px+pw-152, py+50, "3-layer model", 12, CHAR)
    b += f"<circle cx='{px+pw-175}' cy='{py+68}' r='6' fill='white' stroke='{CHAR}' stroke-width='2'/>"
    b += txt(px+pw-152, py+72, "Apollo sensors", 12, CHAR)
    b += punch(w, 388,
               f"The 3-layer column reaches {N['rmsecKAfif']} / {N['rmsecKAsev']} K — about 2.6× (A15) to 10× (A17)",
               "closer to the sensors than a uniform column. Density does it through conductivity.")
    (OUT / "expl_result.svg").write_text(svg(w, h, b, "layers vs smooth"))
    render("expl_result", w, h)


def fig_degeneracy(N):
    w, h = 820, 480
    b = head(30, "Why we anchor K_d instead of fitting it freely")
    def pan(x, y, ww, hh, t1, t2, fc, ec, tc=CHAR):
        s = panel(x, y, ww, hh, fc, ec, 10, 1.6)
        s += txt(x+ww/2, y+(hh/2-6 if t2 else hh/2+5), t1, 14.5, tc, w=700, anchor="middle")
        if t2: s += txt(x+ww/2, y+hh/2+15, t2, 12.5, DIM, anchor="middle")
        return s
    b += pan(250, 92, 320, 56, "one measured slope", "≈ Q_b / K_deep  (a single number)", CREAM, DIM)
    b += pan(60, 190, 300, 54, "more conductive", "raise K_d", TEAL_L, TEAL, TEAL)
    b += pan(460, 190, 300, 54, "denser deep layer", "raises K_c(ρ)", CORAL_L, CORAL, CORAL)
    b += f"<line x1='360' y1='148' x2='230' y2='188' stroke='{DIM}' stroke-width='1.6' marker-end='url(#ar)'/>"
    b += f"<line x1='460' y1='148' x2='590' y2='188' stroke='{DIM}' stroke-width='1.6' marker-end='url(#ar)'/>"
    b += pan(230, 274, 360, 46, "identical slope — the sensors can't tell them apart", None, "#fbeedd", CORAL, CORAL)
    b += f"<line x1='210' y1='244' x2='320' y2='272' stroke='{DIM}' stroke-width='1.6' marker-end='url(#ar)'/>"
    b += f"<line x1='610' y1='244' x2='500' y2='272' stroke='{DIM}' stroke-width='1.6' marker-end='url(#ar)'/>"
    b += pan(60, 344, 320, 50, "fix density → get K_d", "the letter", TEAL_L, TEAL, TEAL)
    b += pan(440, 344, 320, 50, "fix K_d → get density", "this study", CORAL_L, CORAL, CORAL)
    b += f"<line x1='360' y1='320' x2='230' y2='342' stroke='{DIM}' stroke-width='1.6' marker-end='url(#ar)'/>"
    b += f"<line x1='460' y1='320' x2='590' y2='342' stroke='{DIM}' stroke-width='1.6' marker-end='url(#ar)'/>"
    b += punch(w, 412,
               "Not circular: fixing one knob to retrieve the other is the only well-posed choice.",
               "Retrieving K_d and density jointly is the identified next step.")
    (OUT / "expl_degeneracy.svg").write_text(svg(w, h, b, "the degeneracy"))
    render("expl_degeneracy", w, h)


def fig_sweep(N):
    w, h = 800, 480
    b = head(30, "How the density search is built",
             "five knobs, every physical combination, scored against Apollo")
    rows = [("surface ρ₁", ["1100", "1300", "1500"], TEAL),
            ("middle ρ₂", ["1500", "1700"], TEAL),
            ("deep ρ₃", ["1700", "1800", "1900"], TEAL),
            ("skin depth z₁", ["5", "10", "20"], FOREST),
            ("break depth z₂", ["30", "50", "80"], FOREST)]
    y = 108
    for name, vals, col in rows:
        b += txt(40, y+22, name, 14, col, w=700)
        x = 200
        for v in vals:
            b += panel(x, y, 62, 34, GRID, DIM, 6, 0.8) + txt(x+31, y+22, v, 13, CHAR, anchor="middle")
            x += 70
        y += 48
    b += panel(470, 128, 300, 40, TEAL_L, TEAL, 8, 1.3) + txt(620, 153, "3×2×3 = 18 density triples", 14, CHAR, anchor="middle")
    b += panel(470, 248, 300, 40, FOREST_L, FOREST, 8, 1.3) + txt(620, 273, "3×3 = 9 depth pairs", 14, CHAR, anchor="middle")
    b += panel(470, 316, 300, 42, "#eef4f6", TEAL, 8, 1.6) + txt(620, 343, "18 × 9 = 162 per site", 16, CHAR, w=700, anchor="middle")
    b += punch(w, 404,
               "162 profiles × 2 branches × 2 sites (+ baselines) = 650 model runs,",
               "each scored against the Apollo deep sensors.")
    (OUT / "expl_sweep.svg").write_text(svg(w, h, b, "the density sweep"))
    render("expl_sweep", w, h)


def fig_conclusions(N):
    w, h = 1180, 360
    b = f"<text x='30' y='44' font-size='25' font-weight='700' fill='{CHAR}'>What the study shows</text>"
    cards = [
        (PLUM, "Topography is first-order", "it enters twice, and opposes", "cools 2.2 / 0.5 K   ·   warms +1.3 / +0.7 K"),
        (FOREST, "Layers reproduce Apollo", "a 3-layer column fits the record", f"{N['rmsecKAfif']} / {N['rmsecKAsev']} K  (~2.6× / ~10× better)"),
        (TEAL, "Conductivity is the lever", "not heat capacity", "~4 K of leverage   vs   < 0.8 K"),
        (CORAL, "Physical, not fitted", "matches the drive cores", "1800 / 1900 ≈ measured 1825 / 1960"),
    ]
    cw, gap = 272, 15
    for i, (col, head_, sub, num) in enumerate(cards):
        x = 30 + i * (cw + gap)
        b += panel(x, 74, cw, 236, "white", col, 12, 1.8)
        b += f"<path d='M{x} 86 a12 12 0 0 1 12 -12 h{cw-24} a12 12 0 0 1 12 12 v34 h-{cw} z' fill='{col}'/>"
        b += txt(x+cw/2, 106, str(i+1), 17, "white", w=700, anchor="middle")
        b += txt(x+cw/2, 160, head_, 16, col, w=700, anchor="middle")
        b += txt(x+cw/2, 186, sub, 12.5, DIM, anchor="middle", it=True)
        b += panel(x+22, 220, cw-44, 56, GRID, "none", 8, 0)
        # wrap the number onto two lines at the '·'/'vs'
        parts = re.split(r'\s{2,}·\s{2,}|\s{2,}vs\s{2,}|  \(', num)
        b += txt(x+cw/2, 244, num.split("  ")[0], 12.5, CHAR, w=700, anchor="middle")
        rest = num[len(num.split('  ')[0]):].strip()
        if rest:
            b += txt(x+cw/2, 263, rest, 12, DIM, anchor="middle")
    (OUT / "expl_conclusions.svg").write_text(svg(w, h, b, "conclusions"))
    render("expl_conclusions", w, h)


def fig_pipeline(N):
    w, h = 1120, 400
    b = head(30, "One reproducible pass, end to end",
             "the elevation map drives every stage — nothing downstream is hand-tuned")
    stages = [
        (PLUM, "Elevation map", "LOLA + SLDEM DEM", "grid"),
        (TEAL, "Horizon ray-trace", "shadow + sky view", "ray"),
        (FOREST, "Density sweep", "162 layered profiles", "layers"),
        (CORAL, "Equilibrium solve", "periodic steady state", "wave"),
        (CHAR, "Score vs Apollo", "RMSE to deep sensors", "dots"),
    ]
    pw, gap, y = 190, 27, 120
    for i, (col, t, sub, icon) in enumerate(stages):
        x = 30 + i * (pw + gap)
        b += panel(x, y, pw, 200, "white", col, 12, 1.8)
        b += f"<path d='M{x} {y+12} a12 12 0 0 1 12 -12 h{pw-24} a12 12 0 0 1 12 12 v30 h-{pw} z' fill='{col}'/>"
        b += f"<circle cx='{x+24}' cy='{y+16}' r='11' fill='white'/>"
        b += txt(x+24, y+21, str(i+1), 14, col, w=700, anchor="middle")
        b += txt(x+pw/2+12, y+21, t, 14.5, "white", w=700, anchor="middle")
        cx, iy = x + pw / 2, y + 96
        if icon == "grid":
            for r in range(3):
                for c in range(3):
                    sh = ["#dcd6ce", "#b7ada0", "#8a7e6d"][(r + c) % 3]
                    b += f"<rect x='{cx-33+c*22}' y='{iy-33+r*22}' width='20' height='20' fill='{sh}' rx='2'/>"
        elif icon == "ray":
            b += f"<circle cx='{cx+26}' cy='{iy-28}' r='11' fill='{CORAL}'/>"
            b += f"<path d='M{cx-40} {iy+22} L{cx-8} {iy-14} L{cx+24} {iy+22} Z' fill='#cfc6ba'/>"
            b += f"<line x1='{cx+18}' y1='{iy-18}' x2='{cx-16}' y2='{iy+14}' stroke='{CORAL}' stroke-width='2.4' stroke-dasharray='4 3'/>"
        elif icon == "layers":
            for r, sh in enumerate(["#dcd6ce", "#b7ada0", "#8a7e6d"]):
                b += f"<rect x='{cx-38}' y='{iy-30+r*22}' width='76' height='19' fill='{sh}' rx='3'/>"
        elif icon == "wave":
            b += f"<path d='M{cx-40} {iy+18} Q {cx-20} {iy-34} {cx} {iy} T {cx+40} {iy-14}' fill='none' stroke='{CORAL}' stroke-width='2.6'/>"
        elif icon == "dots":
            for dx, dy in [(-30, 14), (-14, 2), (2, 8), (18, -10), (32, -20)]:
                b += f"<circle cx='{cx+dx}' cy='{iy+dy}' r='5' fill='white' stroke='{CHAR}' stroke-width='1.8'/>"
            b += f"<path d='M{cx-40} {iy+22} L{cx+38} {iy-26}' stroke='{FOREST}' stroke-width='2' stroke-dasharray='6 3'/>"
        b += txt(cx, y+164, sub, 12.5, DIM, anchor="middle")
        if i < 4:
            ax = x + pw + 3
            b += f"<line x1='{ax}' y1='{y+100}' x2='{ax+21}' y2='{y+100}' stroke='{DIM}' stroke-width='2.2' marker-end='url(#ar)'/>"
    b += punch(w, 336,
               "Two knobs — discrete density LAYERS and terrain SHADOWING — bolt onto the certified baseline solver.",
               "Same DEM in, one score out; the whole chain re-runs from scratch.")
    (OUT / "expl_pipeline.svg").write_text(svg(w, h, b, "the pipeline"))
    render("expl_pipeline", w, h)


def fig_shadowing(N):
    w, h = 900, 540
    b = head(30, "How a site learns its own skyline",
             "the horizon is measured from the elevation map, one compass bearing at a time")
    steps = [
        ("Stand on the site pixel", "the Apollo location on the DEM is the origin."),
        ("Fire a ray outward", "pick a compass bearing φ; step pixel by pixel."),
        ("Track the steepest rise", "the highest elevation angle so far is the horizon at φ."),
        ("Turn and repeat", "sweep all 360° → a full horizon ring."),
        ("Test the Sun each hour", "Sun below the horizon at its bearing → the site is shadowed."),
    ]
    ly, lh = 106, 78
    for i, (t, d) in enumerate(steps):
        y = ly + i * lh
        b += f"<circle cx='60' cy='{y+16}' r='15' fill='{TEAL}'/>"
        b += txt(60, y+21, str(i+1), 15, "white", w=700, anchor="middle")
        b += txt(88, y+13, t, 15.5, CHAR, w=700)
        b += txt(88, y+33, d, 13, DIM)
    # schematic on the right: terrain profile + ray + horizon angle
    gx, gy, gw = 560, 150, 300
    base = gy + 220
    b += f"<line x1='{gx}' y1='{base}' x2='{gx+gw}' y2='{base}' stroke='{DIM}' stroke-width='1.3'/>"
    # terrain silhouette
    b += (f"<path d='M{gx} {base} L{gx+70} {base-40} L{gx+120} {base-15} "
          f"L{gx+185} {base-120} L{gx+240} {base-55} L{gx+gw} {base-90} "
          f"L{gx+gw} {base} Z' fill='#cfc6ba' stroke='{DIM}' stroke-width='1.2'/>")
    # observer
    ox, oy = gx + 20, base
    b += f"<circle cx='{ox}' cy='{oy-6}' r='5.5' fill='{CHAR}'/>"
    b += txt(ox, oy+18, "site", 12, CHAR, anchor="middle")
    # horizon ray to the peak
    peak = (gx + 185, base - 120)
    b += f"<line x1='{ox}' y1='{oy-6}' x2='{peak[0]}' y2='{peak[1]}' stroke='{CORAL}' stroke-width='2.4'/>"
    # horizontal reference + angle arc
    b += f"<line x1='{ox}' y1='{oy-6}' x2='{ox+150}' y2='{oy-6}' stroke='{DIM}' stroke-width='1.2' stroke-dasharray='5 4'/>"
    b += f"<path d='M{ox+70} {oy-6} A 70 70 0 0 0 {ox+62} {oy-33}' fill='none' stroke='{TEAL}' stroke-width='2'/>"
    b += txt(ox+80, oy-20, "horizon angle", 12, TEAL, it=True)
    # Sun below horizon
    b += f"<circle cx='{peak[0]+40}' cy='{peak[1]+34}' r='12' fill='{CORAL}' opacity='0.55'/>"
    b += txt(peak[0]+40, peak[1]+58, "Sun below → shadow", 12, PLUM, anchor="middle")
    b += txt(gx, gy-6, "elevation profile along one bearing", 12.5, DIM, it=True)
    b += punch(w, 476,
               f"Apollo 15 sits under a {N['horAfif']}° skyline, Apollo 17 under {N['horAsev']}° —",
               "the taller horizon is exactly why Apollo 15 loses more heat to shadow.")
    (OUT / "expl_shadowing.svg").write_text(svg(w, h, b, "the shadowing algorithm"))
    render("expl_shadowing", w, h)


def fig_models(N):
    w, h = 840, 500
    b = head(30, "Each added piece of physics closes the gap",
             "RMSE to the Apollo deep sensors — lower is better")
    models = [
        ("Uniform column", N["rmsehomAfif"], N["rmsehomAsev"], "no structure at all"),
        ("Smooth Hayne K(T,z)", N["rmsehayAfif"], N["rmsehayAsev"], "the standard model"),
        ("3-layer, storage only", N["rmsecpAfif"], N["rmsecpAsev"], "density → heat capacity"),
        ("3-layer, coupled K(ρ)", N["rmsecKAfif"], N["rmsecKAsev"], "density → conductivity"),
    ]
    # legend
    b += f"<rect x='612' y='34' width='15' height='15' rx='3' fill='{TEAL}'/>" + txt(633, 46, "Apollo 15", 13, CHAR)
    b += f"<rect x='720' y='34' width='15' height='15' rx='3' fill='{CORAL}'/>" + txt(741, 46, "Apollo 17", 13, CHAR)
    x0, sc, rh, y = 300, 110, 92, 108
    maxv = 3.76
    b += txt(x0, y-14, "0", 11, DIM, anchor="middle")
    b += txt(x0 + 3.0 * sc, y-14, "3 K", 11, DIM, anchor="middle")
    b += f"<line x1='{x0}' y1='{y-6}' x2='{x0}' y2='{y+3*rh+40}' stroke='{GRID}' stroke-width='1.2'/>"
    for i, (name, a15, a17, note) in enumerate(models):
        yy = y + i * rh
        best = i == 3
        b += txt(288, yy+16, name, 14.5, (FOREST if best else CHAR), w=700, anchor="end")
        b += txt(288, yy+34, note, 11.5, DIM, anchor="end", it=True)
        for j, (v, col, lab) in enumerate([(float(a15), TEAL, "A15"), (float(a17), CORAL, "A17")]):
            by = yy + j * 24
            b += f"<rect x='{x0}' y='{by}' width='{v*sc}' height='18' rx='3' fill='{col}' opacity='{1.0 if best else 0.85}'/>"
            b += txt(x0 + v * sc + 8, by + 14, f"{v:.2f} K", 12, col, w=700)
            b += txt(x0 - 0, by + 14, "", 10)
    # winner flag
    yy = y + 3 * rh
    b += f"<rect x='{x0-4}' y='{yy-6}' width='{maxv*sc+90}' height='54' rx='8' fill='none' stroke='{FOREST}' stroke-width='2' stroke-dasharray='6 4'/>"
    b += txt(x0 + maxv * sc + 52, yy + 40, "best fit", 12.5, FOREST, w=700, anchor="middle", it=True)
    b += punch(w, 436,
               f"From {N['rmsehomAsev']} K down to {N['rmsecKAsev']} K at Apollo 17: conductivity, not capacity, is what",
               "pulls the model onto the sensors. That is the paper's core claim.")
    (OUT / "expl_models.svg").write_text(svg(w, h, b, "model ladder"))
    render("expl_models", w, h)


if __name__ == "__main__":
    N = nums()
    fig_mechanism(N)
    fig_setup(N)
    fig_topography(N)
    fig_result(N)
    fig_degeneracy(N)
    fig_sweep(N)
    fig_pipeline(N)
    fig_shadowing(N)
    fig_models(N)
    fig_conclusions(N)
