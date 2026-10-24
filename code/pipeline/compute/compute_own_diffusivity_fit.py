"""Joint fit with our own annual-wave diffusivities (2026-10-12).

The joint (A, K_d) fit (compute_joint_albedo_fit.py, letter Sec. 3.1) takes the
annual-wave diffusivities of Langseth et al. (1976, Table 1). This script
repeats it with the diffusivities we measured ourselves in the full restored
record (compute_annual_wave.py, uniform_kappa: Langseth's uniform-medium method
applied to our amplitudes and to our delays), as a robustness check that the
result does not rest on the published values:

  * Langseth et al. (1976), as adopted (reproduces joint_albedo_fit.json);
  * our amplitudes, with our bootstrap standard errors (Langseth's method);
  * our amplitudes, with Langseth's uncertainties (0.07 / 0.08);
  * our delays, with our standard errors;
  * the mean of amplitudes and delays, with half their difference as the
    uncertainty (or the larger standard error, if that is bigger).

Our probes span the same depths as Langseth's to within 1 cm (A15 35-139 and
49-97 cm, A17 14-185 and 15-186 cm), so the model diffusivity is averaged over
Langseth's ranges, as in the adopted fit. Only kappa_obs and sigma change; the
solved grid is reused and nothing is solved again. For each variant: the best
fit, its bootstrap 95 % interval (same seeds as the joint fit), the global
K_d = 3.4 tested against it (Delta J, df = 1, Wilks 1938) and the paired
A17 - A15 contrast.

Reads:  results/joint_albedo_fit_cache.npz, results/annual_wave.json
Writes: results/own_diffusivity_fit.json
Runtime: ~15 s.

Run with:
    python pipeline/compute/compute_own_diffusivity_fit.py
"""
from __future__ import annotations
import json, sys, pathlib
_REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO)); sys.path.insert(0, str(_REPO / "src")); sys.path.insert(0, str(_REPO / "pipeline" / "compute"))

import numpy as np
from scipy.stats import chi2
import compute_joint_albedo_fit as jf

SITES = ("A15", "A17")
PROBES = ("p1", "p2")


def own(uk, s, kind, sigma=None):
    """(z_top, z_bottom, kappa, sigma) per probe from our uniform-medium diffusivities."""
    rows = []
    for i, p in enumerate(PROBES):
        z1, z2, _, sig_l = jf.KAPPA_OBS[s][i]
        a, d = uk[s][p]["amplitude"], uk[s][p]["phase"]
        if kind == "mean":
            k, sg = (a["kappa"] + d["kappa"]) / 2, max(abs(a["kappa"] - d["kappa"]) / 2, a["se"], d["se"])
        else:
            src = a if kind == "amplitude" else d
            k, sg = src["kappa"], (src["se"] if sigma is None else sig_l)
        rows.append((z1, z2, float(k), float(sg)))
    return rows


def main():
    c = np.load(_REPO / "results" / "joint_albedo_fit_cache.npz")
    assert np.allclose(c["A_grid"], jf.A_GRID) and np.allclose(c["kd_grid"], jf.KD_GRID), "cache grid differs"
    uk = {s: json.loads((_REPO / "results" / "annual_wave.json").read_text())["sites"][s]["uniform_kappa"] for s in SITES}
    variants = {
        "langseth1976": lambda s: [tuple(p) for p in jf.KAPPA_OBS[s]],
        "own_amplitude": lambda s: own(uk, s, "amplitude"),
        "own_amplitude_langseth_sigma": lambda s: own(uk, s, "amplitude", sigma="langseth"),
        "own_phase": lambda s: own(uk, s, "phase"),
        "own_mean_amplitude_phase": lambda s: own(uk, s, "mean"),
    }
    out = dict(meta=dict(purpose="joint (A, K_d) fit with our own annual-wave diffusivities in place of Langseth et al. (1976)",
                         kappa_units="1e-4 cm^2 s^-1", global_test="Delta J = J(K_d=3.4, A refitted) - J(best), df = 1",
                         n_boot=jf.N_BOOT, seed=jf.SEED), variants={})
    data = {}
    for s in SITES:
        z, Tobs = jf.observed(s)
        data[s] = (z, Tobs) + tuple(c[f"{s}_{nm}"] for nm in ("Tz", "prof", "Ts", "clos", "kap"))
    for v, f in variants.items():
        row, boots = {}, {}
        for s in SITES:
            ko = f(s)
            r = jf.analyse(s, *data[s], True, kappa_obs=ko)
            b, g, bk = r["best"], r["global_test"], r["bootstrap"]["kd_mW"]
            dJ = g["J"] - b["J"]
            boots[s] = np.array(r["bootstrap"]["samples_kd_mW"])
            row[s] = dict(kappa_obs=[p[2] for p in ko], sigma=[p[3] for p in ko], A=b["A"], kd_star_mW=b["kd_star_mW"],
                          kd_p2_5=bk["p2.5"], kd_p97_5=bk["p97.5"], sensor_rmse_K=b["sensor_rmse_K"],
                          surface_mean_K=b["surface_mean_K"],
                          global_3p4=dict(delta_J=float(dJ), df=1, p=float(chi2.sf(dJ, 1))))
        d = boots["A17"] - boots["A15"]
        row["contrast_mW"] = dict(best=row["A17"]["kd_star_mW"] - row["A15"]["kd_star_mW"], median=float(np.median(d)),
                                  p2_5=float(np.percentile(d, 2.5)), p97_5=float(np.percentile(d, 97.5)),
                                  p_leq0=float(np.mean(d <= 0)))
        out["variants"][v] = row
        print(f"\n{v}")
        for s in SITES:
            x = row[s]
            print(f"  {s}: kappa {np.round(x['kappa_obs'], 3).tolist()} +- {np.round(x['sigma'], 3).tolist()} -> A {x['A']:.4f}, "
                  f"K_d {x['kd_star_mW']:.2f} [{x['kd_p2_5']:.2f}, {x['kd_p97_5']:.2f}], RMSE {x['sensor_rmse_K']:.2f} K; "
                  f"global 3.4: dJ {x['global_3p4']['delta_J']:.1f}, p {x['global_3p4']['p']:.2g}")
        k = row["contrast_mW"]
        print(f"  A17 - A15: {k['best']:+.2f} (bootstrap median {k['median']:+.2f}, 95% [{k['p2_5']:+.2f}, {k['p97_5']:+.2f}],"
              f" P(<=0) {k['p_leq0']:.3f})")
    p = _REPO / "results" / "own_diffusivity_fit.json"
    p.write_text(json.dumps(out, indent=1))
    print(f"\nwrote {p.relative_to(_REPO)}")


if __name__ == "__main__":
    main()
