# Cross-check status, 2026-06-22 UTC

## Checklist

- PASS: `make test` now imports the local `src/` package and passes: 43/43.
- PASS: Guidebook compiled twice with `pdflatex -interaction=nonstopmode`; no undefined references or citations. One pre-existing float-size warning remains.
- PASS: Canonical JSON values checked against the guidebook: `K_d*` 4.58 / 8.12, contrast 3.31, `p=0.0107`, quadrature totals 1.75 / 4.61, MCMC `P(A17>A15)=0.833`, and AICc gaps 3.99 / 2.71.
- PASS: Code references checked for the named load-bearing symbols: `find_stable_window`, `_thomas`, `conductivity_hayne`, `solve_periodic_equilibrium`, `kd_star_from_residuals`, `EQ_Z_ANCHOR`, and `SPICE_KERNEL_DIR`.
- PASS: Notebook spot-check: `notebooks/00..04` contain no inline solver, stable-window, or `K(T,z)` reimplementation; stale `scripts/`, `output/`, and `docs/letter/figures/` paths were updated.
- PASS: Letter audit completed without editing `docs/letter/letter.tex` or `letter.pdf`.
- NOT RUN: `make retrieve`; canonical `results/kd_retrieval_results.json` was probed directly instead.

## What Changed

- Test/import reliability: added pytest `pythonpath = ["src"]` in `pyproject.toml`.
- Numerical robustness: added `SPICE_KERNEL_DIR` support in `src/lunar/ephem.py`; added validation for surface Newton BC inputs, sub-skin reconstruction conductivity/depth inputs, zero-flux closure, out-of-grid observation depths, and anchor depth below grid bottom.
- Test coverage: added dedicated tests for `_solve_surface_newton`, `_reconstruct_subskin`, `_mean_flux_closure`, and the SPICE directory override.
- Pipeline/notebook consistency: updated pipeline/figure scripts and notebooks to prefer local `src/` and current `pipeline/` / `results/` paths.
- Guidebook: added F1 bug, 3D thermal field, and MCMC corner figures; improved the `K(T,z)` figure; fixed M2/M3 AICc labeling; updated test counts to 43; sharpened `chi` conditionality/runbook text; corrected the Martínez alpha interpretation to current JSON values.
- Letter: wrote `docs/letter/AUDIT_20260622.md` only.

## Not Fixed

- HIGH: `docs/letter/letter.tex:826` labels Apollo 15 Table 2 as `K_d*=4.57 [4.12,7.45]`; canonical retrieval text/JSON round to 4.58. Recommendation: change to 4.58 or relabel as the RMSE-table site-fit value.
- MEDIUM: `docs/letter/letter.tex:722` still says each `K_d` uses a full Crank--Nicolson spin-up, while the solver section describes the flux-anchored equilibrium construction. Recommendation: revise to “certified periodic-equilibrium solve.”
- MEDIUM: `letter.pdf` is rendered in `newonly` mode with green text and line numbers. Recommendation: build the clean submission PDF before sending.
- MEDIUM: Open Research names the GitHub repo but not a frozen tag/commit or Zenodo DOI. Recommendation: add the canonical results commit/release before submission.

## Letter Audit

See `docs/letter/AUDIT_20260622.md`.

## Final State

- Guidebook: 68 pages.
- Guidebook figures: 37 figure floats; `results/figures/` now contains 52 PDFs.
- Tests: 43/43 passing.
- Letter source/PDF: unchanged; audit report added only.
