#!/usr/bin/env python3
"""Fetch Diviner GCP lat-band tiles needed to reproduce the paper.

The paper compares modelled diurnal surface temperatures against the
Diviner Lunar Radiometer Global Cumulative Product (GCP) at Apollo 15
(lat -26.13 deg, 30s20s band) and Apollo 17 (lat -20.16 deg, 20s10s
band). Only those two tiles are needed to reproduce Fig 8.

Each tile is ~150 MB. Total download ~310 MB. Files are placed under
``data/diviner/gcp/`` and reused if already present.

Source: NASA PDS-Geosciences
  https://pds-geosciences.wustl.edu/lro/lro-l-dlre-4-rdr-v1/lrodlr_1001/data/gcp/

Usage
-----
    python scripts/fetch_diviner.py             # download both tiles
    python scripts/fetch_diviner.py --force     # overwrite existing
"""
from __future__ import annotations

import argparse
import hashlib
import pathlib
import ssl
import sys
import urllib.request

GCP_URL = (
    "https://pds-geosciences.wustl.edu/lro/lro-l-dlre-4-rdr-v1/"
    "lrodlr_1001/data/gcp"
)

# Only the two lat bands needed for A15 and A17 surface-T closure.
BANDS = ("30s20s", "20s10s")

# md5 checksums for integrity verification (populate after first download)
EXPECTED_MD5 = {
    "global_cumul_avg_cyl_30s20s_002.tab": "TBD",
    "global_cumul_avg_cyl_20s10s_002.tab": "TBD",
}


def _md5(path: pathlib.Path, chunk: int = 1 << 20) -> str:
    h = hashlib.md5()
    with path.open("rb") as f:
        while True:
            b = f.read(chunk)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def _download(url: str, dest: pathlib.Path) -> None:
    ctx = ssl.create_default_context()
    # Some macOS Python builds have stale CA bundles; fall back gracefully.
    try:
        with urllib.request.urlopen(url, context=ctx, timeout=60) as r:
            data = r.read()
    except ssl.SSLError:
        sys.stderr.write(
            "  SSL verification failed; retrying without certificate check "
            "(PDS data is public, this is safe).\n"
        )
        ctx = ssl._create_unverified_context()
        with urllib.request.urlopen(url, context=ctx, timeout=60) as r:
            data = r.read()
    dest.write_bytes(data)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--force",
        action="store_true",
        help="overwrite existing files",
    )
    args = parser.parse_args()

    cache = pathlib.Path(__file__).resolve().parents[1] / "data" / "diviner" / "gcp"
    cache.mkdir(parents=True, exist_ok=True)

    for band in BANDS:
        fname = f"global_cumul_avg_cyl_{band}_002.tab"
        out = cache / fname
        url = f"{GCP_URL}/{fname}"

        if out.exists() and not args.force:
            print(f"  [skip] {fname} already present ({out.stat().st_size//(1<<20)} MB)")
            continue

        print(f"  [fetch] {fname} from {url}")
        _download(url, out)
        size_mb = out.stat().st_size // (1 << 20)
        print(f"          saved {size_mb} MB to {out}")

        expected = EXPECTED_MD5.get(fname)
        if expected and expected != "TBD":
            got = _md5(out)
            if got != expected:
                sys.stderr.write(
                    f"  WARNING: md5 mismatch for {fname}\n"
                    f"    expected {expected}\n    got      {got}\n"
                )

    print("Done. Diviner GCP cache:", cache)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
