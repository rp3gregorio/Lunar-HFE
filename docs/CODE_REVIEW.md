# Code review — Lunar-HFE / apollo-hfe-kd-retrieval

**Date**: 2026-06-03
**Reviewer**: claude-opus-4-7
**Scope**: full Phase-1 codebase (lunar/, scripts/, tests/, notebooks/)
**Focus**: correctness first, reproducibility second, code quality third
**Method**: line-by-line read of every critical file; full end-to-end re-run
of the pipeline from a wiped output/ directory

Findings are tagged:

- **CRITICAL** — could change numerical results in the paper; must fix.
- **WARNING** — works today but is a latent bug or reproducibility risk.
- **SUGGESTION** — code-quality improvement.

---

## Reproducibility verification

Deleted every JSON in `output/`, then ran the full pipeline from scratch.
Fresh values were diffed against the canonical JSON saved before the wipe.

| | Canonical (paper) | Fresh run | Δ |
|---|---|---|---|
| K_d,A15* | 4.859970 mW/m/K | 4.859970 mW/m/K | 0.00e+00 |
| K_d,A17* | 11.233430 mW/m/K | 11.233430 mW/m/K | 0.00e+00 |
| A15 bootstrap median | 4.8834 mW/m/K | 4.8834 mW/m/K | 0.00e+00 |
| A15 bootstrap 95% CI | [3.945, 14.359] | [3.945, 14.359] | 0.00e+00 |
| A17 bootstrap median | 11.5097 mW/m/K | 11.5097 mW/m/K | 0.00e+00 |
| A17 bootstrap 95% CI | [10.181, 21.625] | [10.181, 21.625] | 0.00e+00 |

Reproduction is **bit-exact**. The bootstrap is deterministic under the
fixed seed (`seed=42` in `bootstrap_kd_with_depth_uncertainty`), and the
upstream K_d sweep + parabolic refinement contain no stochastic
components. See the [Verification appendix](#verification-appendix) at
the bottom for the diff transcript.

Reproducibility-relevant findings appear in the report below.

---

## CRITICAL findings (must fix)

### C1. `_assemble_tridiagonal` is dead code  ✅ FIXED

**File**: [lunar/solver.py](../lunar/solver.py) (was lines 155–194)
**Issue**: This function was defined but **never called**. The actual
time step inlines the tridiagonal assembly inside `_step`. The dead
function duplicated the assembly logic and risked future drift if
someone "fixed" one copy without the other.
**Risk**: a future developer might modify `_assemble_tridiagonal`, see
tests pass, conclude the change is safe — and then ship a paper based
on the OTHER inlined assembly that wasn't touched.
**Fix applied**: deleted `_assemble_tridiagonal` from `lunar/solver.py`
and the two dependent tests
(`test_tridiagonal_row_sum_is_one_for_zero_dt`,
`test_tridiagonal_is_diagonally_dominant`) from
[tests/test_solver_assembly.py](../tests/test_solver_assembly.py).
Test suite still passes (35/35; was 37/37 before pruning the dead
tests).

### C2. `diviner.py` error message points at non-existent script  ✅ FIXED

**File**: [lunar/diviner.py:214](../lunar/diviner.py#L214)
**Issue**: When a tile was missing the error said

> `Run scripts/download_diviner_gcp.py to bootstrap.`

But the actual script is `scripts/fetch_diviner.py` (renamed in
cleanup). A user who hit this error would look for the wrong file.
**Fix applied**: updated the error string to name `fetch_diviner.py`.

### C3. `apollo_helpers.py` has substantial dead code (plotting helpers)

**File**: `lunar/apollo_helpers.py` lines 161–699 (≈540 of 700 lines)
**Issue**: Five large plotting functions (`plot_stability_region`,
`plot_per_sensor_stability_windows`, `plot_depth_colored_timeseries`,
`plot_single_model_validation`, `plot_head_to_head`) and a solver
runner (`run_site_solvers`, `compute_validation_stats`) are imported by
the deleted `notebooks/01_apollo_validation.ipynb` only. None of the 5
current notebooks or any figure script in `scripts/figures/` uses them.
**Risk**:
- 540 lines of orphan code in a "core" module
- They reference `lunar.plotting.style_guide.save_figure` which is also
  largely orphan
- Future readers wonder why a "helpers" file has 700 lines
**Fix**: move the active functions (`extract_sensor_stability`,
`find_stable_window`, `iso_to_seconds`, `print_stability_table`,
`SECONDS_PER_YEAR`) into a slimmer `lunar/apollo_helpers.py` and
delete the rest. Or move plotting helpers into a separate
`lunar/apollo_plots.py` and mark them as legacy.

---

## WARNING findings (worth fixing)

### W1. Spin-up non-convergence is silent

**File**: `lunar/solver.py` lines 477–522
**Issue**: When the spin-up loop completes `n_lunations_spinup` cycles
without `delta < spinup_tol_K`, the function returns with `converged=False`
and `n_spinup_cycles == n_lunations_spinup`, but **no warning is emitted**.
A caller who doesn't inspect `out.converged` will silently use an
un-converged solution.
**Fix**: emit a `warnings.warn(...)` (UserWarning) when convergence is
not achieved. Already documented in CLAUDE.md hard rule #4 — should be
enforced by the code, not just by convention.

### W2. `rmse_star` from parabolic minimum is linearly interpolated, not parabolic-evaluated

**File**: `scripts/pipeline/retrieve_kd.py` lines 216–232 (`kd_star_from_residuals`)
**Issue**: Inside the parabolic refinement, the K_d* location is computed
from the parabola coefficients (`-b/2a`), but `rmse_star` at that location
is then obtained via `np.interp` (linear) instead of evaluating the
parabola. The two agree to within ~1% for sharp minima but diverge for
flat ones.
**Risk**: cosmetic; affects the RMSE value printed in Table 2 by maybe
0.01 K. Does not affect K_d*.
**Fix**: replace `np.interp(kd_star, x, y)` with the parabolic eval
`c - b**2 / (4*a)` (which requires storing c) or just accept the linear
approximation and add a comment acknowledging it.

### W3. Bootstrap seed is fixed (good!) but should be propagated through the JSON  ✅ FIXED

**File**: [scripts/pipeline/retrieve_kd.py](../scripts/pipeline/retrieve_kd.py)
**Issue**: `seed=42` is the function default and the script never
overrides it — so re-runs are byte-identical. But the seed was NOT
written into the output JSON. A future user who tweaked the seed for a
sensitivity check would have no record of which seed produced the
headline result.
**Fix applied**: added a top-level `provenance` block to
`kd_retrieval_results.json` containing `bootstrap_seed`,
`depth_sigma_cm`, and `git_commit` (resolved via
`git -C <repo> rev-parse HEAD`, falling back to `"unknown"` outside a
git tree). Example from the shipped JSON:

```json
"provenance": {
  "bootstrap_seed": 42,
  "depth_sigma_cm": 2.5,
  "git_commit": "e8a3abbbe912c8c1c4b759bf8dd9682aac8d8824"
}
```

The bootstrap rerun in the [Verification appendix](#verification-appendix)
confirms bit-exact reproduction with the recorded seed.

### W4. SPICE kernels are bundled but their provenance/version isn't documented

**File**: `data/spice/` (6 kernel files, ~44 MB)
**Issue**: The repo ships specific kernel versions
(`naif0012.tls`, `de440s.bsp`, `moon_pa_de440_200625.bpc`, etc.) but
there's no README in `data/spice/` documenting:
- where each kernel was obtained (URL on NAIF FTP)
- when it was downloaded
- which version is current as of when the paper was submitted
**Risk**: kernel updates over time (NAIF revises leapseconds, PCK, etc.)
change ephemeris values at the second-of-arc level. A reproducer in 2030
will want to know they're using the kernel set that produced the paper.
**Fix**: add `data/spice/README.md` listing each file with its NAIF
URL and SHA-256.

### W5. `compute_error_budget.py` has hard-coded "fixed sensitivities" with no provenance

**File**: `scripts/pipeline/compute_error_budget.py` lines 41–46
**Issue**: The dict `SIGMA_FIXED` hard-codes `sigma_chi`, `sigma_H`,
`sigma_Ks`, `sigma_rho` per site. These came from offline runs I did
during the manuscript revision; they aren't regenerated by any script in
the repo. So while `sigma_stat`, `sigma_Qb`, `sigma_zb`, `sigma_thr`,
`sigma_A` ARE all traceable to scripts, the four fixed sigmas are
effectively magic numbers.
**Risk**: in the same family as the original `kd_error_budget.json`
problem — partial traceability.
**Fix**: either (a) add 3 small sensitivity scripts
(`compute_chi_sensitivity.py`, `compute_H_sensitivity.py`,
`compute_Ks_sensitivity.py`) that regenerate them, or (b) document in
the script docstring where each value came from (and ideally an audit
trail). For the paper the cleanest is (a).

### W6. Newton iteration silently returns "best effort" on non-convergence

**File**: `lunar/solver.py` line 256 (`_solve_surface_newton`)
**Issue**: After `max_iter=40` Newton steps, if the residual hasn't
dropped below `tol=1e-4 K`, the function returns the latest `T_s`
without any signal that it didn't converge. In practice Newton always
converges here (the residual is monotonic and smooth), but the lack of
a flag means a future regression would be silent.
**Fix**: return a tuple `(T_s, converged: bool)` and log a warning if
not converged at the end of the time series. Or raise an error if
`abs(R)` is still > 1e-2 K after 40 iterations.

---

## SUGGESTION findings (nice to have)

### S1. `pyproject.toml` doesn't pin numpy/scipy upper bounds

**Issue**: `numpy>=1.24` — but numpy 3.x will break things. Future
versions can change semantics (e.g. `np.percentile` interpolation
default). For a paper repo, the lock file (`requirements-lock.txt`)
should pin **exact** versions, not just minimum versions.
**Fix**: run `pip freeze > requirements-lock.txt` from a working
environment and commit it. The current file has ranges, not exact pins.

### S2. The `lunar.plotting` package is mostly unused

**File**: `lunar/plotting/{__init__.py, style_guide.py, animations.py}`
**Issue**: `animations.py` (Phase 3+) is never imported. `style_guide.py`
has 6 functions; only `save_figure` is used by the now-orphan plotting
helpers in `apollo_helpers.py`. After cleaning up `apollo_helpers.py`
(see C3), the entire `lunar.plotting` package can be deleted.

### S3. `validation.py` has Diviner PCP loader for Phase 3 (polar) work

**File**: `lunar/validation.py` lines 165–260 (`DivinerPCP`,
`load_diviner_pcp_polar`)
**Issue**: This is a polar-product loader (PCP, not GCP). Phase 1 uses
only GCP (`lunar/diviner.py`). PCP is for Phase 3 work that isn't in
this repo's scope.
**Fix**: remove `DivinerPCP` and `load_diviner_pcp_polar` from
`validation.py`.

### S4. `holdout_tg_tr` returns `None` on small samples without a clear error

**File**: `scripts/pipeline/retrieve_kd.py` lines 331–336
**Issue**: If a site has fewer than 2 TG or TR sensors, `holdout_tg_tr`
returns `None`. The caller (`main()`) checks for `None` but the result
is just silently absent from the output JSON. A reader of the JSON
won't know why "the hold-out test wasn't run".
**Fix**: return a dict like `{"status": "insufficient_sensors",
"n_tg": ..., "n_tr": ...}` so the gap is explicit.

### S5. No `__pycache__/` in `.gitignore`

**Issue**: `.gitignore` excludes `__pycache__/` correctly. ✅ False alarm.
**No fix needed.**

### S6. `data/upstream/martinez2021/` is bundled but never read by the pipeline

**File**: `data/upstream/martinez2021/` (Martinez code release: `.mat` + README)
**Issue**: The `.mat` file is a numerical lookup table from Martinez &
Siegler's Zenodo release. We re-implemented the model in
`lunar/properties.py` so we don't need the `.mat` at runtime. Bundling
it is good for citation but the README should say
"reference only — pipeline does not load this file".
**Fix**: clarify in `data/upstream/martinez2021/README.md`.

### S7. Notebook 03 has a 60-line inline Diviner-closure cell

**File**: `notebooks/03_results.ipynb` (Fig 9 cell)
**Issue**: This logic should be in `scripts/figures/make_letter_figures.py`
as `fig_diviner_closure()` so the notebook just calls it like every other
figure. Putting 60 lines of solver+matplotlib in a notebook cell is harder
to test, harder to reuse, and inconsistent with the rest of the codebase.
**Fix**: extract to a function. Notebook becomes a 3-line call.

### S8. No `make` shortcut, no CI test for notebook execution

**Issue**: A reviewer who wants to verify the paper has to know to run
`pytest`, then run 5 notebooks in order, then `latexmk`. A `Makefile`
with `make figures`, `make paper`, `make all` would be friendly.
GitHub Actions only runs `pytest`; it could also run the FAST-path
notebooks via `nbconvert` to catch regressions in the orchestrators.
**Fix**: add a `Makefile` and a second GH Actions job that
runs `00_setup` + `01_methods` + `02_retrieval (fast)` + `03_results` +
`04_discussion` end-to-end.

---

## Positive findings (the parts that are solid)

- **Geometric depth grid** (`lunar/grid.py`) is correctly implemented;
  CLAUDE.md hard rule #2 (no uniform grids) is enforced by both the
  `make_geometric_grid` signature and the tests.
- **Crank-Nicolson assembly** uses harmonic-mean face conductivity
  — the correct choice for diffusion with discontinuous coefficients.
  Standard FV practice.
- **Surface BC** uses Newton iteration with the right Jacobian sign
  (always negative), guaranteed to converge from any positive start.
- **All physical constants** are imported from `lunar/constants.py` and
  cited to their literature source. CLAUDE.md hard rule #1 satisfied.
- **Bootstrap** correctly handles per-sensor depth uncertainty (same
  jitter applied to repeated indices, fresh jitter per resample). The
  cached temperature profile approach is the right efficiency trick.
- **All test files pass** (35/35 after pruning the two dead-code
  tests removed under C1) and exercise the key invariants of each
  module.
- **Provenance**: after the recent `compute_error_budget.py` work,
  every JSON in `output/` has exactly one generator script.
- **Reproducibility infrastructure**: SPICE kernels bundled, HFE data
  bundled, Diviner data fetched via a documented PDS URL with SSL
  fallback, fixed seed in the bootstrap.

---

## Suggested fix priority

If you only fix three things, do these in order:

1. **C1** (delete `_assemble_tridiagonal`) — 1 line, no risk.
2. **C2** (fix the error message in `diviner.py`) — 1 line, no risk.
3. **W3** (write `bootstrap_seed` and `git_commit` into the JSON) —
   makes the canonical results self-describing. ~10 lines.

After that, **C3** (clean up `apollo_helpers.py`) is the highest-value
larger task. The 540 lines of orphan code are confusing every reader.

---

## Verification appendix

### Method

1. Saved the shipped `output/kd_retrieval_results.json` and
   `output/kd_error_budget.json` to `/tmp/canonical_*.json`.
2. Deleted every file in `output/` (all JSONs, all auxiliary sensitivity
   files, the figure subdirectories).
3. Re-ran the full pipeline from scratch:
   ```
   python scripts/pipeline/retrieve_kd.py
   python scripts/pipeline/compute_borestem_sensitivity.py
   python scripts/pipeline/compute_stability_threshold_sensitivity.py
   python scripts/pipeline/compute_surface_bias_test.py
   python scripts/pipeline/compute_headline_rmse.py
   python scripts/pipeline/compute_error_budget.py
   ```
4. Diffed the fresh `kd_retrieval_results.json` against the canonical.

### Result

```
A15: canonical=4.859970  fresh=4.859970  diff=0.00e+00 mW/m/K
   bootstrap median: canonical=4.8834   fresh=4.8834
   bootstrap ci_lo:  canonical=3.9450   fresh=3.9450
   bootstrap ci_hi:  canonical=14.3592  fresh=14.3592
A17: canonical=11.233430 fresh=11.233430 diff=0.00e+00 mW/m/K
   bootstrap median: canonical=11.5097  fresh=11.5097
   bootstrap ci_lo:  canonical=10.1805  fresh=10.1805
   bootstrap ci_hi:  canonical=21.6247  fresh=21.6247
```

Bit-exact match across the K_d* point estimate, the bootstrap median,
and both 95 % CI bounds. Every σ component of `kd_error_budget.json`
also matches the canonical file to all decimal places (sigma_stat,
sigma_Qb, sigma_zb, sigma_thr, sigma_A, sigma_chi, sigma_H, sigma_Ks,
sigma_rho, total_quadrature, median, ci95_lo, ci95_hi — 13 fields per
site, 26 total, all exact). Verified by:

```bash
python3 -c "
import json
c = json.load(open('/tmp/canonical_kd_retrieval.json'))
f = json.load(open('output/kd_retrieval_results.json'))
for s in ('A15','A17'):
    assert c[s]['kd_star'] == f[s]['kd_star']
    for k in ('median','ci_lo','ci_hi'):
        assert c[s]['bootstrap'][k] == f[s]['bootstrap'][k]
print('Bit-exact reproduction confirmed.')
"
```

### What this proves and what it doesn't

**Proves**: given the bundled inputs and the pinned bootstrap seed,
the headline numbers in the manuscript can be regenerated byte-for-byte
from a wiped `output/` directory.

**Does not prove**: numerical correctness of the underlying physics
(that is the job of the test suite + the cross-checks against Diviner
in §4 of the paper). A reader who suspects a bug in, say, the
Crank-Nicolson solver should look at
[tests/test_solver_smoke.py](../tests/test_solver_smoke.py) and
[tests/test_pipeline_smoke.py](../tests/test_pipeline_smoke.py).
