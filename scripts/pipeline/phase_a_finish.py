"""Finish Phase A: add Q_b sensitivity + regenerate the two letter figures
that depend on it, plus the held-out figure."""
from __future__ import annotations
import json, sys, pathlib
sys.path.insert(0, '/Users/rp3gregorio/Lunar-V2/scripts')
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

# Load Phase-A results
RES = pathlib.Path('/Users/rp3gregorio/Lunar-V2/output/phase_a_results.json')
d = json.loads(RES.read_text())

# Add Q_b sensitivity (analytical via K_d/Q_b degeneracy on the new K_d*)
# Grid extended down to alpha=0 so the published Saito-reanalysis case
# (alpha_15 = 0.7) sits comfortably inside the panel rather than at the
# left edge of the data extent.
alphas = np.linspace(0.0, 1.3, 27)
g15, g17 = np.meshgrid(alphas, alphas, indexing='ij')
kd15 = d['A15']['kd_star'] * g15
kd17 = d['A17']['kd_star'] * g17
contrast = kd17 - kd15
sigma_c = (d['contrast_bootstrap']['ci_hi'] -
           d['contrast_bootstrap']['ci_lo']) / 4.0
sig = contrast / sigma_c
d['qb_sensitivity'] = dict(
    alpha_grid=alphas.tolist(),
    contrast_grid=contrast.tolist(),
    significance_grid=sig.tolist(),
)

# Save back
RES.write_text(json.dumps(d, indent=2))
print(f"updated {RES}")

# Now regenerate the figures that depend on qb_sensitivity + held-out
LETTER_FIGS = pathlib.Path('/Users/rp3gregorio/Lunar-V2/paper/letter/figures')
APPENDIX_FIGS = pathlib.Path('/Users/rp3gregorio/Lunar-V2/paper/appendix/figures')

from phase2_figures_v2 import fig_bootstrap, fig_robustness     # type: ignore
from phase_a_pipeline import fig_holdout                         # type: ignore

fig_bootstrap(d, LETTER_FIGS / 'fig_bootstrap.pdf')
fig_robustness(d, LETTER_FIGS / 'fig_robustness.pdf')
fig_holdout(d, APPENDIX_FIGS / 'fig_holdout.pdf')
print("done.")
