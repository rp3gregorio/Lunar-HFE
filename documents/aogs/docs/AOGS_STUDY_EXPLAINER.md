# AOGS study — plain-language explainer

*A short, self-contained summary of the discrete-layer thermal study behind the
poster. For the dense archive notes and every number's provenance, see
`AOGS_FINDINGS.md`. All values below are pulled from the results JSONs.*

---

## 1. What this study is, in one sentence
It is an **extension of the JGR letter**: the letter retrieved one deep
conductivity `K_d` per Apollo site; this study asks *what layered regolith
density structure* best explains the same borehole temperatures, and adds
**topographic shadowing** from the real terrain.

## 2. The engine we reuse (nothing new here)
Same **Hayne et al. (2017)** physics as the letter:

- Heat flows in a 1-D column by conduction: `ρ(z)·c_p(T)·∂T/∂t = ∂/∂z[K·∂T/∂z]`.
- Conductivity has two parts: `K(T,z) = K_c(z)·[1 + χ(T/350K)³]`
  — grain-contact conduction (rises with depth) **plus** radiative transfer
  between grains (rises with T³).
- Top boundary: sunlight in = thermal emission + heat conducted down.
  Bottom boundary: fixed geothermal flux `Q_b` from below.
- We solve for the **repeating** lunar-day cycle (periodic equilibrium) using
  the letter's fast flux-anchored solver (~20× faster than brute force).

The output we care about is **`T̄(z)` — the time-averaged temperature vs depth**,
compared to the seven Apollo deep sensors. That comparison is one RMSE number.

## 3. The two things we add
1. **Topographic shadowing.** We ray-trace the LOLA DEM around each borehole to
   get the skyline (horizon). When the Sun is below the terrain, it is blocked.
   Apollo 15 (Apennine front) loses 1.16% of its sunlight; Apollo 17 (North
   Massif) loses 0.18%.
2. **Discrete density layers.** Instead of Hayne's single smooth density curve,
   we allow a **3-layer staircase**: loose surface → intermediate → compact
   deep, with density rising with depth.

## 4. The pipeline (how a single score is produced)
`LOLA DEM + Hayne model + Apollo record` →
**1** ray-traced horizons (shadowed sunlight) →
**2** pick a 3-layer density profile →
**3** flux-anchored solver → **4** mean profile `T̄(z)` →
**5** RMSE vs sensors. Repeat over **650 configurations**; the best-fitting
profiles *are* the retrieved structure. (See the pipeline flowchart in
`talk_figures/aogs_pipeline_flowchart.pdf`.)

## 5. What density profiles we test
Three layers, each denser than the one above (physically required — regolith
compacts with depth). Swept grid:

| knob | values |
|---|---|
| skin\|mid boundary z₁ | 5, 10, 20 cm |
| mid\|deep boundary z₂ | 30, 50, 80 cm |
| surface density ρ₁ | 1100, 1300, 1500 |
| mid density ρ₂ | 1500, 1700 |
| deep density ρ₃ | 1700, 1800, 1900 kg/m³ |

Monotone (ρ₁ ≤ ρ₂ ≤ ρ₃) → **18 density triples × 9 boundary pairs = 162
profiles** per site, per branch. **Two branches:**
- **cp** — density changes heat storage only; conductivity stays at the site `K_d*`.
- **coupled** — density *also* sets conductivity through the Hayne form's own
  internal `K_c(ρ)` relation (no new constants).

## 6. The key subtlety you must be able to explain: K_d ↔ density degeneracy
The deep temperature gradient is essentially `Q_b / K_deep`. **Both** a higher
`K_d` **and** a denser deep layer raise `K_deep` — they produce the *same*
gradient. So from the sensors alone you **cannot separate them**.

- The **letter** pinned the density (Hayne's) and solved for `K_d` → 4.60 / 7.08 mW.
- **This study** pins `K_d` (the letter value) and solves for density.

Consequence, in the coupled branch, the winner's *effective* deep conductivity
is `K_c(ρ₃)`, **not** `K_d*`:

| site | letter K_d* | winner ρ₃ | effective deep K |
|---|---|---|---|
| A15 | 4.60 | 1800 (= Hayne ρ_d) | **4.60** — unchanged |
| A17 | 7.08 | 1900 (> ρ_d) | **7.99** — shifted +0.91 |

So "K_d* = 7.08 **and** the deep layer is 1900" are **not two independent
facts** — they are two descriptions of A17's one deep-gradient requirement.
The letter said it with a bigger `K_d`; this study says it with a denser layer.
**Same physics, two parameterizations.**

## 7. So how *should* K_d be found? (recommendation)
Because of the degeneracy, don't fit both freely. Three tiers:
- **Tier 1 (lead with this):** pin the deep density to the *measured* Apollo
  drive-core value, then retrieve `K_d`. One honest number, broken free of the
  circularity by an independent measurement.
- **Tier 2 (best figure):** sweep the density and retrieve `K_d` for each →
  a **K_d\*(ρ_deep) trade-off curve** that literally draws the degeneracy.
- **Tier 3 (next paper):** joint `(K_d, ρ)` fit with a density prior → a ridge,
  not a point.
- **Anchor hierarchy:** site `K_d*` = anchor · Hayne global 3.4 = named baseline
  · shadowed-forcing vertices (1.88 / 9.69) = diagnostic only, never an anchor.

## 8. The results (shadowed forcing, RMSE in K vs deep sensors)
| model | A15 | A17 |
|---|---|---|
| homogeneous (constant K, constant ρ) | 2.31 | 3.76 |
| Hayne **global** K_d = 3.4 | 1.90 | 0.71 |
| Hayne continuous at site K_d* | 2.03 | 0.54 |
| best **cp** (density → heat capacity) | 1.74 | 0.39 |
| best **coupled** (density → conductivity) | **0.90** | **0.36** |

- **Layering wins:** the coupled model beats the homogeneous baseline by
  ~2.6× (A15) and ~10× (A17).
- **The lever is conductivity, not heat capacity:** cp barely moves the fit
  (≤0.7 K); coupled spans ~4 K.
- **Bootstrap (free, from stored temperatures):** the *improvement* is solid —
  coupled best-RMSE 95% CIs 0.85 [0.26, 1.08] / 0.35 [0.25, 0.43] K — but the
  *exact* A15 triple is degenerate (13% stability); the robust claim is the
  **class** of profile (denser-than-Hayne surface, high transition), not one
  triple. A17's densities are stable (88% of draws).
- **Geology check:** retrieved deep densities **1800 / 1900** vs *measured*
  Apollo core **1825 / 1960** kg/m³ (Grott et al., via the Chandrayaan-3 paper
  in `code/references/`) — values *and* the A17 > A15 ordering match.

## 9. Honest caveats (Q&A ammunition)
- **Terrain radiation.** Terrain that blocks the Sun also glows (IR) and
  reflects. Quantified: +1.15 K (A15) / +0.65 K (A17) — the *same order* as the
  ~1 K shadowing loss, and *opposite* sign. So topography enters through two
  first-order channels that nearly cancel; a full re-sweep with these on is the
  next step.
- **K_d–density degeneracy** (Sec. 6) — the central limitation; the joint
  retrieval resolves it.
- **16 ppd DEM** under-resolves A17's massifs (horizons are a lower bound).
- **χ and Q_b held fixed** (they dominate the letter's error budget).

## 10. One-sentence takeaway
Using the letter's certified engine, adding real terrain shadowing and a
3-layer density column reproduces the Apollo borehole temperatures far better
than any smooth homogeneous model, and the densities it retrieves *thermally*
match the ones Apollo measured *mechanically* — with the honest caveat that
deep conductivity and deep density are two views of the same quantity.
