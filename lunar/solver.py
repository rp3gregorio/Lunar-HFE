"""1D subsurface heat-equation solver.

Solves

.. math::

    \\rho(z)\\, c_p(T)\\, \\partial_t T
        = \\partial_z \\big( K(T, z)\\, \\partial_z T \\big)

on a geometric depth grid. Two upper boundary conditions are supported:

* ``'dirichlet'`` — prescribed :math:`T_s(t)`. Used for analytical-wave
  validation: with constant coefficients the problem has a closed-form
  thermal-wave solution (see :func:`analytical_thermal_wave`).
* ``'radiative'`` — full non-linear surface energy balance solved by
  Newton iteration at each time step. This is what the science runs
  use. The bottom boundary is always the geothermal flux.

Spin-up
-------
For radiative BC runs, the driver loops over the forcing for
``n_lunations_spinup`` full diurnal cycles. Convergence is declared
when ``max |T^{k+1} - T^k| < 0.01 K`` between successive cycles, as
required by SKILL.md.

Performance
-----------
The tridiagonal sweep is a small inner loop but Numba JIT makes per-pixel
runs ~10-100x faster. The ``@njit`` fast path is wired via ``NUMBA_OK``;
when Numba is unavailable the code falls back to pure NumPy and the
tests still pass.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Literal

import numpy as np

from .constants import EMISSIVITY_DEFAULT, Q_B_SOUTH_POLAR, SIGMA_SB
from .grid import DepthGrid
from .properties import density_hayne, specific_heat

try:
    from numba import njit  # type: ignore

    NUMBA_OK = True
except Exception:  # pragma: no cover - numba is optional at import time
    NUMBA_OK = False

    def njit(*args, **kwargs):  # type: ignore
        def decorator(func):
            return func

        if len(args) == 1 and callable(args[0]):
            return args[0]
        return decorator


BCMode = Literal["dirichlet", "radiative"]


# ---------------------------------------------------------------------------
# Input / output containers
# ---------------------------------------------------------------------------


@dataclass
class PixelInputs:
    """All inputs required to run the 1D solver at one DEM pixel."""

    grid: DepthGrid
    t: np.ndarray  # time samples [s], shape (N_t,)
    bc_mode: BCMode = "radiative"
    # Radiative BC
    insolation: np.ndarray | None = None  # [W m^-2], shape (N_t,)
    albedo: float = 0.12
    emissivity: float = EMISSIVITY_DEFAULT
    # Dirichlet BC (used only for validation)
    T_surface_forced: np.ndarray | None = None  # shape (N_t,)
    # Bottom
    Q_b: float = Q_B_SOUTH_POLAR
    # Properties
    K_func: Callable[[np.ndarray, np.ndarray], np.ndarray] | None = None
    rho_func: Callable[[np.ndarray], np.ndarray] | None = None
    cp_func: Callable[[np.ndarray], np.ndarray] | None = None
    T_init: np.ndarray | None = None  # shape (N_z,)
    # Spin-up control (radiative mode only)
    n_lunations_spinup: int = 10
    spinup_tol_K: float = 0.01
    #: When set, the convergence check uses only cells with
    #: ``z_mid <= spinup_depth_m`` (default: all cells). Set to one
    #: diurnal skin depth (~0.1 m) for fast surface-T convergence
    #: when deep cells matter little for the diagnostic of interest.
    spinup_depth_m: float | None = None


@dataclass
class PixelOutputs:
    """Solver output for one DEM pixel."""

    T: np.ndarray  # shape (N_z, N_t) [K]
    z: np.ndarray  # shape (N_z,) [m]
    t: np.ndarray  # shape (N_t,) [s]
    T_surface: np.ndarray | None = None  # shape (N_t,) [K] — true skin temperature
    n_spinup_cycles: int = 0
    converged: bool = False
    diagnostics: dict = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Core numerics
# ---------------------------------------------------------------------------


@njit(cache=True)
def _face_harmonic_mean(K: np.ndarray) -> np.ndarray:
    """Harmonic-mean face conductivities between adjacent cells."""
    n = K.size
    K_face = np.empty(n + 1)
    K_face[0] = K[0]
    K_face[-1] = K[-1]
    for i in range(1, n):
        if K[i - 1] == 0.0 or K[i] == 0.0:
            K_face[i] = 0.0
        else:
            K_face[i] = 2.0 * K[i - 1] * K[i] / (K[i - 1] + K[i])
    return K_face


@njit(cache=True)
def _thomas(a: np.ndarray, b: np.ndarray, c: np.ndarray, d: np.ndarray) -> np.ndarray:
    """Thomas algorithm for an (a, b, c) tridiagonal system A x = d.

    ``a`` and ``c`` are the sub- and super-diagonals; ``a[0]`` and
    ``c[n-1]`` are ignored. All arrays have shape ``(n,)``.
    """
    n = b.size
    cp = np.empty(n)
    dp = np.empty(n)
    x = np.empty(n)
    cp[0] = c[0] / b[0]
    dp[0] = d[0] / b[0]
    for i in range(1, n):
        m = b[i] - a[i] * cp[i - 1]
        cp[i] = c[i] / m if i < n - 1 else 0.0
        dp[i] = (d[i] - a[i] * dp[i - 1]) / m
    x[n - 1] = dp[n - 1]
    for i in range(n - 2, -1, -1):
        x[i] = dp[i] - cp[i] * x[i + 1]
    return x


def surface_energy_balance_residual(
    T_s: float,
    insolation: float,
    albedo: float,
    emissivity: float,
    K_surf: float,
    dz_surf: float,
    T_subsurf: float,
) -> float:
    """Residual :math:`R(T_s)` of the non-linear surface energy balance.

    .. math::

        R(T_s) = (1-A) S
                 - \\varepsilon \\sigma T_s^4
                 - K \\frac{T_s - T_\\mathrm{sub}}{\\Delta z / 2}

    Roots of :math:`R(T_s)=0` are found by Newton iteration inside
    :func:`solve_pixel`.
    """
    radiative_in = (1.0 - albedo) * insolation
    radiative_out = emissivity * SIGMA_SB * T_s**4
    conductive = K_surf * (T_s - T_subsurf) / (0.5 * dz_surf)
    return radiative_in - radiative_out - conductive


def _solve_surface_newton(
    insolation: float,
    albedo: float,
    emissivity: float,
    K_surf: float,
    dz_surf: float,
    T_subsurf: float,
    T_s_guess: float,
    tol: float = 1e-4,
    max_iter: int = 40,
) -> float:
    """Newton solve for the surface temperature given the non-linear BC.

    Derivative of :func:`surface_energy_balance_residual`::

        dR/dT_s = -4 eps sigma T_s^3 - 2 K / dz_surf

    The derivative is always negative, so Newton converges from any
    positive starting point.
    """
    T_s = max(T_s_guess, 1.0)
    for _ in range(max_iter):
        R = surface_energy_balance_residual(
            T_s, insolation, albedo, emissivity, K_surf, dz_surf, T_subsurf
        )
        dR = -4.0 * emissivity * SIGMA_SB * T_s**3 - 2.0 * K_surf / dz_surf
        step = R / dR
        T_s_new = T_s - step
        if T_s_new < 1.0:
            T_s_new = 0.5 * (T_s + 1.0)
        if abs(T_s_new - T_s) < tol:
            return T_s_new
        T_s = T_s_new
    return T_s  # best effort — caller can flag diagnostics


# ---------------------------------------------------------------------------
# Driver
# ---------------------------------------------------------------------------


def _default_K(T: np.ndarray, z: np.ndarray) -> np.ndarray:
    from .properties import conductivity_hayne

    return conductivity_hayne(T, z)


def _default_rho(z: np.ndarray) -> np.ndarray:
    return density_hayne(z)


def _default_cp(T: np.ndarray) -> np.ndarray:
    return specific_heat(T, model="hayne")


def _step(
    grid: DepthGrid,
    T_prev: np.ndarray,
    T_surface_prev: float | None,
    T_surface_new: float | None,
    inputs: PixelInputs,
    idx_new: int,
    dt: float,
) -> np.ndarray:
    """One Crank-Nicolson step.

    Physics::

        cap_i dT_i/dt = flux_right(i) - flux_left(i)

    where flux_left(i) = K_face[i] * (T_i - T_{i-1}) / dz_c[i], etc.
    The Crank-Nicolson scheme averages implicit (n+1) and explicit (n)
    evaluations of the right-hand side.

    Boundary conditions
    -------------------
    Upper (z=0): either Dirichlet (``T_surface_prev`` and
    ``T_surface_new`` supplied) or non-linear radiative (both None; the
    surface temperature is solved by Newton iteration against the
    current sub-surface cell).
    Lower (z=z_max): geothermal flux ``Q_b`` (Neumann).

    Property coefficients (K, rho, c_p) are frozen at the explicit
    half-step T_prev — this is the standard linearisation for a
    non-linear heat equation and is adequate once the properties vary
    slowly within a time step, which is true for the spin-up grid.
    """
    K_func = inputs.K_func or _default_K
    rho_func = inputs.rho_func or _default_rho
    cp_func = inputs.cp_func or _default_cp

    K = K_func(T_prev, grid.z_mid)
    rho = rho_func(grid.z_mid)
    cp = cp_func(T_prev)
    rho_cp = rho * cp

    n = grid.n_layers
    dz = grid.dz
    K_face = _face_harmonic_mean(K)

    dz_c = np.empty(n + 1)
    dz_c[0] = 0.5 * dz[0]
    dz_c[-1] = 0.5 * dz[-1]
    for i in range(1, n):
        dz_c[i] = 0.5 * (dz[i - 1] + dz[i])

    cap = rho_cp * dz

    # alpha_l[i] = dt * K_face[i]   / (dz_c[i]   * cap[i])
    # alpha_r[i] = dt * K_face[i+1] / (dz_c[i+1] * cap[i])
    alpha_l = np.zeros(n)
    alpha_r = np.zeros(n)
    for i in range(n):
        alpha_l[i] = dt * K_face[i] / (dz_c[i] * cap[i])
        alpha_r[i] = dt * K_face[i + 1] / (dz_c[i + 1] * cap[i])

    # Build tridiagonal (Crank-Nicolson, theta=0.5). For interior cells
    # we have both left and right neighbours.
    a = np.zeros(n)
    b = np.zeros(n)
    c = np.zeros(n)
    for i in range(n):
        a[i] = -0.5 * alpha_l[i]
        c[i] = -0.5 * alpha_r[i]
        b[i] = 1.0 + 0.5 * (alpha_l[i] + alpha_r[i])

    # Explicit-side RHS
    d = np.zeros(n)
    for i in range(n):
        left = T_prev[i - 1] if i > 0 else T_prev[i]
        right = T_prev[i + 1] if i < n - 1 else T_prev[i]
        d[i] = (
            0.5 * alpha_l[i] * left
            + (1.0 - 0.5 * (alpha_l[i] + alpha_r[i])) * T_prev[i]
            + 0.5 * alpha_r[i] * right
        )

    # --- Upper (surface) BC -------------------------------------------------
    # alpha_l[0] already encodes the conductance between cell 0's center
    # and a ghost at the top face (distance dz_c[0] = dz[0]/2 and K_face[0]).
    # Our loop above used ``left = T_prev[0]`` as a wall surrogate; we
    # now replace that wall contribution with the true Dirichlet ghost.

    if T_surface_prev is not None and T_surface_new is not None:
        T_s_prev, T_s_new = float(T_surface_prev), float(T_surface_new)
    else:
        # Radiative BC: solve for the new surface temperature holding the
        # sub-surface at the explicit-level T_prev[0]. First-order in time
        # on the non-linearity, which is adequate during spin-up.
        assert inputs.insolation is not None
        T_s_new = _solve_surface_newton(
            insolation=float(inputs.insolation[idx_new]),
            albedo=inputs.albedo,
            emissivity=inputs.emissivity,
            K_surf=K[0],
            dz_surf=dz[0],
            T_subsurf=float(T_prev[0]),
            T_s_guess=float(T_prev[0]),
        )
        T_s_prev = T_s_new  # constant-within-step on the explicit side

    # b[0] already has the 0.5*alpha_l[0] contribution from the loop.
    # Cancel the wall explicit-side term and add the real ghost terms.
    d[0] -= 0.5 * alpha_l[0] * T_prev[0]  # remove the wall surrogate
    d[0] += 0.5 * alpha_l[0] * T_s_prev  # explicit-side ghost
    d[0] += 0.5 * alpha_l[0] * T_s_new  # implicit-side ghost, moved to RHS

    # --- Lower BC: geothermal flux (Neumann) --------------------------------
    # The correct equation for cell n-1 is:
    #   (1 + 0.5 alpha_l[-1]) T^{n+1}[-1] - 0.5 alpha_l[-1] T^{n+1}[-2]
    #   = (1 - 0.5 alpha_l[-1]) T^n[-1] + 0.5 alpha_l[-1] T^n[-2]
    #     + dt * Q_b / cap[-1]
    # The loop's assembly computed b[-1] with an extra 0.5*alpha_r[-1] and
    # the RHS wall term (1 - 0.5(alpha_l + alpha_r)) T^n[-1] + 0.5 alpha_r T^n[-1]
    # which simplifies to (1 - 0.5 alpha_l) T^n[-1]. That explicit-side is
    # already correct. We only need to fix b[-1] and add the flux source.
    b[-1] -= 0.5 * alpha_r[-1]
    d[-1] += dt * inputs.Q_b / cap[-1]

    return _thomas(a, b, c, d), T_s_new


def solve_pixel(inputs: PixelInputs) -> PixelOutputs:
    """Drive the 1D thermal solver for one pixel over ``inputs.t``.

    Supports both Dirichlet (for analytical validation) and radiative
    (for science runs) upper boundary conditions. Radiative runs perform
    a spin-up of ``inputs.n_lunations_spinup`` cycles and declare
    convergence when the maximum cell-by-cell temperature change between
    successive cycles drops below ``inputs.spinup_tol_K``.
    """
    grid = inputs.grid
    n_z = grid.n_layers
    n_t = inputs.t.size
    if n_t < 2:
        raise ValueError("inputs.t must have at least two samples")

    # Initial condition: equilibrium with the mean surface forcing if
    # none provided.
    if inputs.T_init is None:
        if inputs.T_surface_forced is not None:
            T = np.full(n_z, float(np.mean(inputs.T_surface_forced)))
        elif inputs.insolation is not None:
            # Very rough zeroth-order: set interior to the radiative
            # equilibrium of the mean flux; far from final but a decent
            # start for Newton in the early spin-up.
            S_mean = float(np.mean(inputs.insolation))
            T_eq = ((1 - inputs.albedo) * max(S_mean, 1.0)
                    / (inputs.emissivity * SIGMA_SB)) ** 0.25
            T = np.full(n_z, max(T_eq, 50.0))
        else:
            T = np.full(n_z, 200.0)
    else:
        T = np.asarray(inputs.T_init, dtype=np.float64).copy()

    out = np.empty((n_z, n_t))
    out[:, 0] = T
    T_surf_arr = np.empty(n_t)
    T_surf_arr[0] = T[0]  # initial guess

    if inputs.bc_mode == "dirichlet":
        if inputs.T_surface_forced is None:
            raise ValueError("dirichlet BC requires T_surface_forced")
        T_s_arr = np.asarray(inputs.T_surface_forced, dtype=np.float64)
        if T_s_arr.shape[0] != n_t:
            raise ValueError("T_surface_forced must have the same length as t")
        for k in range(1, n_t):
            dt = float(inputs.t[k] - inputs.t[k - 1])
            T, T_s_k = _step(
                grid,
                T_prev=T,
                T_surface_prev=float(T_s_arr[k - 1]),
                T_surface_new=float(T_s_arr[k]),
                inputs=inputs,
                idx_new=k,
                dt=dt,
            )
            out[:, k] = T
            T_surf_arr[k] = T_s_k
        return PixelOutputs(
            T=out, z=grid.z_mid, t=inputs.t,
            T_surface=T_s_arr,
            converged=True, n_spinup_cycles=0,
        )

    # Radiative BC with spin-up
    if inputs.insolation is None:
        raise ValueError("radiative BC requires insolation[:]")
    if inputs.insolation.shape[0] != n_t:
        raise ValueError("insolation must have the same length as t")

    converged = False
    delta = np.nan
    cycle = 0
    for cycle in range(1, inputs.n_lunations_spinup + 1):
        T_cycle_start = T.copy()
        # Record the cycle-start state as t=0 so the output is seamless
        out[:, 0] = T.copy()
        T_surf_arr[0] = _solve_surface_newton(
            insolation=float(inputs.insolation[0]),
            albedo=inputs.albedo,
            emissivity=inputs.emissivity,
            K_surf=float((inputs.K_func or _default_K)(T, grid.z_mid)[0]),
            dz_surf=float(grid.dz[0]),
            T_subsurf=float(T[0]),
            T_s_guess=float(T[0]),
        )
        for k in range(1, n_t):
            dt = float(inputs.t[k] - inputs.t[k - 1])
            T, T_s_k = _step(
                grid,
                T_prev=T,
                T_surface_prev=None,
                T_surface_new=None,
                inputs=inputs,
                idx_new=k,
                dt=dt,
            )
            out[:, k] = T
            T_surf_arr[k] = T_s_k
        delta = float(
            np.max(
                np.abs(
                    T[grid.z_mid <= inputs.spinup_depth_m]
                    - T_cycle_start[grid.z_mid <= inputs.spinup_depth_m]
                )
                if inputs.spinup_depth_m is not None
                else np.abs(T - T_cycle_start)
            )
        )
        if delta < inputs.spinup_tol_K and cycle >= 2:
            converged = True
            break

    return PixelOutputs(
        T=out, z=grid.z_mid, t=inputs.t,
        T_surface=T_surf_arr,
        n_spinup_cycles=cycle, converged=converged,
        diagnostics={"last_cycle_max_dT": delta},
    )


# ---------------------------------------------------------------------------
# Analytical reference solution (used for validation)
# ---------------------------------------------------------------------------


def analytical_thermal_wave(
    z: np.ndarray,
    t: np.ndarray,
    T_mean: float,
    amplitude: float,
    period: float,
    alpha: float,
) -> np.ndarray:
    """Semi-infinite thermal wave with prescribed sinusoidal surface T.

    Closed-form solution of ``dT/dt = alpha * d2T/dz2`` with
    ``T(0, t) = T_mean + A sin(omega t)`` and ``T(infinity, t) = T_mean``:

    .. math::

        T(z, t) = T_\\mathrm{mean}
                + A\\, e^{-z/\\delta}\\, \\sin(\\omega t - z/\\delta),

    with skin depth :math:`\\delta = \\sqrt{2\\alpha/\\omega}` and
    :math:`\\omega = 2\\pi / P`.

    Returns a ``(len(z), len(t))`` array. Used by the solver test to
    check first-order correctness in a regime where all coefficients
    are constant.
    """
    omega = 2.0 * np.pi / period
    delta = np.sqrt(2.0 * alpha / omega)
    Z = np.asarray(z, dtype=np.float64)[:, None]
    T_arr = np.asarray(t, dtype=np.float64)[None, :]
    return T_mean + amplitude * np.exp(-Z / delta) * np.sin(omega * T_arr - Z / delta)
