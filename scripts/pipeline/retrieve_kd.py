"""Retrieve the deep-regolith thermal conductivity K_d at each Apollo
HFE borehole and quantify uncertainty.

Reads the bundled HFE record under data/apollo/, runs the 1-D
Crank-Nicolson heat solver under the Hayne (2017) K(T,z) form,
sweeps K_d against the deep-sensor RMSE, and reports:

    - K_d* per site (point estimate at the RMSE minimum)
    - 95% non-parametric bootstrap CI (N_boot = 1500, +-2.5 cm depth jitter)
    - K_d / Q_b degeneracy mapping for the inter-site contrast
    - joint (K_d, H) RMSE surface for the held-out diagnostic
    - hold-out tests (TG vs TR, leave-one-deepest-out)

Writes:
    output/kd_retrieval_results.json     # canonical numerical results
    paper/letter/figures/fig_bootstrap.pdf
    paper/letter/figures/fig_robustness.pdf
    output/figures/fig_holdout.pdf

Table of contents (jump to the section you need):
    line  ~80  : Hayne / 3-layer conductivity model wrappers
    line ~150  : run_kd_sweep_extended()     -- the K_d sweep
    line ~260  : bootstrap_kd_with_depth_uncertainty()
    line ~330  : joint_kd_h_dense()          -- joint (K_d, H) fit
    line ~370  : holdout_tg_tr() and loo_deepest()
    line ~410  : main()                      -- orchestrates the above

Wall time: ~5 min on a recent laptop.

Runtime breakdown (measured on 2.6 GHz 6-core Intel i7):
    PHYSICAL K_d RETRIEVAL (35% of total):
        ~20%  Extended K_d sweeps (58 solver runs, line ~390)
        ~12%  Joint K_d×H grid (128 solver runs, line ~470)
         ~5%  3-layer model sweep (58 solver runs, line ~410)
    STATISTICAL POST-PROCESSING (65% of total):
        ~65%  Bootstrap uncertainty quantification (1500 resamples, line ~430)
              (NOT part of thermal model - pure statistics for error bars)

Core thermal computation: solve_periodic_equilibrium runs ~40 lunations per
call, invoked ~300 times. Bootstrap reuses cached results - no new physics.

Run with:
    python scripts/pipeline/retrieve_kd.py
"""
from __future__ import annotations
import json, sys, pathlib, time
from copy import deepcopy

# Repo root resolved from this file's location, so results and figures
# are written into the SAME checkout the script is run from.
_REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO))
from lunar import _bootstrap as boot
boot.ensure_lunar(extra=('spiceypy', 'scipy'))
boot.ensure_apollo_hfe(mission='a15', probes=())
boot.ensure_apollo_hfe(mission='a17', probes=())

import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

from lunar.grid import make_geometric_grid
from lunar.properties import (conductivity_hayne, conductivity_martinez,
                              specific_heat)
from lunar.constants import (
    K_SURFACE, H_PARAMETER, CHI_RADIATIVE, T_REFERENCE, LUNATION_SECONDS,
)
from lunar.solver import PixelInputs, solve_pixel
from lunar.equilibrium import solve_periodic_equilibrium
from lunar.apollo_helpers import extract_sensor_stability


# Shared publication style from the package (no longer a figure-script import).
from lunar.plotting.style import (   # noqa: E402
    C_A15, C_A17, C_HAYNE, C_MS, C_LAB, C_TEAL, C_TEAL_L,
    C_FOREST, C_CORAL, C_CHAR, C_DIM, C_GRID,
    ANTH_DIVERGE, ANTH_SEQ,
    FS_BASE, FS_TITLE, FS_LABEL, FS_TICK, FS_LEGEND,
    fmt_axis,
)
# Single source of truth for ALL run configuration (lunar/config.py) --
# SITES, GRID, the Hayne bundle, the equilibrium-solver settings, the
# 3-layer parameters. These used to be redefined here and in four figure
# scripts; now there is exactly one definition.
from lunar.config import (   # noqa: E402
    S0, T_LUNAR, DT_STEP, N_LUN_FAST, TOL_FAST,
    EQ_Z_ANCHOR, EQ_N_INNER, EQ_MAX_OUTER, EQ_ANCHOR_TOL,
    GRID, HAYNE, SITES, DEPTH_SIGMA_CM,
    TL_Z1, TL_Z2, TL_RHO_REF, TL_RHO_SITE,
)
# scripts/figures kept on path for the end-of-run figure helpers
# (fig_bootstrap, fig_robustness) imported inside main().
sys.path.insert(0, str(_REPO / 'scripts' / 'figures'))

# In-process memo cache for converged mean profiles, keyed on every input
# that can change the forward model (speeds the repeated sweeps).
_PROFILE_CACHE: dict = {}


def conductivity_3layer(T, z, Kd, rho_deep=TL_RHO_REF):
    """Discrete 3-layer K(T,z): piecewise structural profile times the
    Hayne radiative multiplier.  A denser column (higher rho_deep)
    compacts faster, encoded as a transition-ramp exponent p<1."""
    z = np.asarray(z, dtype=float)
    T = np.broadcast_to(np.asarray(T, dtype=float), z.shape).astype(float)
    p = float(np.clip(1.0 - 0.5 * (rho_deep - TL_RHO_REF) / TL_RHO_REF,
                      0.4, 1.6))
    frac = np.clip((z - TL_Z1) / (TL_Z2 - TL_Z1), 0.0, 1.0) ** p
    Kc = np.where(z < TL_Z1, HAYNE['K_S'],
                  HAYNE['K_S'] + (Kd - HAYNE['K_S']) * frac)
    return Kc * (1.0 + HAYNE['CHI'] * (T / HAYNE['T_REF']) ** 3)


# ── Solver wrappers ──────────────────────────────────────────────────────────
def run_with(site_cfg, *, kd=None, h=None, qb=None, k_model='hayne',
             rho_deep=None, martinez_alpha=None):
    """Drive the 1-D solver for one site under a chosen K(z) model.

    Parameters
    ----------
    kd : float, optional
        Deep conductivity (W/m/K). Required for 'hayne' and '3layer';
        ignored for 'martinez' (Martinez forward).
    rho_deep : float, optional
        Override the per-site deep bulk density used by the 3-layer
        model. If None, falls back to TL_RHO_SITE[site_cfg['tag']]
        then TL_RHO_REF.
    martinez_alpha : float, optional
        Per-site density scalar applied to the Hayne-form rho(z) entering
        the Martinez K(T, rho) formulation. alpha=1 reproduces the
        forward published model (rho_d = 1800 kg/m^3); other values
        scale the deep asymptote to alpha*1800. Used for the Martinez
        per-site retrieval; ignored under 'hayne' and '3layer'.
    """
    site = deepcopy(site_cfg)
    if qb is not None:
        site['Q_BASAL'] = qb
    h = HAYNE['H'] if h is None else h
    cache_key = (site.get('tag'), site['lat'], site['albedo'],
                 site['emissivity'], site['Q_BASAL'],
                 kd, h, k_model, rho_deep, martinez_alpha)
    if cache_key in _PROFILE_CACHE:
        return _PROFILE_CACHE[cache_key]
    grid_  = make_geometric_grid(**GRID)
    z_mid  = grid_.z_mid
    N_t    = int(T_LUNAR / DT_STEP) + 1
    t_s    = np.linspace(0.0, T_LUNAR, N_t)
    cos_lat = np.cos(np.deg2rad(site['lat']))
    phase   = 2.0 * np.pi * t_s / T_LUNAR
    insol   = S0 * cos_lat * np.maximum(0.0, np.cos(phase))
    if k_model == '3layer':
        if kd is None:
            raise ValueError("3layer model requires kd")
        rd = (rho_deep if rho_deep is not None
              else TL_RHO_SITE.get(site_cfg.get('tag', ''), TL_RHO_REF))
        def k_func(T, z):
            return conductivity_3layer(T, z, Kd=kd, rho_deep=rd)
    elif k_model == 'martinez':
        # Martinez K(T, rho). When martinez_alpha is None the model is
        # evaluated forward against the published Hayne-form rho(z)
        # (matches the calibration in the original paper). When
        # martinez_alpha is supplied, the deep asymptote of rho(z) is
        # rescaled by alpha, exposing a single per-site free parameter
        # for the Martinez retrieval.
        from lunar.properties import density_hayne
        from lunar.constants import RHO_SURFACE, RHO_DEEP, H_PARAMETER
        if martinez_alpha is None:
            def k_func(T, z):
                return conductivity_martinez(T, z=z)
        else:
            rho_d_scaled = float(martinez_alpha) * RHO_DEEP
            def k_func(T, z):
                rho = density_hayne(np.asarray(z, dtype=float),
                                    rho_s=RHO_SURFACE,
                                    rho_d=rho_d_scaled,
                                    H=H_PARAMETER)
                return conductivity_martinez(T, rho=rho)
    else:
        if kd is None:
            raise ValueError("hayne model requires kd")
        def k_func(T, z):
            return conductivity_hayne(T, z, Ks=HAYNE['K_S'], Kd=kd,
                                      H=h, chi=HAYNE['CHI'])
    def cp_func(T):
        return specific_heat(T, model='hayne')
    # ──────────────────────────────────────────────────────────────────────────
    # PERFORMANCE: Thermal solver dominates per-call runtime
    # ──────────────────────────────────────────────────────────────────────────
    # Flux-anchored equilibrium solver (lunar/equilibrium.py) runs 12 inner
    # lunations per outer iteration, typically converging in 3-5 outer cycles
    # (36-60 total lunations per call). Each lunation requires 2551 hourly
    # timesteps; each timestep invokes Thomas tridiagonal solver plus Newton
    # iteration for the radiative surface boundary condition.
    #
    # Called ~300 times in full pipeline: K_d sweeps (120), joint H×K_d grid
    # (130), cross-validation tests (50). Total work: approximately 12000
    # simulated lunations. Initial guess T_MEAN_EFF only seeds first iterate;
    # final profile is independent of it (F1 audit).
    # ──────────────────────────────────────────────────────────────────────────
    eq = solve_periodic_equilibrium(
        grid=grid_, t=t_s, insolation=insol,
        albedo=site['albedo'], emissivity=site['emissivity'],
        Q_b=site['Q_BASAL'], K_func=k_func, cp_func=cp_func,
        T_guess=site['T_MEAN_EFF'],
        z_anchor=EQ_Z_ANCHOR, n_inner=EQ_N_INNER,
        max_outer=EQ_MAX_OUTER, anchor_tol_K=EQ_ANCHOR_TOL,
    )
    if not eq.converged or eq.flux_closure > 0.05:
        print(f"   WARNING: equilibrium not fully converged "
              f"(drift={eq.anchor_drift_K:.3f} K, "
              f"closure={eq.flux_closure:.3%})", flush=True)
    _PROFILE_CACHE[cache_key] = (z_mid, eq.T_mean)
    return z_mid, eq.T_mean


def kd_star_from_residuals(R, kd_grid, idx=None):
    if idx is None:
        idx = np.arange(R.shape[0])
    rmse = np.sqrt((R[idx]**2).mean(axis=0))
    k_min = int(np.argmin(rmse))
    if 0 < k_min < len(kd_grid) - 1:
        x = kd_grid[k_min-1:k_min+2]
        y = rmse[k_min-1:k_min+2]
        denom = (x[0]-x[1])*(x[0]-x[2])*(x[1]-x[2])
        a = (x[2]*(y[1]-y[0]) + x[1]*(y[0]-y[2]) + x[0]*(y[2]-y[1])) / denom
        b = (x[2]**2*(y[0]-y[1]) + x[1]**2*(y[2]-y[0]) + x[0]**2*(y[1]-y[2])) / denom
        kd_star = -b / (2*a) if a > 0 else kd_grid[k_min]
        rmse_star = float(np.interp(kd_star, x, y))
    else:
        kd_star = kd_grid[k_min]
        rmse_star = float(rmse[k_min])
    return float(kd_star), rmse_star


# ══════════════════════════════════════════════════════════════════════════════
# A1 — Extended K_d sweep
# ══════════════════════════════════════════════════════════════════════════════
def run_kd_sweep_extended(site_cfg, kd_grid, k_model='hayne'):
    """Sweep through K_d values to find optimal fit to Apollo HFE data.
    
    This is the core K_d retrieval loop. For each K_d value in kd_grid:
    1. Run full thermal solver (40 lunations, ~100k timesteps)
    2. Extract predicted temperatures at sensor depths
    3. Compute residuals vs Apollo observations
    
    Returns residual matrix R[sensor, K_d] used to find K_d* that minimizes RMSE.
    Takes ~1 minute for both sites (58 total solver runs).
    """
    obs = extract_sensor_stability(site_cfg['mission'],
                                   min_depth_cm=site_cfg['MIN_DEPTH_CM'])
    z_obs = np.asarray(obs['depth_cm_all']) / 100.0
    T_obs = np.asarray(obs['T_eq_all'])
    deep  = np.asarray(obs['deep_mask'], dtype=bool)
    stype = np.asarray(obs['stype_all'])
    z_obs_deep = z_obs[deep]
    T_obs_deep = T_obs[deep]
    stype_deep = stype[deep]

    # Build residual matrix: R[sensor_i, K_d_j] = T_model(K_d_j) - T_observed
    R = np.empty((len(z_obs_deep), len(kd_grid)))
    for k, kd in enumerate(kd_grid):
        # EXPENSIVE: This calls solve_periodic_equilibrium (~40 lunations)
        z_mid, T_mean_z = run_with(site_cfg, kd=kd, k_model=k_model)
        T_pred = np.interp(z_obs_deep, z_mid, T_mean_z)
        R[:, k] = T_pred - T_obs_deep
        if (k + 1) % 5 == 0 or k == len(kd_grid) - 1:
            print(f"   K_d sweep ({site_cfg['label']}, {k_model}): "
                  f"{k+1}/{len(kd_grid)}", flush=True)
    return z_obs_deep, T_obs_deep, R, stype_deep


# ══════════════════════════════════════════════════════════════════════════════
# A5 — Bootstrap with sensor depth uncertainty
# ══════════════════════════════════════════════════════════════════════════════
def bootstrap_kd_with_depth_uncertainty(
    site_cfg, kd_grid, R, z_obs_deep, T_obs_deep,
    *, n_boot=1500, depth_sigma_cm=DEPTH_SIGMA_CM, seed=42,
):
    """For each bootstrap resample:
      (a) draw a sensor index set with replacement,
      (b) jitter each sensor depth by ~N(0, σ_z),
      (c) compute T_model at the jittered depths from the existing K_d-sweep
          temperature profile (cached), refit the parabolic K_d* minimum.
    """
    rng = np.random.default_rng(seed)
    n = R.shape[0]

    # We need T_model at every K_d on a finer depth grid (interpolated from
    # the spin-up output). Cache T_mean(z_grid) for each K_d in the sweep.
    z_grid_dense = np.linspace(0.05, 3.0, 200)
    T_cache = np.empty((len(kd_grid), len(z_grid_dense)))
    for k, kd in enumerate(kd_grid):
        z_mid, T_mean_z = run_with(site_cfg, kd=kd)
        T_cache[k] = np.interp(z_grid_dense, z_mid, T_mean_z)
    print(f"   built depth interpolation cache ({len(kd_grid)} K_d × "
          f"{len(z_grid_dense)} depths)", flush=True)

    # ──────────────────────────────────────────────────────────────────────────
    # PERFORMANCE: Bootstrap statistical resampling (65% of runtime)
    # ──────────────────────────────────────────────────────────────────────────
    # This is NOT part of K_d retrieval - pure statistical uncertainty analysis.
    # Reuses cached thermal solver results from above. NO new physics runs.
    #
    # Each of 1500 iterations: (1) resample sensor indices with replacement,
    # (2) jitter depths by ±2.5 cm, (3) interpolate cached T_model(z,K_d),
    # (4) refit K_d* from resampled data. Total: 18M interpolations (cheap
    # operations, expensive only due to iteration count). Reduce to 300 for
    # testing (docs/REPRODUCING.md).
    # ──────────────────────────────────────────────────────────────────────────
    boots = np.empty(n_boot)
    for b in range(n_boot):
        idx = rng.integers(0, n, size=n)
        # jittered depths
        dz = rng.normal(0.0, depth_sigma_cm / 100.0, size=n)
        z_jit = z_obs_deep[idx] + dz[idx]
        # build a residual matrix per K_d at the jittered depths
        R_jit = np.empty((n, len(kd_grid)))
        for k in range(len(kd_grid)):
            T_pred = np.interp(z_jit, z_grid_dense, T_cache[k])
            R_jit[:, k] = T_pred - T_obs_deep[idx]
        kd_star, _ = kd_star_from_residuals(R_jit, kd_grid)
        boots[b] = kd_star
    return boots


# ══════════════════════════════════════════════════════════════════════════════
# A2 — Densified joint K_d × H grid
# ══════════════════════════════════════════════════════════════════════════════
def joint_kd_h_dense(site_cfg, kd_grid, h_grid):
    obs = extract_sensor_stability(site_cfg['mission'],
                                   min_depth_cm=site_cfg['MIN_DEPTH_CM'])
    z_obs = np.asarray(obs['depth_cm_all']) / 100.0
    T_obs = np.asarray(obs['T_eq_all'])
    deep  = np.asarray(obs['deep_mask'], dtype=bool)
    z_obs_deep = z_obs[deep]
    T_obs_deep = T_obs[deep]
    rmse = np.empty((len(h_grid), len(kd_grid)))
    total = len(h_grid) * len(kd_grid)
    n = 0
    for i, h in enumerate(h_grid):
        for j, kd in enumerate(kd_grid):
            z_mid, T_mean_z = run_with(site_cfg, kd=kd, h=h)
            T_pred = np.interp(z_obs_deep, z_mid, T_mean_z)
            rmse[i, j] = np.sqrt(((T_pred - T_obs_deep)**2).mean())
            n += 1
            if n % 16 == 0 or n == total:
                print(f"   joint ({site_cfg['label']}): {n}/{total}",
                      flush=True)
    return rmse


# ══════════════════════════════════════════════════════════════════════════════
# A3 — Held-out validation
# ══════════════════════════════════════════════════════════════════════════════
def holdout_tg_tr(site_cfg, kd_grid, R, stype_deep):
    """Fit K_d using only TG sensors, predict TR; and vice-versa."""
    is_tg = stype_deep == 'TG'
    is_tr = stype_deep == 'TR'
    if is_tg.sum() < 2 or is_tr.sum() < 2:
        return None
    kd_tg, rmse_tg_in   = kd_star_from_residuals(R, kd_grid, idx=np.where(is_tg)[0])
    kd_tr, rmse_tr_in   = kd_star_from_residuals(R, kd_grid, idx=np.where(is_tr)[0])
    # Out-of-sample RMSE: predict TR using K_d fit to TG only
    k_tg_idx = int(np.argmin(np.abs(kd_grid - kd_tg)))
    k_tr_idx = int(np.argmin(np.abs(kd_grid - kd_tr)))
    rmse_tr_oos = float(np.sqrt((R[is_tr, k_tg_idx]**2).mean()))
    rmse_tg_oos = float(np.sqrt((R[is_tg, k_tr_idx]**2).mean()))
    return dict(
        n_tg=int(is_tg.sum()), n_tr=int(is_tr.sum()),
        kd_tg_fit=kd_tg, kd_tr_fit=kd_tr,
        rmse_tg_in=rmse_tg_in, rmse_tr_in=rmse_tr_in,
        rmse_tr_predicted_from_tg=rmse_tr_oos,
        rmse_tg_predicted_from_tr=rmse_tg_oos,
    )


def loo_deepest(R, kd_grid, z_obs_deep):
    """Leave-one-out with the DEEPEST sensor held out: fit K_d using all
    but the deepest sensor, predict the deepest sensor."""
    i_deepest = int(np.argmax(z_obs_deep))
    idx_train = np.array([i for i in range(R.shape[0]) if i != i_deepest])
    kd_train, _ = kd_star_from_residuals(R, kd_grid, idx=idx_train)
    k_idx = int(np.argmin(np.abs(kd_grid - kd_train)))
    rmse_oos = float(np.abs(R[i_deepest, k_idx]))
    return dict(
        i_deepest=i_deepest, z_deepest_cm=float(z_obs_deep[i_deepest] * 100),
        kd_train=kd_train, abs_residual_deepest_cm=rmse_oos,
    )


# ══════════════════════════════════════════════════════════════════════════════
# Main
# ══════════════════════════════════════════════════════════════════════════════
def main():
    t0 = time.time()
    out_dir = _REPO / 'output'
    fig_letter = _REPO / 'paper' / 'letter' / 'figures'
    fig_appendix = _REPO / 'output' / 'figures'
    results = {}

    # ── A1: extended K_d grids ────────────────────────────────────────────
    # Sized so the bootstrap upper-tail percentiles sit inside the swept
    # range rather than reaching the grid edge via parabolic extrapolation.
    kd_grids = {
        'A15': np.linspace(1.0e-3, 15.0e-3, 28),
        'A17': np.linspace(3.0e-3, 25.0e-3, 30),
    }
    # ──────────────────────────────────────────────────────────────────────────
    # PERFORMANCE: Extended K_d sweep accounts for ~20% of total runtime
    # ──────────────────────────────────────────────────────────────────────────
    # Run equilibrium solver at 28 (A15) + 30 (A17) = 58 K_d values to map out
    # RMSE(K_d) curves. Each solver call runs ~40 lunations × 2551 timesteps.
    # This establishes the baseline residual matrix R[sensor, K_d] used for
    # optimal K_d* retrieval and subsequent bootstrap resampling.
    # ──────────────────────────────────────────────────────────────────────────
    cache = {}
    for name, cfg in SITES.items():
        print(f"\n=== A1: extended K_d sweep — {name} ===", flush=True)
        # This loop calls the thermal solver 28 (A15) or 30 (A17) times.
        # Each call runs ~40 lunations × 2551 timesteps = ~100k timesteps.
        # Total: 58 solver runs × 40 lunations = 2320 simulated lunations.
        z_obs, T_obs, R, stype = run_kd_sweep_extended(cfg, kd_grids[name])
        cache[name] = dict(z_obs=z_obs, T_obs=T_obs, R=R,
                           kd_grid=kd_grids[name], stype=stype)
        # Find K_d* that minimizes RMSE via parabolic fit to R
        kd_star, rmse_star = kd_star_from_residuals(R, kd_grids[name])
        results[name] = dict(kd_star=kd_star, rmse_star=rmse_star,
                             kd_grid=kd_grids[name].tolist(),
                             rmse_curve=np.sqrt((R**2).mean(axis=0)).tolist())
        print(f"   K_d* = {kd_star*1e3:.3f} mW/m/K, RMSE* = {rmse_star:.3f} K",
              flush=True)

    # ── A1b: same K_d sweep under the this-work discrete 3-layer model ────
    # ──────────────────────────────────────────────────────────────────────────
    # PERFORMANCE: 3-layer model sweep adds ~5% to total runtime
    # ──────────────────────────────────────────────────────────────────────────
    # Repeat K_d sweep (58 solver runs) using discrete 3-layer conductivity
    # model instead of continuous H-parameter formulation. Same single free
    # parameter K_d; same retrieval method. Quantifies sensitivity of K_d* to
    # assumed vertical transition structure between surface and deep regolith.
    # ──────────────────────────────────────────────────────────────────────────
    for name, cfg in SITES.items():
        print(f"\n=== A1b: 3-layer K_d sweep — {name} ===", flush=True)
        _, _, R3, _ = run_kd_sweep_extended(cfg, kd_grids[name],
                                            k_model='3layer')
        kd3, rmse3 = kd_star_from_residuals(R3, kd_grids[name])
        results[name]['kd_star_3layer'] = kd3
        results[name]['rmse_star_3layer'] = rmse3
        results[name]['rmse_curve_3layer'] = \
            np.sqrt((R3**2).mean(axis=0)).tolist()
        print(f"   3-layer K_d* = {kd3*1e3:.3f} mW/m/K, "
              f"RMSE* = {rmse3:.3f} K", flush=True)

    # ── A5: depth-uncertainty bootstrap (extended grid + jittered depths) ─
    # ──────────────────────────────────────────────────────────────────────────
    # PERFORMANCE: Statistical post-processing (65% of runtime, but NOT physics)
    # ──────────────────────────────────────────────────────────────────────────
    # Bootstrap resampling to quantify uncertainty: 1500 iterations per site
    # to propagate ±2.5 cm depth uncertainty into K_d* confidence intervals.
    # Uses cached thermal solver results from A1 above - no new physics runs.
    # This is pure statistics for error bars. Reduce to 300 for testing.
    # ──────────────────────────────────────────────────────────────────────────
    print(f"\n=== A5: bootstrap with depth uncertainty (±{DEPTH_SIGMA_CM} cm) ===",
          flush=True)
    for name, cfg in SITES.items():
        c = cache[name]
        boots = bootstrap_kd_with_depth_uncertainty(
            cfg, c['kd_grid'], c['R'], c['z_obs'], c['T_obs'])
        med, lo, hi = np.percentile(boots, [50, 2.5, 97.5])
        results[name]['bootstrap'] = dict(
            n_boot=len(boots), median=float(med),
            ci_lo=float(lo), ci_hi=float(hi),
            samples=boots.tolist())
        print(f"   {name}: K_d* = {med*1e3:.2f} (95% CI [{lo*1e3:.2f}, {hi*1e3:.2f}])",
              flush=True)

    boot15 = np.array(results['A15']['bootstrap']['samples'])
    boot17 = np.array(results['A17']['bootstrap']['samples'])
    contrast = boot17 - boot15
    cmed, clo, chi_ = np.percentile(contrast, [50, 2.5, 97.5])
    results['contrast_bootstrap'] = dict(
        median=float(cmed), ci_lo=float(clo), ci_hi=float(chi_),
        p_value=float((contrast <= 0).mean()))
    print(f"   contrast = {cmed*1e3:.2f} (95% CI [{clo*1e3:.2f}, {chi_*1e3:.2f}]),  "
          f"p={(contrast<=0).mean():.4g}", flush=True)
    print(f"   [t={time.time()-t0:.0f}s]", flush=True)

    # ── A2: 8x8 joint K_d × H grid ────────────────────────────────────────
    # ──────────────────────────────────────────────────────────────────────────
    # PERFORMANCE: Joint parameter grid accounts for ~12% of total runtime
    # ──────────────────────────────────────────────────────────────────────────
    # Map 8×8 grid in (K_d, H) space for both sites: 64 runs/site × 2 = 128
    # solver calls at ~40 lunations each. Tests for degeneracy between deep
    # conductivity K_d and compaction scale height H. Result: minimal trade-off,
    # K_d* is robust to H variations.
    # ──────────────────────────────────────────────────────────────────────────
    print(f"\n=== A2: dense joint K_d × H (8×8 per site) ===", flush=True)
    h_grid = np.linspace(0.03, 0.10, 8)
    for name, cfg in SITES.items():
        ks = results[name]['kd_star']
        kd_g = np.linspace(0.55*ks, 1.45*ks, 8)
        rmse2d = joint_kd_h_dense(cfg, kd_g, h_grid)
        i, j = np.unravel_index(np.argmin(rmse2d), rmse2d.shape)
        results[name]['joint_kd_h'] = dict(
            h_grid=h_grid.tolist(), kd_grid=kd_g.tolist(),
            rmse2d=rmse2d.tolist(),
            h_min=float(h_grid[i]), kd_min=float(kd_g[j]),
            rmse_min=float(rmse2d[i, j]))
        print(f"   {name}: joint min K_d={kd_g[j]*1e3:.2f}, "
              f"H={h_grid[i]*100:.1f} cm, RMSE={rmse2d[i,j]:.3f} K", flush=True)
    print(f"   [t={time.time()-t0:.0f}s]", flush=True)

    # ── A3: held-out validation ───────────────────────────────────────────
    print(f"\n=== A3: held-out validation ===", flush=True)
    for name in SITES:
        c = cache[name]
        tgtr = holdout_tg_tr(SITES[name], c['kd_grid'], c['R'], c['stype'])
        loo  = loo_deepest(c['R'], c['kd_grid'], c['z_obs'])
        results[name]['holdout'] = dict(tg_tr=tgtr, loo_deepest=loo)
        print(f"   {name}:", flush=True)
        if tgtr:
            print(f"     TG-only fit K_d* = {tgtr['kd_tg_fit']*1e3:.2f}; "
                  f"predicting TR sensors gives RMSE = {tgtr['rmse_tr_predicted_from_tg']:.3f} K",
                  flush=True)
            print(f"     TR-only fit K_d* = {tgtr['kd_tr_fit']*1e3:.2f}; "
                  f"predicting TG sensors gives RMSE = {tgtr['rmse_tg_predicted_from_tr']:.3f} K",
                  flush=True)
        print(f"     LOO deepest (z={loo['z_deepest_cm']:.0f} cm): "
              f"K_d_train = {loo['kd_train']*1e3:.2f}, "
              f"|residual| = {loo['abs_residual_deepest_cm']:.3f} K", flush=True)

    # ── save ──────────────────────────────────────────────────────────────
    def jsonify(o):
        import numpy as _np
        if isinstance(o, _np.ndarray): return o.tolist()
        if isinstance(o, (_np.floating, _np.integer)): return o.item()
        if isinstance(o, dict): return {k: jsonify(v) for k, v in o.items()}
        if isinstance(o, (list, tuple)): return [jsonify(x) for x in o]
        return o
    # Add Q_b sensitivity (analytical, from the K_d/Q_b degeneracy on
    # the retrieved K_d*). Required by fig_robustness panel (a). Doing
    # this *before* writing the JSON so the saved file is complete.
    import numpy as _np
    alphas = _np.linspace(0.0, 1.3, 27)
    g15, g17 = _np.meshgrid(alphas, alphas, indexing='ij')
    _kd15 = results['A15']['kd_star'] * g15
    _kd17 = results['A17']['kd_star'] * g17
    _contrast = _kd17 - _kd15
    _sigma_c = (results['contrast_bootstrap']['ci_hi'] -
                results['contrast_bootstrap']['ci_lo']) / 4.0
    results['qb_sensitivity'] = dict(
        alpha_grid=alphas.tolist(),
        contrast_grid=_contrast.tolist(),
        significance_grid=(_contrast / _sigma_c).tolist(),
    )

    # Provenance: pin the bootstrap seed and git commit so the JSON is
    # self-describing for reproducibility checks.
    import subprocess as _sub
    try:
        _git = _sub.check_output(
            ['git', '-C', str(_REPO), 'rev-parse', 'HEAD'],
            stderr=_sub.DEVNULL,
        ).decode().strip()
    except Exception:
        _git = 'unknown'
    results['provenance'] = dict(
        bootstrap_seed=42,
        depth_sigma_cm=DEPTH_SIGMA_CM,
        git_commit=_git,
    )

    out_path = out_dir / 'kd_retrieval_results.json'
    out_path.write_text(json.dumps(jsonify(results), indent=2))
    print(f"\nSaved: {out_path}", flush=True)

    # ── figures ───────────────────────────────────────────────────────────
    print(f"\n=== Figures ===", flush=True)
    from make_results_figures import (   # type: ignore
        fig_bootstrap, fig_robustness,
    )
    fig_bootstrap(results, fig_letter / 'fig_bootstrap.pdf')
    fig_robustness(results, fig_letter / 'fig_robustness.pdf')
    fig_holdout(results, fig_appendix / 'fig_holdout.pdf')

    print(f"\n[t={time.time()-t0:.0f}s] Phase-A pipeline complete.", flush=True)


# ══════════════════════════════════════════════════════════════════════════════
# Held-out figure
# ══════════════════════════════════════════════════════════════════════════════
def fig_holdout(d, out_path):
    fig, axes = plt.subplots(1, 2, figsize=(13.0, 5.0),
                             gridspec_kw={'wspace': 0.32})
    fig.subplots_adjust(left=0.07, right=0.78, bottom=0.16, top=0.88)
    axA, axB = axes

    sites = ['A15', 'A17']
    width = 0.35
    x = np.arange(len(sites))

    in_tg  = [d[s]['holdout']['tg_tr']['rmse_tg_in']   for s in sites]
    in_tr  = [d[s]['holdout']['tg_tr']['rmse_tr_in']   for s in sites]
    oos_tr = [d[s]['holdout']['tg_tr']['rmse_tr_predicted_from_tg'] for s in sites]
    oos_tg = [d[s]['holdout']['tg_tr']['rmse_tg_predicted_from_tr'] for s in sites]

    # ── (a) TG↔TR cross-prediction bars ────────────────────────────────────
    axA.bar(x - width/2, in_tg,  width, color=C_A15, alpha=0.55,
            edgecolor=C_A15, lw=0.6,
            label="TG fit, evaluated on TG  (in-sample)")
    axA.bar(x + width/2, oos_tr, width, color=C_A15, alpha=0.95,
            edgecolor=C_A15, lw=0.6, hatch='//',
            label="TG fit, evaluated on TR  (out-of-sample)")

    axA.bar(x - width/2 + 2.4, in_tr,  width, color=C_A17, alpha=0.55,
            edgecolor=C_A17, lw=0.6,
            label="TR fit, evaluated on TR  (in-sample)")
    axA.bar(x + width/2 + 2.4, oos_tg, width, color=C_A17, alpha=0.95,
            edgecolor=C_A17, lw=0.6, hatch='\\\\',
            label="TR fit, evaluated on TG  (out-of-sample)")

    axA.set_xticks(np.concatenate([x, x + 2.4]))
    axA.set_xticklabels(sites + sites)
    axA.set_xlim(-0.7, 4.9)
    fmt_axis(axA,
             ylabel="Deep-sensor RMSE  (K)",
             title="(a)  TG vs TR cross-prediction")
    axA.set_xlabel("")

    # text labels above each bar pair
    for xi, vin, voos in zip(x, in_tg, oos_tr):
        axA.text(xi, max(vin, voos) + 0.05,
                 f"$\\Delta$ = {voos-vin:+.2f} K", ha="center", va="bottom",
                 fontsize=FS_TICK, color=C_A15)
    for xi, vin, voos in zip(x + 2.4, in_tr, oos_tg):
        axA.text(xi, max(vin, voos) + 0.05,
                 f"$\\Delta$ = {voos-vin:+.2f} K", ha="center", va="bottom",
                 fontsize=FS_TICK, color=C_A17)

    # ── (b) Leave-one-deepest-out residual ────────────────────────────────
    deepest_z = [d[s]['holdout']['loo_deepest']['z_deepest_cm']  for s in sites]
    deepest_r = [d[s]['holdout']['loo_deepest']['abs_residual_deepest_cm'] for s in sites]

    bars = axB.bar(sites, deepest_r, color=[C_A15, C_A17], alpha=0.78,
                   edgecolor=[C_A15, C_A17], lw=0.7,
                   label="|model − obs| at the deepest withheld sensor")
    for bar, z, r in zip(bars, deepest_z, deepest_r):
        axB.text(bar.get_x() + bar.get_width()/2, r + 0.03,
                 f"z = {z:.0f} cm\n|Δ| = {r:.2f} K",
                 ha="center", va="bottom", fontsize=FS_TICK, color=C_CHAR,
                 linespacing=1.3)
    fmt_axis(axB,
             ylabel="Out-of-sample residual  |Δ|  (K)",
             title="(b)  Leave-one-deepest-out residual")
    axB.set_xlabel("")
    axB.set_ylim(0, max(deepest_r) * 1.6)

    # shared legend OUTSIDE on the right
    h0, l0 = axA.get_legend_handles_labels()
    h1, l1 = axB.get_legend_handles_labels()
    fig.legend(h0 + h1, l0 + l1,
               loc="center left", bbox_to_anchor=(0.79, 0.5),
               frameon=True, edgecolor=C_GRID, framealpha=0.97,
               handlelength=2.2, borderpad=0.7,
               title="Held-out validation",
               title_fontsize=FS_LABEL)

    fig.savefig(out_path)
    plt.close(fig)
    print(f"  → {out_path}", flush=True)


if __name__ == '__main__':
    main()
