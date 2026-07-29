# Findings from the guidebook research pass (2026-07-27)

Surfaced while gathering implementation facts for the fresh guidebook. Split by
whether it affects only the guidebook, or reaches the thesis and letter too.

---

## A. Reaches the thesis (a submission artifact) — decide before the defense

### A1. One thesis sentence is strictly false
`documents/gedes/thesis/thesis.tex:1682`

> "A discrete three-layer alternative fitted per site does not outperform the
> site-fitted Hayne form at either site."

At Apollo 15 it does, narrowly. From `code/results/model_selection.json`:

| A15 model | RMSE (K) | AICc |
|---|---|---|
| `hayne_global` | 1.0939 | **4.057** ← lowest |
| `layer3_fit` | 0.9795 | 6.709 |
| `hayne_fit` | 0.9998 | 6.998 |

`layer3_fit` beats `hayne_fit` by 0.29 AICc. The gap is deep inside the
ΔAICc < 2 indistinguishability band, so the *scientific* claim is unharmed, but
the sentence as written is not what the artifact says. Safer wording: "does not
meaningfully outperform ... the three models are statistically indistinguishable
at Apollo 15 (spread < 3 AICc)".

### A2. The Apollo 17 three-layer row is a grid floor, not a fit
`kd_star_3layer_edge_limited: true`, `kd_star_3layer = 0.003` exactly, and the
RMSE curve rises monotonically from its first grid point. The true optimum lies
**below** the sweep floor of 3.0 mW m⁻¹ K⁻¹.

`compute_model_selection.py` consumes `kd_star_3layer` without checking that
flag. So the A17 three-layer AICc (+26.96 vs `hayne_fit`) compares against an
unconverged fit. The honest defense answer to "why does the three-layer model
lose at A17?" is *"its optimum is outside my sweep, so that row is a bound, not
a comparison"* — not *"the data reject it"*.

### A3. `TL_RHO_SITE` is defined twice, with inverted physics
This violates the CLAUDE.md rule that config lives in `config.py` only.

| File | A15 | A17 | Story |
|---|---|---|---|
| `code/src/lunar/config.py:119` | 2000 | 1900 | A15 denser. **What the retrieval uses.** |
| `code/pipeline/figures/make_letter_figures.py:111` | 1825 | 1960 | A17 denser, cited to Grott 2010. Illustration only. |

The figure's narrative ("the A17 column, being denser, reaches the deep value
faster") is inverted relative to what the retrieval actually computes: the config
values give ramp exponents p(A15) = 0.944 < p(A17) = 0.972, so **A15** ramps
faster. A third partial copy of `TL_Z1/TL_Z2` sits in `make_intro_figures.py:63`.

### A4. The three-layer model has an uncounted free parameter
`TL_RHO_SITE` is described in config as "per-site RMSE-optimal deep rho", i.e.
tuned against the same deep-sensor data used for model selection. Yet
`compute_model_selection.py:86` passes `n_free=1`. Honest accounting is k = 3,
not k = 2. This does not change the A17 conclusion (the margin is 27 AICc) but it
does further weaken the already-tied A15 comparison.

---

## B. Guidebook-only — fix while writing

| # | Issue | Correct value |
|---|---|---|
| B1 | `guidebook.tex:2288` says P(A17>A15) = 99.3% | **99.2%** (0.99246). The Jacobian fix moved it. |
| B2 | `figures-tikz/mcmcflow.tex` says K_d flat in log over [1,30] | Per-site: A15 [0.8, 9.0], A17 [3.0, 15.0] |
| B3 | Symbol table: anchor "0.25 then 0.55 m", skin depth 0.04–0.10 m | 0.55 m; 3–5 cm |
| B4 | Archived AICc section: M1/M2/M3, ΔAICc 3.99 / 2.71, "M1 wins" | Model set no longer used. Pooled test now has **M3 (the null) lowest**, all within 0.6. |
| B5 | Archived threshold "≳2 notable, ≳4 strong" | 2 / 10, cited to `burnham2002` |
| B6 | Archived Martínez section quotes 4.58 / 8.12 | 4.60 / 7.08 |
| B7 | Archived practice problems quote p = 0.011, CI [4.12, 7.45] | p = 0.031, CI [4.18, 6.96] |

---

## C. Figure defects (report, do not silently fix — shared assets)

### C1. `fig_kd_qb_posterior.pdf` mislabels its contours
`bayesian_crosscheck.py:316` legends them "posterior 1-, 2-, 3-σ contours".
They are drawn at **5%, 32%, 68% of peak density** (`:266`), which for a 2-D
Gaussian is roughly 2.45σ, 1.51σ, 0.88σ — wrong values *and* reversed order.

**Not used in the thesis or the letter.** Contained. If the guidebook uses this
figure, describe the contours as iso-density fractions of peak, never as σ.

Also on the same figure: the star is the **median**, not the MAP, despite the
code comment; and the three dotted rays are Q_b = 1,2,3 × K_d reference lines for
a proportional degeneracy the project *disproved*. They must be explained as a
foil or they read as endorsement.

### C2. `fig_book_aicc.pdf` annotates a conclusion its own data contradicts
`make_book_figures.py` prints "M1 wins" while plotting `delta_aicc` where
M3 = 0.0 and M1 = 0.077. Leftover from a pre-recertification run. The figure is
not referenced by any current document.

### C3. `fig_aicc_anatomy.pdf` hardcodes rounded inputs
`make_more_explainers.py:190` uses `rmse_g/rmse_f` rounded to 2 dp rather than
reading `model_selection.json`. Its net values are +2.99 / −22.95 against the
JSON's +2.94 / −23.17. The thesis caption already hedges this as "within
rounding". Keep the hedge if the guidebook reuses the figure.

### C4. Two posterior figures are not regenerable by `make figures`
`fig_kd_qb_posterior.pdf` and `fig_posterior_compare.pdf` are written by
`bayesian_crosscheck.py` itself, not by a figure script. Rebuilding them requires
re-running the ~10 minute MCMC. `fig_posterior_compare.pdf` **is** used in the
thesis (`thesis.tex:2033`).

---

## D. Method facts worth teaching honestly (not defects, but gaps)

- **No interpolation-error quantification** for the 13 × 9 bilinear RMSE surface.
  The 68% Q_b credible interval spans only 1.2–1.6 grid cells, so the Q_b
  marginal shape is close to a bilinear artifact convolved with the prior.
- **No R-hat, no trace plots, no posterior-predictive check.** Autocorrelation
  time is the only diagnostic (τ ≈ 32–36, ESS ≈ 2700–2900). Acceptance rate is
  never recorded; measured ≈ 0.69 from the archived chains.
- **σ_data = 0.5 K is uncalibrated** and set near the *misfit* level rather than
  the *instrument* level (0.03–0.05 K). By construction this pins the best-fit
  reduced chi-square near 1 and prevents the likelihood from ever declaring the
  model wrong. The code docstring says so candidly; the guidebook should too.
- **A15 has essentially no posterior ridge**: corr(K_d, Q_b) = +0.08, versus
  −0.75 at A17. The claim that the ridge "tilts opposite ways at the two sites"
  is true of the *retrieval* map but not of the *posterior*. A15's likelihood is
  too weak to tilt it.
- **The prior-width scan moves the ordering probability upward**, 99.21% → 99.42%
  as the prior widens fourfold, because the two sites respond to a flux revision
  in opposite directions. At 40% width the A17 effective sample size collapses
  from 96 000 to 21 256.
- **No tests** cover `conductivity_3layer`, the AICc functions, or
  `model_selection.json`.
