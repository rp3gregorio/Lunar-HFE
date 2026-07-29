# Speaker script — GEDES defense

**Ramon III P. Gregorio · 24M58378 · Institute of Science Tokyo, Kasai Laboratory**

Written against the deck built by `build_gedes_deck.py`. Slide numbers below are
the real slide numbers in `24M58378Gregorio.pptx` — if you rebuild the deck, the
numbers here still hold unless you add or remove a slide.

Timed at **130 words per minute**, the same budget the build script enforces.
Each block is written to its slide's second allocation, so at a normal speaking
pace the two parts land inside their windows without you managing the clock.

| Part | Slides | Spoken | Allocated | Q&A |
|---|---|---|---|---|
| 1 — Master's thesis | 1–15 | **11.4 min** | 12 min | 5 min |
| 2 — Doctoral plan | 16–23 | **5.5 min** | 6 min | 7 min |
| Backup (not presented) | 24–40 | — | — | jump by number |

### Four rules for the day

1. **Say the numbers out loud.** They are the evidence. One number spoken beats
   three adjectives.
2. **Do not apologise for slide 14.** Stating the limit plainly is what makes
   everything before it believable. Deliver it at the same volume as the result.
3. **If you are running long, cut slide 9,** not slide 14. Slide 9 only sets up
   slide 10, and the setup can be one sentence.
4. **Stop when slide 15 lands.** No thank-you slide, no "that's all from me".
   Say the last line and wait.

---

# PART 1 — MASTER'S THESIS · 12 minutes

## Slide 1 · Title — 20 s

> Good morning. I am Ramon Gregorio, from Kasai Laboratory. My thesis asks one
> question: how well does the Moon hold on to its heat? I answer it at the only
> two places where anyone has ever dug deep enough to find out.

*Pause. Advance.*

## Slide 2 · The surface is violent, a metre down nothing moves — 40 s

*Let the animation loop once before you speak. Do not talk over the first loop.*

> Watch one month on the Moon. At the surface, the temperature runs from about a
> hundred kelvin at night to three hundred and ninety at noon. Colder than
> liquid nitrogen, then hotter than boiling water. Every month.
>
> Now watch one metre down. It does not move. Not by a tenth of a degree.
>
> Ice survives where the ground is cold and steady, and that is decided down
> here, not up there.

## Slide 3 · Every model uses one number for the whole Moon — 45 s

> So what sets how fast heat leaks through that metre? One property:
> conductivity. And here is the problem. Every thermal model of the Moon uses a
> single value for it — three point four — across thirty-eight million square
> kilometres.
>
> That number was fitted from orbit. A satellite feels the top few centimetres
> and nothing below it. So the number that governs the deep ground was never
> measured in the deep ground.
>
> The count of subsurface measurements that have ever tested it is zero.

## Slide 4 · Only two holes have ever been drilled — 55 s

> There are exactly two places where it can be checked. Apollo 15 and Apollo 17
> drilled into the regolith and left thermometers in the hole. They recorded for
> six years, from 1971 to 1977.
>
> That record was nearly lost. It has been recovered from the original mission
> tapes.
>
> I use the sensors below eighty centimetres. Above that line the drilling
> disturbed the ground, so those readings tell you about the hole rather than
> about the Moon. That leaves seven sensors at Apollo 15 and sixteen at Apollo
> 17.
>
> Twenty-three thermometers. Nothing like them is coming again soon.

## Slide 5 · The whole study on one slide — 35 s

*Walk the three columns with your hand. Do not read the equations aloud.*

> This is the entire study. Three inputs on the left, four steps in the middle,
> three numbers on the right.
>
> The one thing worth noticing is in the input column: only a single quantity
> there is unknown. The heat arriving from below, the density, the heat capacity
> — all of it is fixed from published measurements before I start.
>
> Everything from here on is detail on these four steps.

## Slide 6 · Turning six years of wobble into one number — 50 s

> Step one. The record is not clean. The probes were still shedding heat from
> the drilling, and the electronics drifted.
>
> So I do not pick the good stretch by eye. A rule picks it. Take the longest
> flat run at the tail of each record, reject it if it drifts by more than
> eight-hundredths of a kelvin per year, and whatever drift is left, carry it
> forward as an error instead of discarding it.
>
> That rule runs on all twenty-three sensors identically. Nothing was chosen by
> hand, which means nobody can argue I chose it to get the answer I wanted.

## Slide 7 · A simple picture of the ground, and the equations behind it — 40 s

> Step two is the model, and I want to be clear that this part is standard.
>
> Sunlight comes in at the top. Heat radiates back out. A steady trickle rises
> from the deep interior. In between, heat conducts through the regolith, and the
> material properties depend on temperature and on depth.
>
> Four equations, five constants from the literature, and exactly one unknown:
> the deep conductivity.
>
> Nothing here is new. The next three slides are where something is.

## Slide 8 · The model runs blind — 35 s

> One point to be precise about, because it separates a fit from a result.
>
> The forward model never sees a thermometer. It takes a trial conductivity, runs
> the physics, and predicts a temperature profile. The Apollo data enters at
> exactly one place — the final step, where I score the prediction against it.
>
> The physics never sees the answer it is trying to reproduce.

## Slide 9 · Why this calculation was impossible — 35 s

> Now the obstacle. The calculation has three loops nested inside each other.
>
> The outer loop sweeps about thirty candidate conductivities. Each one needs a
> steady state, which takes roughly three thousand month-long cycles to settle.
> Each cycle is hundreds of time steps.
>
> Multiply it out and one experiment is about twenty-seven hours.
>
> That is not merely slow. That is the reason nobody had done it.

## Slide 10 · The calculation used to take a day, now it takes a minute — 70 s

*Star slide. Slow down. If eyes glaze, use the kettle line.*

> This is the contribution.
>
> The old way, on the left, time-steps every cell in the column, every hour, for
> three thousand cycles, and waits.
>
> But look at what is actually happening. The top seventy centimetres swing with
> the month. Below that the ground is quiet — it just carries a steady flow of
> heat upward. Simulating that deep part cycle after cycle spends almost all the
> computer time on the part that is not doing anything.
>
> So I time-step only the top. Then, from one anchor point at fifty-five
> centimetres, I rebuild everything beneath it in a single downward pass, from
> one equation.
>
> It is the difference between watching a kettle until it boils and knowing what
> boiling looks like.
>
> Twenty-seven hours becomes under a minute. About two and a half thousand times
> faster.
>
> And this matters more than the speed: it is not an approximation. Same answer,
> agreeing to better than one-hundredth of a milliwatt.

## Slide 11 · Both sites hold heat differently than the textbook value — 65 s

*Star slide. Let the bars sit for a beat before you speak.*

> This is the result.
>
> Apollo 15 comes out at four point six. Apollo 17 at seven point one. Both sit
> above the global value of three point four that everyone has been using, and
> Apollo 17 lets heat through about one and a half times more easily than Apollo
> 15.
>
> Now the part nobody asks for, which is exactly why I want to say it first.
>
> If I had bent the model to get this, the fit would have degraded. It did the
> opposite. At Apollo 15 the mismatch went from one point zero nine kelvin to one
> point zero zero. At Apollo 17 it went from zero point eight nine down to zero
> point four zero. Better than halved.
>
> Letting each site have its own conductivity does not just change the answer. It
> explains the measurements better.

## Slide 12 · The model against the actual thermometers — 50 s

> And here is what that means physically, rather than as a score.
>
> The dots are the measured temperatures. The line is the model at the retrieved
> conductivity. Remember slide 8 — the model never saw these points.
>
> The open circles are the shallow sensors. They were excluded from the
> retrieval, so I am not going to quietly claim credit for them here either.
>
> The dashed line is the Martínez and Siegler conductivity model, run forward the
> same way. It is a genuinely different formulation of the physics, and it lands
> close to mine. So the result is not an artefact of one particular equation.

## Slide 13 · Re-running the whole analysis 1500 times — 35 s

*Do NOT say "p-value". It is a bootstrap tail proportion.*

> How confident am I? I ran the entire analysis fifteen hundred times, each run
> leaving out sensors at random and nudging the recorded depths by a couple of
> centimetres.
>
> Two spreads come out, one per site, and they barely overlap.
>
> That overlap is what my confidence in the ordering rests on. Not the width of
> either bar on its own.

## Slide 14 · What I can claim, and what I cannot — 55 s

*Star slide. Level, calm, no apology. This is the slide that earns the rest.*

> Now the honest limit, and I want to state it before anyone has to ask.
>
> A buried thermometer does not measure conductivity. It measures how steeply
> temperature climbs with depth. And that steepness is heat-from-below divided by
> conductivity. Two quantities, one measurement.
>
> Double both and the tilt is identical. So the absolute values ride on the
> published heat flow being right.
>
> What survives that is the ordering. Apollo 17 is the more conductive site in
> over ninety-nine percent of the cases I tested, including when I let the heat
> flow float freely by a factor of four.
>
> What does not survive is the exact size of the gap. The ninety-five percent
> range on the difference runs from minus zero point one two to three point five
> six. It still touches zero.

## Slide 15 · Conclusions — 55 s

*Land these four and stop. Do not add a closing pleasantry.*

> Four things.
>
> One. The two boreholes are genuinely different. Four point six and seven point
> one, about one and a half times apart, and both above the global value
> everyone uses.
>
> Two. A calculation that took a day now takes a minute. That is not a
> convenience. It is what made the uncertainty analysis possible at all —
> fifteen hundred re-runs is not something you do at twenty-seven hours each.
>
> Three. The ordering is robust and the magnitude is not, and I have shown you
> both.
>
> Four. Every mission that looks beneath the lunar surface needs ground truth to
> calibrate against. Right now, this is it.

*Stop. Wait for questions.*

---

# PART 2 — DOCTORAL RESEARCH PLAN · 6 minutes

## Slide 16 · Divider — 10 s

> That is what I have done. Here is where it goes.

## Slide 17 · Five phases, and where the work stands — 45 s

*Point at the dashed vertical rule. That gesture is the whole slide.*

> Five phases. Two are finished, three are proposed.
>
> The dashed line is the important part. Everything to its left exists and has
> been presented. Everything to its right is the proposal.
>
> I am not going to read the columns — they are there so you can read them.
> Let me spend the time on the two that carry the argument: phase two, which is
> the evidence, and phase three, which is what the evidence demands.

## Slide 18 · Phase 1 — the thesis, delivered — 40 s

> Phase one is the thesis you just heard, so I will keep it short.
>
> Both boreholes reproduced. Fifteen hundred bootstrap draws, a Bayesian
> cross-check that floats the heat flow, held-out validation, and a comparison
> against orbital surface temperatures that were never fitted.
>
> One thing I will volunteer rather than defend. The model-selection test is
> decisive at Apollo 17 and not at Apollo 15. Seven sensors is a thin basis for
> its own fitted parameter. The Apollo 15 case rests on the interval, not on that
> test.

## Slide 19 · Phase 2 — real terrain at the two sites — 60 s

*Strongest slide in Part 2. This is the evidence for everything after it.*

> Phase two asks what happens when you stop pretending the ground is flat.
>
> I built a horizon calculation from lunar topography and applied it at both
> sites. Apollo 15 sits below the Apennines and loses one point one six percent
> of its sunlight to its own skyline. Apollo 17 loses zero point one eight.
>
> Then I re-ran the retrieval with that shadowing included, and this is the
> finding. Apollo 15 moves down by two point seven. Apollo 17 moves up by two
> point six.
>
> Opposite directions. Which means no single global correction factor can absorb
> terrain — it would have to push one site up and the other down at the same
> time.
>
> I will also report a negative result: adding infrared self-heating from the
> surrounding slopes made the fit worse, so it is not in the model.

## Slide 20 · Phase 3 — from two neighbourhoods to the whole Moon — 50 s

> That finding is the argument for phase three.
>
> If terrain moves the answer in opposite directions at two sites, you cannot
> correct for it globally. You have to solve for it everywhere.
>
> Same physics, same solver. What changes is scale — a Moon-wide map is millions
> of independent columns.
>
> And this is where the thesis pays for itself. One column now costs about a
> second. Millions of independent columns at a second each is a compute job, not
> a research risk. Before the solver, it was not a job anyone could run.
>
> Validation is against the Diviner global composites.

## Slide 21 · Phase 4 — coupling to TSUKIMI — 45 s

> Phase four is why this work belongs here in particular.
>
> NICT is developing TSUKIMI, a terahertz instrument for observing the Moon.
> Terahertz emission does not come from the surface. It comes from tens of
> centimetres down, below the daily temperature wave.
>
> Which is exactly the region this model was built to resolve.
>
> So the chain is: my subsurface temperature field feeds the radiative transfer,
> that predicts terahertz brightness, and comparing it against what the
> instrument sees gives an ice-survivability map.
>
> That chain only works if someone supplies a trustworthy profile below the skin.
> That is what phases one to three build.

## Slide 22 · Phase 5 — the next-generation regolith model — 35 s

> Phase five is the physics I would like to add, and the point of the slide is
> that the three were weighed before any was attempted.
>
> Depth-varying compaction is the straightforward one. Temperature-dependent
> emissivity matters for permanently shadowed craters. Water vapour diffusion
> with latent heat is genuinely new physics — high risk, which is precisely why
> it is scheduled last and not promised.

## Slide 23 · Why this is achievable — 45 s

*Then stop. Do not summarise the summary.*

> To close, three reasons this is a continuation rather than a wish list.
>
> The solver exists and is verified. That is what turns a Moon-wide map from
> impossible into arithmetic.
>
> The terrain and material-property studies are finished and have been presented
> at AOGS. Phase two is not a plan. It is done.
>
> And the setting is in place: Institute of Science Tokyo, Kasai Laboratory, with
> a direct link to the NICT terahertz mission that phase four depends on.
>
> Thank you.

---

# BACKUP — slides 24 to 40

Not presented. Jump by slide number. Each exists because a specific question is
likely.

| # | Slide | Answers |
|---|---|---|
| 25 | Where the uncertainty comes from | "Why is the error bar so wide?" |
| 26 | The conductivity–heat-flow trade-off | "Could this be a heat-flow difference instead?" |
| 27 | Is a per-site value statistically justified? | "Is the difference significant?" |
| 28 | Independent check against orbital data | "How do you know the model is right?" |
| 29 | Does it hold when you hold data back? | "Are you over-fitting seven sensors?" |
| 30 | The Bayesian cross-check | "What if the published heat flow is wrong?" |
| 31 | The bootstrap, as published | "Show me the real distribution." |
| 32 | Finding the answer: the RMSE bowl | "How exactly did you pick the value?" |
| 33 | What the old method had to do | "Explain the speed-up." |
| 34 | The anchor method, step by step | "How does the anchor method actually work?" |
| 35 | The flux-anchored loop | "Show me the algorithm." |
| 36 | From the heat equation to the closure | "Where does the closure come from?" |
| 37 | How one sensor becomes one temperature | "How were the windows chosen?" |
| 38 | Terrain shadowing at both sites | "How was the DEM used?" |
| 39 | The AOGS parameter study | "Show me the real analysis." |
| 40 | The three bugs, and what each cost | "What went wrong along the way?" |

---

# Q&A preparation

The honest answer is the strong answer in every one of these. Do not defend past
the evidence.

**"Is the difference statistically significant?"** → slide 27.
No, not at the ninety-five percent level. The interval on the difference runs
from minus zero point one two to three point five six, and it touches zero. What
is significant is the ordering — Apollo 17 is more conductive in over
ninety-nine percent of tested cases. The model-selection test is decisive at
Apollo 17, minus twenty-three, and not at Apollo 15, plus three. That split is
in the thesis.

**"You are fitting seven sensors with a free parameter."** → slides 27, 29.
Correct, and that is exactly why Apollo 15 does not pass the model-selection
test. Leave-one-deepest-out and cross-prediction still reproduce the value, but I
would not claim Apollo 15 alone justifies a separate fit.

**"What if Langseth's heat flow is wrong?"** → slides 26, 30.
Then the absolute numbers move, which is slide 14, and I raised it myself. The
Bayesian version floats the heat flow over a factor of four and the ordering
survives at ninety-nine point two percent. Slide 26 shows the two sites respond
to a flux revision in opposite directions, which is why the ordering is harder to
break than the magnitude.

**"Two and a half thousand times faster — really?"** → slides 33, 35.
Two separate factors, and I should be precise. About twenty-one times from the
algorithm, because the deep column is reconstructed rather than simulated. About
one hundred and seventeen times from compiling the kernel. Multiplied, roughly
two and a half thousand — and that figure is compiled-anchored against
interpreted-brute-force. The algorithmic contribution on its own is the
twenty-one.

**"Is the anchor method an approximation?"** → slides 34, 35, 36.
No. It is exact for a periodic steady state, and the condition is stated on the
slide. Once the column repeats its monthly cycle the time-derivative averages to
zero, and the deep profile is fixed by an ordinary differential equation.
Certified against brute force to better than one-hundredth of a milliwatt.

**"How do you know the code is right?"** → slide 28.
Two independent checks. The surface temperature was never fitted, so comparing
it against Diviner is genuinely out-of-sample, and it closes. And the solver
exists in three separate implementations — interpreted Python, the compiled
kernel, and a C++ port — verified equal to better than a millionth of a kelvin.

**"Why is chi two point seven?"**
It is Hayne 2017's published value, and Vasavada 2012 explicitly raises the
radiative coefficient to two point seven. The absolute conductivities are
conditional on it. I tested the alternative and the ordering does not change.

**"Why only sixteen pixels per degree for the topography?"** → slide 38.
That is the global product, and it is coarse for a horizon calculation. Higher
resolution would raise both shadowing losses rather than reverse their signs.
Doing it at full resolution is part of phase three.

**"What about the shallow sensors?"** → slides 12, 37.
Excluded above eighty centimetres because the drilling disturbed the ground
there, and the borestem conducts heat down from the surface. Slide 37 is the
decision rule. They are drawn open wherever they appear, so they are never
quietly counted as agreement.

**"Only two sites — can you generalise?"**
No, and I do not. Two boreholes cannot establish how the Moon varies as a whole.
What they establish is that at least this much site-to-site variation exists,
which is enough to make a single global value an assumption rather than a fact.
Generalising is a measurement problem. It needs more landers.

---

# Numbers, so you never guess at the podium

All certified against `code/results/*.json`.

| Quantity | Apollo 15 | Apollo 17 |
|---|---|---|
| Retrieved K_d (mW m⁻¹ K⁻¹) | 4.60 | 7.08 |
| 95% bootstrap interval | [4.18, 6.96] | [6.16, 8.07] |
| Misfit, global → per-site (K) | 1.09 → 1.00 | 0.89 → 0.40 |
| Deep sensors used | 7 | 16 |
| ΔAICc | +2.94 (not decisive) | −23.17 (decisive) |
| Horizon elevation | 14.0° | 10.1° |
| Insolation lost to terrain | 1.16% | 0.18% |
| K_d under shadowing | 4.60 → 1.88 | 7.08 → 9.69 |

Global value in use **3.4**. Ratio between sites **≈1.5×**. Inter-site contrast
**2.31** median, 95% interval **[−0.12, 3.56]**, bootstrap tail proportion
**0.031** — *not* a p-value, do not call it one. MCMC ordering **99.2%**.
Speed-up **≈2500×** total (**21×** algorithmic × **117×** compiled kernel);
brute-force sweep **26.6 h** against **0.65 min** anchored. Anchor depth
**0.55 m**, borestem cut **80 cm**, drift limit **0.08 K yr⁻¹**, bootstrap
**1500** draws with **2.5 cm** depth jitter. Three-implementation agreement
better than **10⁻⁶ K**.

---

# Delivery checklist

- [ ] Rehearse slides 10, 11 and 14 out loud — those three carry the talk
- [ ] Time a full run: target 11:30 for Part 1, 5:30 for Part 2
- [ ] Check the GIFs on slides 2, 33, 34 and 38 animate on the GEDES laptop
- [ ] Memorise four backup numbers: **27** significance, **30** heat flow,
      **33** speed-up, **38** terrain
- [ ] Arrive early and verify the pre-loaded deck is the right file
