"""Apollo HFE deep-sensor stability helpers.

Functions:
  iso_to_seconds            -- ISO-8601 -> Unix timestamps
  find_stable_window        -- pick the trailing equilibrium window per sensor
  extract_sensor_stability  -- load HFE depth tables and reduce to per-sensor T_eq
"""
from __future__ import annotations

from datetime import datetime, timezone

import numpy as np

from lunar.validation import load_apollo_hfe_depth


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
