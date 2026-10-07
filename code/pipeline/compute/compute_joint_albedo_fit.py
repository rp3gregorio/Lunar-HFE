"""Joint retrieval of the effective albedo and K_d at each site (audit 2026-10-04).

Why
---
At Apollo 17 the sensor temperatures cannot separate the (effective,
constant) Bond albedo A from K_d: a cooler column from a higher albedo is
traded against a higher K_d. A fixed albedo therefore fixes K_d. This script
stops choosing the albedo and FITS it, using in-situ measurements only:

  1. the equilibrium temperatures of the retained meter-scale sensors;
  2. the diurnal-mean surface temperature measured at the site
     (Keihm et al. 1973a,b, as tabulated by Hayne et al. 2017, Table A2):
     211 +- 5 K at A15, 216 +- 5 K at A17;
  3. the annual-wave thermal diffusivities measured at the same probes
     (Langseth et al. 1976, Table 1; x 1e-4 cm^2/s):
     A15 probe 1 (35-138 cm) 0.87 +- 0.07, probe 2 (49-96 cm) 0.74 +- 0.07;
     A17 probe 1 (15-185 cm) 1.00 +- 0.08, probe 2 (16-186 cm) 0.88 +- 0.08.
     These come from how fast the annual wave decays with depth, so they
     constrain the conductivity independently of the absolute temperature
     level, and hence of the albedo. The model diffusivity
     K(T, z) / (rho(z) c_p(T)) is averaged over each probe's depth range on
     the model's own mean-temperature profile.

Two variants are reported:
  "temperature_only"  measurements 1 + 2;
  "with_diffusivity"  measurements 1 + 2 + 3 (the full in-situ set).

Model: the Hayne et al. (2017) form at its published K_s, H, chi, rho, eps,
the Langseth et al. (1976) site Q_b, constant effective albedo A (the
angular-law alternatives are the conditionality of Text S2).

Objective (Gaussian likelihood, sensor variance profiled out, so no sensor
noise scale is chosen by hand):

    J2 = n ln(RSS / n) + ((<T_s> - T_s,obs) / 5 K)^2
    J3 = J2 + sum_probes ((kappa_model - kappa_obs) / sigma_kappa)^2

Outputs per site and variant
  * the best-fit (A*, K_d*), with sensor RMSE, mean bias, gradient, <T_s>,
    model diffusivities;
  * profile likelihoods over K_d and over A, with the Delta J <= 1 and
    <= 3.84 sets (68 / 95 %; union of intervals, since A15 can be bimodal);
  * a bootstrap (N = 1500, seed 42): sensors resampled with replacement with
    the production +-2.5 cm depth jitter, the surface datum and the probe
    diffusivities redrawn from their stated uncertainties;
  * the global-value test with the albedo free in BOTH models: K_d = 3.4 with
    A fitted (k = 2) against (A, K_d) fitted (k = 3);
  * the inter-site contrast from the paired bootstrap draws.

Writes: results/joint_albedo_fit.json, results/joint_albedo_fit_cache.npz (the solved grid)
Runtime: ~25 min on 5 workers (4,700 Hayne fast-path solves); seconds with --reuse.

Run with:
    python pipeline/compute/compute_joint_albedo_fit.py            # solve + analyse
    python pipeline/compute/compute_joint_albedo_fit.py --reuse    # analyse the cached grid
"""
from __future__ import annotations
import json, sys, pathlib, time
from multiprocessing import Pool

_REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO))
sys.path.insert(0, str(_REPO / "src"))
sys.path.insert(0, str(_REPO / "pipeline" / "compute"))

import numpy as np

N_WORKERS = 5
A_GRID = np.round(np.arange(0.115, 0.17501, 0.0025), 4)
KD_GRID = np.unique(np.round(np.concatenate([np.arange(1.0, 24.001, 0.25), [3.4]]), 4)) * 1e-3
KD_GLOBAL = 3.4e-3
KD_CERTIFIED_MAX = 18.5e-3             # flux closure degrades above this (SI, Known imperfections)
Z_DENSE = np.linspace(0.05, 3.0, 200)  # bootstrap interpolation grid (as retrieve_kd)
TS_OBS = {"A15": 211.0, "A17": 216.0}  # Keihm et al. (1973a,b) via Hayne et al. (2017) Table A2
SIGMA_TS = 5.0
# Langseth et al. (1976) Table 1, annual-wave results: (z_top m, z_bottom m, kappa, sigma) [1e-4 cm^2/s]
KAPPA_OBS = {"A15": [(0.35, 1.38, 0.87, 0.07), (0.49, 0.96, 0.74, 0.07)],
             "A17": [(0.15, 1.85, 1.00, 0.08), (0.16, 1.86, 0.88, 0.08)]}
N_BOOT, SEED = 1500, 42


def observed(site):
    import retrieve_kd as rk
    from lunar.config import SITES
    cfg = SITES[site]
    o = rk.extract_sensor_stability(cfg["mission"], min_depth_cm=cfg["MIN_DEPTH_CM"])
    m = np.asarray(o["deep_mask"], bool)
    return np.asarray(o["depth_cm_all"])[m] / 100.0, np.asarray(o["T_eq_all"])[m]


def solve_row(job):
    """All K_d at one (site, A): sensor-depth T, dense profile, <T_s>, probe diffusivities, closure.

    job = (site, A) or (site, A, overrides). Overrides (all optional): Q_b [W m^-2],
    K_s, rho_d, H, chi (Hayne inputs), cp_scale (c_p multiplied by this factor; the
    heat equation and the diffusivity see only rho*c_p, so it is applied by scaling
    the whole rho(z) profile), kd_grid [W m^-1 K^-1], and law = "keihm"
    with constants a, b, in which case A is the normal-incidence A0 of
    A(theta) = A0 + a (theta/45 deg)^3 + b (theta/90 deg)^8.
    """
    site, A = job[0], job[1]
    ov = job[2] if len(job) > 2 else {}
    from lunar.config import SITES, GRID, DT_STEP, HAYNE, T_LUNAR, EQ_Z_ANCHOR, EQ_N_INNER, EQ_MAX_OUTER, EQ_ANCHOR_TOL
    from lunar.constants import RHO_SURFACE, RHO_DEEP
    from lunar.grid import make_geometric_grid
    from lunar.solver import periodic_time_grid, standard_insolation
    from lunar.properties import conductivity_hayne, specific_heat, density_hayne
    from lunar.equilibrium import solve_periodic_equilibrium
    cfg = SITES[site]
    qb = ov.get("Q_b", cfg["Q_BASAL"])
    ks, H, chi = ov.get("K_s", HAYNE["K_S"]), ov.get("H", HAYNE["H"]), ov.get("chi", HAYNE["CHI"])
    rho_d = ov.get("rho_d", RHO_DEEP)
    kd_grid = np.asarray(ov.get("kd_grid", KD_GRID), dtype=float)
    z, _ = observed(site)
    G = make_geometric_grid(**GRID)
    t = periodic_time_grid(DT_STEP)
    S = standard_insolation(cfg["lat"], t)
    if ov.get("law") == "keihm":
        mu = np.cos(np.deg2rad(cfg["lat"])) * np.cos(2 * np.pi * t / T_LUNAR)
        th = np.arccos(np.clip(mu, 0.0, 1.0))
        Ath = A + ov["a"] * (th / (np.pi / 4)) ** 3 + ov["b"] * (th / (np.pi / 2)) ** 8
        insol, alb = (1.0 - np.clip(Ath, 0.0, 1.0)) * S, 0.0
    else:
        insol, alb = S, float(A)
    s_cp = float(ov.get("cp_scale", 1.0))
    rho_s_e, rho_d_e = RHO_SURFACE * s_cp, rho_d * s_cp          # rho*c_p scaling (see docstring)
    rho = density_hayne(G.z_mid, rho_s=rho_s_e, rho_d=rho_d_e, H=H)
    rho_func = (None if not ({"rho_d", "H", "cp_scale"} & set(ov))
                else (lambda zz: density_hayne(zz, rho_s=rho_s_e, rho_d=rho_d_e, H=H)))
    nK, probes = len(kd_grid), KAPPA_OBS[site]
    Tz, prof = np.empty((nK, len(z))), np.empty((nK, len(Z_DENSE)))
    Ts, clos, kap = np.empty(nK), np.empty(nK), np.empty((nK, len(probes)))
    for k, kd in enumerate(kd_grid):
        eq = solve_periodic_equilibrium(
            grid=G, t=t, insolation=insol, albedo=alb, emissivity=cfg["emissivity"], Q_b=qb,
            K_func=lambda T, zz, _k=float(kd): conductivity_hayne(T, zz, Ks=ks, Kd=_k, H=H, chi=chi),
            cp_func=lambda T: specific_heat(T, model="hayne"), rho_func=rho_func, T_guess=cfg["T_MEAN_EFF"],
            z_anchor=EQ_Z_ANCHOR, n_inner=EQ_N_INNER, max_outer=EQ_MAX_OUTER, anchor_tol_K=EQ_ANCHOR_TOL,
            hayne_params=(ks, float(kd), H, chi, rho_s_e, rho_d_e))
        Tz[k] = np.interp(z, G.z_mid, eq.T_mean)
        prof[k] = np.interp(Z_DENSE, G.z_mid, eq.T_mean)
        Ts[k], clos[k] = float(eq.out.T_surface.mean()), float(eq.flux_closure)
        Kz = conductivity_hayne(eq.T_mean, G.z_mid, Ks=ks, Kd=float(kd), H=H, chi=chi)
        kz = Kz / (rho * specific_heat(eq.T_mean, model="hayne")) * 1e8          # [1e-4 cm^2/s]
        for p, (z1, z2, _, _) in enumerate(probes):
            zz = np.linspace(z1, z2, 200)
            kap[k, p] = float(np.interp(zz, G.z_mid, kz).mean())                 # depth-averaged
    return site, float(A), Tz, prof, Ts, clos, kap


def vertex(x, y, i):
    """3-point parabola vertex at grid index i (clamped to its bracket)."""
    if i <= 0 or i >= len(x) - 1:
        return float(x[i]), float(y[i])
    xs, ys = x[i - 1:i + 2], y[i - 1:i + 2]
    d = (xs[0] - xs[1]) * (xs[0] - xs[2]) * (xs[1] - xs[2])
    a = (xs[2] * (ys[1] - ys[0]) + xs[1] * (ys[0] - ys[2]) + xs[0] * (ys[2] - ys[1])) / d
    b = (xs[2] ** 2 * (ys[0] - ys[1]) + xs[1] ** 2 * (ys[2] - ys[0]) + xs[0] ** 2 * (ys[1] - ys[2])) / d
    c = ys[1] - a * xs[1] ** 2 - b * xs[1]
    if a <= 0:
        return float(xs[1]), float(ys[1])
    v = min(max(-b / (2 * a), xs[0]), xs[2])
    return float(v), float(a * v * v + b * v + c)


def objective(Tmodel, Tobs, Ts, ts_obs, kap=None, kobs=None, ksig=None):
    """J over the grid; Tmodel (..., n), Ts (...), kap (..., P)."""
    n = Tobs.shape[-1]
    rss = ((Tmodel - Tobs) ** 2).sum(axis=-1)
    J = n * np.log(rss / n) + ((Ts - ts_obs) / SIGMA_TS) ** 2
    if kap is not None:
        J = J + (((kap - kobs) / ksig) ** 2).sum(axis=-1)
    return J, rss


def best_point(J, a_grid=None, kd_grid=None):
    """Grid minimum refined by 1-D parabolas along K_d then A."""
    a_grid = A_GRID if a_grid is None else a_grid
    kd_grid = KD_GRID if kd_grid is None else kd_grid
    ia, ik = np.unravel_index(int(np.argmin(J)), J.shape)
    kd, _ = vertex(kd_grid, J[ia], ik)
    a, _ = vertex(a_grid, J[:, ik], ia)
    return float(a), float(kd), int(ia), int(ik)


def level_sets(x, prof, levels=(1.0, 3.84)):
    """Union of x-intervals where prof - min <= level (linear interpolation at the crossings)."""
    d = prof - prof.min()
    out = {}
    for L in levels:
        inside = d <= L
        segs, i = [], 0
        while i < len(x):
            if inside[i]:
                j = i
                while j + 1 < len(x) and inside[j + 1]:
                    j += 1
                lo = x[i] if i == 0 else x[i - 1] + (L - d[i - 1]) / (d[i] - d[i - 1]) * (x[i] - x[i - 1])
                hi = x[j] if j == len(x) - 1 else x[j] + (L - d[j]) / (d[j + 1] - d[j]) * (x[j + 1] - x[j])
                segs.append([float(lo), float(hi)])
                i = j + 1
            else:
                i += 1
        out[f"dJ<={L}"] = segs
    return out


def aicc(J, k, N):
    return J + 2 * k + 2 * k * (k + 1) / (N - k - 1)


def analyse(s, z, Tobs, Tz, prof, Ts, clos, kap, use_kappa, a_grid=None, kd_grid=None, n_boot=None,
            ts_obs=None, kappa_obs=None):
    a_grid = A_GRID if a_grid is None else a_grid
    kd_grid = KD_GRID if kd_grid is None else kd_grid
    n_boot = N_BOOT if n_boot is None else n_boot
    ts_obs = TS_OBS[s] if ts_obs is None else ts_obs
    n, probes = len(z), (KAPPA_OBS[s] if kappa_obs is None else kappa_obs)
    kobs = np.array([p[2] for p in probes]); ksig = np.array([p[3] for p in probes])
    kw = dict(kap=kap, kobs=kobs, ksig=ksig) if use_kappa else {}
    J, rss = objective(Tz, Tobs, Ts, ts_obs, **kw)
    a_best, kd_best, ia, ik = best_point(J, a_grid, kd_grid)
    r = Tz[ia, ik] - Tobs
    ols = lambda TT: float(np.polyfit(z, TT, 1)[0])
    prof_K, prof_A = J.min(axis=0), J.min(axis=1)
    iG = int(np.argmin(np.abs(kd_grid - KD_GLOBAL)))
    iaG = int(np.argmin(J[:, iG]))
    aG, JG = vertex(a_grid, J[:, iG], iaG)
    _, Jbest = vertex(kd_grid, J[ia], ik)
    N = n + 1 + (len(probes) if use_kappa else 0)
    out = dict(
        best=dict(A=a_best, kd_star_mW=kd_best * 1e3, J=Jbest,
                  sensor_rmse_K=float(np.sqrt(np.mean(r ** 2))), bias_K=float(r.mean()),
                  surface_mean_K=float(Ts[ia, ik]), surface_mean_obs_K=ts_obs,
                  gradient_model_K_per_m=ols(Tz[ia, ik]), gradient_observed_K_per_m=ols(Tobs),
                  kappa_model=kap[ia, ik].tolist(), kappa_obs=kobs.tolist(),
                  flux_closure=float(clos[ia, ik]), above_certified_kd=bool(kd_best > KD_CERTIFIED_MAX)),
        profile_kd=dict(J=prof_K.tolist(), sets_mW=level_sets(kd_grid * 1e3, prof_K)),
        profile_A=dict(J=prof_A.tolist(), sets=level_sets(a_grid, prof_A)),
        global_test=dict(A_fitted=aG, J=JG, sensor_rmse_K=float(np.sqrt(rss[iaG, iG] / n)),
                         surface_mean_K=float(Ts[iaG, iG]), gradient_model_K_per_m=ols(Tz[iaG, iG]),
                         kappa_model=kap[iaG, iG].tolist(), delta_aicc_global_minus_fit=float(aicc(JG, 2, N) - aicc(Jbest, 3, N))),
        J_map=J.tolist())
    # sensors: the production bootstrap stream (seed 42 per site); surface and
    # diffusivity data: an independent stream PER SITE, so the two sites'
    # measurement perturbations are not correlated in the paired contrast
    rng = np.random.default_rng(SEED)
    rng_d = np.random.default_rng([SEED, 1, ("A15", "A17").index(s)])
    if n_boot == 0:
        return out
    kb, ab = np.empty(n_boot), np.empty(n_boot)
    for b in range(n_boot):
        idx = rng.integers(0, n, size=n)
        dz = rng.normal(0.0, _DEPTH_SIGMA_M, size=n)
        zj = z[idx] + dz[idx]
        j0 = np.clip(np.searchsorted(Z_DENSE, zj) - 1, 0, len(Z_DENSE) - 2)
        w = (zj - Z_DENSE[j0]) / (Z_DENSE[j0 + 1] - Z_DENSE[j0])
        Tm = prof[..., j0] * (1 - w) + prof[..., j0 + 1] * w
        ts_b = ts_obs + rng_d.normal(0.0, SIGMA_TS)
        kb_obs = kobs + rng_d.normal(0.0, 1.0, size=len(kobs)) * ksig
        kwb = dict(kap=kap, kobs=kb_obs, ksig=ksig) if use_kappa else {}
        Jb, _ = objective(Tm, Tobs[idx], Ts, ts_b, **kwb)
        ab[b], kb[b], _, _ = best_point(Jb, a_grid, kd_grid)
    pct = lambda v: dict(zip(("p2.5", "p16", "p50", "p84", "p97.5"), np.percentile(v, [2.5, 16, 50, 84, 97.5]).tolist()))
    out["bootstrap"] = dict(kd_mW=pct(kb * 1e3), A=pct(ab), samples_kd_mW=(kb * 1e3).tolist(), samples_A=ab.tolist(),
                            frac_above_certified=float(np.mean(kb > KD_CERTIFIED_MAX)))
    return out


from lunar.config import DEPTH_SIGMA_CM as _DEPTH_SIGMA_CM
_DEPTH_SIGMA_M = _DEPTH_SIGMA_CM / 100.0


def main():
    t0 = time.time()
    cache = _REPO / "results" / "joint_albedo_fit_cache.npz"
    names = ("Tz", "prof", "Ts", "clos", "kap")
    rows = {}
    if "--reuse" in sys.argv and cache.exists():
        c = np.load(cache)
        assert np.allclose(c["A_grid"], A_GRID) and np.allclose(c["kd_grid"], KD_GRID), "cache grid differs"
        for s in ("A15", "A17"):
            for i, A in enumerate(A_GRID):
                rows[(s, float(A))] = tuple(c[f"{s}_{nm}"][i] for nm in names)
        print(f"reused the solved grid from {cache.relative_to(_REPO)}", flush=True)
    else:
        jobs = [(s, A) for s in ("A15", "A17") for A in A_GRID]
        print(f"{len(jobs)} rows x {len(KD_GRID)} K_d = {len(jobs)*len(KD_GRID)} solves on {N_WORKERS} workers", flush=True)
        with Pool(N_WORKERS) as pool:
            for r in pool.imap_unordered(solve_row, jobs):
                rows[(r[0], r[1])] = r[2:]
                print(f"  {r[0]} A={r[1]:.4f} done ({len(rows)}/{len(jobs)}, {time.time()-t0:.0f} s)", flush=True)
        np.savez_compressed(cache, A_grid=A_GRID, kd_grid=KD_GRID,
                            **{f"{s}_{nm}": np.stack([rows[(s, float(A))][i] for A in A_GRID])
                               for s in ("A15", "A17") for i, nm in enumerate(names)})
    out = dict(meta=dict(
        purpose="joint (A, K_d) retrieval per site from in-situ measurements only (audit 2026-10-04)",
        objective={"temperature_only": "n ln(RSS/n) + ((<Ts>-Ts_obs)/5 K)^2",
                   "with_diffusivity": "temperature_only + sum_probes ((kappa_model-kappa_obs)/sigma)^2"},
        ts_obs_K=TS_OBS, sigma_ts_K=SIGMA_TS, kappa_obs_langseth1976_table1=KAPPA_OBS,
        A_grid=A_GRID.tolist(), kd_grid_mW=(KD_GRID * 1e3).tolist(), kd_certified_max_mW=KD_CERTIFIED_MAX * 1e3,
        n_boot=N_BOOT, seed=SEED, depth_jitter_cm=_DEPTH_SIGMA_M * 100), sites={}, contrast={})
    boots = {v: {} for v in ("temperature_only", "with_diffusivity")}
    for s in ("A15", "A17"):
        z, Tobs = observed(s)
        stack = lambda i: np.stack([rows[(s, float(A))][i] for A in A_GRID])
        Tz, prof, Ts, clos, kap = (stack(i) for i in range(5))
        out["sites"][s] = dict(n_sensors=len(z), maps=dict(surface_mean_K=Ts.tolist(), flux_closure=clos.tolist(),
                                                           kappa_model=kap.tolist()))
        for v, use in (("temperature_only", False), ("with_diffusivity", True)):
            res = analyse(s, z, Tobs, Tz, prof, Ts, clos, kap, use)
            out["sites"][s][v] = res
            boots[v][s] = np.array(res["bootstrap"]["samples_kd_mW"])
            b, bb, g = res["best"], res["bootstrap"]["kd_mW"], res["global_test"]
            print(f"\n{s} [{v}]: A* = {b['A']:.4f}, K_d* = {b['kd_star_mW']:.2f}  (RMSE {b['sensor_rmse_K']:.3f} K, bias {b['bias_K']:+.2f} K, "
                  f"<Ts> {b['surface_mean_K']:.1f} vs {TS_OBS[s]:.0f}, gradient {b['gradient_model_K_per_m']:.2f} vs "
                  f"{b['gradient_observed_K_per_m']:.2f} K/m, kappa {np.round(b['kappa_model'], 2).tolist()} vs {b['kappa_obs']})", flush=True)
            print(f"    profile K_d sets: {res['profile_kd']['sets_mW']}", flush=True)
            print(f"    profile A sets:   {res['profile_A']['sets']}", flush=True)
            print(f"    bootstrap K_d: median {bb['p50']:.2f}, 68% [{bb['p16']:.2f}, {bb['p84']:.2f}], 95% [{bb['p2.5']:.2f}, {bb['p97.5']:.2f}]; "
                  f"A median {res['bootstrap']['A']['p50']:.4f} [{res['bootstrap']['A']['p2.5']:.4f}, {res['bootstrap']['A']['p97.5']:.4f}]", flush=True)
            print(f"    global 3.4 with A fitted (A={g['A_fitted']:.4f}): RMSE {g['sensor_rmse_K']:.3f} K, gradient "
                  f"{g['gradient_model_K_per_m']:.2f}, kappa {np.round(g['kappa_model'], 2).tolist()}; dAICc = {g['delta_aicc_global_minus_fit']:+.1f}", flush=True)
    for v in boots:
        c = boots[v]["A17"] - boots[v]["A15"]
        out["contrast"][v] = dict(median=float(np.median(c)), p2_5=float(np.percentile(c, 2.5)),
                                  p97_5=float(np.percentile(c, 97.5)), p_leq0=float(np.mean(c <= 0)))
        print(f"\ncontrast A17-A15 [{v}]: median {out['contrast'][v]['median']:+.2f}, 95% [{out['contrast'][v]['p2_5']:+.2f}, "
              f"{out['contrast'][v]['p97_5']:+.2f}], P(<=0) = {out['contrast'][v]['p_leq0']:.4f}", flush=True)
    out["meta"]["runtime_s"] = round(time.time() - t0, 1)
    p = _REPO / "results" / "joint_albedo_fit.json"
    p.write_text(json.dumps(out))
    print(f"wrote {p.relative_to(_REPO)} in {time.time() - t0:.0f} s")


if __name__ == "__main__":
    main()
