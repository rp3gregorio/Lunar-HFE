// GEDES defense deck — built to OUTLINE.md and the per-slide briefs in
// SLIDE_PROMPTS.md. Read those before changing anything here.
//
//   Part 1  Master's thesis   slides 1-15    12 min + 5 min Q&A
//   Part 2  Doctoral plan     slides 16-22    6 min + 7 min Q&A
//   Part 3  Backup for Q&A    slides 23-49   not presented, indexed on 24
//   Final   EN/JP term table  slide 50       required by GEDES, must be last
//
// Design (SLIDE_PROMPTS.md sec 0.2-0.5): white stage, charcoal type, thesis
// palette accents. Lay artwork is drawn on a fixed 2.41:1 canvas so it fills
// the art box exactly; PUBLISHED figures (guidebook TikZ, thesis Ch 5) keep
// their own aspect and are fitted to height instead.
const pptxgen = require("pptxgenjs");
const fs = require("fs");
const path = require("path");

const IMGDIR = path.join(__dirname, "img");
const P = (f) => path.join(IMGDIR, f);

function aspect(file) {
  const b = fs.readFileSync(P(file));
  if (file.endsWith(".gif")) return b.readUInt16LE(6) / b.readUInt16LE(8);
  return b.readUInt32BE(16) / b.readUInt32BE(20);        // PNG IHDR
}

const CHAR = "2A2520", CORAL = "B85B3A", TEAL = "2A6478", FOREST = "3D6E4A";
const DIM = "6E6862", GRID = "E8E5E0", WHITE = "FFFFFF", TINT = "F7F5F2";
const HEAD = "Cambria", BODY = "Calibri";

const MX = 0.72, CW = 11.90;              // left margin, content width
const ART_Y = 1.88, ART_H = 4.94;         // the art box
const RULE_Y = 1.78;

const pres = new pptxgen();
pres.layout = "LAYOUT_WIDE";                              // 13.333 x 7.5 in
pres.author = "Ramon III P. Gregorio";
pres.title = "Difference of Lunar Regolith Thermal Conductivity Kd";

let n = 0;                       // actual slide position, dark slides included
const newSlide = () => { n++; return pres.addSlide(); };
const foot = (s) => {
  s.addText(String(n), { x: 12.45, y: 6.98, w: 0.55, h: 0.3, fontFace: BODY,
    fontSize: 10, color: GRID, align: "right", margin: 0 });
};
const kicker = (s, t, c) => s.addText(t.toUpperCase(), {
  x: MX, y: 0.32, w: CW, h: 0.28, fontFace: BODY, fontSize: 11,
  bold: true, color: c || CORAL, charSpacing: 2, margin: 0 });
const title = (s, t) => s.addText(t, {
  x: MX, y: 0.60, w: CW, h: 0.62, fontFace: HEAD, fontSize: 29,
  bold: true, color: CHAR, margin: 0, valign: "top" });
const hairline = (s) => s.addShape(pres.ShapeType.rect, {
  x: MX, y: RULE_Y, w: CW, h: 0.008, fill: { color: GRID }, line: { width: 0 } });

/** The three-stage rail, lifted from guidebook Fig 2.1 (SLIDE_PROMPTS sec 0.1). */
const STAGES = ["What we have", "What we do", "What we get"];
function rail(s, stage, accent) {
  if (!stage) return;
  for (let i = 0; i < 3; i++) {
    s.addShape(pres.ShapeType.rect, {
      x: MX + i * 0.82, y: 7.05, w: 0.72, h: 0.055,
      fill: { color: i === stage - 1 ? (accent || CORAL) : GRID },
      line: { width: 0 } });
  }
  s.addText(STAGES[stage - 1].toUpperCase(), {
    x: MX + 2.62, y: 6.95, w: 4.0, h: 0.26, fontFace: BODY, fontSize: 9,
    bold: true, color: DIM, charSpacing: 1.5, margin: 0, valign: "middle" });
}

function fit(file, bx, by, bw, bh) {
  const ar = aspect(file);
  let w = bw, h = bw / ar;
  if (h > bh) { h = bh; w = bh * ar; }
  return { path: P(file), x: bx + (bw - w) / 2, y: by + (bh - h) / 2, w, h };
}

function head(o) {
  const s = newSlide(); s.background = { color: WHITE };
  kicker(s, o.kicker, o.accent); title(s, o.title);
  if (o.take) {
    s.addText(o.take, { x: MX, y: 1.24, w: CW, h: 0.44, fontFace: BODY,
      fontSize: 14.5, color: DIM, margin: 0 });
  }
  hairline(s);
  return s;
}

/** Hero slide: one big picture filling the art box. */
function hero(o) {
  const s = head(o);
  s.addImage(fit(o.fig, MX, ART_Y, CW, ART_H));
  rail(s, o.stage, o.accent);
  if (o.notes) s.addNotes(o.notes);
  foot(s); return s;
}

/** Figure + note column. For PUBLISHED figures whose aspect is narrower than
 *  the art box: fitting them full width would leave a wide white gutter, so
 *  the gutter is given to a "what you are looking at" column instead. */
function split(o) {
  const s = head(o);
  const fw = o.figW || 6.9;
  s.addImage(fit(o.fig, MX, ART_Y, fw, ART_H));
  const bx = MX + fw + 0.45, bw = CW - fw - 0.45;
  (o.points || []).forEach((p, i) => {
    const y = ART_Y + 0.25 + i * 1.30;
    s.addShape(pres.ShapeType.rect, { x: bx, y: y + 0.02, w: 0.055, h: 0.95,
      fill: { color: o.accent || TEAL }, line: { width: 0 } });
    s.addText(p[0], { x: bx + 0.24, y, w: bw - 0.3, h: 0.36, fontFace: HEAD,
      fontSize: 15.5, bold: true, color: CHAR, margin: 0 });
    s.addText(p[1], { x: bx + 0.24, y: y + 0.40, w: bw - 0.3, h: 0.62,
      fontFace: BODY, fontSize: 12.5, color: DIM, margin: 0 });
  });
  rail(s, o.stage, o.accent);
  if (o.notes) s.addNotes(o.notes);
  foot(s); return s;
}

/** Backup slide: the real figure, scaled to height, plus the one line to say
 *  and a grey source note. */
function evidence(o) {
  const s = newSlide(); s.background = { color: WHITE };
  kicker(s, o.kicker || "Backup", DIM); title(s, o.title);
  s.addText(o.take, { x: MX, y: 1.24, w: CW, h: 0.44, fontFace: BODY,
    fontSize: 14.5, color: DIM, margin: 0 });
  hairline(s);
  s.addImage(fit(o.fig, MX, ART_Y, CW, 4.62));
  s.addText(o.src, { x: MX, y: 6.62, w: CW, h: 0.3, fontFace: BODY,
    fontSize: 10, italic: true, color: DIM, margin: 0 });
  if (o.notes) s.addNotes(o.notes);
  foot(s); return s;
}

function dark(o) {
  const s = newSlide(); s.background = { color: CHAR };
  s.addText(o.kicker.toUpperCase(), { x: 1.0, y: 2.62, w: 11.3, h: 0.3,
    fontFace: BODY, fontSize: 12, bold: true, color: CORAL, charSpacing: 3, margin: 0 });
  s.addText(o.title, { x: 1.0, y: 3.02, w: 11.3, h: 0.95, fontFace: HEAD,
    fontSize: 38, bold: true, color: WHITE, margin: 0 });
  if (o.sub) s.addText(o.sub, { x: 1.0, y: 4.05, w: 11.3, h: 0.5, fontFace: BODY,
    fontSize: 16.5, color: GRID, margin: 0 });
  if (o.notes) s.addNotes(o.notes);
  return s;
}

// =============================================================== 1  TITLE
{
  const s = newSlide(); s.background = { color: CHAR };
  s.addText("GEDES MASTER'S THESIS DEFENSE", { x: 1.05, y: 1.35, w: 11.3, h: 0.3,
    fontFace: BODY, fontSize: 12, bold: true, color: CORAL, charSpacing: 3, margin: 0 });
  s.addText([
    { text: "How well does the Moon hold its heat?", options: { breakLine: true } },
    { text: "Measuring it at the only two places we ever dug",
      options: { fontSize: 21, color: GRID } },
  ], { x: 1.05, y: 1.95, w: 11.3, h: 1.9, fontFace: HEAD, fontSize: 36,
    bold: true, color: WHITE, lineSpacingMultiple: 1.2, margin: 0 });
  s.addText("Ramon III P. Gregorio", { x: 1.05, y: 4.35, w: 11.3, h: 0.4,
    fontFace: BODY, fontSize: 18, color: WHITE, margin: 0 });
  s.addText("Student No. 24M58378   ·   Institute of Science Tokyo   ·   Kasai Laboratory",
    { x: 1.05, y: 4.83, w: 11.3, h: 0.35, fontFace: BODY, fontSize: 13, color: GRID, margin: 0 });
  s.addText("Supervisor: Prof. Yasuko Kasai      Co-supervisor: Dr. Richard Larsson",
    { x: 1.05, y: 5.32, w: 11.3, h: 0.35, fontFace: BODY, fontSize: 13, color: GRID, margin: 0 });
  s.addText("July 2026", { x: 1.05, y: 6.05, w: 11.3, h: 0.3, fontFace: BODY,
    fontSize: 12, color: DIM, margin: 0 });
  s.addNotes("20 s. CONTENT: the question, not the filing label. Name, student "
    + "number, institute, laboratory, both supervisors, date. The formal thesis "
    + "title lives on the term table and in the abstract.\n\n"
    + "SAY: 'Good morning. My name is Ramon Gregorio, from Kasai Laboratory. My "
    + "thesis asks a simple question: how well does the Moon hold on to its heat? "
    + "And I answer it at the only two places we have ever dug deep enough to find "
    + "out.' Then pause and advance.");
  foot(s);
}

// =============================================================== 2  HOOK
hero({ kicker: "Why this matters", fig: "anim_hook.gif",
  title: "The surface is violent. A metre down, nothing moves.",
  take: "Ice can only survive where the ground stays cold and steady, and that is decided below the surface.",
  notes: "45 s. CONTENT: one lunation looped. A regolith cross-section coloured "
       + "by temperature with the colour key beneath it, the Sun tracking "
       + "overhead, the regolith layering marked (6 cm where the loose fines "
       + "compact, 20 cm where the daily wave has died, 80 cm where the "
       + "drilling-disturbed zone ends, and the measured zone below), and two "
       + "live readouts.\n\n"
       + "SAY: let it loop once before speaking. The surface swings from about "
       + "100 K at night to 390 K at noon, every month. One metre down the number "
       + "does not move at all. That steady deep temperature decides whether ice "
       + "survives, and no instrument can measure it from orbit — it has to be "
       + "calculated." });

// =============================================================== 3  GAP
hero({ kicker: "The problem", fig: "lay_gap.png", stage: 1,
  title: "Every model uses one number for the whole Moon",
  take: "It was fitted from orbit, and a satellite only feels the top few centimetres.",
  notes: "50 s. CONTENT: the Moon carrying K_d = 3.4, then three beats — "
       + "calibrated from orbit; subsurface measurements that have checked it: "
       + "ZERO; places where it can be tested: TWO.\n\n"
       + "SAY: land the two numerals, 3.4 and 0. The number is not wrong because "
       + "anyone was careless — it is unchecked because until now there was no way "
       + "to check it. Hand off to the two places where there is." });

// =============================================================== 4  DATA 1
hero({ kicker: "The Apollo data  ·  1 of 2", fig: "lay_boreholes.png", stage: 1,
  title: "Only two holes have ever been drilled and instrumented",
  take: "Apollo 15 and 17, 1971 to 1977. The records were recovered from the original mission tapes.",
  notes: "55 s. CONTENT: both boreholes to scale — Apollo 15 at 1.4 m with 7 "
       + "usable sensors, Apollo 17 at 2.3 m with 16 — the top 80 cm shaded out "
       + "as drilling-disturbed, the real Clementine globe from the thesis "
       + "(Fig 1.2a) with both sites marked, and three scarcity facts.\n\n"
       + "SAY: the astronauts drilled and left thermometers. This is still today "
       + "the only subsurface temperature data anywhere on the Moon. I throw away "
       + "everything above 80 cm because the drilling disturbed it, which leaves "
       + "23 trustworthy sensors: seven and sixteen. Nothing like it is coming "
       + "again." });

// =============================================================== 5  ROADMAP
hero({ kicker: "The whole study", accent: TEAL, fig: "gb_pipeline.png", stage: 1,
  title: "The whole study on one slide",
  take: "Three things going in, four steps in the middle, three numbers coming out. Everything after this slide is one of those boxes.",
  notes: "40 s. CONTENT: guidebook Figure 2.1, the published retrieval pipeline. "
       + "Three inputs (the restored Apollo HFE record; the Hayne K(T,z) form "
       + "with one free knob; the published basal flux Q_b), four processes "
       + "(stable window, forward solve, sweep, uncertainty), three results.\n\n"
       + "SAY: walk the three columns with your hand. Do NOT read the equations "
       + "aloud. The one sentence that matters: only ONE thing in the input column "
       + "is unknown — everything else is measured or published. Then: every "
       + "remaining slide in Part 1 is one of these boxes." });

// =============================================================== 6  DATA 2
hero({ kicker: "The Apollo data  ·  2 of 2", accent: TEAL,
  fig: "lay_window.png", stage: 2,
  title: "Turning six years of wobble into one honest number",
  take: "An automatic rule picks the flattest trailing stretch of each record. No sensor is chosen by hand.",
  notes: "55 s. CONTENT: a real Apollo 15 record. Early years shaded coral "
       + "(drilling heat, mission disturbances, instrument drift); the selected "
       + "flat tail shaded green; the resulting single equilibrium temperature. "
       + "The rule in three lines: longest flat tail, reject if drift is worse "
       + "than 0.08 K per year, carry the leftover drift as an error.\n\n"
       + "SAY: nothing here is hand-picked. The same rule runs on every sensor and "
       + "anyone can reproduce it. 23 of the deep sensors qualify. The full "
       + "decision tree is backup — see the window-rule flowchart." });

// =============================================================== 7  PHYSICS
hero({ kicker: "The physics", accent: TEAL, fig: "lay_model.png", stage: 2,
  title: "A simple picture of the ground, and the equations behind it",
  take: "Sunlight in at the top, heat radiated back to space, a steady trickle from the interior below — and exactly one unknown in the middle.",
  notes: "40 s. CONTENT: one column of soil with the three energy flows, plus "
       + "THE GOVERNING EQUATIONS, each next to what it governs: heat conduction "
       + "in the column; the Hayne (2017) conductivity K(T,z) with its contact and "
       + "radiative terms; the non-linear surface energy balance; and the fixed "
       + "geothermal flux as the basal condition.\n\n"
       + "SAY: say plainly that this part is standard one-dimensional heat "
       + "conduction — nothing here is new. Saying so buys credibility for the "
       + "next three slides, where something is. Point at K_d: everything in these "
       + "four equations is measured or published except that one symbol." });

// =============================================================== 8  BLIND
split({ kicker: "How the Apollo data is used", accent: TEAL,
  fig: "gb_dataenters_slide.png", figW: 6.2, stage: 2,
  title: "The model runs blind — the data enters only at the fit",
  take: "The forward model never sees a thermometer. Apollo data touches the pipeline at exactly one step: scoring how badly each trial missed.",
  points: [
    ["The model is not tuned to the data",
     "sunlight, conductivity form and basal flux go in; a predicted deep profile comes out, with no Apollo input at all"],
    ["The data scores, it does not steer",
     "the 23 measured temperatures enter once, as the misfit RMSE(K_d) that ranks the trials"],
    ["So the fit is a test, not a fit",
     "the retrieved value is the one profile that happens to pass through measurements the model never saw"],
  ],
  notes: "50 s. CONTENT: guidebook flowchart — trial K_d enters a blind forward "
       + "solve, the predicted deep profile meets the Apollo sensors only at the "
       + "misfit step, and the smallest RMSE picks K_d*.\n\n"
       + "SAY: this is the slide that answers 'did you just fit your own data?'. "
       + "The physics never sees a thermometer. That is why slide 12, where the "
       + "modelled profile lands on the measurements, is evidence rather than "
       + "circular reasoning." });

// =============================================================== 9  WALL
split({ kicker: "The anchor method  ·  1 of 2", accent: FOREST,
  fig: "gb_costnesting.png", figW: 7.1, stage: 2,
  title: "Why this calculation was impossible",
  take: "Three nested loops: one time step, inside the settling loop, inside the sweep over candidate values.",
  points: [
    ["~3000 lunations to settle",
     "the deep column relaxes on a slow diffusive clock, not on the daily one"],
    ["27 hours for one experiment",
     "and a sweep needs about thirty of them, before any error analysis"],
    ["Which is why nobody had checked",
     "the uncertainty analysis on slide 13 is simply unaffordable at this cost"],
  ],
  notes: "45 s. CONTENT: the guidebook cost-nesting figure — the K_d sweep (x30) "
       + "wrapping the anchor loop (x6-10) wrapping one Crank-Nicolson step "
       + "(x~136,000).\n\n"
       + "SAY: this is the wall. Not 'slow' — not possible. Say the multipliers "
       + "out loud, then set up the next slide: the way through is to stop "
       + "simulating the part that does not need simulating." });

// =============================================================== 10 SOLVER
hero({ kicker: "The anchor method  ·  2 of 2", accent: FOREST,
  fig: "lay_solver.png", stage: 2,
  title: "The calculation used to take a day. Now it takes a minute.",
  take: "Once the ground repeats the same monthly cycle, the deep part can be rebuilt from a single anchor point instead of simulated.",
  notes: "70 s. STAR SLIDE. CONTENT: the same 5 m column twice. Left, every cell "
       + "hatched and time-stepped for ~3000 lunations, 27 hours. Right, only the "
       + "top 0.7 m hatched, the anchor marked at 0.55 m, everything below rebuilt "
       + "from the closure equation — under a minute, about 2500x faster. The "
       + "closure itself is printed along the bottom.\n\n"
       + "SAY: once the ground repeats the same monthly cycle, the average heat "
       + "flowing through it is the same at every depth. That single constraint "
       + "removes the need to simulate the deep column. Kettle analogy if eyes "
       + "glaze: you do not need to watch a kettle boil three thousand times to "
       + "know what temperature it ends at. ALWAYS pair the speed claim with the "
       + "accuracy claim — same answer to better than 0.01 mW. The five-move "
       + "derivation is in backup." });

// =============================================================== 11 RESULT 1
hero({ kicker: "Result  ·  1 of 2", fig: "lay_results.png", stage: 3,
  title: "Both sites hold heat differently than the textbook value",
  take: "Apollo 17 lets heat through about 1.5× more easily than Apollo 15, and both exceed the single global value.",
  notes: "65 s. STAR SLIDE. CONTENT: two bars with 95% bootstrap whiskers; the "
       + "global 3.4 as a dashed reference LINE, not a bar, because it is not a "
       + "measurement of these sites; the 1.5x bracket; and the fit-improvement "
       + "cards.\n\n"
       + "SAY: the numbers out loud — 4.60 and 7.08 against a global 3.4. Then the "
       + "evidence nobody asks for but everyone should: the fit got BETTER. At "
       + "Apollo 17 the mismatch more than halved, 0.89 to 0.40 K; at Apollo 15 it "
       + "improved from 1.09 to 1.00." });

// =============================================================== 12 RESULT 2
hero({ kicker: "Result  ·  2 of 2", fig: "th_profiles.png", stage: 3,
  title: "The model against the actual thermometers",
  take: "The retrieved value is not a number from an optimiser. It is the profile that passes through measurements the model never saw.",
  notes: "50 s. CONTENT: thesis Figure 5.5, meter-scale panels. The modelled "
       + "temperature column at the retrieved K_d* drawn through the real HFE "
       + "sensors at both sites, with the Martinez & Siegler forward curve as an "
       + "independent comparison, and the borestem base marked at 80 cm.\n\n"
       + "SAY: this is the whole claim in one picture, and it is the pay-off of "
       + "slide 8 — the model was blind to these points. Note the shallow sensors "
       + "are drawn open: they were excluded, and they are excluded here too." });

// =============================================================== 13 SPREAD
hero({ kicker: "How sure am I?", accent: TEAL, fig: "lay_bootstrap.png", stage: 3,
  title: "Re-running the whole analysis 1500 times",
  take: "Randomly leaving sensors out and jittering their depths gives the full spread of answers the data can support.",
  notes: "45 s. CONTENT: left, what one draw is — sensors dropped at random, "
       + "depths jittered by 2.5 cm; right, the two resulting spreads with their "
       + "95% ranges printed.\n\n"
       + "SAY: the spreads barely overlap, which is why the ORDERING is solid. Do "
       + "NOT say p-value: nothing here was tested against a null hypothesis. It "
       + "is a bootstrap tail proportion and it comes out at 0.031. Then be honest "
       + "that the systematic budget is wider than the statistical one — which is "
       + "the next slide." });

// =============================================================== 14 CAVEAT
hero({ kicker: "The honest limit", accent: CORAL, fig: "lay_seesaw.png", stage: 3,
  title: "What I can claim, and what I cannot",
  take: "A thermometer buried in the ground measures the steepness of the temperature rise, and steepness is heat-from-below divided by conductivity.",
  notes: "60 s. STAR SLIDE. CONTENT: the degeneracy drawn as a balance — Q_b on "
       + "one pan, K_d on the other, the thermometers seeing only the tilt, and a "
       + "ghosted second pair showing that doubling both gives an identical tilt. "
       + "Then two cards: what is solid, and what is not settled.\n\n"
       + "SAY: calmly, and do not apologise. My data alone cannot fully separate "
       + "'the ground conducts differently' from 'more heat is arriving from "
       + "below'. What IS solid: Apollo 17 is the more conductive site, in more "
       + "than 99% of tested cases. What is NOT: the exact size of the gap — the "
       + "95% range on the difference still touches zero, and I say so in the "
       + "thesis rather than rounding it away." });

// =============================================================== 15 CONCLUSION
{
  const s = newSlide(); s.background = { color: WHITE };
  kicker(s, "In three sentences", FOREST);
  title(s, "Conclusions");
  hairline(s);
  const row = (y, num, h, sub, col) => {
    s.addShape(pres.ShapeType.ellipse, { x: 0.85, y, w: 0.62, h: 0.62, fill: { color: col } });
    s.addText(num, { x: 0.85, y, w: 0.62, h: 0.62, fontFace: HEAD, fontSize: 19,
      bold: true, color: WHITE, align: "center", valign: "middle", margin: 0 });
    s.addText(h, { x: 1.75, y: y + 0.02, w: 10.8, h: 0.42, fontFace: HEAD,
      fontSize: 19, bold: true, color: CHAR, margin: 0 });
    s.addText(sub, { x: 1.75, y: y + 0.46, w: 10.6, h: 0.5, fontFace: BODY,
      fontSize: 14, color: DIM, margin: 0 });
  };
  row(2.18, "1", "The two boreholes are genuinely different",
    "4.60 and 7.08 — Apollo 17 conducts heat about 1.5× more easily, and both beat the global 3.4", FOREST);
  row(3.56, "2", "A calculation that took a day now takes a minute",
    "the flux-anchored solver, about 2500× faster, which is what made the uncertainty analysis possible", TEAL);
  row(4.94, "3", "This is the ground truth future Moon missions need",
    "instruments that see beneath the surface need a temperature profile no satellite can measure", CORAL);
  s.addShape(pres.ShapeType.roundRect, { x: 0.85, y: 6.10, w: 11.6, h: 0.72,
    fill: { color: TINT }, line: { color: GRID, width: 1 }, rectRadius: 0.06 });
  s.addText("The honest caveat: the size of the difference is not yet nailed down, only its direction.",
    { x: 1.1, y: 6.10, w: 11.1, h: 0.72, fontFace: BODY, fontSize: 14, italic: true,
      color: CHAR, valign: "middle", margin: 0 });
  s.addNotes("55 s. CONTENT: three numbered rows and the caveat bar.\n\n"
    + "SAY: land the three, then stop talking. No thank-you slide — end here so "
    + "the last thing on screen is the result.");
  foot(s);
}

// =============================================================== 16 DIVIDER
dark({ kicker: "Part 2", title: "Doctoral Research Plan",
  sub: "From two holes in the ground to a map of the whole Moon",
  notes: "10 s. Change of gear: 'that is what I have done — here is where it "
       + "goes.' The move in Part 2 is three slides of FINISHED work before a "
       + "single promise." });

// =============================================================== 17 GOAL
hero({ kicker: "The goal", fig: "lay_global.png",
  title: "Two points are not a map",
  take: "Where ice can survive is a question about the whole Moon, not about two Apollo sites.",
  notes: "35 s. CONTENT: two measured dots today, a Moon-wide subsurface field at "
       + "the end, and a three-year arrow with Y1/Y2/Y3 ticks that come back on "
       + "slide 21.\n\nSAY: state the ambition plainly, then spend the rest "
       + "showing it is already underway." });

// =============================================================== 18 DONE 1
hero({ kicker: "Already built  ·  not a proposal", accent: FOREST, fig: "shadowing.gif",
  title: "Step 1: put the real landscape into the model",
  take: "Mountains shade the ground and radiate back onto it. Apollo 15 loses 1.16% of its sunlight to the Apennine front; Apollo 17 loses 0.18%.",
  notes: "55 s. CONTENT: the DEM horizon ring at Apollo 15 with the Sun tracking "
       + "through it, and the resulting irradiance over one lunar day.\n\n"
       + "SAY: my thesis assumed flat ground. Apollo 15 sits at the foot of the "
       + "Apennines, Apollo 17 in a valley between two massifs. Horizons reach "
       + "14.0 degrees and 10.1 degrees. Stress the words ALREADY BUILT — this was "
       + "presented at AOGS." });

// =============================================================== 19 DONE 2
hero({ kicker: "Already built  ·  not a proposal", accent: FOREST, fig: "lay_cpvc.png",
  title: "Step 2: find out which property actually matters",
  take: "650 model runs. Density matters mainly through conductivity, not through heat storage, and a layered ground beats a uniform one by 2.6× at Apollo 15 and 10× at Apollo 17.",
  notes: "65 s. STAR SLIDE of Part 2. CONTENT: left, density does two jobs — "
       + "storage and conductivity — and which one the answer cares about; right, "
       + "layered versus cross-applied versus uniform, all on one shared scale.\n\n"
       + "SAY: be honest about the left panel. The coupling halves the error at "
       + "Apollo 15 (1.74 to 0.90 K) and barely moves Apollo 17 (0.39 to 0.36 K), "
       + "because that site already fits well. Do not overstate it — a committee "
       + "that checks will find it. The point: the controlling parameter was "
       + "identified BEFORE the PhD was proposed." });

// =============================================================== 20 DONE 3
{
  const s = newSlide(); s.background = { color: WHITE };
  kicker(s, "Already built  ·  the key test", FOREST);
  title(s, "Step 3: check that the physics travels");
  s.addText("Each site's best setup was applied, untouched, at the other site. It still beat a uniform-property model, so this is transferable physics, not curve-fitting.",
    { x: MX, y: 1.24, w: CW, h: 0.5, fontFace: BODY, fontSize: 14.5, color: DIM, margin: 0 });
  hairline(s);
  const card = (x, lab, big, sub, col) => {
    s.addShape(pres.ShapeType.roundRect, { x, y: 2.35, w: 3.6, h: 3.1,
      fill: { color: TINT }, line: { color: GRID, width: 1 }, rectRadius: 0.07 });
    s.addShape(pres.ShapeType.rect, { x: x + 0.001, y: 2.45, w: 0.055, h: 2.9,
      fill: { color: col }, line: { width: 0 } });
    s.addText(lab, { x: x + 0.3, y: 2.62, w: 3.0, h: 0.35, fontFace: BODY,
      fontSize: 12, bold: true, color: col, charSpacing: 1, margin: 0 });
    s.addText(big, { x: x + 0.3, y: 3.05, w: 3.1, h: 0.85, fontFace: HEAD,
      fontSize: 27, bold: true, color: CHAR, margin: 0 });
    s.addText(sub, { x: x + 0.3, y: 4.0, w: 3.05, h: 1.15, fontFace: BODY,
      fontSize: 12.5, color: DIM, margin: 0 });
  };
  card(0.85, "ITS OWN SITE", "0.36 – 0.90", "the layered model at the site it was tuned on", FOREST);
  card(4.87, "THE OTHER SITE", "1.64 – 1.73", "the same setup moved across, untouched", TEAL);
  card(8.89, "UNIFORM GROUND", "2.31 – 3.76", "the old assumption, worse than both", DIM);
  s.addText("mismatch against the real Apollo thermometers  (K — lower is better)",
    { x: 0.85, y: 5.6, w: 11.6, h: 0.4, fontFace: BODY, fontSize: 13, italic: true,
      color: DIM, margin: 0 });
  s.addNotes("40 s. CONTENT: three stat cards, all in kelvin, lower is better.\n\n"
    + "SAY: I took the best configuration from one site and applied it, untouched, "
    + "at the other. If this were curve-fitting it would fall apart. Instead it "
    + "degrades gracefully and still beats the uniform assumption. Give the MIDDLE "
    + "card the weight — that is the licence to go global.");
  foot(s);
}

// =============================================================== 21 PLAN
hero({ kicker: "The plan", accent: CORAL, fig: "lay_planflow.png",
  title: "Three years, three deliverables",
  take: "Each year starts from something that already exists and ends in a product the next year needs.",
  notes: "80 s. STAR SLIDE. CONTENT: a flow, left to right and top to bottom — "
       + "what is already built feeds each year; each year hands over one "
       + "deliverable; the years run down a single spine.\n\n"
       + "SAY: one sentence per year, and say each DELIVERABLE out loud — that is "
       + "the line a committee listens for. Point out the left column: every year "
       + "begins from finished work, not from a wish. The Y1/Y2/Y3 markers are the "
       + "same three ticks they saw on slide 17." });

// =============================================================== 22 FEASIBLE
{
  const s = newSlide(); s.background = { color: CHAR };
  s.addText("WHY THIS IS ACHIEVABLE", { x: 1.0, y: 1.35, w: 11.3, h: 0.3, fontFace: BODY,
    fontSize: 12, bold: true, color: CORAL, charSpacing: 3, margin: 0 });
  s.addText("The hard part is already done", { x: 1.0, y: 1.8, w: 11.3, h: 0.8,
    fontFace: HEAD, fontSize: 33, bold: true, color: WHITE, margin: 0 });
  const row = (y, h, t) => {
    s.addShape(pres.ShapeType.ellipse, { x: 1.05, y: y + 0.07, w: 0.16, h: 0.16, fill: { color: CORAL } });
    s.addText(h, { x: 1.5, y, w: 10.8, h: 0.35, fontFace: HEAD, fontSize: 17,
      bold: true, color: WHITE, margin: 0 });
    s.addText(t, { x: 1.5, y: y + 0.37, w: 10.6, h: 0.45, fontFace: BODY, fontSize: 13.5,
      color: GRID, margin: 0 });
  };
  row(3.05, "The fast solver exists and is verified",
    "a Moon-wide map is millions of independent columns, and each one now costs a second");
  row(4.10, "The terrain and property studies are finished",
    "presented at AOGS; the controlling parameter is already identified");
  row(5.15, "The home for the work is in place",
    "Institute of Science Tokyo, Kasai Laboratory, with the NICT terahertz mission link");
  s.addNotes("50 s, then stop for questions. CONTENT: three feasibility rows.\n\n"
    + "SAY: this is not a wish list, it is the continuation of something already "
    + "running.");
}

// =============================================================== 23 BACKUP
dark({ kicker: "Appendix", title: "Backup slides",
  sub: "Kept for questions — not part of the timed presentation",
  notes: "Do not present. The next slide indexes everything here by the question "
       + "it answers; jump by slide number." });

// ---------------------------------------------------------- backup content
// [title, image, one-line answer, source, when to use]
const EVIDENCE = [
  ["Where the uncertainty comes from", "robustness.png",
   "The basal heat flux dominates at Apollo 15; the surface albedo dominates at Apollo 17.",
   "thesis Fig 5.12  ·  code/results/kd_error_budget.json",
   "Why is the error bar so wide?",
   "Why is the error bar so wide?"],
  ["The conductivity–heat-flow trade-off", "qbdeg.png",
   "The two sites respond to a flux revision in opposite directions, which is why the ordering survives.",
   "thesis Fig 5.11  ·  code/results/qb_degeneracy.json",
   "Could this be a heat-flow difference instead?",
   "Could this be a heat-flow difference?"],
  ["Is a per-site value statistically justified?", "aicc.png",
   "Decisive at Apollo 17. At Apollo 15 the global value is not formally rejected, and the case there rests on the confidence interval.",
   "thesis Fig 5.6  ·  ΔAICc −23.2 at A17, +2.9 at A15",
   "Is the difference significant? Answer this one honestly — Apollo 15's own model selection does NOT justify fitting it separately.",
   "Is the difference significant?"],
  ["Independent check against orbital data", "diviner.png",
   "Surface temperatures were never fitted, so this is a genuine out-of-sample test.",
   "thesis Fig 5.10  ·  code/results/diviner_closure.json",
   "How do you know the model is right?",
   "How do you know the model is right?"],
  ["Does it hold when you hold data back?", "holdout.png",
   "TG/TR cross-prediction and leave-one-deepest-out both reproduce the retrieved value.",
   "thesis Fig 5.7",
   "Are you over-fitting seven sensors?",
   "Are you over-fitting seven sensors?"],
  ["The Bayesian cross-check", "posterior.png",
   "Floating the basal flux instead of fixing it gives the same ordering, at 99.2%.",
   "thesis Fig 5.13  ·  code/results/bayesian_crosscheck_samples.json",
   "What if the published heat flow is wrong?",
   "What if the published heat flow is wrong?"],
  ["The bootstrap, as published", "bootstrap.png",
   "The journal version of slide 13, with both panels and the tail proportion.",
   "thesis Fig 5.4  ·  1500 draws, tail 0.031 (46/1500)",
   "Show me the real distribution.",
   "Show me the real distribution"],
  ["Finding the answer: the RMSE bowl", "lay_bowl.png",
   "Each site's misfit against candidate conductivity, with the minima and the global value marked.",
   "thesis Fig 5.2",
   "How exactly did you pick the value?",
   "How exactly did you pick the value?"],
  ["What the old method had to do", "anim_race.gif",
   "The old approach crawls toward the answer over thousands of cycles; the anchored solver arrives in four.",
   "code/results/speedup_benchmark.json",
   "Explain the speed-up in more detail.",
   "Explain the speed-up in more detail"],
  ["The AOGS parameter study, as presented", "aogs_cpvc.png",
   "The journal version of slide 19: the full density sweep and the coupling line.",
   "documents/aogs/results/aogs_density_study.json  ·  650 runs",
   "Show me the real analysis behind the doctoral plan.",
   "The real analysis behind the plan"],
];

const METHOD = [
  ["How one sensor becomes one temperature", "gb_windowflow.png",
   "The stability-window rule as a decision tree, ending at the 7 and 16 sensors that qualify.",
   "guidebook, windowflow"],
  ["From the heat equation to the closure", "gb_pde2odeflow.png",
   "Five moves collapse the two-variable PDE to a one-variable ODE in depth. The time term dies because the cycle closes.",
   "guidebook, pde2odeflow"],
  ["Brute force versus the anchor method", "gb_anchormethod_slide.png",
   "Which depths actually get time-stepped, side by side.",
   "guidebook, anchormethod"],
  ["Why the deep column is almost free", "gb_deepprofile_slide.png",
   "Below the anchor the mean profile is a straight line of slope Q_b/K, so one downward integration replaces ~1000 lunations.",
   "guidebook, deepprofile"],
  ["Step A and Step B, in full", "gb_stepsAB_flow.png",
   "The complete two-stage anchor schedule, with the tolerances and what each stage produces.",
   "guidebook, stepsAB"],
  ["The outer loop and its convergence test", "gb_anchorflow.png",
   "Iterate Step A and Step B until the anchor stops moving; the test is anchor drift, not a fixed cycle count.",
   "guidebook, anchorflow"],
  ["How a converged solve is certified", "gb_certflow.png",
   "Guess independence, flux closure, and an honest 120-lunation re-run. All three, or it does not enter the sweep.",
   "guidebook, certflow"],
  ["One Crank–Nicolson time step", "gb_marchflow.png",
   "Properties, tridiagonal assembly, Newton surface balance, Thomas solve — and the wrap step that closes the cycle.",
   "guidebook, marchflow"],
  ["The depth grid", "gb_gridcells.png",
   "Geometric cells, 2 mm at the surface growing 8% each, 69 cells to 5 m, with harmonic-mean face conductivity.",
   "guidebook, gridcells"],
  ["One bootstrap draw, in full", "gb_bootflow.png",
   "Resample with replacement, jitter each depth, refit from cached profiles — no new solver call.",
   "guidebook, bootflow"],
  ["The Bayesian cross-check, step by step", "gb_mcmcflow.png",
   "32 walkers over (K_d, Q_b), scored against a surface of 117 real solves per site.",
   "guidebook, mcmcflow"],
  ["Three disjoint slices of physics", "gb_crosschecks.png",
   "Diviner surface closure, the Martínez density model, and the robustness battery — no single choice carries the result.",
   "guidebook, crosschecks"],
  ["The three bugs, and what each cost", "gb_threebugs.png",
   "A wrong basal flux, an under-resolved inner loop, and a skipped wrap step. Symptom, fix, and the effect on the answer.",
   "guidebook, threebugs"],
  ["How a number earns its way in", "gb_inputflow.png",
   "Cited, convergence-tested, or budgeted — otherwise treated as wrong until proven otherwise. This posture found all three bugs.",
   "guidebook, inputflow"],
  ["Reproducing the whole chain", "gb_makeflow.png",
   "make retrieve, make aux, make figures, make paper. Everything in the thesis regenerates from these four.",
   "guidebook, makeflow"],
];

// slide numbers: 23 is the divider (unnumbered by foot()), 24 is this index
const IDX_NO = n + 1;                    // the index slide's own number
let no = IDX_NO;
const evNums = EVIDENCE.map(() => ++no);
const mtNums = METHOD.map(() => ++no);

// =============================================================== 24 INDEX
{
  const s = newSlide(); s.background = { color: WHITE };
  kicker(s, "Appendix", DIM);
  title(s, "Backup index — jump by slide number");
  hairline(s);
  const col = (x, heading, rows, col2) => {
    s.addText(heading, { x, y: 1.98, w: 5.6, h: 0.3, fontFace: BODY, fontSize: 11.5,
      bold: true, color: col2, charSpacing: 1.5, margin: 0 });
    s.addText(rows.map((r, i) => ({ text: r, options: { breakLine: i !== rows.length - 1 } })),
      { x, y: 2.36, w: 5.7, h: 4.3, fontFace: BODY, fontSize: 11.5, color: CHAR,
        lineSpacingMultiple: 1.32, margin: 0, valign: "top" });
  };
  col(MX, "EVIDENCE  ·  thesis figures",
    EVIDENCE.map((e, i) => `${evNums[i]}   ${e[5]}`), CORAL);
  col(MX + 6.1, "METHOD IN DEPTH  ·  guidebook flowcharts",
    METHOD.map((m, i) => `${mtNums[i]}   ${m[0]}`), TEAL);
  s.addNotes("Do not present. This is the map you use during Q&A: find the "
    + "question on the left or the method on the right and jump to that number.");
  foot(s);
}

EVIDENCE.forEach(([t, f, take, src, use]) => {
  evidence({ title: t, fig: f, take, src: "Source: " + src,
    notes: "BACKUP — use if asked: " + use });
});
METHOD.forEach(([t, f, take, src]) => {
  evidence({ kicker: "Backup  ·  method in depth", title: t, fig: f, take,
    src: "Source: " + src,
    notes: "BACKUP — guidebook flowchart, shown as published. Use for a "
         + "method question; do not present." });
});

// =============================================================== 50 TERMS
{
  const s = newSlide(); s.background = { color: WHITE };
  kicker(s, "Required appendix", DIM);
  title(s, "Technical terms  ·  専門用語対訳表");
  hairline(s);
  const pairs = [
    ["Thermal conductivity", "熱伝導率"], ["Regolith", "レゴリス"],
    ["Heat flow / heat flux", "熱流量"], ["Basal heat flux", "底部熱流量"],
    ["Borehole", "掘削孔"], ["Diurnal variation", "日変化"],
    ["Thermal skin depth", "熱表皮深さ"], ["Periodic steady state", "周期定常状態"],
    ["Finite difference method", "差分法"], ["Boundary condition", "境界条件"],
    ["Equilibrium temperature", "平衡温度"], ["Bootstrap (resampling)", "ブートストラップ法"],
    ["Confidence interval", "信頼区間"], ["Statistical error", "統計誤差"],
    ["Systematic error", "系統誤差"], ["Degeneracy", "縮退"],
    ["Albedo", "アルベド"], ["Emissivity", "放射率"],
    ["Digital elevation model", "数値標高モデル"], ["Topographic shadowing", "地形遮蔽"],
    ["Radiative transfer", "放射伝達"], ["Root-mean-square error", "二乗平均平方根誤差"],
  ];
  const mid = Math.ceil(pairs.length / 2);
  const mk = (arr) => arr.map(([e, j]) => ([
    { text: e, options: { fontFace: BODY, fontSize: 11.5, color: CHAR } },
    { text: j, options: { fontFace: BODY, fontSize: 11.5, color: TEAL } },
  ]));
  const opt = { y: 2.00, w: 6.0, colW: [3.3, 2.7],
    border: { type: "solid", color: GRID, pt: 0.5 }, rowH: 0.235,
    valign: "middle", margin: [2, 6, 2, 6] };
  s.addTable(mk(pairs.slice(0, mid)), Object.assign({}, opt, { x: MX }));
  s.addTable(mk(pairs.slice(mid)), Object.assign({}, opt, { x: 6.92 }));
  s.addText("Thesis title:  Difference of Lunar Regolith Thermal Conductivity K_d at the Apollo 15 and 17 Heat-Flow Boreholes",
    { x: MX, y: 6.62, w: CW, h: 0.3, fontFace: BODY, fontSize: 11, color: DIM, margin: 0 });
  s.addText("Japanese readings to be confirmed by Kasai Laboratory before submission.",
    { x: MX, y: 6.92, w: CW, h: 0.3, fontFace: BODY, fontSize: 10, italic: true,
      color: DIM, margin: 0 });
  s.addNotes("Required by GEDES and must remain the LAST slide.");
  foot(s);
}

pres.writeFile({ fileName: path.join(__dirname, "24M58378Gregorio.pptx") })
  .then((f) => console.log("wrote", f, "—", n, "numbered +", "2 dark dividers"));
