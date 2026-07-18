"""Shadowing-corrected K_d retrieval: the missing AOGS headline.

The density study held K at each site's certified K_d* (retrieved under
STANDARD forcing). This script answers the direct question: if the
DEM-shadowed forcing is the truth, what deep conductivity does each
borehole require? Same retrieval recipe as the letter (sweep K_d,
solve to certified periodic equilibrium, score deep-sensor RMSE, take
the parabolic vertex of the misfit bowl), with the continuous Hayne
density profile so ONLY the forcing differs from the letter's result.

Two-pass sweep per site: coarse 0.5 mW grid bracketing the certified
value, then a 0.125 mW refinement around the coarse minimum.

Outputs -> results/aogs_kd_shadowed.json
Run:  .venv/bin/python code/pipeline/compute/aogs_kd_shadowed.py  (~5 min)
"""
from __future__ import annotations

import functools
import json
import multiprocessing as mp
import pathlib
import sys

import numpy as np

sys.path.insert(0, str(next(a for a in pathlib.Path(__file__).resolve().parents if (a / "code" / "src" / "lunar").is_dir()) / "code" / "src"))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from lunar._bootstrap import find_repo_root  # noqa: E402
from lunar.config import DT_STEP, GRID, HAYNE, SITES  # noqa: E402
from lunar.grid import make_geometric_grid  # noqa: E402
from lunar.solver import periodic_time_grid  # noqa: E402
from lunar.properties import conductivity_hayne, specific_heat  # noqa: E402
from lunar.equilibrium import solve_periodic_equilibrium  # noqa: E402
from lunar.apollo_helpers import extract_sensor_stability  # noqa: E402

import s1_sensitivity as base  # noqa: E402

ROOT = find_repo_root()
AOGS = next(a for a in pathlib.Path(__file__).resolve().parents if a.name == "aogs")   # this bundle (self-contained)
OUT = AOGS / "results" / "aogs_kd_shadowed.json"


def rmse_at(args):
    site_key, kd_mw, insol = args
    s = SITES[site_key]
    g = make_geometric_grid(**GRID)
    t = periodic_time_grid(DT_STEP)
    K = functools.partial(conductivity_hayne, Ks=HAYNE["K_S"],
                          Kd=kd_mw * 1e-3, H=HAYNE["H"], chi=HAYNE["CHI"])
    cp = functools.partial(specific_heat, model="hayne")
    eq = solve_periodic_equilibrium(
        g, np.asarray(t), np.asarray(insol), s["albedo"], s["emissivity"],
        s["Q_BASAL"], K_func=K, cp_func=cp, rho_func=None, n_inner=24)
    obs = extract_sensor_stability(s["mission"], s["MIN_DEPTH_CM"])
    dm = obs["deep_mask"]
    T_obs = np.asarray(obs["T_eq_all"])[dm]
    T_mod = np.interp(np.asarray(obs["depth_cm_all"])[dm] / 100.0,
                      g.z_mid, eq.T_mean)
    return site_key, kd_mw, float(np.sqrt(np.mean((T_mod - T_obs) ** 2)))


def vertex(kds, rs):
    """Parabolic vertex through the minimum and its neighbours."""
    i = int(np.argmin(rs))
    i = max(1, min(len(kds) - 2, i))
    x = np.asarray(kds[i - 1:i + 2], float)
    y = np.asarray(rs[i - 1:i + 2], float)
    c = np.polyfit(x, y, 2)
    return float(-c[1] / (2 * c[0]))


def main():
    dem, ppd = base.load_dem()
    t = periodic_time_grid(DT_STEP)
    kd_cert = json.loads((ROOT / "results" / "kd_retrieval_results.json")
                         .read_text())
    forc = {}
    for sk in ("A15", "A17"):
        s = SITES[sk]
        az, hor = base.horizon_profile(dem, ppd, s["lat"], s["lon"])
        forc[sk] = base.shadowed_insolation(s["lat"], t, az, hor)

    res = {}
    with mp.Pool(min(8, mp.cpu_count() - 1)) as pool:
        for sk in ("A15", "A17"):
            k0 = kd_cert[sk]["kd_star"] * 1e3
            coarse = [round(k0 + d, 3) for d in np.arange(-2.0, 2.01, 0.5)]
            out = pool.map(rmse_at, [(sk, k, forc[sk]) for k in coarse])
            kds = [o[1] for o in out]
            rs = [o[2] for o in out]
            k1 = kds[int(np.argmin(rs))]
            fine = [round(k1 + d, 3) for d in np.arange(-0.5, 0.51, 0.125)
                    if round(k1 + d, 3) not in kds]
            out2 = pool.map(rmse_at, [(sk, k, forc[sk]) for k in fine])
            kds += [o[1] for o in out2]
            rs += [o[2] for o in out2]
            order = np.argsort(kds)
            kds = [kds[i] for i in order]
            rs = [rs[i] for i in order]
            ks = vertex(kds, rs)
            res[sk] = dict(kd_star_standard_mW=k0,
                           kd_star_shadowed_mW=round(ks, 3),
                           shift_mW=round(ks - k0, 3),
                           rmse_min_K=float(min(rs)),
                           kd_grid_mW=kds, rmse_K=rs)
            print(f"  {sk}: K_d* standard {k0:.2f} -> shadowed {ks:.2f} mW "
                  f"(shift {ks - k0:+.2f}; min RMSE {min(rs):.3f} K)")

    OUT.write_text(json.dumps(dict(
        meta=dict(forcing="DEM-shadowed (aogs_sensitivity horizons)",
                  rho="continuous Hayne (only the forcing differs from "
                      "the letter's retrieval)", n_inner=24, dem_ppd=ppd),
        sites=res), indent=1))
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
