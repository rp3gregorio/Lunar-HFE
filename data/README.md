# Lunar-V2 external data

This directory holds the external reference datasets the pipeline needs
to run on real terrain and to validate against spacecraft measurements.
**None of these files are tracked in git** — see `.gitignore`. This
README is the manifest that lets someone reproduce the contents.

Directory layout:

```
data/
├── dem/       LOLA polar digital elevation models (PGDA)
├── spice/     NAIF SPICE kernels for solar ephemeris
├── apollo/    Apollo 15/17 Heat Flow Experiment archives (PDS)
├── diviner/   Diviner Polar Cumulative Products (PDS)
├── chaste/    Chandrayaan-3 ChaSTE (not yet downloaded — see below)
└── lcross/    LCROSS ice plume data (not yet downloaded — see below)
```

## 1. DEMs — `data/dem/`

20 m / pixel south polar LOLA DEMs from the NASA GSFC PGDA product 90
archive (Barker et al. 2023), downloaded from
<https://pgda.gsfc.nasa.gov/products/90>.

| File | Resolution | Size | Purpose |
|---|---|---|---|
| `LDEM_80S_20MPP_ADJ.TIF` | 20 m/pixel | ~2.5 GB | primary science run |
| `LDEM_80S_40MPP_ADJ.TIF` | 40 m/pixel | ~670 MB | medium-scale testing |
| `LDEM_80S_80MPP_ADJ.TIF` | 80 m/pixel | ~180 MB | fast iteration |

All three cover latitudes poleward of 80 S in polar stereographic
projection. The DEMs also come with companion `_ERR`, `_EFFRES`, and
`_HILL` layers on the PGDA page — not downloaded by default.

Re-download with:

```bash
cd data/dem
curl -LO https://pgda.gsfc.nasa.gov/data/LOLA_20mpp/LDEM_80S_20MPP_ADJ.TIF
curl -LO https://pgda.gsfc.nasa.gov/data/LOLA_20mpp/LDEM_80S_40MPP_ADJ.TIF
curl -LO https://pgda.gsfc.nasa.gov/data/LOLA_20mpp/LDEM_80S_80MPP_ADJ.TIF
```

## 2. SPICE kernels — `data/spice/`

Generic kernels from NAIF, <https://naif.jpl.nasa.gov/pub/naif/generic_kernels/>.

| File | Size | Purpose |
|---|---|---|
| `naif0012.tls` | 5 KB | Leap-seconds (LSK) |
| `pck00011.tpc` | 130 KB | Body constants (text PCK) |
| `moon_pa_de440_200625.bpc` | 13 MB | Moon principal-axis binary PCK, DE440 |
| `moon_de440_250416.tf` | 20 KB | Moon PA/ME frame definitions |
| `moon_assoc_me.tf` | 9 KB | Binds MOON_ME to the PA chain |
| `de440s.bsp` | 33 MB | DE440 short-span planetary ephemeris (1849-2150) |

Loaded by `lunar.ephem._furnish_kernels`.

Re-download with:

```bash
cd data/spice
curl -LO https://naif.jpl.nasa.gov/pub/naif/generic_kernels/lsk/naif0012.tls
curl -LO https://naif.jpl.nasa.gov/pub/naif/generic_kernels/pck/pck00011.tpc
curl -LO https://naif.jpl.nasa.gov/pub/naif/generic_kernels/pck/moon_pa_de440_200625.bpc
curl -LO https://naif.jpl.nasa.gov/pub/naif/generic_kernels/fk/satellites/moon_de440_250416.tf
curl -LO https://naif.jpl.nasa.gov/pub/naif/generic_kernels/fk/satellites/moon_assoc_me.tf
curl -LO https://naif.jpl.nasa.gov/pub/naif/generic_kernels/spk/planets/de440s.bsp
```

## 3. Apollo 15/17 HFE — `data/apollo/`

PDS Geosciences Node concatenated bundle
`urn:nasa:pds:a15_17_hfe_concatenated` (Nagihara et al. 2018, 2019).
Source index:
<https://pds-geosciences.wustl.edu/missions/apollo/a15_17_hfe_concatenated.htm>.

Structure:

```
apollo/
├── a15/            clean concatenated .tab files for Apollo 15 (14 files, ~20 MB)
├── a17/            clean concatenated .tab files for Apollo 17 (16 files, ~20 MB)
└── depth/          sensor-depth metadata, 4 files (<100 KB total)
```

Each `.tab` has five columns:

```
Time   T   dT   dT_corr   flags
```

where `T` is in K, `dT`/`dT_corr` are differential temperatures [K],
and `Time` is the archived sensor clock. Depth metadata are in the
companion `depth/` files.

Loaded via `lunar.validation.load_apollo_hfe_temperature` and
`load_apollo_hfe_depth`.

Re-download with:

```bash
cd data/apollo
BASE="https://pds-geosciences.wustl.edu/lunar/urn-nasa-pds-a15_17_hfe_concatenated/data"
# Probe files
for m in a15 a17; do
  mkdir -p "$m"
  curl -sL "$BASE/clean/$m/" | grep -oE "href=\"[^\"]*\\.tab\"" \
    | sed 's/href="//; s/"$//' | while read p; do
      curl -sLo "$m/$(basename $p)" "https://pds-geosciences.wustl.edu$p"
    done
done
# Depth tables
mkdir -p depth
for f in a15p1 a15p2 a17p1 a17p2; do
  curl -sLo "depth/${f}_depth.tab" "$BASE/depth/${f}_depth.tab"
done
```

## 4. Diviner — `data/diviner/`

LRO Diviner Polar Cumulative Products (PCP) — Williams et al. (2019,
2020), PDS bundle `urn:nasa:pds:lro_diviner_derived1`. Source index:
<https://pds-geosciences.wustl.edu/missions/lro/diviner.htm>.

Downloaded so far (240 PPD south polar, summer season diurnal bins):

| File | Local time | Size |
|---|---|---|
| `pcp_avg_tbol_pols_sum_ltim13_240.tab` | 13:00 (noon) | ~200 MB |
| `pcp_avg_tbol_pols_sum_ltim01_240.tab` | 01:00 (midnight) | ~200 MB |

The full PCP bundle covers 24 diurnal bins × 12 seasonal bins for
both poles (north/south) and is ~30 GB total. Only the two samples
above are kept in `data/` for validation; pull more on demand.

Loaded via `lunar.validation.load_diviner_pcp_polar`.

Re-download with (adjust `ltim13` / `pols` / `sum` as needed):

```bash
cd data/diviner
BASE="https://pds-geosciences.wustl.edu/lro/urn-nasa-pds-lro_diviner_derived1/data_derived_pcp/diurnal/ltim/pols"
curl -LO "$BASE/pcp_avg_tbol_pols_sum_ltim13_240.tab"
curl -LO "$BASE/pcp_avg_tbol_pols_sum_ltim01_240.tab"
```

## 5. ChaSTE (Chandrayaan-3) — `data/chaste/` (not yet downloaded)

Vadawale et al. (2024, *Nature Communications Earth & Environment*)
reported the first in-situ lunar subsurface thermophysical profile
(~70 S). ISRO has not yet mirrored the raw data on a public archive
equivalent to PDS. When the public release becomes available, place it
here as `chaste/chaste_profile.csv`.

## 6. LCROSS — `data/lcross/` (not yet downloaded)

LCROSS Cabeus impact volatile abundances (Colaprete et al. 2010) are
available as PDS datasets and supplementary tables on the paper; we
only need one set of values as priors for `phi_ice`, not a full
mission archive. Drop them here as `lcross/volatiles.csv` when needed.
