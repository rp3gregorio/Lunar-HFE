# Diviner surface temperatures

The Diviner Global Cumulative Product (GCP; Williams et al., 2017), used for
the surface-temperature comparison of SI Table S13. Only the PDS labels
(`*.lbl`) and the column format (`DLRE_GCP.FMT`) are in git. The two data
tables, the 10-20 N and 20-30 N latitude bands that hold the sites (about
310 MB), are downloaded by

```bash
python code/pipeline/fetch_diviner.py
```

Source: PDS bundle `urn:nasa:pds:lro_diviner_derived1`, GCP doi:10.17189/1520650,
<https://pds-geosciences.wustl.edu/missions/lro/diviner.htm>. The product
covers 2009-07-05 to 2015-04-01 at 0.5 degree and 0.25 h of local time.

Each `global_cumul_avg_cyl_<band>_002.tab` is a fixed-width ASCII table of
113-byte records with 11 columns: `clon, clat, ltim, t3 ... t9, tbol`. The value
-9999 marks a bin with no observations and -9998 one with only invalid
radiances. `lunar.diviner.load_gcp_band(lat_min, lat_max)` reads a band.
