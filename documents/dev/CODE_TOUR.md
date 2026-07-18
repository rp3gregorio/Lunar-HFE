# Code tour — how the folders work together

*A walking guide to the repository: what each folder is for, who calls whom,
and how one number travels from raw Apollo data to the manuscript. Read this
top to bottom once; after that the [README](../README.md) tables are enough.*

*(For the physics and derivations, this document's companion is the guidebook,
`docs/guidebook/guidebook.pdf`. This tour is about the **code**.)*

---

## 1. The mental model: four layers, one rule

```
data/          raw inputs (Apollo record, Diviner, SPICE kernels)
   │
   ▼
src/lunar/     THE ENGINE — a pure Python library: physics, solver, config.
   │            Importable, tested, knows nothing about JSON files or figures.
   ▼
pipeline/      THE EXPERIMENTS — scripts that import lunar, run computations,
   │            and write their answers to results/.
   ▼
results/       THE RECORD — canonical JSON numbers + rendered figures.
   │            The single source of truth every document quotes.
   ▼
paper/, docs/  THE DOCUMENTS — letter + guidebook, which display results/
                and must never contain a number that isn't traceable to it.
```

**The one rule: dependencies point down this list, never up.**
`src/lunar` never reads `results/`; a figure script never computes physics
itself (it imports `lunar` or reads a JSON); the manuscripts never invent a
number (they quote `results/*.json`). When you know which layer a file lives
in, you know what it is allowed to touch.

`notebooks/` and `tests/` sit *beside* this chain: notebooks are interactive
front-ends onto the same layers (they import `lunar` and call the same
pipeline functions); tests are guardrails clamped onto `src/lunar`.

---

## 2. `src/lunar/` — the engine

One module per physical idea, listed here **in the order a single solve uses
them**:

| Module | What it owns | Key functions |
|---|---|---|
| `config.py` | **Single source of truth** for every setting: `SITES` (Q_b, albedo, lat/lon), `GRID`, `HAYNE` bundle, `KD_GRIDS`, `EQ_Z_ANCHOR`, `EQ_N_INNER` | — |
| `constants.py` | Cited physical constants (σ_SB, S₀, lunation length, Hayne parameters) | — |
| `apollo_helpers.py` | Reads the Nagihara-restored Apollo record; picks the stable window | `find_stable_window`, `extract_sensor_stability` |
| `grid.py` | The geometric depth grid (2 mm cells at the surface → 69 cells to 5 m) | `make_geometric_grid` |
| `properties.py` | Regolith physics: K(T,z), ρ(z), c_p(T) | `conductivity_hayne`, `density_hayne`, `specific_heat` |
| `solver.py` | The hour-by-hour heat-equation stepper (Crank–Nicolson + Thomas + surface Newton) | `solve_pixel`, `_step`, `_thomas`, `_solve_surface_newton` |
| `equilibrium.py` | **The method contribution**: the flux-anchored steady-state driver (Step A settles the skin, Step B reconstructs the deep) + instantaneous-profile helpers | `solve_periodic_equilibrium`, `_reconstruct_subskin`, `_mean_flux_closure`, `profile_at_time`, `profile_at_local_time` |
| `plotting/style.py` | House figure style: JGR widths, palette, `fmt_axis`, the `assert_no_overlap` guard | — |
| `diviner.py`, `ephem.py`, `validation.py`, `_bootstrap.py` | Support: Diviner data access, SPICE ephemeris, depth-table loader, notebook bootstrap | — |

How the core three nest, in one sentence each:

- **`solver.solve_pixel`** marches the column forward hour by hour for a given
  number of lunations — brute-force time integration, the expensive primitive.
- **`equilibrium.solve_periodic_equilibrium`** wraps it: run `solve_pixel` on
  a *truncated skin grid* (Step A), reconstruct everything below the anchor
  from the closure ODE (Step B), repeat until the anchor temperature stops
  moving. One call ≈ 13 s and returns an `EquilibriumResult` carrying the
  cycle-mean profile `T_mean`, the full stored lunar cycle `out.T`, and the
  convergence `history`.
- **`profile_at_local_time(eq, "14:30")`** then reads any instant of the day
  out of that stored cycle — no re-solve.

**House law:** if a physical value appears anywhere else in the repo, it is a
*copy* and it will eventually drift (this bit us with Q_b). Constants live in
`config.py`/`constants.py`, full stop.

---

## 3. `pipeline/` — the experiments

Thin command-line drivers. Every script imports `lunar`, computes one thing,
and writes one artifact. None of them define physics.

### `pipeline/compute/` — numbers (each writes `results/*.json`)

| Script | Writes | What it is |
|---|---|---|
| `retrieve_kd.py` | `kd_retrieval_results.json` | **The main event**: RMSE sweep over `KD_GRIDS` at both sites → vertex → K_d\*; then the 1500-draw bootstrap (`bootstrap_kd_with_depth_uncertainty`) → CIs, contrast, p-value |
| `compute_error_budget.py` | `kd_error_budget.json` | Reads the sensitivity JSONs below + the Q_b envelopes → quadrature σ per site |
| `compute_headline_rmse.py` | `headline_rmse.json` | Site-fit and global RMSE table |
| `compute_fixed_input_sensitivities.py` | `fixed_input_sensitivities.json` | Re-retrieval with each fixed input perturbed (albedo, K_s, ρ…) |
| `compute_borestem_sensitivity.py` / `compute_surface_bias_test.py` / `compute_stability_threshold_sensitivity.py` | matching JSONs | Individual robustness tests |
| `compute_uniform_kd_sensitivity.py` / `compute_model_selection.py` | `uniform_kd_test.json`, `model_selection.json` | Global-K_d comparison; AICc model selection |
| `bayesian_crosscheck.py` | `bayesian_crosscheck_samples.json` | The MCMC cross-check: emcee over (K_d, Q_b) with the degeneracy-aware likelihood |
| `compute_diviner_closure.py` | `diviner_closure.json` | Surface-temperature closure against Diviner |
| `benchmark_speedup.py` | `speedup_benchmark.json` | **The timing archive** (anchored vs brute wall-clock). Re-run after any solver-config change — the guidebook quotes this file |

### `pipeline/figures/` — pictures

Each `make_*.py` renders one figure (or family) into `results/figures/`,
importing `lunar.plotting.style` and reading either `lunar` directly or a
`results/*.json`. **`pipeline/make_all_figures.py`** holds the `JOBS` registry
— every generator must be listed there so `make figures` reproduces
everything. TikZ diagrams live separately in `docs/guidebook/figures-tikz/`
(built by that folder's `build.sh`).

---

## 4. `notebooks/` — the interactive layer

The notebooks do not contain private physics; they call the same code paths.

| Notebook | Role |
|---|---|
| `00_setup.ipynb` | environment + data integrity check |
| `01_methods.ipynb` | methods figures (Figs 1–4) |
| `02_anchor_method.ipynb` | the flux-anchored solver, explained + animated: brute force converges onto the flux-anchored answer; instantaneous profiles via `profile_at_time` / `profile_at_local_time` |
| `03_retrieval.ipynb` | the core per-site K_d retrieval + bootstrap |
| `04_results.ipynb` → `05_discussion.ipynb` | results & discussion figures (Figs 5–11), in paper order |
| `06_performance.ipynb` | the solver kernel in C++ (Python/Numba/C++ agree + speedup), then the K_d retrieval run live with a tqdm progress bar |

Rule of thumb: if a notebook cell grows a reusable idea, the idea moves into
`src/lunar` (with a test) and the notebook keeps only the call — that is
exactly how `profile_at_local_time` came to exist.

---

## 5. `tests/` — the guardrails (45 tests, `make test`)

| File | Guards |
|---|---|
| `test_constants.py` | the cited constants haven't drifted |
| `test_grid.py` | geometric grid construction |
| `test_properties.py` | K/ρ/c_p models (incl. the radiative term's presence) |
| `test_solver.py`, `test_solver_assembly.py` | the CN step, Thomas solve, surface energy balance |
| `test_equilibrium.py` | **the method**: guess-independence, flux closure, Step-B reconstruction, `profile_at_time` / `profile_at_local_time` |
| `test_ephem.py` | SPICE ephemeris helper |

The equilibrium tests run on a deliberately coarse grid with an explicit
`n_inner=12` so CI stays fast — they test *mechanics*, not production values.
Production convergence is certified separately (`results/convergence_scan.json`
and guidebook Fig. 3.11).

---

## 6. `results/` — the record

- `results/*.json` — the canonical numbers. **If a number in any document
  disagrees with these files, the document is wrong.**
- `results/figures/*.pdf` — rendered figures (hard-linked into
  `docs/guidebook/figures/` and `docs/letter/figures/`, so regenerating a
  figure updates every document at once).
- `results/anim/` — GIFs.

Provenance is embedded where it matters: `kd_retrieval_results.json` records
the bootstrap seed, depth σ, and the git commit that produced it.

---

## 7. Follow one number: where does K_d\*(A17) = 7.16 come from?

The single most useful exercise. Every step names the real file and function.

1. **Raw data.** `data/apollo/` holds the restored 1971–77 HFE record
   (Nagihara 2018).
2. **Targets.** `apollo_helpers.find_stable_window` scans the late mission,
   keeps the earliest window with |slope| < 0.08 K/yr, and
   `extract_sensor_stability` returns the equilibrium temperature of each of
   the 16 deep (≥ 80 cm) Apollo 17 sensors.
3. **One forward model.** For a trial K_d,
   `equilibrium.solve_periodic_equilibrium` (grid from `grid.py`, physics from
   `properties.py`, settings from `config.py`) returns the predicted
   cycle-mean profile ⟨T⟩(z; K_d) in ~13 s — using **no Apollo data**.
4. **The sweep.** `retrieve_kd.run_kd_sweep_extended` repeats step 3 for the
   32 trial values in `config.KD_GRIDS["A17"]` and scores each against the 16
   sensors → RMSE(K_d).
5. **The pick.** `retrieve_kd.kd_star_from_residuals` fits a parabola through
   the three lowest points → the vertex, **7.16 mW m⁻¹ K⁻¹**.
6. **The honesty.** `bootstrap_kd_with_depth_uncertainty` resamples sensors +
   jitters depths 1500 times against the *cached* sweep profiles → CI
   [6.20, 8.16]; paired with A15 → contrast 2.38, p = 0.031.
7. **The record.** All of it lands in `results/kd_retrieval_results.json`.
8. **The documents.** `pipeline/figures/*` render it (headline forest plot,
   sweep, clouds); `docs/letter/letter.tex` and the guidebook quote it.

Change anything upstream (a constant, the grid, n_inner) and the number is
only allowed to change by re-running this chain — never by editing a document.

---

## 8. "How do I…?" recipes

| I want to… | Do this |
|---|---|
| run the tests | `make test` (or `pytest -q`) |
| run one converged solve in Python | see the last cells of `notebooks/02_anchor_method.ipynb` |
| get T(z) at a local lunar time | `profile_at_local_time(eq, "14:30")` — same notebook |
| re-run the full retrieval | `make retrieve` (~15 min: 61 solves + bootstrap) |
| re-run all sensitivity/robustness numbers | `make aux` |
| rebuild every figure | `make figures`; a single one: `python pipeline/figures/make_<name>.py` |
| rebuild a TikZ diagram | `cd docs/guidebook/figures-tikz && ./build.sh <name>` |
| recompile the documents | `make paper` |
| everything from scratch | `make all` |
| change a physical constant | **only** in `src/lunar/config.py` / `constants.py`, with a source comment — then re-run the chain and record the before/after |
| re-measure the speed-up claims | `python pipeline/compute/benchmark_speedup.py` (updates the archive the guidebook quotes) |

---

## 9. House rules (learned the hard way)

These exist because each was once violated and cost real time — the full
stories are in guidebook Ch. 5, "Where every input comes from":

1. **One definition per constant** (`config.py`). A duplicated Q_b drifted
   silently and biased a headline number for weeks.
2. **A convergence criterion must test the quantity you report.** Cycle-to-cycle
   agreement passed while the deep column was 10–40 K wrong (the F1 bug);
   n_inner = 12 passed its own tolerance while biasing K_d\* by 0.4 mW.
3. **Every measured claim needs a writer script.** The timing archive went
   stale the moment its one-off benchmark script was deleted;
   `benchmark_speedup.py` now exists so "measured on this machine" is always
   re-runnable.
4. **Figures never hardcode results.** They read `results/*.json` or compute
   via `lunar` — hardcoded values are how Figure 2.1 once showed a K_d\* three
   revisions old.
5. **Text on data is a build error.** Figure scripts call
   `assert_no_overlap(ax)` before saving; the build fails rather than shipping
   an overlapping label.
