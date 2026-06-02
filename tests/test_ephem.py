"""Tests for the SPICE solar-ephemeris helper.

Skipped unless all the required kernels exist under ``data/spice/``
and ``spiceypy`` is importable.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import numpy as np
import pytest

_SPICE_DIR = Path(__file__).resolve().parent.parent / "data" / "spice"
_REQUIRED = (
    "naif0012.tls",
    "pck00011.tpc",
    "moon_pa_de440_200625.bpc",
    "moon_de440_250416.tf",
    "moon_assoc_me.tf",
    "de440s.bsp",
)
_HAVE_SPICEYPY = importlib.util.find_spec("spiceypy") is not None
_HAVE_KERNELS = all((_SPICE_DIR / k).is_file() for k in _REQUIRED)

pytestmark = pytest.mark.skipif(
    not (_HAVE_SPICEYPY and _HAVE_KERNELS),
    reason="spiceypy or SPICE kernels missing",
)


def test_ephem_equator_diurnal_cycle():
    """The equatorial sub-solar elevation should swing through a full
    diurnal cycle over one lunation, crossing zero twice."""
    from lunar import ephem

    # One lunation at 4 h cadence starting an arbitrary UT.
    # 177 samples (~29.5 d × 6 / d).
    times = [
        f"2024-01-{d:02d}T{h:02d}:00:00"
        for d in range(1, 31)
        for h in (0, 6, 12, 18)
    ]
    et = ephem.et_from_iso(times)
    elev, az = ephem.solar_elevation_azimuth(et, lat_deg=0.0, lon_deg=0.0)
    ephem.unload_kernels()

    # Peak elevation should be close to +90 deg (equator, lon 0, twice
    # per lunation), and the minimum should be near -90 deg.
    assert float(np.rad2deg(elev.max())) > 60.0
    assert float(np.rad2deg(elev.min())) < -60.0
    # Number of zero crossings over one lunation should be at least 2.
    signs = np.sign(elev)
    crossings = int(np.sum(np.diff(signs) != 0))
    assert crossings >= 2


def test_ephem_south_pole_grazing():
    """At a ~89.9° S point, the sun is always grazing — the elevation
    must stay small and positive for many of the samples, never exceeding
    a few degrees above the local horizontal."""
    from lunar import ephem

    times = [f"2024-01-{d:02d}T12:00:00" for d in range(1, 31)]
    et = ephem.et_from_iso(times)
    elev, _ = ephem.solar_elevation_azimuth(et, lat_deg=-89.9, lon_deg=0.0)
    ephem.unload_kernels()

    deg = np.rad2deg(elev)
    # South-pole elevation envelope: within [-10, +10] deg is very
    # loose but correct. The actual value depends on the sub-solar
    # latitude and the 0.1° offset from the pole.
    assert float(deg.min()) > -10.0
    assert float(deg.max()) < 10.0


def test_insolation_series_zero_below_horizon():
    """Insolation must be exactly zero for negative elevations."""
    from lunar import ephem

    elev = np.deg2rad(np.array([-30.0, -1e-6, 0.0, 30.0, 90.0]))
    S = ephem.insolation_series(elev)
    assert S[0] == 0.0
    assert S[1] == 0.0
    assert S[2] == 0.0
    assert S[3] == pytest.approx(1361.0 * 0.5, rel=1e-6)
    assert S[4] == pytest.approx(1361.0, rel=1e-6)
