"""Regression: the JIT step kernel must match the pure-Python reference.

The production solver dispatches the inner Crank-Nicolson step through a
Numba-compiled kernel (``_step_fast`` -> ``_cn_step_kernel``). This test
pins that fast path to the original generic implementation
(``_step_python``) to floating-point round-off, so the two can never
silently drift and the published science stays byte-stable. It exercises:

* the radiative surface boundary condition (the science path),
* the Dirichlet boundary condition (validation path), and
* a non-Hayne conductivity model, to confirm the kernel stays generic
  over arbitrary ``K_func`` (Martinez / 3-layer / bedrock all rely on this).
"""
from __future__ import annotations

import numpy as np

from lunar.config import SITES, GRID, S0, T_LUNAR, DT_STEP
from lunar.constants import CHI_RADIATIVE, H_PARAMETER, K_SURFACE
from lunar.grid import make_geometric_grid
from lunar.properties import conductivity_hayne, conductivity_martinez
from lunar.solver import PixelInputs, _step_fast, _step_python

TOL = 1e-10


def _make_inputs(k_func, bc_mode="radiative"):
    grid = make_geometric_grid(**GRID)
    n_t = int(T_LUNAR / DT_STEP) + 1
    t = np.linspace(0.0, T_LUNAR, n_t)
    site = SITES["A15"]
    insol = (S0 * np.cos(np.deg2rad(site["lat"]))
             * np.maximum(0.0, np.cos(2 * np.pi * t / T_LUNAR)))
    T_forced = 250.0 + 60.0 * np.sin(2 * np.pi * t / T_LUNAR)
    inp = PixelInputs(
        grid=grid, t=t, bc_mode=bc_mode,
        insolation=insol,
        T_surface_forced=T_forced if bc_mode == "dirichlet" else None,
        albedo=site["albedo"], emissivity=site["emissivity"],
        Q_b=site["Q_BASAL"], K_func=k_func,
    )
    return grid, t, inp


def _trajectory_max_diff(k_func, bc_mode, n_steps=60):
    """Run the two implementations independently and return max |ΔT|."""
    grid, t, inp = _make_inputs(k_func, bc_mode)
    T_fast = np.full(grid.n_layers, 250.0)
    T_ref = np.full(grid.n_layers, 250.0)
    worst = 0.0
    for k in range(1, n_steps + 1):
        dt = float(t[k] - t[k - 1])
        if bc_mode == "dirichlet":
            sp = float(inp.T_surface_forced[k - 1])
            sn = float(inp.T_surface_forced[k])
        else:
            sp = sn = None
        T_fast, _ = _step_fast(grid, T_fast, sp, sn, inp, k, dt)
        T_ref, _ = _step_python(grid, T_ref, sp, sn, inp, k, dt)
        worst = max(worst, float(np.max(np.abs(T_fast - T_ref))))
    return worst


def _hayne(T, z):
    return conductivity_hayne(T, z, Ks=K_SURFACE, Kd=4.58e-3,
                              H=H_PARAMETER, chi=CHI_RADIATIVE)


def test_jit_matches_reference_radiative_hayne():
    assert _trajectory_max_diff(_hayne, "radiative") < TOL


def test_jit_matches_reference_dirichlet_hayne():
    assert _trajectory_max_diff(_hayne, "dirichlet") < TOL


def test_jit_matches_reference_nonhayne_model():
    # Martinez K(T, z) stands in for any non-Hayne callable; the kernel must
    # stay generic because it only ever sees the evaluated property arrays.
    assert _trajectory_max_diff(lambda T, z: conductivity_martinez(T, z=z),
                                "radiative") < TOL
