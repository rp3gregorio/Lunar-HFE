# Figure map for the fresh guidebook

Rule adopted: **the guidebook carries the thesis figure set**, plus the
guidebook-only teaching assets that have no thesis equivalent.

Counts: thesis uses **39** figures (excluding the logo). Guidebook currently uses
**29**. Overlap is only **14**. So 25 thesis figures are missing and 5 of the
guidebook's are superseded versions of a thesis figure.

Every figure below already exists in `figures/`. Nothing needs to be created.

---

## A. Superseded — swap these (verified by rendering both)

| Guidebook now | Replace with | Why |
|---|---|---|
| `fig_probe_geometry` | **`fig_intro_probe`** | Old one shows **only Apollo 15**, has **no depth axis** (depths live in text labels), colours Probe 1's deep sensors green but Probe 2's *same category* teal, and in panel (b) the probe body **pokes out below the formula box**. New one shows both sites, real depth axis in cm, annotates the 7/16 counts, and adds the published K(z) comparison including Martínez. |
| `fig_apollo_timeline` | **`fig_apollo_timeline_a15` + `fig_apollo_timeline_a17`** | Old one is 4 cramped stacked panels showing only the deepest sensor per probe. New ones show **every sensor's stability window as a bar**, label the operational events (drilling transient, ALSEP outage, major outage, end-of-mission), and print T_eq per sensor. |
| `fig_context_map` | **`fig_context_globes`** | Thesis version. |
| `fig_speedup` | **`fig_speedup_factors`** | The thesis deliberately reports **hardware-independent factors** in the body and quarantines wall-clock to an appendix with the machine named. The old figure leads with raw wall-clock on an unnamed machine. |
| `fig_stats_bootstrap`, `fig_stats_contrast` | **`fig_bootstrap`, `fig_bootstrap_draw`** | Thesis pair. |

## B. Missing from the guidebook — add all of these

Grouped by the chapter that will host them.

**Ch 1, the problem**
`fig_prior_estimates` (the five-decade literature spread, and the
effective-vs-contact distinction) · `fig_context_globes` · `fig_tsukimi_chain`
(the mission hand-off) · `fig_pipeline_overview`

**Ch 2, the data**
`fig_intro_probe` · `fig_apollo_timeline_a15` · `fig_apollo_timeline_a17` ·
`fig_window_anatomy` (the stability rule on two real sensors) ·
`fig_amplitude_vs_depth` (**the borestem diagnostic** — currently the guidebook
just asserts the 80 cm cut) · `fig_apollo_mean_T_profile`

**Ch 3–4, physics and models**
`fig_boundary_conditions` · `fig_alpha_sweep` (the Martínez density retrieval,
alpha* = 1.19 / 1.04)

**Ch 5–7, the solver**
`fig_numerics_grid_matrix` (the grid and the tridiagonal system) ·
`fig_newton_surface` (the residual curve) · `fig_urect_explainer` ·
`fig_method_fluxanchored` · `fig_anchor_method` · `fig_speedup_factors`

**Ch 9–11, statistics**
`fig_bootstrap_draw` · **`fig_aicc_anatomy`** (the AICc decomposition — the
chapter that does not exist yet) · `fig_epoch_map` (common-epoch sensitivity) ·
`fig_robustness`

**Ch 12–13, results and meaning**
`fig_diviner_closure` · `fig_contrast_mechanisms` (porosity x composition
budget) · `fig_audit_waterfall`

## C. Guidebook-only — keep, no thesis equivalent

These are teaching assets and should survive: `spinup_filmstrip`,
`reconstruct_filmstrip`, `newmethod_filmstrip`, `old_vs_new_filmstrip`,
`fig_retrieval_demo`, `fig_equilibrium_demo`, `fig_convergence_study`,
`fig_anchor_placement`, `fig_baselayer`.

Result: about **48 figures** in the fresh book, all existing, none modified.

---

## D. TikZ diagram defects (guidebook-local, safe to redraw)

Rendered all 32 standalones at 130 dpi and inspected. The crop is `border=6mm`
so it is tight; earlier apparent dead space was an artifact of my contact sheet,
not the diagrams. Real defects:

| Diagram | Defect | Fix |
|---|---|---|
| `pipeline` | **Stale path** `src/lunar/{solver,equilibrium}.py`. Also the `D. Uncertainty` connector is a **long right-margin loop** running back up past boxes C and B to reach the results column, which the connector rules forbid. | Repath to `code/src/lunar/`. Reorder so D sits adjacent to its target, or drop the connector and let the box text carry it. |
| `windowflow` | The branch labels `some start passes` and `none` sit **on** the connector lines. The none-pass return arrow runs **tight underneath** the "keep the EARLIEST start" box. | Move labels off the lines into clear space; reroute the return through a clear channel. |
| `costnesting` | Says **~1418** half-hour steps per lunation; the real count is **1417**. Also "luna-tions" breaks across a line inside a box. | Fix the number; widen the box. |
| `fluxanchored` | The `check each cycle` arrow leaves **Step A**, but the convergence check logically follows **Step B**. Misleading. | Re-anchor the arrow to Step B. |
| `eqnflow` | The three header boxes (Data / Physics fixed / The knob) float with **no connector** to step 1. | Defensible under "encode a dependency once", but add a single grouped feed or a visual bracket so they do not read as orphaned. |
| `mcmcflow` | Says K_d is **flat in log over [1, 30]**. Wrong: the support is per-site, A15 [0.8, 9.0] and A17 [3.0, 15.0]. | Correct the numbers. |

## E. Figures with content errors (do not silently fix, shared assets)

| Figure | Problem |
|---|---|
| `fig_kd_qb_posterior` | Legend calls the white contours "posterior 1-, 2-, 3-sigma". They are drawn at 5%, 32%, 68% **of peak density**, which is roughly 2.45, 1.51, 0.88 sigma — wrong values and reversed order. The star is the **median**, labelled MAP in the code comment. The three dotted rays are a **disproved** proportional degeneracy and read as endorsement unless explained as a foil. Not used in the thesis or letter, so the exposure is contained. |
| `fig_aicc_anatomy` | Hardcodes RMSE rounded to 2 dp instead of reading the JSON, so its net values are +2.99 / −22.95 against the certified +2.94 / −23.17. The thesis caption already hedges this as "within rounding". Keep the hedge. |
| `fig_book_aicc` | Annotates "M1 wins" while plotting data where M3 is best. Unreferenced by any current document. Do not revive. |
