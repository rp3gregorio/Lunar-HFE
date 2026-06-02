#!/usr/bin/env python3
"""Decisive model comparison: variable-K_d vs uniform-K_d/variable-Q_b.

The Apollo HFE deep gradient is governed by the ratio Q_b/K_d, so a
steeper gradient at one borehole can be produced either by a higher
K_d or by a higher Q_b. This script tests the competing hypothesis a
referee will raise: that the two sites share a SINGLE deep
conductivity and differ only in basal heat flux.

Three models are fit to the same deep-sensor set at each site:

  M1  variable K_d   -- per-site K_d, Q_b fixed at the published value
                        (the manuscript's retrieval).
  M2  uniform K_d    -- ONE shared K_d for both sites, with the per-site
                        Q_b free within the published Saito-Nagihara
                        envelope.
  M3  uniform K_d,   -- one shared K_d, Q_b fixed at published values
      Q_b fixed         (the strict null: regolith AND flux uniform).

For each we report the pooled deep-sensor RMSE and AICc, counting
free parameters honestly: M1 has 2 (K_d^A15, K_d^A17); M2 has 3
(K_d shared, Q_b^A15, Q_b^A17); M3 has 1 (K_d shared).

Run from the repo root:
  python scripts/pipeline/compute_uniform_kd_sensitivity.py
"""
from __future__ import annotations
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts" / "figures"))

from lunar.apollo_helpers import extract_sensor_stability        # noqa: E402
from scripts.pipeline.retrieve_kd import SITES, run_with    # noqa: E402

# Published basal-flux envelopes (Langseth 1976 nominal; Saito 2007 /
# Nagihara 2018 reanalysis range), in W m^-2.
QB_NOMINAL = {"A15": 0.021, "A17": 0.015}
QB_ENVELOPE = {"A15": (0.014, 0.025), "A17": (0.010, 0.018)}

# K_d sweep grid (W m^-1 K^-1), wide enough to bracket every minimum.
KD_GRID = np.linspace(2.0e-3, 22.0e-3, 41)
# Q_b sweep grid per site, spanning the published envelope.
QB_GRID = {s: np.linspace(lo, hi, 25) for s, (lo, hi) in QB_ENVELOPE.items()}


def deep_obs(site_cfg):
    """Deep-sensor depths (m), T_eq (K), within-window sigma (K)."""
    obs = extract_sensor_stability(site_cfg["mission"],
                                   min_depth_cm=site_cfg["MIN_DEPTH_CM"])
    deep = np.asarray(obs["deep_mask"], dtype=bool)
    z = np.asarray(obs["depth_cm_all"])[deep] / 100.0
    T = np.asarray(obs["T_eq_all"])[deep]
    sig = np.asarray(obs["T_std_all"])[deep]
    return z, T, sig


def residuals(site_cfg, kd, qb, z_obs, T_obs):
    """Deep-sensor (model - obs) residuals at given K_d and Q_b."""
    z_mid, T_mean = run_with(site_cfg, kd=kd, qb=qb, k_model="hayne")
    return np.interp(z_obs, z_mid, T_mean) - T_obs


def aicc(rss, n, k):
    """Small-sample-corrected Akaike criterion from a residual sum of
    squares (Gaussian-likelihood form; +1 d.o.f. for the variance)."""
    kk = k + 1
    val = n * np.log(rss / n) + 2 * kk
    denom = n - kk - 1
    return val + (2 * kk * (kk + 1) / denom) if denom > 0 else float("nan")


def main():
    obs = {s: deep_obs(SITES[s]) for s in ("A15", "A17")}
    n = {s: len(obs[s][1]) for s in obs}
    n_tot = n["A15"] + n["A17"]

    # ---- precompute residual cubes -------------------------------------
    # rss[s][i, j] = residual sum of squares at KD_GRID[i], QB_GRID[s][j]
    print("Building (K_d, Q_b) residual grids ...", flush=True)
    rss = {}
    for s in ("A15", "A17"):
        z_obs, T_obs, _ = obs[s]
        grid = np.empty((len(KD_GRID), len(QB_GRID[s])))
        for i, kd in enumerate(KD_GRID):
            for j, qb in enumerate(QB_GRID[s]):
                r = residuals(SITES[s], kd, qb, z_obs, T_obs)
                grid[i, j] = float(np.sum(r ** 2))
            print(f"  {s}: K_d {i+1}/{len(KD_GRID)}", flush=True)
        rss[s] = grid

    # index of the published-Q_b column for each site
    j_nom = {s: int(np.argmin(np.abs(QB_GRID[s] - QB_NOMINAL[s])))
             for s in obs}

    # ---- M1: variable K_d, Q_b fixed ----------------------------------
    # independent per-site K_d minimum at the nominal Q_b column
    m1 = {}
    for s in ("A15", "A17"):
        col = rss[s][:, j_nom[s]]
        i = int(np.argmin(col))
        m1[s] = dict(kd=KD_GRID[i], rss=col[i])
    rss_m1 = m1["A15"]["rss"] + m1["A17"]["rss"]
    aicc_m1 = aicc(rss_m1, n_tot, k=2)

    # ---- M2: uniform K_d, Q_b free per site ---------------------------
    # for every shared K_d, each site picks its best Q_b in-envelope
    best = None
    for i, kd in enumerate(KD_GRID):
        r15 = rss["A15"][i, :].min()
        r17 = rss["A17"][i, :].min()
        tot = r15 + r17
        if best is None or tot < best[0]:
            j15 = int(np.argmin(rss["A15"][i, :]))
            j17 = int(np.argmin(rss["A17"][i, :]))
            best = (tot, kd, QB_GRID["A15"][j15], QB_GRID["A17"][j17],
                    r15, r17)
    rss_m2, kd_m2, qb15_m2, qb17_m2, r15_m2, r17_m2 = best
    aicc_m2 = aicc(rss_m2, n_tot, k=3)

    # ---- M3: uniform K_d, Q_b fixed (strict null) ---------------------
    best3 = None
    for i, kd in enumerate(KD_GRID):
        tot = rss["A15"][i, j_nom["A15"]] + rss["A17"][i, j_nom["A17"]]
        if best3 is None or tot < best3[0]:
            best3 = (tot, kd)
    rss_m3, kd_m3 = best3
    aicc_m3 = aicc(rss_m3, n_tot, k=1)

    # ---- report --------------------------------------------------------
    def rmse(rss_):
        return np.sqrt(rss_ / n_tot)

    aiccs = {"M1": aicc_m1, "M2": aicc_m2, "M3": aicc_m3}
    best_aicc = min(aiccs.values())

    out = {
        "n_A15": n["A15"], "n_A17": n["A17"], "n_total": n_tot,
        "M1_variable_kd": {
            "kd_A15": m1["A15"]["kd"], "kd_A17": m1["A17"]["kd"],
            "qb_A15": QB_NOMINAL["A15"], "qb_A17": QB_NOMINAL["A17"],
            "rmse": rmse(rss_m1), "aicc": aicc_m1,
            "delta_aicc": aicc_m1 - best_aicc, "k": 2},
        "M2_uniform_kd_free_qb": {
            "kd_shared": kd_m2, "qb_A15": qb15_m2, "qb_A17": qb17_m2,
            "rmse": rmse(rss_m2), "aicc": aicc_m2,
            "delta_aicc": aicc_m2 - best_aicc, "k": 3},
        "M3_uniform_kd_fixed_qb": {
            "kd_shared": kd_m3,
            "qb_A15": QB_NOMINAL["A15"], "qb_A17": QB_NOMINAL["A17"],
            "rmse": rmse(rss_m3), "aicc": aicc_m3,
            "delta_aicc": aicc_m3 - best_aicc, "k": 1},
    }

    print("\n" + "=" * 70)
    print("MODEL COMPARISON  (pooled deep-sensor fit, N = "
          f"{n_tot}: {n['A15']} at A15, {n['A17']} at A17)")
    print("=" * 70)
    for tag, lbl in [("M1_variable_kd", "M1  variable K_d, Q_b fixed"),
                     ("M2_uniform_kd_free_qb",
                      "M2  uniform K_d, Q_b free"),
                     ("M3_uniform_kd_fixed_qb",
                      "M3  uniform K_d, Q_b fixed")]:
        m = out[tag]
        print(f"\n{lbl}  (k={m['k']})")
        if "kd_shared" in m:
            print(f"   K_d (shared) = {m['kd_shared']*1e3:.2f} mW/m/K")
        else:
            print(f"   K_d = {m['kd_A15']*1e3:.2f} (A15), "
                  f"{m['kd_A17']*1e3:.2f} (A17) mW/m/K")
        print(f"   Q_b = {m['qb_A15']*1e3:.1f} (A15), "
              f"{m['qb_A17']*1e3:.1f} (A17) mW/m^2")
        print(f"   pooled RMSE = {m['rmse']:.3f} K    "
              f"AICc = {m['aicc']:.2f}    dAICc = {m['delta_aicc']:+.2f}")

    print("\n" + "-" * 70)
    # interpretation
    d_m2 = out["M2_uniform_kd_free_qb"]["delta_aicc"]
    if d_m2 < 2:
        verdict = ("M2 is statistically INDISTINGUISHABLE from the best "
                   "model: a uniform K_d with site-specific Q_b fits the "
                   "HFE record as well as a variable K_d. The data "
                   "constrain Q_b/K_d, not K_d alone.")
    elif d_m2 < 10:
        verdict = ("M2 is somewhat disfavoured but not decisively ruled "
                   "out; the uniform-K_d hypothesis cannot be cleanly "
                   "rejected.")
    else:
        verdict = ("M2 is decisively rejected: even with per-site Q_b "
                   "free, a single shared K_d cannot reproduce both "
                   "records. The inter-site K_d contrast is required.")
    print("VERDICT:", verdict)
    print("-" * 70)

    json.dump(out, open(ROOT / "output" / "uniform_kd_test.json", "w"),
              indent=2)
    print("\nwrote output/uniform_kd_test.json")


if __name__ == "__main__":
    main()
