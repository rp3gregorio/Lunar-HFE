"""Regression tests for the flux-anchored periodic-equilibrium driver.

The defining property (audit flag F1, docs/FLAG_REPORT.md): the converged
profile must not depend on the initial-guess temperature. The full
production validation (5-m grid, 1-h steps, guesses 240/260 K, 120-lunation
drift certification) gives <= 0.023 K guess-dependence and <= 0.08 K
honest-run drift at sensor depths, i.e. <= ~0.1 mW/m/K in the retrieved
K_d* -- an order of magnitude below the bootstrap uncertainty. Here we run
a coarsened version so CI stays fast.
"""
from __future__ import annotations

import numpy as np
import pytest

from lunar.equilibrium import (
    _mean_flux_closure,
    _reconstruct_subskin,
    profile_at_local_time,
    profile_at_time,
    solve_periodic_equilibrium,
)
from lunar.grid import make_geometric_grid
from lunar.properties import conductivity_hayne, specific_heat
from lunar.constants import LUNATION_SECONDS


def _setup():
    grid = make_geometric_grid(z_max=3.0, dz0=0.004, growth=0.12)
    n_t = int(LUNATION_SECONDS / 7200.0) + 1
    t = np.linspace(0.0, LUNATION_SECONDS, n_t)
    phase = 2.0 * np.pi * t / LUNATION_SECONDS
    insol = 1361.0 * np.cos(np.deg2rad(26.13)) * np.maximum(0.0, np.cos(phase))
    k_func = lambda T, z: conductivity_hayne(T, z, Kd=4.86e-3)
    cp_func = lambda T: specific_heat(T, model="hayne")
    return grid, t, insol, k_func, cp_func


def test_guess_independence():
    """Converged profiles from 242 K and 258 K guesses must agree."""
    grid, t, insol, k_func, cp_func = _setup()
    profiles = []
    for guess in (242.0, 258.0):
        eq = solve_periodic_equilibrium(
            grid=grid, t=t, insolation=insol, albedo=0.131,
            emissivity=0.95, Q_b=0.021, K_func=k_func, cp_func=cp_func,
            T_guess=guess, n_inner=12)   # explicit: fast mechanics test
        assert eq.converged
        profiles.append(eq.T_mean)
    assert np.max(np.abs(profiles[0] - profiles[1])) < 0.1


def test_flux_closure():
    """Cycle-mean conductive flux must close on Q_b below the anchor."""
    grid, t, insol, k_func, cp_func = _setup()
    eq = solve_periodic_equilibrium(
        grid=grid, t=t, insolation=insol, albedo=0.131,
        emissivity=0.95, Q_b=0.021, K_func=k_func, cp_func=cp_func,
        T_guess=250.0, n_inner=12)   # explicit: fast mechanics test
    assert eq.flux_closure < 0.10


def test_reconstruct_subskin_integrates_constant_flux_profile():
    """Sub-skin reconstruction should reproduce a linear constant-K profile."""
    z = np.array([0.0, 1.0, 2.0])
    T_mean = np.array([250.0, 0.0, 0.0])

    def k_const(T, z):
        return np.full_like(np.asarray(z, dtype=float), 0.01)

    out = _reconstruct_subskin(T_mean, z, i0=0, Q_b=0.02, K_func=k_const)
    assert np.allclose(out, [250.0, 252.0, 254.0])


def test_reconstruct_subskin_rejects_invalid_conductivity():
    """Invalid K values should raise a clear error before division."""
    z = np.array([0.0, 1.0])
    T_mean = np.array([250.0, 250.0])

    def k_zero(T, z):
        return np.zeros_like(np.asarray(z, dtype=float))

    with pytest.raises(ValueError, match="invalid conductivity"):
        _reconstruct_subskin(T_mean, z, i0=0, Q_b=0.02, K_func=k_zero)


def test_flux_closure_certifier_matches_constant_flux():
    """The flux-closure certifier should report zero for an exact profile."""
    z = np.array([0.0, 1.0, 2.0])
    T_mean = np.array([250.0, 252.0, 254.0])

    def k_const(T, z):
        return np.full_like(np.asarray(z, dtype=float), 0.01)

    assert _mean_flux_closure(T_mean, z, i0=0, Q_b=0.02, K_func=k_const) < 1e-12


def test_profile_at_time():
    """Instantaneous profiles interpolate the stored cycle, periodically."""
    grid, t, insol, k_func, cp_func = _setup()
    eq = solve_periodic_equilibrium(
        grid=grid, t=t, insolation=insol, albedo=0.131,
        emissivity=0.95, Q_b=0.021, K_func=k_func, cp_func=cp_func,
        T_guess=250.0, n_inner=12)   # explicit: fast mechanics test
    z = eq.out.z
    lun_h = 29.53059 * 24.0                       # LUNATION_SECONDS in hours

    # exact sample: t = 0 must return the stored first column
    assert np.allclose(profile_at_time(eq, 0.0), eq.out.T[:, 0])
    # named phase == its numeric equivalent
    assert np.allclose(profile_at_time(eq, "midnight"),
                       profile_at_time(eq, 0.5 * lun_h))
    # periodic wrap: one full lunation later, and one before, are identical
    assert np.allclose(profile_at_time(eq, 100.0),
                       profile_at_time(eq, 100.0 + lun_h), atol=1e-9)
    assert np.allclose(profile_at_time(eq, 100.0),
                       profile_at_time(eq, 100.0 - lun_h), atol=1e-9)
    # physics: the surface swings by hundreds of K over the day...
    noon, night = profile_at_time(eq, "noon"), profile_at_time(eq, "midnight")
    assert noon[0] - night[0] > 100.0
    # ...while below the skin the profile barely leaves the cycle mean
    deep = z > 0.5
    assert np.max(np.abs(noon[deep] - eq.out.T.mean(axis=1)[deep])) < 0.5
    # bad phase name -> clear error
    with pytest.raises(ValueError, match="unknown phase"):
        profile_at_time(eq, "teatime")


def test_profile_at_local_time():
    """The 24-hour local-clock front end agrees with the named phases."""
    grid, t, insol, k_func, cp_func = _setup()
    eq = solve_periodic_equilibrium(
        grid=grid, t=t, insolation=insol, albedo=0.131,
        emissivity=0.95, Q_b=0.021, K_func=k_func, cp_func=cp_func,
        T_guess=250.0, n_inner=12)   # explicit: fast mechanics test

    # clock landmarks match the named phases exactly
    assert np.allclose(profile_at_local_time(eq, 12.0), profile_at_time(eq, "noon"))
    assert np.allclose(profile_at_local_time(eq, 0.0), profile_at_time(eq, "midnight"))
    assert np.allclose(profile_at_local_time(eq, 18.0), profile_at_time(eq, "sunset"))
    assert np.allclose(profile_at_local_time(eq, 6.0), profile_at_time(eq, "sunrise"))
    # "HH:MM" string parses the same as the equivalent float
    assert np.allclose(profile_at_local_time(eq, "14:30"),
                       profile_at_local_time(eq, 14.5))
    # the clock wraps: 25:00 reads as 01:00
    assert np.allclose(profile_at_local_time(eq, 25.0),
                       profile_at_local_time(eq, 1.0))
    # midday is hotter at the surface than midnight, as expected
    noon, night = profile_at_local_time(eq, 12.0), profile_at_local_time(eq, 0.0)
    assert noon[0] > night[0]
