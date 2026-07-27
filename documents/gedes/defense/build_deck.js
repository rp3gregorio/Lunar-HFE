// GEDES defense deck — figure-led, built for a non-specialist audience.
//   Part 1  Master's thesis      12 min + 5 min Q&A
//   Part 2  Doctoral plan         6 min + 7 min Q&A
//   Part 3  Backup slides for Q&A (not presented)
//   Final   EN/JP technical-term table (required by GEDES)
//
// Design: white stage, charcoal type, thesis palette accents. The purpose-built
// lay-audience artwork (img/lay_*.png, img/anim_*.gif) is the hero of every
// slide; text is reduced to a title plus one takeaway line so the room looks at
// the picture, not at paragraphs.
const pptxgen = require("pptxgenjs");
const fs = require("fs");
const path = require("path");

const IMGDIR = path.join(__dirname, "img");
const P = (f) => path.join(IMGDIR, f);

// read intrinsic pixel size straight from the PNG/GIF header -> exact aspect
function aspect(file) {
  const b = fs.readFileSync(P(file));
  if (file.endsWith(".gif")) return b.readUInt16LE(6) / b.readUInt16LE(8);
  return b.readUInt32BE(16) / b.readUInt32BE(20);        // PNG IHDR
}

const CHAR = "2A2520", CORAL = "B85B3A", TEAL = "2A6478", FOREST = "3D6E4A";
const DIM = "6E6862", GRID = "E8E5E0", WHITE = "FFFFFF", TINT = "F7F5F2";
const HEAD = "Cambria", BODY = "Calibri";

const pres = new pptxgen();
pres.layout = "LAYOUT_WIDE";                              // 13.333 x 7.5 in
pres.author = "Ramon III P. Gregorio";
pres.title = "Difference of Lunar Regolith Thermal Conductivity Kd";

let n = 0;
const foot = (s) => {
  n++;
  s.addText(String(n), { x: 12.45, y: 6.98, w: 0.55, h: 0.3, fontFace: BODY,
    fontSize: 10, color: GRID, align: "right", margin: 0 });
};
const kicker = (s, t, c) => s.addText(t.toUpperCase(), {
  x: 0.72, y: 0.32, w: 11.9, h: 0.28, fontFace: BODY, fontSize: 11,
  bold: true, color: c || CORAL, charSpacing: 2, margin: 0 });
const title = (s, t) => s.addText(t, {
  x: 0.72, y: 0.62, w: 11.9, h: 0.62, fontFace: HEAD, fontSize: 29,
  bold: true, color: CHAR, margin: 0, valign: "top" });

// fit an image inside a box, centred
function fit(file, bx, by, bw, bh) {
  const ar = aspect(file);
  let w = bw, h = bw / ar;
  if (h > bh) { h = bh; w = bh * ar; }
  return { path: P(file), x: bx + (bw - w) / 2, y: by + (bh - h) / 2, w, h };
}

/** Hero slide: kicker + title + one takeaway line + one big picture. */
function hero(o) {
  const s = pres.addSlide(); s.background = { color: WHITE };
  kicker(s, o.kicker, o.accent); title(s, o.title);
  let top = 1.42;
  if (o.take) {
    s.addText(o.take, { x: 0.72, y: 1.26, w: 11.9, h: 0.42, fontFace: BODY,
      fontSize: 14.5, color: DIM, margin: 0 });
    top = 1.86;
  }
  s.addImage(fit(o.fig, 0.72, top, 11.9, 6.82 - top));
  if (o.notes) s.addNotes(o.notes);
  foot(s); return s;
}

function dark(o) {
  const s = pres.addSlide(); s.background = { color: CHAR };
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
  const s = pres.addSlide(); s.background = { color: CHAR };
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
  s.addNotes("Plain-language title on purpose: the panel is not made of lunar scientists. "
    + "The formal thesis title is on the term-table slide and in the abstract.");
}

// =============================================================== 2  WHY
hero({ kicker: "Why this matters", fig: "anim_hook.gif",
  title: "The surface is violent. A metre down, nothing moves.",
  take: "Ice can only survive where the ground stays cold and steady — and that is decided below the surface.",
  notes: "~50 s. Let the animation run one full loop before you speak over it. "
       + "Point out: the surface line whips back and forth, the deep line is frozen still." });

// =============================================================== 3  GAP
hero({ kicker: "The problem", fig: "lay_gap.png",
  title: "Every model uses one number for the whole Moon",
  notes: "~55 s. The key sentence: this number was fitted from orbit, and orbit only "
       + "senses the top few centimetres. Nobody has ever checked it against the deep ground." });

// =============================================================== 4  DATA
hero({ kicker: "The data", fig: "lay_boreholes.png",
  title: "Only two holes have ever been drilled and instrumented",
  take: "Apollo 15 and 17, 1971–1977. The records were recovered from the original mission tapes.",
  notes: "~55 s. Emphasise scarcity and irreplaceability. 23 sensors survive the cut." });

// =============================================================== 5  STEP 1
hero({ kicker: "Step 1 of 3  ·  preparing the data", accent: TEAL, fig: "lay_window.png",
  title: "Turning six years of wobble into one honest number",
  notes: "~55 s. This is my own automatic rule — no hand-picking. Mention it is reproducible "
       + "and that the leftover drift is carried as an error, not ignored." });

// =============================================================== 6  STEP 2
hero({ kicker: "Step 2 of 3  ·  the physics", accent: TEAL, fig: "lay_model.png",
  title: "A simple picture of the ground",
  take: "Sunlight in at the top, heat radiated back to space, a steady trickle of heat from the interior below.",
  notes: "~50 s. Keep it short — it is standard physics. The only unknown is how easily "
       + "heat moves through the middle." });

// =============================================================== 7  STEP 3 (star)
hero({ kicker: "Step 3 of 3  ·  my contribution", accent: FOREST, fig: "lay_solver.png",
  title: "The calculation used to take a day. Now it takes a minute.",
  take: "Once the ground repeats the same monthly cycle, the deep part can be rebuilt from a single anchor point instead of simulated.",
  notes: "STAR SLIDE, ~80 s. This is the methodological contribution. Analogy that works: "
       + "you do not need to watch a kettle boil 3000 times to know its final temperature. "
       + "Consequence: uncertainty analysis becomes affordable, which is the next slide." });

// =============================================================== 8  SWEEP
hero({ kicker: "Finding the answer", accent: TEAL, fig: "lay_bowl.png",
  title: "Try every value, keep the one that fits best",
  notes: "~50 s. Because each try is now a second instead of a day, we can afford to try "
       + "hundreds of values and repeat the whole thing 1500 times for error bars." });

// =============================================================== 9  RESULT (star)
hero({ kicker: "Result", fig: "lay_results.png",
  title: "Both sites hold heat differently than the textbook value",
  take: "Apollo 17 lets heat through about 1.5× more easily than Apollo 15 — and both exceed the single global value.",
  notes: "STAR SLIDE, ~75 s. Say the numbers out loud: 4.60 and 7.08 against a global 3.4. "
       + "Then say the fit got better: the Apollo 17 mismatch more than halved." });

// =============================================================== 10 UNCERTAIN
hero({ kicker: "How sure am I?", fig: "bootstrap.png",
  title: "Re-running the whole analysis 1500 times",
  take: "Randomly leaving sensors out and jittering their depths gives the spread of answers the data can support.",
  notes: "~55 s. Point to the two humps: they barely overlap, which is why the ORDERING is "
       + "solid. Then be honest that the systematic budget is wider than the statistical one." });

// =============================================================== 11 CAVEAT (star)
hero({ kicker: "The honest limit", accent: CORAL, fig: "lay_seesaw.png",
  title: "What I can claim, and what I cannot",
  notes: "STAR SLIDE, ~65 s. Do not rush this. Saying it plainly is a strength: the "
       + "thermometers measure a ratio, so a difference in conductivity and a difference in "
       + "heat-from-below look the same. The ordering survives; the exact size does not." });

// =============================================================== 12 CONCLUSION
{
  const s = pres.addSlide(); s.background = { color: WHITE };
  kicker(s, "In three sentences", FOREST);
  title(s, "Conclusions");
  const row = (y, num, head, sub, col) => {
    s.addShape(pres.ShapeType.ellipse, { x: 0.85, y, w: 0.62, h: 0.62, fill: { color: col } });
    s.addText(num, { x: 0.85, y, w: 0.62, h: 0.62, fontFace: HEAD, fontSize: 19,
      bold: true, color: WHITE, align: "center", valign: "middle", margin: 0 });
    s.addText(head, { x: 1.75, y: y + 0.02, w: 10.8, h: 0.42, fontFace: HEAD,
      fontSize: 19, bold: true, color: CHAR, margin: 0 });
    s.addText(sub, { x: 1.75, y: y + 0.46, w: 10.6, h: 0.5, fontFace: BODY,
      fontSize: 14, color: DIM, margin: 0 });
  };
  row(1.72, "1", "The two boreholes are genuinely different",
    "4.60 and 7.08 — Apollo 17 conducts heat about 1.5× more easily, and both beat the global 3.4", FOREST);
  row(3.20, "2", "A calculation that took a day now takes a minute",
    "the flux-anchored solver, about 2500× faster, which is what made the error analysis possible", TEAL);
  row(4.68, "3", "This is the ground truth future Moon missions need",
    "instruments that see beneath the surface need a temperature profile no satellite can measure", CORAL);
  s.addShape(pres.ShapeType.roundRect, { x: 0.85, y: 6.10, w: 11.6, h: 0.78,
    fill: { color: TINT }, line: { color: GRID, width: 1 }, rectRadius: 0.06 });
  s.addText("The honest caveat: the size of the difference is not yet nailed down — only its direction.",
    { x: 1.1, y: 6.10, w: 11.1, h: 0.78, fontFace: BODY, fontSize: 14, italic: true,
      color: CHAR, valign: "middle", margin: 0 });
  s.addNotes("~60 s. Land these three, then stop talking. Do not add a 'thank you' slide — "
    + "end here so the last thing on screen is the result.");
  foot(s);
}

// =============================================================== 13 DIVIDER
dark({ kicker: "Part 2", title: "Doctoral Research Plan",
  sub: "From two holes in the ground to a map of the whole Moon",
  notes: "6 min from here. Change of gear: say 'that was what I have done — here is where it goes next.'" });

// =============================================================== 14 VISION
hero({ kicker: "The goal", fig: "lay_global.png",
  title: "Two points are not a map",
  take: "Where ice can survive is a question about the whole Moon, not about two Apollo sites.",
  notes: "~35 s. State the ambition plainly, then spend the rest showing it is already underway." });

// =============================================================== 15 DONE 1
hero({ kicker: "Already built  ·  not a proposal", accent: FOREST, fig: "shadowing.gif",
  title: "Step 1: put the real landscape into the model",
  take: "Mountains shade the ground and radiate back onto it. Apollo 15 loses 1.16% of its sunlight to the Apennine front; Apollo 17 loses 0.18%.",
  notes: "~55 s. Stress the words ALREADY BUILT. This was presented at AOGS. "
       + "It is the piece that makes a global model physically honest." });

// =============================================================== 16 DONE 2 (star)
hero({ kicker: "Already built  ·  not a proposal", accent: FOREST, fig: "aogs_cpvc.png",
  title: "Step 2: find out which property actually matters",
  take: "650 model runs. Heat capacity barely moves the answer; density-linked conductivity moves it a lot — and layering beats a uniform ground by 2.6× at Apollo 15 and 10× at Apollo 17.",
  notes: "STAR SLIDE of part 2, ~65 s. This answers 'do you know what you are doing?' — "
       + "I have already identified the controlling parameter before proposing the PhD." });

// =============================================================== 17 TRANSFERS
{
  const s = pres.addSlide(); s.background = { color: WHITE };
  kicker(s, "Already built  ·  the key test", FOREST);
  title(s, "Step 3: check that the physics travels");
  s.addText("Each site's best setup was applied, untouched, at the other site. It still beat a uniform-property model — so this is transferable physics, not curve-fitting.",
    { x: 0.72, y: 1.26, w: 11.9, h: 0.6, fontFace: BODY, fontSize: 14.5, color: DIM, margin: 0 });
  const card = (x, lab, big, sub, col) => {
    s.addShape(pres.ShapeType.roundRect, { x, y: 2.35, w: 3.6, h: 3.1,
      fill: { color: TINT }, line: { color: GRID, width: 1 }, rectRadius: 0.07 });
    s.addText(lab, { x: x + 0.3, y: 2.62, w: 3.0, h: 0.35, fontFace: BODY,
      fontSize: 12, bold: true, color: col, charSpacing: 1, margin: 0 });
    s.addText(big, { x: x + 0.3, y: 3.05, w: 3.1, h: 0.85, fontFace: HEAD,
      fontSize: 27, bold: true, color: CHAR, margin: 0 });
    s.addText(sub, { x: x + 0.3, y: 4.0, w: 3.05, h: 1.15, fontFace: BODY,
      fontSize: 12.5, color: DIM, margin: 0 });
  };
  card(0.85, "ITS OWN SITE", "0.36 – 0.90", "the layered model at the site it was tuned on", FOREST);
  card(4.87, "THE OTHER SITE", "1.64 – 1.73", "the same setup moved across, untouched", TEAL);
  card(8.89, "UNIFORM GROUND", "2.31 – 3.76", "the old assumption — worse than both", DIM);
  s.addText("mismatch against the real Apollo thermometers  (K — lower is better)",
    { x: 0.85, y: 5.6, w: 11.6, h: 0.4, fontFace: BODY, fontSize: 13, italic: true,
      color: DIM, margin: 0 });
  s.addNotes("~40 s. This is the single strongest argument that a global model is justified.");
  foot(s);
}

// =============================================================== 18 PLAN (star)
{
  const s = pres.addSlide(); s.background = { color: WHITE };
  kicker(s, "The plan", CORAL);
  title(s, "Three years, three deliverables");
  const yr = (x, tag, head, items, deliv, col) => {
    s.addShape(pres.ShapeType.roundRect, { x, y: 1.62, w: 3.76, h: 4.75,
      fill: { color: TINT }, line: { color: GRID, width: 1 }, rectRadius: 0.06 });
    s.addShape(pres.ShapeType.ellipse, { x: x + 0.3, y: 1.88, w: 0.6, h: 0.6, fill: { color: col } });
    s.addText(tag, { x: x + 0.3, y: 1.88, w: 0.6, h: 0.6, fontFace: HEAD, fontSize: 16,
      bold: true, color: WHITE, align: "center", valign: "middle", margin: 0 });
    s.addText(head, { x: x + 0.3, y: 2.62, w: 3.15, h: 0.45, fontFace: HEAD,
      fontSize: 17, bold: true, color: CHAR, margin: 0 });
    s.addText(items.map((t, i) => ({ text: t,
      options: { bullet: true, breakLine: i !== items.length - 1 } })), {
      x: x + 0.3, y: 3.15, w: 3.15, h: 2.05, fontFace: BODY, fontSize: 12.5,
      color: CHAR, paraSpaceAfter: 7, lineSpacingMultiple: 1.1, margin: 0, valign: "top" });
    s.addText([{ text: "DELIVERABLE\n", options: { bold: true, color: col, fontSize: 9.5 } },
               { text: deliv, options: { color: CHAR, fontSize: 12 } }],
      { x: x + 0.3, y: 5.35, w: 3.15, h: 0.85, fontFace: BODY, margin: 0, valign: "top" });
  };
  yr(0.78, "Y1", "Get the physics right", [
    "Which ground properties control the answer",
    "Go beyond the standard formula",
    "Test against both boreholes",
  ], "a validated property model", FOREST);
  yr(4.79, "Y2", "Go global", [
    "Real terrain shading over the whole Moon",
    "A temperature profile for every point",
    "Check against orbital measurements",
  ], "a Moon-wide temperature map", TEAL);
  yr(8.80, "Y3", "Answer the question", [
    "Where can subsurface ice actually survive",
    "Feed the profiles to sounding missions",
    "Publish the global product",
  ], "an ice-survivability map", CORAL);
  s.addNotes("STAR SLIDE, ~80 s. One sentence per year. The deliverable line is what a "
    + "committee listens for — say each one out loud.");
  foot(s);
}

// =============================================================== 19 FEASIBLE
{
  const s = pres.addSlide(); s.background = { color: CHAR };
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
    "a Moon-wide map is millions of independent columns — and each one now costs a second");
  row(4.10, "The terrain and property studies are finished",
    "presented at AOGS; the controlling parameter is already identified");
  row(5.15, "The home for the work is in place",
    "Institute of Science Tokyo, Kasai Laboratory, with the NICT terahertz mission link");
  s.addNotes("~50 s, then stop for questions. The message: this is not a wish list, "
    + "it is the continuation of something already running.");
}

// =============================================================== BACKUP
dark({ kicker: "Appendix", title: "Backup slides",
  sub: "Kept for questions — not part of the timed presentation",
  notes: "Do not present. Jump here by slide number if a question needs it." });

const backups = [
  ["Where the uncertainty comes from", "robustness.png",
   "The basal heat flux dominates at Apollo 15; the surface albedo dominates at Apollo 17.",
   "Use if asked: why is the error bar so wide?"],
  ["The conductivity–heat-flow trade-off", "qbdeg.png",
   "The two sites respond to a flux revision in opposite directions, which is why the ordering survives.",
   "Use if asked: could this be a heat-flow difference instead?"],
  ["Is a per-site value statistically justified?", "aicc.png",
   "Decisive at Apollo 17. At Apollo 15 the global value is not formally rejected — the case there rests on the confidence interval.",
   "Use if asked: is the difference significant? Answer honestly."],
  ["Independent check against orbital data", "diviner.png",
   "Surface temperatures were never fitted, so this is a genuine out-of-sample test.",
   "Use if asked: how do you know the model is right?"],
  ["What the old method had to do", "anim_race.gif",
   "The old approach crawls toward the answer over thousands of cycles; the anchored solver arrives in four.",
   "Use if asked to explain the speed-up in more detail."],
];
backups.forEach(([t, f, take, note]) => {
  hero({ kicker: "Backup", accent: DIM, title: t, fig: f, take, notes: note });
});

// =============================================================== TERM TABLE
{
  const s = pres.addSlide(); s.background = { color: WHITE };
  kicker(s, "Required appendix", DIM);
  title(s, "Technical terms  ·  専門用語対訳表");
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
  const opt = { y: 1.62, w: 6.0, colW: [3.3, 2.7],
    border: { type: "solid", color: GRID, pt: 0.5 }, rowH: 0.235,
    valign: "middle", margin: [2, 6, 2, 6] };
  s.addTable(mk(pairs.slice(0, mid)), Object.assign({}, opt, { x: 0.72 }));
  s.addTable(mk(pairs.slice(mid)), Object.assign({}, opt, { x: 6.92 }));
  s.addText("Thesis title:  Difference of Lunar Regolith Thermal Conductivity K_d at the Apollo 15 and 17 Heat-Flow Boreholes",
    { x: 0.72, y: 6.62, w: 11.9, h: 0.3, fontFace: BODY, fontSize: 11, color: DIM, margin: 0 });
  s.addText("Japanese readings to be confirmed by Kasai Laboratory before submission.",
    { x: 0.72, y: 6.92, w: 11.9, h: 0.3, fontFace: BODY, fontSize: 10, italic: true,
      color: DIM, margin: 0 });
  foot(s);
}

pres.writeFile({ fileName: path.join(__dirname, "24M58378Gregorio.pptx") })
  .then((f) => console.log("wrote", f));
