# Styling the figures yourself (no AI tokens needed)

Every figure is produced by one small Python script (a "generator") that
reads the results JSONs and writes a PDF into `code/results/figures/`.
All documents see that PDF instantly through their `figures/` symlinks.
So the loop is always:

```bash
# 1. edit a knob (global) or a generator (per-figure), then
.venv/bin/python code/pipeline/figures/<generator>.py    # rebuild ONE figure
# or: make figures                                       # rebuild everything
# 2. open the PDF (any doc's figures/ folder or deliverables/figures/)
```

## Global knobs — edit ONE file

`code/src/lunar/plotting/style_overrides.py` — uncomment and change any
line (font sizes, site colors, raw matplotlib settings). It overrides the
house style for every figure. Verified working: setting `FS_LEGEND = 14.0`
there and re-running a generator changes every legend.

## Per-figure edits (legend position, annotations, "text on the graph")

Titles, legends, stat boxes and callouts live in each figure's generator —
search the file for `legend(`, `ax.text(`, or `annotate(` and move/delete
them there. The map for the letter's figures:

| Figure (letter) | Generator in `code/pipeline/figures/` |
|---|---|
| Fig 1 intro probe | `make_intro_figures.py` |
| Fig 2 context map | `make_context_map_figure.py` |
| Fig 3 mission timeline | `make_apollo_timeline_letter.py` |
| Fig 4 amplitude vs depth, Fig 5 mean T profile, Fig 6 K_d sweep | `make_letter_figures.py` |
| Fig 7 bootstrap | `make_results_figures.py` (`fig_bootstrap`) |
| Fig 8 thermal profiles | `make_letter_figures.py` |
| Fig 9 robustness / MCMC map | `make_results_figures.py` (`fig_robustness`) |
| Fig 10 alpha sweep | `make_alpha_sweep_figure.py` |
| Fig 11 prior estimates | `make_prior_estimates_figure.py` |
| Fig 12 Diviner closure | `compute/compute_diviner_closure.py` |

Guidebook/thesis extras: `make_book3d_figures.py` (K(T,z), skin wave),
`make_anchor_*` (method figures), `make_qb_degeneracy_figure.py`,
`make_dt_ladder_figure.py`, `make_sweep_worked_figure.py`; GIFs in
`make_*_animation.py`. TikZ diagrams are LaTeX sources in
`deliverables/documents/guidebook/figures-tikz/` (build with its
`build.sh <name>`).

## About "text in front of the graph"

The house rule is the opposite — **no text may sit on plotted data** —
and it is enforced by a guard: generators call `assert_no_overlap(ax)`
before saving, and the build **fails with `TEXT-ON-DATA ...`** if a
legend/label covers a curve. So:

- If you move a label somewhere that covers data, the rebuild will refuse
  — move it to empty space or outside the axes (`legend_below(...)` /
  `legend_outside(...)` helpers in `lunar/plotting/style.py`).
- If you want a stats box or annotation gone entirely, delete its
  `ax.text(...)`/`annotate(...)` lines in the generator and rebuild.

## If a rebuild errors

- `ModuleNotFoundError` → you used `python3`; use `.venv/bin/python`.
- `TEXT-ON-DATA ...` → your new text position covers a curve; move it.
- Wrong/old numbers in a figure → never hand-edit numbers; they come from
  `code/results/*.json` (re-run the pipeline stage instead).
