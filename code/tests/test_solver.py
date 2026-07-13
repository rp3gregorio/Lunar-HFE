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
import pytest

from lunar.grid import DepthGrid, make_geometric_grid
from lunar.solver import (
    PixelInputs,
    _solve_surface_newton,
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


def test_surface_newton_solves_radiative_bc_directly():
    """Newton's surface solve should return a root of the radiative balance."""
    T_s = _solve_surface_newton(
        insolation=850.0,
        albedo=0.12,
        emissivity=0.95,
        K_surf=1.2e-3,
        dz_surf=0.002,
        T_subsurf=255.0,
        T_s_guess=250.0,
    )
    residual = surface_energy_balance_residual(
        T_s=T_s,
        insolation=850.0,
        albedo=0.12,
        emissivity=0.95,
        K_surf=1.2e-3,
        dz_surf=0.002,
        T_subsurf=255.0,
    )
    assert 255.0 < T_s < 390.0
    assert abs(residual) < 1e-6


def test_surface_newton_rejects_invalid_inputs():
    """Pathological BC inputs should fail at the boundary, not later as NaNs."""
    with pytest.raises(ValueError, match="K_surf must be positive"):
        _solve_surface_newton(
            insolation=850.0,
            albedo=0.12,
            emissivity=0.95,
            K_surf=0.0,
            dz_surf=0.002,
            T_subsurf=255.0,
            T_s_guess=250.0,
        )


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


# ----------------------------------------------------------------------------
# Midpoint-Picard property sweeps (solver._step, 2026-07-03)
# ----------------------------------------------------------------------------


def _picard_march(n_picard: int) -> np.ndarray:
    """One short radiative march at an explicit Picard sweep count."""
    from lunar.grid import make_geometric_grid as _mk
    from lunar.solver import _step

    grid = _mk(z_max=0.5, dz0=0.002, growth=0.12)
    inputs = PixelInputs(
        grid=grid,
        t=np.array([0.0, 1800.0]),  # single step; we drive _step directly
        bc_mode="radiative",
        insolation=np.array([800.0, 400.0]),  # a terminator-like drop
        albedo=0.12,
        emissivity=0.95,
        Q_b=0.018,
    )
    T = np.full(grid.n_layers, 250.0)
    T_s_prev = 300.0
    for _ in range(24):  # 12 h of 1800 s steps
        T, _ts = _step(grid, T, None, None, inputs, idx_new=1, dt=1800.0,
                       radiative_T_s_prev=T_s_prev, n_picard=n_picard)
    return T


def test_picard_idempotent_for_constant_properties():
    """With T-independent K/rho/cp AND a Dirichlet surface, every Picard
    sweep reassembles the identical linear system, so extra sweeps must
    change nothing (this pins the loop against re-using a stale state)."""
    from lunar.solver import _step

    grid = make_geometric_grid(z_max=0.5, dz0=0.002, growth=0.12)
    K_func, rho_func, cp_func = _constant_props(1.0e-3, 1500.0, 600.0)
    inputs = PixelInputs(
        grid=grid, t=np.array([0.0, 1800.0]), bc_mode="dirichlet",
        T_surface_forced=np.array([250.0, 260.0]), Q_b=0.018,
        K_func=K_func, rho_func=rho_func, cp_func=cp_func,
    )
    T0 = np.linspace(260.0, 250.0, grid.n_layers)
    T_a, _ = _step(grid, T0, 250.0, 260.0, inputs, idx_new=1, dt=1800.0,
                   n_picard=0)
    T_b, _ = _step(grid, T0, 250.0, 260.0, inputs, idx_new=1, dt=1800.0,
                   n_picard=3)
    assert np.array_equal(T_a, T_b)


def test_picard_sweep_engages_for_hayne_properties():
    """With the real T-dependent properties the corrector sweep must move
    the answer (guards against the loop silently not executing) but only
    by a small, physically plausible correction."""
    T0 = _picard_march(n_picard=0)
    T1 = _picard_march(n_picard=1)
    dmax = float(np.max(np.abs(T1 - T0)))
    assert dmax > 1.0e-6, "Picard sweep had no effect on a nonlinear march"
    assert dmax < 5.0, f"Picard correction implausibly large: {dmax:.3f} K"


def test_picard_converges_toward_fixed_point():
    """Successive sweep counts must approach a fixed point: the 1->2 sweep
    change should be markedly smaller than the 0->1 change."""
    T0 = _picard_march(n_picard=0)
    T1 = _picard_march(n_picard=1)
    T2 = _picard_march(n_picard=2)
    d01 = float(np.max(np.abs(T1 - T0)))
    d12 = float(np.max(np.abs(T2 - T1)))
    assert d12 < 0.5 * d01, (
        f"Picard not contracting: |T2-T1|={d12:.2e} vs |T1-T0|={d01:.2e}")


def test_fast_march_matches_generic():
    """The compiled Hayne march (hayne_params fast path) must reproduce the
    generic _step march to float-roundoff. This equality is what transfers
    the dt certification to the fast path -- treat any loosening as a bug."""
    import functools
    from lunar.config import SITES, HAYNE
    from lunar.properties import conductivity_hayne, specific_heat
    from lunar.solver import periodic_time_grid, standard_insolation

    site = SITES["A15"]
    kd = 4.6e-3
    grid = make_geometric_grid(z_max=1.5, dz0=0.002, growth=0.10)
    t = periodic_time_grid(7200.0)  # coarse dt: cheap, still 354 steps
    insol = standard_insolation(site["lat"], t)
    common = dict(
        grid=grid, t=t, bc_mode="radiative", insolation=insol,
        albedo=site["albedo"], emissivity=site["emissivity"],
        Q_b=site["Q_BASAL"],
        T_init=np.full(grid.n_layers, 250.0),
        n_lunations_spinup=3, spinup_tol_K=0.0,
    )
    K = functools.partial(conductivity_hayne, Ks=HAYNE["K_S"], Kd=kd,
                          H=HAYNE["H"], chi=HAYNE["CHI"])
    cp = functools.partial(specific_heat, model="hayne")
    slow = solve_pixel(PixelInputs(**common, K_func=K, cp_func=cp))
    fast = solve_pixel(PixelInputs(
        **common, K_func=K, cp_func=cp,
        hayne_params=(HAYNE["K_S"], kd, HAYNE["H"], HAYNE["CHI"])))
    assert fast.diagnostics.get("fast_path") is True
    dev = float(np.max(np.abs(slow.T - fast.T)))
    assert dev < 1e-9, f"fast march deviates from generic by {dev:.3e} K"
    dev_s = float(np.max(np.abs(slow.T_surface - fast.T_surface)))
    assert dev_s < 1e-9, f"surface record deviates by {dev_s:.3e} K"
