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
Only the two per-cell loops -- ``_face_harmonic_mean`` and the ``_thomas``
tridiagonal sweep -- carry ``@njit``; the rest of ``_step`` (the tridiagonal
assembly, the Newton surface solve) runs as interpreted Python for-loops either
way. So ``@njit`` here buys only a measured ~1.5x on the per-lunation cost
(83 vs 128 ms/lun with NUMBA_DISABLE_JIT=1). Compiling the WHOLE step is what
helps: a faithful C port of the entire solver (verified to 9e-13 K) runs the same
brute-force solve ~170x faster -- and ``@njit``-ing all of ``_step`` would too,
without a C build. We keep the readable NumPy because the flux-anchored method
already makes each solve cheap (~7 s). See results/speedup_benchmark.json.
The ``@njit`` fast path is wired via ``NUMBA_OK``; when Numba is unavailable the
code falls back to pure NumPy and the tests still pass.
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
    #: Fast-path switch: when set to ``(Ks, Kd, H, chi)`` [SI] -- or the
    #: 6-tuple ``(Ks, Kd, H, chi, rho_s, rho_d)`` for density-perturbed
    #: sensitivity runs -- the radiative
    #: march runs in the compiled ``_march_radiative_hayne`` kernel instead of
    #: the generic ``_step`` loop (~2 orders of magnitude faster; equality
    #: asserted to <1e-9 K by tests/test_solver.py::test_fast_march_matches_
    #: generic). Setting it DECLARES that the property set is the standard
    #: Hayne one -- conductivity_hayne(Ks,Kd,H,chi), density_hayne with the
    #: constants' rho_s/rho_d and the same H, and the Hayne cp polynomial --
    #: any custom K_func/rho_func/cp_func is IGNORED by the march. Callers
    #: with non-standard properties (3layer, martinez) must leave it None.
    hayne_params: tuple | None = None
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


def periodic_time_grid(dt_target: float) -> np.ndarray:
    """The ONE way to build the solver's time grid for periodic (lunation) work.

    Returns ``t = arange(n) * dt`` with ``n = round(T_LUNAR / dt_target)`` and
    ``dt = T_LUNAR / n`` — a COMMENSURATE grid: n steps of dt tile one lunation
    exactly, so the cycle-to-cycle chaining in ``solve_pixel`` wraps with zero
    phase error and the cycle mean weights every phase once.

    Why this exists (audit 2026-07-03): a plain ``arange(0, T_LUNAR, dt)``
    leaves a sliver (T_LUNAR - n*dt ≠ 0) at the wrap, silently distorting the
    effective forcing period — measured at ~70 mK in sensor-band ⟨T⟩, i.e.
    ~0.1 mW in K_d*. The older inclusive ``linspace`` avoided the sliver but
    double-counted the noon phase in cycle means. This constructor has neither
    defect. The realized dt differs from ``dt_target`` by < 0.05 %; treat the
    TARGET as the config knob and never build a lunation grid any other way.
    """
    from .constants import LUNATION_SECONDS
    n = int(round(LUNATION_SECONDS / float(dt_target)))
    return np.arange(n) * (LUNATION_SECONDS / n)


def standard_insolation(lat_deg: float, t: np.ndarray) -> np.ndarray:
    """The ONE way to build the solar forcing for this project.

    Returns the RAW incident flux at the surface,

        S(t) = S0 * cos(lat) * max(0, cos(2 pi t / T_LUNAR)),

    i.e. the equatorial cosine day/night model tilted to the site latitude.

    CONVENTION -- read before writing your own forcing:
      * Do NOT pre-multiply by (1 - albedo). The solver applies the albedo
        internally in the surface energy balance (``radiative_in =
        (1 - albedo) * insolation`` in ``_surface_residual``); a caller that
        bakes (1 - A) into the forcing counts the albedo TWICE.
      * Do NOT omit cos(lat). Both Apollo sites are off-equator (A15 26.1 N,
        A17 20.2 N); dropping the factor runs a fictitious equatorial site.
    An audit on 2026-07-03 found eight demo/figure callers violating one or
    both rules (published retrieval numbers were unaffected -- retrieve_kd
    always did this correctly). Use this helper instead of re-deriving.

    Parameters
    ----------
    lat_deg : site latitude [degrees] (``config.SITES[site]["lat"]``)
    t : times [s], spanning one forcing cycle for equilibrium work.

    Returns
    -------
    ndarray like ``t`` -- incident flux [W m^-2], zero at night.
    """
    from .constants import SOLAR_CONSTANT, LUNATION_SECONDS
    phase = 2.0 * np.pi * np.asarray(t, dtype=float) / LUNATION_SECONDS
    return SOLAR_CONSTANT * np.cos(np.deg2rad(lat_deg)) * np.maximum(0.0, np.cos(phase))


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
    vals = {
        "insolation": insolation,
        "albedo": albedo,
        "emissivity": emissivity,
        "K_surf": K_surf,
        "dz_surf": dz_surf,
        "T_subsurf": T_subsurf,
        "T_s_guess": T_s_guess,
    }
    bad = [name for name, val in vals.items() if not np.isfinite(val)]
    if bad:
        raise ValueError(f"surface Newton inputs must be finite; bad: {', '.join(bad)}")
    if not 0.0 <= albedo < 1.0:
        raise ValueError("albedo must satisfy 0 <= albedo < 1")
    if emissivity <= 0.0:
        raise ValueError("emissivity must be positive")
    if K_surf <= 0.0:
        raise ValueError("K_surf must be positive")
    if dz_surf <= 0.0:
        raise ValueError("dz_surf must be positive")
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
    radiative_T_s_prev: float | None = None,
    n_picard: int | None = None,
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

    Property treatment (midpoint Picard, 2026-07-03)
    ------------------------------------------------
    K, rho, c_p depend on T, so where we evaluate them sets the order of
    the scheme. Freezing them at the explicit level T_prev -- the
    classic linearisation this solver used until 2026-07-03 -- makes the
    whole step FIRST order in dt regardless of the trapezoidal
    averaging, and the error is not academic: the retrieved K_d*(A17)
    drifted -0.30 mW per dt halving (7.699 / 7.397 / 7.251 at dt =
    1800/900/450 s; Richardson limit 7.104 mW,
    ``results/dt_kdstar_certification_A17wide.json``).

    The fix is ``n_picard`` corrector sweeps: after the predictor solve,
    re-evaluate the properties at the time-midpoint state
    ``0.5*(T_prev + T_new)`` and re-solve. Property evaluation at the
    midpoint is what the implicit-midpoint rule prescribes and restores
    second-order accuracy; the sweeps also move the surface Newton's
    sub-surface anchor from the lagged ``T_prev[0]`` to the implicit
    ``T_new[0]``, closing the surface-interior coupling. The default
    resolves ``config.CN_PICARD_SWEEPS`` at call time (a hard-coded
    signature default is exactly how the stale ``n_inner=12`` bug hid).
    """
    if n_picard is None:
        from .config import CN_PICARD_SWEEPS
        n_picard = CN_PICARD_SWEEPS

    K_func = inputs.K_func or _default_K
    rho_func = inputs.rho_func or _default_rho
    cp_func = inputs.cp_func or _default_cp

    n = grid.n_layers
    dz = grid.dz
    rho = rho_func(grid.z_mid)  # z-only: loop-invariant

    dz_c = np.empty(n + 1)
    dz_c[0] = 0.5 * dz[0]
    dz_c[-1] = 0.5 * dz[-1]
    for i in range(1, n):
        dz_c[i] = 0.5 * (dz[i - 1] + dz[i])

    # Predictor sweep evaluates properties at T_prev; each corrector
    # sweep re-evaluates them at the midpoint of the step just solved.
    T_props = T_prev
    T_subsurf = float(T_prev[0])  # surface Newton anchor (implicit after sweep 0)
    T_s_new: float | None = None
    T_new = T_prev

    for _sweep in range(1 + n_picard):
        K = K_func(T_props, grid.z_mid)
        cp = cp_func(T_props)
        K_face = _face_harmonic_mean(K)
        cap = rho * cp * dz

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

        # --- Upper (surface) BC ---------------------------------------------
        # alpha_l[0] already encodes the conductance between cell 0's center
        # and a ghost at the top face (distance dz_c[0] = dz[0]/2 and
        # K_face[0]). Our loop above used ``left = T_prev[0]`` as a wall
        # surrogate; we now replace that wall contribution with the true
        # Dirichlet ghost.

        if T_surface_prev is not None and T_surface_new is not None:
            T_s_prev, T_s_new = float(T_surface_prev), float(T_surface_new)
        else:
            # Radiative BC: the balance holds instantaneously at t^{n+1},
            # coupled to the sub-surface cell. Sweep 0 anchors it at the
            # lagged T_prev[0]; corrector sweeps re-anchor at T_new[0].
            assert inputs.insolation is not None
            T_s_new = _solve_surface_newton(
                insolation=float(inputs.insolation[idx_new]),
                albedo=inputs.albedo,
                emissivity=inputs.emissivity,
                K_surf=K[0],
                dz_surf=dz[0],
                T_subsurf=T_subsurf,
                T_s_guess=(T_s_new if T_s_new is not None
                           else float(T_prev[0])),
            )
            # Explicit-side ghost: use the PREVIOUS step's surface
            # temperature when the march supplies it, making the boundary
            # genuinely trapezoidal (Crank-Nicolson-consistent). The old
            # behavior (T_s_prev = T_s_new, the same endpoint Newton
            # solution on both sides) degraded the whole scheme to FIRST
            # order in dt at the day/night terminator -- measured as a
            # 136 mK/dt-halving drift in sensor-band <T> (audit
            # 2026-07-03). Zero extra cost: the previous T_s is already
            # stored by solve_pixel.
            T_s_prev = (float(radiative_T_s_prev)
                        if radiative_T_s_prev is not None else T_s_new)

        # b[0] already has the 0.5*alpha_l[0] contribution from the loop.
        # Cancel the wall explicit-side term and add the real ghost terms.
        d[0] -= 0.5 * alpha_l[0] * T_prev[0]  # remove the wall surrogate
        d[0] += 0.5 * alpha_l[0] * T_s_prev  # explicit-side ghost
        d[0] += 0.5 * alpha_l[0] * T_s_new  # implicit-side ghost, moved to RHS

        # --- Lower BC: geothermal flux (Neumann) ----------------------------
        # The correct equation for cell n-1 is:
        #   (1 + 0.5 alpha_l[-1]) T^{n+1}[-1] - 0.5 alpha_l[-1] T^{n+1}[-2]
        #   = (1 - 0.5 alpha_l[-1]) T^n[-1] + 0.5 alpha_l[-1] T^n[-2]
        #     + dt * Q_b / cap[-1]
        # The loop's assembly computed b[-1] with an extra 0.5*alpha_r[-1] and
        # the RHS wall term (1 - 0.5(alpha_l + alpha_r)) T^n[-1]
        # + 0.5 alpha_r T^n[-1], which simplifies to (1 - 0.5 alpha_l) T^n[-1].
        # That explicit-side is already correct. We only need to fix b[-1]
        # and add the flux source.
        b[-1] -= 0.5 * alpha_r[-1]
        d[-1] += dt * inputs.Q_b / cap[-1]

        T_new = _thomas(a, b, c, d)
        # midpoint state + implicit surface anchor for the next sweep
        T_props = 0.5 * (T_prev + T_new)
        T_subsurf = float(T_new[0])

    return T_new, T_s_new


# ---------------------------------------------------------------------------
# Compiled fast march (standard Hayne property set only)
# ---------------------------------------------------------------------------
# A line-for-line transcription of the verified C++ port (cpp/solver.cpp,
# itself equal to the generic Python march to ~1e-12 K): scalar Hayne
# properties, midpoint-Picard Crank-Nicolson step, trapezoidal surface ghost,
# basal Q_b Neumann, cycle chaining WITH the wrap step. Exists because the
# generic ``_step`` loop is pure Python and the 2026-07-03 numerics fixes
# (Picard sweeps x wrap step x dt=1800) made it the pipeline bottleneck.


@njit(cache=True)
def _newton_ts_njit(S, albedo, emissivity, K_surf, dz_surf, T_sub, guess,
                    sigma):
    """Scalar surface Newton, mirroring _solve_surface_newton exactly."""
    Ts = guess if guess > 1.0 else 1.0
    for _ in range(40):
        R = ((1.0 - albedo) * S - emissivity * sigma * Ts**4
             - K_surf * (Ts - T_sub) / (0.5 * dz_surf))
        dR = -4.0 * emissivity * sigma * Ts**3 - 2.0 * K_surf / dz_surf
        Tn = Ts - R / dR
        if Tn < 1.0:
            Tn = 0.5 * (Ts + 1.0)
        if abs(Tn - Ts) < 1e-4:
            return Tn
        Ts = Tn
    return Ts


@njit(cache=True)
def _march_radiative_hayne(z, dz, dz_c, t, insol, T, out, Tsurf,
                           albedo, emissivity, Qb,
                           Ks, Kd, Hh, chi, Tref, rho_s, rho_d,
                           c0, c1, c2, c3, c4, sigma,
                           n_picard, n_lun,
                           spinup_tol, spinup_depth_m, use_depth_mask):
    """Radiative spin-up march, compiled. Mutates T/out/Tsurf in place.

    Returns (cycles_run, converged, last_delta). Semantics identical to the
    generic branch of solve_pixel (including the wrap step and the
    cycle>=2 convergence rule).
    """
    n = z.size
    n_t = t.size
    dt_wrap = t[1] - t[0]

    rho = np.empty(n)
    for i in range(n):
        rho[i] = rho_d - (rho_d - rho_s) * np.exp(-z[i] / Hh)

    K = np.empty(n)
    Kf = np.empty(n + 1)
    cap = np.empty(n)
    al = np.empty(n)
    ar = np.empty(n)
    a = np.empty(n)
    b = np.empty(n)
    c = np.empty(n)
    d = np.empty(n)
    Tprops = np.empty(n)
    T_cycle_start = np.empty(n)
    x = T.copy()

    Ts_at_zero = -1.0
    converged = False
    delta = np.nan
    cyc = 0
    for cyc in range(1, n_lun + 1):
        for i in range(n):
            T_cycle_start[i] = T[i]
            out[i, 0] = T[i]
        if Ts_at_zero > 0.0:
            Tsurf[0] = Ts_at_zero
        else:
            Kc0 = Kd - (Kd - Ks) * np.exp(-z[0] / Hh)
            r0 = T[0] / Tref
            Tsurf[0] = _newton_ts_njit(insol[0], albedo, emissivity,
                                       Kc0 * (1.0 + chi * r0 * r0 * r0),
                                       dz[0], T[0], T[0], sigma)
        # n_t-1 in-grid steps, then the wrap step t[-1] -> P (idx 0 forcing)
        for k in range(1, n_t + 1):
            wrap = k == n_t
            dt = dt_wrap if wrap else t[k] - t[k - 1]
            S_new = insol[0] if wrap else insol[k]
            Ts_prev = Tsurf[n_t - 1] if wrap else Tsurf[k - 1]
            for i in range(n):
                Tprops[i] = T[i]
            T_sub = T[0]
            Ts_new = T[0]
            for _sweep in range(n_picard + 1):
                for i in range(n):
                    Kc = Kd - (Kd - Ks) * np.exp(-z[i] / Hh)
                    r = Tprops[i] / Tref
                    K[i] = Kc * (1.0 + chi * r * r * r)
                Kf[0] = K[0]
                Kf[n] = K[n - 1]
                for i in range(1, n):
                    if K[i - 1] == 0.0 or K[i] == 0.0:
                        Kf[i] = 0.0
                    else:
                        Kf[i] = 2.0 * K[i - 1] * K[i] / (K[i - 1] + K[i])
                for i in range(n):
                    Tp = Tprops[i]
                    cp_i = c0 + Tp * (c1 + Tp * (c2 + Tp * (c3 + Tp * c4)))
                    cap[i] = rho[i] * cp_i * dz[i]
                    al[i] = dt * Kf[i] / (dz_c[i] * cap[i])
                    ar[i] = dt * Kf[i + 1] / (dz_c[i + 1] * cap[i])
                    a[i] = -0.5 * al[i]
                    c[i] = -0.5 * ar[i]
                    b[i] = 1.0 + 0.5 * (al[i] + ar[i])
                for i in range(n):
                    left = T[i - 1] if i > 0 else T[i]
                    right = T[i + 1] if i < n - 1 else T[i]
                    d[i] = (0.5 * al[i] * left
                            + (1.0 - 0.5 * (al[i] + ar[i])) * T[i]
                            + 0.5 * ar[i] * right)
                Ts_new = _newton_ts_njit(S_new, albedo, emissivity, K[0],
                                         dz[0], T_sub, Ts_new, sigma)
                d[0] -= 0.5 * al[0] * T[0]
                d[0] += 0.5 * al[0] * Ts_prev
                d[0] += 0.5 * al[0] * Ts_new
                b[n - 1] -= 0.5 * ar[n - 1]
                d[n - 1] += dt * Qb / cap[n - 1]
                x = _thomas(a, b, c, d)
                for i in range(n):
                    Tprops[i] = 0.5 * (T[i] + x[i])
                T_sub = x[0]
            for i in range(n):
                T[i] = x[i]
            if wrap:
                Ts_at_zero = Ts_new
            else:
                for i in range(n):
                    out[i, k] = T[i]
                Tsurf[k] = Ts_new
        delta = 0.0
        for i in range(n):
            if use_depth_mask and z[i] > spinup_depth_m:
                continue
            dv = abs(T[i] - T_cycle_start[i])
            if dv > delta:
                delta = dv
        if delta < spinup_tol and cyc >= 2:
            converged = True
            break
    return cyc, converged, delta


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

    # Fast path: compiled march for the standard Hayne property set (see
    # the hayne_params field docs; equality with the generic path is a
    # tested invariant, not an assumption).
    if inputs.hayne_params is not None and NUMBA_OK:
        from .config import CN_PICARD_SWEEPS
        from .constants import (RHO_SURFACE, RHO_DEEP, T_REFERENCE,
                                CP_HAYNE_C0, CP_HAYNE_C1, CP_HAYNE_C2,
                                CP_HAYNE_C3, CP_HAYNE_C4)
        hp = tuple(float(v) for v in inputs.hayne_params)
        if len(hp) == 4:      # (Ks, Kd, H, chi); densities from constants
            Ks_, Kd_, H_, chi_ = hp
            rho_s_, rho_d_ = RHO_SURFACE, RHO_DEEP
        else:                 # 6-tuple adds (rho_s, rho_d) for sensitivity runs
            Ks_, Kd_, H_, chi_, rho_s_, rho_d_ = hp
        dz = grid.dz
        dz_c = np.empty(n_z + 1)
        dz_c[0] = 0.5 * dz[0]
        dz_c[-1] = 0.5 * dz[-1]
        dz_c[1:-1] = 0.5 * (dz[:-1] + dz[1:])
        depth = (float(inputs.spinup_depth_m)
                 if inputs.spinup_depth_m is not None else 0.0)
        cyc, conv, delta = _march_radiative_hayne(
            grid.z_mid.astype(np.float64), dz.astype(np.float64), dz_c,
            np.asarray(inputs.t, dtype=np.float64),
            np.asarray(inputs.insolation, dtype=np.float64),
            T, out, T_surf_arr,
            float(inputs.albedo), float(inputs.emissivity), float(inputs.Q_b),
            Ks_, Kd_, H_, chi_, T_REFERENCE, rho_s_, rho_d_,
            CP_HAYNE_C0, CP_HAYNE_C1, CP_HAYNE_C2, CP_HAYNE_C3, CP_HAYNE_C4,
            SIGMA_SB, int(CN_PICARD_SWEEPS), int(inputs.n_lunations_spinup),
            float(inputs.spinup_tol_K), depth,
            inputs.spinup_depth_m is not None)
        return PixelOutputs(
            T=out, z=grid.z_mid, t=inputs.t, T_surface=T_surf_arr,
            n_spinup_cycles=int(cyc), converged=bool(conv),
            diagnostics={"last_cycle_max_dT": float(delta),
                         "fast_path": True},
        )

    converged = False
    delta = np.nan
    cycle = 0
    # The WRAP step (found 2026-07-03, the wrap-sliver bug's final form):
    # t[] spans [0, P-dt] (periodic grid, no duplicated endpoint), so the
    # k-loop below advances only P-dt seconds per cycle. Chaining cycles
    # without also marching the final step t[-1] -> P (whose forcing is
    # insolation[0] again) relabels the t = P-dt state as t = 0 -- a phase
    # slip of exactly dt per cycle that makes the PERIODIC ATTRACTOR itself
    # first-order in dt (+61 mK/halving at dt=1800, depth-uniform; it was
    # the true source of the K_d*(A17) dt drift, NOT the property
    # linearisation). The wrap step below closes the cycle; with it the
    # attractor is second-order (toy study, audit F-5 addendum III).
    dt_wrap = float(inputs.t[1] - inputs.t[0])
    T_s_at_zero: float | None = None
    for cycle in range(1, inputs.n_lunations_spinup + 1):
        T_cycle_start = T.copy()
        # Record the cycle-start state as t=0 so the output is seamless
        out[:, 0] = T.copy()
        if T_s_at_zero is not None:
            # surface temperature at t=0 produced by the previous cycle's
            # wrap step -- already constraint-consistent with T[0]
            T_surf_arr[0] = T_s_at_zero
        else:
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
                radiative_T_s_prev=float(T_surf_arr[k - 1]),
            )
            out[:, k] = T
            T_surf_arr[k] = T_s_k
        # wrap step: t[-1] -> period end == next cycle's t=0 (idx_new=0)
        T, T_s_wrap = _step(
            grid,
            T_prev=T,
            T_surface_prev=None,
            T_surface_new=None,
            inputs=inputs,
            idx_new=0,
            dt=dt_wrap,
            radiative_T_s_prev=float(T_surf_arr[-1]),
        )
        T_s_at_zero = float(T_s_wrap)
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
