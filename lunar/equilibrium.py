"""Periodic steady-state (equilibrium) driver for the 1-D thermal solver.

In plain English (the "anchor point method")
--------------------------------------------
There is a practical problem. The deep Moon soil warms up so slowly
that if you just press "play" on the simulator and wait, it would take
the equivalent of ~1000 lunar days for the deep temperature to settle.
That is far too slow to run thousands of times. Worse, if you stop
early, the deep answer still secretly depends on whatever temperature
you *guessed* at the start -- a hidden cheat that would invalidate the
science.

This module is the clever shortcut that fixes both problems. The key
realisation: the soil has two very different "clocks."

  * The shallow skin (top ~half metre) reacts FAST -- it settles into
    its repeating day/night rhythm within a handful of lunar days.
  * The deep column reacts SLOWLY, but in steady state it must obey one
    simple rule: the same steady trickle of interior heat (Q_b) passes
    through every layer. That rule alone fixes the entire deep
    temperature shape -- no waiting required.

So instead of waiting, we alternate two cheap steps:
  1. Run the full simulator for just a few lunar days to settle the
     fast skin.
  2. Read the temperature at one reliable "anchor" depth just below the
     skin, then *calculate* the rest of the deep profile straight from
     the steady-heat-flow rule above.
Repeat a few times and it locks onto the true answer. Crucially, the
final result no longer depends on the starting guess (we verify this:
starting from 240 K or 260 K lands within 0.03 K of the same answer).
This is what the paper calls the anchor-point / flux-anchored method,
and it is the fix for audit flag F1.

Why this module exists
----------------------
A flux-bottom-boundary column relaxes to its periodic steady state on the
diffusive timescale of the *whole* column: for the 5-m production grid
(kappa ~ 1e-8 m^2 s^-1 at depth) that is of order 10^3 lunations. A
fixed-length spin-up of a few tens of lunations therefore retains memory
of the initial condition at sensor depths (0.8--2.4 m), and any anchor
constant used to build the initial profile acts as a hidden free
parameter of the retrieval (audit flag F1, docs/FLAG_REPORT.md).

Method: flux-anchored outer iteration
-------------------------------------
The true periodic equilibrium is characterised by two properties:

1. the diurnal skin (top ~3 skin depths) is periodic under the surface
   radiation balance, and
2. the cycle-mean conductive flux equals Q_b at every depth, so the
   cycle-mean profile below the skin satisfies the ODE

       d<T>/dz = Q_b / K(<T>, z).                                  (*)

The skin equilibrates in a few lunations (tau(z0) ~ z0^2 / kappa, about
10 lunations at the default z0 = 0.55 m); only the deep column is slow.
The anchor must sit below the diurnal *rectification* zone: where the
diurnal amplitude is still ~K-level, the cycle-mean flux contains an
eddy-correlation term <K' dT'/dz> that the mean-field ODE (*) omits.
At 0.55 m the amplitude is ~0.15 K and that term is < 1 % of Q_b
(validated by the 120-lunation drift test below). We exploit this
split:

  repeat:
    (i)  run ``n_inner`` lunations of the full nonlinear solver from the
         current profile -- this converges the skin against the current
         deep column;
    (ii) read the cycle-mean anchor temperature <T>(z0) just below the
         skin and *reconstruct* the entire sub-skin profile exactly from
         the steady-state mean-flux ODE (*);
  until the anchor moves by less than ``anchor_tol_K`` between outer
  iterations.

The fixed point of this map is the unique periodic equilibrium: the skin
is periodic by construction of step (i), and the deep column satisfies
mean-flux closure by construction of step (ii). Because the skin-mean
temperature is dominated by the surface radiation balance (Q_b is ~1e-4
of the diurnal flux scale), the map is strongly contractive and
converges in 3-5 outer iterations -- comparable in cost to the previous
30-lunation spin-up, but with no dependence on the initial guess.

Validation (see tests/test_equilibrium.py and the audit notebook):
initial guesses 240 K and 260 K converge to sensor-depth mean
temperatures agreeing to < 0.03 K, and the cycle-mean flux closes on
Q_b across the sensor window (>= 0.8 m, i.e. below the diurnal skin where
the mean-flux relation applies) to < 1 % at A15 and < 3 % at A17 -- A17
runs warmer/thicker-skinned (higher K_d, lower Q_b), so a little of the
n_inner=12 under-convergence reaches its shallowest sensor.

A note on what "closure" means here
-----------------------------------
The closure is certified *below the diurnal skin* -- the depth range
where the mean-flux relation d<T>/dz = (Q_b - u_rect)/K is physically
valid and where every Apollo sensor sits (>= 0.8 m). Inside the skin
(roughly the top ~0.6 m) the cycle-mean flux is NOT expected to equal
Q_b -- the surface radiates and the diurnal rectification term is large
-- so a closure number measured from the shallow anchor (0.55 m) reads a
few percent and is misleading. ``EquilibriumResult`` reports both: the
science-relevant ``flux_closure`` (below the skin) and the raw
``flux_closure_anchor`` (from the anchor) for full transparency.

Residual convergence systematic: the production setting ``n_inner = 12``
closes the sensor-window flux to < 1 % (A15) / < 3 % (A17) but leaves the
absolute skin-mean temperature ~0.1 K low (the shallow column is still
settling), which biases K_d* by ~0.09 mW/m/K. This is within the
+/-0.15 mW/m/K solver systematic already carried in the error budget
(Table: error budget) and an order of magnitude below the bootstrap
1-sigma uncertainty; raising ``n_inner`` to ~48 removes it at ~3x
runtime.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .grid import DepthGrid
from .solver import PixelInputs, PixelOutputs, solve_pixel


@dataclass
class EquilibriumResult:
    """Converged periodic state plus convergence diagnostics."""

    out: PixelOutputs          # final inner run (periodic cycle)
    T_mean: np.ndarray         # cycle-mean temperature profile [K]
    n_outer: int               # outer iterations used
    anchor_K: float            # final anchor temperature <T>(z0) [K]
    anchor_drift_K: float      # last inter-iteration anchor change [K]
    flux_closure: float        # max |<q>(z)-Q_b|/Q_b below the diurnal skin
                               #   (the validity domain of the mean-flux ODE;
                               #    this is the science-relevant certification)
    converged: bool
    flux_closure_anchor: float = float("nan")  # same metric from the anchor
                               #   depth, i.e. INCLUDING the diurnal
                               #   rectification skin -- reported for
                               #   transparency only; it is dominated by the
                               #   skin cells where the mean-flux ODE does not
                               #   apply, so it overstates the true closure.
    z_closure: float = float("nan")  # depth [m] below which flux_closure is
                               #   evaluated (the diurnal skin base)


def _rectified_flux(T_cycle: np.ndarray, z: np.ndarray, K_func) -> np.ndarray:
    """Cycle-mean eddy (rectified) conductive flux profile [W m^-2].

    u_rect(z) = <K(T) dT/dz> - K(<T>) d<T>/dz, computed exactly from the
    periodic cycle ``T_cycle`` (shape (N_z, N_t)). In the true steady
    state the *total* mean flux <K dT/dz> equals Q_b at every depth, so
    the mean-field reconstruction must integrate
    d<T>/dz = (Q_b - u_rect) / K(<T>). u_rect decays with the square of
    the diurnal amplitude and is negligible below ~1 m, but at the
    anchor depth it can reach a few percent of Q_b.
    """
    n_t = T_cycle.shape[1]
    Z = np.repeat(z[:, None], n_t, axis=1)
    K_t = np.asarray(K_func(T_cycle, Z), dtype=float)
    dTdz_t = np.gradient(T_cycle, z, axis=0)
    total = (K_t * dTdz_t).mean(axis=1)
    T_mean = T_cycle.mean(axis=1)
    meanfield = np.asarray(K_func(T_mean, z), dtype=float) * np.gradient(T_mean, z)
    return total - meanfield


def _reconstruct_subskin(T_mean: np.ndarray, z: np.ndarray, i0: int,
                         Q_b: float, K_func,
                         u_rect: np.ndarray | None = None) -> np.ndarray:
    """Integrate d<T>/dz = (Q_b - u_rect) / K(<T>, z) down from ``i0``.

    Midpoint (RK2) integration; K varies slowly cell-to-cell so this is
    accurate to << 1 mK per cell at the production grid resolution.
    """
    T_new = T_mean.copy()
    for i in range(i0, z.size - 1):
        dz = z[i + 1] - z[i]
        q_i = Q_b - (0.5 * (u_rect[i] + u_rect[i + 1])
                     if u_rect is not None else 0.0)
        K_i = float(np.asarray(K_func(np.array([T_new[i]]),
                                      np.array([z[i]])))[0])
        T_half = T_new[i] + 0.5 * q_i / K_i * dz
        z_half = 0.5 * (z[i] + z[i + 1])
        K_h = float(np.asarray(K_func(np.array([T_half]),
                                      np.array([z_half])))[0])
        T_new[i + 1] = T_new[i] + q_i / K_h * dz
    return T_new


def _diurnal_skin_index(T_cycle: np.ndarray, z: np.ndarray,
                        amp_floor_K: float, i_min: int) -> int:
    """Index of the diurnal skin base: shallowest depth at or below ``i_min``
    where the peak-to-peak diurnal amplitude has decayed below
    ``amp_floor_K``.

    The mean-flux steady-state relation d<T>/dz = (Q_b - u_rect)/K is only
    valid once the diurnal oscillation is negligible; above this depth the
    cycle-mean flux is not expected to equal Q_b (the surface radiates), so
    closure must be certified *below* the skin. Tying the depth to the
    resolved diurnal amplitude (rather than a hard-coded number) makes the
    diagnostic adapt automatically to the thermal skin depth, which grows
    with K.
    """
    amp = T_cycle.max(axis=1) - T_cycle.min(axis=1)
    below = np.where(amp[i_min:] < amp_floor_K)[0]
    if below.size == 0:
        return min(i_min, z.size - 1)
    return int(i_min + below[0])


def _mean_flux_closure(T_mean: np.ndarray, z: np.ndarray, i0: int,
                       Q_b: float, K_func,
                       u_rect: np.ndarray | None = None) -> float:
    """Max relative deviation of the total mean flux from Q_b below i0.

    The total cycle-mean flux is the mean-field part K(<T>) d<T>/dz plus
    the rectified eddy part u_rect; in the true steady state their sum
    equals Q_b at every depth.
    """
    K = np.asarray(K_func(T_mean, z), dtype=float)
    q = K * np.gradient(T_mean, z)
    if u_rect is not None:
        q = q + u_rect
    rel = np.abs(q[i0:] - Q_b) / Q_b
    return float(np.max(rel))


def solve_periodic_equilibrium(
    grid: DepthGrid,
    t: np.ndarray,
    insolation: np.ndarray,
    albedo: float,
    emissivity: float,
    Q_b: float,
    K_func,
    cp_func=None,
    rho_func=None,
    T_guess: float = 250.0,
    z_anchor: float = 0.55,
    n_inner: int = 12,
    max_outer: int = 20,
    anchor_tol_K: float = 0.005,
    z_closure_min: float | None = None,
    amp_floor_K: float = 0.05,
) -> EquilibriumResult:
    """Compute the periodic steady state, independent of ``T_guess``.

    Parameters mirror :class:`lunar.solver.PixelInputs` (radiative BC);
    ``t``/``insolation`` must span exactly one forcing cycle. ``T_guess``
    only seeds the first iterate and is eliminated by the outer
    iteration -- see the module docstring.

    Convergence diagnostics
    -----------------------
    ``flux_closure`` is the max relative deviation of the cycle-mean
    conductive flux from ``Q_b``, evaluated *below the diurnal skin* --
    the depth range where the mean-flux relation d<T>/dz = (Q_b-u_rect)/K
    actually holds, and where every Apollo sensor (>= 0.8 m) lies. The
    skin base is found from the resolved diurnal amplitude (``amp_floor_K``)
    or, if ``z_closure_min`` is given (e.g. the shallowest sensor depth),
    from that depth. The raw closure measured from the anchor -- which
    includes the rectification skin and therefore overstates the error --
    is returned separately as ``flux_closure_anchor`` for transparency.

    Note on ``n_inner``: the production value (12) closes the mean flux to
    < 1 % (A15) / < 3 % (A17) across the sensor window but leaves a residual
    ~0.1 K bias in the absolute skin-mean temperature (the skin is still
    settling), worth ~0.09 mW/m/K in K_d*. That is within the
    +/-0.15 mW/m/K solver systematic carried in the error budget and an
    order of magnitude below the bootstrap sigma; raising ``n_inner`` to
    ~48 removes it at ~3x cost.
    """
    z = grid.z_mid
    i0 = int(np.argmin(np.abs(z - z_anchor)))

    K0 = np.asarray(K_func(np.full_like(z, T_guess), z), dtype=float)
    T_init = T_guess + Q_b * np.cumsum(grid.dz / K0)

    # Two-stage anchor schedule. Stage 1 anchors high in the column
    # (fast relaxation; tau ~ 2-3 lunations) to close the bulk of the
    # initial-guess error cheaply; its small rectification bias is then
    # removed by stage 2, which anchors below the rectification zone
    # and iterates to ``anchor_tol_K``. Convergence is certified by the
    # returned drift/closure diagnostics, not assumed.
    stages = (
        dict(z0=0.25, n_in=4, max_it=4, tol=0.10),
        dict(z0=z_anchor, n_in=n_inner, max_it=max_outer, tol=anchor_tol_K),
    )

    drift = np.inf
    out = None
    T_mean = None
    n_outer = 0
    for stage in stages:
        i_s = int(np.argmin(np.abs(z - stage["z0"])))
        anchor_prev = np.inf
        for it in range(1, stage["max_it"] + 1):
            n_outer += 1
            out = solve_pixel(PixelInputs(
                grid=grid, t=t, bc_mode="radiative",
                insolation=insolation, albedo=albedo, emissivity=emissivity,
                Q_b=Q_b, T_init=T_init,
                # tol 0 forces all inner cycles (no premature exit)
                n_lunations_spinup=stage["n_in"], spinup_tol_K=0.0,
                K_func=K_func, cp_func=cp_func, rho_func=rho_func,
            ))
            T_mean = out.T.mean(axis=1)
            anchor = float(T_mean[i_s])
            drift = abs(anchor - anchor_prev)
            u_rect = _rectified_flux(out.T, z, K_func)
            T_recon = _reconstruct_subskin(T_mean, z, i_s, Q_b, K_func,
                                           u_rect=u_rect)
            if drift < stage["tol"] and it >= 2:
                break
            anchor_prev = anchor
            T_init = T_recon

    u_final = _rectified_flux(out.T, z, K_func)
    # Closure from the anchor (includes the rectification skin -- transparency)
    closure_anchor = _mean_flux_closure(T_mean, z, i0, Q_b, K_func,
                                        u_rect=u_final)
    # Science-relevant closure: below the diurnal skin, where the mean-flux
    # ODE is valid and where all sensors lie. Honour an explicit retrieval
    # window (z_closure_min) if given, else locate the skin base from the
    # resolved diurnal amplitude.
    if z_closure_min is not None:
        i_clo = int(np.argmin(np.abs(z - z_closure_min)))
    else:
        i_clo = _diurnal_skin_index(out.T, z, amp_floor_K, i0)
    closure = _mean_flux_closure(T_mean, z, i_clo, Q_b, K_func,
                                 u_rect=u_final)
    return EquilibriumResult(
        out=out, T_mean=T_mean, n_outer=n_outer,
        anchor_K=float(T_mean[i0]), anchor_drift_K=float(drift),
        flux_closure=closure,
        converged=bool(drift < anchor_tol_K),
        flux_closure_anchor=closure_anchor,
        z_closure=float(z[i_clo]),
    )
