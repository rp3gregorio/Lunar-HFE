# Fresh guidebook — proposed structure

**Edit this file freely. Anything you change here I implement.**

---

## Why the current document reads as disorganised

Four structural faults, in order of damage:

1. **Statistics comes after the result.** The reader meets
   `4.60 [4.18, 6.96], p = 0.031, marginal` in Ch 6, then learns what a
   bootstrap and a CI are in Ch 7. The answer is presented before the tools
   needed to read it.
2. **The physics sits in Appendix B, at the very end.** Fourier's law, the heat
   equation, the skin depth and the boundary conditions all come after the
   solver that uses them. A reader with no background meets the Crank-Nicolson
   stencil on page 20 having never been told what a heat equation is. For a
   document whose stated job is to teach from zero, this is the worst fault.
3. **Ch 4 re-explains Ch 3.** "How the slope method differs from brute force"
   restates a contrast already made twice.
4. **The K_d-Q_b degeneracy is told four separate times** (lines 1699, 2015,
   2274, 2318). That repetition is why the book reads as circling.

Root cause: **Ch 2 "The pipeline" does three jobs at once** - data reduction,
the physics and models, and the numerical solver - which pushes everything else
out of position.

The five-part spine below fixes all four: nothing is used before it is taught,
statistics precedes the result, physics precedes the solver, the brute-force
contrast folds into one section, and the degeneracy is told once.

---

Built from the ground up. Nothing carried forward from the old guidebook without
re-deriving its numbers. Every thesis section has a home here. Existing figures
are used as-is and never modified; new diagrams are TikZ only.

Target: ~140 pp. Reading time about 7 hours, or dip-in by chapter.

---

## What changed versus the old book

| | Old (76 pp) | Fresh |
|---|---|---|
| Coverage | pipeline, slope method, brute-force contrast | everything in the thesis |
| AICc | absent | own chapter, from zero |
| MCMC | one thin section | own chapter, from zero |
| Martínez & Siegler | absent | full study explained |
| Three-layer model | absent | own section |
| Spin-up | justified but not explained | mechanism, loop by loop |
| Grid / layering | one appendix section | own chapter |
| dt choice | asserted | ladder, wrap-step bug, stability vs accuracy |
| Figures used | 29 of 57 | ~50 of 57, all existing |
| Practice problems | none | every chapter (revived from the archive) |

---

## Front matter
Title · abstract · contents · list of figures · list of tables ·
**Notation** (thesis-style two-table layout, same macros)

## Part I — The problem and the data

**Ch 1 · What this study does and why**
1.1 One Moon-wide number that was never checked ·
1.2 Why subsurface temperature matters (ice, TSUKIMI, radiative-transfer retrievals) ·
1.3 The only two boreholes ever drilled ·
1.4 What we retrieve and what we hold fixed ·
1.5 The shape of the whole argument
`fig_intro_probe` `fig_context_globes` `fig_context_map` `fig_tsukimi_chain`

**Ch 2 · The Apollo Heat Flow Experiment dataset**
2.1 Instrument design and measurement geometry (TG/TR bridges, the borestem) ·
2.2 The 1971–77 record and its disturbances ·
2.3 From a multi-year record to one number: the stability window ·
2.4 The meter-scale sensor cut, and why z ≥ 80 cm ·
2.5 The equilibrium profiles ·
2.6 The basal heat flux, and where 21 and 16 come from
`fig_probe_geometry` `fig_apollo_timeline_probes` `fig_apollo_timeline_a15/a17`
`fig_window_anatomy` `fig_apollo_mean_T_profile`

## Part II — The physics and the models

**Ch 3 · The physics, from the ground up**
3.1 Fourier's law in words, then in symbols · 3.2 The heat equation as conservation
in a column · 3.3 The lunar forcing · 3.4 The skin depth, derived ·
3.5 Boundary conditions at both ends · 3.6 Periodic steady state
`fig_book_skinwave` `fig_amplitude_vs_depth` `fig_boundary_conditions`

**Ch 4 · The three conductivity models**
4.1 Hayne (2017): depth-based, and where χ = 2.7 actually comes from ·
4.2 **Martínez & Siegler (2021): the density-based model** — the study explained
from scratch, its lab data, every coefficient, its limits of validity, and what
depending on density rather than depth changes physically ·
4.3 **The three-layer piecewise model** — form, parameters, why it is in the
comparison · 4.4 What each model lets you tune, and why that matters for retrieval
`fig_book_kTz` `fig_alpha_sweep`

## Part III — The solver, line by line *(the implementer's view)*

**Ch 5 · Discretisation: the grid and the layering**
5.1 Why geometric and not uniform · 5.2 Where the cells actually land (real numbers,
first ten and last five) · 5.3 Finite-volume control cells · 5.4 Harmonic-mean face
conductivity, and what an arithmetic mean would break · 5.5 The boundary rows
`fig_numerics_grid_matrix`

**Ch 6 · One time step, one lunation**
6.1 Crank–Nicolson · 6.2 Assembling the tridiagonal system · 6.3 The Thomas
algorithm · 6.4 Newton at the surface · 6.5 One Crank–Nicolson hour, worked by hand ·
6.6 **Choosing Δt** — the ladder, the wrap-step bug, and why unconditional stability
does not mean any step is safe
`fig_newton_surface` `fig_dt_ladder`

**Ch 7 · Reaching steady state**
7.1 Two timescales · 7.2 Brute force and its cost · 7.3 The F1 bug ·
7.4 The insight: cycle-mean flux is depth-independent · 7.5 The closure ODE ·
7.6 u_rect, why it exists and why it vanishes below the skin ·
7.7 **Step A: skin-only integration and the truncated sub-grid** ·
7.8 Step B: the RK2 walk down · 7.9 The outer loop as a fixed point ·
7.10 **The inner loop: what n_inner counts, why 96, why Apollo 15 sets it** ·
7.11 Why two anchor stages · 7.12 Certification, three checks ·
7.13 The measured speed-up (21× algorithmic, 2465× compiled)
`fig_book_f1_bug` `fig_urect_explainer` `fig_anchor_anatomy` `fig_anchor_placement`
`fig_anchor_convergence` `fig_method_fluxanchored` `fig_speedup_factors`
`spinup_filmstrip` `reconstruct_filmstrip` `old_vs_new_filmstrip`

## Part IV — Retrieval and uncertainty

**Ch 8 · Retrieving K_d**
8.1 The objective function · 8.2 The sweep and its non-uniform grid ·
8.3 Parabolic vertex refinement · 8.4 A full sweep, worked
`fig_kd_sweep` `fig_sweep_worked` `fig_retrieval_demo`

**Ch 9 · The statistics, from zero**
9.1 One number from many misses: RMSE · 9.2 From a curve to one value ·
9.3 The bootstrap · 9.4 The confidence interval · 9.5 The contrast and its p-value ·
9.6 What "marginal" means and why we say it · 9.7 **The systematic error budget** ·
9.8 Adding errors that do not know about each other
`fig_bootstrap` `fig_bootstrap_draw` `fig_stats_bootstrap` `fig_stats_contrast`

**Ch 10 · Model selection: AICc from zero** *(entirely new)*
10.1 Why we cannot just minimise RMSE · 10.2 What a likelihood is ·
10.3 From RSS to log-likelihood under Gaussian errors · 10.4 What k actually counts ·
10.5 The small-sample correction, and why it bites at n = 7 ·
10.6 Reading ΔAICc, and the sign convention (fit − global) ·
10.7 **The honest result: Apollo 17 says yes (−23.2), Apollo 15 says no (+2.9)** ·
10.8 Why the three-layer model loses at both sites
`fig_aicc_anatomy`

**Ch 11 · The Bayesian cross-check: MCMC from zero** *(entirely new)*
11.1 Why a second road to the same answer · 11.2 The prior on Q_b, and its
justification · 11.3 The likelihood and the noise model · 11.4 The precomputed
solve surface and how it is interpolated · 11.5 The sampler and its proposal ·
11.6 Chains, burn-in, thinning, and convergence diagnostics ·
11.7 **How to read the posterior map** · 11.8 The K_d–Q_b degeneracy, measured ·
11.9 The prior-width scan
`fig_kd_qb_posterior` `fig_qb_degeneracy` `fig_posterior_compare`

## Part V — Results and meaning

**Ch 12 · The result and its robustness**
12.1 The headline numbers · 12.2 The largest caveat: conditionality on χ ·
12.3 Internal validation by holdout · 12.4 Common-epoch sensitivity ·
12.5 Diviner surface-temperature closure · 12.6 The independent global model
(α sweep) · 12.7 Comparison with prior estimates · 12.8 Robustness of the contrast
`fig_headline` `fig_holdout` `fig_epoch_map` `fig_diviner_closure`
`fig_prior_estimates` `fig_robustness` `fig_thermal_profiles`

**Ch 13 · What it means**
13.1 Two admissible interpretations · 13.2 Physical plausibility of the contrast ·
13.3 Caveats and limitations · 13.4 Implications for subsurface sounding ·
13.5 Conclusions
`fig_contrast_mechanisms` `fig_baselayer`

## Appendices
**A** Where every input comes from: the register, and the three that bit us
(`fig_audit_waterfall`) ·
**B** Derivations (heat equation, Hayne term by term, skin depth, BCs, grid,
Crank–Nicolson, assembly, Thomas, Newton, closure, RK2, vertex, quadrature) ·
**C** Worked example: the anchor method end to end ·
**D** Reproducing the result ·
**E** Solutions to the practice problems

---

## Three findings that shaped this outline

1. **The old AICc section describes a model set the project no longer uses.**
   It compares M1/M2/M3 (shared-K_d, free-Q_b variants) and claims ΔAICc = 3.99.
   The actual analysis compares hayne_global / hayne_fit / layer3_fit, and the
   result is ΔAICc = −23.2 at A17 but **+2.9 at A15**. Structurally dead, not
   just numerically stale.

2. **Your own model selection does not justify fitting Apollo 15 separately.**
   With 7 sensors the parameter is not paid for. This is a question the panel can
   ask, and Ch 10.7 answers it head on rather than hiding it.

3. **28 of your 57 figures are unused.** The fresh book can be richly illustrated
   using only existing frozen figures, with no new matplotlib work at all.

---

## Edit notes
<!-- Write your changes below. Anything here I implement. -->

-
-
-
