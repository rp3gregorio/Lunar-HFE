"""Headline metrics and internal checks of the joint (A, K_d) retrieval (audit 2026-10-05).

At the joint best fit of each site (compute_joint_albedo_fit.py, with the
diffusivity), and at the global K_d = 3.4 with its own fitted albedo:
  * meter-scale-sensor RMSE, mean bias, offset-removed misfit (the residual
    standard deviation: what is left once the level is matched), the model
    gradient across the retained band against the observed one, and the
    diurnal-mean surface temperature (Table 1 of the letter);
  * the Martinez & Siegler (2021) forward model at the fitted albedo;
  * the hold-out test: refit without the deepest retained sensor, predict it;
  * the thermometer-type split: refit on the gradient-bridge (TG) and
    ring-bridge (TR) sensors alone (surface and diffusivity terms kept);
  * the residuals of the global value at the shallowest and deepest
    retained sensors (the depth trend of the misfit);
  * the forward-drift bound: each sensor's T_eq carried forward at its own
    trailing slope for 1 and 2 yr (compute_common_epoch.py rows), refit;
  * the basal flux at which the model gradient at the fitted point equals
    the observed one (if results/joint_fit_sensitivities.json is present,
    from its Q_b variants);
  * the fixed-albedo sensitivity to a uniform +-1 K bias of the T_eq
    (temperatures only, albedo held at the joint fit; letter Sec. 3.3);
  * the published global K_d values -- 3.4 (Hayne et al. 2017), 3.8 (Feng et
    al. 2020) and 7 (Vasavada et al. 2012, whose radiative term differs, so
    only indicative) -- scored by Delta-AICc against the joint fit, each with
    its own fitted albedo (profile of J over the albedo).

Reads:  results/joint_albedo_fit.json, results/joint_albedo_fit_cache.npz,
        results/joint_fit_sensitivities.json (optional)
Writes: results/joint_fit_checks.json
Runtime: ~1 min (two Martinez solves).

Run with:
    python pipeline/compute/compute_joint_fit_checks.py
"""
from __future__ import annotations
import json, sys, pathlib, copy
_REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO)); sys.path.insert(0, str(_REPO / "src")); sys.path.insert(0, str(_REPO / "pipeline" / "compute"))

import numpy as np
import compute_joint_albedo_fit as jf


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


def main():
    import retrieve_kd as rk
    from lunar.config import SITES
    res = json.loads((_REPO / "results" / "joint_albedo_fit.json").read_text())
    c = np.load(_REPO / "results" / "joint_albedo_fit_cache.npz")
    sens_p = _REPO / "results" / "joint_fit_sensitivities.json"
    sens = json.loads(sens_p.read_text()) if sens_p.exists() else None
    out = {}
    for s in ("A15", "A17"):
        cfg = SITES[s]
        o = rk.extract_sensor_stability(cfg["mission"], min_depth_cm=cfg["MIN_DEPTH_CM"])
        m = np.asarray(o["deep_mask"], bool)
        z, Tobs = np.asarray(o["depth_cm_all"])[m] / 100.0, np.asarray(o["T_eq_all"])[m]
        stype = np.asarray(o["stype_all"])[m]
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
        # thermometer-type split
        for t in ("TG", "TR"):
            msk = np.array([str(x).strip().upper().startswith(t) for x in stype])
            if msk.sum() >= 3:
                a_t, kd_t = fit_subset(msk)
                site[f"split_{t}"] = dict(n=int(msk.sum()), A=a_t, kd_mW=kd_t * 1e3)
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
        # fixed-albedo sensitivity to a uniform bias (letter Sec. 3.3): temperatures only
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
            se = res["sites"][s]["with_diffusivity"]["best"]["gradient_observed_K_per_m"]
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
