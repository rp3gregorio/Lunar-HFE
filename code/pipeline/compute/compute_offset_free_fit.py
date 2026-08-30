"""Free-offset and gradient-only K_d retrieval (reviewer diagnostic, 2026-08-28).

Question this answers
---------------------
The published retrieval minimizes the ABSOLUTE meter-scale-sensor RMSE, so it
is sensitive both to the SHAPE of T(z) and to its overall LEVEL. Section 4.2 of
the letter argues that at A17 the retained band (130-234 cm) is nearly
isothermal, so the fit is driven by the level rather than by the gradient --
which is also why K_d*(A17) rises when Q_b is lowered. If that is right, then
any additive bias in T_eq (residual post-emplacement warming, probe
calibration offset, terrain-driven lunation-mean offset) maps straight into
K_d*. This script tests that directly by re-fitting K_d with the level removed.

Three objectives are evaluated on the SAME residual matrix
R[sensor, K_d] = T_model(K_d) - T_eq_obs produced by the certified sweep
(retrieve_kd.run_kd_sweep_extended -- imported, not re-implemented):

  (1) 'absolute'  RMSE(K_d) = sqrt(< R^2 >)             the published retrieval
  (2) 'offset'    RMSE(K_d) = sqrt(< (R - <R>)^2 >)     additive offset d free.
                  Profiling out an additive d is exactly demeaning R, so the
                  free-offset RMSE is the population SD of the residuals and
                  the certified vertex routine can be reused unchanged.
                  d*(K_d) = -<R> is the temperature shift the fit wants.
  (3) 'gradient'  match the OLS slope dT/dz of the model to that of the data
                  over the retained sensors; K_d found by root-finding
                  slope_model(K_d) - slope_obs = 0.

Self-checks (printed, and stored under 'validation' in the JSON):
  * objective (1) must reproduce results/kd_retrieval_results.json;
  * the bootstrap with center=False must reproduce the canonical 95% CIs.
Both use the canonical seed 42 and the same +-2.5 cm depth jitter.

Writes:
    results/offset_free_fit.json

Runtime: ~1 min (Hayne njit fast path; ~0.5-1.1 s per equilibrium solve).

Run with:
    python pipeline/compute/compute_offset_free_fit.py
"""
from __future__ import annotations
import json, sys, pathlib, time

_REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO))
sys.path.insert(0, str(_REPO / "src"))
sys.path.insert(0, str(_REPO / "pipeline" / "compute"))

import numpy as np

# Single source of physics: the certified retrieval module.
import retrieve_kd as rk
from retrieve_kd import (run_with, run_kd_sweep_extended,
                         kd_star_from_residuals, _interp_profile_at_depths)
from lunar.config import SITES, KD_GRIDS, DEPTH_SIGMA_CM

SEED = 42
N_BOOT = 1500
KD_GLOBAL = 3.4e-3          # Hayne (2017) published global value [W/m/K]


# ── helpers ──────────────────────────────────────────────────────────────────
def ols_slope(z, T):
    """OLS slope dT/dz [K/m] and its standard error, for >=3 distinct depths."""
    z = np.asarray(z, float); T = np.asarray(T, float)
    if z.size < 3 or np.unique(z).size < 3:
        return np.nan, np.nan
    A = np.vstack([z, np.ones_like(z)]).T
    coef, *_ = np.linalg.lstsq(A, T, rcond=None)
    slope = float(coef[0])
    resid = T - A @ coef
    dof = z.size - 2
    if dof <= 0:
        return slope, np.nan
    s2 = float((resid**2).sum() / dof)
    Sxx = float(((z - z.mean())**2).sum())
    return slope, float(np.sqrt(s2 / Sxx)) if Sxx > 0 else np.nan


def gradient_root(kd_grid, slope_mod, slope_obs):
    """K_d where slope_model crosses slope_obs (linear interp on the grid).

    Returns (kd, bracket) or (nan, None) when the target is never crossed --
    which is itself the informative outcome if the observed gradient lies
    outside the range the model can produce over the swept K_d.
    """
    d = np.asarray(slope_mod, float) - float(slope_obs)
    sign = np.sign(d)
    cross = np.where(np.diff(sign) != 0)[0]
    if cross.size == 0 or not np.isfinite(slope_obs):
        return float('nan'), None
    i = int(cross[0])                       # first crossing
    x0, x1 = kd_grid[i], kd_grid[i + 1]
    y0, y1 = d[i], d[i + 1]
    kd = x0 - y0 * (x1 - x0) / (y1 - y0) if y1 != y0 else x0
    return float(kd), [float(x0), float(x1)]


def bootstrap(site_cfg, kd_grid, z_obs, T_obs, *, center, n_boot=N_BOOT,
              seed=SEED, depth_sigma_cm=DEPTH_SIGMA_CM):
    """Sensor resample + depth jitter, refitting K_d* each draw.

    Mirrors retrieve_kd.bootstrap_kd_with_depth_uncertainty exactly (same
    dense grid, same RNG call order, same seed) so that center=False
    reproduces the canonical CIs; center=True demeans the residuals first,
    i.e. profiles out the additive offset in every draw.
    """
    rng = np.random.default_rng(seed)
    n = len(z_obs)
    z_dense = np.linspace(0.05, 3.0, 200)
    T_cache = np.empty((len(kd_grid), len(z_dense)))
    for k, kd in enumerate(kd_grid):
        z_mid, T_mean_z = run_with(site_cfg, kd=kd)
        T_cache[k] = np.interp(z_dense, z_mid, T_mean_z)

    boots = np.empty(n_boot)
    for b in range(n_boot):
        idx = rng.integers(0, n, size=n)
        dz = rng.normal(0.0, depth_sigma_cm / 100.0, size=n)
        z_jit = z_obs[idx] + dz[idx]
        R_jit = np.empty((n, len(kd_grid)))
        for k in range(len(kd_grid)):
            T_pred = _interp_profile_at_depths(
                z_jit, z_dense, T_cache[k], context="offset-free bootstrap")
            R_jit[:, k] = T_pred - T_obs[idx]
        if center:
            R_jit = R_jit - R_jit.mean(axis=0, keepdims=True)
        kd_star, _ = kd_star_from_residuals(R_jit, kd_grid, warn_coarse=False)
        boots[b] = kd_star
    return boots


def bootstrap_gradient(site_cfg, kd_grid, z_obs, T_obs, *, n_boot=N_BOOT,
                       seed=SEED, depth_sigma_cm=DEPTH_SIGMA_CM):
    """Same resampling, but refitting the GRADIENT-ONLY K_d each draw.

    Draws whose resampled depth set has <3 distinct depths, or whose observed
    slope is never crossed by the model over the swept K_d, are recorded as
    NaN and counted (they are reported, not silently dropped).
    """
    rng = np.random.default_rng(seed)
    n = len(z_obs)
    z_dense = np.linspace(0.05, 3.0, 200)
    T_cache = np.empty((len(kd_grid), len(z_dense)))
    for k, kd in enumerate(kd_grid):
        z_mid, T_mean_z = run_with(site_cfg, kd=kd)
        T_cache[k] = np.interp(z_dense, z_mid, T_mean_z)

    boots = np.full(n_boot, np.nan)
    for b in range(n_boot):
        idx = rng.integers(0, n, size=n)
        dz = rng.normal(0.0, depth_sigma_cm / 100.0, size=n)
        z_jit = z_obs[idx] + dz[idx]
        T_b = T_obs[idx]
        s_obs, _ = ols_slope(z_jit, T_b)
        if not np.isfinite(s_obs):
            continue
        s_mod = np.empty(len(kd_grid))
        for k in range(len(kd_grid)):
            T_pred = _interp_profile_at_depths(
                z_jit, z_dense, T_cache[k], context="gradient bootstrap")
            s_mod[k], _ = ols_slope(z_jit, T_pred)
        kd, _ = gradient_root(kd_grid, s_mod, s_obs)
        boots[b] = kd
    return boots


def ci(samples):
    s = np.asarray(samples, float)
    s = s[np.isfinite(s)]
    if s.size == 0:
        return dict(n=0, median=None, ci_lo=None, ci_hi=None)
    return dict(n=int(s.size), median=float(np.median(s)),
                ci_lo=float(np.percentile(s, 2.5)),
                ci_hi=float(np.percentile(s, 97.5)))



def flat_floor(kd_grid, curve, *, tol_K):
    """Range of K_d over which an objective stays within tol_K of its minimum.

    This is the honest summary of a flat objective: quoting the location of a
    minimum that sits on a floor varying by <tol_K is meaningless, so report
    the floor's extent instead. Edge-touching is reported explicitly.
    """
    c = np.asarray(curve, float)
    kd = np.asarray(kd_grid, float)
    m = float(c.min())
    inside = kd[c <= m + tol_K]
    return dict(tol_K=tol_K, min_value=m,
                kd_lo_mW=float(inside.min() * 1e3),
                kd_hi_mW=float(inside.max() * 1e3),
                touches_grid_top=bool(inside.max() >= kd.max() - 1e-12),
                touches_grid_bottom=bool(inside.min() <= kd.min() + 1e-12))


def closure_audit(site_cfg, kd_values):
    """Flux-closure of the equilibrium solve at selected K_d (numerical honesty).

    run_with() prints a warning when closure exceeds 5% but does not return it,
    so the solve is repeated here purely to record the number. Duplicates the
    Hayne k_func construction of retrieve_kd.run_with -- keep in step with it.
    """
    from copy import deepcopy
    from lunar.grid import make_geometric_grid
    from lunar.properties import conductivity_hayne, specific_heat
    from lunar.solver import periodic_time_grid, standard_insolation
    from lunar.equilibrium import solve_periodic_equilibrium
    from lunar.config import (S0, DT_STEP, GRID, HAYNE, EQ_Z_ANCHOR,
                              EQ_N_INNER, EQ_MAX_OUTER, EQ_ANCHOR_TOL)
    site = deepcopy(site_cfg)
    grid_ = make_geometric_grid(**GRID)
    t_s = periodic_time_grid(DT_STEP)
    insol = standard_insolation(site['lat'], t_s)
    rows = []
    for kd in kd_values:
        eq = solve_periodic_equilibrium(
            grid=grid_, t=t_s, insolation=insol, albedo=site['albedo'],
            emissivity=site['emissivity'], Q_b=site['Q_BASAL'],
            K_func=lambda T, z, _kd=kd: conductivity_hayne(
                T, z, Ks=HAYNE['K_S'], Kd=_kd, H=HAYNE['H'], chi=HAYNE['CHI']),
            cp_func=lambda T: specific_heat(T, model='hayne'),
            T_guess=site['T_MEAN_EFF'], z_anchor=EQ_Z_ANCHOR,
            n_inner=EQ_N_INNER, max_outer=EQ_MAX_OUTER,
            anchor_tol_K=EQ_ANCHOR_TOL,
            hayne_params=(HAYNE['K_S'], kd, HAYNE['H'], HAYNE['CHI']))
        rows.append(dict(kd_mW=float(kd * 1e3),
                         flux_closure=float(eq.flux_closure),
                         converged=bool(eq.converged),
                         within_5pct=bool(eq.flux_closure <= 0.05)))
    return rows


# ── main ─────────────────────────────────────────────────────────────────────
def main():
    t0 = time.time()
    canon = json.loads((_REPO / "results" / "kd_retrieval_results.json").read_text())
    out = {"meta": {
        "purpose": "reviewer diagnostic: is K_d* shape-driven or level-driven?",
        "n_boot": N_BOOT, "seed": SEED,
        "depth_jitter_cm": DEPTH_SIGMA_CM,
        "kd_global_hayne_mW": KD_GLOBAL * 1e3,
        "note": ("Sensitivity study; does not re-baseline the headline "
                 "retrieval. Objectives share one residual matrix from the "
                 "certified sweep. 'offset' RMSE is the residual SD (an "
                 "additive offset profiled out) and is NOT dof-corrected, so "
                 "it is not directly comparable to the absolute RMSE as a "
                 "goodness-of-fit; compare K_d*, not RMSE, across objectives."),
    }, "sites": {}, "validation": {}}

    for tag, site in SITES.items():
        print(f"\n=== {site['label']} ({tag}) ===", flush=True)
        kd_grid = KD_GRIDS[tag]
        z_obs, T_obs, R, stype = run_kd_sweep_extended(site, kd_grid,
                                                       k_model='hayne')
        n = len(z_obs)

        # (1) absolute -- must reproduce the canonical retrieval
        kd_abs, rmse_abs = kd_star_from_residuals(R, kd_grid)
        # (2) free additive offset
        R_c = R - R.mean(axis=0, keepdims=True)
        kd_off, rmse_off = kd_star_from_residuals(R_c, kd_grid)
        # offset the fit wants, at each objective's own minimum
        k_at_abs = int(np.argmin(np.abs(kd_grid - kd_abs)))
        k_at_off = int(np.argmin(np.abs(kd_grid - kd_off)))
        delta_at_abs = float(-R[:, k_at_abs].mean())
        delta_at_off = float(-R[:, k_at_off].mean())

        # (3) gradient only
        slope_obs, slope_obs_se = ols_slope(z_obs, T_obs)
        slope_mod = np.array([ols_slope(z_obs, R[:, k] + T_obs)[0]
                              for k in range(len(kd_grid))])
        kd_grad, grad_bracket = gradient_root(kd_grid, slope_mod, slope_obs)

        # the global-K_d level test: how much of the misfit is pure offset?
        z_mid, T_mean_z = run_with(site, kd=KD_GLOBAL)
        T_pred_g = _interp_profile_at_depths(z_obs, z_mid, T_mean_z,
                                             context=f"{tag} global K_d")
        r_g = T_pred_g - T_obs
        rmse_g_abs = float(np.sqrt((r_g**2).mean()))
        rmse_g_off = float(np.sqrt(((r_g - r_g.mean())**2).mean()))
        slope_g, _ = ols_slope(z_obs, T_pred_g)

        # --- band warming: the gradient misfit in kelvin across the band ---
        # Quoted in the Discussion, so archived here rather than recomputed
        # ad hoc. Top/bottom of the retained band, not an OLS slope.
        i_top, i_bot = int(np.argmin(z_obs)), int(np.argmax(z_obs))
        # Evaluate at the EXACT K_d* (one extra solve), not at the nearest
        # grid point: Table 2 of the letter quotes the exact-K_d* bias, and
        # the two differ in the second decimal (0.114 vs 0.122 at A17).
        z_ms, T_ms = run_with(site, kd=kd_abs)
        T_nom = _interp_profile_at_depths(z_obs, z_ms, T_ms,
                                          context=f"{tag} exact K_d*")
        band = dict(
            z_top_cm=float(z_obs[i_top] * 100), z_bot_cm=float(z_obs[i_bot] * 100),
            observed_K=float(T_obs[i_bot] - T_obs[i_top]),
            model_at_global_kd_K=float(T_pred_g[i_bot] - T_pred_g[i_top]),
            model_at_kd_star_K=float(T_nom[i_bot] - T_nom[i_top]),
            mean_bias_at_global_kd_K=float(r_g.mean()),
            mean_bias_at_kd_star_K=float((T_nom - T_obs).mean()))
        print(f"  band warming obs/glob/fit: {band['observed_K']:+.3f} / "
              f"{band['model_at_global_kd_K']:+.3f} / "
              f"{band['model_at_kd_star_K']:+.3f} K", flush=True)

        print(f"  n sensors            : {n}  ({z_obs.min()*100:.0f}-"
              f"{z_obs.max()*100:.0f} cm)", flush=True)
        print(f"  (1) absolute  K_d*   : {kd_abs*1e3:.3f} mW  RMSE {rmse_abs:.4f} K",
              flush=True)
        print(f"  (2) offset    K_d*   : {kd_off*1e3:.3f} mW  SD   {rmse_off:.4f} K"
              f"  (delta = {delta_at_off:+.3f} K)", flush=True)
        print(f"  (3) gradient  K_d*   : {kd_grad*1e3:.3f} mW", flush=True)
        print(f"      obs dT/dz        : {slope_obs:.3f} +- {slope_obs_se:.3f} K/m",
              flush=True)


        # --- (4) uniform T_eq bias: dK_d*/d(delta) -------------------------
        # A uniform shift of the observations by delta maps R -> R - delta, so
        # no new solves are needed. This converts "the fit is level-driven"
        # into a quotable error term.
        teq_offset = []
        for dlt in (-0.50, -0.25, -0.10, 0.0, 0.10, 0.25, 0.50):
            kd_d, rm_d = kd_star_from_residuals(R - dlt, kd_grid,
                                                warn_coarse=False)
            teq_offset.append(dict(delta_K=dlt, kd_star_mW=kd_d * 1e3,
                                   rmse_K=rm_d))
        lo = next(r for r in teq_offset if r["delta_K"] == -0.10)
        hi = next(r for r in teq_offset if r["delta_K"] == 0.10)
        dkd_ddelta = (hi["kd_star_mW"] - lo["kd_star_mW"]) / 0.20

        # --- (5) drift extrapolation (depth-dependent transient) -----------
        # Each retained sensor is carried forward at its own fitted trailing
        # slope for a horizon tau. This is a BOUNDING exercise, not an
        # asymptote: a linear tail diverges, so tau is capped at a few years.
        # Slopes come from results/common_epoch_sensitivity.json; the sensor
        # order there is verified against the retrieval depths below.
        ce = json.loads((_REPO / "results" /
                         "common_epoch_sensitivity.json").read_text())
        ce_depths = np.array([sr["depth_cm"] for sr in ce[tag]["sensors"]])
        slopes = np.array([sr["slope_K_yr"] for sr in ce[tag]["sensors"]])
        depth_match = bool(ce_depths.size == z_obs.size and
                           np.allclose(ce_depths, z_obs * 100, atol=0.51))
        drift = []
        if depth_match:
            for tau in (0.0, 1.0, 2.0, 5.0):
                kd_t, rm_t = kd_star_from_residuals(
                    R - (slopes * tau)[:, None], kd_grid, warn_coarse=False)
                s_obs_t, _ = ols_slope(z_obs, T_obs + slopes * tau)
                drift.append(dict(tau_yr=tau, kd_star_mW=kd_t * 1e3,
                                  rmse_K=rm_t, slope_obs_K_per_m=s_obs_t))
        print(f"  (4) dK_d*/d(delta)   : {dkd_ddelta:+.2f} mW per K of uniform "
              f"T_eq bias", flush=True)
        if depth_match:
            print(f"  (5) drift tau=2 yr   : "
                  f"{drift[2]['kd_star_mW']:.3f} mW "
                  f"(tau=0: {drift[0]['kd_star_mW']:.3f})", flush=True)
        else:
            print("  (5) drift extrapolation SKIPPED: sensor depths do not "
                  "match common_epoch_sensitivity.json", flush=True)

        print("  bootstrapping (absolute, validation) ...", flush=True)
        b_abs = bootstrap(site, kd_grid, z_obs, T_obs, center=False)
        print("  bootstrapping (free offset) ...", flush=True)
        b_off = bootstrap(site, kd_grid, z_obs, T_obs, center=True)
        print("  bootstrapping (gradient only) ...", flush=True)
        b_grad = bootstrap_gradient(site, kd_grid, z_obs, T_obs)

        out["sites"][tag] = {
            "label": site["label"], "n_sensors": n,
            "depth_range_cm": [float(z_obs.min() * 100), float(z_obs.max() * 100)],
            "q_basal_mW": site["Q_BASAL"] * 1e3,
            "absolute": {"kd_star_mW": kd_abs * 1e3, "rmse_K": rmse_abs,
                         "delta_implied_K": delta_at_abs,
                         "bootstrap": {k: (v * 1e3 if isinstance(v, float) else v)
                                       for k, v in ci(b_abs).items()}},
            "offset_free": {"kd_star_mW": kd_off * 1e3, "resid_sd_K": rmse_off,
                            "delta_K": delta_at_off,
                            "bootstrap": {k: (v * 1e3 if isinstance(v, float) else v)
                                          for k, v in ci(b_off).items()}},
            "gradient_only": {
                "kd_star_mW": kd_grad * 1e3 if np.isfinite(kd_grad) else None,
                "bracket_mW": [b * 1e3 for b in grad_bracket] if grad_bracket else None,
                "slope_obs_K_per_m": slope_obs,
                "slope_obs_se_K_per_m": slope_obs_se,
                "slope_model_range_K_per_m": [float(np.nanmin(slope_mod)),
                                              float(np.nanmax(slope_mod))],
                "n_boot_valid": int(np.isfinite(b_grad).sum()),
                "bootstrap": {k: (v * 1e3 if isinstance(v, float) else v)
                              for k, v in ci(b_grad).items()}},
            "at_global_kd": {
                "kd_mW": KD_GLOBAL * 1e3,
                "rmse_absolute_K": rmse_g_abs,
                "resid_sd_offset_free_K": rmse_g_off,
                "delta_K": float(-r_g.mean()),
                "slope_model_K_per_m": slope_g,
                "frac_rmse_removed_by_offset":
                    float(1.0 - rmse_g_off / rmse_g_abs) if rmse_g_abs > 0 else None},
            "band_warming": band,
            "teq_offset_sensitivity": {
                "table": teq_offset,
                "dkd_star_per_K_mW": dkd_ddelta,
                "note": ("uniform additive shift of T_eq; R -> R - delta, "
                         "no new solves")},
            "drift_extrapolation": {
                "depths_matched": depth_match,
                "slopes_K_per_yr": slopes.tolist() if depth_match else None,
                "table": drift,
                "note": ("per-sensor trailing slope carried forward tau years "
                         "(bounding, not asymptotic); slopes from "
                         "results/common_epoch_sensitivity.json")},
            "flat_floor": {
                "absolute": flat_floor(kd_grid, np.sqrt((R**2).mean(axis=0)),
                                       tol_K=0.01),
                "offset_free": flat_floor(kd_grid,
                                          np.sqrt((R_c**2).mean(axis=0)),
                                          tol_K=0.01)},
            "curves": {"kd_grid_mW": (np.asarray(kd_grid) * 1e3).tolist(),
                       "rmse_absolute_K": np.sqrt((R**2).mean(axis=0)).tolist(),
                       "resid_sd_offset_free_K": np.sqrt((R_c**2).mean(axis=0)).tolist(),
                       "slope_model_K_per_m": slope_mod.tolist(),
                       "delta_K": (-R.mean(axis=0)).tolist()},
        }

        # validation against the certified results
        out["validation"][tag] = {
            "kd_star_mW": {"this_run": kd_abs * 1e3,
                           "canonical": canon[tag]["kd_star"] * 1e3,
                           "abs_diff_mW": abs(kd_abs - canon[tag]["kd_star"]) * 1e3},
            "ci95_mW": {"this_run": [ci(b_abs)["ci_lo"] * 1e3,
                                     ci(b_abs)["ci_hi"] * 1e3],
                        "canonical": [canon[tag]["bootstrap"]["ci_lo"] * 1e3,
                                      canon[tag]["bootstrap"]["ci_hi"] * 1e3]},
        }

    # numerical honesty: where does the equilibrium solve stop closing?
    print("\nflux-closure audit (A17 high-K_d end) ...", flush=True)
    out["closure_audit"] = {
        "A17": closure_audit(SITES["A17"],
                             [6.0e-3, 8.0e-3, 12.0e-3, 16.0e-3, 18.5e-3,
                              21.0e-3, 25.0e-3]),
        "note": ("solve_periodic_equilibrium flags |flux closure| > 5% as not "
                 "converged; the offset-free objective floor is reached well "
                 "below that point, so the flat floor does not depend on the "
                 "uncertified high-K_d tail."),
    }

    # contrast under each objective
    for key, name in (("absolute", "absolute"), ("offset_free", "offset_free"),
                      ("gradient_only", "gradient_only")):
        a15 = out["sites"]["A15"][key]["kd_star_mW"]
        a17 = out["sites"]["A17"][key]["kd_star_mW"]
        out.setdefault("contrast_mW", {})[name] = (
            (a17 - a15) if (a15 is not None and a17 is not None) else None)

    p = _REPO / "results" / "offset_free_fit.json"
    p.write_text(json.dumps(out, indent=2))
    print(f"\nwrote {p}  [{time.time()-t0:.0f} s]", flush=True)

    print("\n--- VALIDATION vs certified kd_retrieval_results.json ---")
    for tag, v in out["validation"].items():
        print(f"  {tag} K_d*: {v['kd_star_mW']['this_run']:.4f} vs "
              f"{v['kd_star_mW']['canonical']:.4f} mW  "
              f"(diff {v['kd_star_mW']['abs_diff_mW']:.4f})")
        print(f"  {tag} CI95: [{v['ci95_mW']['this_run'][0]:.3f}, "
              f"{v['ci95_mW']['this_run'][1]:.3f}] vs "
              f"[{v['ci95_mW']['canonical'][0]:.3f}, "
              f"{v['ci95_mW']['canonical'][1]:.3f}] mW")


if __name__ == "__main__":
    main()
