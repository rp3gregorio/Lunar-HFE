# AOGS 2026 — Discrete-Layer Thermal Modeling with Topographic Shadowing

Everything for the poster *Discrete Layer Thermal Modeling of Lunar Landing Sites
with Topographic Shadowing* (Abstract PS18-A007), organized into three buckets.

```
aogs/
├── figures/     ALL figures, sorted into subfolders. poster_numbers.tex
│                (generated — every quoted number) sits at the root so every
│                document can \input it.
│                  poster/      the poster panels (poster_*.pdf)
│                  diagrams/    TikZ schematics + flowchart + K_d bowl
│                               (aogs_*.{tex,pdf,png}, explainer_kd_bowl.*)
│                  explainers/  the clean SVG explainer set (expl_*.{svg,pdf,png})
│                  drafts/      superseded alternatives (illus_*, opt_*)
│
├── code/        ALL code. compute/ = the s1–s8 pipeline; make_*.py regenerate
│                every figure; 08_aogs_study.ipynb is the study notebook;
│                canva_build/ builds the editable PPTX.
│
├── docs/        ALL documents. The poster (aogs_poster.tex/.pdf, the Canva
│                export Gregorio_AOGS.pdf, aogs_poster_canva_v3.pptx), the
│                briefings (guidebook, master_overview, expert_briefing,
│                study_explainer), findings/backbone .md, and archive/ (old
│                poster versions).
│
├── results/     the 8 aogs_*.json archives (+ shadowing GIF) — code inputs/outputs.
└── data/        LOLA DEM (symlinked to the repo's code/data/lola).
```

## Rebuild
- Figures + numbers: `python code/make_poster_figures.py`  (writes to figures/poster/)
  plus `make_teaching_diagrams.py` + `make_explainer_kd_bowl.py` (→ diagrams/),
  `make_density_sweep_figure.py` (→ poster/), `make_explainers.py` (→ explainers/),
  `make_illustrations.py` + `make_figure_options.py` + `make_shadow_algorithm.py` (→ drafts/)
- Any document: `pdflatex <name>.tex` inside `docs/` (figures resolve via the
  `\graphicspath` subfolders, or explicit `../figures/poster/…` in the poster)

## Ground rules
- Numbers come from `figures/poster_numbers.tex` (generated) — never hand-typed.
- Each generator writes to its own figures/ subfolder; docs read via `\graphicspath`.
- The real physics code (lunar package) lives at the repo's `code/src`; the
  generators find it automatically, so the bundle can be relocated freely.
