# Lunar-HFE — Code Manual

*How the code works, what each `.py` file does, and how the files connect to
one another.*

This is the **file-level** companion to two other docs:
- [`CODE_TOUR.md`](../../documents/dev/CODE_TOUR.md) — the folder-level walking tour ("who calls whom" at a glance).
- `guidebook/` — the **physics** (derivations, worked examples).

This manual sits in between: it names every module, says what it contributes,
and draws the import graph so you can trace one number from raw Apollo data to
the paper.

---

## 0. The shape of the code, in one breath

The project retrieves the **deep regolith thermal conductivity `K_d`** at the
Apollo 15 and 17 heat-flow boreholes by fitting a 1-D thermal model to the
measured subsurface temperatures. The code is organized as **four layers with
one rule**:

```
data/          raw inputs  (Apollo HFE record, Diviner, SPICE kernels)
   │
   ▼
code/src/lunar/   THE ENGINE   — a pure, importable, tested physics library.
   │                             Knows nothing about JSON files or figures.
   ▼
code/pipeline/    THE EXPERIMENTS — scripts that import the engine, run it,
   │                              and write answers to results/.
   ▼
code/results/     THE RECORD   — canonical *.json numbers.
   │
   ▼
figures/ + documents/   THE OUTPUT — figures drawn from results/, and the
                                     letter / guidebook / abstract that quote them.
```

**The one rule:** dependencies only ever point **downward**. The engine never
imports the pipeline; the pipeline never imports a figure script. This is what
keeps the physics testable in isolation and the results reproducible.

---

## 1. How the engine files connect (the dependency map)

Every module in `code/src/lunar/` and which internal modules it imports
(verified from the source, not guessed):

```
constants ─────────────────────────────────┐  (base: physical constants, SI)
   ▲          ▲            ▲          ▲      │
   │          │            │          │      │
 config     grid       properties   (…)      │
   ▲  ▲       ▲  ▲          ▲                 │
   │  │       │  │          │                 │
   │  └───────┼──┼──────────┼──── solver ─────┘   (config, constants, grid, properties)
   │          │  │          │        ▲
   │          │  │          │        │
   └──────────┴──┴──────────┴─── equilibrium       (solver + config, constants, grid)

validation ──▶ apollo_helpers          (Apollo data loader → sensor extraction)
ephem, diviner, _bootstrap, plotting/style   (leaf helpers: SPICE, Diviner, notebooks, figure style)
```

Read it as: **`constants` is the floor**; `config`, `grid`, `properties`
build on it; **`solver` sits on those four**; **`equilibrium` sits on the
solver**. Nothing points back up — there are no import cycles.

The retrieval script (`pipeline/compute/retrieve_kd.py`) sits *above* the whole
engine and pulls in almost all of it.

---

## 2. The engine, file by file (`code/src/lunar/`)

The engine is the substance. Each entry: **what it contributes**, its **key
public functions**, and **who uses it**.

### `constants.py` — the physical floor
All SI physical constants and default regolith parameters, each with a source
citation in its docstring (σ, S₀, K_s, H, χ, T_ref, the Hayne c_p polynomial,
Martínez coefficients…). **No internal dependencies** — this is the base every
other module builds on. *Rule: never add a number here without a citation.*

### `config.py` — the single source of truth for a run
Everything that used to be copy-pasted across scripts: the per-site table
`SITES` (lat/lon, albedo, `Q_BASAL`), the depth-grid spec `GRID`
(`z_max=5.0 m`, `dz0=0.002 m`, `growth=0.08`), the Hayne parameter bundle
`HAYNE`, the time step `DT_STEP`, and the equilibrium controls
`EQ_Z_ANCHOR=0.55 m`, `EQ_N_INNER=96`.
**Uses:** `constants`. **Used by:** `solver`, `equilibrium`, `retrieve_kd`,
and nearly every compute script. *Import it; never redefine these values.*

### `grid.py` — the geometric depth grid
`make_geometric_grid(...)` builds the non-uniform column (fine 2 mm cells at
the surface, coarsening with depth to 5 m) and returns a frozen `DepthGrid`
dataclass. Uniform spacing is forbidden — it under-resolves the millimetre
diurnal skin. **Uses:** `constants`. **Used by:** `solver`, `equilibrium`, and
every script that builds a column.

### `properties.py` — the material models `K(T,z)`, `ρ(z)`, `c_p(T)`
The temperature/depth-dependent regolith properties. Three conductivity models,
all reachable through `get_conductivity_model(name)`:
- `conductivity_hayne(T, z, Kd, …)` — the baseline `K_c(z)·[1 + χ(T/T_ref)³]`
  (contact asymptote × radiative term). **This is the model the letter uses.**
- `conductivity_martinez(...)` — the Martínez & Siegler `K(T,ρ)` alternative.
- `conductivity_icy(...)` — an icy variant (not used in the letter).
Plus `density_hayne`, `specific_heat`. **Uses:** `constants`. **Used by:**
`solver`, `retrieve_kd`, the C++ benchmark, and the property-sensitivity scripts.

### `solver.py` — **THE CORE: the 1-D heat-equation solver**
Solves `ρ(z)·c_p(T)·∂ₜT = ∂_z(K(T,z)·∂_zT)` by marching in time. This is where
essentially all the compute cost lives. Key functions, inner → outer:
- `_face_harmonic_mean(K)` — conductivity at cell faces (series resistors); `@njit`.
- `_thomas(a,b,c,d)` — the tridiagonal solve; `@njit`. **The innermost hot op.**
- `_solve_surface_newton(...)` — closes the non-linear surface energy balance by Newton.
- `_step(...)` — assembles **one** Crank–Nicolson (θ=0.5) hour and solves it.
- `_march_radiative_hayne(...)` — the `@njit` lunation march that repeats `_step`
  over the diurnal cycle. **This is the loop the C++ port mirrors.**
- `solve_pixel(inputs) -> PixelOutputs` — the public forward-solve entry point:
  run one column forward for N lunations.
- Helpers: `periodic_time_grid`, `standard_insolation`.
**Uses:** `config`, `constants`, `grid`, `properties`. **Used by:**
`equilibrium`, `retrieve_kd`, every benchmark/sensitivity script.

### `equilibrium.py` — **THE METHOD: the flux-anchored steady state**
The project's methodological contribution ("the slope method"). A flux-bottom
column takes thousands of lunations to relax by brute force; this module reaches
the same steady state ~20× faster by anchoring the mean-flux closure below the
rectification zone. Key functions:
- `solve_periodic_equilibrium(...)` — the public entry: the two-stage outer loop.
- `_reconstruct_subskin(...)` — Step B: walk the deep profile down from the anchor
  via the closure ODE `d⟨T⟩/dz = (Q_b − u_rect)/K`.
- `_rectified_flux(...)` — the eddy/rectified flux `u_rect`.
- `_mean_flux_closure(...)` — the convergence criterion `|⟨K∂_zT⟩ − Q_b|/Q_b`.
- `_truncate_grid(...)` — Step A runs only the skin sub-grid (not the deep column).
- `profile_at_time` / `profile_at_local_time` — read T(z) at any phase without re-solving.
**Uses:** `solver`, `config`, `constants`, `grid`. **Used by:** `retrieve_kd`
and the convergence/sensitivity scripts.

### `apollo_helpers.py` — turning the raw record into fit targets
- `extract_sensor_stability(mission, min_depth_cm)` — the workhorse: returns each
  sensor's depth, equilibrium temperature `T_eq`, its scatter, and the `deep_mask`
  (which sensors clear the 80 cm borestem zone and enter the fit).
- `find_stable_window(...)` — picks the trailing quiescent window per sensor.
**Uses:** `validation`. **Used by:** `retrieve_kd` and most compute scripts.

### `validation.py` — the Apollo HFE data loader
Low-level reader for the bundled Apollo 15/17 depth tables (Nagihara et al. 2018
restoration). **Leaf.** **Used by:** `apollo_helpers`.

### `ephem.py` — solar geometry (SPICE)
Lazily loads SPICE kernels to provide (solar elevation, azimuth) time series for
driving the solver from a real ephemeris (the map/pixel mode). **Leaf.**

### `diviner.py` — Diviner GCP surface-temperature access
Reads the Diviner Global Cumulative Product used to validate the surface skin.
**Leaf.** **Used by:** `compute_diviner_closure.py`.

### `plotting/style.py` (+ `style_overrides.py`) — the figure identity
The JGR:Planets rcParams, palette (`C_A15`, `C_A17`, `C_HAYNE`, `WARM_DIVERGE`,
`WARM_SEQ`…), column widths, and helpers (`fmt_axis`, `legend_below`,
`assert_no_overlap`). Importing it applies the house style. Edit
`style_overrides.py` to tweak any knob globally. **Used by:** every figure script.

### `_bootstrap.py` — notebook convenience
`find_repo_root()` and "Run All"-without-setup helpers so a notebook works from a
clean checkout. **Leaf.** **Used by:** the notebooks.

---

## 3. The pipeline (`code/pipeline/`)

Scripts that *use* the engine. They never define physics — they orchestrate it
and write JSON.

### `compute/retrieve_kd.py` — **the orchestrator (start here)**
The main experiment. Reads the HFE record, sweeps `K_d`, finds the best fit per
site, and bootstraps the uncertainty. Writes `results/kd_retrieval_results.json`.
Key functions:
- `run_with(site_cfg, kd=…, …)` — one full model evaluation at a given `K_d`
  (calls `equilibrium.solve_periodic_equilibrium` → compares to the deep sensors).
- `run_kd_sweep_extended(site_cfg, kd_grid)` — the RMSE sweep over the `K_d` grid.
- `kd_star_from_residuals(R, kd_grid)` — the parabolic-vertex fit → `K_d*`.
- `bootstrap_kd_with_depth_uncertainty(...)` — resamples for the 95% CI.
- `main()` — runs both sites end to end.
**Uses:** essentially the whole engine (`apollo_helpers`, `config`, `constants`,
`equilibrium`, `grid`, `properties`, `solver`).

### `compute/` — the auxiliary scripts (each writes one `results/*.json`)
All follow the same shape (import engine → compute → dump JSON). Grouped by job:
- **Sensitivity sweeps** (does `K_d*` hold up?): `compute_borestem_sensitivity`,
  `compute_common_epoch`, `compute_stability_threshold_sensitivity`,
  `compute_surface_bias_test`, `compute_fixed_input_sensitivities`,
  `compute_uniform_kd_sensitivity`.
- **Model comparison**: `compute_headline_rmse`, `compute_model_selection`,
  `compute_error_budget` (assembles Table 3).
- **The Q_b degeneracy / Bayesian side**: `compute_qb_degeneracy`,
  `bayesian_crosscheck` (emcee), `qb_prior_width_scan`.
- **Numerical certification**: `convergence_scan` (n_inner), `dt_ladder` (time step),
  `check_discretization`.
- **The surface closure**: `compute_diviner_closure` (uses `diviner`).
- **Speed**: `benchmark_speedup` (anchored vs brute), `benchmark_cpp` (Python vs C++).
- `_results.py` — read-side accessor so a benchmark can take "the production `K_d*`"
  as an input rather than recomputing it.

### `figures/` — the figure scripts
~38 `make_*.py`, each one figure or figure group. **They all follow one pattern:**
import `lunar.plotting.style`, read the relevant `results/*.json`, draw, and save a
PDF under `figures/`. They read numbers — they never recompute physics. Notable ones:
`make_letter_figures`, `make_results_figures`, `make_intro_figures`,
`make_prior_estimates_figure`, `make_context_map_figure` (+ many guidebook teaching
figures and animations).

### top-level `pipeline/`
- `make_all_figures.py` — runs every figure generator in order (`make figures`).
- `fetch_diviner.py` — one-time download of the Diviner GCP data.
- `extract_lola_relief.py` — crops LOLA shaded-relief for the context map.
- `run_all_timed.py` — runs the whole pipeline with timing.

---

## 4. The one journey: a `K_d` number, end to end

This is the spine of the whole codebase — follow it once and the rest is detail.

```
make retrieve
  └─ pipeline/compute/retrieve_kd.py :: main()
       ├─ apollo_helpers.extract_sensor_stability("a15", 80)   ← the fit targets
       │     └─ validation (reads data/apollo/…)
       ├─ grid.make_geometric_grid()                           ← the column
       └─ run_kd_sweep_extended(site, kd_grid)                 ← try each K_d
            └─ run_with(site, kd=…)  for each K_d
                 └─ equilibrium.solve_periodic_equilibrium()   ← THE METHOD
                      └─ solver.solve_pixel()                  ← forward march
                           └─ solver._march_radiative_hayne()  ← THE HOT LOOP
                                └─ _step() per hour
                                     ├─ properties.conductivity_hayne / density / c_p
                                     ├─ _face_harmonic_mean()
                                     ├─ _solve_surface_newton()
                                     └─ _thomas()               ← innermost solve
       … RMSE(K_d) curve → kd_star_from_residuals() → K_d*
       … bootstrap_kd_with_depth_uncertainty() → 95% CI
  → writes results/kd_retrieval_results.json
       → make_letter_figures.py reads it → figures/*.pdf
            → documents/jgr/letter/letter.tex quotes the number
```

Everything above `_march_radiative_hayne` runs once per `K_d`; that march runs
for every hour of every lunation — which is why **the solver is the entire cost**
(see §5).

---

## 5. The C++ port (`code/cpp/solver.cpp`)

A faithful, dependency-free ~300-line C++ port of **only** the solver hot loop
(`solver._march_radiative_hayne`) — same equations, same order of operations.

- **Driver:** `pipeline/compute/benchmark_cpp.py` (`dump_inputs → run_cpp`) feeds
  it a binary blob and reads the result back. Grid construction and forcing stay
  in Python (single-definition law) — the C++ duplicates no definitions.
- **Where it runs:** notebook `06_performance.ipynb` compiles it and runs all
  three engines (generic Python, Numba, C++) on identical inputs.
- **What it proves:** they agree to ~10⁻¹² K (a language-independent correctness
  check), and it illustrates the speed.
- **Important:** the production pipeline runs on the **Numba** solver, not C++.
  Numba already buys ~115× over interpreted Python; the C++ adds only ~1.5× on top.
  The port's value is as a correctness witness and a path to a dependency-free,
  parallelizable kernel (e.g. for a full-Moon map).

---

## 6. Running it (entry points)

From `code/` (after `pip install -e .` / `make install`):

| Command | What it does |
|---------|--------------|
| `make retrieve` | core retrieval + bootstrap → `results/kd_retrieval_results.json` |
| `make aux` | all sensitivity sweeps, model selection, error budget, MCMC |
| `make figures` | regenerate every figure into `figures/` |
| `make paper` | compile the letter + guidebook |
| `make test` | unit tests (`pytest`, 49 tests) |
| `make all` | the whole chain: retrieve → aux → figures → paper |

**Notebooks** (`code/notebooks/`, narrated walkthrough, in order):
`00_setup` (environment) → `01_methods` → `02_retrieval` → `03_results` →
`04_discussion` → `05_method` (the flux-anchored method) →
`06_performance` (Python vs Numba vs C++, and scaling to a map).

---

## 7. The dependency map at a glance

```
                       data/  (Apollo, Diviner, SPICE)
                         │
   ┌─────────────────────┴───────────── code/src/lunar/ (ENGINE) ───────────┐
   │ constants ─▶ config, grid, properties ─▶ solver ─▶ equilibrium         │
   │ validation ─▶ apollo_helpers      ephem   diviner   plotting/style     │
   └──────────────────────────────┬────────────────────────────────────────┘
                                   │  (imported by)
                  code/pipeline/compute/  (EXPERIMENTS)
                   retrieve_kd.py  +  sensitivity / benchmark / MCMC scripts
                                   │  (write)
                          code/results/*.json  (THE RECORD)
                                   │  (read by)
                  code/pipeline/figures/*.py ──▶ figures/*.pdf
                                   │  (quoted by)
                  documents/  (jgr/, gedes/, aogs/)

              code/cpp/solver.cpp ◀── benchmark_cpp.py  (cross-check of solver.py)
```
