# Diviner Lunar Radiometer data

This directory caches data products from the Diviner Lunar Radiometer
Experiment on board the Lunar Reconnaissance Orbiter (LRO). Files are
not committed to the repository — see `.gitignore`. Only the small
PDS label files (`*.lbl`, `*.FMT`) are tracked so the schema is
self-documenting.

## Sources

| Product | Subdir | PDS bundle | Citation |
| --- | --- | --- | --- |
| GCP — Global Cumulative Product (2 ppd × 0.25 hr LT) | `gcp/` | `urn:nasa:pds:lro_diviner_derived1` | Williams et al. (2017) Icarus 283, 300-325 |
| PCP — Polar Cumulative Product (240 ppd, polar caps) | `pcp/` | same | Williams et al. (2019) JGR Planets 124, 2505-2521 |

PDS landing page: <https://pds-geosciences.wustl.edu/missions/lro/diviner.htm>
GCP DOI: 10.17189/1520650.

Time range covered by GCP v1: 2009-07-05 to 2015-04-01.

## How to fetch

The Phase-2 Martinez & Siegler (2021) replication uses a six-band
subset of GCP. Bootstrap with:

```bash
python scripts/download_diviner_gcp.py
```

This pulls ~940 MB into `gcp/`. Re-running is a no-op once cached. The
loader is `lunar.diviner.load_gcp_band(lat_min, lat_max)`.

## File layout

```
gcp/
  DLRE_GCP.FMT                                  # column schema (PDS3)
  global_cumul_avg_cyl_<band>_002.lbl           # detached PDS3 label per band
  global_cumul_avg_cyl_<band>_002.tab           # 156 MB fixed-width data
```

Latitude bands are 10° wide and named `aaXbbY` where X, Y ∈ {n, s}. North
bands are min-max (`00n10n` = 0..10°N). South bands are written deeper-
south first (`80s70s` = 70..80°S, `90s80s` = 80..90°S).

## Column schema (GCP)

113-byte fixed-width ASCII records, 11 columns: `clon, clat, ltim, t3,
t4, t5, t6, t7, t8, t9, tbol`. Sentinel `-9999` flags a bin with no
observations; `-9998` flags only-invalid radiances.

## Phase-2 validation subset

Bands needed for the LPSC 2022 abstract figure replication (see
`docs/martinez_replication_plan.md`):

| Lat band | Used for | Channels of interest |
| --- | --- | --- |
| 0..10°N | low-latitude diurnal | T7, Tbol |
| 30..40°N | mid-lat mare | T7, Tbol |
| 40..50°N | **LPSC Fig 2** (45°N highlands) | T7 |
| 60..70°N | mid-high lat | T7, Tbol |
| 80..90°N | high-lat highlands | T7, Tbol |
| 80..90°S | **LPSC Figs 3-5** (Shoemaker PSR at 87.91°S) | T9, Tbol |
