#!/usr/bin/env python3
"""Extract per-site LOLA shaded-relief crops for the context-map figure.

The letter's context map (Fig. 1) renders each landing site as a LOLA
topographic shaded-relief inset, so the Apennine front at Apollo 15 and
the Taurus-Littrow massifs at Apollo 17 read directly from the terrain
rather than from an albedo mosaic. This script cuts the two regional
elevation crops the figure consumes.

Source (LOLA LDEM, 16 pixels/degree global topographic map):
  data/lola/ldem_16.img
  16-bit signed integers, row-major, 2880 rows x 5760 cols, elevation in
  units of 0.5 m relative to a 1737.4 km reference sphere. Row 0 is the
  north pole (+90 deg); column 0 is longitude -180 deg.
    lat  ->  row = (90 - lat) * 16
    lon  ->  col = (lon + 180) * 16

Each crop spans +/-15 deg longitude, +/-10 deg latitude about the site
(matching ZOOM_DLON/ZOOM_DLAT in make_context_map_figure.py): 480 cols
by 320 rows, stored as float32 in km, N-up. Writes:
  data/lola_relief/A15.npy
  data/lola_relief/A17.npy

These crops are committed so the figure builds without the (156 MB)
LDEM; re-run this only if the crop window or source changes.

Usage
-----
    python pipeline/extract_lola_relief.py            # from code/
"""
from __future__ import annotations

import pathlib
import sys

import numpy as np

ROOT = pathlib.Path(__file__).resolve().parents[1]          # code/
sys.path.insert(0, str(ROOT / "src"))

from lunar.config import SITES  # noqa: E402  (single source of site coords)

PPD = 16                      # pixels per degree of the LDEM
N_ROWS, N_COLS = 2880, 5760   # LDEM_16 dimensions
ELEV_SCALE_KM = 0.5e-3        # DN units of 0.5 m -> km

LDEM = ROOT / "data" / "lola" / "ldem_16.img"
OUT = ROOT / "data" / "lola_relief"

# Half-widths of the crop window (must match make_context_map_figure.py)
ZOOM_DLON = 15.0
ZOOM_DLAT = 10.0


def load_ldem():
    if not LDEM.exists():
        raise FileNotFoundError(
            f"LDEM source not found at {LDEM}. It ships with the AOGS "
            "assets (data/lola/ldem_16.img); the committed crops in "
            f"{OUT} let the figure build without it.")
    dem = np.fromfile(LDEM, dtype="<i2").reshape(N_ROWS, N_COLS)
    return dem.astype(np.float32) * ELEV_SCALE_KM        # km


def crop_site(dem, lat0, lon0):
    """Return the N-up elevation crop (km) centred on (lat0, lon0)."""
    row0 = int(round((90.0 - lat0) * PPD))
    col0 = int(round((lon0 + 180.0) * PPD))
    dr = int(round(ZOOM_DLAT * PPD))     # 160 -> 320 rows total
    dc = int(round(ZOOM_DLON * PPD))     # 240 -> 480 cols total
    return dem[row0 - dr:row0 + dr, col0 - dc:col0 + dc].copy()


def main():
    dem = load_ldem()
    OUT.mkdir(parents=True, exist_ok=True)
    for name, s in SITES.items():
        crop = crop_site(dem, s["lat"], s["lon"])
        out = OUT / f"{name}.npy"
        np.save(out, crop)
        print(f"  {name}: {crop.shape} crop, relief "
              f"{crop.max() - crop.min():.2f} km  -> {out}")


if __name__ == "__main__":
    main()
