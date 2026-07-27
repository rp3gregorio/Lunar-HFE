# Speaker script — GEDES defense
**Ramon III P. Gregorio · 24M58378 · Institute of Science Tokyo, Kasai Laboratory**

Written for an audience with **little or no background** in lunar science.
Rule of thumb: ~130 words per minute. Everything below is timed to that.

| Part | Slides | Speaking | Q&A |
|---|---|---|---|
| Master's thesis | 1–12 | **12 min** | 5 min |
| Doctoral plan | 13–19 | **6 min** | 7 min |
| Backup (not presented) | 20–25 | — | on demand |
| Term table | 26 | — | — |

**Three rules for the day.** Say the numbers out loud — they are your evidence.
Never apologise for the caveat on slide 11; stating it plainly is what makes the
rest believable. If you run long, cut slide 8, not slide 11.

---

# PART 1 — MASTER'S THESIS (12 min)

## Slide 1 · Title — 20 s
> Good morning. My name is Ramon Gregorio, from Kasai Laboratory.
>
> My thesis asks a simple question: **how well does the Moon hold on to its heat?**
> And I answer it at the only two places where humans have ever dug deep enough
> to find out.

*Pause. Advance.*

## Slide 2 · Why this matters — 50 s
*(Let the animation loop once before speaking.)*

> Look at what happens on the Moon over one month. At the surface, the
> temperature swings from about 100 kelvin at night to 390 kelvin at noon —
> hotter than boiling water, then colder than liquid nitrogen. Every month.
>
> Now watch the two numbers on the right. The top one is the surface — it is
> tearing up and down all month. The bottom one is a single metre below it, and
> it does not move at all. Not by a tenth of a degree.
>
> That violent swing dies away within about the top fifteen centimetres. By
> **80 centimetres**, it is completely gone.
>
> That steady deep temperature is what matters. It decides whether water ice can
> survive underground. It is the number every future lunar mission needs. And no
> instrument can measure it from orbit — it has to be calculated.

## Slide 3 · The problem — 55 s
> To calculate it, you need one key property of the ground: **how easily heat
> moves through it.** We call it K-d.
>
> Here is the problem. Every thermal model of the Moon in use today takes a
> single value — 3.4 — and applies it to the entire Moon. Every crater, every
> plain, every latitude. One number.
>
> And that number has a weakness. It was fitted using satellite data, and a
> satellite only feels the top few centimetres — the part that is swinging
> wildly. It has **never been checked against a measurement from deep
> underground.**
>
> There are exactly two places where it can be checked. That is what this thesis
> does.

## Slide 4 · The data — 55 s
> Those two places are the Apollo 15 and Apollo 17 landing sites.
>
> The astronauts drilled into the surface and left thermometers in the holes —
> 1.4 metres deep at Apollo 15, 2.3 metres at Apollo 17. Those instruments
> recorded temperatures from 1971 to 1977. This is still, today, the only
> subsurface temperature data that exists anywhere on the Moon.
>
> The full record was recovered from the original mission tapes only a few years
> ago. I use it here.
>
> One important choice: I throw away everything in the top 80 centimetres. The
> act of drilling disturbed the ground and the drill stem itself conducts heat.
> That leaves me **23 trustworthy sensors** — seven at Apollo 15, sixteen at
> Apollo 17.

## Slide 5 · Step 1 — 55 s
> Now, three steps. The first is preparing the data.
>
> Each thermometer gives six years of readings, and the early part is unusable —
> the ground is still recovering from the drilling, there are disturbances from
> mission operations, and the instruments drift.
>
> So I wrote an automatic rule: find the longest stretch at the end of each
> record that is genuinely flat — where the trend is less than 0.08 kelvin per
> year — and average inside it. If no stretch qualifies, fall back to the final
> quarter and carry the leftover drift as an error.
>
> The point is that **nothing here is hand-picked.** The same rule runs on every
> sensor, and anyone can reproduce it. That turns six years of wobble into one
> honest number per sensor.

## Slide 6 · Step 2 — 50 s
> Step two is the physics, and it is refreshingly simple.
>
> I model a single column of lunar soil. Sunlight comes in at the top. Heat
> radiates back out to space. And from underneath, there is a slow, steady
> trickle of heat leaking out of the Moon's interior.
>
> Everything in that picture is known and measured, except one thing: **how
> easily heat moves through the middle.** That is the unknown I am solving for.

## Slide 7 · Step 3 — my contribution — 80 s ★
> Step three is where I had to do something new.
>
> To find that unknown, I have to run the simulation until the ground settles
> into its repeating monthly rhythm. The trouble is that settling takes about
> **3000 simulated months.** One experiment took roughly a day of computing.
> And I needed hundreds of them. That is not practical.
>
> So here is the idea. Once the ground has settled into that repeating cycle,
> the average amount of heat flowing through it is the same at every depth. That
> is a strong constraint. It means I do not have to simulate the deep part at
> all — I can solve only the thin, sun-baked skin at the top, and then
> **reconstruct everything below it** from a single anchor point.
>
> The result is that a calculation that took 27 hours now takes under a minute.
> About **2500 times faster.**
>
> And that is not just convenience. It is what made the next part possible:
> because each answer is now cheap, I can afford to repeat the entire analysis
> thousands of times and find out how uncertain the answer really is.

*This is your contribution. Do not rush it. If someone's eyes glaze, use the
kettle line: "you don't need to watch a kettle boil 3000 times to know how hot
it ends up."*

## Slide 8 · Finding the answer — 50 s
> Finding the answer itself is then straightforward. I try many candidate
> values. For each one I run the model and measure how badly it misses the real
> Apollo thermometers. That traces out a curve, and the lowest point of the
> curve is the best answer.
>
> Apollo 15 lands at 4.60. Apollo 17 lands at 7.08.

## Slide 9 · Result — 75 s ★
> And here is the headline.
>
> The value everyone currently uses for the whole Moon is 3.4. At Apollo 15, the
> ground actually requires **4.60**. At Apollo 17, it requires **7.08**.
>
> Two things stand out. First, both sites are **more conductive than the global
> value** — the standard number is too low at both places we can check. Second,
> the two sites differ from each other by roughly a factor of one and a half.
>
> And the fits genuinely improve. At Apollo 17 the mismatch with the real
> thermometers drops from 0.89 kelvin to 0.40 — it more than halves. At Apollo
> 15 it improves more modestly, from 1.09 to 1.00.

## Slide 10 · How sure am I? — 55 s
> The obvious question is: how confident am I in those numbers?
>
> To answer that I re-ran the whole analysis **1500 times.** Each time I randomly
> resample which sensors are included and jitter their recorded depths by their
> real uncertainty. That gives me the full spread of answers the data can
> support, rather than a single number with no error bar.
>
> You can see the two sites sit in largely separate places — which is why I am
> confident about the *ordering*. But I want to be equally clear that the
> statistical spread is not the whole story, and that brings me to the most
> important slide in this talk.

## Slide 11 · The honest limit — 65 s ★
> Here is what the thermometers actually measure.
>
> They do not measure conductivity directly. They measure how steeply the
> temperature rises as you go down. And that steepness is a **ratio** — the heat
> coming from below, divided by the conductivity.
>
> That has a consequence I have to be straight about. If a site's temperature
> rises more steeply, it could be because the ground conducts heat differently —
> or because more heat is arriving from the interior. My data alone cannot fully
> separate those two explanations.
>
> So let me split my result in two.
>
> **What is solid:** Apollo 17 is the more conductive site. I tested this across
> the entire published range of interior heat-flow values, and the ordering holds
> in more than 99% of cases.
>
> **What is not settled:** the exact size of the gap. Its confidence interval
> still touches zero, and I say so in the thesis rather than rounding it away.

*Deliver this calmly and slowly. It is the slide that earns you credibility.*

## Slide 12 · Conclusions — 60 s
> Three sentences to finish.
>
> **One.** The two Apollo boreholes genuinely require different values — 4.60 and
> 7.08 — and both are higher than the single global number in use today.
>
> **Two.** I built a method that made a day-long calculation take a minute, about
> 2500 times faster, and that is what made a full uncertainty analysis possible.
>
> **Three.** These are the only in-situ anchors that exist. Missions that look
> beneath the lunar surface need exactly this kind of temperature profile, and no
> satellite can supply it.
>
> With the honest caveat that the *direction* of the difference is solid while
> its *size* is not yet nailed down.
>
> Thank you.

*Stop here. Do not add a thank-you slide — leave the result on screen.*

---

# PART 2 — DOCTORAL RESEARCH PLAN (6 min)

## Slide 13 · Divider — 10 s
> That is the work I have completed. Let me now turn to where I want to take it.

## Slide 14 · The goal — 35 s
> My thesis measured two points on the Moon. But the question people actually
> want answered — *where can water ice survive underground* — is a question about
> the **whole** Moon.
>
> So my doctoral goal is to go from two measured points to a Moon-wide map, and
> then to turn that map into an index of where subsurface ice can persist.
>
> I want to show you that this is already underway, not just a wish.

## Slide 15 · Already built (1) — 55 s
> The first step is putting the real landscape into the model.
>
> My thesis assumed flat ground. In reality Apollo 15 sits at the foot of the
> Apennine mountains, and Apollo 17 sits in a valley between two massifs. Those
> mountains block sunlight near sunrise and sunset, and they radiate heat back
> onto the site at midday.
>
> I have already implemented this using elevation maps. The horizon reaches 14
> degrees at Apollo 15, removing about 1.2% of the incoming sunlight; at Apollo
> 17 it is 10 degrees and 0.2%.
>
> This work was presented at AOGS. It is **built and tested**, not proposed.

## Slide 16 · Already built (2) — 65 s ★
> The second step was to find out which property of the ground actually controls
> the answer. I ran 650 model variations to find out.
>
> The result is clear. Changing the heat capacity barely moves the answer —
> it is a second-order effect. But linking the conductivity to the **density**
> of the soil moves it a great deal — it is first-order.
>
> And when I let the ground be layered, rather than uniform, the model fits the
> real thermometers **2.6 times better at Apollo 15 and 10 times better at
> Apollo 17.**
>
> That matters because it tells me exactly which knob to turn before I attempt a
> global model. I am not proposing to go and find out — I already know.

## Slide 17 · The key test — 40 s
> One more test, and it is the one that convinced me a global model is
> justified.
>
> I took the best configuration from one site and applied it, untouched, at the
> other. If this were just curve-fitting, that would fall apart. Instead it
> degrades gracefully — and still beats the uniform-ground assumption everywhere.
>
> That means what I am capturing is **transferable physics**, not a fit tuned to
> one hole in the ground. That is the licence to go global.

## Slide 18 · The plan — 80 s ★
> So, three years, with a deliverable each year.
>
> **Year one: get the physics right.** Finish the property work — the
> density-linked conductivity — go beyond the standard formula, and validate
> against both boreholes. The deliverable is a validated property model.
>
> **Year two: go global.** Apply terrain shading across the entire Moon, compute
> a temperature profile for every point on the surface, and check the result
> against orbital measurements. The deliverable is a Moon-wide subsurface
> temperature map.
>
> **Year three: answer the question.** Convert those profiles into where
> subsurface ice can actually survive, and feed the columns to missions that
> sound beneath the surface. The deliverable is an ice-survivability map, and the
> publication of the global product.

## Slide 19 · Why it is achievable — 50 s
> Finally, why I believe this is achievable in three years.
>
> A Moon-wide map is millions of independent columns. That would have been
> impossible at a day per column — but the solver I built for my thesis brings
> each one down to about a second, and they can all run in parallel.
>
> The terrain work and the property study are already finished. The controlling
> parameter is already identified. And the work has a home — Kasai Laboratory,
> with the link to the NICT terahertz mission that will use these profiles.
>
> This is not a new project. It is the continuation of one that is already
> running.
>
> Thank you.

---

# Q&A PREPARATION

**Master's Q&A (5 min) — most likely questions**

**"Is the difference between the two sites statistically significant?"**
> Not at the 95% level, and I say so directly in the thesis. The confidence
> interval on the difference touches zero. What *is* robust is the ordering —
> Apollo 17 is the more conductive site in over 99% of the cases I tested across
> the published heat-flow range. I report the direction as solid and the
> magnitude as marginal. *(Backup slide 23.)*

**"Could this be a difference in heat flow rather than conductivity?"**
> Yes — and I cannot fully rule it out, because the thermometers constrain the
> ratio of the two. What I can say is that the two sites respond to a heat-flow
> revision in *opposite* directions, which is exactly why the ordering survives
> even when I vary it. *(Backup slide 22.)*

**"Why throw away the top 80 centimetres?"**
> Two reasons. The drilling physically disturbed the ground, and the fiberglass
> drill stem conducts heat down from the surface. I show this independently: the
> daily temperature swing above 80 cm is far larger than the model allows, which
> is the signature of that heat short. Below 80 cm it disappears. I also tested
> cuts at 70 and 90 cm and the answer barely moves.

**"How do you know your model is right at all?"**
> An out-of-sample test. I never fit surface temperatures — but I can compare the
> model's predicted surface temperature against orbital measurements from the
> Diviner instrument. It closes. And the whole solver was independently
> reimplemented in C++ and agrees to twelve decimal places. *(Backup slide 24.)*

**"Only two data points — can you generalise?"**
> No, and I do not claim to. Two boreholes cannot establish how the Moon varies
> as a whole. What they establish is that **at least this much site-to-site
> variation exists**, which is enough to show that a single global value is an
> assumption, not a fact. Generalising is a measurement problem — it needs more
> landers.

**Doctoral Q&A (7 min) — most likely questions**

**"Is three years realistic?"**
> The two hardest pieces are already done — the fast solver and the parameter
> study. Year one finishes physics I have already started; year two is
> computation that is naturally parallel; year three is the analysis. The risk is
> in year two's validation, and my fallback is to restrict to well-mapped
> equatorial terrain first.

**"Your data are equatorial — ice is at the poles. Does this transfer?"**
> That is the sharpest question, and the honest answer is that transfer is not
> established. Apollo 15 and 17 are warm, dry, low-latitude sites. Polar regolith
> is colder and may be ice-cemented, which changes the physics. My plan treats
> the Apollo sites as *calibration anchors* for the method, not as
> representative of the poles. Bridging that gap will need polar in-situ data —
> Chandrayaan-3's ChaSTE is the first step.

**"What is genuinely new compared to your master's?"**
> The master's retrieves one number at two points on flat ground. The doctorate
> makes the ground layered and realistic, puts real terrain into the forcing, and
> extends from two points to global coverage — ending at a product, an
> ice-survivability map, rather than a single parameter.

---

# DELIVERY CHECKLIST

- [ ] Confirm the Japanese terms on slide 25 with someone in the lab
- [ ] Rehearse slides 7, 9, 11 out loud — they carry the talk
- [ ] Time a full run; target 11:30 for part 1, 5:30 for part 2
- [ ] Check the GIFs on slides 2 and 15 actually animate on the GEDES laptop
- [ ] Know your backup slide numbers: **21** error budget, **22** degeneracy, **23** significance, **24** validation, **25** solver animation
- [ ] Arrive early — the instructions say slides are pre-loaded, so verify them
