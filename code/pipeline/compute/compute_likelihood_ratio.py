"""Likelihood-ratio tests for the letter's model comparisons (2026-10-07).

The joint-fit objective J (letter Eq. 10) is -2 ln L up to a constant, with
the sensor noise estimated from the residuals. For nested models -- a model
with some parameters held fixed against the same model with them fitted --
the increase in J, Delta J, then follows a chi^2 distribution with as many
degrees of freedom as parameters fixed (Wilks 1938). This is the same rule
that gives the profile-likelihood intervals (Delta J <= 3.84 at 95 %, one
parameter), so a value outside its 95 % interval has p < 0.05.

This script only post-processes stored fits; it solves nothing.
  * per site, the global K_d = 3.4 against the joint fit, each with its own
    fitted albedo (joint_albedo_fit.json: global_test J minus best J), with
    and without the diffusivity; df = 1 (Table 1, Sec. 3.2);
  * per site, the published global values 3.4 (Hayne et al. 2017), 3.8
    (Feng et al. 2020) and 7 (Vasavada et al. 2012, whose radiative term
    differs) read off the profile of J over K_d; df = 1 (Sec. 3.2);
  * pooled over both sites: one shared K_d (df = 1) and the global value
    (df = 2) against separate values per site
    (joint_fit_sensitivities.json, model_comparison; Sec. 3.4);
  * the global value under other radiative coefficients chi and the site
    densities (joint_chi_density.json; Sec. 4.4, SI Table S14). That file keeps
    only Delta-AICc, which is converted back to Delta J exactly:
    Delta J = Delta AICc - [pen(2) - pen(3)], pen(k) = 2k + 2k(k+1)/(N-k-1),
    N = n + 3 (compute_joint_albedo_fit.analyse);
  * the temperature-only fits at a fixed albedo (albedo_sensitivity.json,
    albedo_anchor.json; SI Table S7): Delta J = n ln(RMSE_global^2 / RMSE_fit^2),
    over the admissible treatments of compute_albedo_anchor.py;
  * a stress test of the weakest input: the global value against the joint
    fit with the Langseth et al. (1976) diffusivity uncertainties doubled,
    per site (df = 1) and over both sites (df = 2), recomputed on the cached
    joint-fit grid (grid minima, as in the pooled model comparison; Sec. 3.2);
  * the standard lunar-average albedo 0.12 (Hayne et al. 2017, their Table A1)
    held fixed against the fitted albedo, with the diffusivity, per site
    (df = 1): K_d* along K_d at A = 0.12 (parabola vertex, as in the joint
    fit), the sensor bias and RMSE and the surface mean there (Sec. 3.3);
  * what carries the rejection of the global value: the change of each term of J
    (sensors, surface mean, diffusivity) between the joint best and K_d = 3.4
    with its own albedo, and the test of the diffusivity term alone (Sec. 3.2).

p is the chi^2 survival probability; "sigma" is the two-sided Gaussian
equivalent of p.

Reads:  results/joint_albedo_fit.json, results/joint_albedo_fit_cache.npz,
        results/joint_fit_sensitivities.json, results/joint_chi_density.json,
        results/albedo_sensitivity.json, results/albedo_anchor.json
Writes: results/likelihood_ratio.json
Runtime: < 1 s.

Run with:
    python pipeline/compute/compute_likelihood_ratio.py
"""
from __future__ import annotations
import json, sys, pathlib
_REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO)); sys.path.insert(0, str(_REPO / "src")); sys.path.insert(0, str(_REPO / "pipeline" / "compute"))

import numpy as np
from scipy.stats import chi2, norm
import compute_joint_albedo_fit as jf

PUBLISHED = (("hayne2017", 3.4), ("feng2020", 3.8), ("vasavada2012", 7.0))
A_STANDARD = 0.12          # lunar-average albedo of the standard model (Hayne et al. 2017, Table A1)


def test(dJ, df):
    p = float(chi2.sf(dJ, df))
    return dict(delta_J=float(dJ), df=df, p=p, sigma=float(norm.isf(p / 2)))


def load(name):
    return json.loads((_REPO / "results" / name).read_text())


def main():
    jfit, sens = load("joint_albedo_fit.json"), load("joint_fit_sensitivities.json")
    chid, asens, anchor = load("joint_chi_density.json"), load("albedo_sensitivity.json"), load("albedo_anchor.json")
    out = dict(meta=dict(method="likelihood-ratio test on the objective J (-2 ln L + const); "
                                "Delta J ~ chi^2(df) for nested models (Wilks 1938)"),
               sites={})
    for s in ("A15", "A17"):
        site, n = jfit["sites"][s], jfit["sites"][s]["n_sensors"]
        N = n + 3
        pen = lambda k: 2 * k + 2 * k * (k + 1) / (N - k - 1)
        row = {}
        for mode in ("with_diffusivity", "temperature_only"):
            m = site[mode]
            row[f"global_3p4_{mode}"] = test(m["global_test"]["J"] - m["best"]["J"], 1)
        wd = site["with_diffusivity"]
        Jp, J0 = np.asarray(wd["profile_kd"]["J"]), wd["best"]["J"]
        row["published_global_values"] = {name: dict(kd_mW=v, **test(np.interp(v, jf.KD_GRID * 1e3, Jp) - J0, 1))
                                          for name, v in PUBLISHED}
        # chi sweep and site densities (Delta-AICc -> Delta J)
        cd = chid["sites"][s]
        row["global_3p4_chi_density"] = {k: test(v["delta_aicc_global_minus_fit"] - (pen(2) - pen(3)), 1)
                                         for k, v in cd.items()}
        # temperature-only fits at fixed albedo, admissible treatments only
        ok = lambda c: (abs(c["bias_K"]) <= 1.0 and abs(c["surface_mean_K"] - c["surface_mean_obs_K"]) <= 5.0
                        and not c["at_grid_edge"])
        cases = [c for c in asens["cases"] if c["family"] in ("constant", "angular")] + anchor["published_laws_at_sites"]
        adm = [c for c in cases if c["site"] == s and ok(c)]
        assert len(adm) == anchor["admissible_treatments"][s]["n_cases"], "admissible set differs from albedo_anchor.json"
        dJ = [n * np.log(c["rmse_global_K"] ** 2 / c["rmse_star_K"] ** 2) for c in adm]
        row["global_3p4_fixed_albedo_temperature_only"] = dict(
            n_cases=len(adm), delta_J=[float(min(dJ)), float(max(dJ))],
            p=[test(max(dJ), 1)["p"], test(min(dJ), 1)["p"]])
        out["sites"][s] = row
    # pooled over both sites
    mc = sens["model_comparison"]
    Js, Jsh, Jg = mc["per_site"]["J"], mc["shared"]["J"], mc["global_3p4"]["J"]
    out["pooled"] = dict(N=mc["N"], kd_shared_mW=mc["shared"]["kd_shared_mW"],
                         shared_vs_per_site=test(Jsh - Js, mc["per_site"]["k"] - mc["shared"]["k"]),
                         global_vs_per_site=test(Jg - Js, mc["per_site"]["k"] - mc["global_3p4"]["k"]),
                         global_vs_shared=test(Jg - Jsh, mc["shared"]["k"] - mc["global_3p4"]["k"]))

    # stress test: the diffusivity uncertainties doubled (grid minima, as in the pooled comparison)
    c = np.load(_REPO / "results" / "joint_albedo_fit_cache.npz")
    iG = int(np.argmin(np.abs(jf.KD_GRID - jf.KD_GLOBAL)))
    dbl, tot = {}, 0.0
    for s in ("A15", "A17"):
        z, Tobs = jf.observed(s)
        kobs = np.array([q[2] for q in jf.KAPPA_OBS[s]]); ksig = np.array([q[3] for q in jf.KAPPA_OBS[s]])
        J, _ = jf.objective(c[f"{s}_Tz"], Tobs, c[f"{s}_Ts"], jf.TS_OBS[s], kap=c[f"{s}_kap"], kobs=kobs, ksig=2 * ksig)
        dJ = float(J[:, iG].min() - J.min()); tot += dJ
        dbl[s] = test(dJ, 1)
    dbl["pooled"] = test(tot, 2)
    out["diffusivity_uncertainty_doubled"] = dbl

    # what carries the rejection of the global value (grid minima, as above): the change of each
    # term of J between the joint best and K_d = 3.4 with its own albedo. The diffusivity term
    # alone does not rest on the sensors being independent (Sec. 3.2).
    terms = {}
    for s in ("A15", "A17"):
        z, Tobs = jf.observed(s)
        n = len(Tobs)
        kobs = np.array([q[2] for q in jf.KAPPA_OBS[s]]); ksig = np.array([q[3] for q in jf.KAPPA_OBS[s]])
        parts = dict(sensors=n * np.log(((c[f"{s}_Tz"] - Tobs) ** 2).sum(axis=-1) / n),
                     surface_mean=((c[f"{s}_Ts"] - jf.TS_OBS[s]) / jf.SIGMA_TS) ** 2,
                     diffusivity=(((c[f"{s}_kap"] - kobs) / ksig) ** 2).sum(axis=-1))
        J = sum(parts.values())
        ib = np.unravel_index(int(np.argmin(J)), J.shape)
        ig = (int(np.argmin(J[:, iG])), iG)
        terms[s] = {k: float(v[ig] - v[ib]) for k, v in parts.items()}
        terms[s]["diffusivity_alone"] = test(terms[s]["diffusivity"], 1)
    out["global_3p4_terms"] = terms

    # the standard albedo 0.12 held fixed, with the diffusivity (refined minima, as in the per-site tests)
    ia = int(np.argmin(np.abs(np.asarray(jf.A_GRID) - A_STANDARD)))
    assert abs(jf.A_GRID[ia] - A_STANDARD) < 1e-9, "0.12 is not on the albedo grid"
    K = jf.KD_GRID * 1e3
    std = {}
    for s in ("A15", "A17"):
        z, Tobs = jf.observed(s)
        kobs = np.array([q[2] for q in jf.KAPPA_OBS[s]]); ksig = np.array([q[3] for q in jf.KAPPA_OBS[s]])
        J, _ = jf.objective(c[f"{s}_Tz"], Tobs, c[f"{s}_Ts"], jf.TS_OBS[s], kap=c[f"{s}_kap"], kobs=kobs, ksig=ksig)
        kd, Jk = jf.vertex(K, J[ia], int(np.argmin(J[ia])))
        r = np.array([np.interp(kd, K, c[f"{s}_Tz"][ia, :, i]) for i in range(len(Tobs))]) - Tobs
        J0 = jfit["sites"][s]["with_diffusivity"]["best"]["J"]
        std[s] = dict(A=A_STANDARD, kd_star_mW=float(kd), sensor_bias_K=float(r.mean()),
                      sensor_rmse_K=float(np.sqrt((r ** 2).mean())),
                      surface_mean_K=float(np.interp(kd, K, c[f"{s}_Ts"][ia])), surface_mean_obs_K=jf.TS_OBS[s],
                      fixed_vs_fitted_albedo=test(Jk - J0, 1),
                      global_3p4_at_standard_albedo=test(J[ia, iG] - J0, 2))
        # the standard model exactly as published (A = 0.12, K_d = 3.4), at the grid node (letter Table 1)
        rg = c[f"{s}_Tz"][ia, iG] - Tobs
        std[s]["hayne_as_published"] = dict(
            A=A_STANDARD, kd_mW=float(K[iG]), sensor_rmse_K=float(np.sqrt((rg ** 2).mean())),
            sensor_bias_K=float(rg.mean()), surface_mean_K=float(c[f"{s}_Ts"][ia, iG]),
            kappa_model_1e4_cm2_s=[float(k) for k in c[f"{s}_kap"][ia, iG]],
            vs_joint_fit=test(J[ia, iG] - J0, 2))
    out["standard_albedo_0p12"] = std

    f = lambda t: f"dJ {t['delta_J']:6.2f} (df {t['df']}) p {t['p']:.2g} = {t['sigma']:.1f} sigma"
    for s, row in out["sites"].items():
        print(f"{s}: global 3.4 with diffusivity   {f(row['global_3p4_with_diffusivity'])}")
        print(f"     global 3.4 temperatures only  {f(row['global_3p4_temperature_only'])}")
        for k, v in row["published_global_values"].items():
            print(f"     {k:13s} {v['kd_mW']:4.1f}            {f(v)}")
        cd = {k: v for k, v in row["global_3p4_chi_density"].items() if k.startswith("chi_") and k != "chi_1.5"}
        lo = min(cd.values(), key=lambda t: t["delta_J"])
        print(f"     chi 2.2-3.2: dJ {min(t['delta_J'] for t in cd.values()):.1f}-{max(t['delta_J'] for t in cd.values()):.1f},"
              f" largest p {lo['p']:.2g} ({lo['sigma']:.1f} sigma); site densities {f(row['global_3p4_chi_density']['rho_site'])}")
        fa = row["global_3p4_fixed_albedo_temperature_only"]
        print(f"     fixed albedo, temperatures only ({fa['n_cases']} cases): dJ {fa['delta_J'][0]:.2f}-{fa['delta_J'][1]:.2f},"
              f" p {fa['p'][0]:.2g}-{fa['p'][1]:.2g}")
    for k in ("shared_vs_per_site", "global_vs_per_site", "global_vs_shared"):
        print(f"pooled {k:20s} {f(out['pooled'][k])}")
    for k, v in dbl.items():
        print(f"diffusivity uncertainties doubled, {k:6s} {f(v)}")
    for k, v in std.items():
        print(f"A = 0.12 fixed, {k}: K_d* {v['kd_star_mW']:.2f}, sensor bias {v['sensor_bias_K']:+.2f} K,"
              f" RMSE {v['sensor_rmse_K']:.2f} K, surface {v['surface_mean_K']:.1f} K;"
              f" fixed vs fitted albedo {f(v['fixed_vs_fitted_albedo'])}")
    p = _REPO / "results" / "likelihood_ratio.json"
    p.write_text(json.dumps(out, indent=1))
    print(f"wrote {p.relative_to(_REPO)}")


if __name__ == "__main__":
    main()
