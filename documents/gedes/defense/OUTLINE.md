# Defense deck — flow and outline
**Edit this file freely.** Anything you change here I can push into the deck.

## The story in one sentence
*Everyone assumes the Moon insulates itself the same way everywhere; I checked that
assumption at the only two places it can be checked, found it wrong at both, and built
the tool that made checking affordable.*

## The arc

```
  ACT 1  SETUP           ACT 2  METHOD          ACT 3  PAYOFF        ACT 4  FORWARD
  slides 2-4             slides 5-8             slides 9-12          slides 13-19
  ──────────────         ──────────────         ──────────────       ──────────────
  why you should care    how I did it           what I found         where it goes
  what nobody checked    (the contribution)     what I can't claim   (already started)
        4.5 min                3.5 min              3.5 min              6 min
```

---

## PART 1 — MASTER'S THESIS · 12 min

| # | Beat | Slide title | Visual | Takeaway line | Time |
|---|---|---|---|---|---|
| 1 | — | *How well does the Moon hold its heat?* | — | name, ID, supervisors | 20s |
| 2 | **Hook** | The surface is violent. A metre down, nothing moves. | 🎞 `anim_hook.gif` | Ice survives only where the ground is cold and steady | 50s |
| 3 | **Gap** | Every model uses one number for the whole Moon | `lay_gap` | — | 55s |
| 4 | **Data** | Only two holes have ever been drilled and instrumented | `lay_boreholes` | Apollo 15 & 17, 1971–77, recovered from mission tapes | 55s |
| 5 | Method 1/3 | Turning six years of wobble into one honest number | `lay_window` | — | 55s |
| 6 | Method 2/3 | A simple picture of the ground | `lay_model` | Sun in, heat out, trickle from below | 50s |
| 7 | ★ **Method 3/3** | The calculation used to take a day. Now it takes a minute. | `lay_solver` | Rebuild the deep part from one anchor instead of simulating | 80s |
| 8 | Method | Try every value, keep the one that fits best | `lay_bowl` | — | 50s |
| 9 | ★ **RESULT** | Both sites hold heat differently than the textbook value | `lay_results` | A17 ≈1.5× A15; both exceed the global value | 75s |
| 10 | Rigour | Re-running the whole analysis 1500 times | `bootstrap` *(thesis fig)* | Resample sensors + jitter depths | 55s |
| 11 | ★ **Honesty** | What I can claim, and what I cannot | `lay_seesaw` | — | 65s |
| 12 | **Close** | Conclusions | 3 numbered rows + caveat bar | — | 60s |

**Spoken total: 10.1 min** → ~1.5 min of headroom for pauses and the animation loop.

---

## PART 2 — DOCTORAL PLAN · 6 min

| # | Beat | Slide title | Visual | Time |
|---|---|---|---|---|
| 13 | Divider | Doctoral Research Plan | dark | 10s |
| 14 | **Ambition** | Two points are not a map | `lay_global` | 35s |
| 15 | Evidence 1 | Step 1: put the real landscape into the model | 🎞 `shadowing.gif` | 55s |
| 16 | ★ **Evidence 2** | Step 2: find out which property actually matters | `aogs_cpvc` | 65s |
| 17 | Evidence 3 | Step 3: check that the physics travels | 3 stat cards | 40s |
| 18 | ★ **Plan** | Three years, three deliverables | Y1/Y2/Y3 cards | 80s |
| 19 | **Close** | The hard part is already done | dark, 3 rows | 50s |

**Spoken total: 4.7 min** → ~1 min headroom.

The rhetorical move in Part 2: **three slides of completed work before any promise.**
By the time the plan appears on 18, the committee has already seen that you can execute.

---

## BACKUP · not presented

| # | Question it answers |
|---|---|
| 20 | *(divider)* |
| 21 | Why is the error bar so wide? |
| 22 | Could this be a heat-flow difference instead? |
| 23 | Is the difference statistically significant? |
| 24 | How do you know the model is right? |
| 25 | Explain the speed-up in more detail |
| 26 | **EN/JP term table** (GEDES requirement — must be last) |

---

## Edit notes
<!-- Write your changes below. Anything here I will implement. -->

-
-
-
