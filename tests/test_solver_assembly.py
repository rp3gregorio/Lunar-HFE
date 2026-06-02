"""Smoke tests for the tridiagonal assembly.

The full solver is not yet wired (see ``lunar/solver.py``), but the
linear tridiagonal assembly can be checked in isolation.
"""

import numpy as np

from lunar.grid import make_geometric_grid
from lunar.solver import _assemble_tridiagonal, surface_energy_balance_residual
from lunar.constants import SIGMA_SB


def test_tridiagonal_row_sum_is_one_for_zero_dt():
    g = make_geometric_grid(z_max=0.1, dz0=0.002, growth=0.2)
    K = np.full(g.n_layers, 1e-3)
    rho_cp = np.full(g.n_layers, 1e6)  # arbitrary but non-zero
    a, b, c = _assemble_tridiagonal(g, K, rho_cp, dt=0.0)
    np.testing.assert_allclose(a + b + c, np.ones_like(b))


def test_tridiagonal_is_diagonally_dominant():
    g = make_geometric_grid(z_max=0.1, dz0=0.002, growth=0.2)
    K = np.full(g.n_layers, 1e-3)
    rho_cp = np.full(g.n_layers, 1e6)
    a, b, c = _assemble_tridiagonal(g, K, rho_cp, dt=10.0)
    # |b_i| >= |a_i| + |c_i| for implicit operator I + theta*dt*L
    assert np.all(np.abs(b) >= np.abs(a) + np.abs(c) - 1e-12)


def test_surface_energy_balance_residual_sign():
    # Hot surface (1000 K) with no sun should lose energy (R < 0 contribution
    # from radiation dominates). We check the sign convention: radiation out
    # makes R smaller.
    R_cold = surface_energy_balance_residual(
        T_s=100.0, insolation=0.0, albedo=0.0, emissivity=0.95,
        K_surf=1e-3, dz_surf=0.002, T_subsurf=100.0,
    )
    R_hot = surface_energy_balance_residual(
        T_s=1000.0, insolation=0.0, albedo=0.0, emissivity=0.95,
        K_surf=1e-3, dz_surf=0.002, T_subsurf=100.0,
    )
    assert R_hot < R_cold  # hotter surface radiates more -> smaller residual


def test_stefan_boltzmann_constant_used():
    # Regression guard: if someone swaps SIGMA_SB for a different value,
    # this test's analytic comparison will flag it.
    T_s = 300.0
    R = surface_energy_balance_residual(
        T_s=T_s, insolation=0.0, albedo=0.0, emissivity=1.0,
        K_surf=0.0, dz_surf=1.0, T_subsurf=T_s,
    )
    # With K_surf=0 and T_s == T_subsurf, the conductive term is zero and
    # R = -sigma * T^4.
    assert R == -SIGMA_SB * T_s**4
