"""Solver validation tests.

The primary validation is against the analytical thermal-wave solution
for a semi-infinite domain with constant coefficients and sinusoidal
surface temperature. This is a rigorous check that the Crank-Nicolson
assembly, Thomas solve, and Dirichlet BC are internally consistent.

A separate radiative-BC smoke test checks that the Newton surface
solver converges and produces a physically plausible diurnal range.
"""

from __future__ import annotations

import numpy as np

from lunar.grid import DepthGrid, make_geometric_grid
from lunar.solver import (
    PixelInputs,
    analytical_thermal_wave,
    solve_pixel,
    surface_energy_balance_residual,
)
from lunar.constants import SIGMA_SB


# ----------------------------------------------------------------------------
# Analytical thermal-wave validation
# ----------------------------------------------------------------------------


def _constant_props(K_val: float, rho_val: float, cp_val: float):
    """Build K/rho/cp callables with constant coefficients."""
    def K_func(T, z):
        return np.full_like(z, K_val, dtype=np.float64)

    def rho_func(z):
        return np.full_like(z, rho_val, dtype=np.float64)

    def cp_func(T):
        return np.full_like(T, cp_val, dtype=np.float64)

    return K_func, rho_func, cp_func


def test_thermal_wave_matches_analytical():
    """Dirichlet-BC CN solver should track the closed-form thermal wave.

    Physical setup: lunar-like K = 1e-3 W/m/K, rho = 1500 kg/m^3,
    cp = 600 J/kg/K, diurnal period = one lunation (29.53 days).
    The thermal diffusivity is alpha = K / (rho * cp) ~ 1.1e-9 m^2/s;
    skin depth delta = sqrt(2*alpha/omega) ~ 7 cm.

    Expectation: after the surface transient dies out, the solver
    reproduces the analytical exp(-z/delta) * sin(omega t - z/delta)
    shape. We compare the solver output at the last quarter of the
    simulation against the analytical form with L-infinity norm <= 2 K.
    """
    K_val = 1.0e-3
    rho_val = 1500.0
    cp_val = 600.0
    alpha = K_val / (rho_val / 1.0 * cp_val)  # diffusivity
    T_mean = 250.0
    amplitude = 80.0
    P = 29.530589 * 86400.0  # one lunation
    omega = 2.0 * np.pi / P

    # Use a dense geometric grid deep enough that the wave vanishes.
    grid = make_geometric_grid(z_max=1.5, dz0=0.002, growth=0.08)

    # Simulate 3 periods so the first two serve as spin-up for the
    # Dirichlet transient.
    n_periods = 3
    n_t = 721  # 240 steps per period
    t = np.linspace(0.0, n_periods * P, n_t)
    T_surface = T_mean + amplitude * np.sin(omega * t)

    K_func, rho_func, cp_func = _constant_props(K_val, rho_val, cp_val)
    inputs = PixelInputs(
        grid=grid,
        t=t,
        bc_mode="dirichlet",
        T_surface_forced=T_surface,
        Q_b=0.0,  # analytical solution has no geothermal flux
        K_func=K_func,
        rho_func=rho_func,
        cp_func=cp_func,
        T_init=np.full(grid.n_layers, T_mean),
    )
    out = solve_pixel(inputs)

    # Analytical solution on the same grid and time vector
    T_ana = analytical_thermal_wave(
        z=grid.z_mid, t=t, T_mean=T_mean,
        amplitude=amplitude, period=P, alpha=alpha,
    )

    # Compare only the last period to exclude the transient.
    k0 = int(2 * (n_t - 1) / n_periods)  # start of last period
    diff = out.T[:, k0:] - T_ana[:, k0:]
    max_err = float(np.max(np.abs(diff)))
    rms_err = float(np.sqrt(np.mean(diff**2)))
    # Tight bound at the surface, looser deep. 2 K L-infinity is comfortably
    # better than any real validation target.
    assert max_err < 2.0, f"max analytical-wave error = {max_err:.3f} K"
    assert rms_err < 1.0, f"RMS analytical-wave error = {rms_err:.3f} K"


# ----------------------------------------------------------------------------
# Radiative BC smoke tests
# ----------------------------------------------------------------------------


def test_radiative_bc_surface_newton_equilibrium():
    """The radiative surface residual should vanish at its analytical root.

    For an isothermal subsurface (T_sub = T_s) the conduction term is zero
    and the residual reduces to ``(1-A)*S - eps*sigma*T_s^4``. Pick T_s,
    emissivity and albedo, solve for the insolation that makes the residual
    zero, and verify the residual function returns ~0 at that point.
    """
    T_s = 300.0
    albedo = 0.12
    emissivity = 0.95
    # Balance: (1-A)*S = eps*sigma*T_s^4
    insol = emissivity * SIGMA_SB * T_s**4 / (1.0 - albedo)

    R = surface_energy_balance_residual(
        T_s=T_s, insolation=insol, albedo=albedo, emissivity=emissivity,
        K_surf=1e-3, dz_surf=0.002, T_subsurf=T_s,
    )
    assert abs(R) < 1e-9

    # And the far-field cold limit: for Q_b-only heating through a thin
    # surface cell with large subsurface-to-surface gradient, T_s equilibrates
    # at (Q_b/(eps*sigma))**0.25 ~ 24 K (this is just an arithmetic check,
    # not a residual check).
    Q_b = 0.018
    T_cold = (Q_b / (emissivity * SIGMA_SB)) ** 0.25
    assert 20.0 < T_cold < 30.0


def test_radiative_bc_smoke_run_short():
    """Short run with a constant insolation — just checks no crash and
    that the solver returns sensible-looking temperatures."""
    grid = make_geometric_grid(z_max=1.0, dz0=0.002, growth=0.12)
    P = 29.530589 * 86400.0
    # 2 sample days, 48 samples/day — this is a short smoke test, not a
    # science run.
    n_per_day = 48
    n_t = 2 * n_per_day + 1
    t = np.linspace(0.0, 2.0 * P / 29.53, n_t)  # 2 earth days-ish
    # Square wave: half the time sunlit at 1361 W/m^2, half in shadow.
    insol = np.where((np.arange(n_t) // (n_per_day // 2)) % 2 == 0, 1361.0, 0.0)

    inputs = PixelInputs(
        grid=grid,
        t=t,
        bc_mode="radiative",
        insolation=insol,
        albedo=0.12,
        emissivity=0.95,
        Q_b=0.018,
        n_lunations_spinup=2,  # very short
        T_init=np.full(grid.n_layers, 250.0),
    )
    out = solve_pixel(inputs)
    # No NaNs
    assert np.all(np.isfinite(out.T))
    # Temperatures should be physically bounded
    assert out.T.min() > 20.0
    assert out.T.max() < 500.0
    # Deep temperatures should vary much less than surface
    assert float(out.T[0].std()) > float(out.T[-1].std())
