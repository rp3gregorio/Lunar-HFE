# Repository structure

Two umbrellas at the top level: **`deliverables/`** (everything you look at
or read) and **`code/`** (the machinery — logic, code, and inputs). Config
files sit at the root. Nothing is duplicated: figures and animations live in
one physical place and are surfaced into `deliverables/` via symlinks.

```
Lunar-Clean/
│
├── deliverables/               ← WHAT YOU LOOK AT
│   ├── documents/              the manuscripts
│   │   ├── letter/             the JGR:Planets letter (+ references.bib, SI)
│   │   ├── guidebook/          the teach-from-zero companion book
│   │   ├── thesis/             the PhD thesis
│   │   ├── slides/  notes/     talk material, audit trails
│   │   ├── aogs/               ALL AOGS-poster deliverables (poster/, briefing/,
│   │   │                       talk_figures/) — see aogs/README.md
│   │   └── assets/
│   ├── figures/     → code/results/figures   (symlink: the graphs)
│   └── animations/  → code/results/anim       (symlink: the GIFs)
│
├── code/                       ← THE MACHINERY (logic + code + inputs)
│   ├── src/lunar/              the importable package (solver, equilibrium,
│   │                           properties, grid, config, plotting/style …)
│   ├── pipeline/               scripts that USE the package
│   │   ├── compute/            retrieval, bootstrap, MCMC, error budget
│   │   │   └── aogs/           the AOGS study, numbered in run order (s1…s8)
│   │   ├── figures/            every figure/animation generator
│   │   └── make_all_figures.py JOBS registry ("make figures")
│   ├── cpp/  tests/  notebooks/
│   ├── data/                   INPUTS: Apollo HFE, Diviner, SPICE records
│   ├── references/             INPUTS: cited-paper PDFs (anti-hallucination)
│   └── results/                OUTPUTS: *.json, figures/, anim/
│
└── README.md  Makefile  pyproject.toml  STRUCTURE.md  CLAUDE.md  LICENSE*
```

## The figure symlink model (important)

There is **one** physical copy of every figure, in `code/results/figures/`,
and one of every GIF in `code/results/anim/`. Documents and the top-level
`deliverables/` views reach them through **symlinks**:

```
deliverables/figures            -> code/results/figures
deliverables/animations         -> code/results/anim
deliverables/documents/letter/figures     -> ../../../code/results/figures
deliverables/documents/guidebook/figures   -> ../../../code/results/figures
deliverables/documents/thesis/figures       -> ../../../code/results/figures
deliverables/documents/thesis/references.bib -> ../letter/references.bib
```

**Consequence:** to change a figure, edit its generator in
`code/pipeline/figures/` and re-run it — it writes to `code/results/…` and
every document + the `deliverables/` view updates at once. Generators write
**only** to `code/results/`, never through a document folder, so moving or
renaming a document can never break them.

## How the code finds its own root

Scripts locate the machinery root (`code/`) two ways, both of which resolve
to `code/` after this layout:
- most compute paths from their own location: `Path(__file__).parents[2]`
  (from `code/pipeline/{compute,figures}/x.py`) → `code/`;
- `lunar._bootstrap.find_repo_root()` recognises the umbrella layout and
  returns `code/` (the dir holding `src/`, `data/`, `results/`).

The Python package is installed editable via `pyproject.toml`
(`package-dir = code/src`); `pytest` runs `testpaths = code/tests`.

## House rules (see CLAUDE.md and the lunar-* skills)

- **Numbers match code:** every value in a document traces to
  `code/results/*.json`; never hand-edit a figure or manuscript number.
- **One figure home:** never copy a figure into a document folder; use the
  existing `figures/` symlink.
- **Cleanup + verify:** `lunar-organize` (`organize.py scan`,
  `clean-artifacts --apply`, then `verify`) proves the code still runs and
  all three documents still compile after any tidy-up.
