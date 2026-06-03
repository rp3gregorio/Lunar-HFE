"""Assemble the per-component K_d* error budget for Table 3.

Reads the canonical retrieval JSON and all five auxiliary-sensitivity
JSONs, combines them in quadrature, and writes the result to
output/kd_error_budget.json.

Required inputs (run their generating scripts first if missing):
    output/kd_retrieval_results.json            -- retrieve_kd.py
    output/borestem_sensitivity.json            -- compute_borestem_sensitivity.py
    output/stability_threshold_sensitivity.json -- compute_stability_threshold_sensitivity.py
    output/surface_bias_test.json               -- compute_surface_bias_test.py
    (no input file needed for sigma_Qb -- it is analytical from the
     K_d/Q_b degeneracy, with the published Q_b envelopes hard-coded
     below from Langseth (1976), Saito (2007), and Nagihara (2018).)

Output schema (kd_error_budget.json):
    {
      "A15": {
        "sigma_stat": float,         # bootstrap CI half-width
        "sigma_Qb":   float,         # K_d * (max(Q_b)-min(Q_b)) / (2*Q_b_nom)
        "sigma_zb":   float,         # half-range over the borestem-cut sweep
        "sigma_thr":  float,         # half-range over stability-threshold sweep
        "sigma_A":    float,         # half-range over Bond-albedo sweep
        "sigma_chi":  float,         # Hayne 2017 chi sensitivity (constant)
        "sigma_H":    float,         # joint K_d-H fit sensitivity
        "sigma_Ks":   float,         # surface conductivity (constant)
        "sigma_rho":  float,         # bulk density (constant)
        "total_quadrature": float,   # sqrt(sum sigma_i^2)
        "median":  float,            # bootstrap median (mW/m/K)
        "ci95_lo": float,            # 95% lower bound (mW/m/K)
        "ci95_hi": float             # 95% upper bound (mW/m/K)
      },
      "A17": { ... same keys ... }
    }

Run with:
    python scripts/pipeline/compute_error_budget.py
"""
from __future__ import annotations
import json
import pathlib

import numpy as np

ROOT = pathlib.Path(__file__).resolve().parents[2]
OUT = ROOT / "output"

# Published Q_b envelopes in mW m^-2 (Langseth 1976 / Saito 2007 / Nagihara 2018)
QB_ENVELOPES = {
    "A15": {"nominal": 21.0, "low": 14.0, "high": 25.0},
    "A17": {"nominal": 15.0, "low": 10.0, "high": 18.0},
}

# Fixed-input sensitivities from the Hayne 2017 envelope (chi, K_s, rho).
# These do not require a sweep -- they propagate analytically.
SIGMA_FIXED = {
    "A15": {"sigma_chi": 0.7325, "sigma_H": 0.2607,
            "sigma_Ks": 0.0977, "sigma_rho": 0.0244},
    "A17": {"sigma_chi": 1.7265, "sigma_H": 1.3855,
            "sigma_Ks": 0.2302, "sigma_rho": 0.0575},
}


def _half_range(values):
    """Half-range = (max - min) / 2 across a sensitivity sweep."""
    v = np.asarray(values, dtype=float)
    return float((v.max() - v.min()) / 2.0)


def main() -> int:
    print("Loading inputs...")
    kd = json.loads((OUT / "kd_retrieval_results.json").read_text())
    bs = json.loads((OUT / "borestem_sensitivity.json").read_text())
    th = json.loads((OUT / "stability_threshold_sensitivity.json").read_text())
    sb = json.loads((OUT / "surface_bias_test.json").read_text())

    budget = {}
    for site in ("A15", "A17"):
        bootstrap = kd[site]["bootstrap"]
        # sigma_stat = half-width of the bootstrap 16-84 percentile interval
        samples_mW = np.array(bootstrap["samples"]) * 1e3
        p16, p84 = np.percentile(samples_mW, [16, 84])
        sigma_stat = float((p84 - p16) / 2.0)

        # sigma_Qb = K_d_nom * (Q_b_high - Q_b_low) / (2 * Q_b_nom)
        env = QB_ENVELOPES[site]
        kd_nom_mW = kd[site]["kd_star"] * 1e3
        sigma_Qb = kd_nom_mW * (env["high"] - env["low"]) / (2.0 * env["nominal"])

        # Sweep half-ranges
        sigma_zb = _half_range(bs[site])
        sigma_thr = _half_range(th[site]["kd_star_mW"])
        sigma_A = _half_range(sb[site]["kd_star"])

        sigmas = {
            "sigma_stat": sigma_stat,
            "sigma_Qb": sigma_Qb,
            "sigma_zb": sigma_zb,
            "sigma_thr": sigma_thr,
            "sigma_A": sigma_A,
            **SIGMA_FIXED[site],
        }
        total = float(np.sqrt(sum(s ** 2 for s in sigmas.values())))

        budget[site] = {
            **sigmas,
            "total_quadrature": total,
            "median": float(np.median(samples_mW)),
            "ci95_lo": float(np.percentile(samples_mW, 2.5)),
            "ci95_hi": float(np.percentile(samples_mW, 97.5)),
        }

        print(f"\n  {site}:")
        for k, v in budget[site].items():
            print(f"    {k:<20} = {v:.4f}")

    out_path = OUT / "kd_error_budget.json"
    out_path.write_text(json.dumps(budget, indent=2))
    print(f"\nSaved: {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
