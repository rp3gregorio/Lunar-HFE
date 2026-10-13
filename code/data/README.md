# Input data

Everything the analysis reads. The Apollo record, the SPICE kernels and the
site-map crops are in the repository; two larger public data sets are
downloaded only if you want to recompute the steps that use them.

| Folder | What | Source | In git |
|---|---|---|---|
| `apollo/depth/` | the restored Apollo 15 and 17 Heat-Flow Experiment record, one table per probe (`a15p1`, `a15p2`, `a17p1`, `a17p2`): time, temperature (K), sensor, depth (cm), quality flag | PDS Geosciences bundle `urn:nasa:pds:a15_17_hfe_concatenated` (Nagihara et al., 2018), <https://pds-geosciences.wustl.edu/missions/apollo/a15_17_hfe_concatenated.htm> | yes (38 MB) |
| `spice/` | JPL ephemeris DE440 and the lunar frame kernels, for the Sun's position | NAIF generic kernels, <https://naif.jpl.nasa.gov/pub/naif/generic_kernels/> | yes |
| `apollo_site_maps/` | landing-site NAC mosaics and EVA traverses for SI Figure S1 (`meta.json` records the request) | LROC Lunaserv WMS, made by `pipeline/fetch_apollo_site_maps.py` | yes |
| `lola_relief/` | shaded-relief crops around the two sites for SI Figure S1 | LOLA, made by `pipeline/extract_lola_relief.py` | yes |
| `diviner/gcp/` | Diviner global cumulative surface temperatures, the two latitude bands of the sites (~310 MB); only the labels are in git | PDS bundle `urn:nasa:pds:lro_diviner_derived1` (Williams et al., 2017), GCP DOI 10.17189/1520650; download with `pipeline/fetch_diviner.py` | labels only |
| `lola/ldem_16.img` | global LOLA elevation, 16 pixels per degree (33 MB), for SI Figure S1 | PDS LOLA GDR, <https://pds-geosciences.wustl.edu/lro/lro-l-lola-3-rdr-v1/lrolol_1xxx/data/lola_gdr/cylindrical/img/ldem_16.img> | no |

The Apollo tables are read by `lunar.validation.load_apollo_hfe_depth`, and
each sensor's stability window is found by
`lunar.apollo_helpers.extract_sensor_stability`.

The two downloads are optional: notebook `00_setup` fetches them
(`DOWNLOAD = True`), or see `documents/notes/REPRODUCING.md`, Step 3. Without
them, the stored results and every other step still work. The LOLA albedo map
used for the site-albedo comparison (SI Table S4) is read pixel by pixel from
PDS by `compute_albedo_diagnostics.py` and needs no download.
