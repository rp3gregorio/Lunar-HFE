"""YOUR figure-style knobs — edit this file, re-run a generator, done.

Anything you define here overrides the same name in lunar/plotting/style.py
for EVERY figure. Uncomment a line, change the value, then rebuild the
figure(s) you care about:

    .venv/bin/python code/pipeline/figures/<generator>.py     # one figure
    make figures                                              # everything

The how-to (including the per-figure map of which generator makes which
figure, and where its legend/annotation lines live) is:
    deliverables/documents/notes/FIGURE_STYLING.md

NOTE the no-overlap guard: if you move a legend/label ONTO plotted data,
the build fails on purpose with "TEXT-ON-DATA". Move it to empty space.
"""
import matplotlib.pyplot as plt  # noqa: F401  (available for rcParams below)

# ── font sizes (points) ──────────────────────────────────────────────────────
# FS_BASE   = 10.0      # everything not covered below
# FS_TITLE  = 11.5      # panel titles
# FS_LABEL  = 10.5      # axis labels
# FS_TICK   = 9.5       # tick numbers
# FS_LEGEND = 9.5       # legend text

# ── site / model colors (hex) — keep the semantic roles consistent ──────────
# C_A15   = "#3D6E4A"   # Apollo 15  (forest green)
# C_A17   = "#B85B3A"   # Apollo 17  (coral)
# C_HAYNE = "#2A6478"   # Hayne 2017 global model (teal)

# ── any raw matplotlib setting (fonts, line widths, dpi, ...) ────────────────
# plt.rcParams.update({
#     "font.family": "serif",
#     "lines.linewidth": 2.0,
#     "savefig.dpi": 300,
#     "legend.framealpha": 0.97,
# })
