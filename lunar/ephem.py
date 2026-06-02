"""Solar ephemeris helper built on SPICE.

Provides the (solar elevation, solar azimuth) time series needed to drive
the per-pixel solver's insolation input. Lazily furnishes kernels from
``data/spice/`` on first use.

Required kernels (downloaded by the data-setup step):
    data/spice/naif0012.tls              — leap seconds (LSK)
    data/spice/pck00011.tpc              — body constants (PCK)
    data/spice/moon_pa_de440_200625.bpc  — Moon PA binary PCK
    data/spice/de440s.bsp                — planetary ephemeris (short span)

References
----------
* NAIF generic kernels: https://naif.jpl.nasa.gov/pub/naif/generic_kernels/
* SpiceyPy docs: https://spiceypy.readthedocs.io/
* Acton, C. H. (1996), "Ancillary data services of NASA's Navigation and
  Ancillary Information Facility", Planet. Space Sci. 44, 65-70.
"""

from __future__ import annotations

from pathlib import Path
from typing import Iterable, Sequence

import numpy as np

_SPICE_DIR = Path(__file__).resolve().parent.parent / "data" / "spice"

_KERNELS = (
    "naif0012.tls",               # leap seconds
    "pck00011.tpc",               # text body constants
    "moon_pa_de440_200625.bpc",   # Moon PA binary PCK (DE440)
    "moon_de440_250416.tf",       # Moon PA/ME frame definitions
    "moon_assoc_me.tf",           # binds MOON_ME to the PA chain
    "de440s.bsp",                 # DE440 short-span ephemeris
)

_FURNISHED = False


def _furnish_kernels() -> None:
    """Load the standard kernel set into SPICE once per process."""
    global _FURNISHED
    if _FURNISHED:
        return
    try:
        import spiceypy as spice  # type: ignore[import-not-found]
    except ImportError as exc:  # pragma: no cover
        raise ImportError(
            "spiceypy is required for lunar.ephem. Install with "
            "`pip install spiceypy`."
        ) from exc

    missing = []
    for name in _KERNELS:
        path = _SPICE_DIR / name
        if not path.is_file():
            missing.append(str(path))
        else:
            spice.furnsh(str(path))
    if missing:
        raise FileNotFoundError(
            "Missing SPICE kernels — download via the data-setup script:\n  "
            + "\n  ".join(missing)
        )
    _FURNISHED = True


def unload_kernels() -> None:
    """Unload all furnished kernels (useful for tests)."""
    global _FURNISHED
    try:
        import spiceypy as spice  # type: ignore[import-not-found]
    except ImportError:  # pragma: no cover
        return
    spice.kclear()
    _FURNISHED = False


def et_from_iso(times_iso: Sequence[str]) -> np.ndarray:
    """Convert ISO UTC strings to SPICE ephemeris time [s past J2000 TDB]."""
    _furnish_kernels()
    import spiceypy as spice  # type: ignore[import-not-found]

    return np.array([spice.str2et(s) for s in times_iso], dtype=np.float64)


def solar_vector_moon_frame(et: np.ndarray) -> np.ndarray:
    """Direction from the Moon center to the Sun, in the Moon body-fixed
    frame (MOON_ME, mean Earth / polar axis).

    Parameters
    ----------
    et : np.ndarray
        Ephemeris time [s past J2000 TDB], shape ``(N,)``.

    Returns
    -------
    np.ndarray
        Unit vectors, shape ``(N, 3)``, in the MOON_ME frame.
    """
    _furnish_kernels()
    import spiceypy as spice  # type: ignore[import-not-found]

    et = np.atleast_1d(np.asarray(et, dtype=np.float64))
    out = np.empty((et.size, 3), dtype=np.float64)
    for i, ti in enumerate(et):
        # Position of Sun as seen from Moon center, corrected for
        # light-time and stellar aberration, expressed in MOON_ME.
        pos, _ = spice.spkpos("SUN", float(ti), "MOON_ME", "LT+S", "MOON")
        out[i] = np.asarray(pos, dtype=np.float64) / np.linalg.norm(pos)
    return out


def solar_elevation_azimuth(
    et: np.ndarray,
    lat_deg: float,
    lon_deg: float,
) -> tuple[np.ndarray, np.ndarray]:
    """Solar elevation and azimuth at a Moon-fixed surface point.

    Parameters
    ----------
    et : np.ndarray
        Ephemeris time [s past J2000], shape ``(N,)``.
    lat_deg, lon_deg : float
        Selenographic latitude and east longitude [deg]. Uses the
        Moon mean-Earth frame (MOON_ME).

    Returns
    -------
    elev : np.ndarray
        Solar elevation above the local horizontal plane [rad].
        Negative values indicate sub-horizon (night).
    az : np.ndarray
        Solar azimuth measured clockwise from local north [rad],
        in ``[0, 2*pi)``. Matches the convention used by
        :func:`lunar.illumination.compute_horizon`.
    """
    et = np.atleast_1d(np.asarray(et, dtype=np.float64))
    lat = np.deg2rad(lat_deg)
    lon = np.deg2rad(lon_deg)

    # Local ENU basis at (lat, lon) on a spherical Moon. For the solar
    # vector only, ignoring Moon oblateness is fine (< 0.01 deg error).
    ex = np.array([-np.sin(lon), np.cos(lon), 0.0])                  # east
    en = np.array([-np.sin(lat) * np.cos(lon),
                   -np.sin(lat) * np.sin(lon),
                    np.cos(lat)])                                    # north
    eu = np.array([ np.cos(lat) * np.cos(lon),
                    np.cos(lat) * np.sin(lon),
                    np.sin(lat)])                                    # up

    s = solar_vector_moon_frame(et)  # (N, 3)
    e = s @ ex
    n = s @ en
    u = s @ eu

    elev = np.arcsin(np.clip(u, -1.0, 1.0))
    # Azimuth clockwise from north: atan2(east, north).
    az = np.mod(np.arctan2(e, n), 2.0 * np.pi)
    return elev, az


def insolation_series(
    elev: np.ndarray,
    solar_constant: float = 1361.0,
    distance_au: float = 1.0,
) -> np.ndarray:
    """Instantaneous top-of-surface insolation [W/m^2] from solar elevation.

    ``S = S0 * max(0, sin(elev)) / r^2`` — this is the direct (un-shadowed)
    value; multiply by a horizon/shadow mask to get the realized flux.
    """
    elev = np.asarray(elev, dtype=np.float64)
    return solar_constant * np.maximum(0.0, np.sin(elev)) / (distance_au**2)
