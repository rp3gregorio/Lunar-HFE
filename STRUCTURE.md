# Repository structure

This repository holds the code, inputs and results of the paper, nothing else.
The manuscript is kept separately.

```
Lunar-HFE/
├── code/
│   ├── src/lunar/          the physics, as an installed package (import lunar)
│   │   ├── config.py         every site value and solver setting (one source of truth)
│   │   ├── constants.py      cited physical constants
│   │   ├── properties.py     conductivity K(T,z), density, heat capacity (Hayne et al. 2017)
│   │   ├── grid.py           the depth grid (69 cells to 5 m)
│   │   ├── solver.py         the heat equation (Crank-Nicolson, compiled with Numba)
│   │   ├── equilibrium.py    the flux-anchored periodic-equilibrium solver
│   │   ├── apollo_helpers.py the Apollo record and each sensor's stability window
│   │   ├── ephem.py          Sun position (SPICE)
│   │   ├── diviner.py        Diviner surface temperatures
│   │   ├── notebook.py       runs the pipeline steps from the notebooks
│   │   └── plotting/         the figure style
│   │
│   ├── pipeline/
│   │   ├── compute/        one script per analysis; each writes code/results/<name>.json
│   │   ├── figures/        the figure scripts (writes figures/)
│   │   ├── make_all_figures.py   all of the paper's figures ("make figures")
│   │   └── fetch_diviner.py, fetch_apollo_site_maps.py, extract_lola_relief.py   data preparation
│   │
│   ├── notebooks/          00-06: run the whole study, step by step (README.md inside)
│   ├── results/            every result the paper reports (README.md maps file -> paper)
│   ├── data/               inputs: Apollo HFE record, SPICE kernels, site maps, LOLA relief
│   ├── tests/              unit tests of the physics code (make test)
│   └── cpp/                an independent C++ copy of the solver (SI Table S5)
│
├── figures/                generated figures (not in git; make figures, or the notebooks)
├── documents/notes/REPRODUCING.md   the step-by-step recipe
└── README.md  Makefile  pyproject.toml  CITATION.cff  LICENSE  LICENSE-CC-BY-4.0
```

## How the parts connect

Data flow one way:

```
code/data/  ->  code/pipeline/compute/  ->  code/results/  ->  code/pipeline/figures/  ->  figures/
                       ^                                              ^
                 code/src/lunar/ (the physics)                code/src/lunar/plotting/
```

- **The physics lives only in `code/src/lunar/`.** The pipeline scripts call
  it; they never redefine a site value or a solver setting (`config.py` is the
  one source).
- **Each analysis is one script** in `code/pipeline/compute/`, with its purpose,
  inputs, outputs and runtime in its first lines. The `Makefile` (`make aux`)
  and the notebooks run them in the same order.
- **Figures never compute physics.** They read `code/results/`.
- **The notebooks are the interface.** Each cell calls one script through
  `lunar.notebook.step`, so the notebooks and `make` run exactly the same code.

## Order of the analysis

`retrieve_kd.py` and the analyses the joint fit builds on (common 1974 window,
Diviner comparison, albedo models) come first; then the joint fit
(`compute_joint_albedo_fit.py`), its tests and error budget, and the
independent checks (annual wave, warming after deployment, posterior). The
`Makefile` lists all 24 steps in order, with their runtimes.

## Earlier versions

Analyses and figures of the study's earlier stages (the fixed-albedo
analysis, the GEDES thesis, the AOGS poster, the guidebook) are not in the
current tree. They are in the git history and in release v1.4.2-jgr.
