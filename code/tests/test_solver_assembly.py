"""Sanity tests for the surface energy balance residual.

The full Crank-Nicolson solver is exercised through the pipeline tests
([tests/test_pipeline_smoke.py](test_pipeline_smoke.py)); this file
covers the surface boundary in isolation so a regression in the SEB
formulation is caught early.
"""

from lunar.solver import surface_energy_balance_residual
from lunar.constants import SIGMA_SB


def test_surface_energy_balance_residual_sign():
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
    T_s = 300.0
    R = surface_energy_balance_residual(
        T_s=T_s, insolation=0.0, albedo=0.0, emissivity=1.0,
        K_surf=0.0, dz_surf=1.0, T_subsurf=T_s,
    )
    # With K_surf=0 and T_s == T_subsurf, conductive term is zero, so R = -sigma * T^4.
    assert R == -SIGMA_SB * T_s**4
