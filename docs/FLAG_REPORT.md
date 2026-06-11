# Flag Report — physics, code, and figure audit

> **Status update (second pass, 2026-06-11):** F2 resolved by rewriting
> §1/§2.2 to describe the implemented idealized forcing with bounded
> neglected terms (tracked changes). F3 resolved: figure script fixed
> (radiative term, consistent ρc_p) and regenerated; text/caption now
> describe the √2σ proxy. F4 largely resolved: `compute_error_budget.py`
> fixed (z_b ∈ {70,80,90}, ±0.02 albedo), JSON regenerated, Table 4 and
> all dependent prose updated to the reproducible values (totals
> 1.73/5.81) — remaining: commit the χ/H/Ks/ρ generating sweeps. Stale
> numbers in F5/F6 (grids, H range, thresholds, 55–80 %, kd-sweep
> caption) corrected in tracked changes. **F1 remains OPEN and blocks
> submission**; the Diviner-closure stub, Bayesian outputs, and missing
> appendix (F5) also remain open.

Audit of the Lunar-HFE repository against the manuscript
(`paper/letter/letter.tex`), performed 2026-06-11. Every flag below was
verified by reading the released code and, where marked **measured**, by
re-running the released pipeline. Matching `\note{}` comments are embedded
at the relevant locations in `letter.tex`.

Status summary: the **statistical machinery is sound and the committed
JSON results match the manuscript's headline numbers**, but there are
**two critical physics/implementation flags (F1, F2)** and several
reproducibility gaps that must be resolved before submission.

---

## F1 — CRITICAL: spin-up does not converge; hard-coded per-site initial anchor controls the retrieval

`scripts/pipeline/retrieve_kd.py` initialises every solver run at
`T(z) = T_MEAN_EFF + Q_b * cumsum(dz / K)` with hard-coded, uncited
anchors `T_MEAN_EFF = 250.0` (A15) and `255.0` (A17), then spins up for
30 lunations to a 5e-2 K/cycle tolerance. With a 5-m column under a flux
bottom boundary, the deep relaxation time is ~10^3 lunations, so the
sensor-depth (0.8–2.4 m) mean temperatures retain strong memory of the
anchor.

**Measured with the released code:**

| Experiment (A15, production settings) | Result |
|---|---|
| Anchor 245 K → ⟨T⟩(0.8 m / 1.4 m) | 249.25 / 249.35 K |
| Anchor 250 K (production) | 252.12 / 253.42 K |
| Anchor 255 K | 255.61 / 257.89 K |
| 400 lunations, tol 1e-4, anchors 245 vs 255 | still differ by 1.6–2.6 K |
| **End-to-end Kd\* at anchor 245 / 250 / 255 K** | **1.75 / 4.86 / 11.00 mW m⁻¹ K⁻¹** |

A ±5 K perturbation of the anchor swings the retrieved Kd\* by a factor
of ~6 — larger than the headline inter-site contrast — and the two sites
are assigned *different* anchors (250 vs 255 K). As released, T_MEAN_EFF
acts as an undeclared per-site free parameter. This also invalidates the
k=1 AICc accounting and the bootstrap CIs as stated.

The manuscript's claim that tightening to 60 lunations / 5e-3 K shifts
Kd\* by <0.1 mW m⁻¹ K⁻¹ is not reproducible from the released code and is
inconsistent with the measured relaxation timescale.

**Required fix:** run to a demonstrated periodic steady state
(shorter column, warm-started sweeps, or an analytically anchored deep
mean derived from the converged diurnal-mean surface temperature), then
show Kd\* is anchor-independent; or derive T_MEAN_EFF self-consistently
and document it. Re-run the entire pipeline afterwards.

## F2 — MAJOR: manuscript describes SPICE/DE440 forcing; pipeline uses idealized cosine insolation

Manuscript §1 and §2.2 state each Apollo timestamp is propagated through
SPICE (DE440, light-time + aberration), "eliminating the ~1 lunar-hour
drift inherent in sinusoidal local-solar-time approximations." The
released retrieval (`retrieve_kd.py::run_with`) forces the solver with
`S0 * cos(lat) * max(0, cos(2π t / P))` over one synodic lunation — no
SPICE call, no solar declination (±1.5°), no eccentricity (±3.3 % flux),
no site longitude. `lunar/ephem.py` (a correct SPICE implementation)
exists but is never invoked by the Kd pipeline.

**Fix:** wire the ephemeris chain into the pipeline and re-run, or
rewrite the methods text to describe the idealized forcing and bound the
neglected terms.

## F3 — MAJOR: amplitude figure does not implement the stated method

`make_letter_figures.py::fig_amplitude_vs_depth` plots √2 × the
within-stability-window standard deviation as "diurnal amplitude" (the
code comment admits the approximation), while the caption/methods claim
the half-range of the SPICE LST-folded median. Additionally its Hayne
attenuation curve uses K = 3.4e-3 *without* the radiative multiplier
(≈2.0× at 250 K) and a hard-coded ρc_p = 1500 × 850 that matches neither
the caption (ρ = 1800) nor the model c_p(250 K) ≈ 670 J kg⁻¹ K⁻¹. The
plotted model curves differ by ~50 % in skin depth, not the "~10 %"
claimed. The qualitative borestem conclusion survives.

## F4 — MAJOR: error-budget table (manuscript Table 4) is not reproducible from the archive

`output/kd_error_budget.json` vs the manuscript: σ_Qb 1.27/3.00 vs
1.47/3.45; σ_A 0.56/0.95 (±0.04 albedo sweep) vs 0.07/0.54 (stated
±0.01); σ_χ 0.73/1.73 vs 0.69/2.03; σ_zb at A17 3.81 vs <0.05 (the
script includes the 60-cm outlier the text excludes); σ_ρ 0.02/0.06 vs
"identically zero by structure"; totals 1.80/7.01 vs 1.86/6.17. The
σ_χ/σ_H/σ_Ks/σ_ρ values are hard-coded constants in
`compute_error_budget.py` with no generating sweep committed, while the
table claims re-retrievals.

## F5 — Reproducibility gaps (must fix before the Open Research statement is true)

- **Diviner closure (Fig. 9, §3.3 numbers):** the notebook cell in
  `03_results.ipynb` is a stub that defers to "the Lunar-V2 dev repo"
  and carries placeholder parameters (negative latitudes, albedo/emissivity
  contradicting Table 1, and `growth=1.05` passed to an API that expects a
  fractional growth — i.e. 2.05× per layer). No closure JSON is committed.
- **Bayesian cross-check (§3.3):** `bayesian_crosscheck.py` exists but its
  output JSON and posterior figures are not committed; the quoted medians
  (3.9/13.1, contrast +9.2, P≈96 %) are unverifiable.
- **Appendix:** the letter header references companion `appendix.tex`;
  no appendix source exists in the repo (only `fig_holdout.pdf`).
- **Stale methods text:** sweep grids (paper: 20 pts 1.5–9.0 / 24 pts
  3.0–18.0; code: 28 pts 1.0–15.0 / 30 pts 3.0–25.0 — the extrapolation
  caveat no longer applies); joint H sweep (paper: 1–11 cm, 11×8; code:
  3–10 cm, 8×8); threshold-sensitivity numbers (paper 0.03/0.11; JSON
  0.02/0.07).

## F6 — Minor

- `find_stable_window` never evaluates candidate start fractions >80 %
  (min-tail guard), so the stated "55–85 %" is effectively 55–80 %.
- `fig_kd_sweep` caption said "shaded band: 95 % CI"; the figure draws
  horizontal error bars (caption fixed in tracked changes).
- Headline Kd\* is grid-dependent at the 0.03 mW level
  (`headline_rmse.json` 4.885 vs `kd_retrieval_results.json` 4.860, two
  different sweep grids) — consistent with the stated robustness, but
  quote one source.
- `make_results_figures.py::fig_kd_sweep_v2` is dead code with a
  hard-coded stale x-grid; safe only because unused — consider deleting.
- Working tree at clone time contained a single-character corruption in
  `paper/letter/letter.tex` (`amssymb}` → `amssymb)`); superseded by the
  new draft.

## What checks out (verified clean)

- Crank–Nicolson assembly, harmonic-mean face conductivities, Newton
  surface balance (residual and analytic derivative), geothermal-flux
  Neumann bottom BC: all mathematically correct.
- Geometric grid (Δz₀ = 2 mm, ratio 1.08, z_max = 5 m) matches the paper.
- Hayne (2017) K(T,z), ρ(z), c_p(T) and Martínez & Siegler (2021)
  K(T,ρ) coefficients verified against cited sources (incl. the B1
  missing-zero correction, documented).
- All committed headline numbers match the manuscript: RMSE table,
  Kd\* point estimates and bootstrap CIs, contrast (6.63, CI [−3.2, 16.6],
  p = 0.05), borestem-cut sweep (incl. the 60-cm outlier values),
  model-selection table (M1/M2/M3 RMSE and ΔAICc), α-retrieval
  (1.12/2010 and 1.83/3300), hold-out diagnostics (LOO 0.31/0.16 K).
- Test suite: 35/35 pass.
- Bib: every cited key resolves; letter compiles cleanly.
