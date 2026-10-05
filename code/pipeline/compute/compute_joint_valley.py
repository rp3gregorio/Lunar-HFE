"""What the diffusivity adds: the K_d cut through the joint objective at the fitted albedo (2026-10-05).

Holds the albedo at each site's joint-fit value and tabulates, for a set of
K_d, how well the model matches each measurement: the meter-scale sensor
temperatures (RMSE and their term of the objective), the surface mean, and the
two annual-wave diffusivities. This is the letter's worked example (Sec. 3.3,
Table 2): at Apollo 17 the sensor temperatures barely separate K_d = 6 from 7,
while the diffusivity does.

No new solves: the solved grid of compute_joint_albedo_fit.py is interpolated
linearly in A to the fitted albedo.

Reads:  results/joint_albedo_fit.json, results/joint_albedo_fit_cache.npz
Writes: results/joint_valley.json
Runtime: seconds.

Run with:
    python pipeline/compute/compute_joint_valley.py
"""
from __future__ import annotations
import json, sys, pathlib
_REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO)); sys.path.insert(0, str(_REPO / "src")); sys.path.insert(0, str(_REPO / "pipeline" / "compute"))

import numpy as np
import compute_joint_albedo_fit as jf

KD_ROWS_MW = (3.4, 5.0, 6.0, 7.0, 8.0, 10.0)


def at_albedo(arr, A):
    """Linear interpolation of a grid array (n_A, n_K, ...) to albedo A."""
    i = int(np.clip(np.searchsorted(jf.A_GRID, A) - 1, 0, len(jf.A_GRID) - 2))
    w = (A - jf.A_GRID[i]) / (jf.A_GRID[i + 1] - jf.A_GRID[i])
    return arr[i] * (1 - w) + arr[i + 1] * w


def vertex(x, y):
    k = int(np.argmin(y))
    if not 0 < k < len(x) - 1:
        return float(x[k])
    a, b, _ = np.polyfit(x[k - 1:k + 2], y[k - 1:k + 2], 2)
    return float(np.clip(-b / (2 * a), x[k - 1], x[k + 1])) if a > 0 else float(x[k])


def main():
    res = json.loads((_REPO / "results" / "joint_albedo_fit.json").read_text())
    cache = np.load(_REPO / "results" / "joint_albedo_fit_cache.npz")
    K = jf.KD_GRID * 1e3
    out = {}
    for s in ("A15", "A17"):
        A = res["sites"][s]["with_diffusivity"]["best"]["A"]
        z, Tobs = jf.observed(s)
        n = len(Tobs)
        Tz, Ts, kap = (at_albedo(cache[f"{s}_{nm}"], A) for nm in ("Tz", "Ts", "kap"))
        kobs = np.array([p[2] for p in jf.KAPPA_OBS[s]])
        ksig = np.array([p[3] for p in jf.KAPPA_OBS[s]])
        rss = ((Tz - Tobs) ** 2).sum(axis=-1)
        J_sens = n * np.log(rss / n)
        J_surf = ((Ts - jf.TS_OBS[s]) / jf.SIGMA_TS) ** 2
        J_kap = (((kap - kobs) / ksig) ** 2).sum(axis=-1)
        J_temp, J_all = J_sens + J_surf, J_sens + J_surf + J_kap
        kd_temp, kd_all = vertex(K, J_temp), vertex(K, J_all)
        ref = int(np.argmin(J_all))
        rows = []
        for kd in KD_ROWS_MW:
            k = int(np.argmin(abs(K - kd)))
            r = Tz[k] - Tobs
            rows.append(dict(kd_mW=float(K[k]), sensor_rmse_K=float(np.sqrt(np.mean(r ** 2))),
                             sensor_bias_K=float(r.mean()), surface_mean_K=float(Ts[k]),
                             kappa_model=kap[k].tolist(),
                             kappa_sigmas=((kap[k] - kobs) / ksig).tolist(),
                             dJ_sensors=float(J_sens[k] - J_sens[ref]), dJ_surface=float(J_surf[k] - J_surf[ref]),
                             dJ_diffusivity=float(J_kap[k] - J_kap[ref]), dJ_total=float(J_all[k] - J_all[ref])))
            q = rows[-1]
            print(f"  {s} A={A:.4f} K_d {q['kd_mW']:5.2f}: RMSE {q['sensor_rmse_K']:.3f} K, kappa "
                  f"{np.round(q['kappa_model'], 2).tolist()} ({np.round(q['kappa_sigmas'], 1).tolist()} sigma), "
                  f"dJ sensors {q['dJ_sensors']:+.1f} surface {q['dJ_surface']:+.1f} "
                  f"diffusivity {q['dJ_diffusivity']:+.1f} total {q['dJ_total']:+.1f}", flush=True)
        print(f"  {s}: at A = {A:.4f}, temperatures alone -> K_d {kd_temp:.2f}; with the diffusivity -> {kd_all:.2f}", flush=True)
        out[s] = dict(A=A, kappa_obs=kobs.tolist(), kappa_sigma=ksig.tolist(), n_sensors=n,
                      kd_temperatures_only_mW=kd_temp, kd_with_diffusivity_mW=kd_all,
                      reference_row_kd_mW=float(K[ref]), rows=rows)
    p = _REPO / "results" / "joint_valley.json"
    p.write_text(json.dumps(out, indent=1))
    print(f"wrote {p.relative_to(_REPO)}")


if __name__ == "__main__":
    main()
