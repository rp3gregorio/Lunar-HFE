"""K_d from each probe and each thermometer type on its own (letter Secs. 3.1, 3.2; Table 1, Fig. 3).

The joint (A, K_d) fit of compute_joint_albedo_fit.py is repeated on subsets of
the meter-scale sensors of each site, with the same objective J, the same solved
grid (results/joint_albedo_fit_cache.npz) and the same 1500-draw bootstrap:

  * each probe on its own, as if it were a borehole of its own: that probe's
    sensors, the measured surface mean, and that probe's annual-wave
    diffusivity (Langseth et al. 1976, Table 1);
  * each thermometer type on its own (gradient bridge TG, ring bridge TR): the
    sensors of that type in both probes, the surface mean and both
    diffusivities;
  * all the sensors (the joint fit itself, recomputed here as a check).

A subset with fewer than three sensors (A15 probe 2 has two below the 80 cm
cut) cannot fix both the albedo and K_d; for it the albedo is held at the
all-sensor value of the site (the solved grid interpolated linearly in A) and
only K_d is fitted. For every subset the global K_d = 3.4 is also tested
(likelihood ratio, the albedo refitted where it is free; df = 1).

Reads:  results/joint_albedo_fit.json, results/joint_albedo_fit_cache.npz, the Apollo record
Writes: results/subset_fits.json
Runtime: about 1 min (no new model runs).

Run with:
    python pipeline/compute/compute_subset_fits.py
"""
from __future__ import annotations
import json, sys, time, pathlib
_REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO)); sys.path.insert(0, str(_REPO / "src")); sys.path.insert(0, str(_REPO / "pipeline" / "compute"))

import numpy as np
from scipy.stats import chi2
import compute_joint_albedo_fit as jf

MIN_FREE = 3      # fewer sensors than this: albedo held at the all-sensor value


def _aicc(J, k, N):
    """jf.analyse also stores a Delta-AICc (not used in the letter), undefined for N <= k + 1
    (A15 probe 2: two sensors); return NaN there instead of dividing by zero."""
    return J + 2 * k + 2 * k * (k + 1) / (N - k - 1) if N - k - 1 > 0 else float("nan")


jf.aicc = _aicc


def sensor_table(site):
    """Probe, thermometer type and depth of each meter-scale sensor, in the order of jf.observed."""
    import retrieve_kd as rk
    from lunar.config import SITES
    cfg = SITES[site]
    o = rk.extract_sensor_stability(cfg["mission"], min_depth_cm=cfg["MIN_DEPTH_CM"])
    m = np.asarray(o["deep_mask"], bool)
    sens = [x for x, keep in zip(o["sensors"], m) if keep]
    return (np.array([int(x["probe"]) for x in sens]),
            np.array([str(x["stype"]).strip().upper()[:2] for x in sens]),
            [str(x["sensor"]) for x in sens])


def rows_at(arr, a, a_grid):
    """arr (nA, ...) linearly interpolated to albedo a, as a (1, ...) array."""
    i = int(np.clip(np.searchsorted(a_grid, a) - 1, 0, len(a_grid) - 2))
    u = (a - a_grid[i]) / (a_grid[i + 1] - a_grid[i])
    return ((1 - u) * arr[i] + u * arr[i + 1])[None]


def at_fit(Tz, a, kd, a_grid):
    """Model temperatures at the refined fit (a, kd): linear in K_d, then in A (the misfit
    of Table 2 of the letter is evaluated the same way, compute_joint_fit_checks.bilinear)."""
    K = jf.KD_GRID
    j = int(np.clip(np.searchsorted(K, kd) - 1, 0, len(K) - 2)); v = (kd - K[j]) / (K[j + 1] - K[j])
    along_k = lambda row: (1 - v) * row[j] + v * row[j + 1]
    if len(a_grid) == 1:
        return along_k(Tz[0])
    i = int(np.clip(np.searchsorted(a_grid, a) - 1, 0, len(a_grid) - 2)); u = (a - a_grid[i]) / (a_grid[i + 1] - a_grid[i])
    return (1 - u) * along_k(Tz[i]) + u * along_k(Tz[i + 1])


def fit_subset(s, mask, probes, c, a_fixed=None):
    """jf.analyse on the sensors in mask and the diffusivities of the listed probes."""
    z_all, T_all = jf.observed(s)
    Tz, prof, Ts, clos, kap = (c[f"{s}_{k}"] for k in ("Tz", "prof", "Ts", "clos", "kap"))
    Tz, kap = Tz[..., mask], kap[..., probes]
    a_grid = jf.A_GRID
    if a_fixed is not None:
        Tz, prof, Ts, clos, kap = (rows_at(x, a_fixed, jf.A_GRID) for x in (Tz, prof, Ts, clos, kap))
        a_grid = np.array([a_fixed])
    res = jf.analyse(s, z_all[mask], T_all[mask], Tz, prof, Ts, clos, kap, True, a_grid=a_grid,
                     kappa_obs=[jf.KAPPA_OBS[s][p] for p in probes])
    b, bt, g = res["best"], res["bootstrap"], res["global_test"]
    dJ = float(g["J"] - b["J"])
    r = at_fit(Tz, b["A"], b["kd_star_mW"] * 1e-3, a_grid) - T_all[mask]       # misfit at the refined fit
    return dict(n_sensors=int(mask.sum()), probes_diffusivity=[int(p) + 1 for p in probes],
                albedo_fixed=a_fixed is not None,
                A=b["A"], kd_mW=b["kd_star_mW"], sensor_rmse_K=float(np.sqrt(np.mean(r ** 2))), bias_K=float(r.mean()),
                surface_mean_K=b["surface_mean_K"], kappa_model=b["kappa_model"], kappa_obs=b["kappa_obs"],
                kd_bootstrap_mW=bt["kd_mW"], A_bootstrap=bt["A"],
                profile_sets_mW=res["profile_kd"]["sets_mW"],
                global_3p4=dict(delta_J=dJ, df=1, p=float(chi2.sf(max(dJ, 0.0), 1))))


def main():
    t0 = time.time()
    c = np.load(_REPO / "results" / "joint_albedo_fit_cache.npz")
    assert np.allclose(c["A_grid"], jf.A_GRID) and np.allclose(c["kd_grid"], jf.KD_GRID), "cache grid differs"
    joint = json.loads((_REPO / "results" / "joint_albedo_fit.json").read_text())["sites"]
    out = dict(meta=dict(purpose="K_d from each probe and each thermometer type on its own (letter Secs. 3.1, 3.2; Fig. 3)",
                         min_sensors_for_free_albedo=MIN_FREE, n_boot=jf.N_BOOT, seed=jf.SEED), sites={})
    for s in ("A15", "A17"):
        probe, stype, names = sensor_table(s)
        a_all = joint[s]["with_diffusivity"]["best"]["A"]
        site = dict(sensors=[dict(name=n_, probe=int(p), type=t) for n_, p, t in zip(names, probe, stype)])
        subsets = [(f"probe{p}", probe == p, [p - 1]) for p in (1, 2)]
        subsets += [(t, stype == t, [0, 1]) for t in ("TG", "TR")]
        subsets += [("all", np.ones(len(probe), bool), [0, 1])]
        for key, mask, probes in subsets:
            r = fit_subset(s, mask, probes, c, a_fixed=None if mask.sum() >= MIN_FREE else a_all)
            site[key] = r
            kb = r["kd_bootstrap_mW"]
            print(f"{s} {key:6s} n={r['n_sensors']:2d} diffusivity of probe(s) {r['probes_diffusivity']}"
                  f"{' (albedo held at %.4f)' % a_all if r['albedo_fixed'] else ''}: A {r['A']:.4f}, K_d {r['kd_mW']:.2f} "
                  f"[{kb['p2.5']:.2f}, {kb['p97.5']:.2f}], RMSE {r['sensor_rmse_K']:.2f} K; "
                  f"global 3.4: dJ {r['global_3p4']['delta_J']:.1f}, p {r['global_3p4']['p']:.1e}", flush=True)
        a_ = site["all"]
        ref = joint[s]["with_diffusivity"]["best"]
        assert abs(a_["kd_mW"] - ref["kd_star_mW"]) < 1e-9 and abs(a_["A"] - ref["A"]) < 1e-12, "all-sensor fit differs from the joint fit"
        out["sites"][s] = site
    out["meta"]["runtime_s"] = round(time.time() - t0, 1)
    p = _REPO / "results" / "subset_fits.json"
    p.write_text(json.dumps(out, indent=1))
    print(f"wrote {p.relative_to(_REPO)} in {time.time() - t0:.0f} s")


if __name__ == "__main__":
    main()
