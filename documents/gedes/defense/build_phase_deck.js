// Study-phase slides as a standalone, EDITABLE PowerPoint deck.
//
// Everything here is a native PowerPoint object — text boxes, rounded
// rectangles, lines, arrows — not a flattened picture. Click any element and
// change it. Only the master overview (slide 1) is an embedded image, because
// rebuilding that five-column chart natively would be less editable, not more.
//
// Content mirrors make_phase_slides.py exactly; see PHASE_SLIDE_PROMPTS.md.
// Scope: Phase 1 IS the thesis (complete). Phase 2 IS the AOGS terrain work,
// applied at the two Apollo sites only. Phases 3-5 are the proposal.
//
// Build:  cd documents/gedes/defense && node build_phase_deck.js
// Output: study_phases.pptx
const pptxgen = require("pptxgenjs");
const path = require("path");

const CHAR = "2A2520", CORAL = "B85B3A", TEAL = "2A6478", FOREST = "3D6E4A";
const DIM = "6E6862", GRID = "E8E5E0", WHITE = "FFFFFF", PLUM = "5A4A6A";
const GOLD = "9A7B12";
const FOREST_L = "E9F0EA", TEAL_L = "E6EEF1", CORAL_L = "FBEFEA",
      PLUM_L = "EEEAF2", GOLD_L = "F6F1E2";
const HEAD = "Cambria", BODY = "Calibri";

const MX = 0.72, CW = 11.90, BX = 7.35, LW = 5.9;

const pres = new pptxgen();
pres.layout = "LAYOUT_WIDE";                       // 13.333 x 7.5 in
pres.author = "Ramon III P. Gregorio";
pres.title = "Study phases";

// ------------------------------------------------------------------ helpers
const txt = (s, t, o) => s.addText(t, Object.assign({ fontFace: BODY, margin: 0 }, o));

const roundRect = (s, o) => s.addShape(pres.ShapeType.roundRect, Object.assign(
  { rectRadius: 0.06 }, o));

function hairline(s, y, x = MX, w = CW, color = GRID) {
  s.addShape(pres.ShapeType.rect, { x, y, w, h: 0.008,
    fill: { color }, line: { width: 0 } });
}

function downArrow(s, x, y, h, color) {
  s.addShape(pres.ShapeType.line, { x, y, w: 0, h,
    line: { color, width: 1.75, endArrowType: "triangle" } });
}

function rightArrow(s, x, y, w, color) {
  s.addShape(pres.ShapeType.line, { x, y, w, h: 0,
    line: { color, width: 1.75, endArrowType: "triangle" } });
}

function chip(s, xRight, y, label, color, filled) {
  const w = 0.098 * label.length + 0.34;
  roundRect(s, { x: xRight - w, y, w, h: 0.30, rectRadius: 0.15,
    fill: { color: filled ? color : WHITE },
    line: { color, width: 1.25 } });
  txt(s, label, { x: xRight - w, y, w, h: 0.30, fontSize: 10, bold: true,
    color: filled ? WHITE : color, align: "center", valign: "middle",
    charSpacing: 0.5 });
}

// ------------------------------------------------------------------ content
const PHASES = [
  { tag: "Phase 1", col: FOREST, colL: FOREST_L, status: "COMPLETE", filled: true,
    kicker: "Study phases · Phase 1 · complete",
    title: "The thesis: two ground-truth anchors, delivered",
    take: "Both boreholes reproduced, every claim stress-tested, and the limits stated honestly.",
    q: "Does the model reproduce sub-surface temperature at a point?",
    items: [
      [1, "per-site K_d: 4.60 / 7.08  (misfit 1.09 to 1.00, 0.89 to 0.40 K)"],
      [1, "1500-draw bootstrap, tail 0.031 · MCMC ordering 99.2%"],
      [1, "AICc: A17 −23.2, A15 +2.9 — stated honestly, not hidden"],
      [1, "held-out + Diviner surface closure, both out-of-sample"],
      [1, "error budget audited to source (±1.88 / ±3.88, χ conditional)"],
    ],
    val: "scored against Apollo HFE · 23 deep sensors",
    deliv: "two calibrated ground-truth anchors" },
  { tag: "Phase 2", col: TEAL, colL: TEAL_L, status: "COMPLETE", filled: true,
    kicker: "Study phases · Phase 2 · complete",
    title: "Real terrain, at the two sites we can check",
    take: "The DEM machinery is built and applied where ground truth exists — and terrain turns out to matter a great deal.",
    q: "How much does real terrain change the answer?",
    items: [
      [1, "DEM horizon algorithm built (16 ppd, 90 azimuths)"],
      [1, "applied at both sites: 14.0° / 10.1°, insolation −1.16% / −0.18%"],
      [1, "re-retrieval under shadowing: K_d 4.60 to 1.88, 7.08 to 9.69"],
      [1, "650-run density study — density sets conductivity, not c_p"],
      [1, "layered physics transfers between sites (2.31–3.76 to 0.36–0.90 K)"],
    ],
    val: "two sites only — deliberately not yet global",
    deliv: "a terrain-aware, layered retrieval" },
  { tag: "Phase 3", col: GOLD, colL: GOLD_L, status: "NEXT", filled: true,
    kicker: "Study phases · Phase 3 · next",
    title: "From two neighbourhoods to the whole Moon",
    take: "Same physics, same solver. What remains is scale, and the solver already makes it affordable.",
    q: "Does it hold at many points, not just two?",
    items: [
      [0, "tile the solver over the DEM grid (one column ≈ 1 s, so feasible)"],
      [0, "Moon-wide horizons, beyond the two Apollo neighbourhoods"],
      [0, "sub-surface T(z) everywhere, to annual-wave depth"],
      [0, "validate against Diviner global brightness composites"],
      [0, "publish the gridded product"],
    ],
    val: "to be scored against Diviner global composites",
    deliv: "a validated Moon-wide temperature map" },
  { tag: "Phase 4", col: CORAL, colL: CORAL_L, status: "PLANNED", filled: false,
    kicker: "Study phases · Phase 4 · planned",
    title: "Coupling to TSUKIMI: from temperature to ice",
    take: "The temperature field becomes terahertz brightness, and finally an ice-survivability map.",
    q: "Where can subsurface ice actually survive?",
    items: [
      [0, "couple T(z) into the TSUKIMI radiative-transfer simulator (NICT)"],
      [0, "THz brightness-temperature forward model for sounding"],
      [0, "cold traps and permanently shadowed regions treated explicitly"],
      [0, "ice stability against depth from the sub-surface field"],
    ],
    val: "to be tested against THz observations",
    deliv: "an ice-survivability map" },
  { tag: "Phase 5", col: PLUM, colL: PLUM_L, status: "HORIZON", filled: false,
    kicker: "Study phases · Phase 5 · horizon",
    title: "Beyond: the next-generation regolith model",
    take: "Three physics upgrades, each weighed by difficulty and scientific impact before any is attempted.",
    q: "What would the next-generation regolith model add?",
    items: [
      [0, "depth-varying H(z) compaction history — moderate / medium"],
      [0, "ε(T) emissivity for cold PSRs — low difficulty / medium impact"],
      [0, "vapor diffusion + latent heat — high / high, genuinely new"],
      [0, "doctoral thesis, written from the running system"],
    ],
    val: "each weighed by difficulty and impact first",
    deliv: "next-generation regolith model" },
];

// --------------------------------------------------------------- slide body
function frame(P) {
  const s = pres.addSlide();
  s.background = { color: WHITE };
  txt(s, P.kicker.toUpperCase(), { x: MX, y: 0.32, w: 9.6, h: 0.28,
    fontSize: 11, bold: true, color: P.col, charSpacing: 1.5 });
  chip(s, 13.333 - MX, 0.28, P.status, P.col, P.filled);
  txt(s, P.title, { x: MX, y: 0.62, w: CW, h: 0.62, fontFace: HEAD,
    fontSize: 25, bold: true, color: CHAR, valign: "top" });
  txt(s, P.take, { x: MX, y: 1.28, w: CW, h: 0.44, fontSize: 13, color: DIM });
  hairline(s, 1.80);

  // ---- left column: question, checklist, validation, deliverable
  txt(s, P.q, { x: MX, y: 2.02, w: LW, h: 0.34, fontSize: 12.5,
    italic: true, color: DIM });
  let y = 2.58;
  P.items.forEach(([done, t]) => {
    txt(s, done ? "✓" : "○", { x: MX, y, w: 0.34, h: 0.34, fontSize: done ? 14 : 12,
      bold: true, color: P.col, align: "center" });
    txt(s, t, { x: MX + 0.36, y, w: LW - 0.36, h: 0.42, fontSize: 11.5, color: CHAR });
    y += 0.54;
  });
  y += 0.06;
  hairline(s, y, MX, LW);
  txt(s, P.val, { x: MX, y: y + 0.10, w: LW, h: 0.30, fontSize: 10.5,
    italic: true, color: DIM });
  roundRect(s, { x: MX, y: y + 0.52, w: LW, h: 0.68,
    fill: { color: P.colL }, line: { color: P.col, width: 1.4 } });
  txt(s, "DELIVERABLE", { x: MX + 0.24, y: y + 0.58, w: LW - 0.4, h: 0.24,
    fontSize: 9, bold: true, color: P.col, charSpacing: 1 });
  txt(s, P.deliv, { x: MX + 0.24, y: y + 0.82, w: LW - 0.4, h: 0.32,
    fontSize: 13, bold: true, color: CHAR });
  return s;
}

function sectionLabel(s, label, color) {
  txt(s, label, { x: BX, y: 2.02, w: 5.0, h: 0.28, fontSize: 10.5,
    bold: true, color, charSpacing: 1 });
}

// ---------------------------------------------------------- slide 1: master
{
  const s = pres.addSlide();
  s.background = { color: WHITE };
  txt(s, "DOCTORAL RESEARCH PLAN", { x: MX, y: 0.32, w: CW, h: 0.28,
    fontSize: 11, bold: true, color: CORAL, charSpacing: 2 });
  txt(s, "Five phases, and where the work actually stands", { x: MX, y: 0.62,
    w: CW, h: 0.62, fontFace: HEAD, fontSize: 27, bold: true, color: CHAR,
    valign: "top" });
  txt(s, "Two phases are delivered and presented; three are scheduled against them.",
    { x: MX, y: 1.28, w: CW, h: 0.44, fontSize: 14, color: DIM });
  hairline(s, 1.80);
  s.addImage({ path: path.join(__dirname, "img", "study_phases_flow.png"),
    x: MX, y: 1.98, w: CW, h: CW * 1500 / 3040 });
  s.addNotes("40 s. Name the five headings, then point at the dashed rule between "
    + "Phase 2 and 3: everything to its left exists and has been presented; "
    + "everything to its right is the proposal. Then stop — the detail is there "
    + "to be read, not narrated.\n\n"
    + "This slide is an embedded image. The five detail slides that follow are "
    + "fully editable native shapes.");
}

// ------------------------------------------------------- slide 2: phase 1
{
  const P = PHASES[0], s = frame(P);
  sectionLabel(s, "WHERE IT LANDED", P.col);
  const x0 = BX, wMax = 4.9, scale = wMax / 8.6;
  [["Apollo 15", 4.60, FOREST], ["Apollo 17", 7.08, CORAL]].forEach(([nm, v, c], i) => {
    const y = 2.46 + i * 0.72;
    s.addShape(pres.ShapeType.rect, { x: x0, y, w: v * scale, h: 0.52,
      fill: { color: c }, line: { width: 0 } });
    txt(s, nm, { x: x0 + 0.14, y, w: 1.6, h: 0.52, fontSize: 11,
      bold: true, color: WHITE, valign: "middle" });
    txt(s, v.toFixed(2), { x: x0, y, w: v * scale - 0.14, h: 0.52, fontSize: 14,
      bold: true, color: WHITE, align: "right", valign: "middle" });
  });
  s.addShape(pres.ShapeType.line, { x: x0 + 3.4 * scale, y: 2.30, w: 0, h: 1.60,
    line: { color: DIM, width: 1.4, dashType: "dash" } });
  txt(s, "global 3.4", { x: x0 + 3.4 * scale + 0.08, y: 2.00, w: 1.4, h: 0.26,
    fontSize: 10, color: DIM });
  [["bootstrap tail 0.031", FOREST], ["MCMC ordering 99.2%", TEAL],
   ["AICc: A17 −23.2 · A15 +2.9", CORAL]].forEach(([t, c], i) => {
    const y = 4.18 + i * 0.56;
    roundRect(s, { x: BX, y, w: 4.9, h: 0.44, rectRadius: 0.1,
      fill: { color: WHITE }, line: { color: c, width: 1.3 } });
    s.addShape(pres.ShapeType.ellipse, { x: BX + 0.22, y: y + 0.16, w: 0.12, h: 0.12,
      fill: { color: c }, line: { width: 0 } });
    txt(s, t, { x: BX + 0.48, y, w: 4.3, h: 0.44, fontSize: 11.5,
      color: CHAR, valign: "middle" });
  });
  txt(s, "On the slide, not hidden: Apollo 15 alone does not justify a separate "
       + "fit — the case there rests on the interval.",
    { x: BX, y: 6.02, w: 4.9, h: 0.60, fontSize: 10.5, italic: true, color: DIM });
  s.addNotes("50 s. Say the numbers, then the honesty. Volunteering the AICc "
    + "split is worth more than defending it under question.");
}

// ------------------------------------------------------- slide 3: phase 2
{
  const P = PHASES[1], s = frame(P);
  sectionLabel(s, "WHAT TERRAIN DOES TO THE ANSWER", P.col);
  [["Apollo 15", "4.60", "1.88", FOREST, "−2.72 mW m⁻¹ K⁻¹"],
   ["Apollo 17", "7.08", "9.69", CORAL, "+2.61 mW m⁻¹ K⁻¹"]].forEach(
    ([nm, a, b, c, d], i) => {
      const y = 2.42 + i * 1.00;
      txt(s, nm, { x: BX, y, w: 2.0, h: 0.26, fontSize: 11, bold: true, color: c });
      txt(s, a, { x: BX, y: y + 0.26, w: 0.90, h: 0.42, fontSize: 18,
        bold: true, color: DIM });
      rightArrow(s, BX + 0.92, y + 0.47, 0.68, c);
      txt(s, b, { x: BX + 1.68, y: y + 0.26, w: 0.95, h: 0.42, fontSize: 18,
        bold: true, color: c });
      txt(s, "flat ground to real horizon", { x: BX + 2.66, y, w: 2.3, h: 0.26,
        fontSize: 9.5, italic: true, color: DIM });
      txt(s, d, { x: BX + 2.66, y: y + 0.28, w: 2.3, h: 0.32, fontSize: 11, color: DIM });
    });
  hairline(s, 4.48, BX, 4.9);
  txt(s, "The two sites move in OPPOSITE directions — terrain cannot be averaged away.",
    { x: BX, y: 4.62, w: 4.9, h: 0.56, fontSize: 12, bold: true, color: CHAR });
  [["sky-view factor 0.985 / 0.991", TEAL],
   ["adding IR self-heating made the fit worse", DIM]].forEach(([t, c], i) => {
    const y = 5.30 + i * 0.56;
    roundRect(s, { x: BX, y, w: 4.9, h: 0.44, rectRadius: 0.1,
      fill: { color: WHITE }, line: { color: c, width: 1.2 } });
    s.addShape(pres.ShapeType.ellipse, { x: BX + 0.22, y: y + 0.16, w: 0.12, h: 0.12,
      fill: { color: c }, line: { width: 0 } });
    txt(s, t, { x: BX + 0.48, y, w: 4.3, h: 0.44, fontSize: 11, color: CHAR,
      valign: "middle" });
  });
  txt(s, "Presented at AOGS 2026 — built and tested, not proposed.",
    { x: BX, y: 6.48, w: 4.9, h: 0.30, fontSize: 10.5, italic: true, color: DIM });
  s.addNotes("55 s. The strongest slide in the plan. Terrain shifts Apollo 15 "
    + "DOWN by 2.72 and Apollo 17 UP by 2.61 — opposite signs, so no global "
    + "correction factor can absorb it. That is the argument for doing it "
    + "properly Moon-wide, which is Phase 3. Say the IR result too: a negative "
    + "finding you report yourself reads as rigour.");
}

// --------------------------------------------- slides 4-5: stacked-box pairs
function stackSlide(P, label, boxes, footer, note, footerY) {
  const s = frame(P);
  sectionLabel(s, label, P.col);
  boxes.forEach(([h, sub, c, cl], i) => {
    const y = 2.42 + i * 1.02;
    roundRect(s, { x: BX, y, w: 4.9, h: 0.80,
      fill: { color: cl }, line: { color: c, width: 1.5 } });
    txt(s, h, { x: BX + 0.26, y: y + 0.08, w: 4.4, h: 0.34, fontSize: 12.5,
      bold: true, color: CHAR });
    txt(s, sub, { x: BX + 0.26, y: y + 0.44, w: 4.4, h: 0.28, fontSize: 10,
      color: DIM });
    if (i < boxes.length - 1) downArrow(s, BX + 2.45, y + 0.82, 0.18, P.col);
  });
  // footerY lets a caller that adds its own box below the stack push this
  // line clear of it — without it the Phase-3 footer lands inside that box
  txt(s, footer, { x: BX, y: footerY || (2.42 + boxes.length * 1.02 + 0.18),
    w: 4.9, h: 0.70, fontSize: 10.5, italic: true, color: DIM });
  s.addNotes(note);
  return s;
}

{
  const P = PHASES[2];
  const s = stackSlide(P, "WHAT REMAINS", [
    ["Tile the DEM grid", "horizons everywhere", P.col, P.colL],
    ["Moon-wide T(z)", "to annual-wave depth", P.col, P.colL],
    ["Diviner validation", "global brightness composites", P.col, P.colL],
  ], "The DEM machinery already exists; this phase is scale, not new physics.",
    "50 s. Nothing here is a research risk — it is compute and validation. "
    + "The 2500x speed-up is what turns millions of columns from impossible "
    + "into a weekend.", 6.62);
  roundRect(s, { x: BX, y: 5.62, w: 4.9, h: 0.86, rectRadius: 0.08,
    fill: { color: WHITE }, line: { color: P.col, width: 1.4 } });
  txt(s, "Why it is affordable", { x: BX + 0.26, y: 5.70, w: 4.4, h: 0.26,
    fontSize: 10.5, bold: true, color: P.col });
  txt(s, "one column ≈ 1 s — the flux-anchored solver is ≈ 2500× faster than brute force",
    { x: BX + 0.26, y: 5.96, w: 4.4, h: 0.46, fontSize: 11, color: CHAR });
}

{
  const P = PHASES[3];
  stackSlide(P, "THE CHAIN", [
    ["Sub-surface T(z) field", "delivered by Phase 3", GOLD, GOLD_L],
    ["TSUKIMI radiative transfer", "NICT terahertz simulator", CORAL, CORAL_L],
    ["THz brightness temperature", "what a sounder would see", CORAL, CORAL_L],
    ["Ice-survivability map", "cold traps + PSRs explicit", FOREST, FOREST_L],
  ], "THz emission originates below the diurnal skin — exactly the region this "
   + "model was built to resolve.",
    "50 s. The 'why me, why here' slide. The chain only works if someone "
    + "supplies a trustworthy sub-surface profile, which is what Phases 1-3 "
    + "build. Name the NICT link explicitly.");
}

// ------------------------------------------------------- slide 6: phase 5
{
  const P = PHASES[4], s = frame(P);
  sectionLabel(s, "WEIGHED, NOT WISHED", P.col);
  // a hand-built difficulty x impact quadrant, all native shapes
  const gx = BX + 0.55, gy = 2.55, gw = 4.05, gh = 3.05;
  s.addShape(pres.ShapeType.line, { x: gx, y: gy, w: 0, h: gh,
    line: { color: DIM, width: 1.1 } });
  s.addShape(pres.ShapeType.line, { x: gx, y: gy + gh, w: gw, h: 0,
    line: { color: DIM, width: 1.1 } });
  txt(s, "implementation difficulty →", { x: gx, y: gy + gh + 0.30, w: gw, h: 0.26,
    fontSize: 10, color: DIM, align: "center" });
  txt(s, "scientific impact →", { x: gx - 2.05, y: gy + gh / 2 - 0.13, w: 2.0, h: 0.26,
    fontSize: 10, color: DIM, align: "right" });
  ["low", "moderate", "high"].forEach((t, i) => txt(s, t,
    { x: gx + gw * (0.16 + i * 0.34) - 0.4, y: gy + gh + 0.04, w: 0.8, h: 0.24,
      fontSize: 9.5, color: DIM, align: "center" }));
  ["high", "medium"].forEach((t, i) => txt(s, t,
    { x: gx - 0.86, y: gy + gh * (0.18 + i * 0.44) - 0.12, w: 0.78, h: 0.24,
      fontSize: 9.5, color: DIM, align: "right" }));
  [["ε(T) for PSRs", 0.16, 0.62, FOREST], ["H(z) compaction", 0.50, 0.62, TEAL],
   ["vapor diffusion + latent heat", 0.84, 0.18, CORAL]].forEach(
    ([nm, fx, fy, c]) => {
      const px = gx + gw * fx, py = gy + gh * fy;
      s.addShape(pres.ShapeType.ellipse, { x: px - 0.11, y: py - 0.11, w: 0.22, h: 0.22,
        fill: { color: c }, line: { color: WHITE, width: 1.5 } });
      txt(s, nm, { x: px - 1.15, y: py - 0.52, w: 2.3, h: 0.34, fontSize: 10,
        color: CHAR, align: "center" });
    });
  txt(s, "The vapor-diffusion term is genuinely new physics — high risk, and "
       + "precisely why it is scheduled last.",
    { x: BX, y: 6.20, w: 4.9, h: 0.60, fontSize: 10.5, italic: true, color: DIM });
  s.addNotes("45 s. The point is not the three ideas, it is that they were "
    + "weighed. A committee reads 'I know which of my own ideas is risky' as "
    + "maturity. Do not promise the vapor-diffusion term.");
}

pres.writeFile({ fileName: path.join(__dirname, "study_phases.pptx") })
  .then((f) => console.log("wrote", f, "— 6 slides, 5 fully editable"));
