"""Periodic steady-state (equilibrium) driver for the 1-D thermal solver.

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
Q_b to < 2 % at all depths below 0.3 m.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .constants import LUNATION_SECONDS
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
    flux_closure: float        # max |<q>(z) - Q_b| / Q_b below the anchor
    converged: bool
    # Per-outer-cycle convergence trace: tuples (stage_z0, iter, anchor_K,
    # drift_K). Diagnostic only; lets callers visualise the contraction.
    history: tuple = ()


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
    if not 0 <= i0 < z.size:
        raise ValueError(f"anchor index i0={i0} is outside the depth grid")
    if not np.all(np.diff(z) > 0):
        raise ValueError("depth grid z must be strictly increasing")
    if not np.isfinite(Q_b):
        raise ValueError("Q_b must be finite")
    T_new = T_mean.copy()
    for i in range(i0, z.size - 1):
        dz = z[i + 1] - z[i]
        q_i = Q_b - (0.5 * (u_rect[i] + u_rect[i + 1])
                     if u_rect is not None else 0.0)
        K_i = float(np.asarray(K_func(np.array([T_new[i]]),
                                      np.array([z[i]])))[0])
        if not np.isfinite(K_i) or K_i <= 0.0:
            raise ValueError(
                f"K_func returned invalid conductivity {K_i!r} "
                f"at z={z[i]:.3g} m during sub-skin reconstruction"
            )
        T_half = T_new[i] + 0.5 * q_i / K_i * dz
        z_half = 0.5 * (z[i] + z[i + 1])
        K_h = float(np.asarray(K_func(np.array([T_half]),
                                      np.array([z_half])))[0])
        if not np.isfinite(K_h) or K_h <= 0.0:
            raise ValueError(
                f"K_func returned invalid midpoint conductivity {K_h!r} "
                f"at z={z_half:.3g} m during sub-skin reconstruction"
            )
        T_new[i + 1] = T_new[i] + q_i / K_h * dz
    return T_new


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
    if Q_b == 0.0:
        raise ValueError("Q_b must be non-zero for relative flux-closure certification")
    rel = np.abs(q[i0:] - Q_b) / Q_b
    return float(np.max(rel))


def _truncate_grid(grid: DepthGrid, z_cut: float) -> tuple[DepthGrid, int]:
    """Shallow sub-grid spanning ``[0, z_cut]`` for the Step A spin-up.

    Returns the sub-grid (the shallowest cells whose lower face reaches
    ``z_cut``) and its cell count ``n`` so the caller can slice full-grid
    arrays as ``arr[:n]``. Step A is time-stepped on this sub-column with the
    geothermal Q_b flux BC applied at its base; the deep column below ``z_cut``
    is reconstructed by Step B's closure ODE and never time-stepped. A
    ``z_cut >= z_max`` returns the full grid (recovering the old behaviour).
    """
    n = int(np.searchsorted(grid.z_face, z_cut, side="left"))
    n = int(np.clip(n, 2, grid.n_layers))
    return (
        DepthGrid(
            z_face=grid.z_face[: n + 1].copy(),
            z_mid=grid.z_mid[:n].copy(),
            dz=grid.dz[:n].copy(),
        ),
        n,
    )


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
    n_inner: int | None = None,
    max_outer: int = 20,
    anchor_tol_K: float = 0.005,
    step_a_depth_m: float | None = None,
    hayne_params: tuple | None = None,
) -> EquilibriumResult:
    """Compute the periodic steady state, independent of ``T_guess``.

    Parameters mirror :class:`lunar.solver.PixelInputs` (radiative BC);
    ``t``/``insolation`` must span exactly one forcing cycle. ``T_guess``
    only seeds the first iterate and is eliminated by the outer
    iteration -- see the module docstring.

    ``n_inner`` defaults to the PRODUCTION converged value
    (``config.EQ_N_INNER``): the old hardcoded default of 12 was the
    under-resolved setting that biased K_d*(A17) ~0.4 mW high, and callers
    kept inheriting it silently. Pass a smaller value explicitly only for
    speed-insensitive mechanics tests.
    """
    if n_inner is None:
        from .config import EQ_N_INNER
        n_inner = EQ_N_INNER
    if z_anchor > grid.z_mid[-1]:
        raise ValueError(
            f"z_anchor={z_anchor} m lies below the grid bottom "
            f"({grid.z_mid[-1]:.3g} m cell center)"
        )
    z = grid.z_mid
    i0 = int(np.argmin(np.abs(z - z_anchor)))

    # --- Step A domain truncation (the n_inner convergence fix, 2026-06-30) ---
    # Step A's only job is to settle the diurnal *skin*; the deep column below
    # the anchor is reconstructed by Step B's closure ODE. The original code
    # time-stepped the WHOLE 5 m column in Step A, so the slow ~10^3-lunation
    # deep relaxation leaked back into the anchor and the retrieved K_d* drifted
    # with n_inner (biased high at the old n_inner=12). We therefore run Step A
    # on a sub-grid [0, cap] a short margin below the anchor, applying the Q_b
    # flux BC at its base (at steady state the flux there IS Q_b). Everything
    # below cap is reconstructed, never time-stepped, so a small n_inner suffices
    # and each solve is cheap. cap >= z_max recovers the old full-column path.
    cap = step_a_depth_m if step_a_depth_m is not None else z_anchor + 0.15
    sub_grid, n_cut = _truncate_grid(grid, cap)
    if i0 >= n_cut:
        raise ValueError(
            f"anchor index {i0} (z={z[i0]:.3g} m) is at/below the Step A sub-grid "
            f"base ({n_cut} cells to {sub_grid.z_face[-1]:.3g} m); "
            f"increase step_a_depth_m"
        )

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
    T_recon = T_init
    n_outer = 0
    history: list = []
    for stage in stages:
        i_s = int(np.argmin(np.abs(z - stage["z0"])))
        anchor_prev = np.inf
        for it in range(1, stage["max_it"] + 1):
            n_outer += 1
            # Step A: time-step ONLY the sub-skin column [0, cap].
            out_sub = solve_pixel(PixelInputs(
                grid=sub_grid, t=t, bc_mode="radiative",
                insolation=insolation, albedo=albedo, emissivity=emissivity,
                Q_b=Q_b, T_init=T_init[:n_cut],
                # tol 0 forces all inner cycles (no premature exit)
                n_lunations_spinup=stage["n_in"], spinup_tol_K=0.0,
                K_func=K_func, cp_func=cp_func, rho_func=rho_func,
                # compiled march when the caller declares standard Hayne
                # properties (see PixelInputs.hayne_params)
                hayne_params=hayne_params,
            ))
            T_mean_sub = out_sub.T.mean(axis=1)
            anchor = float(T_mean_sub[i_s])
            drift = abs(anchor - anchor_prev)
            history.append((float(stage["z0"]), it, anchor, float(drift)))
            # Assemble the full-grid cycle-mean: measured skin on [0, cap],
            # closure reconstruction (Step B) below the anchor.
            T_mean_full = np.empty(z.size)
            T_mean_full[:n_cut] = T_mean_sub
            T_mean_full[n_cut:] = T_mean_sub[-1]   # placeholder; overwritten below
            u_rect = np.zeros(z.size)
            u_rect[:n_cut] = _rectified_flux(out_sub.T, sub_grid.z_mid, K_func)
            T_recon = _reconstruct_subskin(T_mean_full, z, i_s, Q_b, K_func,
                                           u_rect=u_rect)
            if drift < stage["tol"] and it >= 2:
                break
            anchor_prev = anchor
            T_init = T_recon

    # One short full-column solve from the converged profile, solely to expose
    # the full periodic cycle (out.T) for diagnostics/figures and a genuine
    # flux-closure cross-check. The deep column is already at steady state, so
    # these few lunations do not move it; T_mean is the clean reconstruction.
    out = solve_pixel(PixelInputs(
        grid=grid, t=t, bc_mode="radiative",
        insolation=insolation, albedo=albedo, emissivity=emissivity,
        Q_b=Q_b, T_init=T_recon, n_lunations_spinup=3, spinup_tol_K=0.0,
        K_func=K_func, cp_func=cp_func, rho_func=rho_func,
        hayne_params=hayne_params,
    ))
    closure = _mean_flux_closure(T_recon, z, i0, Q_b, K_func,
                                 u_rect=_rectified_flux(out.T, z, K_func))
    return EquilibriumResult(
        out=out, T_mean=T_recon, n_outer=n_outer,
        anchor_K=float(T_recon[i0]), anchor_drift_K=float(drift),
        flux_closure=closure,
        converged=bool(drift < anchor_tol_K),
        history=tuple(history),
    )


# Named moments of the lunar day, as fractions of one lunation past the
# insolation peak. The standard pipeline forcing is
# ``insol = S0 cos(lat) max(0, cos(2 pi t / T_LUNAR))``, so t = 0 is local
# lunar NOON, the sun sets a quarter-lunation later, and so on.
PHASES = {"noon": 0.0, "sunset": 0.25, "midnight": 0.5, "sunrise": 0.75}


def profile_at_time(eq: EquilibriumResult,
                    time_hours: float | str) -> np.ndarray:
    """Instantaneous temperature profile T(z) at any moment of the cycle.

    The converged steady state is *periodic*, and ``solve_periodic_equilibrium``
    stores the full final lunar cycle in ``eq.out`` (``T`` of shape
    ``(N_z, N_t)`` sampled at times ``t``). So "the profile at a specific
    time" needs no re-solve: this helper linearly interpolates the stored
    cycle -- periodically, so any time maps onto its phase of the lunar
    day -- and returns the instantaneous column ``T(z)`` on ``eq.out.z``.

    Parameters
    ----------
    eq : EquilibriumResult
        A converged result from ``solve_periodic_equilibrium``.
    time_hours : float or str
        Hours past local lunar noon (t = 0 of the standard forcing).
        Values wrap: negative hours and times beyond one lunation
        (~708.7 h) are folded back into the cycle, so "354 h after noon"
        and "midnight" agree. Alternatively a named phase, one of
        ``"noon"``, ``"sunset"``, ``"midnight"``, ``"sunrise"``.

    Returns
    -------
    numpy.ndarray, shape (N_z,)
        The temperature profile at that moment [K]. Only the diurnal skin
        moves with the chosen time; below ~0.5 m the profile is the
        cycle-mean to within ~0.1 K (that is the anchor-method fact).
    """
    if isinstance(time_hours, str):
        try:
            frac = PHASES[time_hours.lower()]
        except KeyError:
            raise ValueError(
                f"unknown phase {time_hours!r}; use one of {sorted(PHASES)} "
                "or a number of hours past lunar noon") from None
        t_req = frac * LUNATION_SECONDS
    else:
        t_req = float(time_hours) * 3600.0

    T, t = eq.out.T, np.asarray(eq.out.t, dtype=float)
    # Fold onto the stored cycle's phase (the forcing period is one lunation).
    ts = t[0] + ((t_req - t[0]) % LUNATION_SECONDS)

    # Bracketing samples, wrapping the last interval back onto the first.
    j = int(np.searchsorted(t, ts, side="right")) - 1
    if j >= t.size - 1:                       # ts in [t[-1], t[0] + period)
        t_lo, t_hi = t[-1], t[0] + LUNATION_SECONDS
        T_lo, T_hi = T[:, -1], T[:, 0]
    else:
        t_lo, t_hi = t[j], t[j + 1]
        T_lo, T_hi = T[:, j], T[:, j + 1]
    w = 0.0 if t_hi == t_lo else (ts - t_lo) / (t_hi - t_lo)
    return (1.0 - w) * T_lo + w * T_hi


def profile_at_local_time(eq: EquilibriumResult,
                          local_time: float | str) -> np.ndarray:
    """Instantaneous temperature profile T(z) at a 24-hour LOCAL LUNAR TIME.

    This is the friendlier front end of ``profile_at_time``: instead of
    "hours past noon", read the clock the way you would on Earth --
    ``12:00`` = local noon (hottest surface), ``00:00`` = local midnight
    (coldest surface), ``06:00`` = sunrise, ``18:00`` = sunset -- exactly a
    sundial reading, just stretched over one lunation (~29.5 Earth days)
    instead of 24 Earth hours.

    Parameters
    ----------
    eq : EquilibriumResult
        A converged result from ``solve_periodic_equilibrium``.
    local_time : float or str
        Clock reading in [0, 24) hours, e.g. ``14.5`` or ``"14:30"``.
        Values outside [0, 24) wrap (``25:00`` reads as ``01:00``).

    Returns
    -------
    numpy.ndarray, shape (N_z,)
        The temperature profile at that local time [K], on ``eq.out.z``.

    Examples
    --------
    >>> profile_at_local_time(eq, "14:30")   # mid-afternoon
    >>> profile_at_local_time(eq, 3.0)       # 03:00, deep lunar night
    """
    if isinstance(local_time, str):
        hh, _, mm = local_time.partition(":")
        local_time = float(hh) + (float(mm) / 60.0 if mm else 0.0)
    local_time = float(local_time) % 24.0
    # noon (12:00) is t=0 of the stored cycle; one lunation = 24 clock-hours
    lunation_hours = LUNATION_SECONDS / 3600.0
    hours_past_noon = (local_time - 12.0) / 24.0 * lunation_hours
    return profile_at_time(eq, hours_past_noon)
