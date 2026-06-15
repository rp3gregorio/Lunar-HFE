# Code Manual — how the Lunar-HFE codebase fits together

A developer's map of the repository: what each module does, **what imports
what**, how data flows from raw Apollo records to the figures in the paper,
and where to change things. Read this once and you can navigate the whole
codebase. (For the *science*, see `paper/primer/guidebook.tex`; this
document is about the *code*.)

---

## 1. The big picture: three layers

The code is layered, and dependencies only ever point **downward**:

```
   paper/         letter.tex, guidebook.tex   (consume figures + numbers)
        ▲
   scripts/       thin command-line drivers     (compute, then draw)
        ▲              │
        │              ▼
   lunar/         the package: engine + config + style   (no upward deps)
```

- **`lunar/`** is the installable package — the physics engine, the single
  configuration, and the shared plotting style. It imports nothing from
  `scripts/`.
- **`scripts/`** are thin drivers. `scripts/pipeline/` computes results
  (writes `output/*.json`); `scripts/figures/` reads those JSONs and draws
  PDFs.
- **`paper/`** consumes the figures and the committed numbers.

**Golden rule:** if you find yourself importing *sideways* (a pipeline
script importing a figure script, or two figure scripts importing each
other) for anything other than a genuine figure function, it belongs in
`lunar/` instead. That sideways tangle was the old source of confusion and
has been removed.

---

## 2. The `lunar/` package, module by module

| Module | What it provides | Imports (within lunar) |
|---|---|---|
| `constants.py` | Every cited physical number: σ, K_s, K_d, H, χ, densities, c_p and Martínez coefficients. | — |
| **`config.py`** | **Single source of truth** for run config: `SITES`, `GRID`, `HAYNE`, `S0`, `T_LUNAR`, `DT_STEP`, equilibrium settings (`EQ_*`), `KD_GRIDS`, `DEPTH_SIGMA_CM`, 3-layer params (`TL_*`). | `constants` |
| `grid.py` | `make_geometric_grid()` → `DepthGrid` (the thin-at-top depth mesh). | `constants` |
| `properties.py` | The material models: `conductivity_hayne`, `conductivity_martinez`, `density_hayne`, `specific_heat` (+ ice variants). | `constants` |
| `solver.py` | The 1-D heat-equation engine: `PixelInputs`/`PixelOutputs`, `solve_pixel`, the Crank–Nicolson step `_step`, the tridiagonal `_thomas`, the surface energy balance + Newton iteration. | `constants`, `grid`, `properties` |
| `equilibrium.py` | `solve_periodic_equilibrium()` — the flux-anchored settled-state solver (the F1 fix). | `grid`, `solver` |
| `apollo_helpers.py` | `extract_sensor_stability()`, `find_stable_window()` — turn raw HFE records into one settled temperature per sensor. | `validation` |
| `validation.py` | `load_apollo_hfe_depth()` — read the bundled depth tables. | — |
| `ephem.py` | SPICE solar geometry (`et_from_iso`, `solar_elevation_azimuth`, …). Used for geometry checks; the retrieval itself uses idealized cosine forcing. | (spiceypy) |
| `diviner.py` | Diviner GCP loading (`load_gcp_band`, `select_diurnal_curve`). | — |
| `plotting/style.py` | Shared figure palette (`C_A15`, `C_A17`, …), rcParams, `fmt_axis`, `legend_below`. | (matplotlib) |
| `_bootstrap.py` | `ensure_lunar` / `ensure_apollo_hfe` — dependency + data checks run at the top of scripts. | — |

### The dependency graph inside `lunar/`

```
constants ─┬─► config
           ├─► grid ─────┐
           ├─► properties┤
           │             ▼
           │           solver ──► equilibrium
validation ──► apollo_helpers
(matplotlib) ─► plotting/style
```

Nothing here imports a script. You can `import lunar.<module>` from
anywhere.

---

## 3. The physics → number → figure flow

This is the path a result travels, end to end:

```
 lunar.config  +  lunar.constants
        │  (SITES, grid, Hayne params)
        ▼
 lunar.properties  ── K(T,z), ρ(z), c_p(T)
        │
        ▼
 lunar.grid ─► lunar.solver ─► lunar.equilibrium      ← the forward model
        │
        ▼
 scripts/pipeline/retrieve_kd.py : run_with()         ← one settled profile
        │   sweep K_d, bootstrap, joint (K_d,H), hold-outs
        ▼
 output/kd_retrieval_results.json   (the canonical result file)
        │
        ├─► other scripts/pipeline/*.py  ─►  output/*.json
        │       (headline RMSE, sensitivities, model selection,
        │        error budget, Bayesian MCMC, Diviner closure)
        ▼
 scripts/figures/*.py   (read output/*.json, draw with lunar.plotting.style)
        ▼
 paper/letter/figures/*.pdf   ─►   paper/letter/letter.tex
```

**`run_with()` in `retrieve_kd.py` is the heart**: give it a site config and
a trial `K_d`, it builds the grid, the forcing, and the chosen conductivity
model, runs `solve_periodic_equilibrium`, and returns the settled
mean-temperature profile. Everything else (sweeps, bootstrap, sensitivities,
figures) calls `run_with`.

---

## 4. `scripts/` — who calls whom

### `scripts/pipeline/` (compute → JSON)

| Script | Reads | Writes | Imports |
|---|---|---|---|
| **`retrieve_kd.py`** | bundled HFE data | `kd_retrieval_results.json`, `fig_bootstrap/robustness.pdf`, `output/figures/fig_holdout.pdf` | `lunar.*`, `lunar.config`, `lunar.plotting.style`, and `make_results_figures` (only `fig_bootstrap`, `fig_robustness`) |
| `compute_headline_rmse.py` | data | `headline_rmse.json` | `retrieve_kd` (`run_with`, `kd_star_from_residuals`) |
| `compute_borestem_sensitivity.py` | data | `borestem_sensitivity.json` | `retrieve_kd` |
| `compute_stability_threshold_sensitivity.py` | data | `stability_threshold_sensitivity.json` | `retrieve_kd` |
| `compute_surface_bias_test.py` | data | `surface_bias_test.json` | `retrieve_kd` |
| `compute_uniform_kd_sensitivity.py` | data | `uniform_kd_test.json` | `retrieve_kd` |
| `compute_fixed_input_sensitivities.py` | data | `fixed_input_sensitivities.json` | `retrieve_kd`, `lunar.config` |
| `compute_model_selection.py` | `kd_retrieval_results.json` | `model_selection.json` | `retrieve_kd` |
| `compute_error_budget.py` | several JSONs above | `kd_error_budget.json` | (reads JSON only) |
| `bayesian_crosscheck.py` | `kd_retrieval_results.json` | `bayesian_crosscheck_samples.json`, `output/figures/fig_kd_qb_posterior.pdf` | `emcee`, `lunar.plotting.style` |
| `compute_diviner_closure.py` | `kd_retrieval_results.json` + GCP | `diviner_closure.json`, `fig_diviner_closure.pdf` | `retrieve_kd`, `lunar.*` |

**Key point:** every `compute_*` script imports the engine through
`retrieve_kd` (which in turn re-exports the single `lunar.config.SITES`), so
they all share one configuration automatically.

### `scripts/figures/` (JSON → PDF)

All import `lunar.plotting.style` for the palette and `lunar.config` for
`SITES`; the ones that need a forward run import `retrieve_kd.run_with`.

| Script | Produces |
|---|---|
| `make_intro_figures.py` | Fig 1 (probe schematic) |
| `make_context_map_figure.py` | Fig 2 (landing-site map) |
| `make_apollo_timeline.py` | Fig 3 (stability-window timeline) |
| `make_letter_figures.py` | Figs 4–6 (amplitude, mean-T, K_d sweep) |
| `make_results_figures.py` | Figs 7–8 + the bootstrap/robustness helpers |
| `make_alpha_sweep_figure.py` | Fig 9 (Martínez α-sweep) |
| `make_book_figures.py` / `make_primer_figures.py` | the guidebook teaching figures |
| `make_equilibrium_certification.py` | solver-certification figure (→ `output/figures/`) |
| **`make_all_figures.py`** | runs all of the above, timed (`make figures`) |

---

## 5. Where do I change…? (cookbook)

| I want to change… | Edit only… |
|---|---|
| a site's albedo, basal flux, latitude | `lunar/config.py` → `SITES` |
| the depth grid, time step, or spin-up settings | `lunar/config.py` (`GRID`, `DT_STEP`, `EQ_*`) |
| a physical constant (σ, K_s, χ, densities…) | `lunar/constants.py` |
| the conductivity / density / c_p formula | `lunar/properties.py` |
| how the heat equation is stepped | `lunar/solver.py` |
| the settled-state algorithm | `lunar/equilibrium.py` |
| figure colours / fonts / layout helpers | `lunar/plotting/style.py` |
| the K_d sweep range | `lunar/config.py` → `KD_GRIDS` |
| add a new figure | add a function in a `scripts/figures/` module, then register it in `scripts/make_all_figures.py` |

Because configuration is single-sourced, a change in `lunar/config.py`
propagates to the retrieval, every sensitivity script, and every figure at
once — no hunting for copies.

---

## 6. Running it

```bash
make install     # editable install of the lunar package + dev deps
make retrieve    # core retrieval + bootstrap  -> output/kd_retrieval_results.json
make aux         # all sensitivity sweeps, model selection, MCMC, Diviner closure
make figures     # regenerate every figure
make paper       # compile the letter + guidebook PDFs
make test        # the pytest suite (37 tests)
make all         # everything, from scratch
```

Each script is also runnable standalone (`python scripts/pipeline/retrieve_kd.py`),
and the five `notebooks/` walk the same pipeline interactively.

---

## 7. A note for the planned C++ port

The Python layout is deliberately a clean reference for a future C++
version: the numerics live in three small, self-contained modules
(`grid.py`, `solver.py`, `equilibrium.py`) with no plotting or I/O mixed in,
fed by a single `config.py`. Port those three first; keep `config.py` as the
single parameter file the C++ side also reads; leave the analysis
(`scripts/pipeline/`) and figures in Python calling the fast core.
