# Study-phase slides — one build prompt per phase

Companion to `SLIDE_PROMPTS.md`. Five phases, one reference slide each, plus
the master chart that opens the section. Renders in `img/`; rebuild with
`python documents/gedes/defense/make_phase_slides.py`.

**Scope, corrected 2026-07-29.** Phase 1 *is* the thesis — complete, submitted,
and the ChaSTE/Chang'E benchmark is no longer part of it. Phase 2 *is* the AOGS
terrain work — the DEM exists and is applied **at the two Apollo sites only**.
Going Moon-wide is its own phase, not a loose end inside Phase 2. Every number
below is certified against `code/results/*.json` and `documents/aogs/results/*.json`.

| | Phase | Status | Deliverable |
|---|---|---|---|
| 1 | The thesis | **COMPLETE** | two calibrated ground-truth anchors |
| 2 | Terrain at the Apollo sites | **COMPLETE** | a terrain-aware, layered retrieval |
| 3 | Go global | NEXT | a validated Moon-wide temperature map |
| 4 | TSUKIMI coupling + ice | PLANNED | an ice-survivability map |
| 5 | Model physics upgrades | HORIZON | next-generation regolith model |

---

## Master chart — opens the section

**Art:** `study_phases_flow.png` (3040 × 1500) · **Title:** Five phases, and
where the work actually stands · **Take:** Two are delivered; three are
scheduled against them.

Five columns sharing one skeleton so the eye compares across: status chip ·
progress bar · guiding question · itemised tasks (drawn ✓ done, open ○ planned)
· what it is scored against · deliverable band. A **dashed vertical rule between
Phase 2 and 3 splits DELIVERED from PROPOSED** — the single most important line
on the chart. Timeline of diamonds below; dashed return arrow shows Phase-5
physics upgrades re-running the Phase-3 global products.

**Say (~40 s):** name the five headings, then point at the divider: *"everything
left of this line exists and has been presented; everything right of it is the
proposal."* Stop there. The detail is for reading, not narrating.

---

## Phase 1 — the thesis · COMPLETE

**Art:** `phase1_slide.png` · forest · 100 %
**Title:** The thesis: two ground-truth anchors, delivered
**Take:** Both boreholes reproduced, every claim stress-tested, and the limits
stated honestly.

**Left (all ✓):** per-site K_d 4.60 / 7.08, misfit 1.09→1.00 and 0.89→0.40 K ·
1500-draw bootstrap, tail 0.031, MCMC ordering 99.2 % · AICc A17 −23.2, A15
+2.9, stated honestly · held-out plus Diviner surface closure, both
out-of-sample · error budget audited to source (±1.88 / ±3.88, χ conditional).

**Right:** the two bars against the dashed global 3.4, then three stat chips.
Footnote: *Apollo 15 alone does not justify a separate fit — the case there
rests on the interval.*

**Say (~50 s):** the numbers, then the honesty. Volunteering the AICc split is
worth more than defending it under question.

---

## Phase 2 — terrain at the Apollo sites · COMPLETE

**Art:** `phase2_slide.png` · teal · 100 %
**Title:** Real terrain, at the two sites we can check
**Take:** The DEM machinery is built and applied where ground truth exists —
and terrain turns out to matter a great deal.

**Left (all ✓):** DEM horizon algorithm (16 ppd, 90 azimuths) · applied at both
sites, horizons 14.0° / 10.1°, insolation −1.16 % / −0.18 % · re-retrieval under
shadowing, K_d 4.60→1.88 and 7.08→9.69 · 650-run density study, density sets
conductivity not c_p · layered physics transfers between sites, 2.31–3.76 →
0.36–0.90 K.
**Scored against:** *two sites only — deliberately not yet global.*

**Right — the headline finding.** Before/after arrows for each site showing the
K_d shift under real terrain, then the punchline in bold: **the two sites move
in opposite directions — terrain cannot be averaged away.** Plus two chips:
sky-view factor 0.985 / 0.991, and *adding IR self-heating made the fit worse*.

**Say (~55 s):** this is the strongest slide in the plan. Terrain shifts A15
down by 2.72 and A17 up by 2.61 — opposite signs, so no global correction
factor can absorb it. That is precisely the argument for doing it properly
Moon-wide, which is Phase 3. Say the IR result too: a negative finding you
report yourself reads as rigour.

---

## Phase 3 — go global · NEXT

**Art:** `phase3_slide.png` · gold · 5 %
**Title:** From two neighbourhoods to the whole Moon
**Take:** Same physics, same solver. What remains is scale, and the solver
already makes it affordable.

**Left (all ○):** tile the solver over the DEM grid · Moon-wide horizons beyond
the two Apollo neighbourhoods · sub-surface T(z) everywhere to annual-wave depth
· validate against Diviner global composites · publish the gridded product.

**Right:** three stacked steps — tile the DEM grid → Moon-wide T(z) → Diviner
validation — then a boxed feasibility argument: *one column ≈ 1 s; the
flux-anchored solver is ≈ 2500× faster than brute force.* Closing line: *the DEM
machinery already exists; this phase is scale, not new physics.*

**Say (~50 s):** the honest framing is that nothing here is a research risk —
it is compute and validation. The 2500× is what turns "millions of columns" from
impossible into a weekend.

---

## Phase 4 — TSUKIMI coupling + ice · PLANNED

**Art:** `phase4_slide.png` · coral · 0 %
**Title:** Coupling to TSUKIMI: from temperature to ice
**Take:** The temperature field becomes terahertz brightness, and finally an
ice-survivability map.

**Right — the chain**, four stacked boxes: sub-surface T(z) field *(delivered by
Phase 3)* → TSUKIMI radiative transfer *(NICT)* → THz brightness temperature →
ice-survivability map. Closing line: *THz emission originates below the diurnal
skin — exactly the region this model was built to resolve.*

**Say (~50 s):** the "why me, why here" slide. The chain only works if someone
supplies a trustworthy sub-surface profile — which is what Phases 1–3 build.
Name the NICT link explicitly.

---

## Phase 5 — physics upgrades · HORIZON

**Art:** `phase5_slide.png` · plum · 0 %
**Title:** Beyond: the next-generation regolith model
**Take:** Three physics upgrades, each weighed by difficulty and scientific
impact before any is attempted.

**Right:** a difficulty × impact scatter placing H(z) compaction, ε(T) for PSRs,
and vapor diffusion + latent heat — so the sequencing argument is visual.
Closing line: *the vapor-diffusion term is genuinely new physics — high risk,
and precisely why it is scheduled last.*

**Say (~45 s):** the point is not the three ideas, it is that they were
*weighed*. Do not promise the vapor-diffusion term.

---

## If you are short on time

Master chart + **Phase 2** + **Phase 3**. Phase 2 carries the opposite-signs
finding, which is the evidence; Phase 3 carries the feasibility argument. Phase 1
is already covered by the thesis defense itself, and 4–5 can be one sentence
each off the master chart.
