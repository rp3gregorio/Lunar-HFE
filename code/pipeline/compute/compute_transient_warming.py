"""Does the post-deployment warming bias K_d? A transient test (2026-10-07).

The meter-scale HFE sensors were still warming when their records end.
Nagihara et al. (2018) attribute this to the astronauts darkening the surface:
an abrupt rise of the surface temperature by 1.6-3.5 K at probe deployment
reproduces the size and timing of the warming at both sites. The joint
retrieval compares a periodic steady-state model with each sensor's
late-record window mean T_eq, so the window means carry part of that
response. This script measures how much, and refits.

1. Forward runs. The Hayne column at the joint fit (A*, K_d*) is driven by the
   real insolation (SPICE, 1966-1977, as in compute_annual_wave.py), started
   from the periodic equilibrium, twice: undisturbed, and with the surface
   darkened at deployment (the first sample of the site's record). The albedo
   enters the model only as (1 - A) S, so the darkening is applied by scaling
   S after deployment by (1 - A1) / (1 - A*). The albedo drop A* - A1 is set
   from the steady-state surface mean of the joint-fit grid so that the mean
   surface temperature rises by dTs = 1.6, 2.5 or 3.5 K.
2. Bias. delta_i = mean over sensor i's stability window of
   T_darkened - T_undisturbed at its depth: the part of the disturbance that
   T_eq contains.
3. Refit. T_eq - delta is the undisturbed equilibrium; it is refitted on the
   cached joint-fit grid (same objective, same diffusivities). Two treatments
   of the surface mean: as measured (211 / 216 K), and lowered by dTs (if the
   measured surface was itself darkened). delta is recomputed at the refitted
   point once, and the refit repeated.
4. Check. The disturbance's warming rate over each window, against each
   sensor's measured trailing slope; the observed gradient after the
   correction; the likelihood-ratio test of the global K_d = 3.4 on the
   corrected data (grid minima, df = 1); and the temperature-only fit (no
   diffusivity term) before and after the correction, with the 95 % profile
   interval of K_d (Delta J <= 3.84).

Reads:  results/joint_albedo_fit.json, results/joint_albedo_fit_cache.npz,
        results/stability_windows.json, data/spice/*
Writes: results/transient_warming.json
Runtime: ~3 min (SPICE insolation once per site, 2 runs per case).

Run with:
    python pipeline/compute/compute_transient_warming.py
"""
from __future__ import annotations
import json, sys, pathlib, time
from multiprocessing import Pool
_REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO)); sys.path.insert(0, str(_REPO / "src")); sys.path.insert(0, str(_REPO / "pipeline" / "compute"))

import numpy as np
import pandas as pd
from scipy.stats import chi2
import compute_joint_albedo_fit as jf
import compute_annual_wave as aw
from compute_joint_fit_checks import bilinear

STEPS_K = (1.6, 2.5, 3.5)               # Nagihara et al. (2018): abrupt surface rise at deployment
N_WORKERS = 4


def run(job):
    """Daily-mean T at each depth (and the surface) for one (site, A, K_d [mW], insolation scale after day0)."""
    site, A, kd_mW, depths, day0, scale = job
    from lunar.config import SITES, GRID, DT_STEP, HAYNE, EQ_Z_ANCHOR, EQ_N_INNER, EQ_MAX_OUTER, EQ_ANCHOR_TOL
    from lunar.grid import make_geometric_grid
    from lunar.solver import periodic_time_grid, standard_insolation, PixelInputs, solve_pixel
    from lunar.properties import conductivity_hayne, specific_heat
    from lunar.equilibrium import solve_periodic_equilibrium
    cfg = SITES[site]; kd = kd_mW * 1e-3
    ks, H, chi = HAYNE["K_S"], HAYNE["H"], HAYNE["CHI"]
    G = make_geometric_grid(**GRID)
    tp = periodic_time_grid(DT_STEP)
    eq = solve_periodic_equilibrium(
        grid=G, t=tp, insolation=standard_insolation(cfg["lat"], tp), albedo=A, emissivity=cfg["emissivity"],
        Q_b=cfg["Q_BASAL"], K_func=lambda T, zz: conductivity_hayne(T, zz, Ks=ks, Kd=kd, H=H, chi=chi),
        cp_func=lambda T: specific_heat(T, model="hayne"), T_guess=cfg["T_MEAN_EFF"], z_anchor=EQ_Z_ANCHOR,
        n_inner=EQ_N_INNER, max_outer=EQ_MAX_OUTER, anchor_tol_K=EQ_ANCHOR_TOL, hayne_params=(ks, kd, H, chi))
    t, S, day = aw.spice_insolation(site)
    S = np.where(day >= day0, S * scale, S)
    out = solve_pixel(PixelInputs(grid=G, t=t, bc_mode="radiative", insolation=S, albedo=A,
                                  emissivity=cfg["emissivity"], Q_b=cfg["Q_BASAL"], T_init=eq.T_mean.copy(),
                                  hayne_params=(ks, kd, H, chi), n_lunations_spinup=1))
    u, inv = np.unique(day, return_inverse=True); cnt = np.bincount(inv)
    zm = G.z_mid; Td = np.empty((len(depths), len(u)))
    for i, z in enumerate(depths):
        j = np.searchsorted(zm, z) - 1; w = (z - zm[j]) / (zm[j + 1] - zm[j])
        Td[i] = np.bincount(inv, out.T[j] * (1 - w) + out.T[j + 1] * w) / cnt
    Tsd = np.bincount(inv, out.T_surface) / cnt
    return u, Td, Tsd


def to_day(d):
    return (pd.Timestamp(d, tz="UTC") - aw.T0).total_seconds() / 86400.0


def main():
    t0 = time.time()
    res = json.loads((_REPO / "results" / "joint_albedo_fit.json").read_text())
    c = np.load(_REPO / "results" / "joint_albedo_fit_cache.npz")
    win = json.loads((_REPO / "results" / "stability_windows.json").read_text())
    out = dict(meta=dict(steps_K=STEPS_K, source="Nagihara et al. (2018): abrupt surface-temperature rise at deployment"),
               sites={})
    for s in ("A15", "A17"):
        z, Tobs = jf.observed(s)
        used = sorted([r for r in win[s] if r["used"]], key=lambda r: r["depth_cm"])
        zw = np.array([r["depth_cm"] for r in used]) / 100.0
        assert len(used) == len(z) and np.allclose(np.sort(z), zw), f"{s}: stability windows do not match the sensors"
        order = np.argsort(z)                                   # map the windows onto the order of z
        wins = [None] * len(z)
        for k, r in zip(order, used):
            assert abs(r["T_eq_K"] - Tobs[k]) < 1e-6, f"{s}: T_eq mismatch at {r['sensor']}"
            wins[k] = (to_day(r["window_start"]), to_day(r["window_end"]), r["trailing_slope_K_per_yr"], r["sensor"])
        day0 = min(to_day(r["record_start"]) for r in win[s])
        Tz, Ts, kap = c[f"{s}_Tz"], c[f"{s}_Ts"], c[f"{s}_kap"]
        kobs = np.array([p[2] for p in jf.KAPPA_OBS[s]]); ksig = np.array([p[3] for p in jf.KAPPA_OBS[s]])
        b = res["sites"][s]["with_diffusivity"]["best"]
        A0, kd0 = b["A"], b["kd_star_mW"]

        iG = int(np.argmin(np.abs(jf.KD_GRID - jf.KD_GLOBAL)))
        grad = lambda T: float(np.polyfit(z, T, 1)[0])

        def fit(T, ts_obs):
            J, _ = jf.objective(Tz, T, Ts, ts_obs, kap=kap, kobs=kobs, ksig=ksig)
            a, kd, _, _ = jf.best_point(J)
            return a, kd * 1e3

        def fit_temperature_only(T, ts_obs):
            """The same fit without the diffusivity term: best point and 95 % profile interval of K_d."""
            J, _ = jf.objective(Tz, T, Ts, ts_obs)
            a, kd, _, _ = jf.best_point(J)
            seg = jf.level_sets(jf.KD_GRID * 1e3, J.min(axis=0))["dJ<=3.84"]
            return dict(A=a, kd_mW=kd * 1e3, interval95_mW=[seg[0][0], seg[-1][1]],
                        at_grid_edge=bool(seg[-1][1] >= jf.KD_GRID[-1] * 1e3 - 1e-9 or seg[0][0] <= jf.KD_GRID[0] * 1e3 + 1e-9))

        def global_test(T, ts_obs):
            """Likelihood-ratio test of K_d = 3.4 (albedo refitted), on the grid."""
            J, _ = jf.objective(Tz, T, Ts, ts_obs, kap=kap, kobs=kobs, ksig=ksig)
            dJ = float(J[:, iG].min() - J.min())
            return dict(delta_J=dJ, p=float(chi2.sf(dJ, 1)))

        def disturbance(A, kd_mW, dTs):
            """delta per sensor, realized surface step, and the disturbance's warming rate per window."""
            dTdA = (bilinear(Ts, A + 0.005, kd_mW * 1e-3) - bilinear(Ts, A - 0.005, kd_mW * 1e-3)) / 0.01
            A1 = A + dTs / dTdA                                 # dTdA < 0: darker surface, higher mean
            scale = (1 - A1) / (1 - A)
            with Pool(2) as pool:
                (u, Ta, Tsa), (_, Tb, Tsb) = pool.map(run, [(s, A, kd_mW, z, day0, 1.0), (s, A, kd_mW, z, day0, scale)])
            d = Tb - Ta
            delta, rate = np.empty(len(z)), np.empty(len(z))
            for i, (w0, w1, _, _) in enumerate(wins):
                m = (u >= w0) & (u <= w1)
                delta[i] = d[i, m].mean()
                rate[i] = np.polyfit(u[m] / 365.25, d[i, m], 1)[0]
            post = (u >= day0 + 30) & (u < day0 + 30 + 365)
            return dict(A_darkened=float(A1), surface_step_K=float((Tsb - Tsa)[post].mean()),
                        delta_K=delta, rate_K_per_yr=rate)

        site = dict(nominal=dict(A=A0, kd_mW=kd0, gradient_observed_K_per_m=grad(Tobs),
                                 temperature_only=fit_temperature_only(Tobs, jf.TS_OBS[s]),
                                 global_3p4=global_test(Tobs, jf.TS_OBS[s])),
                    deployment_day_since_1972=day0, cases={})
        print(f"{s}: joint fit A {A0:.4f}, K_d {kd0:.2f}; deployment day {day0:.0f} (since 1972-01-01); observed gradient "
              f"{site['nominal']['gradient_observed_K_per_m']:.2f} K/m; 3.4: p {site['nominal']['global_3p4']['p']:.1g}; "
              f"temperatures only {site['nominal']['temperature_only']['kd_mW']:.2f} "
              f"{site['nominal']['temperature_only']['interval95_mW']}", flush=True)
        for dTs in STEPS_K:
            case = {}
            for surf in ("surface_lowered", "surface_as_measured"):   # adopted last: the case summary below is its
                ts_obs = jf.TS_OBS[s] - (dTs if surf == "surface_lowered" else 0.0)
                A, kd = A0, kd0
                for it in range(2):                             # delta at the nominal point, then at the refit
                    dist = disturbance(A, kd, dTs)
                    A, kd = fit(Tobs - dist["delta_K"], ts_obs)
                case[surf] = dict(A=A, kd_mW=kd, d_kd_mW=kd - kd0, d_A=A - A0,
                                  gradient_observed_corrected_K_per_m=grad(Tobs - dist["delta_K"]),
                                  temperature_only=fit_temperature_only(Tobs - dist["delta_K"], ts_obs),
                                  global_3p4=global_test(Tobs - dist["delta_K"], ts_obs))
            obs_rate = np.array([w[2] for w in wins])
            case.update(A_darkened=dist["A_darkened"], surface_step_K=dist["surface_step_K"],
                        delta_K=dict(zip([w[3] for w in wins], dist["delta_K"].round(4).tolist())),
                        delta_range_K=[float(dist["delta_K"].min()), float(dist["delta_K"].max())],
                        model_rate_K_per_yr=dist["rate_K_per_yr"].round(4).tolist(),
                        observed_trailing_slope_K_per_yr=obs_rate.round(4).tolist(),
                        median_rate_ratio_model_over_observed=float(np.median(dist["rate_K_per_yr"] / obs_rate)))
            site["cases"][f"step_{dTs:g}K"] = case
            print(f"  step {dTs:.1f} K (realized {case['surface_step_K']:.2f} K, A {A0:.4f} -> {case['A_darkened']:.4f}): "
                  f"delta {case['delta_range_K'][0]:.2f}-{case['delta_range_K'][1]:.2f} K; "
                  f"K_d {case['surface_as_measured']['kd_mW']:.2f} ({case['surface_as_measured']['d_kd_mW']:+.2f}), "
                  f"surface lowered {case['surface_lowered']['kd_mW']:.2f} ({case['surface_lowered']['d_kd_mW']:+.2f}); "
                  f"A {case['surface_as_measured']['A']:.4f}; model/observed warming rate {case['median_rate_ratio_model_over_observed']:.2f}; "
                  f"corrected gradient {case['surface_as_measured']['gradient_observed_corrected_K_per_m']:.2f} K/m; "
                  f"3.4: p {case['surface_as_measured']['global_3p4']['p']:.1g}; temperatures only "
                  f"{case['surface_as_measured']['temperature_only']['kd_mW']:.2f} "
                  f"[{case['surface_as_measured']['temperature_only']['interval95_mW'][0]:.2f}, "
                  f"{case['surface_as_measured']['temperature_only']['interval95_mW'][1]:.2f}]",
                  flush=True)
        out["sites"][s] = site
    out["meta"]["runtime_s"] = round(time.time() - t0, 1)
    p = _REPO / "results" / "transient_warming.json"
    p.write_text(json.dumps(out, indent=1))
    print(f"wrote {p.relative_to(_REPO)} in {time.time()-t0:.0f} s")


if __name__ == "__main__":
    main()
