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
    results/kd_retrieval_results.json     # canonical numerical results
    ../figures/fig_bootstrap.pdf          # top-level shared figure home
    ../figures/fig_robustness.pdf
    ../figures/fig_holdout.pdf

Sections (search the function name -- line numbers drift):
    conductivity_3layer / run_with       -- model wrappers + one solve
    run_kd_sweep_extended                -- the K_d sweep
    kd_star_from_residuals               -- parabola vertex (+ spacing guard)
    bootstrap_kd_with_depth_uncertainty  -- 1500-draw CI
    joint_kd_h_dense                     -- joint (K_d, H) fit
    holdout_tg_tr / loo_deepest          -- hold-out diagnostics
    main                                 -- orchestrates the above

Runtime: dominated by the equilibrium solves -- the Hayne and 3-layer K_d
sweeps (one solve per config.KD_GRIDS point per site) and the joint K_d x H
grid. main() runs these independent solves on N_WORKERS processes
(prefetch_profiles) and the analysis then reads them from _PROFILE_CACHE;
each solve is deterministic, so the results are bit-identical to a serial
run. The
3-layer sweep has no compiled fast path and is the slowest phase. The
bootstrap reuses the cached profiles, no new physics (~1 s). Per-solve cost
depends on DT_STEP / EQ_N_INNER / CN_PICARD_SWEEPS (lunar.config) -- see
results/speedup_benchmark.json rather than trusting a figure here.

Run with:
    python pipeline/compute/retrieve_kd.py
"""
from __future__ import annotations
import functools, json, sys, pathlib, time
from multiprocessing import Pool

# Repo root resolved from this file's location, so results and figures
# are written into the SAME checkout the script is run from.
_REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO))
sys.path.insert(0, str(_REPO / "src"))
from lunar import _bootstrap as boot
boot.ensure_lunar(extra=('spiceypy', 'scipy'))
boot.ensure_apollo_hfe(mission='a15', probes=())
boot.ensure_apollo_hfe(mission='a17', probes=())

import numpy as np
from tqdm.auto import tqdm  # live progress bars: clean HTML widget in Jupyter,
                            # plain text in a terminal (needs ipywidgets for the widget)
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

from lunar.grid import make_geometric_grid
from lunar.properties import (conductivity_hayne, conductivity_martinez,
                              specific_heat)
from lunar.solver import periodic_time_grid, standard_insolation
from lunar.equilibrium import solve_periodic_equilibrium
from lunar.apollo_helpers import extract_sensor_stability


# Shared publication style from the package (no longer a figure-script import).
from lunar.plotting.style import (   # noqa: E402
    C_A15, C_A17, C_CHAR, C_GRID,
    FS_LABEL, FS_TICK, fmt_axis,
)
# Single source of truth for ALL run configuration (lunar/config.py) --
# SITES, GRID, the Hayne bundle, the equilibrium-solver settings, the
# 3-layer parameters. These used to be redefined here and in four figure
# scripts; now there is exactly one definition.
from lunar.config import (   # noqa: E402
    S0, T_LUNAR,   # noqa: F401 -- re-exported (make_equilibrium_certification imports them from here)
    DT_STEP,
    EQ_Z_ANCHOR, EQ_N_INNER, EQ_MAX_OUTER, EQ_ANCHOR_TOL,
    GRID, HAYNE, SITES, DEPTH_SIGMA_CM, KD_GRIDS,
    TL_Z1, TL_Z2, TL_RHO_REF, TL_RHO_SITE,
)
# pipeline/figures kept on path for the end-of-run figure helpers
# (fig_bootstrap, fig_robustness) imported inside main().
sys.path.insert(0, str(_REPO / 'pipeline' / 'figures'))

# In-process memo cache for converged mean profiles, keyed on every input
# that can change the forward model (speeds the repeated sweeps).
_PROFILE_CACHE: dict = {}

# Worker processes for the independent equilibrium solves in main(); each
# solve is single-threaded (same count as the other compute scripts).
N_WORKERS = 5

# The HFE record is otherwise re-read for every sweep (~2 s each); callers
# only read the returned arrays.
_sensor_obs = functools.lru_cache(maxsize=None)(extract_sensor_stability)


def _interp_profile_at_depths(z_obs, z_model, T_model, *, context):
    """Interpolate a model profile, rejecting depths outside the solved grid."""
    z_obs = np.asarray(z_obs, dtype=float)
    z_model = np.asarray(z_model, dtype=float)
    if z_obs.size == 0:
        raise ValueError(f"{context}: no observation depths were supplied")
    if z_obs.min() < z_model[0] or z_obs.max() > z_model[-1]:
        raise ValueError(
            f"{context}: observation depths [{z_obs.min():.3f}, {z_obs.max():.3f}] m "
            f"fall outside model grid [{z_model[0]:.3f}, {z_model[-1]:.3f}] m"
        )
    return np.interp(z_obs, z_model, T_model)


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
def _cache_key(site_cfg, *, kd=None, h=None, qb=None, k_model='hayne',
               rho_deep=None, martinez_alpha=None):
    """_PROFILE_CACHE key of one run_with() call (same keyword interface)."""
    return (site_cfg.get('tag'), site_cfg['lat'], site_cfg['albedo'],
            site_cfg['emissivity'],
            site_cfg['Q_BASAL'] if qb is None else qb,
            kd, HAYNE['H'] if h is None else h, k_model, rho_deep,
            martinez_alpha)


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
    cache_key = _cache_key(site_cfg, kd=kd, h=h, qb=qb, k_model=k_model,
                           rho_deep=rho_deep, martinez_alpha=martinez_alpha)
    if cache_key in _PROFILE_CACHE:
        return _PROFILE_CACHE[cache_key]
    site = dict(site_cfg)
    if qb is not None:
        site['Q_BASAL'] = qb
    h = HAYNE['H'] if h is None else h
    grid_  = make_geometric_grid(**GRID)
    z_mid  = grid_.z_mid
    t_s = periodic_time_grid(DT_STEP)   # commensurate lunation grid (audit 2026-07-03)
    insol = standard_insolation(site['lat'], t_s)   # the ONE forcing builder
    if k_model == '3layer':
        if kd is None:
            raise ValueError("3layer model requires kd")
        rd = (rho_deep if rho_deep is not None
              else TL_RHO_SITE.get(site_cfg.get('tag', ''), TL_RHO_REF))
        def k_func(T, z):
            return conductivity_3layer(T, z, Kd=kd, rho_deep=rd)
    elif k_model == 'martinez':
        # Martinez K(T, rho). When martinez_alpha is None the model is
        # evaluated forward on the Hayne-form rho(z) with H = 6 cm, the
        # profile of the Hayne runs (Martinez & Siegler 2021 use 5.6 cm;
        # compute_joint_fit_checks.py runs both). When
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
    # The flux-anchored solve (lunar/equilibrium.py) is the whole cost of this
    # call: EQ_N_INNER skin lunations per outer iteration, round(T_LUNAR /
    # DT_STEP) Crank-Nicolson steps per lunation, 1 + CN_PICARD_SWEEPS
    # tridiagonal solves per step. T_MEAN_EFF only seeds the first iterate;
    # the converged profile is independent of it (F1 audit).
    eq = solve_periodic_equilibrium(
        grid=grid_, t=t_s, insolation=insol,
        albedo=site['albedo'], emissivity=site['emissivity'],
        Q_b=site['Q_BASAL'], K_func=k_func, cp_func=cp_func,
        T_guess=site['T_MEAN_EFF'],
        z_anchor=EQ_Z_ANCHOR, n_inner=EQ_N_INNER,
        max_outer=EQ_MAX_OUTER, anchor_tol_K=EQ_ANCHOR_TOL,
        # compiled march for the standard Hayne set (tested equal to the
        # generic path to <1e-9 K); 3layer/martinez use the generic path
        hayne_params=((HAYNE['K_S'], kd, h, HAYNE['CHI'])
                      if k_model == 'hayne' else None),
    )
    if not eq.converged or eq.flux_closure > 0.05:
        print(f"   WARNING: equilibrium not fully converged "
              f"(drift={eq.anchor_drift_K:.3f} K, "
              f"closure={eq.flux_closure:.3%})", flush=True)
    _PROFILE_CACHE[cache_key] = (z_mid, eq.T_mean)
    return z_mid, eq.T_mean


def _solve_job(job):
    """Pool worker: one run_with() call, tagged with its job index."""
    i, site_cfg, kw = job
    return i, run_with(site_cfg, **kw)


def prefetch_profiles(jobs, desc):
    """Solve independent run_with() calls on N_WORKERS processes.

    ``jobs`` is a list of ``(site_cfg, run_with_kwargs)``. The profiles land
    in _PROFILE_CACHE, so the serial analysis loops that follow are cache
    hits. Each solve is deterministic and self-contained, so the cached
    profiles are bit-identical to running the same calls serially. Other
    compute scripts call it ahead of their own run_with() loops; call it from
    code under ``if __name__ == "__main__"`` (workers re-import that module).
    """
    todo = [(cfg, kw) for cfg, kw in jobs
            if _cache_key(cfg, **kw) not in _PROFILE_CACHE]
    if not todo:
        return
    tagged = [(i, cfg, kw) for i, (cfg, kw) in enumerate(todo)]
    with Pool(N_WORKERS) as pool:
        for i, profile in tqdm(pool.imap_unordered(_solve_job, tagged),
                               total=len(todo), desc=desc, unit="solve"):
            cfg, kw = todo[i]
            _PROFILE_CACHE[_cache_key(cfg, **kw)] = profile


# The vertex is only as accurate as the grid spacing AROUND the minimum.
# config.KD_GRIDS packs a dense ~0.2 mW band bracketing today's minima; if a
# future input change (Q_b, albedo, chi, ...) moves K_d* out of that band, the
# vertex silently degrades to the coarse spacing (~0.76 mW -> +-0.02 mW vertex
# noise, the bug that drove the 7.15-vs-7.18 disagreement). The guard below
# makes that failure LOUD instead of silent.
KD_VERTEX_MAX_SPACING = 0.30e-3   # [W/m/K] warn if bracket spacing exceeds this


def kd_star_from_residuals(R, kd_grid, idx=None, warn_coarse=True):
    """Sub-grid minimum of RMSE(K_d): 3-point parabola through the lowest points.

    Guards (both print loud warnings rather than fail, so bootstrap draws
    keep running):
      * minimum at a grid EDGE -> no bracket, returns the edge value;
      * bracket spacing > KD_VERTEX_MAX_SPACING -> the minimum has drifted
        out of the dense band; re-center config.KD_GRIDS before trusting
        the third decimal of K_d*.
    Two numerical safeguards (audit 2026-10-04) change nothing on a clean
    bracket: near-duplicate grid points (one K_d built twice, differing in
    the last bit -- np.unique over two linspaces keeps both) are collapsed,
    since a bracket holding both makes the parabola singular; and the vertex
    is kept inside its bracket. Replaying the production bootstrap (seed 42)
    with both safeguards moves 2 of the 1500 A15 draws (3.900 -> 3.86, 3.80
    mW, both on the config.KD_GRIDS twin at 3.8 and below the 2.5th
    percentile) and leaves the nominal K_d*, every CI, the contrast CI and
    P_boot unchanged to four decimals.
    """
    if idx is None:
        idx = np.arange(R.shape[0])
    rmse = np.sqrt((R[idx]**2).mean(axis=0))
    kd_grid = np.asarray(kd_grid, dtype=float)
    keep = np.concatenate([[True], np.abs(np.diff(kd_grid)) > 1e-9])
    kd_grid, rmse = kd_grid[keep], rmse[keep]
    k_min = int(np.argmin(rmse))
    if 0 < k_min < len(kd_grid) - 1:
        x = kd_grid[k_min-1:k_min+2]
        y = rmse[k_min-1:k_min+2]
        if warn_coarse and (np.diff(x).max() > KD_VERTEX_MAX_SPACING):
            print(f"   WARNING: K_d* bracket spacing {np.diff(x).max()*1e3:.2f} mW "
                  f"exceeds {KD_VERTEX_MAX_SPACING*1e3:.2f} mW -- the minimum "
                  f"(~{kd_grid[k_min]*1e3:.2f} mW) left the dense KD_GRIDS band; "
                  f"re-center the band in config.py (vertex noise ~+-0.02 mW).")
        denom = (x[0]-x[1])*(x[0]-x[2])*(x[1]-x[2])
        a = (x[2]*(y[1]-y[0]) + x[1]*(y[0]-y[2]) + x[0]*(y[2]-y[1])) / denom
        b = (x[2]**2*(y[0]-y[1]) + x[1]**2*(y[2]-y[0]) + x[0]**2*(y[1]-y[2])) / denom
        kd_star = -b / (2*a) if a > 0 else kd_grid[k_min]
        kd_star = min(max(kd_star, x[0]), x[2])    # vertex stays in its bracket
        rmse_star = float(np.interp(kd_star, x, y))
    else:
        if warn_coarse:
            print(f"   WARNING: RMSE minimum sits at the EDGE of the K_d grid "
                  f"({kd_grid[k_min]*1e3:.2f} mW) -- no parabola bracket; "
                  f"widen config.KD_GRIDS.")
        kd_star = kd_grid[k_min]
        rmse_star = float(rmse[k_min])
    return float(kd_star), rmse_star


# ══════════════════════════════════════════════════════════════════════════════
# A1 — Extended K_d sweep
# ══════════════════════════════════════════════════════════════════════════════
def run_kd_sweep_extended(site_cfg, kd_grid, k_model='hayne'):
    """Sweep through K_d values to find optimal fit to Apollo HFE data.

    This is the core K_d retrieval loop. For each K_d value in kd_grid:
    1. Run the flux-anchored equilibrium solver (run_with)
    2. Extract predicted temperatures at sensor depths
    3. Compute residuals vs Apollo observations

    Returns residual matrix R[sensor, K_d] used to find K_d* that minimizes
    RMSE. Wall time scales with len(kd_grid) x one equilibrium solve; see
    results/speedup_benchmark.json for the current per-solve cost.
    """
    obs = _sensor_obs(site_cfg['mission'],
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
    for k, kd in enumerate(tqdm(kd_grid,
                                desc=f"K_d sweep {site_cfg['label']} {k_model}",
                                unit="Kd")):
        # one full equilibrium solve, unless main() prefetched it
        z_mid, T_mean_z = run_with(site_cfg, kd=kd, k_model=k_model)
        T_pred = _interp_profile_at_depths(
            z_obs_deep, z_mid, T_mean_z,
            context=f"{site_cfg['label']} {k_model} K_d sweep",
        )
        R[:, k] = T_pred - T_obs_deep
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
    for k, kd in enumerate(tqdm(kd_grid,
                                desc=f"boot cache {site_cfg['label']}",
                                unit="Kd")):
        z_mid, T_mean_z = run_with(site_cfg, kd=kd)
        T_cache[k] = np.interp(z_grid_dense, z_mid, T_mean_z)

    # Pure statistics on the cached profiles -- no new physics (~1 s for
    # 1500 draws). Each draw: resample sensors with replacement, jitter their
    # depths, re-interpolate the cached T_model(z, K_d), refit K_d*.
    boots = np.empty(n_boot)
    for b in tqdm(range(n_boot),
                  desc=f"bootstrap {site_cfg['label']}", unit="draw"):
        idx = rng.integers(0, n, size=n)
        # jittered depths
        dz = rng.normal(0.0, depth_sigma_cm / 100.0, size=n)
        z_jit = z_obs_deep[idx] + dz[idx]
        # build a residual matrix per K_d at the jittered depths
        R_jit = np.empty((n, len(kd_grid)))
        for k in range(len(kd_grid)):
            T_pred = _interp_profile_at_depths(
                z_jit, z_grid_dense, T_cache[k],
                context=f"{site_cfg['label']} bootstrap depth jitter",
            )
            R_jit[:, k] = T_pred - T_obs_deep[idx]
        # warn_coarse=False: individual bootstrap draws may wander off the
        # dense band by design -- that is sampling, not a config error, and
        # 1500 draws must not print 1500 warnings. The NOMINAL fit (called
        # once, warn_coarse=True) is the guard that matters.
        kd_star, _ = kd_star_from_residuals(R_jit, kd_grid, warn_coarse=False)
        boots[b] = kd_star
    return boots


# ══════════════════════════════════════════════════════════════════════════════
# A2 — Densified joint K_d × H grid
# ══════════════════════════════════════════════════════════════════════════════
def joint_kd_h_dense(site_cfg, kd_grid, h_grid):
    obs = _sensor_obs(site_cfg['mission'],
                      min_depth_cm=site_cfg['MIN_DEPTH_CM'])
    z_obs = np.asarray(obs['depth_cm_all']) / 100.0
    T_obs = np.asarray(obs['T_eq_all'])
    deep  = np.asarray(obs['deep_mask'], dtype=bool)
    z_obs_deep = z_obs[deep]
    T_obs_deep = T_obs[deep]
    rmse = np.empty((len(h_grid), len(kd_grid)))
    total = len(h_grid) * len(kd_grid)
    pbar = tqdm(total=total, desc=f"joint K_d×H {site_cfg['label']}",
                unit="cell")
    for i, h in enumerate(h_grid):
        for j, kd in enumerate(kd_grid):
            z_mid, T_mean_z = run_with(site_cfg, kd=kd, h=h)
            T_pred = _interp_profile_at_depths(
                z_obs_deep, z_mid, T_mean_z,
                context=f"{site_cfg['label']} joint K_d-H grid",
            )
            rmse[i, j] = np.sqrt(((T_pred - T_obs_deep)**2).mean())
            pbar.update(1)
    pbar.close()
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
    out_dir = _REPO / 'results'
    # One figure home: every generator writes to the top-level shared
    # figures/ folder (see STRUCTURE.md); results/ holds JSON only.
    fig_dir = _REPO.parent / 'figures'
    results = {}

    # ── A1: extended K_d grids ────────────────────────────────────────────
    # Single-sourced in lunar.config.KD_GRIDS (wide span + dense 0.2 mW band at
    # the minimum for a grid-converged parabola vertex; see the comment there).
    kd_grids = KD_GRIDS
    # Solve every sweep point of A1 (Hayne) and A1b (3-layer) for both sites
    # in parallel up front; the loops below then read the cache. The 3-layer
    # solves run the generic (uncompiled) march and are much slower, so they
    # are queued first to keep the workers busy to the end.
    print(f"\n=== A1/A1b: equilibrium solves on {N_WORKERS} workers ===",
          flush=True)
    prefetch_profiles([(cfg, dict(kd=kd, k_model=k_model))
                       for k_model in ('3layer', 'hayne')
                       for name, cfg in SITES.items() for kd in kd_grids[name]],
                      desc="K_d sweeps (3-layer + Hayne)")
    print(f"   [t={time.time()-t0:.0f}s]", flush=True)

    # R[sensor, K_d] per site: the residual matrix behind K_d*, the bootstrap
    # and the hold-out tests.
    cache = {}
    for name, cfg in SITES.items():
        print(f"\n=== A1: extended K_d sweep — {name} ===", flush=True)
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
    # Same single free parameter and retrieval; quantifies how K_d* depends
    # on the assumed surface-to-deep transition structure.
    for name, cfg in SITES.items():
        print(f"\n=== A1b: 3-layer K_d sweep — {name} ===", flush=True)
        _, _, R3, _ = run_kd_sweep_extended(cfg, kd_grids[name],
                                            k_model='3layer')
        kd3, rmse3 = kd_star_from_residuals(R3, kd_grids[name])
        results[name]['kd_star_3layer'] = kd3
        results[name]['rmse_star_3layer'] = rmse3
        results[name]['rmse_curve_3layer'] = \
            np.sqrt((R3**2).mean(axis=0)).tolist()
        # Edge guard: if the minimum sits ON a grid endpoint it is a FLOOR,
        # not a fitted vertex (A17 pins at the 3.0 mW floor -- the 3-layer
        # model prefers K_d below the sweep). Persist the flag so the value
        # is never quoted as a retrieved number without the caveat.
        edge3 = bool(np.isclose(kd3, kd_grids[name][0])
                     or np.isclose(kd3, kd_grids[name][-1]))
        results[name]['kd_star_3layer_edge_limited'] = edge3
        print(f"   3-layer K_d* = {kd3*1e3:.3f} mW/m/K, "
              f"RMSE* = {rmse3:.3f} K"
              + ("   [EDGE-LIMITED: grid floor, not a vertex]" if edge3 else ""),
              flush=True)

    # ── A5: depth-uncertainty bootstrap (extended grid + jittered depths) ─
    # 1500 draws per site propagate the sensor-depth envelope into the K_d*
    # CIs; reuses the A1 profiles, no new physics.
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
    # 16-84 percentiles: the asymmetric 1-sigma interval the manuscript
    # quotes (2.31 +0.67/-0.90); persist so the quote is auditable.
    cq16, cq84 = np.percentile(contrast, [16, 84])
    results['contrast_bootstrap'] = dict(
        median=float(cmed), ci_lo=float(clo), ci_hi=float(chi_),
        q16=float(cq16), q84=float(cq84),
        # NB this is the bootstrap tail proportion P_boot(contrast <= 0)
        # computed from the FITTED (non-null-centered) bootstrap draws --
        # report it as such, never as a conventional null-centered p-value
        # (audit 2026-07-13, codex F5). Key name kept for compatibility;
        # p_boot_leq0 is the honest alias.
        p_value=float((contrast <= 0).mean()),
        p_boot_leq0=float((contrast <= 0).mean()))
    print(f"   contrast = {cmed*1e3:.2f} (95% CI [{clo*1e3:.2f}, {chi_*1e3:.2f}]),  "
          f"P_boot(dK<=0)={(contrast<=0).mean():.4g}", flush=True)
    print(f"   [t={time.time()-t0:.0f}s]", flush=True)

    # ── A2: joint K_d × H grid ────────────────────────────────────────────
    # Degeneracy between deep conductivity K_d and the compaction scale H:
    # 8 H values x 8 (A15) / 12 (A17) K_d values around each site's K_d*.
    print("\n=== A2: dense joint K_d × H per site ===", flush=True)
    h_grid = np.linspace(0.03, 0.10, 8)
    kd_joint = {}
    for name in SITES:
        ks = results[name]['kd_star']
        # A17's K_d-H degeneracy valley bottoms ABOVE the old 1.45x edge, so
        # sweep it wider (to ~1.7x, ~12 mW) on a finer grid to capture the
        # interior minimum; A15's minimum is interior already (unchanged).
        hi, npts = (1.70, 12) if name == "A17" else (1.45, 8)
        kd_joint[name] = np.linspace(0.55*ks, hi*ks, npts)
    prefetch_profiles([(cfg, dict(kd=kd, h=h)) for name, cfg in SITES.items()
                       for h in h_grid for kd in kd_joint[name]],
                      desc="joint K_d×H")
    for name, cfg in SITES.items():
        kd_g = kd_joint[name]
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
    print("\n=== A3: held-out validation ===", flush=True)
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
        if isinstance(o, np.ndarray): return o.tolist()
        if isinstance(o, (np.floating, np.integer)): return o.item()
        if isinstance(o, dict): return {k: jsonify(v) for k, v in o.items()}
        if isinstance(o, (list, tuple)): return [jsonify(x) for x in o]
        return o
    # Add the PROPORTIONAL Q_b surrogate grid. SUPERSEDED (audit F-9):
    # the proportional rule K_d*(alpha*Qb) = alpha*K_d* is a disproved
    # model of the degeneracy -- the real relation is inverse and
    # non-proportional (see results/qb_degeneracy.json, written by
    # compute_qb_degeneracy.py, which fig_robustness panel (a) and the
    # error budget actually use). Kept only for backward compatibility
    # of the JSON schema; do NOT base any conclusion on this block.
    alphas = np.linspace(0.0, 1.3, 27)
    g15, g17 = np.meshgrid(alphas, alphas, indexing='ij')
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
    print("\n=== Figures ===", flush=True)
    from make_results_figures import (   # type: ignore
        fig_bootstrap, fig_robustness,
    )
    fig_bootstrap(results, fig_dir / 'fig_bootstrap.pdf')
    try:   # v1.1 (fixed-albedo) figure, used only by the GEDES thesis; its guard checks a
           # claim of that text and must not stop the reproduction of the current paper
        fig_robustness(results, fig_dir / 'fig_robustness.pdf')
    except AssertionError as e:
        print(f"  WARNING: fig_robustness.pdf (v1.1, not in the current paper) not drawn: {e}", flush=True)
    fig_holdout(results, fig_dir / 'fig_holdout.pdf')

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
