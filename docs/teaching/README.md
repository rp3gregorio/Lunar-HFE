# Beginner's Guide — LaTeX teaching handbook

This folder is a **self-contained LaTeX project** that turns
`docs/BEGINNERS_GUIDE.md` into a polished, illustrated PDF handbook for someone
with no coding or physics background. It is ready to upload to
[Overleaf](https://www.overleaf.com) as-is.

## Contents

```
docs/teaching/
├── beginners_guide.tex      # main document (compile this one)
├── sections/                # one .tex per chapter, pulled in via \input
│   ├── 01_bigpicture.tex
│   ├── 02a_notation.tex     # complete symbol reference (tables)
│   ├── 02_physics.tex
│   ├── 02b_orbit_top_bc.tex # orbital forcing + top BC TikZ figures
│   ├── 03_numerics.tex
│   ├── 04_anchor.tex
│   ├── 05_retrieval.tex
│   ├── 06_codetour.tex
│   ├── 07_running.tex
│   ├── 08_glossary.tex
│   └── 09_roadmap.tex
├── figures/                 # all figure assets (PNG + PDF)
├── make_teaching_figures.py # regenerates the computed figures
└── README.md                # this file
```

All graphics are referenced with **relative paths** via
`\graphicspath{{figures/}}`, so the project compiles with no external
dependencies.

## Compile locally

You need a TeX distribution (TeX Live / MacTeX). From inside this folder:

```bash
latexmk -pdf -interaction=nonstopmode beginners_guide.tex
```

This produces `beginners_guide.pdf`. To clean up auxiliary files:

```bash
latexmk -c
```

The document uses only packages that ship with a standard TeX Live install
(`geometry`, `amsmath`, `siunitx`, `booktabs`, `graphicx`, `xcolor`,
`tcolorbox`, `listings`, `tikz`, `hyperref`). It deliberately uses **`listings`**
(not `minted`) so that **no `-shell-escape` flag is required** — important for
Overleaf compatibility.

## Upload to Overleaf

1. Zip this folder:

   ```bash
   cd docs && zip -r teaching.zip teaching
   ```

2. In Overleaf choose **New Project → Upload Project** and select `teaching.zip`.
3. In **Menu → Settings**, set:
   - **Compiler:** pdfLaTeX
   - **Main document:** `beginners_guide.tex`
4. Click **Recompile**. The PDF builds with the table of contents, all figures,
   and clickable cross-references.

## Regenerating the figures

The five computed figures (`fig_skin_depth`, `fig_mean_profile`,
`fig_conductivity`, `fig_kd_retrieval`, `fig_bootstrap`) are produced by
`make_teaching_figures.py`, which only *imports* the existing `lunar` package
APIs and reads the committed `output/kd_retrieval_results.json`. From the
repository root:

```bash
export MPLCONFIGDIR=/tmp/mpl
python3 docs/teaching/make_teaching_figures.py
```

Two further figures (`fig_phase2_depth_convergence`, `fig_phase4_njit_vs_cpp`)
are copies of committed repository figures, included here so the project stays
self-contained. The conceptual diagrams (geometric grid, the two-clock Anchor
Point Method, the data-flow pipeline) are drawn in-document with TikZ and need no
external files.
