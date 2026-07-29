# Slide prompts — GEDES defense deck

One dedicated build brief per slide. Each brief is written so the slide can be
rebuilt from the brief alone, without re-reading the thesis.

**Edit any brief. Whatever this file says, the build follows.**

Two build steps, in order:

```bash
python documents/gedes/defense/make_slide_art.py   # img/*.png + img/*.gif
cd documents/gedes/defense && node build_deck.js   # 24M58378Gregorio.pptx
```

---

# 0 · The design system

Everything below is a hard contract. A slide that breaks it is a build error,
not a taste disagreement.

## 0.1 The spine — where this deck's structure comes from

Guidebook **Figure 2.1** (`documents/jgr/guidebook/figures-tikz/pipeline.tex`) is
the one picture that holds the whole study: three inputs, four processes, three
results, read left to right. It earns two jobs in this deck.

1. **Slide 5 is that figure, redrawn for a projector.** It becomes the roadmap:
   the audience sees the entire thesis once, in plain words, before any step is
   explained. Every later method slide is then "we are here", not a new topic.
2. **A three-segment rail in the footer** carries the same three stages
   (`WHAT WE HAVE` → `WHAT WE DO` → `WHAT WE GET`) on every content slide of
   Part 1, with the current stage lit in the slide's accent colour.

Nobody has to notice the rail for it to work. It removes the "how much is left"
anxiety that makes an audience stop listening.

## 0.2 The stage grid — 13.333 × 7.5 in

| Element | x | y | w | h |
|---|---|---|---|---|
| Kicker (caps, tracked) | 0.72 | 0.32 | 11.90 | 0.28 |
| Title | 0.72 | 0.60 | 11.90 | 0.62 |
| Takeaway line | 0.72 | 1.26 | 11.90 | 0.42 |
| Hairline rule (`GRID`, 0.75 pt) | 0.72 | 1.78 | 11.90 | — |
| **Art box** | **0.72** | **1.88** | **11.90** | **4.94** |
| Stage rail | 0.72 | 7.02 | 2.60 | 0.06 |
| Page number | 12.45 | 6.98 | 0.55 | 0.30 |

Margins are 0.72 in left and right, 0.68 in bottom. Nothing crosses them.

## 0.3 The canvas contract — the fix for the dead space

The current deck floats its pictures because `save()` uses
`bbox_inches="tight"`, so every image comes out at whatever aspect its content
happened to make. Measured across the ten lay figures the aspect runs from
**1.76 to 2.35** against an art box of **2.41**, which is why most slides show a
thick white gutter above and below the picture.

The contract, from now on:

* Hero art is drawn on a **fixed canvas of 12.00 × 4.98 in (2.41 : 1)** at
  **dpi 200** (2400 × 996 px) and saved with **`bbox_inches=None`**.
* Composition happens *inside* the canvas. If a drawing does not reach the
  edges, widen the drawing; do not let the saver crop it.
* Backup slides are exempt: they show real thesis figures whose aspect is fixed
  by the journal, so they use the `evidence` layout, which scales to height and
  centres.

## 0.4 Type

| Role | Face | Size | Colour |
|---|---|---|---|
| Kicker | Calibri bold caps, +2 tracking | 11 | accent |
| Title | Cambria bold | 29 | `CHAR` |
| Takeaway | Calibri | 14.5 | `DIM` |
| In-art headline | Helvetica bold | 20–26 | `CHAR` or accent |
| In-art label | Helvetica | 15–17 | `CHAR` |
| In-art annotation | Helvetica | 13 | `DIM` |
| In-art hero number | Helvetica bold | 34–46 | accent |

**Floor: nothing in any artwork below 12 pt at the 12-inch canvas width.** At
that size a glyph is about 1.1 % of stage height, which is the back-row limit
for a 12-minute talk. Axis tick labels are the usual offender.

## 0.5 Palette and what each colour is allowed to mean

| Token | Hex | Meaning, fixed for the whole deck |
|---|---|---|
| `CHAR` | `#2A2520` | text, structure, neutral geometry |
| `CORAL` | `#B85B3A` | **Apollo 17**, heat, the honest caveat |
| `FOREST` | `#3D6E4A` | **Apollo 15**, work already completed |
| `TEAL` | `#2A6478` | method and machinery |
| `DIM` | `#6E6862` | secondary text, the discarded option |
| `GRID` | `#E8E5E0` | rules, grids, inactive rail segments |
| `TINT` | `#F7F5F2` | card fills |

A site keeps its colour on every slide, including the backups. Grey is never
decorative: grey means *this is the thing we are replacing*.

## 0.6 Motion rules for the GIFs

1. Canvas **1200 × 498 px** (matching the 2.41 art box), 12 fps, loop forever.
2. **48 frames maximum**, one lunation per loop, so a loop is exactly 4 s.
3. **Frame 0 must read as a finished still.** PowerPoint sometimes shows only
   the first frame until the slide is clicked, so frame 0 carries the labels and
   the most legible state.
4. **One variable moves.** Text never moves. Axes never rescale. Only data and
   an explicit counter change.
5. **Every animation shows its clock** as a plain counter, for example
   `day 12 of 29.5`, so nobody has to guess what "one loop" means.
6. The loop seam must be continuous: the last frame flows into frame 0 with no
   visible jump.

## 0.7 The number register — nothing else may appear on a slide

Sourced from `code/results/*.json` and `documents/aogs/results/*.json`. Any
number on a slide that is not in this table has to be added here first, with
its source.

| Quantity | Value | Source |
|---|---|---|
| K_d* Apollo 15 | **4.60** mW m⁻¹ K⁻¹ | `kd_retrieval_results.json` |
| K_d* Apollo 17 | **7.08** | same |
| Global (Hayne 2017) K_d | **3.4** | `headline_rmse.json` |
| Ratio A17 / A15 | **1.54×** ("about 1.5×") | derived |
| Bootstrap 95 % CI, A15 | **[4.18, 6.96]** | `kd_retrieval_results.json` |
| Bootstrap 95 % CI, A17 | **[6.16, 8.07]** | same |
| Contrast median | **2.31**, CI **[−0.12, 3.56]** | same |
| Bootstrap tail proportion | **0.031** (46 of 1500) | same |
| Bootstrap draws | **1500** | same |
| RMSE A15, global → fitted | **1.09 → 1.00 K** | `headline_rmse.json` |
| RMSE A17, global → fitted | **0.89 → 0.40 K** | same |
| Deep sensors used | **7** (A15), **16** (A17); 23 total | `apollo_helpers` |
| Probe depth | **1.4 m** (A15), **2.3 m** (A17) | same |
| Borestem cut | **80 cm** | `config.py` |
| Stability drift limit | **0.08 K per year** | `apollo_helpers` |
| Basal flux Q_b | **21** / **16** mW m⁻² | `config.py`, Langseth 1976 |
| Anchor depth | **0.55 m** | `config.EQ_Z_ANCHOR` |
| Speed-up | **≈2500×**; 27 h → under 1 min | `speedup_benchmark.json` |
| Brute-force spin-up | **~3000** lunations | `equilibrium_certification.json` |
| Anchored solve | **4** outer cycles | same |
| Record span | **1971–1977** | Nagihara 2018 |
| Horizon shading loss | **1.16 %** (A15), **0.18 %** (A17) | `aogs_sensitivity.json` |
| Max horizon elevation | **14.0°** (A15), **10.1°** (A17) | same |
| AOGS model runs | **650** | `aogs_density_study.json` |
| Native layered fit | **0.90** (A15) / **0.36** K (A17) | `aogs_crossite.json` |
| Cross-applied fit | **1.64** / **1.73** K | same |
| Uniform-ground fit | **2.31** / **3.76** K | same |
| Layering gain | **2.6×** (A15), **10×** (A17) | derived from the above |
| cp-only vs coupled-K, A15 | **1.74 → 0.90 K** | `aogs_density_study.json` |
| cp-only vs coupled-K, A17 | **0.39 → 0.36 K** | same |

> **Correction carried into this revision.** The old slide 16 said "heat
> capacity barely moves the answer; density-linked conductivity moves it a lot".
> That is true at Apollo 15 (1.74 → 0.90 K, a 48 % cut) and **not** at Apollo 17
> (0.39 → 0.36 K, an 8 % cut, because that site already fits well). The brief
> for slide 17 states both, because a committee that checks will find it.

## 0.8 Layout templates in `build_deck.js`

| Template | Use |
|---|---|
| `title` | slide 1 only |
| `hero` | kicker · rule · title · takeaway · 2.41:1 art · rail |
| `evidence` | backup slides: real thesis figure, scaled to height, plus a one-line answer and a source note |
| `cards` | three side-by-side stat or concept cards |
| `plan` | the three-year columns |
| `dark` | dividers and the two closing statements |
| `terms` | the required EN/JP table |

---

# 1 · Part 1 — Master's thesis, 13 slides, 12 min

Running total of spoken time: **10.7 min**, leaving about 1.3 min of headroom
for pauses and one animation loop.

---

## Slide 1 · Title
**Template** `dark` · **Time** 20 s · **Accent** `CORAL`

**Leave with:** a plain-language question they can hold for twelve minutes.

Dark charcoal field. Kicker `GEDES MASTER'S THESIS DEFENSE`. Headline
*How well does the Moon hold its heat?* at 36 pt, subtitle *Measuring it at the
only two places we ever dug* at 21 pt in `GRID`. Then name, student number,
institute, laboratory, both supervisors, date.

The formal thesis title does **not** go here. It lives on the term-table slide
and in the abstract. A defense opens with the question, not the filing label.

**Accept when:** no line wraps, and the eye lands on the question first.

---

## Slide 2 · Why this matters
**Template** `hero` · **Time** 50 s · **Accent** `CORAL` · **Art** `anim_hook.gif`

**Leave with:** the surface is violent, one metre down nothing moves, and the
still part is the part that decides whether ice survives.

**Title** The surface is violent. A metre down, nothing moves.
**Takeaway** Ice can only survive where the ground stays cold and steady, and
that is decided below the surface.

**Animation brief.** 1200 × 498, 48 frames, 12 fps, one lunation per loop.

* Left 60 %: temperature (x, 90–400 K) against depth (y, 0–150 cm, inverted).
  A single thick profile line, `CORAL` when the surface is above 250 K and
  `TEAL` when below, redrawn each frame from `250 + 140·exp(−z/δ)·cos(phase)`
  with δ = 5 cm. A soft `FOREST` band and dashed rule at 80 cm labelled
  `THE MEASURED ZONE`, static.
* Right 40 %: two stacked live readouts, each a number at 40 pt with a small
  caps label above.
  `AT THE SURFACE` in `CORAL`, counting between 96 K and 387 K.
  `ONE METRE DOWN` in `FOREST`, frozen at 253 K, with `±0.0 K all month`
  underneath in 13 pt `DIM`. The contrast between a spinning number and a dead
  one is the whole slide.
* Top right: `day 12.0 of 29.5`, monospaced digits so the counter does not
  jitter its own width.
* Frame 0 is lunar noon: profile at maximum excursion, both readouts legible.

**Forbidden:** a legend, a colourbar, more than one moving curve, any axis
rescale mid-loop.

**Accept when:** paused on any frame, the slide still makes its point; and the
deep readout is visibly unchanged across the whole loop.

---

## Slide 3 · The problem
**Template** `hero` · **Time** 55 s · **Accent** `CORAL` · **Art** `lay_gap.png`

**Leave with:** the number everyone uses is one number, fitted from orbit, never
tested underground.

**Title** Every model uses one number for the whole Moon
**Takeaway** It was fitted from orbit, and a satellite only feels the top few
centimetres.

**Art brief.** Canvas 12.00 × 4.98.

* Left third: a Moon disc in `TINT` with faint craters, and across its middle
  `K_d = 3.4` at 46 pt `CORAL` bold. Caption under it in 13 pt italic `DIM`:
  *one value, applied to all 38 million square kilometres.*
* A single `CHAR` arrow to the right, with `but` above it.
* Right two-thirds: three beats, generously spaced, each a coral dot plus a
  17 pt bold headline plus a 13 pt `DIM` sub-line.
  1. **Calibrated from orbit** — satellites only feel the top few centimetres
  2. **Never tested at depth** — subsurface measurements that checked it: **0**
  3. **Only two places can test it** — Apollo 15 and 17, the boreholes in this
     thesis
* The `0` in beat 2 is set at 34 pt `CORAL` inline. It is the rhetorical hinge
  of the slide and must be the second thing the eye finds after `3.4`.

**Accept when:** the two big numerals, 3.4 and 0, read from the back of the
room, and the three sub-lines sit on a shared left edge.

---

## Slide 4 · The data
**Template** `hero` · **Time** 55 s · **Accent** `CORAL` · **Art** `lay_boreholes.png`

**Leave with:** this dataset is tiny, irreplaceable, and fifty years old.

**Title** Only two holes have ever been drilled and instrumented
**Takeaway** Apollo 15 and 17, 1971 to 1977. The records were recovered from the
original mission tapes.

**Art brief.** Canvas 12.00 × 4.98, three zones left to right.

* **Zone A (0–15 %)** a depth ruler in `DIM`: ticks and labels at 0, 50, 100,
  150, 200, 230 cm, with `depth below the surface (cm)` rotated on the far left.
* **Zone B (15–62 %)** the two boreholes to scale, `FOREST` for Apollo 15
  (1.4 m, 7 sensors) and `CORAL` for Apollo 17 (2.3 m, 16 sensors). Stem drawn
  as a `TINT` rectangle with a `DIM` outline; sensors as 11 pt filled circles
  with white edges; duplicate depths fanned left and right so none is hidden.
  The top 80 cm of both stems is filled `#F4D6CB` with a dashed `CORAL` top
  border and labelled once, between the two stems, `top 80 cm excluded —
  disturbed by the drilling`.
* **Zone C (65–100 %)** three stacked facts, each a hero numeral at 34 pt with a
  13 pt caption: **6 years** of continuous record · **23 sensors** deep enough
  to use · **2 sites**, and no more are coming.
* Above Zone C, a small Moon disc, 0.9 in across, with the two sites marked in
  their site colours and hairline leader lines to their names. This is guidebook
  Fig 1.1 reduced to its one readable idea; do not import the real figure.

**Forbidden:** the thesis probe-geometry figure, latitude and longitude, any
mention of TG and TR bridges. Those belong in the backups.

**Accept when:** the 80 cm exclusion is unmistakable, and Zone C balances the
drawing so the canvas has no empty right half.

---

## Slide 5 · ★ The roadmap  *(new — this is the guidebook Fig 2.1 slide)*
**Template** `hero` · **Time** 35 s · **Accent** `TEAL` · **Art** `lay_pipeline.png`

**Leave with:** the whole thesis, once, in one picture, before any detail.

**Title** The whole study on one slide
**Takeaway** Three things going in, three steps in the middle, three numbers
coming out. Everything after this slide is one of those boxes.

**Art brief.** Canvas 12.00 × 4.98. A direct lay-audience translation of
guidebook Fig 2.1, which is the retrieval pipeline. Three columns under three
caps headings, separated by two large chevrons in `GRID`.

* **`WHAT WE HAVE`** (`TEAL` rail, three cards)
  1. **23 thermometers** — Apollo 15 and 17, buried 0.8 to 2.3 m, 1971–77
  2. **A formula for heat flow** — how conductivity varies with depth and
     temperature *(Hayne 2017)*
  3. **Heat from the interior** — 21 and 16 mW m⁻², measured by Apollo
* **`WHAT WE DO`** (`CHAR`, three numbered steps, matching slides 6, 7 and 9)
  1. Pick the steady stretch of each record → one temperature per sensor
  2. Simulate the ground until it repeats the same month forever
  3. Try every candidate conductivity, keep the one that fits best
* **`WHAT WE GET`** (result cards)
  Apollo 15 → **4.60** in `FOREST`; Apollo 17 → **7.08** in `CORAL`; and beneath
  them a `DIM` card, *the global value everyone used: 3.4*.

Between column 1 and column 2, one `CORAL` callout with a leader line to card 2:
**the only unknown is K_d** *(everything else is measured or published)*. That
single annotation is what makes the picture a method and not a flowchart.

**Forbidden:** the Hayne equation, the symbols u_rect, χ, H, T_ref, the words
bootstrap, MCMC and AICc, and any arrow that is not one of the two chevrons.
Guidebook Fig 2.1 shows the equation because a reader can stop and study it. A
room cannot.

**Accept when:** a person who has never heard of this project can read the
three columns aloud in 20 s, and the three result numbers are the highest
contrast marks on the canvas.

---

## Slide 6 · Method, step 1 of 3
**Template** `hero` · **Time** 55 s · **Accent** `TEAL` · **Art** `lay_window.png`

**Leave with:** six years of drifting record become one number per sensor, by an
automatic rule, not by hand.

**Title** Turning six years of wobble into one honest number
**Takeaway** An automatic rule picks the flattest trailing stretch of each
record. No sensor is chosen by hand.

**Art brief.** Canvas 12.00 × 4.98, split 62 / 38.

* **Left:** the real Apollo 15 TG12B record at 139 cm, temperature against days
  since the experiment started. Early section under a `#F4D6CB` wash labelled
  `contaminated — drilling heat, disturbances`; the selected tail under a
  `FOREST` wash labelled `the stability window`; a dashed `CHAR` horizontal at
  the resulting T_eq with the label `one temperature per sensor` at the right
  edge. Tick labels at 14 pt, not the matplotlib default.
* **Right:** a `TINT` card titled `THE RULE` with three lines, each a `TEAL`
  numeral and a plain sentence:
  1. keep the longest flat tail
  2. reject it if the drift is worse than **0.08 K per year**
  3. carry whatever drift is left as an error, do not discard it
  Under the card, in 13 pt `DIM`: *23 of the deep sensors qualify.*

**Accept when:** the two washes are distinguishable at a glance without reading
their labels, and no axis label is under 14 pt.

---

## Slide 7 · Method, step 2 of 3
**Template** `hero` · **Time** 50 s · **Accent** `TEAL` · **Art** `lay_model.png`

**Leave with:** the physics is ordinary. Sun in, heat out, a trickle from below,
and exactly one unknown in the middle.

**Title** A simple picture of the ground
**Takeaway** Sunlight in at the top, heat radiated back to space, a steady
trickle of heat from the interior below.

**Art brief.** Canvas 12.00 × 4.98, split 60 / 40.

* **Left:** a vertical cross-section of the ground, `TINT` fill with a `CHAR`
  outline, drawn tall enough to use the full canvas height. Depth ticks at 0,
  80 cm and 5 m on its left edge.
  * A gold sun at the top left with three rays and a `GOLD` arrow labelled
    `sunlight in`.
  * A `CORAL` arrow leaving the top surface, `heat radiated back to space`.
  * A `TEAL` arrow entering the bottom edge, `heat from the interior  Q_b =
    21 and 16 mW m⁻²`.
  * Across the middle of the column, a `CORAL` box: **K_d = ?** with
    `how easily heat moves through the deep ground` beneath it, and under that,
    in 13 pt, *the one thing we solve for*.
* **Right:** three plain lines with small colour chips matching the three
  arrows, restating in from the Sun, out to space, up from below. Then a
  `DIM` footnote: *standard one-dimensional heat conduction; nothing new here.*

Saying out loud that this part is standard buys credibility for slide 8, where
something is new.

**Accept when:** the three arrows are unambiguous in direction, and the coral
unknown is the visual centre.

---

## Slide 8 · ★ Method, step 3 of 3 — the contribution
**Template** `hero` · **Time** 80 s · **Accent** `FOREST` · **Art** `lay_solver.png`

**Leave with:** the deep column never has to be simulated, and that is what made
everything downstream affordable.

**Title** The calculation used to take a day. Now it takes a minute.
**Takeaway** Once the ground repeats the same monthly cycle, the deep part can
be rebuilt from a single anchor point instead of simulated.

**Art brief.** Canvas 12.00 × 4.98, two equal halves with a `GRID` divider.

This is the methodological contribution and the current artwork does not draw
it. A row of identical grey rectangles is a picture of *repetition*, not a
picture of *the idea*. Both halves must show the same depth column so the
difference is visible as geometry.

* **Left, `THE OLD WAY`, in `DIM`:** a full 5 m column, hatched top to bottom to
  mean "every cell time-stepped, every hour". Beside it a faint stack of
  repeated cycle glyphs fading out to the right with `× ~3000 lunations`.
  Below: **27 hours** at 40 pt `DIM`, and `for one experiment` at 13 pt.
* **Right, `THE FLUX-ANCHORED SOLVER`, in `FOREST`:** the same column, but only
  the top 0.7 m is hatched, labelled `time-stepped — the sun-baked skin only`.
  A `CORAL` dot at **0.55 m** with the label `the anchor`. Below the anchor, a
  smooth `FOREST` curve drawn with a dashed leader and the label `rebuilt from
  one equation, never simulated`. Below: **under 1 minute** at 40 pt `FOREST`,
  and `≈ 2500× faster · 4 cycles instead of 3000` at 13 pt.
* Centred beneath both halves, one `CHAR` line at 15 pt: *the same answer, to
  better than a hundredth of a milliwatt.* The speed claim is worthless to a
  committee without the accuracy claim beside it.

**Spoken analogy** (notes, not on the slide): you do not have to watch a kettle
boil three thousand times to know what temperature it ends at.

**Accept when:** the hatched fraction of the two columns differs obviously, the
anchor dot is the only coral mark on the canvas, and both hero numbers sit on
the same baseline.

---

## Slide 9 · Finding the answer
**Template** `hero` · **Time** 50 s · **Accent** `TEAL` · **Art** `lay_bowl.png`

**Leave with:** we did not solve for the answer, we tried every value and kept
the best, and we could only afford that because of slide 8.

**Title** Try every value, keep the one that fits best
**Takeaway** Each attempt now costs a second, so we can afford hundreds of them,
and then repeat the whole thing 1500 times.

**Art brief.** Canvas 12.00 × 4.98. Two RMSE curves against candidate K_d, from
2 to 12 mW m⁻¹ K⁻¹. Apollo 15 in `FOREST`, Apollo 17 in `CORAL`, 3.5 pt lines.
Minima marked with a large filled dot and the value in a white pill: **4.60**
and **7.08**. A vertical dashed `DIM` line at **3.4** labelled
`the global value everyone used`, which quietly foreshadows the result.
One annotation with a leader: `lowest point = best answer`.

The y-axis carries **no numbers**, only the label
`how badly the model misses the real thermometers`, with a small `better ↓`
arrow. The audience needs the shape, not the scale.

**Accept when:** both minima are visibly to the right of the 3.4 line, and no
tick label is smaller than 14 pt.

---

## Slide 10 · ★ Result
**Template** `hero` · **Time** 75 s · **Accent** `CORAL` · **Art** `lay_results.png`

**Leave with:** two numbers, both above the textbook value, and Apollo 17 about
one and a half times Apollo 15.

**Title** Both sites hold heat differently than the textbook value
**Takeaway** Apollo 17 lets heat through about 1.5× more easily than Apollo 15,
and both exceed the single global value.

**Art brief.** Canvas 12.00 × 4.98.

* Two horizontal bars only: Apollo 15 in `FOREST` at 4.60, Apollo 17 in `CORAL`
  at 7.08, each 0.9 in tall, with the value set inside the bar in white at
  30 pt. 95 % bootstrap whiskers in `CHAR` at the bar end, with the interval
  printed in 13 pt `DIM` beyond the whisker.
* The global 3.4 becomes a **dashed vertical reference line** running the full
  height, labelled `the global value everyone uses: 3.4`. It is not a bar,
  because it is not a measurement of these sites and drawing it as a third bar
  invites the wrong comparison.
* A slim `CHAR` bracket spanning the two bar ends, annotated **1.5×**.
* Bottom strip, three small `TINT` cards: `fit at Apollo 15: 1.09 → 1.00 K`,
  `fit at Apollo 17: 0.89 → 0.40 K`, `both above the global value`. The middle
  card is the strongest evidence in the thesis and currently appears nowhere on
  a presented slide.
* Axis label: `deep conductivity  (mW m⁻¹ K⁻¹)  —  higher = lets heat through
  more easily`.

**Accept when:** the two numerals are the largest marks on the slide, and the
dashed reference line is clearly a different class of object from the bars.

---

## Slide 11 · How sure am I
**Template** `hero` · **Time** 55 s · **Accent** `TEAL` · **Art** `lay_bootstrap.png` *(new)*

**Leave with:** the ordering is robust because we deliberately tried to break it
1500 times and it held.

**Title** Re-running the whole analysis 1500 times
**Takeaway** Randomly leaving sensors out and jittering their depths gives the
full spread of answers the data can support.

**Art brief.** Canvas 12.00 × 4.98, split 34 / 66. The current slide borrows the
thesis figure `bootstrap.png`, whose two stacked panels and 9 pt axis text are
unreadable at projection size. That figure moves to the backups; this replaces
it.

* **Left, `ONE DRAW`:** four small stacked rows of sensor dots. In each row some
  dots are `DIM` and hollow (left out this time) and the rest are filled in the
  site colour, with a small horizontal jitter to stand for the ±2.5 cm depth
  uncertainty. A downward brace to `repeat 1500 times`, in `TEAL`.
* **Right, `THE SPREAD OF ANSWERS`:** the two bootstrap histograms drawn from
  the real `kd_retrieval_results.json` draws, `FOREST` and `CORAL`, direct-
  labelled at their peaks, no legend. Under each, a thick 95 % interval bar with
  the numbers printed: **[4.18, 6.96]** and **[6.16, 8.07]**.
* One `CHAR` annotation across the gap between the two humps:
  `the two distributions barely overlap — this is why the ORDERING is solid`.

**Forbidden:** the word *p-value*. What we have is a bootstrap tail proportion,
0.031, and if it is said at all it is said in words on slide 12. This is the
same correction already applied to the guidebook.

**Accept when:** the two histograms are direct-labelled with no legend, and the
95 % bars are readable as intervals rather than as error bars.

---

## Slide 12 · ★ The honest limit
**Template** `hero` · **Time** 65 s · **Accent** `CORAL` · **Art** `lay_seesaw.png`

**Leave with:** the thermometers measure a ratio, so the direction of the result
is solid and the exact size is not.

**Title** What I can claim, and what I cannot
**Takeaway** A thermometer buried in the ground measures the steepness of the
temperature rise, and steepness is heat-from-below divided by conductivity.

**Art brief.** Canvas 12.00 × 4.98. Currently this slide is an equation plus two
boxes. The equation is correct and lands with physicists; it does not land with
the rest of the panel. Draw the degeneracy instead.

* **Left 45 %:** a balance beam on a `CHAR` fulcrum. On the left pan, a `TEAL`
  block labelled `heat from below  Q_b`; on the right pan, a `FOREST` block
  labelled `conductivity  K_d`. A thermometer icon sits above the beam with a
  leader to the *tilt*, labelled `the thermometers only see the tilt`. Under
  the drawing, small and grey, the actual relation:
  `steepness = Q_b / K_d`. Two different pairs of blocks can produce the same
  tilt, and the drawing should show a ghosted second pair doing exactly that.
* **Right 55 %:** two cards, equal size, side by side.
  * `FOREST` card, **What is solid** — Apollo 17 is the more conductive site;
    this holds in more than 99 % of the tested cases, including when the
    assumed heat flow is allowed to vary by four times its published spread.
  * `CORAL` card, **What is not settled** — the exact size of the gap, and
    whether the difference is conductivity or heat from below. The 95 % interval
    on the difference, **[−0.12, 3.56]**, still touches zero.

**Delivery note:** do not rush and do not apologise. Stating the limit plainly
is what makes slides 10 and 11 believable.

**Accept when:** a non-physicist can point at the picture and explain why two
different grounds could give the same reading.

---

## Slide 13 · Conclusions
**Template** `cards` (three numbered rows) · **Time** 60 s · **Accent** `FOREST`

**Leave with:** three sentences, then silence.

**Title** Conclusions

1. **The two boreholes are genuinely different** — 4.60 and 7.08; Apollo 17
   conducts heat about 1.5× more easily, and both beat the global 3.4
2. **A calculation that took a day now takes a minute** — the flux-anchored
   solver, about 2500× faster, which is what made the uncertainty analysis
   possible at all
3. **This is the ground truth future Moon missions need** — instruments that see
   beneath the surface need a temperature profile no satellite can measure

Footer bar in `TINT`: *The honest caveat: the size of the difference is not yet
nailed down, only its direction.*

No thank-you slide. The last thing on the screen should be the result.

**Accept when:** the three rows are vertically even and the caveat bar does not
collide with the rail.

---

# 2 · Part 2 — Doctoral plan, 7 slides, 6 min

The rhetorical move: **three slides of finished work before a single promise.**
By the time the plan appears, the committee has already watched the applicant
execute.

---

## Slide 14 · Divider
**Template** `dark` · **Time** 10 s

Kicker `PART 2`, title *Doctoral Research Plan*, subtitle *From two holes in the
ground to a map of the whole Moon*. Change of gear: say "that is what I have
done, here is where it goes."

---

## Slide 15 · The goal
**Template** `hero` · **Time** 35 s · **Accent** `CORAL` · **Art** `lay_global.png`

**Title** Two points are not a map
**Takeaway** Where ice can survive is a question about the whole Moon, not about
two Apollo sites.

**Art brief.** Canvas 12.00 × 4.98, three panels left to right.

1. `TODAY` — a plain Moon disc with exactly two dots in the site colours,
   captioned `2 measured points`.
2. A horizontal `3-YEAR PLAN` arrow with three ticks labelled Y1, Y2, Y3,
   matching slide 19 so the two slides visibly rhyme.
3. `GOAL` — the same disc, filled with a smooth subsurface-temperature field,
   captioned `a Moon-wide subsurface map, and where ice can survive`.

Use `ANTH_DIVERGE` from the project style module for the field so it matches
the thesis. No colourbar; the point is coverage, not values.

**Accept when:** the two discs are the same size, so the eye reads the change as
information rather than as scale.

---

## Slide 16 · Already built, step 1
**Template** `hero` · **Time** 55 s · **Accent** `FOREST` · **Art** `shadowing.gif`

**Title** Step 1: put the real landscape into the model
**Takeaway** Mountains shade the ground and radiate back onto it. Apollo 15
loses 1.16 % of its sunlight to the Apennine front; Apollo 17 loses 0.18 %.

> **Not yet done.** This GIF is a copy of an AOGS artifact
> (`documents/aogs/results/shadowing_algorithm.gif`, 748 × 360, aspect 2.08), and
> it is produced by `documents/aogs/code/08_aogs_study.ipynb`, which needs the
> LOLA DEM pipeline. It therefore does **not** meet the canvas contract and
> letterboxes slightly inside the art box, and its in-figure type is below the
> 12 pt floor. Re-rendering it is a separate job that has to run in that
> notebook. Everything below is the brief for when it does.

**Animation brief.** Re-render at 1200 × 498, 48 frames, 12 fps, one lunar day
per loop.

* Left: the polar horizon plot for Apollo 15, real DEM horizon ring in `CHAR`,
  the Sun's track as a moving `GOLD` dot, and the ring shaded where the Sun is
  blocked. Annotate the tallest sector once: `the Apennine front — up to 14°`.
* Right: the resulting irradiance against time in Earth days, with the shadowed
  curve in `FOREST` filled against the unshadowed curve in `DIM`, and the gap
  hatched. Label the gap `1.16 % of the month's sunlight, removed`.
* Counter top right: `day 0.0 → 29.5`.
* Frame 0 at local noon, both panels legible.

Stress the words **already built** out loud. This was presented at AOGS.

**Accept when:** the shaded sector on the left and the notch on the right
visibly correspond, frame by frame.

---

## Slide 17 · ★ Already built, step 2
**Template** `hero` · **Time** 65 s · **Accent** `FOREST` · **Art** `lay_cpvc.png` *(new)*

**Leave with:** the controlling parameter was identified before the PhD was
proposed.

**Title** Step 2: find out which property actually matters
**Takeaway** 650 model runs. Density matters mainly through conductivity, not
through heat storage, and a layered ground beats a uniform one by 2.6× at
Apollo 15 and 10× at Apollo 17.

**Art brief.** Canvas 12.00 × 4.98. Replaces the AOGS technical two-panel
figure, which is unreadable at projection size and moves to the backups.

* **Left 45 %, `DENSITY DOES TWO JOBS`:** a small branch diagram. `a layer's
  density ρ` splits into two paths: `heat storage (ρ·c_p)` and
  `conductivity K(ρ)`. Each path ends in a horizontal bar showing the best RMSE
  achievable when only that path is active, drawn to the same scale, paired per
  site:
  * Apollo 15 — storage only **1.74 K**, storage + conductivity **0.90 K**
  * Apollo 17 — storage only **0.39 K**, storage + conductivity **0.36 K**
  Annotate honestly: `at Apollo 15 the coupling halves the error; at Apollo 17
  the site already fits, so it changes little.` The overstated version of this
  claim is corrected in §0.7 and must not come back.
* **Right 55 %, `LAYERED BEATS UNIFORM`:** three grouped bars per site, uniform
  ground / cross-applied / native layered, using 2.31 · 1.64 · 0.90 for
  Apollo 15 and 3.76 · 1.73 · 0.36 for Apollo 17, with the gain factors
  **2.6×** and **10×** called out. Lower is better; say so on the axis.

**Accept when:** every bar in the figure is drawn on one shared scale, so the
comparison cannot be misread.

---

## Slide 18 · Already built, step 3
**Template** `cards` · **Time** 40 s · **Accent** `FOREST`

**Title** Step 3: check that the physics travels
**Takeaway** Each site's best setup was applied, untouched, at the other site.
It still beat a uniform-property model, so this is transferable physics, not
curve-fitting.

Three cards, mismatch against the real Apollo thermometers, lower is better:

| Card | Value (K) | Sub |
|---|---|---|
| `ITS OWN SITE` (`FOREST`) | 0.36 – 0.90 | the layered model at the site it was tuned on |
| `THE OTHER SITE` (`TEAL`) | 1.64 – 1.73 | the same setup moved across, untouched |
| `UNIFORM GROUND` (`DIM`) | 2.31 – 3.76 | the old assumption, worse than both |

This is the single strongest argument that a global model is justified, so give
the middle card the accent weight, not the left one.

---

## Slide 19 · ★ The plan
**Template** `plan` · **Time** 80 s · **Accent** `CORAL`

**Title** Three years, three deliverables

| Year | Heading | Work | Deliverable |
|---|---|---|---|
| Y1 `FOREST` | Get the physics right | which ground properties control the answer · go beyond the standard formula · test against both boreholes | a validated property model |
| Y2 `TEAL` | Go global | real terrain shading over the whole Moon · a temperature profile for every point · check against orbital measurements | a Moon-wide temperature map |
| Y3 `CORAL` | Answer the question | where subsurface ice can actually survive · feed the profiles to sounding missions · publish the global product | an ice-survivability map |

The Y1/Y2/Y3 markers must be the same three ticks used on slide 15, in the same
colours. One sentence per year when speaking; say each deliverable out loud,
because that is the line a committee listens for.

---

## Slide 20 · Why this is achievable
**Template** `dark` · **Time** 50 s

**Title** The hard part is already done

* **The fast solver exists and is verified** — a Moon-wide map is millions of
  independent columns, and each one now costs a second
* **The terrain and property studies are finished** — presented at AOGS; the
  controlling parameter is already identified
* **The home for the work is in place** — Institute of Science Tokyo, Kasai
  Laboratory, with the NICT terahertz mission link

Then stop for questions. Not a wish list: the continuation of something running.

---

# 3 · Backup — not presented

Backup slides use the `evidence` template, which scales the real thesis figure
to the full remaining height and centres it, with a one-line answer above and a
grey source note below. **These deliberately keep the journal figures.** A
questioner who asks for the error budget wants the actual evidence, not the
teaching cartoon, and the slide is on screen for one question, not for a talk.

| # | Question it answers | Figure | The one line to say |
|---|---|---|---|
| 21 | *(divider)* | — | — |
| 22 | Why is the error bar so wide? | `robustness.png` | The basal heat flux dominates at Apollo 15; the surface albedo dominates at Apollo 17. |
| 23 | Could this be a heat-flow difference instead? | `qbdeg.png` | The two sites respond to a flux revision in opposite directions, which is why the ordering survives. |
| 24 | Is the difference statistically significant? | `aicc.png` | Decisive at Apollo 17. At Apollo 15 the global value is not formally rejected, and the case there rests on the confidence interval. Answer this one honestly. |
| 25 | How do you know the model is right? | `diviner.png` | Surface temperatures were never fitted, so this is a genuine out-of-sample test. |
| 26 | Explain the speed-up in more detail | `anim_race.gif` | The old approach crawls toward the answer over thousands of cycles; the anchored solver arrives in four. |
| 27 | What does the raw bootstrap look like? | `bootstrap.png` | The journal version of slide 11, with both panels and the tail proportion. |
| 28 | The AOGS parameter study in full | `aogs_cpvc.png` | The journal version of slide 17. |

Slides 27 and 28 are new, and exist because slides 11 and 17 now use purpose-
drawn artwork. Anyone who asks to see the real analysis gets it in one keystroke.

---

## Final slide · Technical terms  ·  専門用語対訳表
**Template** `terms`

Required by GEDES and **must be the last slide**. Two columns of English and
Japanese pairs, `booktabs`-like hairlines in `GRID`, English in `CHAR`,
Japanese in `TEAL`, 11.5 pt. The formal thesis title goes at the foot, and
below it the note that the Japanese readings are to be confirmed by Kasai
Laboratory before submission.

---

# 4 · Acceptance checklist

Run this before saying the deck is done. Every item was a real defect in a
previous revision.

- [ ] every hero art file is exactly 2400 × 996 px, so no slide floats its
      picture in a white gutter
- [ ] no text anywhere in any artwork is below 12 pt at the 12-inch canvas
- [ ] every number on every slide appears in the register at §0.7
- [ ] the site colours are never swapped: Apollo 15 is `FOREST`, Apollo 17 is
      `CORAL`, on presented slides and backups alike
- [ ] no legend or annotation sits on top of a plotted line, marker or fill
- [ ] each GIF's frame 0 is legible as a still, and the loop seam does not jump
- [ ] the stage rail lights the correct segment on every Part 1 content slide
- [ ] the term table is the last slide in the file
- [ ] the deck is rendered and **looked at**, page by page, at ≥150 dpi. Code
      that looks right is not a slide that looks right.

---

## Edit notes
<!-- Write your changes below. Anything here gets implemented. -->

-
-
-
