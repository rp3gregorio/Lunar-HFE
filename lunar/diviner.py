"""Diviner Lunar Radiometer Global Cumulative Product (GCP) access.

The GCP product is the primary validation dataset cited by Martinez &
Siegler (2021). It is a 2-pixels-per-degree (0.5° × 0.5°) global temperature
grid binned at 0.25 hours of local time, derived from all nadir Diviner
observations between 2009-07-05 and 2015-04-01.

PDS data set ID: ``LRO-L-DLRE-5-GCP-V1.0``  (DOI 10.17189/1520650).
Reference: Williams et al. (2017) Icarus 283, 300-325.

Each .tab file covers one 10° latitude band over all longitudes, has a
fixed-width 113-byte ASCII record format, and is ~156 MB. The 11 columns
are documented in ``DLRE_GCP.FMT`` (kept under ``data/diviner/gcp/`` for
reference). Sentinel ``-9999`` flags bins with no observations.

The companion :func:`load_diviner_pcp_polar` for the polar product lives
in :mod:`lunar.validation` and reads a different (lower-volume, polar
stereographic) format.
"""

from __future__ import annotations

import hashlib
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import numpy as np

_PDS_BUNDLE = (
    "https://pds-geosciences.wustl.edu/lro/"
    "urn-nasa-pds-lro_diviner_derived1"
)
GCP_DIR_URL = f"{_PDS_BUNDLE}/data_derived_gcp"
GCP_FMT_URL = f"{_PDS_BUNDLE}/label/dlre_gcp.fmt"

# Column order from DLRE_GCP.FMT (PDS3 fixed-width ASCII, 113 bytes/record).
GCP_COLUMNS: tuple[str, ...] = (
    "clon", "clat", "ltim",
    "t3", "t4", "t5", "t6", "t7", "t8", "t9",
    "tbol",
)
GCP_NO_OBS = -9999.0   # bin contained no observations
GCP_INVALID = -9998.0  # bin contained only invalid radiances

_REPO_ROOT = Path(__file__).resolve().parents[1]
_DEFAULT_CACHE = _REPO_ROOT / "data" / "diviner" / "gcp"


@dataclass(frozen=True)
class GCPBand:
    """One 10° latitude band of Diviner GCP, loaded into memory."""

    clon: np.ndarray   # center longitude [deg], -180..+180 east-positive
    clat: np.ndarray   # center latitude [deg]
    ltim: np.ndarray   # local time [hour], 0..24
    channels: dict[str, np.ndarray]  # {"t3": ..., ..., "t9": ..., "tbol": ...}
    lat_min: float
    lat_max: float
    source_file: Path


def gcp_band_filename(lat_min: int, lat_max: int, ppd: int = 2) -> str:
    """Build the canonical GCP filename for a 10° latitude band.

    Bands are encoded as ``aaXbbY`` where ``aa`` and ``bb`` are 2-digit
    latitudes and ``X``, ``Y`` are ``n``/``s``. Northern bands are written
    *min-max* (e.g. ``00n10n`` for 0..10°N); southern bands are written
    *max-min* with deeper-south latitudes first (e.g. ``10s00s`` for
    -10..0°S, ``80s70s`` for -80..-70°S).
    """
    if lat_min >= 0 and lat_max > 0:
        band = f"{lat_min:02d}n{lat_max:02d}n"
    elif lat_min < 0 and lat_max <= 0:
        # Filenames write the deeper-south latitude first, e.g. 10s00s.
        band = f"{abs(lat_min):02d}s{abs(lat_max):02d}s"
    else:
        raise ValueError(
            f"Lat band must not straddle equator: got {lat_min}..{lat_max}"
        )
    return f"global_cumul_avg_cyl_{band}_{ppd:03d}.tab"


def gcp_band_for_latitude(latitude: float) -> tuple[int, int]:
    """Return the (lat_min, lat_max) of the 10° band containing ``latitude``.

    Latitude is in degrees, positive north. Boundaries are inclusive at
    the lower edge so 10.0° belongs to the 10..20°N band.
    """
    if latitude >= 0:
        lat_min = int(latitude // 10) * 10
        return lat_min, lat_min + 10
    lat_max = int(np.ceil(latitude / 10.0)) * 10
    return lat_max - 10, lat_max


def _download(url: str, dest: Path, *, force: bool = False) -> Path:
    """Streaming HTTP download with simple cache-on-disk semantics."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.is_file() and not force:
        return dest
    tmp = dest.with_suffix(dest.suffix + ".part")
    req = urllib.request.Request(
        url, headers={"User-Agent": "Lunar-V2/phase2-martinez"}
    )
    with urllib.request.urlopen(req, timeout=60) as resp, tmp.open("wb") as fh:
        while True:
            chunk = resp.read(1 << 20)  # 1 MiB
            if not chunk:
                break
            fh.write(chunk)
    tmp.replace(dest)
    return dest


def download_gcp_band(
    lat_min: int,
    lat_max: int,
    *,
    ppd: int = 2,
    cache_dir: Path | None = None,
    fetch_label: bool = True,
    fetch_format: bool = True,
    force: bool = False,
) -> dict[str, Path]:
    """Download one Diviner GCP 10° latitude band and its sidecar files.

    Returns a dict with keys ``tab``, optionally ``lbl`` and ``fmt``. The
    ``.tab`` file is the only large file (~156 MB); ``.lbl`` is the PDS3
    detached label (~3 KB) and ``DLRE_GCP.FMT`` is the column schema
    (~4 KB). Sidecar files are skipped if already present.

    Parameters
    ----------
    lat_min, lat_max : int
        Edges of the 10° latitude band, in degrees, positive north.
        See :func:`gcp_band_filename` for the filename convention.
    ppd : int, default 2
        Pixels per degree. Only ``2`` is currently archived for GCP.
    cache_dir : Path, optional
        Where to store the files. Defaults to ``data/diviner/gcp/``.
    """
    cache_dir = cache_dir or _DEFAULT_CACHE
    fname = gcp_band_filename(lat_min, lat_max, ppd)

    out: dict[str, Path] = {}
    out["tab"] = _download(
        f"{GCP_DIR_URL}/{fname}", cache_dir / fname, force=force
    )
    if fetch_label:
        lbl_name = fname.replace(".tab", ".lbl")
        out["lbl"] = _download(
            f"{GCP_DIR_URL}/{lbl_name}", cache_dir / lbl_name, force=force
        )
    if fetch_format:
        out["fmt"] = _download(
            GCP_FMT_URL, cache_dir / "DLRE_GCP.FMT", force=force
        )
    return out


# -- Loader -----------------------------------------------------------------

# Byte-offset table from DLRE_GCP.FMT. Tuples are (start_byte, length).
_FIELD_BYTES: dict[str, tuple[int, int]] = {
    "clon": (1, 7),
    "clat": (10, 6),
    "ltim": (18, 6),
    "t3":   (26, 9),
    "t4":   (37, 9),
    "t5":   (48, 9),
    "t6":   (59, 9),
    "t7":   (70, 9),
    "t8":   (81, 9),
    "t9":   (92, 9),
    "tbol": (103, 9),
}
_RECORD_BYTES = 113


def load_gcp_band(
    lat_min: int,
    lat_max: int,
    *,
    ppd: int = 2,
    cache_dir: Path | None = None,
    columns: Iterable[str] | None = None,
    auto_download: bool = False,
) -> GCPBand:
    """Read a Diviner GCP latitude band into memory.

    Parses the fixed-width ASCII .tab file via numpy. Each record is 113
    bytes (1 newline-terminated row); a single 10° band has ~1.38 M rows
    and uses ~110 MB of RAM when all columns are loaded.

    Parameters
    ----------
    columns : iterable of str, optional
        Subset of channels to load (e.g. ``("t7", "tbol")``). The location
        columns ``clon``, ``clat``, ``ltim`` are always loaded. Default
        loads everything.
    auto_download : bool
        If True, fetch the file from PDS when missing. Default False —
        the explicit downloader script is the intended bootstrap path.
    """
    cache_dir = cache_dir or _DEFAULT_CACHE
    fname = gcp_band_filename(lat_min, lat_max, ppd)
    path = cache_dir / fname
    if not path.is_file():
        if not auto_download:
            raise FileNotFoundError(
                f"Diviner GCP band not on disk: {path}\n"
                "Run scripts/download_diviner_gcp.py to bootstrap."
            )
        download_gcp_band(lat_min, lat_max, ppd=ppd, cache_dir=cache_dir)

    wanted = set(columns) if columns else set(GCP_COLUMNS)
    wanted |= {"clon", "clat", "ltim"}

    # Read fixed-width records as raw bytes, view as (n_records, 113)
    # uint8 grid, then slice and reinterpret each field as ASCII floats.
    # Record 1 is a 113-byte text header per the .lbl file (^HEADER = (..., 1)),
    # so skip it before parsing.
    raw = np.fromfile(path, dtype=np.uint8)
    n_records, remainder = divmod(raw.size, _RECORD_BYTES)
    if remainder != 0:
        import warnings
        warnings.warn(
            f"GCP file {path.name} has {remainder} trailing byte(s) after "
            f"{n_records} complete {_RECORD_BYTES}-byte records; truncating. "
            f"This can happen when a concurrent download created a slightly "
            f"oversized file. Data loss is at most one record.",
            UserWarning,
            stacklevel=2,
        )
        raw = raw[: n_records * _RECORD_BYTES]
    view = raw.reshape(n_records, _RECORD_BYTES)[1:]  # drop header row

    def _parse(name: str) -> np.ndarray:
        start, length = _FIELD_BYTES[name]   # PDS3 START_BYTE is 1-indexed
        field = np.ascontiguousarray(
            view[:, start - 1 : start - 1 + length]
        )
        return np.frombuffer(field.tobytes(), dtype=f"S{length}").astype(
            np.float64
        )

    fields: dict[str, np.ndarray] = {
        name: _parse(name) for name in ("clon", "clat", "ltim")
    }
    channels: dict[str, np.ndarray] = {
        name: _parse(name)
        for name in GCP_COLUMNS
        if name not in ("clon", "clat", "ltim") and name in wanted
    }

    return GCPBand(
        clon=fields["clon"],
        clat=fields["clat"],
        ltim=fields["ltim"],
        channels=channels,
        lat_min=float(lat_min),
        lat_max=float(lat_max),
        source_file=path,
    )


def select_diurnal_curve(
    band: GCPBand,
    latitude: float,
    *,
    channel: str = "t7",
    half_width_deg: float = 0.25,
    longitude_range: tuple[float, float] | None = None,
) -> tuple[np.ndarray, np.ndarray]:
    """Average ``band`` to a single diurnal curve at one latitude.

    Returns ``(local_time, T)`` arrays sorted by local time, with the
    -9999/-9998 sentinels masked out. Optionally restrict to a longitude
    range (for highlands/mare separation by region).

    Parameters
    ----------
    half_width_deg : float, default 0.25
        Half-width of the latitude window. The default 0.25° matches the
        Martinez & Siegler (2021) `extractdiv.m` filter (one 2 ppd row).
    """
    if channel not in band.channels:
        raise KeyError(
            f"Channel {channel!r} not loaded; available: {list(band.channels)}"
        )
    mask = np.abs(band.clat - latitude) <= half_width_deg
    if longitude_range is not None:
        lo, hi = longitude_range
        mask &= (band.clon >= lo) & (band.clon <= hi)

    T = band.channels[channel][mask]
    LT = band.ltim[mask]
    valid = (T > GCP_INVALID + 1.0)  # excludes both -9999 and -9998
    T = T[valid]
    LT = LT[valid]

    # Bin by local time (the GCP grid is already on 0.25-hr LT bins, so
    # we just collapse over longitude with a mean per LT).
    lt_bins, inverse = np.unique(LT, return_inverse=True)
    means = np.zeros_like(lt_bins)
    counts = np.zeros_like(lt_bins, dtype=np.int64)
    np.add.at(means, inverse, T)
    np.add.at(counts, inverse, 1)
    return lt_bins, means / np.maximum(counts, 1)


def file_md5(path: Path, chunk: int = 1 << 20) -> str:
    """SHA-style chunked MD5 for sanity-checking downloads."""
    h = hashlib.md5()
    with path.open("rb") as fh:
        while True:
            data = fh.read(chunk)
            if not data:
                break
            h.update(data)
    return h.hexdigest()
