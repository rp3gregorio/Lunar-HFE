# Upstream data — Martinez & Siegler (2021)

Files in this directory are bit-for-bit copies of small data products from
the Martinez & Siegler (2021) MATLAB code release, included so the Phase 2
notebooks can reproduce the published figures without requiring the user to
clone the upstream repository.

## Provenance

> Martinez, A. & Siegler, M. A. (2021). *A Global Thermal Conductivity Model
> for Lunar Regolith at Low Temperatures.* JGR: Planets 126, e2021JE006829.
>
> Code release: `angelicam01/lunar1Dheat` v1.6 (GitHub).
> Archived: Zenodo, [DOI 10.5281/zenodo.12586656](https://doi.org/10.5281/zenodo.12586656).

## Files

| File | Original location in upstream | Used by |
| --- | --- | --- |
| `shoemakerIllumination.mat` | `lunar1Dheat/PSRShoemaker/data/shoemakerIllumination.mat` | `notebooks/phase2/03_psr_shoemaker.ipynb` |

## `shoemakerIllumination.mat` contents (697 time samples, 14 KB)

| Field | Shape | Range | Meaning |
| --- | --- | --- | --- |
| `IRillumination` | (697, 1) | 0.0005 .. 0.82 W/m² | Thermal-IR re-emission from sunlit crater walls onto the floor |
| `visibleillumination` | (697, 1) | 0 .. 0.13 W/m² | Scattered visible light from sunlit walls onto the floor |
| `juliandate` | (697, 1) | 2.46e6 .. 2.46e6 | Time stamp (Julian date) |
| `latitude` | (697, 1) | constant -87.91° | Shoemaker tile latitude |
| `longitude` | (697, 1) | constant 45.51° | Shoemaker tile longitude |
| `daveTemp` | (697, 1) | 22.5 .. 63.5 K | Dave-Paige-pipeline reference T from Diviner mosaicking |
| `date` | (697, 1) | 5e3 .. 6e3 (days) | Alternative time axis |

The radiosity values were precomputed by the Martinez & Siegler ray-tracing
pipeline using LOLA topography; this is the same time series their published
Shoemaker figures are driven from.
