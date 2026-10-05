"""Review diagnostics (audit 2026-10-01): three questions the letter answers in words.

Question 1 -- is the global K_d rejected at A17 whatever the basal flux?
------------------------------------------------------------------------
The letter's established result is that the Hayne (2017) global K_d = 3.4
does not reproduce the A17 column. At the Langseth (1976) flux it fails on
the GRADIENT. But the gradient below the anchor scales with Q_b, so at a low
enough flux (Saito et al. 2007 report 3.7 mW m^-2) the global value must
match the gradient. This section evaluates K_d = 3.4 at A17 across
Q_b = 3.7-16 mW m^-2 and, at each Q_b, re-retrieves the best K_d* for the
Delta-AICc comparison. It records the model OLS gradient and the mean bias,
so the letter can state HOW the global value fails at each flux, not just
that it does.

Question 2 -- how large is the diurnal swing at the retained-sensor depths?
---------------------------------------------------------------------------
The converged cycle eq.out.T spans the full column, but below ~0.85 m its
max-min is dominated by the slow residual relaxation of the deep column over
one cycle (a ~1e-3 K floor), not by the diurnal wave. The swing is therefore
measured where it is clean -- the decay length is fitted over 0.45-0.70 m,
where K is at its deep asymptote and the swing (>=0.04 K) is far above that
floor -- and continued exponentially to the retained-sensor depths. The raw
max-min at those depths (wave plus residual drift) is stored alongside as a
cross-check; the two agree in order of magnitude.
Also reported: the depths at which the swing (and the half-swing amplitude)
fall below 0.1 K. Replaces the hard-coded Z_SKIN_DEAD = 54 cm of
make_intro_column.py.

Question 3 -- why does the A17 level rise with K_d?
---------------------------------------------------
The A17 retrieval is level-driven (+4.5 mW m^-1 K^-1 per K of T_eq bias;
offset_free_fit.json) and the A15 one is not (-0.16). This section records
the mean surface temperature, the anchor temperature and the mean band
temperature as K_d is raised. Raising K_d warms the mean surface (a more
conductive column buffers the night-time cooling) but flattens the gradient
below the anchor; the band level therefore has a minimum in K_d. Local
slopes between neighbouring K_d values are stored, because a single linear
fit across the minimum would hide the sign change.

Question 4 -- does the Diviner surface data favor the site K_d or the global one?
-------------------------------------------------------------------------------
results/diviner_closure.json compares each site model with the Diviner GCP
averaged over ALL longitudes in a 0.5-degree latitude strip (a zonal curve,
mixing mare and highlands -- close to what the global K_d was calibrated on).
This section evaluates Hayne at the site K_d*, Hayne at the global 3.4, and
Martinez forward against BOTH that zonal curve and the GCP pixels at the
landing site itself (site longitude +-0.5 deg, robustness +-1 deg), with the
mean bias split into day (06-18 LT) and night. Model cycles and statistics
are the closure script's own functions (imported, not re-implemented); the
zonal Hayne-K_d* row must reproduce diviner_closure.json (self-check).

Question 5 -- why do the two thermometer types disagree at A17?
----------------------------------------------------------------
The hold-out fits in kd_retrieval_results.json give, at A17, K_d = 8.06 from
the gradient-bridge (TG) sensors alone and 6.18 from the ring-bridge (TR)
sensors alone. The four shallow TG sensors (130-178 cm) carry the latest
stability windows. This section repeats the TG-only / TR-only fits (the
retrieval's own holdout_tg_tr) on the common-1974-epoch T_eq of
common_epoch_sensitivity.json: if the split collapses there, it is the
window-epoch effect, not a sensor-type calibration offset.

Writes:
    results/review_diagnostics.json

Runtime: ~5 min (Hayne njit fast path; ~0.6 s per equilibrium solve).

Run with:
    python pipeline/compute/compute_review_diagnostics.py
"""
from __future__ import annotations
import json, sys, pathlib, time

_REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO))
sys.path.insert(0, str(_REPO / "src"))
sys.path.insert(0, str(_REPO / "pipeline" / "compute"))

import numpy as np

# Single source of physics: the certified retrieval module and the solver.
import retrieve_kd as rk
from retrieve_kd import run_with, kd_star_from_residuals, _interp_profile_at_depths
from lunar.config import (SITES, GRID, DT_STEP, HAYNE, EQ_Z_ANCHOR,
                          EQ_N_INNER, EQ_MAX_OUTER, EQ_ANCHOR_TOL)
from lunar.grid import make_geometric_grid
from lunar.solver import periodic_time_grid, standard_insolation
from lunar.properties import conductivity_hayne, specific_heat
from lunar.equilibrium import solve_periodic_equilibrium

KD_GLOBAL = 3.4e-3                          # Hayne (2017) global value [W/m/K]
QB_SCAN_MW = [3.7, 5.0, 7.0, 10.0, 14.0, 16.0]   # 3.7 Saito 2007; 14, 16 Langseth 1976
KD_COARSE = np.arange(2.0, 20.01, 1.0) * 1e-3     # wide bracket for the vertex search
SWING_THRESHOLD_K = 0.1
FIT_WINDOW_M = (0.45, 0.70)                 # clean decay-length fit window [m]


# ── helpers ──────────────────────────────────────────────────────────────────
def observed(site_cfg):
    """Retained (meter-scale) sensor depths [m] and T_eq [K], as in the retrieval."""
    obs = rk.extract_sensor_stability(site_cfg['mission'],
                                      min_depth_cm=site_cfg['MIN_DEPTH_CM'])
    deep = np.asarray(obs['deep_mask'], dtype=bool)
    return (np.asarray(obs['depth_cm_all'])[deep] / 100.0,
            np.asarray(obs['T_eq_all'])[deep])


def ols_slope(z, T):
    """OLS slope dT/dz [K/m] and its standard error."""
    A = np.vstack([z, np.ones_like(z)]).T
    coef, *_ = np.linalg.lstsq(A, T, rcond=None)
    resid = T - A @ coef
    s2 = (resid @ resid) / (len(z) - 2)
    se = np.sqrt(s2 / ((z - z.mean()) ** 2).sum())
    return float(coef[0]), float(se)


def aicc(rmse, n, k):
    """Small-sample AICc as defined in the letter (k includes the variance term)."""
    return n * np.log(rmse ** 2) + 2 * k + 2 * k * (k + 1) / (n - k - 1)


def residuals(site_cfg, z_obs, T_obs, kd_grid, qb):
    R = np.empty((len(z_obs), len(kd_grid)))
    for j, kd in enumerate(kd_grid):
        z_mid, T_mean = run_with(site_cfg, kd=kd, qb=qb)
        R[:, j] = _interp_profile_at_depths(z_obs, z_mid, T_mean,
                                            context="review diagnostic") - T_obs
    return R


def best_fit(site_cfg, z_obs, T_obs, qb):
    """Coarse bracket, then a dense 0.1 mW band around it, then the certified vertex."""
    Rc = residuals(site_cfg, z_obs, T_obs, KD_COARSE, qb)
    k0 = KD_COARSE[int(np.argmin(np.sqrt((Rc ** 2).mean(axis=0))))]
    dense = np.round(np.arange(k0 - 1.0e-3, k0 + 1.0001e-3, 0.1e-3), 7)
    dense = dense[dense > 0]
    grid = np.unique(np.round(np.concatenate([KD_COARSE, dense]), 7))   # round: no last-bit twins
    R = residuals(site_cfg, z_obs, T_obs, grid, qb)
    kd_star, rmse_star = kd_star_from_residuals(R, grid)
    return float(kd_star), float(rmse_star)


def equilibrium(site_cfg, kd):
    g = make_geometric_grid(**GRID)
    t = periodic_time_grid(DT_STEP)
    eq = solve_periodic_equilibrium(
        grid=g, t=t, insolation=standard_insolation(site_cfg['lat'], t),
        albedo=site_cfg['albedo'], emissivity=site_cfg['emissivity'],
        Q_b=site_cfg['Q_BASAL'],
        K_func=lambda T, z, _kd=kd: conductivity_hayne(
            T, z, Ks=HAYNE['K_S'], Kd=_kd, H=HAYNE['H'], chi=HAYNE['CHI']),
        cp_func=lambda T: specific_heat(T, model='hayne'),
        T_guess=site_cfg['T_MEAN_EFF'], z_anchor=EQ_Z_ANCHOR,
        n_inner=EQ_N_INNER, max_outer=EQ_MAX_OUTER, anchor_tol_K=EQ_ANCHOR_TOL,
        hayne_params=(HAYNE['K_S'], kd, HAYNE['H'], HAYNE['CHI']))
    return g, eq


def crossing_depth(z, y, lam, threshold):
    """Depth where y falls below threshold (within the grid, else extrapolated)."""
    below = np.nonzero(y < threshold)[0]
    if below.size and below[0] > 0:
        i = below[0]
        return float(np.interp(np.log(threshold), np.log(y[[i, i - 1]]), z[[i, i - 1]]))
    return float(z[-1] + lam * np.log(y[-1] / threshold))


# ── question 1 ───────────────────────────────────────────────────────────────
def global_kd_vs_qb():
    site = SITES['A17']
    z_obs, T_obs = observed(site)
    n = len(z_obs)
    slope_obs, se_obs = ols_slope(z_obs, T_obs)
    rows = []
    for qb_mw in QB_SCAN_MW:
        qb = qb_mw * 1e-3
        z_mid, T_mean = run_with(site, kd=KD_GLOBAL, qb=qb)
        T_pred = _interp_profile_at_depths(z_obs, z_mid, T_mean, context="global K_d")
        r = T_pred - T_obs
        rmse_g = float(np.sqrt((r ** 2).mean()))
        kd_star, rmse_star = best_fit(site, z_obs, T_obs, qb)
        rows.append(dict(
            qb_mW=qb_mw,
            rmse_global_K=rmse_g,
            bias_global_K=float(r.mean()),
            slope_model_global_K_per_m=ols_slope(z_obs, T_pred)[0],
            kd_star_mW=kd_star * 1e3,
            rmse_star_K=rmse_star,
            delta_aicc_global_minus_fit=float(aicc(rmse_g, n, 1) - aicc(rmse_star, n, 2)),
        ))
        print(f"   Q_b={qb_mw:5.1f}: global RMSE {rmse_g:.3f} K, bias {r.mean():+.3f} K, "
              f"slope {rows[-1]['slope_model_global_K_per_m']:.3f} K/m | "
              f"K_d*={kd_star*1e3:.2f}, RMSE* {rmse_star:.3f} K, "
              f"dAICc {rows[-1]['delta_aicc_global_minus_fit']:.1f}", flush=True)
    return dict(site='A17', n_sensors=n, kd_global_mW=KD_GLOBAL * 1e3,
                slope_obs_K_per_m=slope_obs, slope_obs_se_K_per_m=se_obs, rows=rows)


# ── question 2 ───────────────────────────────────────────────────────────────
def diurnal_swing():
    canon = json.loads((_REPO / "results" / "kd_retrieval_results.json").read_text())
    # the joint (albedo, K_d) fit: config.SITES holds its albedo, so this pair is
    # the letter's model column (Sec. 2.6); kd_star is the temperature-only value
    joint = json.loads((_REPO / "results" / "joint_albedo_fit.json").read_text())["sites"]
    out = {}
    for name, cfg in SITES.items():
        z_obs, _ = observed(cfg)
        per_kd = {}
        kd_joint = joint[name]["with_diffusivity"]["best"]["kd_star_mW"] * 1e-3
        for label, kd in (("kd_star", canon[name]['kd_star']), ("kd_joint", kd_joint),
                          ("kd_global", KD_GLOBAL)):
            _, eq = equilibrium(cfg, kd)
            zc, Tc = eq.out.z, eq.out.T
            p2p = Tc.max(axis=1) - Tc.min(axis=1)
            fit = (zc >= FIT_WINDOW_M[0]) & (zc <= FIT_WINDOW_M[1])
            slope, icpt = np.polyfit(zc[fit], np.log(p2p[fit]), 1)
            lam = float(-1.0 / slope)
            extrap = lambda d: float(np.exp(icpt + slope * d))
            upper = lambda d: float(np.exp(np.interp(d, zc, np.log(p2p))))
            per_kd[label] = dict(
                kd_mW=float(kd * 1e3),
                fit_window_m=list(FIT_WINDOW_M),
                decay_length_m=lam,
                p2p_at_0p54_m_K=float(np.interp(0.54, zc, p2p)),
                depth_p2p_below_0p1K_m=crossing_depth(zc, p2p, lam, SWING_THRESHOLD_K),
                depth_amp_below_0p1K_m=crossing_depth(zc, p2p / 2, lam, SWING_THRESHOLD_K),
                p2p_shallowest_sensor_K=extrap(float(z_obs.min())),
                p2p_shallowest_sensor_raw_maxmin_K=upper(float(z_obs.min())),
                p2p_deepest_sensor_K=extrap(float(z_obs.max())),
            )
            d = per_kd[label]
            print(f"   {name} {label} ({kd*1e3:.2f}): decay {lam*100:.1f} cm, "
                  f"p2p(0.54 m) {d['p2p_at_0p54_m_K']:.3f} K, p2p<0.1 K below "
                  f"{d['depth_p2p_below_0p1K_m']*100:.0f} cm, amp<0.1 K below "
                  f"{d['depth_amp_below_0p1K_m']*100:.0f} cm, p2p at "
                  f"{z_obs.min()*100:.0f} cm {d['p2p_shallowest_sensor_K']:.1e} K "
                  f"(raw max-min {d['p2p_shallowest_sensor_raw_maxmin_K']:.1e})", flush=True)
        out[name] = dict(shallowest_sensor_m=float(z_obs.min()),
                         deepest_sensor_m=float(z_obs.max()), **per_kd)
    return out


# ── question 3 ───────────────────────────────────────────────────────────────
def level_vs_kd():
    out = {}
    for name, kds in (("A17", (3.4, 5.0, 6.0, 7.08, 8.0, 9.0)),
                      ("A15", (3.4, 4.0, 4.6, 5.2, 6.0))):
        cfg = SITES[name]
        z_obs, _ = observed(cfg)
        rows = []
        for kd_mw in kds:
            g, eq = equilibrium(cfg, kd_mw * 1e-3)
            T_band = np.interp(z_obs, g.z_mid, eq.T_mean)
            rows.append(dict(kd_mW=kd_mw,
                             T_surface_mean_K=float(eq.out.T_surface.mean()),
                             T_anchor_K=float(eq.anchor_K),
                             T_band_top_K=float(T_band[np.argmin(z_obs)]),
                             T_band_bottom_K=float(T_band[np.argmax(z_obs)]),
                             T_band_mean_K=float(T_band.mean())))
            print(f"   {name} K_d={kd_mw:5.2f}: surface mean {rows[-1]['T_surface_mean_K']:.2f}, "
                  f"anchor {rows[-1]['T_anchor_K']:.2f}, band mean {rows[-1]['T_band_mean_K']:.2f} K",
                  flush=True)
        k = np.array([r['kd_mW'] for r in rows])
        local = lambda key: [dict(kd_mid_mW=float(0.5 * (k[i] + k[i + 1])),
                                  slope_K_per_mW=float((rows[i + 1][key] - rows[i][key])
                                                       / (k[i + 1] - k[i])))
                             for i in range(len(k) - 1)]
        out[name] = dict(rows=rows,
                         dT_surface_dKd_local=local('T_surface_mean_K'),
                         dT_anchor_dKd_local=local('T_anchor_K'),
                         dT_band_mean_dKd_local=local('T_band_mean_K'))
    return out


# ── question 4 ───────────────────────────────────────────────────────────────
def diviner_site_vs_zonal():
    import compute_diviner_closure as dc
    from lunar.diviner import load_gcp_band, gcp_band_for_latitude, select_diurnal_curve
    from lunar.properties import conductivity_martinez
    canon = json.loads((_REPO / "results" / "kd_retrieval_results.json").read_text())
    closure = json.loads((_REPO / "results" / "diviner_closure.json").read_text())

    def stats(lst_obs, T_obs, lst_mod, T_mod):
        order = np.argsort(lst_mod)
        pred = np.interp(lst_obs, lst_mod[order], T_mod[order], period=24.0)
        r = pred - T_obs
        day = (lst_obs >= 6.0) & (lst_obs < 18.0)
        return dict(rmse_K=float(np.sqrt(np.mean(r ** 2))), bias_K=float(r.mean()),
                    bias_day_K=float(r[day].mean()), bias_night_K=float(r[~day].mean()),
                    n_bins=int(len(r)))

    out = {}
    for name, cfg in SITES.items():
        lo, hi = gcp_band_for_latitude(cfg['lat'])
        band = load_gcp_band(lo, hi, columns=(dc.CHANNEL,))
        curves = {"zonal": select_diurnal_curve(band, cfg['lat'], channel=dc.CHANNEL)}
        for hw in (0.5, 1.0):
            curves[f"site_pm{hw}deg"] = select_diurnal_curve(
                band, cfg['lat'], channel=dc.CHANNEL,
                longitude_range=(cfg['lon'] - hw, cfg['lon'] + hw))
        models = {
            "hayne_kd_star": lambda T, z, k=float(canon[name]['kd_star']): conductivity_hayne(
                T, z, Ks=HAYNE['K_S'], Kd=k, H=HAYNE['H'], chi=HAYNE['CHI']),
            "hayne_kd_global": lambda T, z: conductivity_hayne(
                T, z, Ks=HAYNE['K_S'], Kd=KD_GLOBAL, H=HAYNE['H'], chi=HAYNE['CHI']),
            "martinez_forward": lambda T, z: conductivity_martinez(T, z=z),
        }
        res = {}
        for mname, kf in models.items():
            lst_m, T_m = dc.model_surface_cycle(cfg, kf)
            res[mname] = {cname: stats(lo_, To_, lst_m, T_m) for cname, (lo_, To_) in curves.items()}
            z, s = res[mname]["zonal"], res[mname]["site_pm0.5deg"]
            print(f"   {name} {mname:17s}: zonal bias {z['bias_K']:+.2f} (day {z['bias_day_K']:+.2f}, "
                  f"night {z['bias_night_K']:+.2f}) | site bias {s['bias_K']:+.2f} "
                  f"(day {s['bias_day_K']:+.2f}, night {s['bias_night_K']:+.2f}), "
                  f"site RMSE {s['rmse_K']:.2f} K", flush=True)
        self_check = abs(res["hayne_kd_star"]["zonal"]["bias_K"]
                         - closure[name]["hayne_site_fit"]["bias_K"])
        print(f"   {name} self-check vs diviner_closure.json: |d bias| = {self_check:.3f} K", flush=True)
        out[name] = dict(lon=cfg['lon'], models=res,
                         self_check_zonal_bias_diff_K=float(self_check))
    return out


# ── question 5 ───────────────────────────────────────────────────────────────
def thermometer_type_split():
    from lunar.config import KD_GRIDS
    ce = json.loads((_REPO / "results" / "common_epoch_sensitivity.json").read_text())
    out = {}
    for name, cfg in SITES.items():
        kd_grid = KD_GRIDS[name]
        z_obs, T_obs, R, stype = rk.run_kd_sweep_extended(cfg, kd_grid)
        # Match by sensor NAME, in the retrieval's own order: depth is not a
        # unique key (A17 TR11A and TR21A both sit at 140 cm).
        obs = rk.extract_sensor_stability(cfg['mission'], min_depth_cm=cfg['MIN_DEPTH_CM'])
        names = [s['sensor'] for s, d in zip(obs['sensors'], obs['deep_mask']) if d]
        by_name = {s['sensor']: s for s in ce[name]['sensors']}
        rows = [by_name[n] for n in names]
        T_cert = np.array([r['T_certified'] for r in rows])
        T_comm = np.array([r['T_common'] for r in rows])
        match = float(np.abs(T_cert - T_obs).max())   # self-check: same sensors, same T_eq
        R_common = R + (T_obs - T_comm)[:, None]      # R = T_model - T_obs
        cert = rk.holdout_tg_tr(cfg, kd_grid, R, stype)
        comm = rk.holdout_tg_tr(cfg, kd_grid, R_common, stype)
        all_comm = kd_star_from_residuals(R_common, kd_grid)[0]
        shift = {t: float(np.mean((T_obs - T_comm)[stype == t])) for t in ("TG", "TR")}
        mw = lambda d: {k: (v * 1e3 if k.startswith('kd') else v) for k, v in d.items()}
        out[name] = dict(certified=mw(cert), common_1974=mw(comm),
                         kd_all_common_1974_mW=float(all_comm * 1e3),
                         mean_Teq_shift_to_common_K=shift,
                         self_check_max_Teq_mismatch_K=match)
        print(f"   {name}: certified TG {cert['kd_tg_fit']*1e3:.2f} / TR {cert['kd_tr_fit']*1e3:.2f} | "
              f"common-1974 TG {comm['kd_tg_fit']*1e3:.2f} / TR {comm['kd_tr_fit']*1e3:.2f} "
              f"(all {all_comm*1e3:.2f}) | mean T_eq shift TG {shift['TG']:+.2f} K, "
              f"TR {shift['TR']:+.2f} K | T_eq match {match:.3f} K", flush=True)
    return out


# ── main ─────────────────────────────────────────────────────────────────────
def main():
    t0 = time.time()
    print("Q1: global K_d at A17 across basal flux", flush=True)
    q1 = global_kd_vs_qb()
    print("Q2: diurnal swing vs depth", flush=True)
    q2 = diurnal_swing()
    print("Q3: band level vs K_d", flush=True)
    q3 = level_vs_kd()
    print("Q4: Diviner, site pixels vs zonal curve", flush=True)
    q4 = diviner_site_vs_zonal()
    print("Q5: thermometer-type split vs window epoch", flush=True)
    q5 = thermometer_type_split()
    out = dict(
        meta=dict(purpose="pre-submission diagnostics (audit 2026-10-01)",
                  note="Sensitivity diagnostics; do not re-baseline the certified retrieval.",
                  runtime_s=round(time.time() - t0, 1)),
        global_kd_vs_qb=q1, diurnal_swing=q2, level_vs_kd=q3,
        diviner_site_vs_zonal=q4, thermometer_type_split=q5)
    path = _REPO / "results" / "review_diagnostics.json"
    path.write_text(json.dumps(out, indent=1))
    print(f"wrote {path.relative_to(_REPO)} in {time.time() - t0:.0f} s")


if __name__ == "__main__":
    main()
