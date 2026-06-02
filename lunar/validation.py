"""Validation-data loaders.

Lightweight readers for the external reference datasets downloaded into
``data/``. Keeps the I/O layer separate from the solver.

Currently supported:

* :func:`load_apollo_hfe_temperature` — Apollo 15/17 Heat Flow
  Experiment concatenated temperature tables (Nagihara et al. 2018,
  PDS Geosciences Node bundle
  ``urn:nasa:pds:a15_17_hfe_concatenated``).
* :func:`load_apollo_hfe_depth` — companion depth tables giving the
  buried sensor depth vs time for each probe.
* :func:`load_diviner_pcp_polar` — Diviner Polar Cumulative Product
  (Williams et al. 2019) bolometric temperature maps at the south pole.

All loaders return plain numpy arrays or simple dataclasses; they do not
depend on pandas/astropy.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np

_DATA = Path(__file__).resolve().parent.parent / "data"


# ---------------------------------------------------------------------------
# Apollo 15/17 HFE — Nagihara et al. (2018, 2019)
# ---------------------------------------------------------------------------


@dataclass
class HFERecord:
    """One Apollo heat flow experiment probe timeseries.

    Attributes
    ----------
    time_s : np.ndarray
        Time in seconds (sensor-internal clock as archived in PDS).
    T : np.ndarray
        Sensor temperature [K].
    dT : np.ndarray
        Raw differential temperature [K].
    dT_corr : np.ndarray
        Corrected differential temperature [K].
    flags : np.ndarray
        Data quality flags (see PDS XML labels).
    mission : str
        ``'a15'`` or ``'a17'``.
    probe_name : str
        Probe identifier (e.g. ``'a15p1f1'``).
    """

    time_s: np.ndarray
    T: np.ndarray
    dT: np.ndarray
    dT_corr: np.ndarray
    flags: np.ndarray
    mission: str
    probe_name: str


def load_apollo_hfe_temperature(mission: str, probe: str) -> HFERecord:
    """Load one concatenated HFE temperature file.

    Parameters
    ----------
    mission : {'a15', 'a17'}
    probe : str
        The probe identifier used by the PDS bundle, e.g. ``'p1f1'``
        (Probe 1, Fast sensor 1) or ``'1975p1f1'`` (the 1975-1977
        restored subset).
    """
    if mission not in ("a15", "a17"):
        raise ValueError(f"mission must be 'a15' or 'a17', not {mission!r}")
    path = _DATA / "apollo" / mission / f"{mission}{probe}.tab"
    if not path.is_file():
        raise FileNotFoundError(f"Apollo HFE file not found: {path}")

    data = np.loadtxt(path, skiprows=1)
    ncols = data.shape[1]

    if ncols == 5:
        # Standard fast-sensor format: Time, T, dT, dT_corr, flags
        time_s = data[:, 0]
        T = data[:, 1]
        dT = data[:, 2]
        dT_corr = data[:, 3]
        flags = data[:, 4]
    elif ncols == 4:
        # Reduced format (e.g. p1f2): Time, T, dT, flags — no dT_corr
        time_s = data[:, 0]
        T = data[:, 1]
        dT = data[:, 2]
        dT_corr = np.full(data.shape[0], np.nan)
        flags = data[:, 3]
    elif ncols >= 8:
        # Thermocouple ring format (e.g. p1f3):
        # Time, HTR, TREF, TC1, TC2, TC3, TC4, flags
        # Use TREF (col 2) as the representative temperature.
        time_s = data[:, 0]
        T = data[:, 2]
        dT = np.full(data.shape[0], np.nan)
        dT_corr = np.full(data.shape[0], np.nan)
        flags = data[:, -1]
    else:
        raise ValueError(
            f"Unexpected column count {ncols} in {path}. "
            "Expected 4, 5, or 8 columns."
        )

    return HFERecord(
        time_s=time_s,
        T=T,
        dT=dT,
        dT_corr=dT_corr,
        flags=flags.astype(np.int64),
        mission=mission,
        probe_name=f"{mission}{probe}",
    )


def load_apollo_hfe_depth(mission: str, probe_num: int) -> np.ndarray:
    """Load the depth metadata for one HFE probe.

    Returns a structured array with fields
    ``('time_iso', 'T', 'sensor', 'depth_cm', 'flags')``.
    Depths are reported in centimeters below the regolith surface.

    Parameters
    ----------
    mission : {'a15', 'a17'}
    probe_num : {1, 2}
    """
    if mission not in ("a15", "a17"):
        raise ValueError(f"mission must be 'a15' or 'a17', not {mission!r}")
    if probe_num not in (1, 2):
        raise ValueError("probe_num must be 1 or 2")
    path = _DATA / "apollo" / "depth" / f"{mission}p{probe_num}_depth.tab"
    if not path.is_file():
        raise FileNotFoundError(f"HFE depth file not found: {path}")

    dt = np.dtype(
        [
            ("time_iso", "U24"),
            ("T", np.float64),
            ("sensor", "U8"),
            ("depth_cm", np.float64),
            ("flags", np.int64),
        ]
    )
    return np.genfromtxt(path, delimiter=",", dtype=dt, skip_header=1)


# ---------------------------------------------------------------------------
# Diviner Polar Cumulative Products — Williams et al. (2019)
# ---------------------------------------------------------------------------


@dataclass
class DivinerPCP:
    """Diviner polar cumulative bolometric-temperature table.

    The PDS bundle ``urn:nasa:pds:lro_diviner_derived1`` distributes
    each Polar Cumulative Product as a 5-column ASCII table, NOT a
    gridded raster. Columns are:

    ``x, y, clon, clat, tbol``

    where ``(x, y)`` are polar-stereographic map coordinates (in the
    projection units documented by the matching XML label), ``clon``
    and ``clat`` are selenographic longitude/latitude [deg], and
    ``tbol`` is the bolometric brightness temperature [K].

    Attributes
    ----------
    x, y : np.ndarray
        Polar-stereographic map coordinates, shape ``(N,)``.
    clon, clat : np.ndarray
        Selenographic east-longitude and latitude [deg], shape ``(N,)``.
    tbol : np.ndarray
        Bolometric brightness temperature [K], shape ``(N,)``.
    local_time, season, pole, source_file : metadata.
    """

    x: np.ndarray
    y: np.ndarray
    clon: np.ndarray
    clat: np.ndarray
    tbol: np.ndarray
    local_time: int
    season: str
    pole: str
    source_file: Path


def load_diviner_pcp_polar(
    local_time: int,
    season: str = "sum",
    pole: str = "pols",
    max_rows: int | None = None,
) -> DivinerPCP:
    """Load one Diviner Polar Cumulative Product ASCII table.

    File naming convention (PDS bundle
    ``urn:nasa:pds:lro_diviner_derived1``):
    ``pcp_avg_tbol_<pole>_<season>_ltim<NN>_240.tab``

    Parameters
    ----------
    local_time : int
        Local-time hour bin (1-24) for the diurnal product.
    season : str, default 'sum'
        Seasonal tag.
    pole : {'pols', 'poln'}, default 'pols'
        South or north polar cap.
    max_rows : int, optional
        Read at most this many rows. Useful for smoke-testing — the
        full file is ~3.5 M rows / ~200 MB.
    """
    fname = (
        f"pcp_avg_tbol_{pole}_{season}_ltim{local_time:02d}_240.tab"
    )
    path = _DATA / "diviner" / fname
    if not path.is_file():
        raise FileNotFoundError(f"Diviner PCP file not found: {path}")

    # Comma-separated with a whitespace-padded header row.
    data = np.genfromtxt(
        path,
        delimiter=",",
        skip_header=1,
        max_rows=max_rows,
        dtype=np.float64,
        autostrip=True,
    )
    return DivinerPCP(
        x=data[:, 0],
        y=data[:, 1],
        clon=data[:, 2],
        clat=data[:, 3],
        tbol=data[:, 4],
        local_time=local_time,
        season=season,
        pole=pole,
        source_file=path,
    )


# ---------------------------------------------------------------------------
# Chang'E-4 + ChaSTE reference tables (Huang 2022, Murty 2025)
# ---------------------------------------------------------------------------


def _load_reference_csv(path: Path) -> dict[str, tuple[float, str, str, str]]:
    """Parse a ``data/reference/*.csv`` reference table.

    The file format is simple and human-readable:
    ``quantity,value,unit,source,notes`` with ``#`` comments.
    Returns a dict keyed by quantity, mapping to
    ``(value_as_float_or_str, unit, source, notes)``.
    """
    if not path.is_file():
        raise FileNotFoundError(
            f"Reference table not found: {path}\n"
            "Run lunar._bootstrap.ensure_change4() / ensure_chaste() first."
        )
    out: dict[str, tuple[float, str, str, str]] = {}
    with open(path, "r", encoding="utf-8") as f:
        for raw in f:
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            parts = [p.strip() for p in line.split(",", 4)]
            if len(parts) < 5 or parts[0] == "quantity":
                continue
            name, value, unit, source, notes = parts
            try:
                v: float | str = float(value)
            except ValueError:
                v = value
            out[name] = (v, unit, source, notes)
    return out


def load_change4_reference() -> dict[str, tuple[float, str, str, str]]:
    """Load the bundled Chang'E-4 reference table (Huang et al. 2022)."""
    return _load_reference_csv(_DATA / "reference" / "change4_huang2022.csv")


def load_chaste_reference() -> dict[str, tuple[float, str, str, str]]:
    """Load the bundled ChaSTE reference table (Murty et al. 2025 + coauthors)."""
    return _load_reference_csv(_DATA / "reference" / "chaste_murty2025.csv")
