# Notebooks — reading order and which code each one uses

This folder is the **narrated walkthrough** of the project, in the order a
reader should follow it (**00 → 06**). Each notebook drives the real
`src/lunar` engine and/or the `pipeline/` scripts — it does **not**
re-implement physics. The table says exactly which `.py` files each notebook
touches, so you can jump from a notebook to the code behind it.

**Two tracks.** `00 → 04` is the **letter pipeline**: run them and they
regenerate every one of the 11 figures in `letter.pdf` into the shared
top-level `figures/` (02 first, for the retrieval JSON the figure notebooks
read). `05` and `06` are the **method & performance explainers** — how the
flux-anchored solver works, and how the three solver backends compare and
scale to a map.

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
| 01 | `01_methods.ipynb` | Methods-section figures — probe schematic, site-context map, sensor timeline, amplitude-vs-depth (letter Figs 1–4) | `pipeline/figures/`: `make_intro_figures`, `make_context_map_figure`, `make_apollo_timeline_letter`, `make_letter_figures` |
| 02 | `02_retrieval.ipynb` | The core K_d retrieval + bootstrap — writes `kd_retrieval_results.json` (the input every figure notebook reads) | `pipeline/compute/retrieve_kd.py`, run via `subprocess` |
| 03 | `03_results.ipynb` | Results figures — mean-T profile, K_d sweep, bootstrap, thermal profiles, Diviner closure (letter Figs 5–9) | `pipeline/figures/`: `make_letter_figures`, `make_results_figures`; `pipeline/compute/compute_diviner_closure` |
| 04 | `04_discussion.ipynb` | Discussion figures — inter-site robustness contrast, prior-K estimates (letter Figs 10–11) | `pipeline/figures/`: `make_results_figures`, `make_prior_estimates_figure` |
| 05 | `05_method.ipynb` | **The flux-anchored method, explained + animated** — brute force vs. shortcut (same answer), three teaching GIFs, and reading profiles off a converged cycle. *(merged from the former `05_animations` + `equilibrium_demo`)* | `lunar.equilibrium` (`solve_periodic_equilibrium`, `profile_at_time`, `profile_at_local_time`), `lunar.{config,grid,properties,solver}`, `make_equilibrium_demo` |
| 06 | `06_performance.ipynb` | **Performance & scale-up** — generic-Python vs. Numba vs. C++ speed (all three verified equal to ~1e-12 K), then scaling to a **region of the Moon** (naive per-pixel vs. latitude-symmetry, real-surface drape, poles). *(merged from the former `07_cpp_solver` + `08_mapping_scaleup`)* | `pipeline/compute/benchmark_cpp`, `cpp/solver.cpp`, `lunar.{config,constants,grid,solver,plotting}`, `results/cpp_benchmark.json`, `figures/moon_global.png`, `aogs/data/lola/ldem_16.img` |

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
