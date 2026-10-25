"""Headline metrics and internal checks of the joint (A, K_d) retrieval.

At the joint best fit of each site (compute_joint_albedo_fit.py, with the
diffusivity), and at the global K_d = 3.4 with its own fitted albedo:
  * meter-scale-sensor RMSE, mean bias, offset-removed misfit (the residual
    standard deviation: what is left once the level is matched), the model
    gradient across the retained band against the observed one, and the
    diurnal-mean surface temperature (Table 1 of the letter, Secs. 3.1, 3.2);
  * the Martinez & Siegler (2021) forward model at the fitted albedo, with the
    density profile of the Hayne runs (H = 6 cm; Table 1) and with their own
    H = 5.6 cm (text above their Eq. 10), applied to the conductivity and to rho*c_p;
  * the hold-out test: refit without the deepest retained sensor, predict it;
  * the other published surface mean: 207 K at Apollo 15 in Langseth & Keihm
    (1977, Table 1) against the 211 K used (Keihm et al. 1973a, via Hayne et al.
    2017, Table A2); refit with it (both give 216 K at Apollo 17);
  * the thermometer-type split: refit on the gradient-bridge (TG) and
    ring-bridge (TR) sensors alone (surface and diffusivity terms kept);
  * the probe split: refit on the sensors of one probe alone, where it has at
    least 3 below the cut (A15 probe 1, i.e. probe 2 left out; A17 probes 1 and 2);
  * the residuals of the global value at the shallowest and deepest
    retained sensors (the depth trend of the misfit);
  * each sensor minus the joint fit, with its probe, thermometer type and the
    year its stability window ends, and the offsets between probes and between
    thermometer types at matched depths (letter Sec. 4.2; Fig. 3);
  * the forward-drift bound: each sensor's T_eq carried forward at its own
    trailing slope for 1 and 2 yr (compute_common_epoch.py rows), refit;
  * the basal flux at which the model gradient at the fitted point equals
    the observed one (if results/joint_fit_sensitivities.json is present,
    from its Q_b variants);
  * the fixed-albedo sensitivity to a uniform +-1 K bias of the T_eq
    (temperatures only, albedo held at the joint fit);
  * the published global K_d values -- 3.4 (Hayne et al. 2017), 3.8 (Feng et
    al. 2020) and 7 (Vasavada et al. 2012, whose radiative term differs, so
    only indicative) -- scored by Delta-AICc against the joint fit, each with
    its own fitted albedo (profile of J over the albedo).

Reads:  results/joint_albedo_fit.json, results/joint_albedo_fit_cache.npz, results/stability_windows.json,
        results/joint_fit_sensitivities.json (optional)
Writes: results/joint_fit_checks.json
Runtime: ~4 min (four Martinez solves and the subset refits).

Run with:
    python pipeline/compute/compute_joint_fit_checks.py
"""
from __future__ import annotations
import json, sys, pathlib, copy
_REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO)); sys.path.insert(0, str(_REPO / "src")); sys.path.insert(0, str(_REPO / "pipeline" / "compute"))

import numpy as np
import compute_joint_albedo_fit as jf


MS_H_PUBLISHED = 0.056   # Martinez & Siegler (2021): H changed from 6.0 to 5.6 cm (text above their Eq. 10)


def martinez_with_H(cfg, H):
    """Martinez & Siegler K(T, rho) with the density scale height H in both the
    conductivity and rho*c_p (run_with uses the Hayne profile, H = 6 cm)."""
    import functools
    from lunar.config import GRID, DT_STEP, EQ_Z_ANCHOR, EQ_N_INNER, EQ_MAX_OUTER, EQ_ANCHOR_TOL
    from lunar.grid import make_geometric_grid
    from lunar.solver import periodic_time_grid, standard_insolation
    from lunar.properties import conductivity_martinez, density_hayne, specific_heat
    from lunar.equilibrium import solve_periodic_equilibrium
    g = make_geometric_grid(**GRID); t = periodic_time_grid(DT_STEP)
    rho_f = functools.partial(density_hayne, H=H)
    eq = solve_periodic_equilibrium(
        grid=g, t=t, insolation=standard_insolation(cfg["lat"], t), albedo=cfg["albedo"],
        emissivity=cfg["emissivity"], Q_b=cfg["Q_BASAL"],
        K_func=lambda T, z: conductivity_martinez(T, rho=rho_f(np.asarray(z, dtype=float))),
        cp_func=functools.partial(specific_heat, model="hayne"), rho_func=rho_f,
        T_guess=cfg["T_MEAN_EFF"], z_anchor=EQ_Z_ANCHOR, n_inner=EQ_N_INNER,
        max_outer=EQ_MAX_OUTER, anchor_tol_K=EQ_ANCHOR_TOL)
    return g.z_mid, eq.T_mean


# mean surface temperature in the final report of the experiment (Langseth & Keihm 1977, Table 1)
TS_LANGSETH1977 = {"A15": 207.0, "A17": 216.0}


def bilinear(field, a, kd):
    """Interpolate a (nA, nK, ...) field at (a, kd)."""
    A, K = jf.A_GRID, jf.KD_GRID
    i = int(np.clip(np.searchsorted(A, a) - 1, 0, len(A) - 2)); j = int(np.clip(np.searchsorted(K, kd) - 1, 0, len(K) - 2))
    u = (a - A[i]) / (A[i + 1] - A[i]); v = (kd - K[j]) / (K[j + 1] - K[j])
    return ((1 - u) * (1 - v) * field[i, j] + u * (1 - v) * field[i + 1, j]
            + (1 - u) * v * field[i, j + 1] + u * v * field[i + 1, j + 1])


def metrics(z, Tm, Tobs, Ts=None):
    r = Tm - Tobs
    ols = lambda TT: float(np.polyfit(z, TT, 1)[0])
    out = dict(rmse_K=float(np.sqrt(np.mean(r ** 2))), bias_K=float(r.mean()), offset_removed_K=float(r.std()),
               gradient_model_K_per_m=ols(Tm), gradient_observed_K_per_m=ols(Tobs))
    if Ts is not None:
        out["surface_mean_K"] = float(Ts)
    return out


def sensor_residuals(sensors, resid, window_year):
    """Each sensor minus the joint fit, and the offsets the letter quotes (Sec. 4.2):
    the range of each probe; the mean of each probe and thermometer type; probe 2
    minus probe 1 at matched depths (within 5 cm), by the window year of the pair;
    and TG minus TR within a probe, for pairs averaged in the same year and at most
    12 cm apart."""
    rows = [dict(probe=int(x["probe"]), sensor=str(x["sensor"]), type=str(x["stype"]).strip().upper()[:2],
                 depth_cm=float(x["depth_cm"]), year=window_year[(x["probe"], x["sensor"])], residual_K=float(r))
            for x, r in zip(sensors, resid)]
    out = dict(sensors=rows, probe_range_K={}, type_mean_K={}, probe2_minus_probe1_K={}, tg_minus_tr_same_year_K=[])
    for pr in (1, 2):
        v = [r["residual_K"] for r in rows if r["probe"] == pr]
        out["probe_range_K"][f"probe{pr}"] = [min(v), max(v)]
        for ty in ("TG", "TR"):
            w = [r["residual_K"] for r in rows if r["probe"] == pr and r["type"] == ty]
            if w:
                out["type_mean_K"][f"probe{pr}_{ty}"] = float(np.mean(w))
    for r2 in (r for r in rows if r["probe"] == 2):
        p1 = [r for r in rows if r["probe"] == 1 and abs(r["depth_cm"] - r2["depth_cm"]) <= 5]
        if p1:
            r1 = min(p1, key=lambda r: abs(r["depth_cm"] - r2["depth_cm"]))
            key = r2["year"] if r1["year"] == r2["year"] else f"{r1['year']}/{r2['year']}"
            out["probe2_minus_probe1_K"].setdefault(key, []).append(
                dict(depth_cm=[r1["depth_cm"], r2["depth_cm"]], diff_K=r2["residual_K"] - r1["residual_K"]))
    for tr in (r for r in rows if r["type"] == "TR"):
        tg = [r for r in rows if r["type"] == "TG" and r["probe"] == tr["probe"] and r["year"] == tr["year"]
              and abs(r["depth_cm"] - tr["depth_cm"]) <= 12]
        if tg:
            g = min(tg, key=lambda r: abs(r["depth_cm"] - tr["depth_cm"]))
            out["tg_minus_tr_same_year_K"].append(dict(probe=tr["probe"], year=tr["year"],
                                                       depth_cm=[g["depth_cm"], tr["depth_cm"]],
                                                       diff_K=g["residual_K"] - tr["residual_K"]))
    return out


def main():
    import retrieve_kd as rk
    from lunar.config import SITES
    res = json.loads((_REPO / "results" / "joint_albedo_fit.json").read_text())
    c = np.load(_REPO / "results" / "joint_albedo_fit_cache.npz")
    sens_p = _REPO / "results" / "joint_fit_sensitivities.json"
    sens = json.loads(sens_p.read_text()) if sens_p.exists() else None
    win = json.loads((_REPO / "results" / "stability_windows.json").read_text())
    out = {}
    for s in ("A15", "A17"):
        cfg = SITES[s]
        o = rk.extract_sensor_stability(cfg["mission"], min_depth_cm=cfg["MIN_DEPTH_CM"])
        m = np.asarray(o["deep_mask"], bool)
        z, Tobs = np.asarray(o["depth_cm_all"])[m] / 100.0, np.asarray(o["T_eq_all"])[m]
        stype = np.asarray(o["stype_all"])[m]
        probe = np.asarray([x["probe"] for x in o["sensors"]])[m]   # same order as the *_all arrays
        Tz, prof, Ts, clos, kap = (c[f"{s}_{k}"] for k in ("Tz", "prof", "Ts", "clos", "kap"))
        site = {}
        for v in ("with_diffusivity", "temperature_only"):
            b = res["sites"][s][v]["best"]
            site[f"fit_{v}"] = dict(A=b["A"], kd_mW=b["kd_star_mW"],
                                     **metrics(z, bilinear(Tz, b["A"], b["kd_star_mW"] * 1e-3), Tobs,
                                               bilinear(Ts, b["A"], b["kd_star_mW"] * 1e-3)),
                                     kappa_model=bilinear(kap, b["A"], b["kd_star_mW"] * 1e-3).tolist())
        # effective conductivity at the retained sensors (contact x radiative factor), joint fit
        from lunar.config import HAYNE
        from lunar.properties import conductivity_hayne
        bj = res["sites"][s]["with_diffusivity"]["best"]
        Tj = bilinear(Tz, bj["A"], bj["kd_star_mW"] * 1e-3)
        Keff = conductivity_hayne(Tj, z, Ks=HAYNE["K_S"], Kd=bj["kd_star_mW"] * 1e-3, H=HAYNE["H"], chi=HAYNE["CHI"])
        site["effective_conductivity_mW"] = dict(mean=float(Keff.mean() * 1e3), radiative_factor=float((Keff / (bj["kd_star_mW"] * 1e-3)).mean()))
        # each sensor minus the joint fit, by probe, thermometer type and window year
        year = {(r["probe"], r["sensor"]): int(r["window_end"][:4]) for r in win[s]}
        deep = [x for x, keep in zip(o["sensors"], m) if keep]
        site["sensor_residuals"] = sensor_residuals(deep, Tobs - Tj, year)
        g = res["sites"][s]["with_diffusivity"]["global_test"]
        rg = bilinear(Tz, g["A_fitted"], 3.4e-3) - Tobs
        i_sh, i_dp = int(np.argmin(z)), int(np.argmax(z))
        site["global_residual_trend"] = dict(shallow_cm=float(z[i_sh] * 100), shallow_K=float(rg[i_sh]),
                                             deep_cm=float(z[i_dp] * 100), deep_K=float(rg[i_dp]))
        site["global_3p4"] = dict(A=g["A_fitted"], kd_mW=3.4,
                                  **metrics(z, bilinear(Tz, g["A_fitted"], 3.4e-3), Tobs, bilinear(Ts, g["A_fitted"], 3.4e-3)),
                                  kappa_model=bilinear(kap, g["A_fitted"], 3.4e-3).tolist())
        # Martinez & Siegler (2021) forward at the fitted albedo
        best = res["sites"][s]["with_diffusivity"]["best"]
        cfgA = copy.deepcopy(cfg); cfgA["albedo"] = best["A"]
        zm, Tm = rk.run_with(cfgA, k_model="martinez")
        site["martinez_forward"] = dict(A=best["A"], **metrics(z, np.interp(z, zm, Tm), Tobs))
        zm56, Tm56 = martinez_with_H(cfgA, MS_H_PUBLISHED)
        site["martinez_forward_H5p6"] = dict(A=best["A"], H_m=MS_H_PUBLISHED,
                                             **metrics(z, np.interp(z, zm56, Tm56), Tobs))
        # hold-out: deepest sensor
        kobs = np.array([p[2] for p in jf.KAPPA_OBS[s]]); ksig = np.array([p[3] for p in jf.KAPPA_OBS[s]])
        def fit_subset(mask):
            J, _ = jf.objective(Tz[..., mask], Tobs[mask], Ts, jf.TS_OBS[s], kap=kap, kobs=kobs, ksig=ksig)
            a, kd, _, _ = jf.best_point(J)
            return a, kd
        i_deep = int(np.argmax(z)); keep = np.arange(len(z)) != i_deep
        a_h, kd_h = fit_subset(keep)
        pred = float(bilinear(Tz, a_h, kd_h)[i_deep])
        site["holdout_deepest"] = dict(depth_cm=float(z[i_deep] * 100), A=a_h, kd_mW=kd_h * 1e3,
                                       predicted_K=pred, observed_K=float(Tobs[i_deep]), residual_K=pred - float(Tobs[i_deep]))
        # the other published surface mean (Langseth & Keihm 1977), where it differs
        if TS_LANGSETH1977[s] != jf.TS_OBS[s]:
            J, _ = jf.objective(Tz, Tobs, Ts, TS_LANGSETH1977[s], kap=kap, kobs=kobs, ksig=ksig)
            a_l, kd_l, _, _ = jf.best_point(J)
            site["surface_mean_langseth1977"] = dict(surface_mean_obs_K=TS_LANGSETH1977[s], A=a_l, kd_mW=kd_l * 1e3,
                                                     surface_mean_model_K=float(bilinear(Ts, a_l, kd_l)))
        # thermometer-type split
        for t in ("TG", "TR"):
            msk = np.array([str(x).strip().upper().startswith(t) for x in stype])
            if msk.sum() >= 3:
                a_t, kd_t = fit_subset(msk)
                site[f"split_{t}"] = dict(n=int(msk.sum()), A=a_t, kd_mW=kd_t * 1e3)
        # probe split: the sensors of one probe only (both diffusivities kept); at A15 probe 2
        # has only two sensors below the cut, so "probe 1 only" there is "probe 2 left out"
        for pr in (1, 2):
            msk = probe == pr
            if msk.sum() >= 3:
                a_p, kd_p = fit_subset(msk)
                site[f"probe{pr}_only"] = dict(n=int(msk.sum()), A=a_p, kd_mW=kd_p * 1e3)
        # forward-drift bound (per-sensor trailing slopes from compute_common_epoch.py)
        ep = json.loads((_REPO / "results" / "common_epoch_sensitivity.json").read_text())[s]["sensors"]
        ze = np.array([r["depth_cm"] for r in ep]) / 100.0
        Tc = np.array([r["T_certified"] for r in ep]); sl = np.array([(r["slope_K_yr"] or 0.0) for r in ep])
        from compute_joint_fit_sensitivities import interp_profiles
        for tau in (1.0, 2.0):
            TT = Tc + sl * tau
            J, _ = jf.objective(interp_profiles(prof, ze), TT, Ts, jf.TS_OBS[s], kap=kap, kobs=kobs, ksig=ksig)
            a_d, kd_d, _, _ = jf.best_point(J)
            site[f"drift_forward_{tau:g}yr"] = dict(A=a_d, kd_mW=kd_d * 1e3, observed_gradient_K_per_m=float(np.polyfit(ze, TT, 1)[0]))
        # fixed-albedo sensitivity to a uniform bias (not quoted in the letter): temperatures only
        # (sensors + surface mean, no diffusivity), albedo held at the joint fit, every T_eq
        # shifted by -1, 0 and +1 K
        aj = res["sites"][s]["with_diffusivity"]["best"]["A"]
        ia = int(np.clip(np.searchsorted(jf.A_GRID, aj) - 1, 0, len(jf.A_GRID) - 2))
        u = (aj - jf.A_GRID[ia]) / (jf.A_GRID[ia + 1] - jf.A_GRID[ia])
        Tzi, Tsi = (1 - u) * Tz[ia] + u * Tz[ia + 1], (1 - u) * Ts[ia] + u * Ts[ia + 1]
        kdb = {}
        for d in (-1.0, 0.0, 1.0):
            Jb, _ = jf.objective(Tzi, Tobs + d, Tsi, jf.TS_OBS[s])
            kdb[d] = jf.vertex(jf.KD_GRID, Jb, int(np.argmin(Jb)))[0] * 1e3
        site["fixed_albedo_uniform_bias"] = dict(A=aj, kd_mW={f"{d:+g}K": v for d, v in kdb.items()},
                                                 shift_plus1K_mW=kdb[1.0] - kdb[0.0], shift_minus1K_mW=kdb[-1.0] - kdb[0.0])
        # basal flux that would make the model gradient match the observed one
        if sens is not None:
            from compute_joint_fit_sensitivities import QB, QB_NOMINAL
            pts = [(q, sens["sites"][s]["variants"][f"Qb_{q:g}"]["with_diffusivity"]["gradient_model_K_per_m"]) for q in QB[s]]
            pts.append((QB_NOMINAL[s], site["fit_with_diffusivity"]["gradient_model_K_per_m"]))
            pts.sort()
            q, gm = np.array(pts).T
            p = np.polyfit(gm, q, 1)                      # Q_b as a linear function of the model gradient
            go = site["fit_with_diffusivity"]["gradient_observed_K_per_m"]
            site["qb_matching_observed_gradient"] = dict(points=pts, qb_mW=float(np.polyval(p, go)))
        # published global K_d values against the joint fit, each with its own fitted albedo
        wd = res["sites"][s]["with_diffusivity"]
        Jp, J0, N = np.asarray(wd["profile_kd"]["J"]), wd["best"]["J"], len(z) + 3
        aicc = lambda J, k: J + 2 * k + 2 * k * (k + 1) / (N - k - 1)
        site["published_global_values"] = {
            name: dict(kd_mW=v, delta_aicc=float(aicc(np.interp(v, jf.KD_GRID * 1e3, Jp), 2) - aicc(J0, 3)))
            for name, v in (("hayne2017", 3.4), ("feng2020", 3.8), ("vasavada2012", 7.0))}
        out[s] = site
        f = site["fit_with_diffusivity"]
        print(f"{s}: joint A={f['A']:.4f} K_d={f['kd_mW']:.2f} RMSE {f['rmse_K']:.3f} bias {f['bias_K']:+.2f} "
              f"offset-removed {f['offset_removed_K']:.3f} grad {f['gradient_model_K_per_m']:.2f}/{f['gradient_observed_K_per_m']:.2f} Ts {f['surface_mean_K']:.1f}")
        gg = site["global_3p4"]
        print(f"     global 3.4 (A={gg['A']:.4f}): RMSE {gg['rmse_K']:.3f} bias {gg['bias_K']:+.2f} offset-removed {gg['offset_removed_K']:.3f} "
              f"grad {gg['gradient_model_K_per_m']:.2f}")
        mm = site["martinez_forward"]
        print(f"     Martinez forward (A={mm['A']:.4f}): RMSE {mm['rmse_K']:.3f} bias {mm['bias_K']:+.2f} grad {mm['gradient_model_K_per_m']:.2f}")
        h = site["holdout_deepest"]
        print(f"     hold-out {h['depth_cm']:.0f} cm: K_d {h['kd_mW']:.2f}, predicted {h['predicted_K']:.2f} vs {h['observed_K']:.2f} ({h['residual_K']:+.2f} K)")
        for t in ("TG", "TR"):
            if f"split_{t}" in site:
                print(f"     {t} only (n={site[f'split_{t}']['n']}): K_d {site[f'split_{t}']['kd_mW']:.2f}, A {site[f'split_{t}']['A']:.4f}")
        for pr in (1, 2):
            if f"probe{pr}_only" in site:
                q = site[f"probe{pr}_only"]
                print(f"     probe {pr} sensors only (n={q['n']}): K_d {q['kd_mW']:.2f}, A {q['A']:.4f}")
        sr = site["sensor_residuals"]
        print("     sensor minus joint fit, range by probe: " + ", ".join(f"{k} {v[0]:+.2f}..{v[1]:+.2f}" for k, v in sr["probe_range_K"].items())
              + "; mean by probe and type: " + ", ".join(f"{k} {v:+.2f}" for k, v in sr["type_mean_K"].items()))
        for y, pairs in sr["probe2_minus_probe1_K"].items():
            print(f"     probe 2 minus probe 1 at matched depths ({y}): " + ", ".join(f"{q['diff_K']:+.2f}" for q in pairs))
        if sr["tg_minus_tr_same_year_K"]:
            print("     TG minus TR, same probe and year: " + ", ".join(f"{q['diff_K']:+.2f}" for q in sr["tg_minus_tr_same_year_K"]))
        print(f"     effective K at the sensors: {site['effective_conductivity_mW']['mean']:.2f} mW/m/K (factor {site['effective_conductivity_mW']['radiative_factor']:.3f})")
        gt = site["global_residual_trend"]
        print(f"     global residuals: {gt['shallow_K']:+.2f} K at {gt['shallow_cm']:.0f} cm -> {gt['deep_K']:+.2f} K at {gt['deep_cm']:.0f} cm")
        for tau in (1, 2):
            dd = site[f"drift_forward_{tau}yr"]
            print(f"     forward drift {tau} yr: K_d {dd['kd_mW']:.2f}, A {dd['A']:.4f}, observed gradient {dd['observed_gradient_K_per_m']:+.2f}")
        if "qb_matching_observed_gradient" in site:
            print(f"     Q_b matching the observed gradient: {site['qb_matching_observed_gradient']['qb_mW']:.1f} mW/m2")
        fb = site["fixed_albedo_uniform_bias"]
        print(f"     fixed albedo {fb['A']:.4f}, temperatures only: uniform +1 K -> {fb['shift_plus1K_mW']:+.2f}, -1 K -> {fb['shift_minus1K_mW']:+.2f} mW/m/K")
        print("     published global values, dAICc vs joint fit: "
              + ", ".join(f"{k} {v['kd_mW']:g}: {v['delta_aicc']:+.1f}" for k, v in site["published_global_values"].items()))
    p = _REPO / "results" / "joint_fit_checks.json"
    p.write_text(json.dumps(out, indent=1))
    print(f"wrote {p.relative_to(_REPO)}")


if __name__ == "__main__":
    main()
