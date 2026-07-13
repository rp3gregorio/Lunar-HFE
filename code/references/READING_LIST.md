# Reference reading list — Apollo K_d retrieval

Papers that ground this project, **ordered by how important they are for you to
read** (and to defend the letter). Three are already downloaded here; the four
AGU/Wiley papers are paywalled — grab them through your institution via the DOI
links below and drop the PDFs in this folder, and I'll wire them into the
guidebook bibliography.

> ✅ = PDF in this folder &nbsp;&nbsp; 🔒 = paywalled, link only

---

## Tier 1 — the foundation (read these first, in order)

**1. Hayne et al. (2017)** 🔒 — *the conductivity model you stand on*
> Global Regolith Thermophysical Properties of the Moon From the Diviner Lunar
> Radiometer Experiment. *JGR: Planets* **122**, 2371–2400.
> doi:[10.1002/2017JE005387](https://doi.org/10.1002/2017JE005387)
- This is the source of the $K(T,z)$ form you fit, the fixed shape parameters
  ($K_s=7.4\times10^{-4}$, $H\approx6$–7 cm, $\chi$), and the **global
  $K_d=3.4$** you re-measure per site. Read §on the conductivity/density
  profiles and the $T^3$ radiative term most carefully.

**2. Langseth, Keihm & Peters (1976)** ✅ `langseth1976_revised_heat_flow_FULL.pdf`
> The Revised Lunar Heat Flow Values. *Proc. 7th Lunar Sci. Conf.*, 3143–3171.
> ADS:[1976LPSC....7.3143L](https://ui.adsabs.harvard.edu/abs/1976LPSC....7.3143L)
- Where the **basal fluxes $Q_b$ (21 / 16 mW m⁻²)** you hold fixed come from,
  and the original in-situ conductivity analysis. Since $Q_b$ is your single
  largest error term and the result is *conditional* on it, you must be able to
  defend these numbers and their ~±15% uncertainty.

**3. Nagihara et al. (2018)** 🔒 — *the data you actually fit*
> Examination of the Long-Term Subsurface Warming … Newly Restored Heat Flow
> Experiment Data From 1975 to 1977. *JGR: Planets* **123**, 1125–1139.
> doi:[10.1029/2018JE005579](https://doi.org/10.1029/2018JE005579)
- The restored 1975–77 record is your dataset. Read for the digitisation
  procedure and the depth/temperature uncertainties that feed your bootstrap
  (the ~2.5 cm depth jitter), and the long-term subsurface warming caveat.

## Tier 2 — cross-checks and model inputs

**4. Martínez & Siegler (2021)** 🔒 — *your independent cross-check model*
> A Global Thermal Conductivity Model for Lunar Regolith at Low Temperatures.
> *JGR: Planets* **126**(10), e2021JE006829.
> doi:[10.1029/2021JE006829](https://doi.org/10.1029/2021JE006829) ·
> code: [Zenodo](https://zenodo.org/records/12586656)
- The density-based $K(T,\rho)$ used in your $\alpha$-sweep cross-check. The
  model source code is openly on Zenodo (`lunar1Dheat`) — useful to compare
  against your solver.

**5. Vasavada et al. (2012)** 🔒 — *the Diviner surface model*
> Lunar Equatorial Surface Temperatures and Regolith Properties from the Diviner
> Lunar Radiometer Experiment. *JGR: Planets* **117**, E00H18.
> doi:[10.1029/2011JE003987](https://doi.org/10.1029/2011JE003987)
- Background for the Diviner surface-temperature closure cross-check; the graded
  near-surface density/conductivity picture your model also produces.

**6. Hemingway, Robie & Wilson (1973)** ✅ `hemingway1973_specific_heats_lunar.pdf`
> Specific Heats of Lunar Soils, Basalt, and Breccias … between 90 and 350 K.
> *Proc. 4th Lunar Sci. Conf.*, vol. 4, 2481.
> ADS:[1973LPSC....4.2481H](https://ui.adsabs.harvard.edu/abs/1973LPSC....4.2481H)
- The $c_p(T)$ polynomial used by the solver. Short; read to confirm the
  temperature range of validity matches your model's use.

## Tier 3 — recent context (optional but worth it)

**7. ChaSTE / Chandrayaan-3 team (2025)** ✅ `chaste2025_chandrayaan3_insitu_conductivity.pdf`
> Thermal conductivity of high-latitude lunar regolith measured by ChaSTE
> onboard the Chandrayaan-3 lander. *Scientific Reports* **15**.
> doi:[10.1038/s41598-025-91866-4](https://doi.org/10.1038/s41598-025-91866-4) (open access)
- The first new *in-situ* lunar regolith conductivity measurement since Apollo —
  an independent yardstick for your retrieved $K_d$ values and a strong citation
  for the introduction/discussion.

---

### Suggested reading order
**1 → 2 → 3** gives you the model, the heat-flow boundary condition, and the
data — everything needed to defend the core retrieval. **4 → 5** are the
cross-checks; **6** is a solver input; **7** is the modern comparison point.
