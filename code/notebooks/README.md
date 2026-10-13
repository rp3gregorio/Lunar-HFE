# Notebook guide

The notebooks run the whole study, step by step, and show every result next
to the number printed in the paper. Each analysis step is one script in
`code/pipeline/`; a notebook cell runs it with `nb.step(...)` and its printout
streams into the notebook. Nothing is computed in the notebooks themselves, so
they and `make aux` run exactly the same code.

## Start

```bash
cd Lunar-HFE
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev,mcmc]"
jupyter lab code/notebooks/
```

Open the notebooks in order and use *Run All* on each.

## The run mode

The first code cell of each notebook sets `MODE`:

| `MODE` | What runs | Time, all notebooks |
|---|---|---|
| `"show"` (default) | nothing: every step reads its stored result in `code/results/` | minutes |
| `"quick"` | steps of a few minutes run; long ones run their fast form (re-analysing stored model runs) or show the stored result | about 30 min |
| `"full"` | every step from scratch, as for the paper | about 6 h on a six-core laptop |

Figures are made whenever one is missing (a fresh download has none) and
remade in "quick" and "full". On a Mac each run keeps the computer awake
(`caffeinate`). In every mode, the comparison tables (✓ / ✗) check the results
against the paper.

## What each notebook runs

Scripts are in `code/pipeline/compute/` unless marked *figures/*. Times are
for a full run.

| Notebook | Step (script) | Time | Paper |
|---|---|---|---|
| **00_setup** | checks; optional downloads (`fetch_diviner.py`, LOLA map) | — | — |
| **01_inputs** | `compute_stability_windows.py` | seconds | Sec. 2.1, SI Table S2 |
| | model inputs from `lunar/config.py` | — | SI Table S1 |
| | *figures/* `make_joint_figures.py` | 2 min | Figs 1, 2; SI Fig S4 |
| | *figures/* `make_context_map_figure.py` (needs the LOLA map) | 1 min | SI Fig S1 |
| | *figures/* `make_study_overview.py` (needs pdflatex) | seconds | SI Fig S2 |
| **02_anchor_method** | the solver, step by step, live; *figures/* `make_spinup_animation.py`, `make_anchor_method_animation.py`, `make_anchor_process_figure.py` | 1–5 min | Sec. 2.3; SI Fig S3 |
| **03_joint_fit** | `retrieve_kd.py` | 95 min | (inputs to the later steps) |
| | `compute_common_epoch.py` | 15 min | Sec. 3.2 (common 1974 window) |
| | `compute_diviner_closure.py`, `compute_review_diagnostics.py` (need Diviner) | 3, 5 min | Fig 1 swing depth; Diviner comparison |
| | `compute_albedo_diagnostics.py`, `compute_albedo_sensitivity.py`, `compute_albedo_anchor.py` | 13, 35, 5 min | SI Table S4 |
| | **`compute_joint_albedo_fit.py`** (quick: `--reuse`) | 25 min | **Table 1**, Sec. 3.2 |
| | `compute_joint_valley.py` | seconds | SI Table S9 |
| | `compute_joint_probe_checks.py` | seconds | Secs. 3.3, 4.1; SI Table S10 |
| | `compute_joint_block_bootstrap.py` | 1 min | SI Table S6 |
| | *figures/* `make_joint_figures.py` | 2 min | Fig 4 |
| **04_uncertainty_and_tests** | `certify_joint_numerics.py` | 3 min | SI Table S5 |
| | `compute_joint_fit_sensitivities.py` (quick: `--reuse`, if its cache is present) | 80 min | Tables 2, 3; SI Table S13 |
| | `compute_joint_fit_checks.py` | 1 min | Table 1 (RMSE, bias), Sec. 4.2 |
| | `compute_joint_diviner.py` (needs Diviner) | 3 min | SI Table S11, SI Fig S5 |
| | `compute_gradient_epochs.py` | seconds | Secs. 3.1, 3.2 |
| | `compute_joint_chi_density.py` | 50 min | Sec. 4.2, SI Table S14 |
| | `compute_likelihood_ratio.py` | seconds | Tables 1, 2 ($p$) |
| | *figures/* `make_joint_figures.py` | 2 min | Fig 3; SI Fig S6 |
| **05_annual_wave_and_posterior** | `compute_annual_wave.py` | 3 min | Sec. 3.4, Fig 5, SI Table S12 |
| | `compute_own_diffusivity_fit.py` | seconds | SI Table S12 |
| | `compute_annual_wave_surface_test.py` | 6 min | Sec. 4.4, SI Table S12 |
| | `compute_transient_warming.py` | 2 min | Sec. 4.3, SI Table S7 |
| | `compute_joint_mcmc.py` (quick: `--sample`) | 2 h | Sec. 4.1, Fig 6, SI Table S8 |
| **06_performance** | optional: Python, Numba and C++ solvers compared (`benchmark_cpp.py`) | minutes | SI Table S5 (last row) |

## Where the code is

- `code/src/lunar/` — the physics (installed as the package `lunar`). Start
  with `properties.py`, then `equilibrium.py`.
- `code/pipeline/compute/` — the analyses. Each script's first lines say what
  it does, what it reads and writes, and how long it takes.
- `code/results/README.md` — which file holds which number of the paper.

## Older notebooks

The notebooks of the study's earlier, fixed-albedo stage (K_d 4.60 / 7.08) are
in release v1.4.2-jgr; they do not reproduce the current paper.
