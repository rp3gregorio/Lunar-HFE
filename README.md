# apollo-hfe-kd-retrieval

Per-site retrieval of the lunar deep-regolith thermal conductivity $K_d$ at the
Apollo 15 and 17 Heat-Flow Experiment (HFE) boreholes from the restored
1971–1977 record.

This is the reproducibility repository for the paper:

> Gregorio, Larsson, Yamada, Kuroda & Kasai (2026), *Difference of Lunar Regolith
> Thermal Conductivity $K_d$ at the Apollo 15 and 17 Heat-Flow Boreholes*,
> submitted to **JGR: Planets**.

## What it does

We retrieve the deep-regolith thermal conductivity $K_d$ separately at each
Apollo HFE borehole by holding the Hayne (2017) $K(T,z)$ functional form fixed
and sweeping $K_d$ against the deep-sensor RMSE. The retrieval yields

- $K_{d,\text{A15}}^{*} = 4.60^{+2.36}_{-0.42}$ mW m⁻¹ K⁻¹
- $K_{d,\text{A17}}^{*} = 7.08^{+0.99}_{-0.92}$ mW m⁻¹ K⁻¹

(95% non-parametric bootstrap, $N_\text{boot}=1500$, conditional on the
Langseth et al. (1976) basal heat fluxes; inter-site contrast median 2.31,
95% CI [-0.12, 3.56] — includes zero, so the contrast is marginal —
p ≈ 0.031). The forward model is solved to a certified periodic steady
state (see `code/src/lunar/equilibrium.py` and `documents/notes/FLAG_REPORT.md`).

These per-site values reduce the meter-scale-sensor RMSE relative to the
published global $K_d = 3.4$ (halving it at Apollo 17) and supply the
meter-scale $T(z)$ boundary condition needed by sub-surface
radiative-transfer retrievals.

## Reproducing the paper

The full reproduction recipe is in
[`documents/notes/REPRODUCING.md`](documents/notes/REPRODUCING.md).
There is a `Makefile` with one-word entry points — run `make help` to list
them. Short version:

```bash
git clone https://github.com/rp3gregorio/Lunar-HFE.git
cd Lunar-HFE
python3 -m venv .venv && source .venv/bin/activate
make install                 # editable install of the `lunar` package + dev deps
python code/pipeline/fetch_diviner.py  # ~310 MB from PDS-Geosciences (one-time)

make retrieve                # core retrieval + bootstrap  -> code/results/*.json
make aux                     # all sensitivity sweeps, model selection, MCMC, closure
make figures                 # regenerate every figure (paper + guidebook) -> figures/
make paper                   # compile all PDFs
# or simply:  make all
```

Prefer notebooks? `jupyter lab code/notebooks/` and run the seven in order
— but note the notebooks are **demonstrations**, not the source of truth:
every published number comes from the `code/pipeline/` scripts via `make`,
which is what reviewers should run. Each file under
`code/pipeline/compute/` and `code/pipeline/figures/` runs standalone.

### For reviewers: how it all runs, in five commands

```bash
make install                                 # editable install into .venv
.venv/bin/python -m pytest -q                # 49 tests (physics invariants + fast path)
make retrieve                                # headline K_d* + bootstrap -> code/results/*.json
make figures && make paper                   # figures + all PDFs (letter, guidebook, thesis, ...)
clang++ -O3 -std=c++17 -o code/cpp/lunar_solver code/cpp/solver.cpp \
  && .venv/bin/python code/pipeline/compute/benchmark_cpp.py   # C++ <-> Python to ~1e-12 K
```

Data flows one way: `code/data/` (inputs) → `code/pipeline/compute/`
(writes `code/results/*.json`) → `code/pipeline/figures/` (writes
`figures/`) → the documents (via each document’s local `figures/` link).
Figures never compute physics; documents never hold hand-typed numbers.
To restyle any figure without touching logic, see
`documents/notes/FIGURE_STYLING.md` and the self-serve knobs
in `code/src/lunar/plotting/style_overrides.py`.

### How the code is organised (start here)

All configuration and the physics engine live in the **`code/src/lunar/` package**;
the **`code/pipeline/`** scripts are thin command-line drivers that call it. There is
exactly one definition of everything:

| Where | What |
|---|---|
| `code/src/lunar/config.py` | **single source of truth** — site table (`SITES`), grid, Hayne bundle, solver + sweep settings |
| `code/src/lunar/constants.py` | cited physical constants |
| `code/src/lunar/properties.py` | conductivity / density / specific-heat models |
| `code/src/lunar/grid.py`, `solver.py`, `equilibrium.py` | the 1-D heat-equation engine |
| `code/src/lunar/plotting/style.py` | shared figure palette + layout helpers |
| `code/pipeline/compute/` | retrieval, bootstrap, sensitivity sweeps, MCMC (write `code/results/*.json`) |
| `code/pipeline/figures/` | figure generators; `code/pipeline/make_all_figures.py` runs them all |

New to the code? Two guides, by purpose:

- **[`documents/dev/CODE_TOUR.md`](documents/dev/CODE_TOUR.md)** — how the *repository* works:
  the four layers, who calls whom, a walkthrough of one number from raw data
  to the manuscript, and "how do I…?" recipes. Start here.
- **[`documents/jgr/guidebook/`](documents/jgr/guidebook/)** (`guidebook.pdf`; rebuild with
  `make paper`) — how the *physics and statistics* work, taught from zero.

Then run the seven notebooks in order (chronological — you meet the solver in
`02` before the retrieval that uses it in `03`):

| Notebook | Produces |
|---|---|
| `00_setup.ipynb` | Dependency check, data integrity check |
| `01_methods.ipynb` | Figs 1–3 & 5, Table 1 (parameters) |
| `02_anchor_method.ipynb` | The flux-anchored solver, explained + animated (letter Fig. 4; brute force = fast solve) |
| `03_retrieval.ipynb` | Per-site $K_d^*$ retrieval, bootstrap CIs, error budget |
| `04_results.ipynb` | Figs 6–9 & 12 (mean-T, $K_d$ sweep, bootstrap, thermal profiles, Diviner closure), Tables 2–3 |
| `05_discussion.ipynb` | Figs 10–11 (robustness, Martínez α-sweep), Tables 4–5 |
| `06_performance.ipynb` | The solver kernel in C++ — Python/Numba/C++ agree, the speedup, then the $K_d$ retrieval run live with a tqdm progress bar |

Run `03_retrieval.ipynb` before `04`/`05` — they read the JSON it writes.

Each notebook is idempotent: re-running it overwrites the corresponding
figures and any JSON it produces in `code/results/`. The canonical retrieval JSON
([`code/results/kd_retrieval_results.json`](code/results/kd_retrieval_results.json)) is committed for
direct verification.

## Repository layout

Three folders at the top level — `documents/` (what you read, grouped by
venue), `figures/` (every shared graph, one copy), and `code/` (the engine +
inputs). See `STRUCTURE.md` for the full map.

```
Lunar-HFE/
├── documents/                  # WHAT YOU READ (grouped by venue)
│   ├── jgr/                    # JGR:Planets
│   │   ├── letter/             #   the manuscript (LaTeX + PDF)
│   │   └── guidebook/          #   the teach-from-zero companion
│   ├── gedes/                  # GEDES symposium
│   │   ├── abstract/           #   the extended abstract (self-contained figures/)
│   │   └── thesis/             #   the PhD thesis manuscript
│   ├── aogs/                   # AOGS conference (self-contained bundle)
│   │   └── docs/  code/  data/  figures/  results/
│   ├── slides/  notes/         # progress deck; REPRODUCING/FLAG/audit notes
│   └── <jgr|gedes>/<doc>/figures -> ../../../figures   # link into the shared figure folder
├── figures/                    # EVERY SHARED FIGURE (one physical copy)
│   ├── *.pdf   anim/   _archive/
├── code/                       # THE ENGINE (logic + inputs, no figures)
│   ├── src/lunar/              # 1-D heat solver + conductivity models
│   ├── pipeline/{compute,figures}/   # sweeps -> code/results/*.json; generators -> figures/
│   ├── cpp/  tests/  notebooks/
│   ├── data/  references/      # INPUTS: apollo/diviner/spice records; cited-paper PDFs
│   └── results/                # OUTPUTS: canonical *.json (figures now live in figures/)
└── README.md  Makefile  pyproject.toml  STRUCTURE.md  LICENSE
```

The JGR and GEDES manuscripts reach shared figures through a `figures/` symlink
to the top-level `figures/`, so there is exactly one physical copy of each; the
GEDES abstract and AOGS poster are self-contained (each keeps its own `figures/`).

## Citing this work

If you use this code or data, please cite both the paper and the repository:

```bibtex
@article{gregorio2026,
  author  = {Gregorio, R.~P. and Larsson, R. and Yamada, T. and Kuroda, T. and Kasai, Y.},
  title   = {Difference of Lunar Regolith Thermal Conductivity $K_d$
             at the Apollo 15 and 17 Heat-Flow Boreholes},
  journal = {Journal of Geophysical Research: Planets},
  year    = {2026},
  doi     = {TBD}
}
```

`CITATION.cff` is provided for GitHub's automatic citation widget.

## Licenses

- **Code** (`code/src/lunar/`, `code/pipeline/`, `code/tests/`, `code/notebooks/`): MIT License
  (see [`LICENSE`](LICENSE))
- **Paper text, figures, and tabular results** (`documents/`, `figures/`):
  Creative Commons Attribution 4.0 International (CC-BY-4.0)
  (see [`LICENSE-CC-BY-4.0`](LICENSE-CC-BY-4.0))
- **Bundled HFE data** (`code/data/apollo/`): public domain via NASA PDS-Geosciences
  (Nagihara et al. 2018 release)

## Contact

R. P. Gregorio · `rp3gregorio@gmail.com`
Kasai Laboratory, Institute of Science Tokyo
