# AOGS study — compute pipeline (in run order)

The DEM-shadowing + discrete-density study for the AOGS poster. Files are
**numbered by the order the process runs** (`s1 … s8`); each writes one
`code/results/aogs_*.json` (the JSON names are NOT numbered — only the scripts).
They import each other by these stage names, so keep them co-located here.

Run from anywhere in the repo (each resolves `src/` and its siblings itself):

| # | script | consumes | produces | ~time |
|---|--------|----------|----------|-------|
| s1 | `s1_sensitivity.py` | LOLA DEM, HFE sensors | `aogs_sensitivity.json` — horizons, shadowed forcing, first density sweep. **Base module**: `load_dem`, `horizon_profile`, `shadowed_insolation`, `sun_track`. | ~10 min |
| s2 | `s2_density_study.py` | s1 (forcing) | `aogs_density_study.json` — 650 configs (swept boundaries × cp/coupled). Defines `rho_layered`, `K_coupled`. | ~45 min |
| s3 | `s3_kd_shadowed.py` | s1 | `aogs_kd_shadowed.json` — K_d retrieval under shadowed forcing. | ~5 min |
| s4 | `s4_kd_shadowed_extend.py` | s1, s3 | extends the K_d grids in `aogs_kd_shadowed.json` to the physical bounds. | ~3 min |
| s5 | `s5_crossite.py` | s2 (winners) | `aogs_crossite.json` — homogeneous baseline + cross-site transfer. | ~5 min |
| s6 | `s6_svf_terms.py` | s2 (winners) | `aogs_svf_terms.json` — (1−SVF) terrain-radiation channels. | ~2 min |
| s7 | `s7_winner_bootstrap.py` | s2 (stored T) | `aogs_winner_bootstrap.json` — winner stability (10k draws, zero new solves). | <1 min |
| s8 | `s8_wave.py` | s1 | `aogs_wave.json` — diurnal-wave decay diagnostic. | ~2 min |

**Then** `../../figures/make_poster_figures.py` reads the JSONs → the poster
panels + `poster_numbers.tex`; `../../figures/make_explainer_kd_bowl.py` → the
briefing's K_d bowl. Notebook `code/notebooks/08_aogs_study.ipynb` is the
interactive front end (imports `s2_density_study`).

Dependency order is also the numeric order: every `sN` only imports `s<N`.
