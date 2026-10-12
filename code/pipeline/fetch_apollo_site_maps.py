#!/usr/bin/env python3
"""Fetch the landing-site basemaps and EVA traverses for SI Figure S1 (e, f).

Source: the LROC Lunaserv WMS (Arizona State University), the same layers the
LROC "featured sites" traverse maps show:
  luna_apollo_{15,17}_high_resolution_nac_mosaic   NAC orthomosaic (basemap)
  luna_apollo_{15,17}_eva{1,2,3}                   EVA traverses mapped by the
                                                   LROC team (rendered lines)
Requested in simple cylindrical lon/lat (EPSG:4326 on the lunar sphere) with
TRANSPARENT=TRUE, so areas without NAC data come back with alpha 0.

Writes data/apollo_site_maps/{A15,A17}_nac.png (8-bit gray + alpha),
{A15,A17}_eva{1,2,3}.png (1-bit masks) and meta.json (boxes, layers, date).
Run once; the figure script only reads the saved files.
"""
from __future__ import annotations
import datetime
import io
import json
import pathlib
import ssl
import urllib.parse
import urllib.request

import numpy as np
from PIL import Image

ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "apollo_site_maps"
WMS = "https://wms1.im-ldi.com/"

# lon_min, lat_min, lon_max, lat_max: the traverses plus a margin, inside NAC coverage
BOXES = {
    "A15": dict(bbox=(3.548, 25.955, 3.712, 26.160), width=1100, mission=15),
    "A17": dict(bbox=(30.520, 20.090, 30.892, 20.300), width=1600, mission=17),
}


def _getmap(layers: str, bbox, width: int, height: int) -> Image.Image:
    q = dict(SERVICE="WMS", VERSION="1.1.1", REQUEST="GetMap", SRS="EPSG:4326",
             FORMAT="image/png", TRANSPARENT="TRUE", STYLES="", LAYERS=layers,
             BBOX=",".join(f"{v:.4f}" for v in bbox), WIDTH=width, HEIGHT=height)
    url = WMS + "?" + urllib.parse.urlencode(q)
    try:                                   # python.org builds on macOS ship no CA store
        import certifi
        ctx = ssl.create_default_context(cafile=certifi.where())
    except ImportError:
        ctx = ssl.create_default_context()
    with urllib.request.urlopen(url, timeout=180, context=ctx) as r:
        return Image.open(io.BytesIO(r.read())).convert("RGBA")


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    meta = dict(source="LROC Lunaserv WMS " + WMS, srs="EPSG:4326 (lunar lon/lat)",
                retrieved=datetime.date.today().isoformat(), sites={})
    for site, b in BOXES.items():
        lon0, lat0, lon1, lat1 = b["bbox"]
        # square ground pixels: height from the box aspect at the box latitude
        aspect = (lat1 - lat0) / ((lon1 - lon0) * np.cos(np.radians(0.5 * (lat0 + lat1))))
        w = b["width"]; h = int(round(w * aspect))
        m = b["mission"]
        nac = _getmap(f"luna_apollo_{m}_high_resolution_nac_mosaic", b["bbox"], w, h)
        a = np.asarray(nac)
        gray = a[..., :3].mean(-1).astype(np.uint8)
        Image.fromarray(np.dstack([gray, a[..., 3]]), "LA").save(OUT / f"{site}_nac.png")
        evas = []
        for e in (1, 2, 3):
            mask = np.asarray(_getmap(f"luna_apollo_{m}_eva{e}", b["bbox"], w, h))[..., 3] > 0
            Image.fromarray(mask).save(OUT / f"{site}_eva{e}.png")
            evas.append(int(mask.sum()))
        meta["sites"][site] = dict(bbox=b["bbox"], width=w, height=h,
                                   nac_layer=f"luna_apollo_{m}_high_resolution_nac_mosaic",
                                   eva_layers=[f"luna_apollo_{m}_eva{e}" for e in (1, 2, 3)],
                                   nodata_fraction=float((a[..., 3] == 0).mean()),
                                   eva_pixels=evas)
        print(f"  {site}: {w}x{h}, no-data {meta['sites'][site]['nodata_fraction']:.3%}, EVA px {evas}")
    (OUT / "meta.json").write_text(json.dumps(meta, indent=1))


if __name__ == "__main__":
    main()
