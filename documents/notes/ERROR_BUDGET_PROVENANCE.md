# Error-budget provenance audit

**Date:** 2026-07-27 · **Scope:** every envelope feeding Table 4.1 of the thesis
(`code/results/kd_error_budget.json`), checked against the reference PDFs in
`code/references/`.

Method: read the source. Two PDFs (Langseth 1976, Cremers 1971) are scanned
images with no text layer (~19 characters/page), so a text search over them
returns nothing and proves nothing — those were read visually, page by page.
An earlier pass that only grepped is not evidence and was discarded.

---

## Verdict at a glance

| Quantity | Code value | Source verdict |
|---|---|---|
| Q_b nominal, A15 | 21 mW m⁻² | ✅ **exact** — Langseth 1976 |
| Q_b nominal, A17 | 16 mW m⁻² | ✅ **exact** — Langseth 1976 |
| χ | 2.7 | ✅ **exact**, dual-sourced — Hayne 2017 + Vasavada 2012 |
| K_s | 7.4×10⁻⁴ W m⁻¹ K⁻¹ | ✅ **exact** — Hayne 2017 |
| K_d global | 3.4×10⁻³ | ✅ **exact** — Hayne 2017 |
| H | 0.06 m | ✅ **exact** — Hayne 2017 |
| ρ_s, ρ_d | 1100, 1800 kg m⁻³ | ✅ **exact** — Hayne 2017 |
| Q_b envelope | A15 14–25, A17 10–18 | ✅ **resolved 2026-08-17** — Saito 2007 (LPSC XXXVIII #2197, now in references/) infers 3.7 mW/m² at A17, *below* the swept lower bound; envelope is conservative |
| **χ alternative** | **1.48** | ❌ **misattributed** |
| K_s ±30 % | "Cremers 1971 lab scatter" | ⚠️ not a quoted uncertainty |
| Albedo ±0.01 | "Vasavada 2012" | ⚠️ inferred, not quoted |
| ρ_d 1700–2000 | "Mitchell 1973 / Carrier 1991" | ✅ **resolved 2026-08-17** — Mitchell CR-134306 (now in references/) gives ρ=1.27+0.121·ln(z+1) g/cm³ → 1.83–1.93 at 1–2.3 m |

---

## 1. Confirmed exactly

**Langseth, Keihm & Peters (1976), *Revised lunar heat-flow values*** — read
visually; p. 3143 abstract and p. 3156.

> "At the Apollo 15 site a heat-flow value of **2.1 μW/cm²** is the mean of the
> two probe measurements and at Apollo 17, the probe 1 value of **1.6 μW/cm²**
> is considered the more reliable measurement."

2.1 μW cm⁻² = 21 mW m⁻², 1.6 μW cm⁻² = 16 mW m⁻². Matches `config.SITES`
exactly. The A17 choice of *probe 1 only* is the paper's own recommendation,
not a project decision.

**Hayne et al. (2017)** — text-searchable, quoted verbatim:

> "Radiative conductivity parameter **χ 2.7** — This study and Vasavada et al. (2012)"
> "Thermal conductivity varies from **7.4×10⁻⁴** W m⁻¹ K⁻¹ at the surface, to
> **3.4×10⁻³** W m⁻¹ K⁻¹ at depths of ~1 m"
> "fixed values of ρs (**1100** kg m⁻³) and ρd (**1800** kg m⁻³)"
> "standard parameters from Table A1, with **H = 0.06 m**"

**Vasavada et al. (2012)** independently confirms χ:

> "...350)³; (3) where ks and kd are 0.0006 and 0.007 W/m/K, respectively, and
> **c is 2.7**."

So the entire published parameter set the model runs on is verified against
source. This is the defensible core.

---

## 2. ❌ The χ = 1.48 attribution is wrong

`compute_fixed_input_sensitivities.py` states:

> `sigma_chi : chi = 1.48 (Vasavada et al. 2012 normalisation) vs the adopted
> 2.7 (Hayne 2017 App. A) -- the actual published disagreement`

**There is no published disagreement.** Vasavada et al. (2012) use χ = 2.7 —
the *same* value as Hayne — and say so explicitly:

> "To address a deficiency in our previous model in matching the Apollo data, we
> **increase c to 2.7 (from 1.5)** at the surface in the revised model"

The string `1.48` appears **nowhere** in Vasavada 2012, and nowhere in
Hayne 2017. The nearest published number is **1.5**, which is Vasavada's
*superseded* pre-2012 value.

**Impact.** The physics is unaffected: re-running at a lower χ is a legitimate
robustness test, and "the direction of the contrast survives at low χ" still
holds. What is wrong is the *label*. The thesis presents χ = 1.48 as the
competing published value; an examiner who opens Vasavada 2012 will find 2.7.

**Recommended fix** — one of:
1. relabel as "Vasavada et al.'s **pre-2012** value (1.5), superseded by their
   own revision to 2.7", and use 1.5 rather than 1.48; or
2. find the actual origin of 1.48 and cite it; or
3. reframe as an arbitrary low-χ stress test with no attribution at all.

Option 1 is the most honest and needs only a re-run at χ = 1.5.

---

## 3. ⚠️ Q_b envelope — upper bounds sound, lower bounds unsourced

Langseth p. 3156 gives the measurement uncertainty:

> "Errors of the measurements, deriving primarily from the resolution
> constraints of the annual wave diffusivity deductions, are estimated at
> **±15 %**."

and Table 2 (p. 3158) gives the topographic corrections — Taurus-Littrow
+10.0 ± 4.0 % (Jeffreys) or +4.0 ± 5.0 % (random walk); Hadley Rille net
−0.3 ± 3.7 % to +3.0 ± 5.5 %, i.e. negligible. The abstract adds that at
Taurus-Littrow "a small downward correction indicates that a value of
**1.4 μW/cm²** is the best estimate for the regional flux."

| | Langseth supports | Code uses |
|---|---|---|
| A15 | 17.9 – 24.2 (21 ±15 %) | **14.0** – 25.0 |
| A17 | 13.6 – 18.4 (16 ±15 %), or 11.9 with the 14 regional anchor | **10.0** – 18.0 |

Upper bounds are fine. **Both lower bounds sit below anything Langseth
supports** and must be coming from Saito (2007) or Nagihara (2018) — neither of
which is held locally, so neither could be checked.

Direction matters: generous lower bounds make σ_Qb *larger*, so the budget errs
conservative. That is the safe direction, but it still needs a citation.

---

## 4. ⚠️ K_s ±30 % is not a quoted uncertainty

`cremers1971_apollo11_fines.pdf` is **Cremers & Birkebak (1971), "Thermal
conductivity of fines from Apollo 12"** — the filename says Apollo 11 and is
wrong. Abstract, read visually:

> "It was found to vary from about **0.12×10⁻² W/m-°K at 160°K** to about
> **0.35×10⁻² W/m-°K at 428°K** for a sample density of **1300 kg/m³**."

That is 1.2 → 3.5 mW m⁻¹ K⁻¹ across a temperature range, for **one sample at
one density**. It is a temperature dependence, not a scatter, and **±30 % is
nowhere stated**. The envelope may be defensible from the wider lab literature,
but it does not come from this paper.

---

## 5. ⚠️ Albedo ±0.01 — inferred, and it is the largest row

This is the **single largest entry in the A17 budget (σ = 2.96)**, so its basis
matters most of all. Vasavada 2012 quotes a "normal albedo of 0.1" for the
model and separates terrain by "albedo > 0.13 (orange) and < 0.09 (green)".
It states **no albedo uncertainty**. The ±0.01 is a reasonable reading of that
spread but it is an inference, not a published error bar.

---

## 6. ⚠️ ρ_d upper bound 2000 kg m⁻³ not located

Carrier (1991) Ch. 9, text-searchable:

> "the best estimate for the average bulk density of the top 15 cm of lunar soil
> is **1.50 ± 0.05 g/cm³**, and of the top 60 cm, **1.66 ± 0.05 g/cm³**"

with penetrometry giving 1.58–1.76 g/cm³ to 60 cm. 2.0 g/cm³ was not found.
Density does keep rising below 60 cm, so 2000 may well be fine at metre depth —
but not from these pages. **Low stakes**: σ_ρ is 0.007 (A15) and 0.33 (A17).

---

## 7. Not verifiable here

`saito2007`, `nagihara2018`, `mitchell1973` exist as bib entries only. Nagihara
is paywalled and CLAUDE.md already forbids citing it from memory.

---

## Priority

| # | Item | Budget impact | Action |
|---|---|---|---|
| 1 | χ = 1.48 misattribution | headline caveat | relabel, or re-run at 1.5 |
| 2 | Albedo ±0.01 basis | **largest A17 row, 2.96** | state as an assumed envelope |
| 3 | Q_b lower bounds | 1.61 / 1.66 | attribute to Saito/Nagihara or tighten |
| 4 | K_s ±30 % basis | 0.36 / 1.55 | state as assumed, or find the source |
| 5 | ρ_d = 2000 | 0.007 / 0.33 | negligible; leave |
| 6 | Cremers filename says Apollo 11 | none | rename |

## What this does not change

The thesis already describes the totals as *"sensitivity summaries, reliable for
judging which inputs matter, not calibrated standard errors."* Every finding
above is consistent with that claim. What must **not** be said is that the
envelopes are published 1σ values — for albedo, K_s and the Q_b lower bounds,
they are not.


---

## Addendum — 2026-08-17 (PDFs located, two ⚠ resolved, one ❌ found)

**Saito et al. (2007) — bib entry was fabricated, paper is real.** The entry
carried title "Lunar heat flow experiment for SELENE-2", *Adv. Space Res.* 40,
1601–1607, doi:10.1016/j.asr.2007.07.007. That DOI resolves to Vial et al.,
"SMESE (SMall Explorer for Solar Eruptions)", *Adv. Space Res.* **41**, 183–189
(2008) — an unrelated solar-physics paper; the page range 1601–1607 was
duplicated from the (now removed) horai1981 entry. The **real** paper, with the
same five authors and year, is:

> Saito, Tanaka, Takita, Horai & Hagermann (2007), *Lost Apollo heat flow data
> suggest a different lunar bulk composition*, LPSC XXXVIII, Abstract #2197.
> → `references/saito2007_lost_apollo_heat_flow_lpsc38.pdf`

Read in full. It states Langseth's originals as "21 mW/m² and 14 mW/m²", revises
the A17 gradient to 0.312 K/m and infers **3.7 mW/m²** at A17. So the letter's
"lower, Saito-direction fluxes" claim is *correct and now source-verified*, and
the [10,18] sweep is **conservative** — Saito's own value sits below it, and
adopting it would widen the contrast (A17 K_d rises as Q_b falls). Letter
updated to say so.

**Mitchell et al. (1973), NASA CR-134306** → `references/mitchell1973_apollo_soil_mechanics_S200_CR134306.pdf`
(public domain, via LPI). Depth relation ρ = 1.27 + 0.121·ln(z+1) g/cm³ gives
**1.83 g/cm³ at 1 m and 1.93 at 2.3 m**; max observed 1.93 (Jaffe 1972). With
Langseth p. 3154 (A15 cores 1.75–1.90, A17 1.83–2.09), the 1700–2000 kg/m³
sweep is now properly supported at meter depth.

**Nagihara et al. (2018)** remains unavailable — agupubs returns HTTP 402
(paywalled). Still the only claim resting on an unread source.


---

## Addendum 2 — 2026-08-17 (four more PDFs supplied by the author)

All four DOIs matched their bib entries exactly. Now in `references/`.

| Source | Letter's claim | Verdict |
|---|---|---|
| **Nagihara 2018** `10.1029/2018JE005579` | Q_b = 21 / 16 mW m⁻² | ✅ verbatim: *"Endogenic heat flow was then determined to be 21 mW/m2 at Site 15 and 16 mW/m2 at Site 17."* |
| " | restored record spans 1971–1977 | ✅ A15 Jul 1971–Jan 1977; A17 Dec 1972–Sep 1977 |
| " | "±2.5 cm astronaut-emplacement envelope **reported by** Nagihara" | ❌ **MISATTRIBUTED — fixed.** The paper reports no depth uncertainty; its only ± is ±0.05 K sensor accuracy. Its "2.5 cm" is the **probe rod diameter** ("solid rods … 2.5-cm diameter"); "2.5 m" is hole depth. The value is a modelling choice and is now labelled an *adopted* envelope set at the probe-rod diameter, which keeps the citation truthful. |
| **Kopp & Lean 2011** `10.1029/2010GL045777` | S₀ = 1361 W m⁻² | ✅ paper gives **1360.8 ± 0.5**; 1361 is the standard rounding |
| **Bandfield 2015** `10.1016/j.icarus.2014.11.009` | ε = 0.95 | ✅ *"Apparent broadband hemispherical emissivity is **0.951** … for the average daytime"* (nighttime 0.901 — the model's single 0.95 is daytime-weighted, defensible for an insolation-driven balance) |
| **Davies & Colvin 2000** `10.1029/1999JE001165` | lat 26.1° / 20.2° N | ✅ **exact**: ALSEP 15 = 26.13407 N, 3.62981 E; ALSEP 17 = 20.19209 N, 30.76492 E — matches `config.py` (26.13/3.63, 20.19/30.77) to 4–5 s.f. |

Every source the letter cites for a physical number has now been read.
