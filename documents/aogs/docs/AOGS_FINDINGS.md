# AOGS study — findings report

*(auto-assembled 2026-07-11 from `results/aogs_sensitivity.json` (88 runs),
`results/aogs_density_study.json` (650 runs), and `results/aogs_kd_shadowed.json`;
all solves = certified flux-anchored periodic equilibrium, scored by RMSE
against the stable-window deep (>= 80 cm) HFE sensors.)*

## 1. The terrain and its horizons
- **A15** (26.1N, 3.6E): horizon max 14.0 deg, insolation energy loss 1.16%
- **A17** (20.2N, 30.8E): horizon max 10.1 deg, insolation energy loss 0.18%
- A15 sits under the Apennine front (mean horizon ~4.7 deg); A17's peak points
  due north at the North Massif. At 16 ppd the A17 horizons are a **lower bound**
  (near-field massifs undersampled).

## 2. What the density profiles look like
- Swept: 3 layers, boundaries z1 in {5,10,20} x z2 in {30,50,80} cm,
  densities rho1<=rho2<=rho3 over 18 ordered triples, x 2 physics branches.
- **Winning shapes** (shadowed forcing):
  - A15 / cp     : z = 5/30 cm, rho = 1500/1700/1700 kg m^-3, RMSE 1.74 K
  - A15 / coupled: z = 10/30 cm, rho = 1500/1700/1800 kg m^-3, RMSE 0.90 K
  - A17 / cp     : z = 5/30 cm, rho = 1500/1700/1700 kg m^-3, RMSE 0.39 K
  - A17 / coupled: z = 5/30 cm, rho = 1300/1500/1900 kg m^-3, RMSE 0.36 K
- Pattern: **denser-than-Hayne surface** (1300-1500 vs 1100) over a **shallow**
  mid|deep break (z2 = 30 cm preferred everywhere): the column wants its
  transition to consolidated regolith HIGH, consistent with Apollo core stratigraphy.

## 3. The two physics branches (the core result)
- A15 / cp     : RMSE 1.74..2.47 K (spread 0.73) | Hayne-continuous baseline 2.03 K
- A15 / coupled: RMSE 0.90..5.02 K (spread 4.11)
- A17 / cp     : RMSE 0.39..0.93 K (spread 0.54) | Hayne-continuous baseline 0.54 K
- A17 / coupled: RMSE 0.36..4.56 K (spread 4.20)
- **Heat capacity alone is second-order** (spread <= 0.73 K, carried entirely by
  the surface layer rho1). **Density-coupled conductivity is first-order**
  (spread ~4.1 K) - and its winner nearly recovers the letter-quality fit at A15
  *despite* shadowing (2.03 -> 0.90 K) and beats it at A17 (0.54 -> 0.36 K).
- Coupling law: the Hayne form's own internal relation
  K_c(rho) = K_d* - (K_d*-K_s)(rho_d-rho)/(rho_d-rho_s) - no new constants.

## 4. Shadowing-corrected K_d* + abstract-promised checks (new)
- **Pure-K retrieval under shadowed forcing** (continuous Hayne rho, only the
  forcing changed vs the letter): **both minima are edge-limited** —
  A15 runs off the LOW end (best grid point 2.1 mW, RMSE 1.19 K, still
  falling) and A17 off the HIGH end (~9.6 mW, RMSE 0.32 K). Reading:
  conductivity ALONE cannot absorb A15's Apennine shadowing (the misfit
  never bottoms out in the plausible range), while the density-coupled
  layering does (0.90 K) — the layered description is the physical one.
- **Homogeneous-property baseline** (constant K_c = K_d*, constant
  rho = 1800): RMSE 2.31 K (A15) / 3.76 K (A17).
  The layered model improves on it by 2.6x (A15) and 10x (A17) — the
  abstract's "improved accuracy compared to homogeneous property
  approaches", quantified.
- **Cross-site validation** (each site's best coupled config applied at the
  other site): A15-config at A17 gives 1.64 K; A17-config at A15
  gives 1.73 K. Transferred parameters degrade gracefully (native
  0.36/0.90 K) yet still beat the homogeneous baseline everywhere — the
  framework captures transferable physics, not site-specific curve-fitting.

## 5. Honest caveats
- 16 ppd DEM under-resolves A17's near massifs (horizons = lower bound).
- Declination fixed at 0 (no +/-1.5 deg seasonal wobble); direct blocking only
  (no terrain-scattered flux).
- Densities enter cp via the Hayne polynomial; the coupled branch's K_c(rho)
  extrapolates mildly above rho_d for rho = 1900.

## 6. What would improve the AOGS story further
1. **Higher-res DEM** (SLDEM2015 tiles) for true A17 horizons.
2. **Terrain-scattered radiation** (the (1-SVF) flux the massif walls re-emit).
3. **Joint retrieval**: fit (K_d, rho-layering) simultaneously under shadowed
   forcing with bootstrap CIs, as in the letter.
4. Diviner surface-T validation alongside the subsurface sensors.

## 7. Winner-stability bootstrap (2026-07-11, zero new solves)
`aogs_winner_bootstrap.py` resamples the deep sensors (with replacement,
plus N(0, T_std) noise) 10,000x and re-picks the best config from the
stored `T_model_at_sensors` of all 650 runs — the letter's bootstrap
philosophy applied to the layer sweep. Results
(`results/aogs_winner_bootstrap.json`):

| site/branch | production winner | stability | best-RMSE median [95% CI] |
|---|---|---|---|
| A15 cp      | z=5/30, 1500/1700/1700 | 100.0% | 1.75 [1.18, 2.17] K |
| A15 coupled | z=10/30, 1500/1700/1800 | 13.3% | 0.85 [0.26, 1.08] K |
| A17 cp      | z=5/30, 1500/1700/1700 | 88.2% | 0.39 [0.26, 0.52] K |
| A17 coupled | z=5/30, 1300/1500/1900 | 35.8% | 0.35 [0.25, 0.43] K |

Honest reading (poster Q&A ammunition):
- The **improvement over homogeneous is bootstrap-solid**: even the upper
  CI bounds (1.08 / 0.43 K coupled) stay far below homogeneous
  (2.31 / 3.76 K) and below Hayne-continuous at A15.
- The **specific A15 coupled triple is degenerate** (13%): alternates
  swap the deep density 1800<->1900 or trade z-boundaries — but ALL top
  configs share the denser-than-Hayne surface and high transition. The
  robust claim is the *class* of profile, not one triple.
- **A17's densities are the stable part** (top-3 configs = 88% of draws
  all have rho = 1300/1500/1900); only the mid|deep boundary wobbles
  (30 vs 50 cm). Quote A17's retrieval as densities-first.

## 8. Bridge to the letter (this study = its extension)
- The letter's robustness section already ran ONE 3-layer density check:
  `kd_retrieval_results.json` has `kd_star_3layer` = 2.93 / 3.00 mW
  (RMSE 0.99 / 0.92 K) vs homogeneous-column K_d* = 4.60 / 7.08. The AOGS
  study expands that single row into 650 configs + DEM shadowing.
- The cp branch is ANCHORED at the letter's certified K_d* (4.60/7.08) —
  the two studies share the same certified solver, sensors, and stable
  windows.
- The letter's K_d contrast (A17 - A15 = +2.31 mW, marginal) reappears
  here as A17's preference for the densest deep layer (1900 vs 1800).
- The letter's error budget is dominated by chi and Q_b — both held FIXED
  in this sweep; a joint (K_d, rho, chi) retrieval under shadowed forcing
  is the natural next paper.

## 9. Quantitative geology tie-in (2026-07-11)
The abstract claims "parameter differences between sites align with known
geological variations." Now quantified against measured densities found in
the repo's own references (`code/references/
chaste2025_chandrayaan3_insitu_conductivity.pdf`, p.2, citing Grott,
Knollenberg & Krause, "Apollo lunar heat flow experiment revisited", JGR
Planets [their ref 6]):

> "The thermal conductivity was found to be in the range of 0.01 to
> 0.03 W m-1 K-1 for the average bulk densities of **1825 and 1960
> kg m-3 for Apollo 15 and Apollo 17**, respectively."  (depth 0.35-2.34 m)

| | thermally retrieved deep layer rho3 (this study) | measured avg bulk density (Grott et al., via Chaste 2025) |
|---|---|---|
| Apollo 15 | 1800 (bootstrap-degenerate with 1900) | 1825 |
| Apollo 17 | 1900 (in 88% of bootstrap draws) | 1960 |

Two independent agreements at our 100 kg m-3 grid resolution:
(1) the VALUES match within 25-60 kg m-3, and (2) the ORDERING matches —
A17 denser than A15 — which is also the direction of the letter's K_d
contrast. The deep-layer densities the sweep retrieved *thermally* are
the densities the Apollo heater experiments measured *mechanically*.
That is the abstract's "physical basis of the optimization approach",
with numbers.

(N.B. the Langseth 1976 PDF in references/ is a scanned copy with no text
layer; the Chaste/Grott chain above is the verifiable in-repo source.)

## 10. Shadowed pure-K retrieval, now properly bounded (2026-07-11)
`aogs_kd_shadowed_extend.py` pushed both grids to their physical bounds
(A15 down to the K_s floor 0.74 mW, A17 up to 14 mW). **Both minima are
now interior** — this SUPERSEDES the earlier "edge-limited" reading:
- A15: shadowed vertex K_d* = 1.88 mW (shift −2.72 from 4.60),
  min RMSE 1.10 K
- A17: shadowed vertex K_d* = 9.69 mW (shift +2.61 from 7.08),
  min RMSE 0.32 K

Correct framing: conductivity alone CAN bottom out under shadowed
forcing, but at A15 it demands K_d = 1.88 mW — far outside the letter's
own bootstrap CI [4.18, 6.96] — and still fits WORSE (1.10 K) than the
density-coupled layered model (0.90 K). The layered description remains
the physical one; the pure-K "fix" is a distortion, now quantified
instead of asserted.

## 11. (1−SVF) terrain radiation terms quantified (2026-07-11)
`aogs_svf_terms.py` (results/aogs_svf_terms.json), evaluated at each
site's best coupled config, upper-bound approximation T_terr ≈ T_s:
- A15 (SVF 0.9848): terrain IR self-heating warms the sensor depths by
  +1.15 K; + terrain-reflected sunlight → +1.30 K total.
- A17 (SVF 0.9914): +0.65 K; +0.74 K total.

Two consequences, stated honestly:
1. Terrain IR back-radiation is the SAME ORDER as, and OPPOSES, the
   direct-beam shadowing loss (~1 K). The net topographic effect at
   depth is the small difference of two ~1 K channels (its sign depends
   on the terrain-temperature approximation; T_terr = T_s is the warm
   upper bound). "Shadowing is first-order" survives — but as one of
   TWO first-order topographic channels, not alone.
2. Adding the terms to winners TUNED WITHOUT them worsens RMSE
   (+0.62 / +0.31 K): a re-sweep with terrain terms enabled is the
   identified next step before any claim about which density column
   wins under full topographic forcing. The abstract's "sky view
   factors for diffuse radiation" is now implemented and quantified,
   not just computed.

## 12. Hayne GLOBAL K_d baseline under shadowed forcing (2026-07-11)
2-solve control (`results/aogs_global_kd_baseline.json`): Hayne et al.
(2017) global K_d = 3.4 mW, continuous density, DEM-shadowed forcing:
RMSE 1.90 K (A15) / 0.71 K (A17).

Full shadowed-forcing ladder (K):
| model | A15 | A17 |
|---|---|---|
| homogeneous (const K_c = K_d*, const rho) | 2.31 | 3.76 |
| Hayne GLOBAL K_d = 3.4, continuous rho    | 1.90 | 0.71 |
| Hayne continuous at site K_d*             | 2.03 | 0.54 |
| best cp (site K_d*)                       | 1.74 | 0.39 |
| best coupled (site K_d*)                  | 0.90 | 0.36 |

Nuance worth stating out loud: at A15 the global 3.4 fits BETTER than
the site K_d* = 4.60 under shadowed forcing (1.90 vs 2.03) — but only
because shadowing pushes the effective pure-K optimum DOWN (vertex
1.88 mW, Sec. 10); 3.4 is closer to that distorted optimum by accident,
not by physics. The resolution is the layered model: coupled at the
site anchor beats every smooth-column variant at both sites. Anchor on
the site-specific letter K_d*; quote the global value as the
site-agnostic baseline it is; never anchor on the shadowed vertices.

## 13. K_d <-> deep-density degeneracy (the key conceptual caveat, 2026-07-11)
Q raised: "if we change density, K_d changes too, so the site K_d* no
longer holds?" -- correct for the coupled branch, and it names the
study's central limitation.

- cp branch: density enters heat capacity only; the deep mean gradient
  is Q_b/K_d BELOW the rectification zone (cp has no leverage there), so
  re-retrieving K_d under a different cp-density gives ~the same value.
  K_d* genuinely holds. (Also why cp moved the fit <=0.7 K.)
- coupled branch: density sets K_c(z) via the linear K_c(rho) law whose
  DEEP ENDPOINT is the site K_d*. So the winner's EFFECTIVE deep
  conductivity = K_c(rho3), not K_d*:
    A15 winner rho3=1800 (= Hayne rho_d) -> K_c = 4.60 mW (= K_d*, holds)
    A17 winner rho3=1900 (> rho_d)       -> K_c = 7.99 mW (K_d* +0.91)
  (A15's degenerate alternate rho3=1900 would give 5.15 mW.)
  K_d* survives as the calibration endpoint, NOT as the model's deep K.

Deep truth: K_d and deep density are DEGENERATE -- both set the deep
gradient; they cannot be retrieved independently from one steady
gradient. The letter fixed density (Hayne) and retrieved K_d; this study
fixes K_d and retrieves density. Each is a conditional slice through a
coupled 2-D space. The letter's A17>A15 conductivity contrast (7.08 vs
4.60) reappears here as A17's denser deep layer (1900 vs 1800): SAME
physics, two parameterizations.

Poster/defense phrasing: never claim K_d*=7.08 AND rho3=1900 as two
independent retrieved facts. Say "anchored at the letter K_d*, the
layered fit prefers a denser A17 deep layer -- equivalently more deep
conductance, consistent with the letter's higher A17 K_d*." Rigorous
resolution = JOINT (K_d, rho-layering) retrieval (Sec. 8 next-paper).
