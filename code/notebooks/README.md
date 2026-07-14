# Notebooks — reading order and which code each one uses

This folder is the **narrated walkthrough** of the project, in the order a
reader should follow it (00 → 07, then the two demos). Each notebook drives
the real `src/lunar` engine and/or the `pipeline/` scripts — it does **not**
re-implement physics. The table says exactly which `.py` files each notebook
touches, so you can jump from a notebook to the code behind it.

> The three code layers, in one line:
> - **`src/lunar/`** — the *engine* (importable library: the solver, the
>   equilibrium method, properties, config, grid). Pure, reusable, no file
>   writes. Everything else imports it.
> - **`pipeline/`** — the *application* that runs the engine: `compute/`
>   turns physics into `results/*.json`; `figures/` turns those JSON into
>   the figures. Scripts with side effects (they write files).
> - **`tests/`** — pytest checks that the **engine** is correct. They import
>   `src/lunar`, never the pipeline.

## Notebook reading order

| # | Notebook | What it does | Key code it uses |
|---|----------|--------------|------------------|
| 00 | `00_setup.ipynb` | Environment check; load the Apollo HFE record and solar geometry | `lunar.apollo_helpers`, `lunar.ephem` |
| 01 | `01_methods.ipynb` | The methods-section figures (site context, probe geometry, timeline) | `pipeline/figures/`: `make_context_map_figure`, `make_intro_figures`, `make_apollo_timeline`, `make_letter_figures` |
| 02 | `02_retrieval.ipynb` | The core K_d retrieval + bootstrap (the headline result) | `pipeline/compute/retrieve_kd.py` (`run_kd_sweep`, `kd_star`, `bootstrap`), run via `subprocess` |
| 03 | `03_results.ipynb` | The results figures (RMSE bowls, thermal profiles) | `pipeline/figures/`: `make_letter_figures`, `make_results_figures` |
| 04 | `04_discussion.ipynb` | Discussion diagnostics (Martínez α-sweep, prior estimates) | `pipeline/figures/`: `make_alpha_sweep_figure`, `make_results_figures` |
| 05 | `05_animations.ipynb` | Builds the teaching animations from the real solver | `lunar.{config,equilibrium,grid,properties,solver}`, `lunar.plotting` |
| 06 | `06_figure_editor.ipynb` | Interactive figure tweaking against archived bootstrap draws | `lunar._bootstrap`, `lunar.plotting`, `make_results_figures` |
| 07 | `07_cpp_solver.ipynb` | Head-to-head of the Python vs C++ solver | `pipeline/compute/benchmark_cpp.py`, `lunar.{config,grid,solver,_bootstrap}` |
| 08 | `08_mapping_scaleup.ipynb` | Simulate a **region of the Moon** with global values; compare the process (naive per-pixel vs latitude-symmetry) across the Python/Numba/C++ backends | `lunar.{config,constants,grid,solver,plotting}`, `results/cpp_benchmark.json` |
| — | `equilibrium_demo.ipynb` | Standalone demo of the flux-anchored equilibrium method | `lunar.equilibrium` (`solve_periodic_equilibrium`, `profile_at_time`), `lunar.{config,grid,properties,solver}` |

## The reproduction pipeline (the *other* order — `make all`)

The notebooks narrate the science; the **Makefile** is the machine order that
regenerates every artifact from scratch. Chronological stages:

1. **`make retrieve`** → `pipeline/compute/retrieve_kd.py` → `results/kd_retrieval_results.json`
2. **`make aux`** → the sensitivity/selection/budget sweeps, in order:
   `compute_headline_rmse` · `compute_borestem_sensitivity` ·
   `compute_stability_threshold_sensitivity` · `compute_surface_bias_test` ·
   `compute_uniform_kd_sensitivity` · `compute_fixed_input_sensitivities` ·
   `compute_model_selection` · `compute_error_budget` (pulls in
   `compute_qb_degeneracy`) · `compute_common_epoch` · `compute_diviner_closure`
   → more `results/*.json`
3. **`make figures`** → `pipeline/make_all_figures.py` runs every generator in
   its `JOBS` list → `figures/`
4. **`make paper`** → compiles `documents/{letter,guidebook}`

## Scripts that are NOT in `make all` (used on demand)

All of these are live — just not part of the standard rebuild. They are
diagnostics/benchmarks you run when re-certifying or exploring:

| Script | Run by / when | Writes |
|---|---|---|
| `pipeline/compute/benchmark_speedup.py` | `make_speedup_figure.py`; re-run after any solver-config change | `results/speedup_benchmark.json` |
| `pipeline/compute/benchmark_cpp.py` | notebook 07; C++ head-to-head | benchmark JSON |
| `pipeline/compute/convergence_scan.py` | `make_convergence_study.py`; n_inner certification | scan JSON |
| `pipeline/compute/dt_ladder.py` | `make_dt_ladder_figure.py`; time-step certification | ladder JSON |
| `pipeline/compute/check_discretization.py` | standalone; grid/vertex sanity check | (report) |
| `pipeline/compute/_results.py` | helper imported by `run_all_timed.py` | — |
| `pipeline/fetch_diviner.py` | one-time ~310 MB Diviner download | `data/diviner/` |
| `pipeline/extract_lola_relief.py` | one-time; cut LOLA crops for the context map | `data/lola_relief/` |

**Deliverable-specific generators (write outside `figures/`, so not in JOBS):**
- `pipeline/figures/make_abstract_figures.py` → `documents/abstract/figures/`
  (the GEDES abstract's own three-globe context map, etc.)
- `pipeline/figures/make_ppt_graphs{,_clean}.py`, `make_ppt_images.py` →
  slide-deck graphics for `documents/slides/`. **These are the one loose end:**
  they are not registered anywhere and not called by `documents/slides/build_deck.js`,
  so they are run by hand (or are stale). If the deck no longer needs them,
  they are the safe candidates to retire.
