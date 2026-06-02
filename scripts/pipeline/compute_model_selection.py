#!/usr/bin/env python3
"""Reduced-chi^2 and AICc for the three Table-1 conductivity-model rows.

For each site and each model configuration we evaluate the deep-sensor
residuals (T_model - T_obs) at the retrieved K_d*, weight them by the
real within-stability-window standard deviation sigma_i carried by
apollo_helpers, and compute

    chi2_red = (1/(N-k)) * sum_i [ (T_model_i - T_obs_i) / sigma_i ]^2
    AICc     = N*ln(RSS/N) + 2k + 2k(k+1)/(N-k-1)

with k = number of free parameters (0 for the Hayne global fixed row,
1 for each K_d* retrieval).  No values are fabricated: K_d* and the
sigma_i come from output/phase_a_results.json and the restored HFE
record respectively.

Run from the repo root:  python scripts/pipeline/compute_model_selection.py
"""
from __future__ import annotations
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'scripts' / 'figures'))   # phase2_figures_v2

from lunar.apollo_helpers import extract_sensor_stability        # noqa: E402
from scripts.pipeline.phase_a_pipeline import (                  # noqa: E402
    SITES, run_with, HAYNE,
)

HAYNE_GLOBAL_KD = 3.4e-3      # Hayne (2017) published global value


def deep_obs(site_cfg):
    """Return deep-sensor depths (m), T_eq (K), and within-window sigma (K)."""
    obs = extract_sensor_stability(site_cfg['mission'],
                                   min_depth_cm=site_cfg['MIN_DEPTH_CM'])
    deep = np.asarray(obs['deep_mask'], dtype=bool)
    z = np.asarray(obs['depth_cm_all'])[deep] / 100.0
    T = np.asarray(obs['T_eq_all'])[deep]
    sig = np.asarray(obs['T_std_all'])[deep]
    return z, T, sig


def stats(z_obs, T_obs, sigma, kd, k_model, site_cfg, n_free):
    """chi2_red and AICc for one model configuration."""
    z_mid, T_mean_z = run_with(site_cfg, kd=kd, k_model=k_model)
    T_pred = np.interp(z_obs, z_mid, T_mean_z)
    resid = T_pred - T_obs
    n = len(resid)

    # Guard against a zero/degenerate sigma (a flat stability window).
    sig = np.where(sigma > 1e-3, sigma, np.median(sigma[sigma > 1e-3]))
    chi2 = float(np.sum((resid / sig) ** 2))
    dof = n - n_free
    chi2_red = chi2 / dof if dof > 0 else float('nan')

    rss = float(np.sum(resid ** 2))
    k = n_free + 1                       # +1 for the variance estimate
    aic = n * np.log(rss / n) + 2 * k
    denom = n - k - 1
    aicc = aic + (2 * k * (k + 1) / denom) if denom > 0 else float('nan')
    return dict(n=n, rmse=float(np.sqrt(rss / n)),
                chi2=chi2, chi2_red=chi2_red, aicc=aicc)


def main():
    res = json.load(open(ROOT / 'output' / 'phase_a_results.json'))
    out = {}
    for tag, cfg in SITES.items():
        z_obs, T_obs, sigma = deep_obs(cfg)
        kd_hayne = res[tag]['kd_star']
        kd_3lay = res[tag]['kd_star_3layer']

        rows = {
            'hayne_global': stats(z_obs, T_obs, sigma, HAYNE_GLOBAL_KD,
                                  'hayne', cfg, n_free=0),
            'hayne_fit':    stats(z_obs, T_obs, sigma, kd_hayne,
                                  'hayne', cfg, n_free=1),
            'layer3_fit':   stats(z_obs, T_obs, sigma, kd_3lay,
                                  '3layer', cfg, n_free=1),
        }
        out[tag] = rows
        print(f'\n=== {cfg["label"]}  (N={rows["hayne_fit"]["n"]} deep '
              f'sensors; median sigma = {np.median(sigma):.3f} K) ===')
        for name, r in rows.items():
            d_aicc = r['aicc'] - rows['hayne_fit']['aicc']
            print(f'  {name:14s}  RMSE={r["rmse"]:.3f} K  '
                  f'chi2_red={r["chi2_red"]:.2f}  '
                  f'AICc={r["aicc"]:7.2f}  dAICc={d_aicc:+6.2f}')

    json.dump(out, open(ROOT / 'output' / 'model_selection.json', 'w'),
              indent=2)
    print('\nwrote output/model_selection.json')


if __name__ == '__main__':
    main()
