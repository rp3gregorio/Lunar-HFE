# Solver and spin-up facts for the fresh guidebook (2026-07-27)

Implementation-level material gathered for Part III. Everything here is measured
from the code or the committed artifacts, not inferred.

---

## The teaching points that matter most

### 1. Flux closure alone does not certify convergence
The single best pedagogical fact found in this pass.

At Apollo 15, `n_inner = 1` gives a flux-closure residual of **0.2355%**.
`n_inner = 96` gives **0.2356%**. Statistically identical. Yet the `n_inner = 1`
profile is **0.09 K wrong** through the entire sensor band.

Closure certifies **Step B** (the reconstruction), not **Step A** (the skin).
This is exactly why the convergence criterion had to move to K_d* plateau
stability rather than "the closure is small". Give it its own section.

### 2. The closure "floor" is a diagnostic artifact, not physics
The reported ~0.12% floor is an `np.gradient` one-sided-stencil error at the
**bottom cell**, not a residual of the solution. Drop the last cell and it
collapses:

| Site | closure, all cells | drop last cell |
|---|---|---|
| A15 | 0.2356% | **0.0007%** |
| A17 | 0.1162% | 0.0537% |

It halves as the bottom cell halves (first order in `dz[-1]`), confirming the
mechanism. `_reconstruct_subskin` builds the profile with a forward RK2 step;
`_mean_flux_closure` differentiates it with `np.gradient`. The two disagree by
O(dz) at the boundary. Do not present the floor as a physical limit.

### 3. Step B fixes the shape; only the offset depends on spin-up
Below the anchor, the n=1, n=12 and n=96 mean profiles are **parallel offsets**
of one another: they differ by 0.091 K at 0.55 m and 0.086 K at 4.85 m, a drift
of 5 mK over 4.3 m. The deep shape comes from the closure ODE regardless of
spin-up; only the anchor value moves. That is why K_d* is a pure function of the
anchor, and why the tolerance is a **temperature** tolerance.

### 4. The two sites converge from opposite directions
A17 approaches from above (7.45 → 7.08 mW), A15 from below (4.550 → 4.602).
A15 is still creeping at n=96 (+0.005 mW over the last doubling), which is
exactly the stability criterion, and why the slower site sets `n_inner`.

### 5. The wrap-step bug is the strongest numerical validation in the project
The buggy ladder was cleanly first order (differences −0.302 / −0.146 mW,
ratio 2.07). Its Richardson extrapolation is 2 × 7.251 − 7.397 = **7.104 mW**.
The wrap-fixed ladder at dt = 450 gives **7.1045 mW**. Two independent
discretisations agreeing on the continuum limit to four digits.

Effect at production dt: A17 **7.699 → 7.0795 mW (−0.62)**; A15 nearly immune
(+0.010). A depth-uniform offset of under 0.1 K became a 0.62 mW bias because
A17 is absolute-T dominated while A15 is gradient-dominated.

---

## Numbers the guidebook needs

### Grid (production `GRID`: z_max 5.0, dz0 2 mm, growth 8%)
- **69 cells.** The grid **overshoots**: `z_face[-1] = 5.0353 m`, not 5.0, because
  the loop condition is `while faces[-1] < z_max`.
- Anchor cell: **index 40**, `z_mid = 0.539838 m`, `dz = 4.345 cm`. The anchor is
  snapped to a cell centre, so **0.55 m is never actually used** (10.2 mm high).
- Last cell: `dz = 37.48 cm`, centred at 4.848 m.
- 14 cell centres inside the 5 cm skin depth; 16 within H = 6 cm; 45 above 80 cm.
- Uniform 2 mm to 5 m would need **2500 cells** versus 69, a 36x saving since
  Thomas is O(N).
- Spatial convergence: refining to dz0 = 1 mm, growth 6% moves sensor-band
  temperatures by **0.19 mK**. The grid contributes essentially nothing to K_d*.

### Time step
- `DT_STEP = 1800` is a **target**. Realized `dt = 1800.5948 s` (n = 1417 steps,
  n·dt = one lunation exactly).
- dt ladder criterion is |ΔK_d*| < 0.05 mW **per halving**, measured on the
  published quantity, not on a temperature.
- Certified: A17 7.0795 / 7.0975 / 7.1045 at dt = 1800 / 900 / 450 (spread
  0.025 mW, 0.35%). A15 spread 0.0017 mW (0.037%).

### Thomas
- Exactly **8n − 7 flops**. For n = 69 that is **545**, against ~109 000 for dense
  Gaussian elimination.
- Called ~4251 times per lunation (1417 steps x 3 Picard sweeps).

### Newton at the surface
- Analytic scalar Jacobian `dR/dT_s = −4εσT_s³ − 2K_surf/dz_surf`, strictly
  negative, so the root is unique and Newton converges from any positive start.
- Measured over 8503 production calls: **min 1, median 2, mean 2.50, max 6**
  iterations. Zero calls hit the 40-iteration cap.
- Tolerance 1e-4 K, applied to the **step size**, not the residual.

### Spin-up structure
- **Three** nested loops, not two: the two-stage schedule, the outer anchor
  fixed-point, and the inner spin-up lunations.
- Stage 1: anchor 0.25 m, 4 inner lunations, tol 100 mK. Stage 2: anchor 0.55 m,
  96 inner lunations, tol 5 mK.
- Why two stages, measured `u_rect/Q_b`:

| depth | A15 | A17 |
|---|---|---|
| 0.2576 m (stage-1 anchor) | −12.3% | **−70.7%** |
| 0.5398 m (stage-2 anchor) | −0.009% | −0.198% |

  Stage 1 sits inside the rectification zone; stage 2 sits below it. That is the
  whole justification and it is verifiable from the code.
- Step A sub-grid: **44 of 69 cells**, base at 0.7139 m. Cells 41, 42, 43 are
  time-stepped and then **thrown away**, overwritten by Step B. The 0.15 m margin
  exists only so the anchor is not the sub-grid's boundary cell.
- `n_inner = 96` = 7.76 simulated years per Step-A solve, at 2.81 ms per lunation
  on the compiled kernel.
- Measured cost: A15 `n_outer = 4` = 2x4 + 2x96 = **200** sub-grid lunations
  (not 384; the stage-1 iterations are cheap). Full solve 0.59 s.

---

## Traps a reader would fall into

| # | Trap |
|---|---|
| a | **`spinup_tol_K = 0.0` is load-bearing.** `delta < 0.0` can never fire, so every Step-A solve runs the full `n_inner`. "Fixing" it to a small positive value silently invalidates the whole convergence study. |
| b | **`eq.T_mean` is NOT `eq.out.T.mean(axis=1)`.** `T_mean` is the ODE reconstruction; `out` is a separate 3-lunation run. They differ by up to **0.251 K**. Computing the mean from `out` gives a wrong deep profile. |
| c | **The anchor is snapped to a cell centre** (0.5398 m, not 0.55). If the grid changes, the effective anchor moves. |
| d | **Off-by-one at the stage transition.** The `break` fires before `T_init = T_recon`, so the last reconstruction of a stage is computed, recorded in `history`, and discarded. |
| e | **`T_guess` is not the initial surface temperature.** `np.cumsum` is inclusive of element 0, so `T_init[0] = T_guess + Q_b·dz[0]/K0[0]`. The seed is a geothermal-gradient column, not an isotherm. |
| f | **`hayne_params` silently overrides `K_func` in Step A only.** Step B still uses the Python `K_func`. Inconsistent arguments give a solve whose two halves use different physics, with no error raised. Non-Hayne models must pass `hayne_params=None`. |
| g | **`drift` leaks across stages.** Initialised once outside the stage loop, so iteration 1 of every stage records `inf` and can never break. Minimum 2 iterations per stage. |
| h | **The tests do not exercise production config.** Every test passes `n_inner=12` explicitly for speed. Do not cite test tolerances as production certification. |

---

## Stale values found in the code and docs

| Location | Says | Actually |
|---|---|---|
| `config.py:89` | "96 puts both on the plateau (~13 s/solve)" | **0.64 s** compiled; 74.7 s generic |
| `compute_error_budget.py:129` | `EQ_N_INNER = 90` | **96** |
| `equilibrium.py:48` | "converges in 3–5 outer iterations" | 4 (A15), **6** (A17) |
| `equilibrium.py:52` | guess independence "< 0.03 K" | 5 µK (A15), 6 nK (A17) |
| `equilibrium.py` `_rectified_flux` docstring | u_rect "a few percent of Q_b" at the anchor | 0.009% / 0.198%. "A few percent" describes the **stage-1** anchor. |
| `guidebook.tex`, `thesis.tex` | explicit-Euler floor "200 s" | **525–937 s** with the code's actual kappa |
| `solver.py:340` | `_step` annotated `-> np.ndarray` | returns a 2-tuple |

---

## Latent gaps worth stating honestly

- **`_solve_surface_newton` fails silently.** On non-convergence it returns a
  best-effort value, sets no flag, raises nothing. The trailing comment says
  "caller can flag diagnostics"; no caller does. Latent only because the measured
  maximum is 6 of 40 iterations.
- **The compiled Newton twin has no input validation**, unlike the generic path,
  so the fast path silently accepts inputs the slow path rejects.
- **No test covers** the harmonic mean, the basal Neumann row, or the wrap step in
  isolation.
- **The harmonic-vs-arithmetic difference is smaller than the prose implies.**
  Measured maximum on the production grid is **+0.56%**, at the very top face,
  decaying to zero by ~25 cm, because the largest cell-to-cell conductivity ratio
  is only 1.161. The physics argument is right; there is no artifact in the repo
  measuring its effect on K_d*, so do not quote a number for that.
- **`PixelInputs.Q_b` defaults to the south-polar 0.012 W/m².** A caller who
  forgets to pass `Q_b` gets a silently wrong flux.
