# Defending the error budget

**For the viva. The thesis is submitted; nothing here proposes changing it.**
This is the strongest honest justification for each row of Table 4.1, the
concession to make if pushed, and the sentence to say.

Companion: `ERROR_BUDGET_PROVENANCE.md` (what each source actually says).

---

## The frame to establish first, before any row is questioned

Say this early, ideally unprompted, because it makes every later answer easy:

> "The budget is not a set of calibrated standard errors. Each row is the
> half-range of the retrieval as one input is swept across a bounded interval
> from the literature. It answers 'which inputs matter', not 'what is the
> probability distribution of K_d'."

**This is already in the thesis, in writing** (§Error budget): *"The totals are
sensitivity summaries, reliable for judging which inputs matter, not calibrated
standard errors."* You are not retreating to it under pressure — you wrote it
first.

The thesis also pre-empts the obvious follow-up ("why not 3σ?") and answers it:
most rows are half-ranges of bounded intervals, not Gaussian σ; tripling them
would claim an input can sit three times outside its published range, and it
drives K_d*(A15) negative, which is unphysical. **That is a stronger answer than
most examiners expect.**

---

## Row 1 — Q_b (σ = 1.61 / 1.66). Fully defensible.

**Verified exactly.** Langseth, Keihm & Peters (1976), p. 3143 and p. 3156:

> "At the Apollo 15 site a heat-flow value of **2.1 μW/cm²** is the mean of the
> two probe measurements and at Apollo 17, the probe 1 value of **1.6 μW/cm²**
> is considered the more reliable measurement."
>
> "Errors of the measurements … are estimated at **±15 %**."

21 and 16 mW m⁻² — exact. The A17 "probe 1 only" choice is **the paper's own
recommendation**, not yours. Worth saying: it shows you read the source rather
than averaging blindly.

**If pushed on the envelope width** (you use A15 14–25, A17 10–18, wider than
±15 %):

> "The envelope is deliberately wider than Langseth's ±15 % because it spans the
> later re-analyses as well — Langseth's own regional correction at
> Taurus-Littrow gives 1.4 μW/cm² against the 1.6 borehole value, and Saito and
> Nagihara revisit both. Widening the interval makes the budget more
> conservative, not less."

That is true and checkable: Langseth's abstract gives the 1.4 regional estimate,
and Table 2 gives the Taurus-Littrow topographic correction as +10.0 ± 4.0 %.

**Concede if pressed hard:** the exact lower bounds trace to Saito (2007) and
Nagihara (2018) rather than to Langseth, and you widened rather than narrowed.
That is the conservative direction.

---

## Row 2 — Albedo (σ = 0.72 / 2.96). The largest row. Defensible if framed right.

**The trap:** ±0.01 is not a published error bar. Vasavada (2012) states no
albedo uncertainty.

**The defense — and this is already how the thesis words it.** §Error budget
says the Apollo 17 misfit *"responds nearly flatly to K_d and even a ±0.01
albedo change moves the minimum substantially."* Read that carefully: ±0.01 is
deployed as a **demonstration of weak constraint**, not as a measurement
uncertainty. The sentence means "this site is barely constrained — a tiny
albedo change swamps it." That is the honest and correct reading.

> "±0.01 is not a published error bar and I do not present it as one. It is a
> deliberately small perturbation, chosen to show how weakly Apollo 17
> constrains K_d: shift the albedo by less than one part in thirteen and the
> RMSE minimum moves further than the entire statistical uncertainty. That is
> the point of the row."

**Supporting fact worth having:** ±0.01 is roughly the spread between published
choices anyway — the thesis uses 0.131/0.137 per site, Hayne (2017) uses a
global A₀ = 0.12. So the interval is comparable to the real disagreement in the
literature, not invented.

---

## Row 3 — K_s ±30 % (σ = 0.36 / 1.55). Defensible as an assumed envelope.

**The trap:** Cremers & Birkebak (1971) report one Apollo 12 sample at one
density — 1.2 → 3.5 mW m⁻¹ K⁻¹ over 160–428 K. That is a *temperature
dependence*, not a ±30 % scatter.

**The defense:** K_s is a fitted parameter of the Hayne form, not a directly
measured quantity, so no paper publishes a σ for it. ±30 % is an assumed
envelope covering the sample-to-sample spread in the lab literature.

> "K_s is a fitted coefficient of the conductivity parameterisation, so there is
> no published uncertainty to quote. I assumed ±30 %, which is the order of the
> spread between lab samples. It is an assumption, and the row is there to show
> the retrieval is not very sensitive to it — 0.36 at Apollo 15."

**Do not claim** Cremers publishes ±30 %. Say "the order of the lab scatter."

*(Housekeeping: `code/references/cremers1971_apollo11_fines.pdf` is actually the
**Apollo 12** paper. Filename only — the citation in the thesis is correct.)*

---

## Row 4 — χ = 1.48. The one real exposure. Here is how to handle it.

**What the thesis says** (§Caveats): *"Re-retrieving at the \citet{vasavada2012}
normalization χ = 1.48 drives the RMSE minimum outside the physical sweep range
at both sites."*

**The problem:** Vasavada et al. (2012) as published use **χ = 2.7** — the same
as Hayne. They say so explicitly: *"we increase c to 2.7 (from 1.5) at the
surface in the revised model."* The value 1.48 appears nowhere in Vasavada 2012
or in Hayne 2017. The nearest published number is **1.5**, their *superseded*
pre-revision value.

**Why this is survivable — and it genuinely is. I re-ran it.**

The claim the thesis makes does not depend on the exact number. What the
sensitivity shows is that at a materially lower χ the RMSE minimum **rails
against the sweep boundary at both sites** — the retrieval stops having an
interior solution at all.

Re-retrieved 2026-07-27 at both values, full sweep, production settings:

| χ | Apollo 15 | Apollo 17 |
|---|---|---|
| 2.7 (adopted) | 4.600 — interior minimum | 7.079 — interior minimum |
| **1.48** (as written) | **1.000 — railed at low grid edge** | **25.000 — railed at high grid edge** |
| **1.50** (Vasavada's actual pre-revision value) | **1.000 — railed, identical** | **25.000 — railed, identical** |

The two are **numerically identical**, to every digit, at both sites. The
solver even emits its own warning — *"RMSE minimum sits at the EDGE of the K_d
grid — no parabola bracket"* — so these are not converged retrievals at all;
they are the sweep failing to contain a solution. That is precisely what the
thesis says happens.

**So the conclusion "K_d* is conditional on the published χ" is verified robust
to the choice of alternative value.** You can state this as a fact you checked,
not as a hope.

**If asked directly "where does 1.48 come from?":**

> "That is the pre-revision value in the Vasavada model lineage — they state
> they raised c to 2.7 from 1.5. Calling it 'the Vasavada normalization' in the
> caveat is looser than it should be, and 1.5 would have been the cleaner label.
> The substance is unaffected: the point of that test is that *any* materially
> lower χ pushes the minimum outside the physical sweep range at both sites, so
> the absolute K_d is conditional on the adopted χ. Re-running at 1.5 gives the
> same conclusion."

**Do not** defend 1.48 as a competing published value. Concede the label,
hold the conclusion. The conclusion is the part that matters and it is correct.

---

## Row 5 — ρ_d 1700–2000 (σ = 0.007 / 0.33). Low stakes.

Carrier (1991) gives 1.66 ± 0.05 g cm⁻³ for the top 60 cm and penetrometry of
1.58–1.76. The 2000 upper bound is above those pages, though density does keep
rising below 60 cm.

> "The density interval brackets the Apollo core measurements extended to metre
> depth. It contributes 0.007 and 0.33 — the smallest rows in the budget — so
> the exact bound does not affect any conclusion."

True, and the numbers back it.

---

## Row 6 — Statistical, solver, depth cut, threshold, epoch. No exposure.

All are **your own** convergence and sensitivity sweeps, reproducible from the
repository. Nothing to attribute. The solver row (0.04) is the discretisation
certification; the epoch row (0.89 at A17) is the common-1974 re-fit.

---

## The one question that would hurt, and its answer

**"Your quadrature assumes the rows are independent. Are they?"**

Not entirely — and **the thesis says so, before anyone asks**: *"The statistical
and Q_b rows both propagate along the same K_d–Q_b ridge, so the quadrature
assumes an independence that is only approximate, and several rows are
half-ranges of visibly asymmetric responses (the A17 albedo row especially)."*

> "No, and I say so in the text. Q_b and the statistical row share the same
> degeneracy ridge, so the total is not a rigorous convolution. That is exactly
> why I call the totals sensitivity summaries rather than standard errors, and
> why the headline claim is the ordering rather than the magnitude."

---

## The through-line

Every soft spot in this budget points the same way: **the absolute K_d values
carry large, partly-assumed systematics, while the ordering does not.** That is
already the thesis's headline framing. The budget is not the weak point of the
argument — it is the part that demonstrates you know where the weak points are.

If the whole exchange goes badly, the fallback is one sentence:

> "The magnitudes are conditional on published inputs I did not measure. The
> ordering — Apollo 17 more conductive than Apollo 15 — survives every input I
> varied, in over 99 % of tested cases. That is the claim I am defending."
