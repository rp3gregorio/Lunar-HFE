# GEDES extended abstract — Overleaf bundle

Self-contained LaTeX for the GEDES extended abstract (based on
`GEDESabstract_sampleFormat_en.docx`).

## Format
The GEDES template is **A4, two-column body** under a full-width title
band, Times 10 pt, margins 25 mm top/bottom / 20 mm sides, column gap
21 pt, **4 pages maximum**. EVERYTHING sits inside one column
(single-column `figure`/`table`, no `figure*`/`table*`). Six figures:
context globe; the full-detail 4-probe HFE timeline (`fig_apollo_timeline`,
the letter's figure) scaled to column width (labels small but complete);
the flux-anchored-solver schematic (`fig_method`); the RMSE-vs-K_d sweep
with the legend inside; the subsurface T(z) fit (`fig_profile_fit`, data
vs the Hayne and Martinez-Siegler models — runs the solver, ~90 s);
robustness (bootstrap + contrast map stacked). Table 1 is `\footnotesize`
with abbreviated headers. The file currently fills 4 pages.

## Upload to Overleaf
Upload just these two things (everything is relative, no symlinks):

```
gedes_abstract.tex
figures/                 # fig_context_map, fig_apollo_timeline,
                         # fig_kd_sweep, fig_robustness  (real PDFs)
```

Then set the Overleaf compiler to **pdfLaTeX**. Times/newtx ships with
Overleaf, so it builds as-is. (You do not need the `.aux`/`.log`/`.pdf`
or the `.docx` template — leave them out of the upload.)

## Before submitting
Fill the two placeholders near the top of `gedes_abstract.tex`:
`[TODO: student number]` and `[TODO: supervisor name]`.

## Refreshing the figures from the pipeline
The four PDFs in `figures/` are NOT copies of the letter figures — they
are rebuilt by the pipeline at the abstract's true printed size
(A4 text width, 6.69 in), so fonts stay readable at 100%. The timeline
variant shows only the deepest probe per site. To regenerate after any
pipeline re-run, from the repo root:

```bash
.venv/bin/python code/pipeline/figures/make_abstract_figures.py
```

The canonical letter/guidebook figures in `code/results/figures/` are
never touched by this script.

**Figure 1 data layers** (all real / model-derived, nothing invented):
(a) Clementine albedo mosaic `code/results/figures/moon_global.png`;
(b) modeled noon radiative-equilibrium surface temperature from the
paper's own constants (`lunar.constants`, nominal Apollo albedo);
(c) LOLA topography `code/data/lola/ldem_4.img` (LRO LOLA LDEM, 4
pixels/deg, from PDS Geosciences — the same host as the Diviner data).
If `ldem_4.img` is missing, re-fetch it:

```bash
curl -k -o code/data/lola/ldem_4.img \
  https://pds-geosciences.wustl.edu/lro/lro-l-lola-3-rdr-v1/lrolol_1xxx/data/lola_gdr/cylindrical/img/ldem_4.img
```

Numbers in the text are the certified 2026-07-06 set; never hand-edit a
value — re-derive from `code/results/*.json`.
