# LOLA DEM — resolution and how to go finer

The horizon / shadowing model reads a **LOLA LDEM** (Lunar Orbiter Laser
Altimeter Digital Elevation Model), global equirectangular, int16, 0.5 m per
DN. `s1_sensitivity.load_dem()` **auto-selects the finest `ldem_<ppd>.img`
present here** and memory-maps it (only the ~10⁴ sampled points per site are
read from disk), so a finer DEM is a pure drop-in — no code change.

## Present in this repo
| file | ppd | pixel | file size | status |
|---|---|---|---|---|
| `ldem_4.img`  | 4  | 7.6 km | 2 MB  | coarse fallback |
| `ldem_16.img` | 16 | 1.9 km | 32 MB | **currently used** |

## Is 16 ppd fine enough? — No, not yet converged
The site horizon is still **rising with resolution** from 4 → 16 ppd, so the
16 ppd numbers are a **lower bound**:

| site | 4 ppd (7.6 km) | 16 ppd (1.9 km) |
|---|---|---|
| A15 max horizon / loss | 3.9° / 0.02% | 14.0° / 1.16% |
| A17 max horizon / loss | 8.1° / 0.15% | 10.1° / 0.18% |

A15's Apennine front and A17's Taurus–Littrow massifs are both under-resolved at
1.9 km/px; a finer DEM will raise the horizons (more shadowing), most at A17.
(Shadowing is a small, sub-K effect, so this does **not** move the density
result — but it makes the shadowing numbers themselves defensible.)

## To go finer — drop a finer file here, nothing else
Source (PDS Geosciences, same format, drop-in):
`https://pds-geosciences.wustl.edu/lro/lro-l-lola-3-rdr-v1/lrolol_1xxx/data/lola_gdr/cylindrical/img/`

| file | ppd | pixel | download | vs 16 ppd |
|---|---|---|---|---|
| `ldem_64.img`  | 64  | 473 m | 506 MB | 4× finer |
| `ldem_128.img` | 128 | 237 m | 2.0 GB | 8× finer |

After downloading, just place the `.img` (and matching `.lbl`) in this folder and
re-run `s1_sensitivity.py` → the whole pipeline uses it automatically. The
ray-march step auto-shrinks to one pixel, so the finer terrain is actually
sampled.

## SLDEM2015 (~59 m/px) — DONE for A15/A17 (regional crops in `sldem2015/`)
`sldem2015/{A15,A17}.f32` are ±1.5° lat × ±2° lon float32 crops (km topography,
512 ppd) fetched from the PDS tile `sldem2015_512_00n_30n_000_045_float.img`
(1.35 GB) by **HTTP range** — only the ~140 MB latitude band per site, cropped
to 12.6 MB each. Regenerate: `fetch_sldem2015.py`. `<site>.json` carries the
geotransform (`lat_top`, `lon_left`, `ppd`).

**What 59 m/px changed** (both marched to r_max = 40 km, apples-to-apples):

| site | 16 ppd (1.9 km) max / loss | SLDEM2015 (59 m) max / loss |
|---|---|---|
| A15 | 14.0° / 1.16% | 13.6° / **0.54%** (was OVER-estimated) |
| A17 | 10.1° / 0.10% | 14.1° / **0.24%** (was UNDER-estimated) |

So 16 ppd was wrong in **both directions** — the coarse grid inflated A15's
sunrise/sunset horizon and missed A17's near-field North Massif. The SLDEM values
are the defensible ones. (Shadowing is still a sub-K effect, so the density
result is unchanged; but the shadowing numbers themselves now stand up.)

To actually PROPAGATE these into the pipeline, the horizon computation must read
the crops (a `site_horizon()` that prefers `sldem2015/<site>.f32`) and the
shadowed sweeps re-run — that step changes the published loss/horizon numbers, so
it is a conscious re-run, not automatic.

**Finest still:** LROC NAC DTMs (~2 m/px) — highest resolution, but footprints of
only a few km, too small for the horizon march (good only for the immediate field).
