# Repository structure

Three folders at the top level, each with one job:

| Folder | What it holds |
|---|---|
| **`documents/`** | everything you read — grouped by venue (JGR / GEDES / AOGS) |
| **`figures/`** | every shared generated figure, in one place |
| **`code/`** | the engine — the `lunar` package, the pipeline, tests, and data inputs |

Config files sit at the root. There is exactly **one physical copy of every
shared figure** (in `figures/`); the JGR and GEDES documents reach it through a
local `figures/` link.

```
Lunar-HFE/
│
├── documents/                 ← WHAT YOU READ (grouped by venue)
│   ├── jgr/                   JGR:Planets
│   │   ├── letter/            letter.tex, letter_clean.tex,
│   │   │                      supporting_information.tex, references.bib
│   │   └── guidebook/         the teach-from-zero companion (+ figures-tikz/ sources)
│   ├── gedes/                 GEDES symposium
│   │   ├── abstract/          the extended abstract (self-contained figures/)
│   │   └── thesis/            the PhD thesis manuscript
│   ├── aogs/                  AOGS conference (self-contained bundle)
│   │   ├── poster/            aogs_poster.tex + its own figures/ + poster_numbers.tex
│   │   ├── code/              the AOGS study scripts (need the LOLA DEM, kept out of git)
│   │   ├── illustrations/  results/  talk_figures/  briefing/
│   │   └── README.md
│   ├── notes/  slides/        audit trails, talk material
│   ├── dev/                   code walk-throughs (CODE_TOUR, CODE_MANUAL) + wrap-step notes
│   └── <jgr|gedes>/<doc>/figures → ../../../figures   (link into the shared figure folder)
│
├── figures/                   ← EVERY SHARED FIGURE (one physical copy)
│   ├── *.pdf                  the letter / guidebook / thesis / abstract graphs
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
│   └── results/               OUTPUTS: *.json only (figures live in figures/)
│
└── README.md  Makefile  pyproject.toml  STRUCTURE.md  LICENSE*
```

## Where figures live (important)

Every shared figure has **one** physical copy, in the top-level **`figures/`**
folder. The JGR and GEDES manuscripts reach it through a local symlink:

```
documents/jgr/letter/figures        -> ../../../figures
documents/jgr/guidebook/figures      -> ../../../figures
documents/gedes/thesis/figures        -> ../../../figures
documents/gedes/thesis/references.bib -> ../../jgr/letter/references.bib
```

The **GEDES abstract** and the **AOGS poster** are self-contained instead —
each keeps its own `figures/` folder, so it carries its graphics with it.

**Consequence:** to change a shared figure, edit its generator in
`code/pipeline/figures/` and re-run it — every generator writes **only** to the
top-level `figures/` folder, so every JGR/GEDES document updates at once and
moving or renaming a document can never break a generator.

## How the code finds its own root

`lunar._bootstrap.find_repo_root()` returns `code/` (the directory holding
`src/`, `data/`, `results/`). Figure generators write to
`find_repo_root().parent / "figures"` (the top-level shared folder). The Python
package is installed editable via `pyproject.toml` (`package-dir = code/src`);
`pytest` runs `testpaths = code/tests`.

## House rules

- **Numbers match code:** every value in a document traces to
  `code/results/*.json`; never hand-edit a figure or manuscript number.
- **One figure home:** never copy a shared figure into a document folder; use
  the existing `figures/` link.
- **Cleanup + verify:** after any tidy-up, prove the code still runs and every
  document still compiles.
