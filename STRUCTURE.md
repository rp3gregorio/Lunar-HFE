# Repository structure

Four folders at the top level, each with one job:

| Folder | What it holds |
|---|---|
| **`documents/`** | everything you read — the manuscripts |
| **`figures/`** | every generated figure, in one place |
| **`code/`** | the engine — the `lunar` package, the pipeline, tests, and data inputs |
| **`aogs/`** | the AOGS conference work, fully self-contained |

Config files sit at the root. There is exactly **one physical copy of every
figure** (in `figures/`); documents reach it through a local `figures/` link.

```
Lunar-HFE/
│
├── documents/                 ← WHAT YOU READ
│   ├── letter/                the JGR:Planets letter (letter.tex, letter_clean.tex,
│   │                          supporting_information.tex, references.bib)
│   ├── guidebook/             the teach-from-zero companion (+ figures-tikz/ sources)
│   ├── thesis/                the PhD thesis
│   ├── abstract/              the GEDES symposium abstract
│   ├── notes/  slides/        audit trails, talk material
│   ├── CODE_TOUR.*            a walk-through of the codebase
│   └── <doc>/figures  → ../../figures   (local link into the one figure folder)
│
├── figures/                   ← EVERY GENERATED FIGURE (one physical copy)
│   ├── *.pdf                  the letter/guidebook/thesis/abstract graphs
│   ├── anim/                  the GIFs + filmstrips
│   └── _archive/              retired figures kept for reference
│
├── code/                      ← THE ENGINE (logic + inputs, no figures)
│   ├── src/lunar/             the importable package (solver, equilibrium,
│   │                          properties, grid, config, plotting/style …)
│   ├── pipeline/              scripts that USE the package
│   │   ├── compute/           retrieval, bootstrap, MCMC, error budget
│   │   ├── figures/           every letter/guidebook/thesis figure generator
│   │   └── make_all_figures.py   JOBS registry ("make figures")
│   ├── cpp/  tests/  notebooks/
│   ├── data/                  INPUTS: Apollo HFE, Diviner, SPICE records
│   ├── references/            INPUTS: cited-paper PDFs (anti-hallucination)
│   └── results/               OUTPUTS: *.json only (figures now live in figures/)
│
├── aogs/                      ← THE AOGS BUNDLE (self-contained)
│   ├── poster/                aogs_poster.tex + its figures/ + poster_numbers.tex
│   ├── code/                  compute/ (s1…s8), the poster + K_d-bowl generators,
│   │                          08_aogs_study.ipynb — all import `lunar` from code/
│   ├── results/              the aogs_*.json outputs + shadowing_algorithm.gif
│   ├── data/lola/            the LOLA DEM (AOGS-only input)
│   ├── talk_figures/  briefing/
│   └── README.md
│
└── README.md  Makefile  pyproject.toml  STRUCTURE.md  CLAUDE.md  LICENSE*
```

## Where figures live (important)

Every figure has **one** physical copy, in the top-level **`figures/`** folder.
Each document reaches it through a local symlink:

```
documents/letter/figures     -> ../../figures
documents/guidebook/figures   -> ../../figures
documents/thesis/figures       -> ../../figures
documents/abstract/figures      -> ../../figures
documents/thesis/references.bib  -> ../letter/references.bib
```

**Consequence:** to change a figure, edit its generator in
`code/pipeline/figures/` and re-run it — every generator writes **only** to the
top-level `figures/` folder, so every document updates at once and moving or
renaming a document can never break a generator. (AOGS figures are the one
exception: they are AOGS deliverables and live under `aogs/`, written by the
generators in `aogs/code/`.)

## How the code finds its own root

`lunar._bootstrap.find_repo_root()` recognises the umbrella layout and returns
`code/` (the directory holding `src/`, `data/`, `results/`). Figure generators
write to `find_repo_root().parent / "figures"` (the top-level folder); the AOGS
scripts additionally use `AOGS = find_repo_root().parent / "aogs"` for their own
artifacts. The Python package is installed editable via `pyproject.toml`
(`package-dir = code/src`); `pytest` runs `testpaths = code/tests`.

## House rules (see CLAUDE.md and the lunar-* skills)

- **Numbers match code:** every value in a document traces to
  `code/results/*.json`; never hand-edit a figure or manuscript number.
- **One figure home:** never copy a figure into a document folder; use the
  existing `figures/` link.
- **Cleanup + verify:** after any tidy-up, prove the code still runs and every
  document still compiles.
