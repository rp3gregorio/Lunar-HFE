# References

One flat folder of PDF copies of the papers this project stands on. They exist
so physics claims can be grounded against the actual source material instead of
memory (see the anti-hallucination protocol in `CLAUDE.md`).

**These PDFs are copyrighted and local-only.** `.gitignore` already excludes
`code/references/**/*.pdf`; keep it that way. Only this README is tracked.

Filenames lead with the citation key. If you add a paper, follow the same
pattern (`nagihara2018_restored_apollo_hfe.pdf`) and add a row below.

## Tier 1 — the foundation

| File | Paper | Why it matters |
|---|---|---|
| `hayne2017_global_regolith.pdf` | Hayne et al. 2017, *JGR:Planets* **122**, 2371. [doi:10.1002/2017JE005387](https://doi.org/10.1002/2017JE005387) | Source of the K(T,z) form we fit — the fixed shape parameters (K_s = 7.4e-4, H ≈ 6 cm, χ) and the global K_d = 3.4 we re-measure per site. Read the conductivity/density profile section and the T³ radiative term closely. |
| `langseth1976_revised_heat_flow_FULL.pdf` | Langseth, Keihm & Peters 1976, *Proc. 7th LSC*, 3143. [ADS](https://ui.adsabs.harvard.edu/abs/1976LPSC....7.3143L) | Where the basal fluxes Q_b (21 / 16 mW m⁻²) we hold fixed come from, plus the original in-situ conductivity analysis. Q_b is the single largest error term and the result is conditional on it, so these numbers and their ~±15 % uncertainty must be defensible. |
| `apollo_hfe_final_technical_report.pdf` | Apollo HFE Final Technical Report. [PDS](https://pds-geosciences.wustl.edu/Lunar/urn-nasa-pds-apollodoc/document_common/lunar_heat_flow_experiment_final_technical_report.pdf) | Instrument design, deployment, sensors, borestems, drill, calibration — how the experiment was actually meant to work. Grounds the borestem exclusion zone and the stability-window logic. |
| `carrier1991_lunar_sourcebook_ch09_physical_properties.pdf` | Carrier, Olhoeft & Mendell 1991, *Lunar Sourcebook* ch. 9. [LPI](https://www.lpi.usra.edu/publications/books/lunar_sourcebook/pdf/Chapter09.pdf) | Regolith density, porosity, grain-size distribution — why lunar regolith is unlike ordinary terrestrial soil. Read first for physical intuition. |

## Tier 2 — model comparison and material properties

| File | Paper | Why it matters |
|---|---|---|
| `martinez2021_conductivity_model.pdf` | Martínez & Siegler 2021, *JGR:Planets*. [doi:10.1029/2021JE006829](https://doi.org/10.1029/2021JE006829) · [code](https://zenodo.org/records/12586656) | The alternative K(T,ρ) model compared against Hayne in the letter. |
| `martinez2021_model_lpsc2022_summary.pdf` | LPSC 2022 summary of the above. [PDF](https://www.hou.usra.edu/meetings/lpsc2022/pdf/2754.pdf) | Open short-form version of the same model — quicker orientation. |
| `hemingway1973_specific_heats_lunar.pdf` | Hemingway et al. 1973, *Proc. LSC 4*, 2481. [ADS](https://ui.adsabs.harvard.edu/abs/1973LPSC....4.2481H/abstract) | Specific-heat measurements behind the solver's c_p(T) polynomial. |
| `vasavada2012_diviner_equatorial.pdf` | Vasavada et al. 2012, *JGR:Planets*. [doi:10.1029/2011JE003987](https://doi.org/10.1029/2011JE003987) | Diviner surface-temperature modelling and the near-surface thermophysical context behind Hayne-style models. |
| `cremers1971_apollo12_fines.pdf` | Cremers & Birkebak 1971 | Laboratory conductivity of Apollo **12** fines (sample 12001,19): 1.2 to 3.5 mW/m/K over 160-428 K at 1300 kg/m^3. One sample, one density -- a temperature dependence, NOT a +/-30% scatter. |
| `wood2020_porosity_conductivity.pdf` | Wood 2020 | Porosity–conductivity relationship for granular media. |
| `feng2020_thermal_dielectric.pdf` | Feng et al. 2020, *JGR:Planets*. [doi:10.1029/2019JE006130](https://doi.org/10.1029/2019JE006130) | CE-2 microwave + Diviner constraints on regolith thermal/dielectric structure. |

## Tier 3 — cross-checks and modern context

| File | Paper | Why it matters |
|---|---|---|
| `grott2010_apollo_heat_flow_revisited_epsc_abstract.pdf` | Grott et al. 2010, EPSC. [PDF](https://meetingorganizer.copernicus.org/EPSC2010/EPSC2010-49-1.pdf) · full: [doi:10.1029/2010JE003612](https://doi.org/10.1029/2010JE003612) | Independent reassessment of the Apollo heat-flow values. |
| `grott2010_apollo_thermal_conductivity_lpsc_abstract.pdf` | Grott et al. 2010, LPSC. [PDF](https://elib.dlr.de/63808/1/Grott_LPSC_2010.pdf) | Companion abstract on the conductivity side of the same reassessment. |
| `feng2020_thermal_gradient_lpsc_abstract.pdf` | Feng et al. 2020, LPSC. [PDF](https://www.hou.usra.edu/meetings/lpsc2020/pdf/2786.pdf) | Short-form thermal-gradient result. |
| `white2022_apollo_hfe_implications_lpsc_abstract.pdf` | White et al. 2022, LPSC. [PDF](https://www.hou.usra.edu/meetings/lpsc2022/pdf/2485.pdf) | Recent HFE context and implications for lunar thermophysical properties. |
| `chaste2025_chandrayaan3_insitu_conductivity.pdf` | Chaste et al. 2025, *Sci. Rep.* [doi:10.1038/s41598-025-91866-4](https://doi.org/10.1038/s41598-025-91866-4) | Modern landed in-situ conductivity measurement — an independent comparison point. |

## Still missing (paywalled — fetch via institutional access)

The most important gap is **Nagihara et al. 2018**, since it is the restored
Apollo temperature record this project compares against.

- Nagihara et al. 2018, restored Apollo 15/17 HFE data — [doi:10.1029/2018JE005579](https://doi.org/10.1029/2018JE005579)
- Saito et al. 2007, SELENE-2 heat-flow discussion — [doi:10.1016/j.asr.2007.07.007](https://doi.org/10.1016/j.asr.2007.07.007)

Drop any retrieved PDFs straight into this folder and add a row above.
