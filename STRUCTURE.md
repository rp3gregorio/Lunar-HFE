# Repository structure

This repository is **code only**. Three folders at the top level, each with one
job:

| Folder | What it holds |
|---|---|
| **`code/`** | the engine — the `lunar` package, the pipeline, tests, and data inputs |
| **`figures/`** | every shared generated figure, in one place |
| **`documents/`** | how the code works and how to re-run it (notes + developer tour) |

Config files sit at the root. There is exactly **one physical copy of every
shared figure**, in `figures/`.

The **manuscripts are not here.** The JGR letter and guidebook, the GEDES
abstract / thesis / defense deck, the AOGS poster and the slide decks live in a
separate document set outside the repository (see below), so what gets pushed
to GitHub stays strictly the code and the artifacts needed to reproduce it.

```
Lunar-HFE/
│
├── code/                      ← THE ENGINE (logic + inputs, no manuscripts)
│   ├── src/lunar/             the importable package (solver, equilibrium,
│   │                          properties, grid, config, plotting/style …)
│   ├── pipeline/              scripts that USE the package
│   │   ├── compute/           retrieval, bootstrap, MCMC, error budget
│   │   ├── figures/           every letter/guidebook/thesis figure generator
│   │   └── make_all_figures.py   JOBS registry ("make figures")
│   ├── cpp/  tests/  notebooks/
│   ├── data/                  INPUTS: Apollo HFE, Diviner, SPICE records
│   ├── references/            INPUTS: cited-paper PDFs (anti-hallucination, gitignored)
│   └── results/               OUTPUTS: *.json (+ bayesian_chains.npz, archive/)
│
├── figures/                   ← EVERY SHARED FIGURE (one physical copy)
│   ├── *.pdf                  the letter / guidebook / thesis / abstract graphs
│   ├── anim/                  the GIFs + filmstrips
│   └── _archive/              retired figures kept for reference
│
├── documents/                 ← HOW THE CODE WORKS (not the manuscripts)
│   ├── notes/                 REPRODUCING.md, FLAG_REPORT.md, error-budget
│   │                          provenance, Numba-vs-C++ justification, audits
│   └── dev/                   CODE_TOUR (md/tex/pdf) + wrap-step notes
│
└── README.md  Makefile  pyproject.toml  STRUCTURE.md  CITATION.cff  LICENSE*
```

## The document set (outside this repository)

The manuscripts live at `$LUNAR_DOCS`, by default `~/Documents/Lunar-HFE/`:

```
jgr/letter/  jgr/guidebook/
gedes/abstract/  gedes/thesis/  gedes/defense/
aogs/            slides/          overleaf/
```

That tree reaches back into this repository through six symlinks — a `code`
link (so `find_repo_root()` and the AOGS scripts still locate the `lunar`
package), three `figures` links, `references.bib`, and `aogs/data/lola`. Its
own `Makefile` provides `make paper` and a `make check` that verifies every
bridge is alive. `make paper` in *this* repo delegates to it.

## Where figures live (important)

Every shared figure has **one** physical copy, in the top-level **`figures/`**
folder. The JGR and GEDES manuscripts reach it through a symlink:

```
$LUNAR_DOCS/jgr/letter/figures         -> <repo>/figures
$LUNAR_DOCS/jgr/guidebook/figures      -> <repo>/figures
$LUNAR_DOCS/gedes/thesis/figures       -> <repo>/figures
$LUNAR_DOCS/gedes/thesis/references.bib -> ../../jgr/letter/references.bib
```

The **GEDES abstract** and the **AOGS poster** are self-contained instead —
each keeps its own `figures/` folder at its own printed width, so it carries
its graphics with it. The abstract's generator honours `$LUNAR_DOCS`:

```bash
LUNAR_DOCS=~/Documents/Lunar-HFE .venv/bin/python code/pipeline/figures/make_abstract_figures.py
```

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

- **Code and manuscripts stay separated:** never move a `.tex` manuscript back
  into this repository, and never copy a shared figure out of `figures/`.
- **Numbers match code:** every value in a document traces to
  `code/results/*.json`; never hand-edit a figure or manuscript number.
- **One figure home:** never copy a shared figure into a document folder; use
  the existing `figures/` link.
- **Cleanup + verify:** after any tidy-up, prove the code still runs and every
  document still compiles.
