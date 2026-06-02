"""
K_d sensitivity sweep with Hayne (2017) shape held fixed.

For each Apollo site, run solve_pixel across a grid of K_d values
(deep conductivity asymptote, the only varied parameter) and record
the deep-sensor (z >= 0.8 m) RMSE versus the restored Apollo HFE
record (Nagihara et al. 2018).

Per-site optimum K_d^* is found by a parabolic fit to the three points
bracketing the minimum on the discrete grid, with a leave-one-out
jackknife confidence interval on K_d^*.

Outputs:
  - paper/letter/figures/fig5_kd_sweep.pdf   (publication panel)
  - /tmp/kd_sweep_results.json               (numbers for the letter)
"""
from __future__ import annotations
import json, os, pathlib, sys
from copy import deepcopy

# Bootstrap (mirrors notebook cell 1)
_here = pathlib.Path('/Users/rp3gregorio/Lunar-V2').resolve()
sys.path.insert(0, str(_here))
from lunar import _bootstrap as boot
boot.ensure_lunar(extra=('spiceypy', 'scipy'))
boot.ensure_apollo_hfe(mission='a15',
                       probes=('p1f1','p1f2','p1f3','p1f4',
                               'p2f1','p2f2','p2f3','p2f4'))
boot.ensure_apollo_hfe(mission='a17', probes=())

import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

from lunar.grid import make_geometric_grid
from lunar.properties import conductivity_hayne, specific_heat
from lunar.constants import (
    K_SURFACE, K_DEEP, H_PARAMETER, CHI_RADIATIVE, T_REFERENCE,
    LUNATION_SECONDS,
)
from lunar.solver import PixelInputs, solve_pixel
from lunar.apollo_helpers import extract_sensor_stability
from lunar.plotting.style_guide import apply_style, COLORS, save_figure
apply_style()

# ── Constants (mirror notebook cell 5) ─────────────────────────────
S0           = 1361.0
T_LUNAR      = LUNATION_SECONDS
DT_STEP      = 3600.0
N_LUN_FAST   = 30
TOL_FAST     = 0.05
GRID         = dict(z_max=5.0, dz0=0.002, growth=0.08)

SITES = {
    'A15': dict(label='Apollo 15', lat=26.13, lon=3.63,
                albedo=0.131, emissivity=0.95, Q_BASAL=0.021,
                T_MEAN_EFF=250.0, MIN_DEPTH_CM=80, mission='a15'),
    'A17': dict(label='Apollo 17', lat=20.19, lon=30.77,
                albedo=0.137, emissivity=0.95, Q_BASAL=0.015,
                T_MEAN_EFF=255.0, MIN_DEPTH_CM=80, mission='a17'),
}
HAYNE = dict(K_S=K_SURFACE, K_D=K_DEEP, H=H_PARAMETER, CHI=CHI_RADIATIVE)

grid  = make_geometric_grid(**GRID)
z_mid = grid.z_mid
z_cm  = z_mid * 100.0
N_t   = int(T_LUNAR / DT_STEP) + 1
t_s   = np.linspace(0.0, T_LUNAR, N_t)


def run_hayne_kd(site_cfg, *, kd):
    """One Hayne-shape run with Kd swapped, all else fixed."""
    site = deepcopy(site_cfg)
    cos_lat = np.cos(np.deg2rad(site['lat']))
    phase   = 2.0 * np.pi * t_s / T_LUNAR
    insol   = S0 * cos_lat * np.maximum(0.0, np.cos(phase))

    def k_func(T, z):
        return conductivity_hayne(T, z,
                                  Ks=HAYNE['K_S'], Kd=kd,
                                  H=HAYNE['H'], chi=HAYNE['CHI'])
    def cp_func(T):
        return specific_heat(T, model='hayne')

    K_init = k_func(np.full_like(z_mid, site['T_MEAN_EFF']), z_mid)
    T_init = site['T_MEAN_EFF'] + site['Q_BASAL'] * np.cumsum(grid.dz / K_init)
    return solve_pixel(PixelInputs(
        grid=grid, t=t_s, bc_mode='radiative',
        insolation=insol, albedo=site['albedo'],
        emissivity=site['emissivity'], Q_b=site['Q_BASAL'], T_init=T_init,
        n_lunations_spinup=N_LUN_FAST, spinup_tol_K=TOL_FAST,
        K_func=k_func, cp_func=cp_func,
    ))


def deep_rmse_array(out, bundle, mask=None):
    """RMSE of model-vs-obs at deep sensors; mask=None uses bundle's deep_mask."""
    T_mean = out.T.mean(axis=1)
    T_at   = np.interp(bundle['depth_cm_all'], z_cm, T_mean)
    resid  = T_at - bundle['T_eq_all']
    deep   = bundle['deep_mask'] if mask is None else mask
    return float(np.sqrt(np.mean(resid[deep] ** 2))), resid


def parabolic_min(xs, ys):
    """Quadratic fit to three lowest points; return (x*, y*)."""
    i = int(np.argmin(ys))
    i0 = max(1, min(len(xs) - 2, i))
    x = np.array(xs[i0-1:i0+2])
    y = np.array(ys[i0-1:i0+2])
    c = np.polyfit(x, y, 2)
    x_star = -c[1] / (2 * c[0])
    y_star = np.polyval(c, x_star)
    return x_star, y_star


# ── Load HFE bundles ─────────────────────────────────────────────
hfe = {tag: extract_sensor_stability(cfg['mission'], cfg['MIN_DEPTH_CM'])
       for tag, cfg in SITES.items()}
for tag, b in hfe.items():
    print(f'{tag}: {int(b["deep_mask"].sum())} deep sensors '
          f'(min_depth = {SITES[tag]["MIN_DEPTH_CM"]} cm)')

# ── Sweep K_d (per-site grid; A17 needs extended range) ──────────
KD_GRIDS = {
    'A15': np.linspace(1.5e-3, 9.0e-3, 20),
    'A17': np.linspace(3.0e-3, 18.0e-3, 24),
}

results = {tag: dict(kd=KD_GRIDS[tag].copy(), rmse=[], resid=[])
           for tag in SITES}

for tag, cfg in SITES.items():
    print(f'\n── {cfg["label"]} ──  '
          f'K_d sweep over {len(KD_GRIDS[tag])} values: '
          f'{KD_GRIDS[tag][0]*1e3:.2f}–{KD_GRIDS[tag][-1]*1e3:.2f} mW/m/K')
    for kd in KD_GRIDS[tag]:
        out = run_hayne_kd(cfg, kd=kd)
        r, residual = deep_rmse_array(out, hfe[tag])
        results[tag]['rmse'].append(r)
        results[tag]['resid'].append(residual)
        print(f'  K_d = {kd*1e3:5.2f} mW/m/K  →  RMSE = {r:5.3f} K')

# ── Per-site optimum + jackknife CI ──────────────────────────────
summary = {}
for tag, R in results.items():
    rmse_arr = np.array(R['rmse'])
    kd_arr   = R['kd']

    # Best on grid
    i_best = int(np.argmin(rmse_arr))
    kd_grid_best = float(kd_arr[i_best])
    rmse_grid_best = float(rmse_arr[i_best])

    # Parabolic refinement near min
    kd_star, rmse_star = parabolic_min(kd_arr, rmse_arr)
    kd_star = float(np.clip(kd_star, kd_arr[0], kd_arr[-1]))

    # Jackknife: drop one deep sensor at a time, repeat the fit
    bundle = hfe[tag]
    deep_idx = np.where(bundle['deep_mask'])[0]
    kd_jk = []
    for j in deep_idx:
        m = bundle['deep_mask'].copy()
        m[j] = False
        rm = []
        for k_idx in range(len(kd_arr)):
            resid = results[tag]['resid'][k_idx]
            rm.append(float(np.sqrt(np.mean(resid[m] ** 2))))
        kj_star, _ = parabolic_min(kd_arr, rm)
        kd_jk.append(float(np.clip(kj_star, kd_arr[0], kd_arr[-1])))
    kd_jk = np.array(kd_jk)
    n = len(kd_jk)
    se = np.sqrt((n - 1) / n * np.sum((kd_jk - kd_jk.mean()) ** 2))

    # RMSE at the canonical Hayne K_d=3.4e-3 and at M&S 6.3e-3
    def rmse_at(kd_target):
        return float(np.interp(kd_target, kd_arr, rmse_arr))

    # Re-run at the parabolic optimum to get bias and MAE
    out_star = run_hayne_kd(SITES[tag], kd=kd_star)
    rmse_chk, resid_star = deep_rmse_array(out_star, bundle)
    deep = bundle['deep_mask']
    bias_star = float(np.mean(resid_star[deep]))
    mae_star  = float(np.mean(np.abs(resid_star[deep])))

    summary[tag] = dict(
        n_deep=int(bundle['deep_mask'].sum()),
        kd_grid=KD_GRIDS[tag].tolist(),
        rmse_grid=[float(x) for x in rmse_arr],
        kd_grid_best=kd_grid_best,
        rmse_grid_best=rmse_grid_best,
        kd_star=float(kd_star),
        rmse_star=float(rmse_star),
        kd_se_jackknife=float(se),
        kd_jk_min=float(kd_jk.min()),
        kd_jk_max=float(kd_jk.max()),
        rmse_at_hayne=rmse_at(3.4e-3),
        rmse_at_ms=rmse_at(6.3e-3),
        bias_star=bias_star,
        mae_star=mae_star,
        rmse_check_at_star=float(rmse_chk),
    )
    print(f'\n{tag}: K_d* = {kd_star*1e3:.2f} ± {se*1e3:.2f} mW/m/K  '
          f'(jackknife N={n}; RMSE* = {rmse_star:.3f} K; '
          f'Hayne RMSE = {rmse_at(3.4e-3):.3f} K; '
          f'M&S RMSE = {rmse_at(6.3e-3):.3f} K)')

# ── Save numerical results ───────────────────────────────────────
with open('/tmp/kd_sweep_results.json', 'w') as f:
    json.dump(summary, f, indent=2)
print('\nSaved /tmp/kd_sweep_results.json')

# ── Figure: RMSE(K_d) curves ─────────────────────────────────────
fig, ax = plt.subplots(figsize=(7.0, 3.6), constrained_layout=True)

c_a15 = COLORS.get('hayne',    '#2471A3')
c_a17 = COLORS.get('discrete', '#C0392B')

for tag, color, marker in [('A15', c_a15, 'o'), ('A17', c_a17, 's')]:
    s = summary[tag]
    kd_mw = np.array(s['kd_grid']) * 1e3
    rmse  = np.array(s['rmse_grid'])
    ax.plot(kd_mw, rmse, marker=marker, ls='-', lw=1.4, ms=4.5,
            color=color,
            label=f'{tag}  (N={s["n_deep"]})')
    # Optimum marker + jackknife band
    ax.axvline(s['kd_star']*1e3, color=color, ls='--', lw=0.9, alpha=0.7)
    ax.axvspan((s['kd_star']-s['kd_se_jackknife'])*1e3,
               (s['kd_star']+s['kd_se_jackknife'])*1e3,
               color=color, alpha=0.10)
    ax.scatter([s['kd_star']*1e3], [s['rmse_star']],
               marker='*', s=140, color=color, edgecolor='k',
               zorder=5,
               label=fr'{tag} $K_d^*$ = {s["kd_star"]*1e3:.2f}'
                     fr' $\pm$ {s["kd_se_jackknife"]*1e3:.2f} mW/m/K')

# Reference lines
ax.axvline(3.4, color='k', ls=':',  lw=0.8, alpha=0.6)
ax.text(3.4, ax.get_ylim()[1]*0.93, ' Hayne 2017',
        fontsize=8, ha='left', va='top', color='k')
ax.axvline(6.3, color='gray', ls=':', lw=0.8, alpha=0.6)
ax.text(6.3, ax.get_ylim()[1]*0.93, ' Mart\u00ednez & Siegler 2021',
        fontsize=8, ha='left', va='top', color='gray')

ax.axhline(2.0, color='k', ls='--', lw=0.6, alpha=0.5)
ax.text(8.7, 2.0, ' Phase-1 target', fontsize=8,
        ha='right', va='bottom', color='k', alpha=0.7)

ax.set_xlabel(r'Deep conductivity $K_d$  [mW m$^{-1}$ K$^{-1}$]')
ax.set_ylabel('Deep-sensor RMSE  [K]')
ax.set_title(r'Per-site $K_d$ retrieval with Hayne (2017) shape held fixed',
             fontsize=10)
ax.legend(loc='upper right', fontsize=8, frameon=False, handlelength=1.8)
ax.grid(alpha=0.3, lw=0.5)

OUT = pathlib.Path('/Users/rp3gregorio/Lunar-V2/output/figures')
OUT.mkdir(parents=True, exist_ok=True)
save_figure(fig, 'fig5_kd_sweep', output_dir=str(OUT))
print(f'Saved {OUT}/fig5_kd_sweep.pdf')
