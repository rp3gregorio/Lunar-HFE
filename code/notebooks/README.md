# Notebook guide — how to run everything, and what code each part uses

**Read this first, keep it open while you work.** It maps every notebook — and
each step *inside* a notebook — to the exact `.py` file behind it, so you always
know what is actually running.

Two references live in this folder:

| File | Use it for |
|------|------------|
| **`README.md`** (this file) | how to *run* the notebooks + what code each step uses |
| **`CODE_MANUAL.pdf`** (also `.md`) | the *file-by-file* reference — what every `.py` module does and how they connect (with diagrams) |

Rule of thumb: **this guide tells you *which* code a cell runs; the CODE MANUAL
tells you *what that code does inside*.**

*(Prefer to print or read offline? `NOTEBOOK_GUIDE.pdf` is the PDF version of
this file, and `CODE_MANUAL.pdf` is the code reference in PDF.)*

---

## Running them in Jupyter

```bash
cd Lunar-HFE
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"          # installs the `lunar` package (editable)
jupyter lab code/notebooks/
```

Then open the notebooks **in order, 00 → 06**, and use *Run All* on each. Every
notebook finds the repo by itself (`lunar._bootstrap.find_repo_root()`), so it
works no matter where Jupyter was launched. The results are **cached** — you can
read the numbers and figures without waiting for the long solves to finish.

---

## The three kinds of code (what the notebooks are calling)

Everything a notebook runs falls into one of three layers. Knowing which layer a
cell touches tells you what it does:

| Layer | Folder | What it is | Writes files? |
|-------|--------|-----------|---------------|
| **Engine** | `code/src/lunar/` | the physics *library* — solver, equilibrium method, properties, grid, config. Pure and reusable; every notebook imports it. | no |
| **Pipeline** | `code/pipeline/` | the *application* that runs the engine. `compute/` turns physics into `code/results/*.json`; `figures/` turns that JSON into PDFs. | yes |
| **Tests** | `code/tests/` | pytest checks the **engine** is correct (imports `lunar`, never the pipeline). | no |

So when a notebook does `import lunar.equilibrium` it is calling the **engine**;
when it does `import make_letter_figures` or runs `retrieve_kd.py` it is calling
the **pipeline**.

---

## Reading order at a glance

The order is **chronological**: set up, see what we measure, learn the solver,
run it, then the result and discussion figures, and finally performance.

| # | Notebook | What it produces | Main code it uses |
|---|----------|------------------|-------------------|
| 00 | `00_setup.ipynb` | environment + data-load check | `lunar.apollo_helpers`, `lunar.ephem` |
| 01 | `01_methods.ipynb` | letter methods figures (Figs 1–3, 5) | `pipeline/figures/`: `make_intro_figures`, `make_context_map_figure`, `make_apollo_timeline_letter`, `make_letter_figures` |
| 02 | `02_anchor_method.ipynb` | **the flux-anchored solver**, explained + animated | `lunar.equilibrium`, `lunar.{config,grid,properties,solver}`, `make_equilibrium_demo` |
| 03 | `03_retrieval.ipynb` | **the core K_d retrieval** → `kd_retrieval_results.json` | `pipeline/compute/retrieve_kd.py` |
| 04 | `04_results.ipynb` | letter Figs 6–10 (results) | `pipeline/figures/`: `make_letter_figures`, `make_results_figures`; `pipeline/compute/compute_diviner_closure` |
| 05 | `05_discussion.ipynb` | letter Figs 11–12 (discussion) | `pipeline/figures/`: `make_results_figures`, `make_prior_estimates_figure` |
| 06 | `06_performance.ipynb` | the solver kernel in C++ (agreement + speed) + the retrieval run live (tqdm) | `pipeline/compute/benchmark_cpp`, `cpp/solver.cpp`, `pipeline/compute/retrieve_kd` |

**One linear read.** Each notebook builds on the one before it — you meet the
solver (`02`) before the retrieval that uses it (`03`), and you see the result
before the discussion. The two *explainers* are `02` (how the solver works) and
`06` (how the three backends compare); the rest is the letter pipeline. **The one
hard rule: run `03_retrieval` before `04`/`05`** — those figure notebooks read
the JSON it writes.

---

## Inside each notebook — step → code → what happens

### `00_setup` — is everything wired up?
- **environment check** → `lunar._bootstrap.find_repo_root()` locates `code/` and confirms the `lunar` package imports.
- **load the Apollo record** → `lunar.apollo_helpers.extract_sensor_stability()` (which reads `code/data/apollo/` via `lunar.validation`) — returns each sensor's depth, equilibrium temperature, and the deep-sensor mask.
- **solar geometry** → `lunar.ephem` (SPICE kernels in `code/data/spice/`).
- *(one-time)* `pipeline/fetch_diviner.py` downloads the Diviner surface-temperature tiles used later by Fig 9.

### `01_methods` — the methods figures (Figs 1–3, 5)
Each cell: **import a generator → call it (it writes `figures/<name>.pdf`) → `show_fig()` displays it.**
- **Fig 1 probe schematic** → `make_intro_figures.fig_intro_probe()` — draws both borestems from the *real* sensor depths (`lunar.apollo_helpers`) and the K(T,z) model comparison (`lunar.properties`).
- **Fig 2 context map** → `make_context_map_figure.main()` — three nearside globes; uses the LOLA DEM in `code/data/lola/`.
- **Fig 3 sensor timeline** → `make_apollo_timeline_letter.main()` — the per-sensor stability windows (`lunar.apollo_helpers`).
- **Fig 5 amplitude vs depth** → `make_letter_figures.fig_amplitude_vs_depth()` — how the diurnal wave decays with depth (`lunar.solver`).

### `02_anchor_method` — how the flux-anchored solver works
The heart of the study, explained before you use it in `03`.
- builds the depth grid → `lunar.grid.make_geometric_grid`
- runs the slow **brute-force** spin-up and the fast **flux-anchored** solve and shows they reach the *same* steady state → `lunar.equilibrium.solve_periodic_equilibrium`, `lunar.solver`
- reads temperatures off a converged cycle → `lunar.equilibrium.profile_at_time` / `profile_at_local_time`
- the teaching animations → `make_equilibrium_demo`

### `03_retrieval` — the core computation (writes the headline JSON)
- **Step 1** runs `pipeline/compute/retrieve_kd.py` (as a subprocess). Inside, per site it: loads the fit targets (`lunar.apollo_helpers`), **sweeps K_d** and for each value solves the model to steady state (`lunar.equilibrium.solve_periodic_equilibrium` → `lunar.solver`, the method from `02`), finds the RMSE minimum (**K_d\***), and **bootstraps** the confidence interval. It writes `code/results/kd_retrieval_results.json` — **the file every figure notebook reads.**
- **verify cell** → reads that JSON and prints K_d\* and the 95% CI per site.
- **Step 2 (optional)** → the `compute_*` sensitivity scripts; each re-runs the retrieval under one perturbed assumption and writes its own JSON (Table 3 error budget).
- **Step 3 (optional)** → `bayesian_crosscheck.py` — an independent MCMC (`emcee`) cross-check of the contrast direction.

### `04_results` — the results figures (Figs 6–10)
Same **generator → `show_fig()`** pattern; these read the JSON from `03`:
- **Fig 6 mean-T profile** → `make_letter_figures.fig_mean_T_profile()`
- **Fig 7 K_d sweep** → `make_letter_figures.fig_kd_sweep()`
- **Fig 8 bootstrap** → `make_results_figures.fig_bootstrap()`
- **Fig 9 thermal profiles** → `make_results_figures.fig_thermal_profiles()`
- **Fig 10 Diviner closure** → runs `pipeline/compute/compute_diviner_closure.py` (compares the model surface temperature to Diviner; needs the fetched Diviner data).

### `05_discussion` — the discussion figures (Figs 11–12)
- **Fig 11 robustness** → `make_results_figures.fig_robustness()` — the inter-site contrast under stress tests.
- **Fig 12 five-decade K_d context** → `make_prior_estimates_figure.main()` — the two-panel figure separating the *contact asymptote* K_d from the *effective* K.

### `06_performance` — the C++ kernel and the retrieval it powers
All about the one demanding primitive (the solver march), in three parts:
- **§1 agreement** compiles `code/cpp/solver.cpp` (`clang++`) **right in the notebook** and runs *all three* engines — generic Python, Numba, C++ — on identical inputs through `pipeline/compute/benchmark_cpp.py` (`dump_inputs` / `run_cpp` / `run_py`), confirming they agree to ~10⁻¹² K. Python stays the *driver*: it serialises the inputs, launches the compiled C++ binary with `subprocess`, and reads the field back.
- **§2 speed** plots the steady-state ms/lunation for each engine from `results/cpp_benchmark.json`.
- **§3 the real workload** runs the actual `retrieve_kd.run_kd_sweep_extended` **live with a `tqdm` progress bar**, lands on the published K_d\* (4.600 / 7.079), and shows what the backend costs on the full 61-solve sweep (`results/speedup_benchmark.json`).

> For what any of these `.py` modules do *internally* — every function, and how
> the modules depend on one another — open **`CODE_MANUAL.pdf`** in this folder.

---

## The other running order — `make all`

The notebooks *narrate* the science; the **Makefile** is the machine order that
regenerates everything from scratch:

1. **`make retrieve`** → `code/pipeline/compute/retrieve_kd.py` → `code/results/kd_retrieval_results.json`
2. **`make aux`** → the sensitivity / model-selection / error-budget sweeps:
   `compute_headline_rmse` · `compute_borestem_sensitivity` ·
   `compute_stability_threshold_sensitivity` · `compute_surface_bias_test` ·
   `compute_uniform_kd_sensitivity` · `compute_fixed_input_sensitivities` ·
   `compute_model_selection` · `compute_error_budget` · `compute_common_epoch` ·
   `compute_diviner_closure` · `bayesian_crosscheck` · `qb_prior_width_scan`
   → more `code/results/*.json`
3. **`make figures`** → `code/pipeline/make_all_figures.py` runs every generator → `figures/`
4. **`make paper`** → compiles the documents in `documents/`

## Scripts used on demand (not in `make all`)

Live, but run only when re-certifying or exploring:

| Script | Run by / when | Writes |
|---|---|---|
| `pipeline/compute/benchmark_cpp.py` | notebook 06; Python↔C++ head-to-head | `results/cpp_benchmark.json` |
| `pipeline/compute/benchmark_speedup.py` | `make_speedup_figure.py`; after any solver-config change | `results/speedup_benchmark.json` |
| `pipeline/compute/convergence_scan.py` | `make_convergence_study.py`; n_inner certification | scan JSON |
| `pipeline/compute/dt_ladder.py` | `make_dt_ladder_figure.py`; time-step certification | ladder JSON |
| `pipeline/compute/check_discretization.py` | standalone; grid/vertex sanity check | (report) |
| `pipeline/fetch_diviner.py` | one-time ~310 MB Diviner download | `code/data/diviner/` |
| `pipeline/extract_lola_relief.py` | one-time; cut LOLA crops for the context map | `code/data/lola_relief/` |
