# AOGS Poster Backbone — every block of text, ready to paste into Canva

All numbers verified against `results/*.json` in the 2026-07-12 audit (shadow-cooling
and flux-closure claims CORRECTED from the old poster). Figures are in
`deliverables/documents/aogs/poster/figures/` (+ the schematic in `../talk_figures/`); the
assembled skeleton is `aogs_poster_canva.pptx` — import it and rearrange, or build
from scratch with the blocks below. Suggested sizes assume A0 portrait.

---

## HEADER

**Title (2 lines, ~72 pt bold):**
> Discrete Layer Thermal Modeling of Lunar Landing Sites
> with Topographic Shadowing

**Author band (teal bar, white text):**
> Ramón III P. Gregorio¹ · Richard Larsson¹ · Yasuko Kasai²
> ¹Institute of Science Tokyo, Japan · ²Institute of Science Tokyo, Transdisciplinary
> Science & Engineering, School of Environment and Society
> rp3gregorio@gmail.com · Abstract ID: [ID] · Poster session: [window] · AOGS 2026

*(swap [ID] and [window] when the program is out)*

**Takeaway banner (1–2 lines, ~30 pt, the "3-second read"):**
> Three regolith layers + DEM ray-traced horizon shadowing reproduce the Apollo Heat
> Flow Experiment record — the lever is conductivity, unlocked by site-specific density.

---

## 1 · The model & methods
**Figure:** `talk_figures/aogs_model_schematic.pdf/.png` (the schematic), then the
equations below it as an editable text block. (Added 2026-07-12 at the user's request —
a physics poster wants the governing math and the methodological novelty shown, not only
pictured. All constants verified against `config.py`/`constants.py`.)

> Governing 1-D heat diffusion (depth- and temperature-dependent properties):
>     ρ(z) c_p(T) ∂T/∂t  =  ∂/∂z [ K(T,z) ∂T/∂z ]
> Conductivity — Hayne et al. (2017), contact + radiative:
>     K(T,z) = K_c(z)·[1 + χ(T/350 K)³] ,   K_c(z) = K_d − (K_d − K_s) e^(−z/H)
>     K_s = 7.4×10⁻⁴ W m⁻¹ K⁻¹ ,   H = 6 cm ,   χ = 2.7
> Boundaries — surface: (1−A)·S_shadowed(t) = ε σ T_s⁴ + conduction ;   base:
>     K ∂T/∂z = Q_b = 21 / 16 mW m⁻² (A15 / A17; Langseth et al. 1976)
> Flux-anchored solver — anchor ⟨T⟩ below the rectification zone (z₀ = 55 cm),
>     where  d⟨T⟩/dz = (Q_b − u_rect)/K :  periodic equilibrium in ~0.6 s/solve,
>     ~20× faster than brute-force time-stepping.
> Data — HFE deep-sensor equilibria: restored 1971–77 record, quiet late-mission
>     window; sensors above 80 cm excluded (borestem conducts the surface wave down).

**Sign note (do not "fix"):** the closure is `(Q_b − u_rect)/K` — **minus** u_rect (the
diurnal rectification correction, small below z₀). A displayed `+` is the known error.

## 2 · One pipeline, 650 configurations
**Figure:** `talk_figures/aogs_pipeline_flowchart.pdf/.png`. Self-captioned (legend inside).

## 3 · The sites, their horizons, the lost sunlight
**Figure:** `figures/poster_sites.pdf` (DEM maps + horizon polars, now with the sun path).
**Caption (~18 pt italic):**
> The Apennine front raises the Apollo 15 horizon to 14.0° (1.16% insolation loss); the
> North Massif gives Apollo 17 a 10.1° peak (0.18% — a lower bound at 16 ppd). Dotted:
> the sun's path over a lunation; square markers: where the terrain blocks it.

## 4 · Validation against Apollo HFE
**Figure:** `figures/poster_profiles.pdf` (single shared legend below).
**Table (native Canva table, editable):**

| RMSE at deep sensors (K) | homogeneous | Hayne cont. | best cp | best coupled |
|---|---|---|---|---|
| Apollo 15 | 2.31 | 2.03 | 1.74 | **0.90** |
| Apollo 17 | 3.76 | 0.54 | 0.39 | **0.36** |

**Caption:**
> All 650 configurations converged on the anchor criterion; the winning configurations
> close the flux budget to ≤ 0.7% and agree to ≤ 35 mK when re-run at the production
> spin-up (n = 96).

*(Do NOT write "flux closure ≤ 0.8% for all 650" — the audit showed 180 sweep runs with
the z₂ step near the anchor spike the closure METRIC (harmlessly); the sentence above is
the true statement.)*

## 5 · Sensitivity — the lever is conductivity
**Figure:** `figures/poster_leverage.pdf` (branch box plots).
**Caption:**
> Heat capacity alone moves the fit ≤ 0.7 K and only through the surface layer; density,
> through the conductivity it implies, spans ~4 K. Best layer boundaries sit high
> (z₂ = 30 cm) at both sites.

**Stat tiles (two big-number callouts):**
> **2.6×** — better than homogeneous at Apollo 15 (0.90 K vs 2.31 K)
> **10×** — better than homogeneous at Apollo 17 (0.36 K vs 3.76 K)

## 6 · What the regolith prefers — and what transfers
**Figures:** `figures/poster_density.pdf` (retrieved columns) + `figures/poster_transfer.pdf`
(the 3×2 cross-site RMSE matrix — this figure IS the "physics, not curve-fitting" argument).
**Caption:**
> Left: both sites prefer a surface denser than Hayne et al. (1300–1500 vs 1100 kg m⁻³).
> Right: structures moved across sites degrade gracefully and still beat homogeneous.
> The winning triples are degenerate (bootstrap stability 13% at A15) — the robust result
> is the improvement, not one specific triple.

## Conclusions (read last — bottom right)
> • Topography enters twice, and the channels oppose: shadow cooling at the deep sensors
>   (2.2 K at A15, 0.5 K at A17) vs (1−SVF) terrain radiation (+1.3/+0.7 K) — at A17 the
>   warming wins. Both come from the same DEM horizons; both should be standard.
> • A 3-layer column reproduces the HFE record; density matters through the conductivity
>   it implies, not through heat capacity.
> • Site-specific calibration stays physical: cross-site transfer degrades gracefully and
>   parameter differences track the known geology — physics, not curve-fitting.
> • The same pipeline extends to landing-site thermal assessment, regolith property
>   constraints, and any airless body with high-resolution topography.

**Caveats line (small italic, end of the Conclusions box):**
> Caveats — the 16 ppd DEM (~1.9 km/px) under-resolves A17's near massifs, so its horizons
> are a lower bound; solar declination is fixed at 0°; the (1−SVF) terrain-radiation channel
> is a diagnostic, not yet folded into the fits.

## References (one small line, full width)
> [1] Hayne et al., JGR: Planets 122, 2017. [2] Langseth et al., Proc. Lunar Sci. Conf. 7,
> 1976. [3] Nagihara et al., JGR: Planets 123, 2018. [4] Saito et al., Adv. Space Res. 40,
> 2007. [5] Smith et al., GRL 37, 2010. — Code + archives: github.com/rp3gregorio/Lunar-HFE

---

## Numbers you may be asked about at the poster (all archive-backed)
- Shadow cooling at the sensors: **−2.22 K (A15), −0.48 K (A17)**; terrain-IR warming
  **+1.15/+0.65 K** (+1.30/+0.74 with reflected sunlight, upper bound T_terr ≈ T_s).
  Net: −0.9 K at A15, **+0.3 K at A17 (warming wins)**.
- SVF **0.985 / 0.991**; horizon max **14.0° / 10.1°**; insolation loss **1.16% / 0.18%**.
- Certified K_d\*: **4.60 / 7.08 mW m⁻¹ K⁻¹** (the letter's values; K held there in the sweeps).
- Cross-site = structure-only transplant (target site's K_d\* in K_c(ρ)): 1.73 / 1.64 K.
- Winner stability (bootstrap, coupled): A15 13%, A17 36% → quote the improvement CI
  (best-RMSE 95% CI 0.26–1.08 / 0.25–0.43 K), not the specific triple.
- NEVER quote the shadowed-forcing K_d re-retrieval shift (−2.72 mW at A15): mixed
  n_inner regimes + near-floor vertex; needs a matched-resolution re-run first.

## Reading path you can rehearse (60 s)
1. [schematic] "Two places on the Moon have subsurface ground truth. We take one certified
   solver and add two things: discrete density layers, and the terrain's actual horizon."
2. [flowchart] "Every candidate column runs through the same pipeline — 650 solves."
3. [sites] "The Apennines cost A15 about 1% of its sunlight; Taurus–Littrow much less —
   and the same horizons radiate heat back."
4. [profiles + table] "The layered, density-coupled column lands on the sensors where
   homogeneous misses by 2–4 K."
5. [boxplots + tiles] "The lever is conductivity via density — heat capacity alone can't do it."
6. [matrix] "Swap the sites' structures and it degrades gracefully but still beats
   homogeneous — it's physics, not curve-fitting."
