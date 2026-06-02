"""Apollo HFE validation helpers — shared between Apollo 15 / 17 cells.

Notebook 01_apollo_validation.ipynb previously duplicated every figure
recipe twice (once per mission).  This module factors the common pieces
out so each figure is defined in exactly one place and the notebook
simply loops over both sites.
"""
from __future__ import annotations

from datetime import datetime, timezone

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

from lunar.validation import load_apollo_hfe_depth
from lunar.plotting.style_guide import save_figure

SECONDS_PER_YEAR = 365.25 * 86400.0


# --- Time helpers -----------------------------------------------------

def iso_to_seconds(iso_arr):
    """Convert ISO-8601 strings to Unix timestamp seconds."""
    out = np.empty(len(iso_arr), dtype=np.float64)
    for i, s in enumerate(iso_arr):
        s = s.strip()
        if s.endswith('Z'):
            s = s[:-1] + '+00:00'
        out[i] = datetime.fromisoformat(s).replace(tzinfo=timezone.utc).timestamp()
    return out


def find_stable_window(subset, slope_thresh_K_per_year=0.08, min_frac=0.20):
    """Scan 55%–85% of a record; pick the earliest start where the trailing
    linear fit has |slope| < threshold.  Fallback: last 25% of records.

    0.08 K/yr (~2.2e-4 K/day) is the stated criterion in the paper (letter
    §2.1).  It is ~4.6× stricter than the naive 1e-3 K/day often cited;
    the stricter value reduces bias from residual post-disturbance drift.
    """
    n = len(subset)
    t_sec = iso_to_seconds(subset['time_iso'])
    t_day = (t_sec - t_sec[0]) / 86400.0
    t_year = t_day / 365.25
    T = subset['T'].astype(np.float64)

    chosen_i = int(0.75 * n)
    method = 'fallback_last25'
    slope_out = np.nan

    for frac in np.linspace(0.55, 0.85, 13):
        i0 = int(frac * n)
        if n - i0 < max(40, int(min_frac * n)):
            continue
        x, y = t_year[i0:], T[i0:]
        if np.ptp(x) <= 0:
            continue
        sl, _ = np.polyfit(x, y, 1)
        if abs(sl) <= slope_thresh_K_per_year:
            chosen_i = i0
            method = 'trend_flat'
            slope_out = float(sl)
            break

    if np.isnan(slope_out):
        x, y = t_year[chosen_i:], T[chosen_i:]
        if np.ptp(x) > 0:
            slope_out = float(np.polyfit(x, y, 1)[0])

    return chosen_i, float(t_day[chosen_i]), method, slope_out


# --- Data extraction --------------------------------------------------

def extract_sensor_stability(mission, min_depth_cm):
    """Load HFE depth tables and compute per-sensor equilibrium temperatures.

    Returns a dict with keys: d1, d2, sensors, probe_data, depth_cm_all,
    T_eq_all, T_std_all, stype_all, deep_mask.
    """
    d1 = load_apollo_hfe_depth(mission, 1)
    d2 = load_apollo_hfe_depth(mission, 2)

    sensors_all = []
    probe_data = {1: {}, 2: {}}

    for probe_num, dtab in [(1, d1), (2, d2)]:
        t_sec_all = iso_to_seconds(dtab['time_iso'])
        for sensor in np.unique(dtab['sensor']):
            mask = dtab['sensor'] == sensor
            subset = dtab[mask]
            n = len(subset)
            i_start, day_start, method, slope = find_stable_window(subset)
            tail = subset[i_start:]

            depth = float(np.unique(tail['depth_cm'])[0])
            T_eq = float(np.mean(tail['T']))
            T_std = float(np.std(tail['T']))
            stype = sensor.strip()[:2]

            t_s_sensor = t_sec_all[mask]
            t_day = (t_s_sensor - t_s_sensor[0]) / 86400.0
            probe_data[probe_num][sensor.strip()] = {
                't_day': t_day,
                'T': dtab['T'][mask].astype(np.float64),
                'i_start': i_start,
                'T_eq': T_eq,
                'depth_cm': depth,
                'stype': stype,
            }

            sensors_all.append({
                'sensor': sensor.strip(),
                'depth_cm': depth,
                'T_eq': T_eq,
                'T_std': T_std,
                'n_tail': len(tail),
                'stype': stype,
                'probe': probe_num,
                'tail_start_frac': i_start / n,
                'stable_day': day_start,
                'stable_method': method,
                'tail_slope_Kyr': slope,
            })

    sensors_all.sort(key=lambda s: s['depth_cm'])

    depth_cm_all = np.array([s['depth_cm'] for s in sensors_all])
    T_eq_all = np.array([s['T_eq'] for s in sensors_all])
    T_std_all = np.array([s['T_std'] for s in sensors_all])
    stype_all = [s['stype'] for s in sensors_all]
    deep_mask = depth_cm_all >= min_depth_cm

    return {
        'd1': d1, 'd2': d2, 'sensors': sensors_all, 'probe_data': probe_data,
        'depth_cm_all': depth_cm_all, 'T_eq_all': T_eq_all,
        'T_std_all': T_std_all, 'stype_all': stype_all, 'deep_mask': deep_mask,
    }


def print_stability_table(bundle, site_label, min_depth_cm):
    """Print the equilibrium-temperature summary table for one site."""
    print(f'\n{site_label} — equilibrium temperatures '
          f'(averaged within stability window):')
    print(f'{"Sensor":<8} {"P":>2} {"Depth":>6} {"Type":>4} '
          f'{"T_eq(K)":>9} {"σ(K)":>6} {"stable_from_day":>16} '
          f'{"slope[K/yr]":>12} {"Method":>15} {"RMSE?":>6}')
    print('─' * 100)
    for s in bundle['sensors']:
        flag = '✓' if s['depth_cm'] >= min_depth_cm else '·'
        print(f'{s["sensor"]:<8} {s["probe"]:>2d} {s["depth_cm"]:>6.0f} '
              f'{s["stype"]:>4} {s["T_eq"]:>9.2f} {s["T_std"]:>6.3f} '
              f'{s["stable_day"]:>16.0f} {s["tail_slope_Kyr"]:>+12.3f} '
              f'{s["stable_method"]:>15} {flag:>6}')
    n_deep = bundle['deep_mask'].sum()
    print(f'\nDeep sensors (≥{min_depth_cm} cm) used in RMSE: {n_deep}')


# --- Plotting ---------------------------------------------------------

def plot_stability_region(bundle, site_label, min_depth_cm, out_name, output_dir):
    """Two-panel (P1 + P2) full time series with stability window shading.

    Matches the original §1 figure verbatim for Apollo 15 / 17.
    """
    depth_cm_all = bundle['depth_cm_all']
    probe_data = bundle['probe_data']

    cmap = plt.get_cmap('viridis_r')
    norm = plt.Normalize(vmin=0, vmax=depth_cm_all.max())

    fig, axes = plt.subplots(1, 2, figsize=(18, 6), constrained_layout=True)

    for ax, probe_num, dtab in zip(axes, [1, 2], [bundle['d1'], bundle['d2']]):
        pdata = probe_data[probe_num]

        t_sec_probe = iso_to_seconds(dtab['time_iso'])
        total_days = (t_sec_probe[-1] - t_sec_probe[0]) / 86400.0

        deep_start_days = []
        for sn, sd in pdata.items():
            if sd['depth_cm'] < min_depth_cm:
                continue
            mask_sn = dtab['sensor'] == sn
            if not np.any(mask_sn):
                continue
            t_sn = t_sec_probe[mask_sn]
            deep_start_days.append(
                (t_sn[sd['i_start']] - t_sec_probe[0]) / 86400.0
            )
        shared_stable_day = (float(np.percentile(deep_start_days, 75))
                             if deep_start_days else 0.75 * total_days)
        earliest_deep_day = min(deep_start_days) if deep_start_days else 0.0

        ax.axvspan(0, earliest_deep_day, color='#ebebeb', alpha=0.60,
                   zorder=0, label='Initial transient (excluded)')
        ax.axvspan(shared_stable_day, total_days, color='#d5f5e3',
                   alpha=0.75, zorder=0,
                   label=f'Stability window (day {shared_stable_day:.0f}→)\n'
                         'T_eq averaged here')

        for sn, sd in sorted(pdata.items(), key=lambda x: x[1]['depth_cm']):
            clr = cmap(norm(sd['depth_cm']))
            lw = 2.0 if sd['depth_cm'] >= min_depth_cm else 1.0
            ls = '-' if sd['depth_cm'] >= min_depth_cm else '--'
            lbl = f'{sd["depth_cm"]:.0f} cm ({sn})'
            ax.plot(sd['t_day'], sd['T'], color=clr, lw=lw, ls=ls,
                    alpha=0.85, label=lbl, zorder=3)
            t_stab = sd['t_day'][sd['i_start']]
            ax.axvline(t_stab, color=clr, lw=0.9, ls=':', alpha=0.55,
                       zorder=2)
            ax.plot([t_stab, sd['t_day'][-1]], [sd['T_eq'], sd['T_eq']],
                    color='#E67E22', lw=1.2, ls=':', alpha=0.85, zorder=4)

        ax.set_xlabel('Days since emplacement', fontsize=10)
        ax.set_ylabel('Temperature  (K)', fontsize=10)
        ax.set_xlim(0, total_days)
        ax.set_title(f'{site_label} — Probe {probe_num}  '
                     '(Thermal Stability Analysis)', fontsize=11,
                     weight='bold')
        ax.grid(True, alpha=0.15)
        ax.legend(loc='upper left', fontsize=7, ncol=2, framealpha=0.9,
                  bbox_to_anchor=(0.0, 1.0), title='Depth (sensor)',
                  title_fontsize=7)

    sm = plt.cm.ScalarMappable(cmap=cmap, norm=norm)
    sm.set_array([])
    cbar = fig.colorbar(sm, ax=axes, orientation='vertical', shrink=0.75,
                        pad=0.01, label='Depth  (cm)')
    cbar.ax.invert_yaxis()

    fig.suptitle(
        f'{site_label} HFE — Full Time Series with Thermal Stability Windows\n'
        'Green = stability window used for T_eq averaging  |  '
        'Orange dotted = equilibrium temperature T_eq  |  '
        f'Dashed curves = diurnal zone (< {min_depth_cm} cm, excluded from RMSE)',
        fontsize=10, weight='bold')

    save_figure(fig, out_name, output_dir=output_dir)
    plt.show()


def plot_per_sensor_stability_windows(bundle, site_label, min_depth_cm,
                                      out_name, output_dir):
    """Per-sensor grid of stability windows — one panel per sensor."""
    sensors = bundle['sensors']
    probe_data = bundle['probe_data']

    n_sensors = len(sensors)
    ncols = 4
    nrows = int(np.ceil(n_sensors / ncols))

    fig, axes = plt.subplots(nrows, ncols, figsize=(20, 3.2 * nrows),
                             constrained_layout=True)
    axes_flat = axes.ravel()

    for idx, s in enumerate(sensors):
        ax = axes_flat[idx]
        sd = probe_data[s['probe']][s['sensor']]
        t_day, T, i0 = sd['t_day'], sd['T'], sd['i_start']

        ax.plot(t_day, T, color='#2C3E50', lw=0.6, alpha=0.7, zorder=2)
        ax.axvspan(t_day[i0], t_day[-1], color='#d5f5e3', alpha=0.7, zorder=0)
        ax.plot(t_day[i0:], T[i0:], color='#27AE60', lw=0.8, alpha=0.9,
                zorder=3)
        ax.axhline(s['T_eq'], color='#E67E22', lw=1.8, ls='-', alpha=0.9,
                   zorder=4)
        ax.axhspan(s['T_eq'] - s['T_std'], s['T_eq'] + s['T_std'],
                   color='#E67E22', alpha=0.12, zorder=1)
        ax.axvline(t_day[i0], color='#27AE60', lw=1.0, ls='--', alpha=0.7,
                   zorder=3)

        deep = s['depth_cm'] >= min_depth_cm
        title_clr = '#1A5276' if deep else '#999999'
        rmse_tag = ' [RMSE]' if deep else ' [excl.]'
        ax.set_title(
            f'{s["sensor"]}  ({s["depth_cm"]:.0f} cm, P{s["probe"]}){rmse_tag}',
            fontsize=9, weight='bold', color=title_clr)

        ax.text(0.98, 0.05,
                f'T_eq = {s["T_eq"]:.2f} ± {s["T_std"]:.2f} K\n'
                f'window: day {s["stable_day"]:.0f}→{t_day[-1]:.0f}\n'
                f'method: {s["stable_method"]}\n'
                f'slope: {s["tail_slope_Kyr"]:+.3f} K/yr',
                transform=ax.transAxes, fontsize=7, va='bottom', ha='right',
                bbox=dict(boxstyle='round,pad=0.3', facecolor='white',
                          alpha=0.85))

        ax.set_xlabel('Days', fontsize=8)
        ax.set_ylabel('T (K)', fontsize=8)
        ax.tick_params(labelsize=7)
        ax.grid(True, alpha=0.15)

    for j in range(n_sensors, len(axes_flat)):
        axes_flat[j].set_visible(False)

    fig.suptitle(
        f'Per-Sensor Stability Windows — {site_label} HFE\n'
        'Green region = stability window used for T_eq averaging  |  '
        'Orange line = T_eq  |  Gray titles = excluded from RMSE',
        fontsize=11, weight='bold')

    save_figure(fig, out_name, output_dir=output_dir)
    plt.show()


def plot_depth_colored_timeseries(bundle, site_label, min_depth_cm,
                                  out_name, output_dir):
    """Two-panel (P1 + P2) depth-coloured temperature history."""
    depth_cm_all = bundle['depth_cm_all']
    cmap = plt.get_cmap('viridis_r')
    norm = plt.Normalize(vmin=min(depth_cm_all), vmax=max(depth_cm_all))

    fig, axes = plt.subplots(1, 2, figsize=(16, 6), sharey=False,
                             constrained_layout=True)

    for ax, probe_num, dtab, title in zip(
            axes, [1, 2], [bundle['d1'], bundle['d2']], ['Probe 1', 'Probe 2']):
        t0 = None
        for sensor in np.unique(dtab['sensor']):
            mask = dtab['sensor'] == sensor
            subset = dtab[mask]
            depth = float(np.unique(subset['depth_cm'])[0])
            color = cmap(norm(depth))
            stype = sensor.strip()[:2]
            ls = '-' if stype == 'TG' else '--'
            lw = 1.2 if depth >= min_depth_cm else 0.7
            alpha = 0.9 if depth >= min_depth_cm else 0.4

            times_s = iso_to_seconds(subset['time_iso'])
            if t0 is None:
                t0 = times_s[0]
            yr = (times_s - t0) / SECONDS_PER_YEAR

            tag = '' if depth >= min_depth_cm else ' (excl.)'
            ax.plot(yr, subset['T'], lw=lw, ls=ls, color=color, alpha=alpha,
                    label=f'{sensor.strip()} ({depth:.0f} cm){tag}')

        ax.set_xlabel('Years after deployment')
        ax.set_ylabel('Temperature (K)')
        ax.set_title(f'{site_label} HFE — {title}', fontsize=11,
                     weight='bold')
        ax.legend(fontsize=6.8, ncol=2, loc='upper left',
                  bbox_to_anchor=(1.02, 1.0), borderaxespad=0.0,
                  framealpha=0.9, columnspacing=0.8, handlelength=2.0)

    fig.suptitle(
        f'{site_label} — HFE Probe Temperature History\n'
        'Solid = TG (gradient bridge)  ·  Dashed = TR (reference TC)  ·  '
        f'Dim = excluded from validation (< {min_depth_cm} cm)',
        fontsize=11, weight='bold')

    save_figure(fig, out_name, output_dir=output_dir)
    plt.show()


def plot_single_model_validation(model_name, out_m, T_mean_m, T_at_sensor,
                                 resid_all, resid_deep, color, rmse_d,
                                 bias_d, mae_d, r2_d, *, sensors_data,
                                 deep_mask_data, z_cm, min_depth,
                                 zone_clr, zone_line, site_label, y_lim):
    """Single-model validation figure: profile + residuals + stats box."""
    fig, axes = plt.subplots(1, 3, figsize=(16, 7),
                             gridspec_kw={'width_ratios': [2.2, 1, 1.5]},
                             constrained_layout=True)

    ax = axes[0]
    T_max_m = out_m.T.max(axis=1)
    T_min_m = out_m.T.min(axis=1)
    ax.fill_betweenx(z_cm, T_min_m, T_max_m, alpha=0.15, color=color,
                     label='Diurnal envelope')
    ax.plot(T_mean_m, z_cm, color=color, lw=2.5, label=f'{model_name} (mean)')

    for i, s in enumerate(sensors_data):
        marker = 'o' if s['stype'] == 'TG' else ('s' if s['stype'] == 'TR' else '^')
        fc = '#2ECC71' if s['probe'] == 1 else '#F39C12'
        ec = 'k' if deep_mask_data[i] else '#AAAAAA'
        alpha_s = 1.0 if deep_mask_data[i] else 0.35
        ax.plot(s['T_eq'], s['depth_cm'], marker, ms=10, mfc=fc, mec=ec,
                mew=1.5, zorder=5, alpha=alpha_s)

    ax.axhspan(0, min_depth, color=zone_clr, alpha=0.5, zorder=0)
    ax.axhline(min_depth, color=zone_line, lw=1.2, ls='--', alpha=0.7)
    ax.text(T_mean_m.min() + 0.5, min_depth / 2,
            f'diurnal zone\n(< {min_depth} cm)', fontsize=8,
            ha='left', va='center', color=zone_line, style='italic')

    handles = [
        Line2D([0], [0], color=color, lw=2.5, label=f'{model_name}'),
        plt.Rectangle((0, 0), 1, 1, fc=color, alpha=0.15,
                      label='Diurnal envelope'),
        Line2D([0], [0], marker='o', color='w', mfc='#2ECC71', mec='k',
               ms=8, label='Probe 1'),
        Line2D([0], [0], marker='o', color='w', mfc='#F39C12', mec='k',
               ms=8, label='Probe 2'),
    ]
    ax.legend(handles=handles, fontsize=8, loc='upper left',
              bbox_to_anchor=(0.0, -0.10), ncol=4, borderaxespad=0.0)
    ax.set_xlabel('Temperature  [K]', fontsize=11)
    ax.set_ylabel('Depth  [cm]', fontsize=11)
    ax.set_title('(a)  Temperature Profile', fontsize=12, weight='bold')
    ax.invert_yaxis()
    ax.set_ylim(y_lim, 0)
    ax.grid(True, alpha=0.15)

    ax = axes[1]
    for i, s in enumerate(sensors_data):
        alpha_s = 1.0 if deep_mask_data[i] else 0.25
        marker = 'o' if s['stype'] == 'TG' else ('s' if s['stype'] == 'TR' else '^')
        ax.plot([0, resid_all[i]], [s['depth_cm']] * 2, '-',
                color=color, alpha=alpha_s, lw=1.5)
        ax.plot(resid_all[i], s['depth_cm'], marker, ms=7,
                mfc=color, mec='k', alpha=alpha_s, zorder=5)
    ax.axvline(0, color='k', lw=0.8, ls='--')
    ax.axvspan(-1, 1, color='#ABEBC6', alpha=0.3, label='±1 K')
    ax.axhspan(0, min_depth, color=zone_clr, alpha=0.5, zorder=0)
    ax.axhline(min_depth, color=zone_line, lw=1.2, ls='--', alpha=0.7)
    ax.set_xlabel('Model − Obs  [K]', fontsize=10)
    ax.set_ylabel('Depth  [cm]', fontsize=10)
    ax.set_title('(b)  Residuals', fontsize=11, weight='bold')
    ax.invert_yaxis()
    ax.set_ylim(y_lim, 0)
    ax.legend(fontsize=8, loc='upper left',
              bbox_to_anchor=(0.0, -0.10), borderaxespad=0.0)

    ax = axes[2]
    ax.axis('off')
    lines = []
    lines.append(f'Model: {model_name}')
    lines.append('─' * 32)
    lines.append('')
    lines.append(f'  {"Sensor":<9} {"Depth":>5} {"T_obs":>7} {"T_mod":>7} {"Δ":>6}  {"✓":>2}')
    lines.append(f'  {"─"*9} {"─"*5} {"─"*7} {"─"*7} {"─"*6}  {"─"*2}')
    for i, s in enumerate(sensors_data):
        tag = '✓' if deep_mask_data[i] else '·'
        lines.append(
            f'  {s["sensor"]:<9} {s["depth_cm"]:>5.0f} '
            f'{s["T_eq"]:>7.2f} {T_at_sensor[i]:>7.2f} '
            f'{resid_all[i]:>+6.2f}  {tag:>2}'
        )
    lines.append('')
    lines.append(f'  Deep sensors (≥ {min_depth} cm):')
    lines.append(f'    RMSE  = {rmse_d:.3f} K')
    lines.append(f'    Bias  = {bias_d:+.3f} K')
    lines.append(f'    MAE   = {mae_d:.3f} K')
    lines.append(f'    R²    = {r2_d:.4f}')

    ax.text(0.05, 0.95, '\n'.join(lines), transform=ax.transAxes,
            fontsize=8.5, fontfamily='monospace', verticalalignment='top',
            bbox=dict(boxstyle='round,pad=0.5', facecolor='#F8F9F9',
                      edgecolor='#BDC3C7', alpha=0.9))
    ax.set_title('(c)  Statistics', fontsize=11, weight='bold')

    fig.suptitle(f'{site_label} HFE Validation — {model_name}\n'
                 f'RMSE = {rmse_d:.2f} K  (deep sensors ≥ {min_depth} cm)',
                 fontsize=13, weight='bold')
    plt.show()
    return fig


def plot_head_to_head(bundle, stats, z_cm_model, min_depth_cm, *,
                      clr_hayne, clr_disc, zone_clr, zone_line, site_label,
                      q_basal, y_lim, out_name, output_dir, site_suptitle):
    """Three-panel Hayne vs Discrete comparison (overlay + dual residuals + stats)."""
    sensors = bundle['sensors']
    deep_mask = bundle['deep_mask']

    out_h = stats['out_hayne']
    out_d = stats['out_disc']
    T_mean_h = stats['T_mean_hayne']
    T_mean_d = stats['T_mean_disc']
    resid_h = stats['resid_hayne_all']
    resid_d = stats['resid_disc_all']
    rmse_h = stats['rmse_hayne']
    rmse_d = stats['rmse_disc']
    bias_h = stats['bias_hayne']
    bias_d = stats['bias_disc']
    mae_h = stats['mae_hayne']
    mae_d = stats['mae_disc']
    r2_h = stats['r2_hayne']
    r2_d = stats['r2_disc']

    fig, axes = plt.subplots(1, 3, figsize=(17, 7),
                             gridspec_kw={'width_ratios': [2.2, 1.2, 1.5]},
                             constrained_layout=True)

    # Panel (a) — overlaid profiles
    ax = axes[0]
    T_max_h = out_h.T.max(axis=1); T_min_h = out_h.T.min(axis=1)
    T_max_d = out_d.T.max(axis=1); T_min_d = out_d.T.min(axis=1)
    ax.fill_betweenx(z_cm_model, T_min_h, T_max_h, alpha=0.08, color=clr_hayne)
    ax.fill_betweenx(z_cm_model, T_min_d, T_max_d, alpha=0.08, color=clr_disc)
    ax.plot(T_mean_h, z_cm_model, color=clr_hayne, lw=2.5, ls='--',
            label='Hayne 2017')
    ax.plot(T_mean_d, z_cm_model, color=clr_disc, lw=2.5, ls='-',
            label='Discrete Layers')

    for i, s in enumerate(sensors):
        marker = 'o' if s['stype'] == 'TG' else ('s' if s['stype'] == 'TR' else '^')
        fc = '#2ECC71' if s['probe'] == 1 else '#F39C12'
        ec = 'k' if deep_mask[i] else '#AAAAAA'
        alpha_s = 1.0 if deep_mask[i] else 0.35
        ax.plot(s['T_eq'], s['depth_cm'], marker, ms=10, mfc=fc, mec=ec,
                mew=1.5, zorder=5, alpha=alpha_s)

    handles = [
        Line2D([0], [0], color=clr_hayne, lw=2.5, ls='--', label='Hayne 2017'),
        Line2D([0], [0], color=clr_disc, lw=2.5, ls='-', label='Discrete Layers'),
        Line2D([0], [0], marker='o', color='w', mfc='#2ECC71', mec='k',
               ms=8, label='Probe 1'),
        Line2D([0], [0], marker='o', color='w', mfc='#F39C12', mec='k',
               ms=8, label='Probe 2'),
    ]
    ax.legend(handles=handles, fontsize=8, loc='upper left',
              bbox_to_anchor=(0.0, -0.10), ncol=4, borderaxespad=0.0)
    ax.axhspan(0, min_depth_cm, color=zone_clr, alpha=0.5, zorder=0)
    ax.axhline(min_depth_cm, color=zone_line, lw=1.2, ls='--', alpha=0.7)
    ax.set_xlabel('Temperature  [K]', fontsize=11)
    ax.set_ylabel('Depth  [cm]', fontsize=11)
    ax.set_title('(a)  Mean Temperature Profiles', fontsize=12, weight='bold')
    ax.invert_yaxis()
    ax.set_ylim(y_lim, 0)
    ax.grid(True, alpha=0.15)

    # Panel (b) — dual residuals
    ax = axes[1]
    offset = 1.0
    for i, s in enumerate(sensors):
        alpha_s = 1.0 if deep_mask[i] else 0.25
        marker = 'o' if s['stype'] == 'TG' else ('s' if s['stype'] == 'TR' else '^')
        d_cm = s['depth_cm']
        ax.plot([0, resid_h[i]], [d_cm - offset] * 2, '-',
                color=clr_hayne, alpha=alpha_s, lw=1.3)
        ax.plot(resid_h[i], d_cm - offset, marker, ms=6,
                mfc=clr_hayne, mec='k', alpha=alpha_s, zorder=5)
        ax.plot([0, resid_d[i]], [d_cm + offset] * 2, '-',
                color=clr_disc, alpha=alpha_s, lw=1.3)
        ax.plot(resid_d[i], d_cm + offset, marker, ms=6,
                mfc=clr_disc, mec='k', alpha=alpha_s, zorder=5)

    ax.axvline(0, color='k', lw=0.8, ls='--')
    ax.axvspan(-1, 1, color='#ABEBC6', alpha=0.3, label='±1 K band')
    ax.axhspan(0, min_depth_cm, color=zone_clr, alpha=0.5, zorder=0)
    ax.axhline(min_depth_cm, color=zone_line, lw=1.2, ls='--', alpha=0.7)
    res_handles = [
        Line2D([0], [0], color=clr_hayne, lw=2, label='Hayne'),
        Line2D([0], [0], color=clr_disc, lw=2, label='Discrete'),
    ]
    ax.legend(handles=res_handles, fontsize=8, loc='upper left',
              bbox_to_anchor=(0.0, -0.10), ncol=2, borderaxespad=0.0)
    ax.set_xlabel('Model − Obs  [K]', fontsize=10)
    ax.set_ylabel('Depth  [cm]', fontsize=10)
    ax.set_title('(b)  Residuals', fontsize=11, weight='bold')
    ax.invert_yaxis()
    ax.set_ylim(y_lim, 0)

    # Panel (c) — stats
    ax = axes[2]
    ax.axis('off')
    lines = []
    lines.append('Head-to-Head Comparison')
    lines.append(f'Deep sensors ≥ {min_depth_cm} cm  (N = {deep_mask.sum()})')
    lines.append('═' * 40)
    lines.append('')
    lines.append(f'  {"Metric":<14} {"Hayne":>10} {"Discrete":>10} {"Winner":>10}')
    lines.append(f'  {"─"*14} {"─"*10} {"─"*10} {"─"*10}')
    for label, vh, vd in [
        ('RMSE (K)', rmse_h, rmse_d),
        ('|Bias| (K)', abs(bias_h), abs(bias_d)),
        ('MAE (K)', mae_h, mae_d),
    ]:
        w = 'Discrete' if vd < vh else ('Hayne' if vh < vd else 'Tie')
        lines.append(f'  {label:<14} {vh:>10.3f} {vd:>10.3f} {w:>10}')
    lines.append(f'  {"R²":<14} {r2_h:>10.4f} {r2_d:>10.4f}')
    lines.append('')
    lines.append('═' * 40)
    pct = (1 - rmse_d / rmse_h) * 100
    winner = 'Discrete' if rmse_d < rmse_h else 'Hayne'
    lines.append(f'  {winner} is {abs(pct):.0f}% better (RMSE)')
    lines.append('')
    lines.append('  Per-sensor residuals (deep):')
    lines.append(f'  {"Sensor":<9} {"Depth":>5}  {"Hayne":>7}  {"Disc":>7}')
    lines.append(f'  {"─"*9} {"─"*5}  {"─"*7}  {"─"*7}')
    for i, s in enumerate(sensors):
        if deep_mask[i]:
            lines.append(
                f'  {s["sensor"]:<9} {s["depth_cm"]:>5.0f}  '
                f'{resid_h[i]:>+7.2f}  {resid_d[i]:>+7.2f}'
            )

    ax.text(0.05, 0.97, '\n'.join(lines), transform=ax.transAxes,
            fontsize=8.5, fontfamily='monospace', verticalalignment='top',
            bbox=dict(boxstyle='round,pad=0.5', facecolor='#F8F9F9',
                      edgecolor='#BDC3C7', alpha=0.9))
    ax.set_title('(c)  Statistics', fontsize=11, weight='bold')

    fig.suptitle(site_suptitle, fontsize=13, weight='bold')
    save_figure(fig, out_name, output_dir=output_dir)
    plt.show()


# --- Solver runner ----------------------------------------------------

def run_site_solvers(site, grid, t_s, hayne_params, *,
                     K_func_hayne, K_func_disc, rho_func_disc, cp_func,
                     s0_nominal, sun_scale, t_lunar, n_lunations, spinup_tol):
    """Run both Hayne and Discrete solvers at one Apollo site.

    Returns a dict with out_hayne, out_disc, T_mean_hayne, T_mean_disc,
    residuals, RMSEs, biases, MAEs, R² for downstream plotting.
    """
    from scipy.stats import pearsonr

    from lunar.solver import PixelInputs, solve_pixel

    z_mid = grid.z_mid
    _lat  = site.get('lat', site.get('LAT'))
    _alb  = site.get('albedo', site.get('ALBEDO'))
    _eps  = site.get('emissivity', site.get('EMISSIVITY'))
    cos_lat = np.cos(np.deg2rad(_lat))
    S0 = s0_nominal * sun_scale
    phase = 2.0 * np.pi * t_s / t_lunar
    insolation = S0 * cos_lat * np.maximum(0.0, np.cos(phase))

    # Hayne ----------------------------------------------------------
    K_init_h = K_func_hayne(np.full_like(z_mid, site['T_MEAN_EFF']), z_mid,
                            Ks=hayne_params['K_SURFACE'],
                            Kd=hayne_params['K_DEEP'],
                            H=hayne_params['H_PARAM'],
                            chi=hayne_params['CHI'])
    R_z_h = np.cumsum(grid.dz / K_init_h)
    T_init_h = site['T_MEAN_EFF'] + site['Q_BASAL'] * R_z_h

    inputs_h = PixelInputs(
        grid=grid, t=t_s, bc_mode='radiative',
        insolation=insolation, albedo=_alb,
        emissivity=_eps, Q_b=site['Q_BASAL'], T_init=T_init_h,
        n_lunations_spinup=n_lunations, spinup_tol_K=spinup_tol,
    )
    out_h = solve_pixel(inputs_h)

    # Discrete --------------------------------------------------------
    K_init_d = K_func_disc(np.full_like(z_mid, site['T_MEAN_EFF']), z_mid)
    R_z_d = np.cumsum(grid.dz / K_init_d)
    T_init_d = site['T_MEAN_EFF'] + site['Q_BASAL'] * R_z_d

    inputs_d = PixelInputs(
        grid=grid, t=t_s, bc_mode='radiative',
        insolation=insolation, albedo=_alb,
        emissivity=_eps, Q_b=site['Q_BASAL'], T_init=T_init_d,
        n_lunations_spinup=n_lunations, spinup_tol_K=spinup_tol,
        K_func=K_func_disc, rho_func=rho_func_disc, cp_func=cp_func,
    )
    out_d = solve_pixel(inputs_d)

    return {'out_hayne': out_h, 'out_disc': out_d, 'insolation': insolation}


def compute_validation_stats(bundle, run, z_cm_model):
    """Interpolate model means to sensor depths and compute RMSE / bias / MAE."""
    from scipy.stats import pearsonr

    depth_cm_all = bundle['depth_cm_all']
    T_eq_all = bundle['T_eq_all']
    deep_mask = bundle['deep_mask']

    T_mean_hayne = run['out_hayne'].T.mean(axis=1)
    T_mean_disc = run['out_disc'].T.mean(axis=1)
    T_h_at = np.interp(depth_cm_all, z_cm_model, T_mean_hayne)
    T_d_at = np.interp(depth_cm_all, z_cm_model, T_mean_disc)

    resid_h_all = T_h_at - T_eq_all
    resid_d_all = T_d_at - T_eq_all
    resid_h_deep = resid_h_all[deep_mask]
    resid_d_deep = resid_d_all[deep_mask]

    rmse_h = float(np.sqrt(np.mean(resid_h_deep ** 2)))
    bias_h = float(np.mean(resid_h_deep))
    mae_h = float(np.mean(np.abs(resid_h_deep)))
    r_h, _ = pearsonr(T_eq_all[deep_mask], T_h_at[deep_mask])

    rmse_d = float(np.sqrt(np.mean(resid_d_deep ** 2)))
    bias_d = float(np.mean(resid_d_deep))
    mae_d = float(np.mean(np.abs(resid_d_deep)))
    r_d, _ = pearsonr(T_eq_all[deep_mask], T_d_at[deep_mask])

    return {
        'out_hayne': run['out_hayne'], 'out_disc': run['out_disc'],
        'T_mean_hayne': T_mean_hayne, 'T_mean_disc': T_mean_disc,
        'T_hayne_at_sensor': T_h_at, 'T_disc_at_sensor': T_d_at,
        'resid_hayne_all': resid_h_all, 'resid_disc_all': resid_d_all,
        'resid_hayne_deep': resid_h_deep, 'resid_disc_deep': resid_d_deep,
        'rmse_hayne': rmse_h, 'rmse_disc': rmse_d,
        'bias_hayne': bias_h, 'bias_disc': bias_d,
        'mae_hayne': mae_h, 'mae_disc': mae_d,
        'r2_hayne': r_h ** 2, 'r2_disc': r_d ** 2,
    }
