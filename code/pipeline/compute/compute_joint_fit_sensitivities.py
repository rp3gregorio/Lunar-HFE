"""Error budget and sensitivities of the joint (A, K_d) retrieval (audit 2026-10-05).

The joint retrieval (compute_joint_albedo_fit.py) fits the effective albedo
and K_d at each site to three in-situ measurements: the meter-scale sensor
temperatures, the measured diurnal-mean surface temperature, and the
annual-wave diffusivities of Langseth et al. (1976). This script supplies its
error budget and robustness tests.

Re-solved variants (compact grid: A 0.105-0.165 / A0 0.03-0.11 in 0.0025,
K_d 2-12 in 0.5 mW plus 3.4; vertex-refined):
  * Q_b: A15 {14, 16, 18.5, 23.5, 25}, A17 {10, 12, 14, 18} mW m^-2
    (with the nominal fit, the direct contrast map over the envelope);
  * K_s x 0.7 / 1.3;  rho_d 1700 / 2000 kg m^-3;  c_p x 0.97 / 1.03;
  * conditionality: H 3 / 10 cm, chi 1.5, and the albedo FORM (the Keihm
    angular law with the constants of Vasavada et al. 2012 and of Hayne et
    al. 2017, normal-incidence A0 fitted);
  * the nominal set on the compact grid (grid-coarseness check).
Re-analysed on the nominal fine grid (no new solves; the model profile is
interpolated at the variant's sensor depths):
  * borestem cut z_b 70 / 90 cm;
  * stability-window slope threshold 0.04-0.16 K/yr;
  * the other two window-selector choices: scan floor 35-75 % and fallback
    start 60-80 % of the samples (compute_window_criteria_sensitivity.py);
  * common-1974 equilibrium temperatures (compute_common_epoch.py).
Model comparison on the nominal fine grid: per-site K_d, one shared K_d, and
the global 3.4, each with the albedo of each site fitted.

Reads:  results/joint_albedo_fit.json, results/joint_albedo_fit_cache.npz,
        results/common_epoch_sensitivity.json
Writes: results/joint_fit_sensitivities.json (+ _cache.npz)
Runtime: ~80 min on 5 workers; seconds with --reuse.

Run with:
    python pipeline/compute/compute_joint_fit_sensitivities.py [--reuse]
"""
from __future__ import annotations
import json, sys, pathlib, time
from multiprocessing import Pool

_REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO))
sys.path.insert(0, str(_REPO / "src"))
sys.path.insert(0, str(_REPO / "pipeline" / "compute"))

import numpy as np
import compute_joint_albedo_fit as jf

N_WORKERS = 5
A_V = np.round(np.arange(0.105, 0.16501, 0.0025), 4)
A0_V = np.round(np.arange(0.030, 0.11001, 0.0025), 4)
KD_V = np.unique(np.round(np.concatenate([np.arange(2.0, 12.001, 0.5), [3.4]]), 4)) * 1e-3
QB = {"A15": [14.0, 16.0, 18.5, 23.5, 25.0], "A17": [10.0, 12.0, 14.0, 18.0]}
QB_NOMINAL = {"A15": 21.0, "A17": 16.0}
LAWS = {"form_vasavada2012": (0.045, 0.14), "form_hayne2017": (0.06, 0.25)}
# c_p envelope +-3 %: covers all five samples of Hemingway et al. (1973, Table 6:
# soils, breccia, basalt; -1.7 to +2.6 % about the Hayne polynomial at 240-260 K)
CP_SCALES = (0.97, 1.03)
SIGMA_SOLVER = 0.04                    # grid & dt convergence (unchanged; compute_error_budget.py)


def variants():
    v = []
    for s in ("A15", "A17"):
        v.append((s, "nominal_compact", {}, A_V))
        for q in QB[s]:
            v.append((s, f"Qb_{q:g}", {"Q_b": q * 1e-3}, A_V))
        for f in (0.7, 1.3):
            v.append((s, f"Ks_x{f:g}", {"K_s": jf_hayne("K_S") * f}, A_V))
        for r in (1700.0, 2000.0):
            v.append((s, f"rho_d_{r:g}", {"rho_d": r}, A_V))
        for h in (0.03, 0.10):
            v.append((s, f"H_{h:g}", {"H": h}, A_V))
        v.append((s, "chi_1.5", {"chi": 1.5}, A_V))
        for name, (a, b) in LAWS.items():
            v.append((s, name, {"law": "keihm", "a": a, "b": b}, A0_V))
    # appended after both sites so the cache indices of the variants above stay fixed
    for s in ("A15", "A17"):
        for f in CP_SCALES:
            v.append((s, f"cp_x{f:g}", {"cp_scale": f}, A_V))
    return v


def jf_hayne(key):
    from lunar.config import HAYNE
    return HAYNE[key]


def solve_all(var, which=None):
    jobs, index = [], []
    which = range(len(var)) if which is None else which
    for vi in which:
        s, name, ov, agrid = var[vi]
        for A in agrid:
            jobs.append((s, float(A), dict(ov, kd_grid=KD_V.tolist())))
            index.append((vi, float(A)))
    print(f"{len(which)} site-variants, {len(jobs)} rows x {len(KD_V)} K_d = {len(jobs)*len(KD_V)} solves", flush=True)
    rows, t0 = {}, time.time()
    with Pool(N_WORKERS) as pool:
        for k, r in enumerate(pool.imap(jf.solve_row, jobs, chunksize=1)):
            rows[index[k]] = r[2:]
            if (k + 1) % 25 == 0 or k + 1 == len(jobs):
                print(f"  {k+1}/{len(jobs)} rows ({time.time()-t0:.0f} s)", flush=True)
    return rows


def fit(s, z, Tobs, Tz, prof, Ts, clos, kap, agrid, kgrid, use_kappa=True, **kw):
    r = jf.analyse(s, z, Tobs, Tz, prof, Ts, clos, kap, use_kappa, a_grid=agrid, kd_grid=kgrid, n_boot=0, **kw)
    b = r["best"]
    edge = bool(b["kd_star_mW"] <= kgrid[0] * 1e3 + 1e-9 or b["kd_star_mW"] >= kgrid[-1] * 1e3 - 1e-9
                or b["A"] <= agrid[0] + 1e-9 or b["A"] >= agrid[-1] - 1e-9)
    return dict(A=b["A"], kd_star_mW=b["kd_star_mW"], at_grid_edge=edge, sensor_rmse_K=b["sensor_rmse_K"],
                bias_K=b["bias_K"], surface_mean_K=b["surface_mean_K"], kappa_model=b["kappa_model"],
                gradient_model_K_per_m=b["gradient_model_K_per_m"], J=b["J"],
                delta_aicc_global_minus_fit=r["global_test"]["delta_aicc_global_minus_fit"])


def interp_profiles(prof, z):
    j0 = np.clip(np.searchsorted(jf.Z_DENSE, z) - 1, 0, len(jf.Z_DENSE) - 2)
    w = (z - jf.Z_DENSE[j0]) / (jf.Z_DENSE[j0 + 1] - jf.Z_DENSE[j0])
    return prof[..., j0] * (1 - w) + prof[..., j0 + 1] * w


def half(v):
    return 0.5 * (max(v) - min(v))


def main():
    t0 = time.time()
    var = variants()
    cache = _REPO / "results" / "joint_fit_sensitivities_cache.npz"
    names = ("Tz", "prof", "Ts", "clos", "kap")
    missing = []
    if "--reuse" in sys.argv and cache.exists():
        c = np.load(cache, allow_pickle=False)
        rows = {}
        for vi, (s, name, ov, agrid) in enumerate(var):
            if f"v{vi}_Tz" not in c.files:
                missing.append(vi)
                continue
            for i, A in enumerate(agrid):
                rows[(vi, float(A))] = tuple(c[f"v{vi}_{nm}"][i] for nm in names)
        print(f"reused {cache.relative_to(_REPO)}; solving {len(missing)} new site-variants", flush=True)
        if missing:
            rows.update(solve_all(var, missing))
    else:
        rows = solve_all(var)
    if "--reuse" not in sys.argv or missing:
        np.savez_compressed(cache, **{f"v{vi}_{nm}": np.stack([rows[(vi, float(A))][i] for A in agrid])
                                      for vi, (s, name, ov, agrid) in enumerate(var) for i, nm in enumerate(names)})
    out = dict(meta=dict(purpose="error budget and sensitivities of the joint (A, K_d) retrieval (audit 2026-10-05)",
                         A_grid=A_V.tolist(), A0_grid=A0_V.tolist(), kd_grid_mW=(KD_V * 1e3).tolist()),
               sites={}, error_budget={}, qb_contrast_map={}, model_comparison={})
    nominal = json.loads((_REPO / "results" / "joint_albedo_fit.json").read_text())
    fine = np.load(_REPO / "results" / "joint_albedo_fit_cache.npz")
    epoch = json.loads((_REPO / "results" / "common_epoch_sensitivity.json").read_text())
    from compute_stability_threshold_sensitivity import deep_obs_at_threshold, THRESHOLDS_K_PER_YR
    from compute_window_criteria_sensitivity import (deep_obs as window_obs, SWEEPS as WINDOW_SWEEPS,
                                                     ADOPTED as WINDOW_ADOPTED)
    import retrieve_kd as rk
    from lunar.config import SITES
    kq = {}
    for s in ("A15", "A17"):
        z, Tobs = jf.observed(s)
        site = dict(variants={}, reanalysis={})
        for vi, (vs, name, ov, agrid) in enumerate(var):
            if vs != s:
                continue
            st = lambda i: np.stack([rows[(vi, float(A))][i] for A in agrid])
            Tz, prof, Ts, clos, kap = (st(i) for i in range(5))
            site["variants"][name] = dict(with_diffusivity=fit(s, z, Tobs, Tz, prof, Ts, clos, kap, agrid, KD_V, True),
                                          temperature_only=fit(s, z, Tobs, Tz, prof, Ts, clos, kap, agrid, KD_V, False))
            w = site["variants"][name]["with_diffusivity"]
            print(f"  {s} {name:20s} A*={w['A']:.4f} K_d*={w['kd_star_mW']:6.2f}{' EDGE' if w['at_grid_edge'] else '     '} "
                  f"RMSE {w['sensor_rmse_K']:.3f} <Ts> {w['surface_mean_K']:.1f} kappa {np.round(w['kappa_model'], 2).tolist()}", flush=True)
        # re-analyses on the nominal fine grid
        Ff = lambda nm: fine[f"{s}_{nm}"]
        prof_f, Ts_f, clos_f, kap_f = Ff("prof"), Ff("Ts"), Ff("clos"), Ff("kap")
        cfg = SITES[s]
        def refit(zz, TT):
            return fit(s, zz, TT, interp_profiles(prof_f, zz), prof_f, Ts_f, clos_f, kap_f, jf.A_GRID, jf.KD_GRID, True)
        for zb in (70, 90):
            o = rk.extract_sensor_stability(cfg["mission"], min_depth_cm=zb)
            m = np.asarray(o["deep_mask"], bool)
            site["reanalysis"][f"zb_{zb}"] = refit(np.asarray(o["depth_cm_all"])[m] / 100.0, np.asarray(o["T_eq_all"])[m])
        for thr in THRESHOLDS_K_PER_YR:
            zz, TT, _ = deep_obs_at_threshold(cfg["mission"], cfg["MIN_DEPTH_CM"], thr)
            site["reanalysis"][f"thr_{thr:g}"] = refit(np.asarray(zz, float), np.asarray(TT, float))
        for knob in ("floor", "fallback"):               # the other two window-selector choices
            for val in WINDOW_SWEEPS[knob]:
                if val == WINDOW_ADOPTED[knob]:
                    continue
                kw = {k: WINDOW_ADOPTED[k] for k in ("slope", "floor", "fallback")}
                kw[knob] = val
                zz, TT, _ = window_obs(cfg["mission"], cfg["MIN_DEPTH_CM"], **kw)
                site["reanalysis"][f"{knob}_{val:g}"] = refit(zz, TT)
        rws = epoch[s]["sensors"]
        ze = np.array([r["depth_cm"] for r in rws]) / 100.0
        for key in ("T_certified", "T_common"):
            site["reanalysis"][f"epoch_{key}"] = refit(ze, np.array([r[key] for r in rws]))
        for k, v in site["reanalysis"].items():
            print(f"  {s} {k:20s} A*={v['A']:.4f} K_d*={v['kd_star_mW']:6.2f}", flush=True)
        # error budget (with_diffusivity)
        nom = nominal["sites"][s]["with_diffusivity"]
        k0 = nom["best"]["kd_star_mW"]
        V = {k: v["with_diffusivity"]["kd_star_mW"] for k, v in site["variants"].items()}
        R = {k: v["kd_star_mW"] for k, v in site["reanalysis"].items()}
        qvals = [V[f"Qb_{q:g}"] for q in QB[s]] + [k0]
        kq[s] = {**{q: V[f"Qb_{q:g}"] for q in QB[s]}, QB_NOMINAL[s]: k0}
        bs = nom["bootstrap"]["kd_mW"]
        sig = dict(sigma_stat=0.5 * (bs["p84"] - bs["p16"]), sigma_solver=SIGMA_SOLVER,
                   sigma_Qb=half(qvals), sigma_Ks=half([V["Ks_x0.7"], V["Ks_x1.3"]]),
                   sigma_rho=half([V["rho_d_1700"], V["rho_d_2000"]]),
                   sigma_cp=half([V[f"cp_x{f:g}"] for f in CP_SCALES]),
                   sigma_zb=half([R["zb_70"], k0, R["zb_90"]]),
                   sigma_thr=half([R[f"thr_{t:g}"] for t in THRESHOLDS_K_PER_YR]),
                   sigma_window=half([k0] + [v for k, v in R.items() if k.startswith(("floor_", "fallback_"))]),
                   sigma_epoch=abs(R["epoch_T_common"] - R["epoch_T_certified"]))
        total = float(np.sqrt(sum(x ** 2 for x in sig.values())))
        out["error_budget"][s] = dict(**sig, total_quadrature=total, kd_star_mW=k0,
                                      Qb_asym_up_down=[max(qvals) - k0, min(qvals) - k0],
                                      conditional=dict(H=half([V["H_0.03"], V["H_0.1"], k0]),
                                                       chi_1p5_kd_mW=V["chi_1.5"],
                                                       chi_1p5_edge=site["variants"]["chi_1.5"]["with_diffusivity"]["at_grid_edge"],
                                                       albedo_form_kd_mW={k: V[k] for k in LAWS}),
                                      grid_check_compact_vs_fine=V["nominal_compact"] - k0)
        print(f"\n  {s} error budget: " + ", ".join(f"{k} {v:.2f}" for k, v in sig.items()) + f" -> total {total:.2f}", flush=True)
        out["sites"][s] = site
    # direct contrast map over the Q_b envelope
    q15, q17 = sorted(kq["A15"]), sorted(kq["A17"])
    grid = [[kq["A17"][b] - kq["A15"][a] for b in q17] for a in q15]
    out["qb_contrast_map"] = dict(qb_A15=q15, qb_A17=q17, contrast_mW=grid,
                                  min=float(np.min(grid)), max=float(np.max(grid)))
    print(f"\n  contrast over the Q_b envelope: {np.min(grid):+.2f} .. {np.max(grid):+.2f}", flush=True)
    # model comparison on the nominal fine grid (albedo fitted per site in every model)
    Js, Ns = {}, 0
    for s in ("A15", "A17"):
        z, Tobs = jf.observed(s)
        kob = [p[2] for p in jf.KAPPA_OBS[s]]; ksg = [p[3] for p in jf.KAPPA_OBS[s]]
        J, _ = jf.objective(fine[f"{s}_Tz"], Tobs, fine[f"{s}_Ts"], jf.TS_OBS[s], kap=fine[f"{s}_kap"],
                            kobs=np.array(kob), ksig=np.array(ksg))
        Js[s] = J.min(axis=0)                                  # profile over A at each K_d
        Ns += len(z) + 1 + len(kob)
    J_sep = float(Js["A15"].min() + Js["A17"].min())
    J_shared_curve = Js["A15"] + Js["A17"]
    ish = int(np.argmin(J_shared_curve))
    iG = int(np.argmin(np.abs(jf.KD_GRID - jf.KD_GLOBAL)))
    aic = lambda J, k: J + 2 * k + 2 * k * (k + 1) / (Ns - k - 1)
    models = dict(per_site=dict(J=J_sep, k=6), shared=dict(J=float(J_shared_curve[ish]), k=5,
                                                           kd_shared_mW=float(jf.KD_GRID[ish] * 1e3)),
                  global_3p4=dict(J=float(J_shared_curve[iG]), k=4))
    best = min(aic(m["J"], m["k"]) for m in models.values())
    for m in models.values():
        m["AICc"] = float(aic(m["J"], m["k"])); m["dAICc"] = m["AICc"] - best
    out["model_comparison"] = dict(models, N=Ns)
    print("  model comparison: " + ", ".join(f"{k} dAICc {v['dAICc']:+.1f}" for k, v in models.items()), flush=True)
    out["meta"]["runtime_s"] = round(time.time() - t0, 1)
    p = _REPO / "results" / "joint_fit_sensitivities.json"
    p.write_text(json.dumps(out, indent=1))
    print(f"wrote {p.relative_to(_REPO)} in {time.time()-t0:.0f} s")


if __name__ == "__main__":
    main()
