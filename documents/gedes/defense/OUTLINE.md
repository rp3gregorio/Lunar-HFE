# Defense deck — outline, per slide

**Edit this file freely. Whatever it says, the build follows.**
Built and rendered: 50 slides, `24M58378Gregorio.pptx`.

`SLIDE_PROMPTS.md` is the per-slide build brief · `build_deck.js` +
`make_slide_art.py` are the implementation · `SPEAKER_SCRIPT.md` is the narration.

---

## The story in one sentence
*Everyone assumes the Moon insulates itself the same way everywhere; I checked
that assumption at the only two places it can be checked, found it wrong at
both, and built the tool that made checking affordable.*

## What changed in this revision

| Your note | What it does to the outline |
|---|---|
| colour bar on the hook GIF | slide 2 art respec'd |
| show the regolith layering / boundary layers | slide 2 art respec'd |
| slide 4's right figure = the manuscript Moon figure | now thesis Fig 1.2 panel (a), the real Clementine globe |
| use guidebook Fig 2.1 itself | slide 5 is now the actual TikZ figure, not my redraw |
| **highlight the method, the Apollo data, the anchor method** | Apollo data gets 2 slides (4, 6); the anchor method gets **2** slides (8, 9) instead of 1 |
| the main thesis results are missing | **new slide 12**: the model against the real thermometers (thesis Fig 5.5) |
| report which figures come from the guidebook | `Source` column below |
| notes on what goes on each slide | the `Content` block under each row |
| remove unnecessary GIFs | `anim_wave.gif` + 20 orphan images to be deleted |

**Time check: Part 1 is 12.3 min at 130 wpm against a 12-min slot.** That is over
by ~20 s, deliberately, because you asked to expand the method. Cut list, in
order, if you run long on the day: slide 10 (−40 s), then slide 3 (−15 s).
Cross out any slide below and I will rebalance.

---

## PART 1 — MASTER'S THESIS · 12 min · 15 slides

### 1 · Title — 20 s · dark
**How well does the Moon hold its heat?**
*Measuring it at the only two places we ever dug*
**Content:** name, student number, institute, lab, both supervisors, date. The
formal thesis title stays off this slide; it is on the term table. Open with the
question, not the filing label.

---

### 2 · Hook — 45 s · 🎞 `anim_hook.gif` *(respec'd)*
**The surface is violent. A metre down, nothing moves.**
**Content:** one lunation, looped. Cross-section of regolith coloured by
temperature, Sun tracking overhead, two live readouts — surface swinging
100→390 K, one metre down frozen. **New:** a temperature **colour bar** on the
side, and the **regolith layering** drawn in: loose surface fines, the
compaction depth (6 cm), where the daily wave dies out (~20 cm), the 80 cm
drilling-disturbed boundary, and the measured zone below it.
**Say:** that still, deep number is what decides whether ice survives, and no
instrument can measure it from orbit.

---

### 3 · The gap — 50 s · `lay_gap`
**Every model uses one number for the whole Moon**
**Content:** the Moon carrying K_d = 3.4, then three beats — calibrated from
orbit (satellites feel only the top few cm) · tested below the surface: **0**
times · places where it can be tested: **2**.
**Say:** the number is not wrong because someone was careless; it is unchecked
because there was no way to check it.

---

### 4 · The Apollo data (1 of 2) — 55 s · `lay_boreholes` *(respec'd)*
**Only two holes have ever been drilled and instrumented**
**Content:** both boreholes to scale — Apollo 15 at 1.4 m with 7 usable sensors,
Apollo 17 at 2.3 m with 16 — the top 80 cm shaded out as drilling-disturbed, and
the three scarcity facts (6 years, 23 sensors, 2 sites).
**New:** the right-hand figure is now **the real Moon from the manuscript**
(thesis Fig 1.2a, the Clementine albedo globe with both sites marked), not a
drawn disc.
**Say:** 1971–1977, recovered from the original mission tapes. Nothing like it is
coming again.

---

### 5 · The roadmap — 40 s · **guidebook Fig 2.1, as published**
**The whole study on one slide**
**Content:** the actual retrieval pipeline figure — three inputs (Apollo HFE
record; the Hayne K(T,z) form with one free knob; the published basal flux Q_b),
four processes (stable window → forward solve → sweep → uncertainty), three
results (4.60 / 7.08 / the contrast).
**Say:** walk the three columns with your hand, point out that **only one thing
in the input column is unknown**, then say every remaining slide in Part 1 is one
of these boxes. Do not read the equations aloud.
**Note:** this is the real figure, so it carries its equations and its code
paths. Two source fixes needed before use: the stale `src/lunar/…` path, and the
`p ≈ 0.031` label, which the guidebook itself now says must be called a bootstrap
tail proportion. Both are one-line edits to `figures-tikz/pipeline.tex`.

---

### 6 · The Apollo data (2 of 2) — 55 s · `lay_window`
**Turning six years of wobble into one honest number**
**Content:** a real Apollo 15 record. The early years shaded coral
(drilling heat, mission disturbances, instrument drift); the selected flat tail
shaded green; the resulting single equilibrium temperature. Beside it the rule in
three lines: keep the longest flat tail · reject it if the drift is worse than
0.08 K/yr · carry the leftover drift as an error.
**Say:** this is an automatic rule, not hand-picking. 23 of the deep sensors
qualify, and anyone can reproduce the selection.

---

### 7 · The physics — 40 s · `lay_model` *(respec'd)*
**A simple picture of the ground, and the equations behind it**
**Content:** one column of soil. Sunlight in, heat radiated back to space, a
steady trickle Q_b from the interior (21 and 16 mW m⁻²), and one coral unknown in
the middle: K_d.
**New:** carries **the governing equations**, each placed next to what it
governs: heat conduction in the column, the Hayne K(T,z), the surface energy
balance, and the basal geothermal flux.
**Say:** state plainly that this part is standard. Saying so buys credibility for
the next three slides, where something is new. Everything in those four
equations is measured or published except K_d.

---

### 8 · ★ How the Apollo data is used — 50 s · **guidebook `dataenters_slide`**
**The model runs blind — the data enters only at the fit**
**Content:** the guidebook flowchart. A trial K_d enters a forward solve that
never sees a thermometer; the predicted deep profile meets the 23 Apollo
temperatures at exactly one step, the misfit RMSE(K_d); the smallest misfit
picks K_d*. Three notes beside it: the model is not tuned to the data · the data
scores, it does not steer · so the fit is a test, not a fit.
**Say:** this answers "did you just fit your own data?". It is also the setup for
slide 12, where the modelled profile lands on measurements the model never saw.
**Note:** this replaced the standalone RMSE-bowl slide, which moved to backup 32.

---

### 9 · ★ The anchor method (1 of 2) — the wall — 45 s · **guidebook `costnesting`**
**Why this calculation was impossible**
**Content:** the three nested loops, as published: one Crank–Nicolson step
(×~136,000), inside the anchor loop (×6–10), inside the K_d sweep (×30).
~3000 lunations to settle, ~27 hours per experiment.
**Say:** this is the wall. Not "slow" — *not possible*. The uncertainty analysis
on slide 13 is unaffordable at this cost.

---

### 10 · ★ The anchor method (2 of 2) — the way through — 70 s · `lay_solver`
**The calculation used to take a day. Now it takes a minute.**
**Content:** the same 5 m column twice. Left, every cell hatched and time-stepped
for ~3000 lunations → 27 hours. Right, only the top 0.7 m hatched, the anchor at
0.55 m, everything below rebuilt from the closure equation → under a minute,
≈2500× faster. The closure itself is printed along the bottom.
**Say:** once the ground repeats the same monthly cycle, the average heat flowing
through it is the same at every depth. Kettle analogy if eyes glaze. **Always
pair the speed claim with the accuracy claim** — same answer to better than
0.01 mW.

---

### 11 · ★ Result (1 of 2) — the numbers — 65 s · `lay_results`
**Both sites hold heat differently than the textbook value**
**Content:** two bars with 95% bootstrap whiskers, the global 3.4 as a dashed
reference line (not a bar — it is not a measurement of these sites), the 1.5×
bracket, and the fit-improvement cards: 1.09→1.00 K at Apollo 15, 0.89→0.40 K at
Apollo 17.
**Say:** the numbers out loud, then the evidence nobody asks for but everyone
should — the fit got *better*, and at Apollo 17 the mismatch more than halved.

---

### 12 · ★ Result (2 of 2) — the evidence — 50 s · **thesis Fig 5.5** *(new slide)*
**The model against the actual thermometers**
**Content:** the meter-scale panels of the thesis thermal-profile figure — the
modelled temperature column at the retrieved K_d* drawn through the real HFE
sensors at both sites, with the Martínez & Siegler forward curve as the
comparison.
**Say:** this is the whole claim in one picture. The retrieved value is not a
number from an optimiser; it is the profile that actually passes through the
measurements. **This slide is why you asked for it — the deck previously showed
the answer but never showed it fitting the data.**

---

### 13 · How sure am I — 45 s · `lay_bootstrap`
**Re-running the whole analysis 1500 times**
**Content:** left, what one draw is (sensors dropped at random, depths jittered
±2.5 cm); right, the resulting two spreads with their 95% ranges printed.
**Say:** the spreads barely overlap, which is why the *ordering* is solid. Do not
say p-value — it is a bootstrap tail proportion, 0.031.

---

### 14 · ★ The honest limit — 60 s · `lay_seesaw`
**What I can claim, and what I cannot**
**Content:** the degeneracy drawn as a balance — Q_b on one pan, K_d on the
other, the thermometers seeing only the tilt, and a ghosted second pair showing
that doubling both gives an identical tilt. Then two cards: what is solid
(Apollo 17 is the more conductive site, >99% of tested cases) and what is not
settled (the size of the gap; the 95% range on the difference still touches zero).
**Say:** calmly, without apologising. This is the slide that makes 11 and 12
believable.

---

### 15 · Conclusions — 55 s · numbered rows
**Content:** (1) the two boreholes genuinely differ, 4.60 and 7.08, both above
3.4 · (2) a day-long calculation now takes a minute, ≈2500×, which is what made
the uncertainty analysis possible · (3) this is the ground truth future
subsurface missions need. Footer bar: the size of the difference is not nailed
down, only its direction.
**Say:** land the three, then stop. No thank-you slide.

---

## PART 2 — DOCTORAL PLAN · 6 min · 7 slides

Rhetorical move: **three slides of finished work before a single promise.**

### 16 · Divider — 10 s · dark
**Doctoral Research Plan** · *From two holes in the ground to a map of the whole Moon*

### 17 · The goal — 35 s · `lay_global`
**Two points are not a map** — two dots today, a Moon-wide subsurface map at the
end, with Y1/Y2/Y3 ticks that rhyme with slide 21.

### 18 · Already built (1) — 55 s · 🎞 `shadowing.gif`
**Step 1: put the real landscape into the model** — DEM horizons up to 14.0° at
Apollo 15 removing 1.16% of the sunlight; 10.1° and 0.18% at Apollo 17.
Presented at AOGS. Stress **already built**.

### 19 · ★ Already built (2) — 65 s · `lay_cpvc`
**Step 2: find out which property actually matters** — 650 runs. Density does two
jobs; the answer cares about conductivity. Honest version: the coupling halves
the error at Apollo 15 (1.74→0.90 K) and barely moves Apollo 17 (0.39→0.36 K).
Layered beats uniform 2.6× and 10×.

### 20 · Already built (3) — 40 s · three stat cards
**Step 3: check that the physics travels** — own site 0.36–0.90 K, other site
untouched 1.64–1.73 K, uniform ground 2.31–3.76 K. The strongest argument that a
global model is justified.

### 21 · ★ The plan — 80 s · Y1/Y2/Y3 columns
**Three years, three deliverables** — validated property model · Moon-wide
temperature map · ice-survivability map. Say each deliverable out loud.

### 22 · Close — 50 s · dark
**The hard part is already done** — the solver exists and is verified; the
terrain and property studies are finished; the lab and the NICT mission link are
in place.

---

## BACKUP · slides 23–49 · not presented

**23** divider · **24 backup index** (every entry below, by slide number, so you
can jump during Q&A).

### Evidence · thesis figures · 25–34
| # | The question | Figure |
|---|---|---|
| 25 | Why is the error bar so wide? | thesis Fig 5.12 |
| 26 | Could this be a heat-flow difference? | thesis Fig 5.11 |
| 27 | Is the difference significant? | thesis Fig 5.6 (AICc) |
| 28 | How do you know the model is right? | thesis Fig 5.10 (Diviner) |
| 29 | Are you over-fitting seven sensors? | thesis Fig 5.7 (holdout) |
| 30 | What if the published heat flow is wrong? | thesis Fig 5.13 (MCMC) |
| 31 | Show me the real distribution | thesis Fig 5.4 (bootstrap) |
| 32 | How exactly did you pick the value? | the RMSE bowl |
| 33 | Explain the speed-up in more detail | solver race animation |
| 34 | The real analysis behind the plan | AOGS density study |

### Method in depth · guidebook flowcharts · 35–49
| # | What it shows |
|---|---|
| 35 | How one sensor becomes one temperature (the window rule) |
| 36 | From the heat equation to the closure, in five moves |
| 37 | Brute force versus the anchor method, side by side |
| 38 | Why the deep column is almost free |
| 39 | Step A and Step B, in full |
| 40 | The outer loop and its convergence test |
| 41 | How a converged solve is certified |
| 42 | One Crank–Nicolson time step |
| 43 | The depth grid |
| 44 | One bootstrap draw, in full |
| 45 | The Bayesian cross-check, step by step |
| 46 | Three disjoint slices of physics |
| 47 | The three bugs, and what each cost |
| 48 | How a number earns its way into the model |
| 49 | Reproducing the whole chain |

**50 · EN/JP term table** — GEDES requires this LAST.

---

## Where every figure comes from

| Slide | Figure | Origin |
|---|---|---|
| 5 | the retrieval pipeline | **guidebook Fig 2.1**, as published |
| 8 | the model runs blind | **guidebook** `dataenters_slide` |
| 9 | the three nested loops | **guidebook** `costnesting` |
| 35–49 | method flowcharts | **guidebook**, 15 of its 34 TikZ figures |
| 4 (inset) | Clementine globe | **thesis Fig 1.2a** |
| 12 | thermal profiles | **thesis Fig 5.5**, meter-scale panels |
| 25–31 | backup evidence | **thesis Ch 5**, unmodified |
| 2, 3, 4, 6, 7, 10, 11, 13, 14, 17, 19, 21 | lay artwork | purpose-built |
| 18, 34 | shadowing, AOGS study | **AOGS** bundle |

Two fixes were applied to guidebook `pipeline.tex` before use: the stale
`src/lunar/…` path, and the `p ≈ 0.031` label, now `bootstrap tail 0.031` to
match the guidebook's own corrected wording.

**Deleted** (unused): `anim_wave.gif` plus 21 orphaned PNGs.

---

## Open questions for you

1. **Part 1 is 12.3 min against a 12-min slot.** Accept and rely on the cut list,
   or should I drop a slide now?
2. **Slide 5 is the real Fig 2.1**, which means equations and code paths on
   screen for a non-specialist panel. Confirmed?
3. **Slide 8** is a new slide using the guidebook cost-nesting figure. Keep, or
   fold back into slide 9?

## Edit notes
<!-- Write your changes below. Anything here I implement. -->

-
-
-
