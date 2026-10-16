# Notebook guide

`run_everything.ipynb` runs the whole study and shows every number of the
letter next to the value this repository gives. Each analysis step is one
script in `code/pipeline/`; a notebook cell runs it with `nb.step(...)` and its
printout streams into the notebook. Nothing is computed in the notebook itself,
so it and `make aux` run exactly the same code.

## Start

```bash
cd Lunar-HFE
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev,mcmc]"
jupyter lab code/notebooks/run_everything.ipynb
```

Choose `MODE` in the first code cell, then *Run All*. In VS Code, pick the
`.venv` Python as the kernel.

## The run mode

| `MODE` | What runs | Time |
|---|---|---|
| `"show"` (default) | nothing: every step reads its stored result in `code/results/` | minutes |
| `"quick"` | steps of a few minutes run; long ones run their fast form (re-analysing stored model runs) or show the stored result | about 45 min |
| `"full"` | every step from scratch, as for the paper | about 6 h on a six-core laptop |

Figures are made whenever one is missing (a fresh download has none) and
remade in "quick" and "full". On a Mac each step keeps the computer awake
(`caffeinate`), but not with the lid closed. In every mode, the comparison
tables (✓ / ✗) check the results against the letter, and the last cell counts
them (274 values).

## What the notebook contains

**Part 1, setup:** Python and library versions, the `lunar` package, the Apollo
record, the SPICE kernels, and the optional downloads (Diviner, LOLA).

**Part 2, the analysis**, in the order the steps need each other. Scripts are
in `code/pipeline/compute/`; times are for a full run.

| Step (script) | Time | Letter |
|---|---|---|
| `retrieve_kd.py` (the fixed-albedo stage; later steps reuse it) | 95 min | Sec. 3.2 |
| `compute_common_epoch.py` | 15 min | Secs. 3.1, 3.4 (common 1974 window) |
| `compute_diviner_closure.py`, `compute_review_diagnostics.py` (need Diviner) | 3, 5 min | Fig 1 swing depth; Diviner inputs |
| `compute_albedo_diagnostics.py`, `compute_albedo_sensitivity.py`, `compute_albedo_anchor.py` | 13, 35, 5 min | Sec. 3.2; SI Table S7 |
| `compute_stability_windows.py` | seconds | Sec. 2.1; SI Table S1 |
| **`compute_joint_albedo_fit.py`** (quick: `--reuse`) | 25 min | **Sec. 3.3, Table 1** |
| `certify_joint_numerics.py` | 3 min | SI Table S3 |
| `compute_joint_valley.py` | seconds | SI Table S11 |
| `compute_joint_probe_checks.py` | seconds | Secs. 3.2, 4.2; SI Table S9 |
| `compute_joint_block_bootstrap.py` | 1 min | Sec. 2.3; SI Table S5 |
| `compute_joint_fit_sensitivities.py` (quick: `--reuse`, if its cache is present) | 80 min | Table 2; Sec. 4.2; SI Tables S5, S12 |
| `compute_joint_fit_checks.py` | 4 min | Table 1, Fig 3; Secs. 3.1, 3.4 |
| `compute_martinez_density.py` | 20 min | Sec. 4.3; SI Table S4 |
| `compute_joint_diviner.py` (needs Diviner) | 3 min | SI Table S13, SI Fig S6 |
| `compute_gradient_epochs.py` | seconds | Secs. 3.1, 3.3; SI Table S2 |
| `compute_joint_chi_density.py` | 50 min | Sec. 4.3; SI Table S14 |
| `compute_likelihood_ratio.py` | seconds | every $p$: Table 1; Secs. 3.3, 4.2, 4.3 |
| `compute_annual_wave.py` | 3 min | Sec. 3.2, Fig 5; SI Table S10 |
| `compute_own_diffusivity_fit.py` | seconds | Secs. 3.4, 4.2; SI Table S10 |
| `compute_annual_wave_surface_test.py` | 6 min | Sec. 4.4; SI Table S10 |
| `compute_transient_warming.py` | 2 min | Secs. 3.2–3.4, 4.4; SI Table S8 |
| `compute_joint_mcmc.py` (quick: `--sample`) | 2 h | Secs. 3.4, 4.2; Fig 6; SI Table S6 |

**Part 3, the figures:** `figures/make_joint_figures.py` (Figs 1–7, SI Figs
S3–S5; 4 min), `figures/make_context_map_figure.py` (SI Fig S1; needs the LOLA
map), `figures/make_study_overview.py` (SI Fig S2; needs pdflatex), and the
Diviner step (SI Fig S6).

**Part 4, the paper section by section:** Sections 2.1–2.3 (data, model,
fitting), 3.1 (the models against each sensor), 3.2 (one measurement at a
time), 3.3 (all measurements together), 3.4 (checks of the joint fit) and 4
(discussion), each with its tables of checks and its figures.

**Part 5, summary:** how many values were checked and whether all match.

## Optional notebooks

| Notebook | What it shows | Time |
|---|---|---|
| `optional_anchor_method.ipynb` | how the flux-anchored solver reaches the steady state, live, step by step (*figures/* `make_spinup_animation.py`, `make_anchor_method_animation.py`, `make_anchor_process_figure.py`) | 1–5 min |
| `optional_performance.ipynb` | the solver in Python, Numba and C++ compared (`benchmark_cpp.py`) | minutes |

Neither is needed for the paper's numbers.

## Where the code is

- `code/src/lunar/`: the physics (installed as the package `lunar`). Start
  with `properties.py`, then `equilibrium.py`.
- `code/pipeline/compute/`: the analyses. Each script's first lines say what
  it does, what it reads and writes, and how long it takes.
- `code/results/README.md`: which file holds which number of the paper.

## Older notebooks

The seven notebooks of v1.5-jgr (00_setup to 06_performance) follow the
earlier draft of the letter; they are in release v1.5-jgr. The notebooks of
the study's fixed-albedo stage (K_d 4.60 / 7.08) are in release v1.4.2-jgr.
