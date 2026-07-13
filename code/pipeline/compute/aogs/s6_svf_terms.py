"""Quantify the (1-SVF) terrain radiation terms the abstract promises.

The study's forcing only zeroes the direct beam below the horizon; the
sky-view factor (SVF = mean cos^2 H over azimuth, the same formula the
poster quotes) has been diagnostic only. On an airless body the terrain
that blocks the horizon also (a) glows in the IR at ~the local surface
temperature and (b) reflects sunlight. Both scale with (1-SVF) ~ 1-1.5%
-- the same order as the direct-beam energy loss the poster calls
first-order -- so they must be quantified, not assumed away.

Implementation WITHOUT touching src/lunar (both effects enter through
existing solver arguments):
  IR self-heating   with T_terrain ~= T_surface (infinite-slope
                    approximation), net thermal emission becomes
                    eps*sigma*T^4 * (1 - eps*(1-SVF)), i.e. an
                    effective emissivity  eps_eff = eps*(1 - eps*(1-SVF)).
  reflected sun     terrain visible over (1-SVF) reflects albedo*S_un;
                    added to the forcing array (the solver applies the
                    (1-albedo) absorption internally -- house
                    convention). Terrain illumination uses the
                    UNSHADOWED S: the slopes that form our horizon are
                    lit precisely when they block our sun.

Three certified solves per site at the density study's best coupled
config (pulled from the archive, never hand-typed):
  a) shadowed baseline   b) + IR self-heating   c) + IR + reflected sun.

Outputs -> results/aogs_svf_terms.json
Run:  .venv/bin/python code/pipeline/compute/aogs_svf_terms.py  (~2 min)
"""
from __future__ import annotations

import functools
import json
import multiprocessing as mp
import pathlib
import sys

import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3] / "src"))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from lunar._bootstrap import find_repo_root  # noqa: E402
from lunar.config import DT_STEP, GRID, SITES  # noqa: E402
from lunar.grid import make_geometric_grid  # noqa: E402
from lunar.solver import periodic_time_grid  # noqa: E402
from lunar.properties import specific_heat  # noqa: E402
from lunar.equilibrium import solve_periodic_equilibrium  # noqa: E402
from lunar.apollo_helpers import extract_sensor_stability  # noqa: E402

import s1_sensitivity as base  # noqa: E402
import s2_density_study as ds  # noqa: E402  (rho_layered/K_coupled)

ROOT = find_repo_root()
OUT = ROOT / "results" / "aogs_svf_terms.json"


def best_coupled(archive, site):
    recs = [r for r in archive["runs"]
            if r["site"] == site and r["branch"] == "coupled"
            and r["rho"] != "hayne"]
    return min(recs, key=lambda r: r["rmse_K"])


def solve_case(args):
    (sk, variant, insol, emissivity, win, kd_star) = args
    s = SITES[sk]
    g = make_geometric_grid(**GRID)
    t = periodic_time_grid(DT_STEP)
    z1, z2 = win["z1_m"], win["z2_m"]
    r1, r2, r3 = win["rho"]
    rho = functools.partial(ds.rho_layered, z1=z1, z2=z2, r1=r1, r2=r2, r3=r3)
    K = functools.partial(ds.K_coupled, z1=z1, z2=z2, r1=r1, r2=r2, r3=r3,
                          kd_star=kd_star)
    cp = functools.partial(specific_heat, model="hayne")
    eq = solve_periodic_equilibrium(
        g, np.asarray(t), np.asarray(insol), s["albedo"], emissivity,
        s["Q_BASAL"], K_func=K, cp_func=cp, rho_func=rho, n_inner=24)
    obs = extract_sensor_stability(s["mission"], s["MIN_DEPTH_CM"])
    dm = obs["deep_mask"]
    T_obs = np.asarray(obs["T_eq_all"])[dm]
    z_obs = np.asarray(obs["depth_cm_all"])[dm] / 100.0
    T_mod = np.interp(z_obs, g.z_mid, eq.T_mean)
    return sk, variant, dict(
        rmse_K=float(np.sqrt(np.mean((T_mod - T_obs) ** 2))),
        T_mean_at_sensors=[float(v) for v in T_mod],
        anchor_K=float(np.interp(0.55, g.z_mid, eq.T_mean)))


def main():
    archive = json.loads(
        (ROOT / "results" / "aogs_density_study.json").read_text())
    dem, ppd = base.load_dem()
    t = periodic_time_grid(DT_STEP)

    jobs, svfs, winners = [], {}, {}
    for sk in ("A15", "A17"):
        s = SITES[sk]
        az, hor = base.horizon_profile(dem, ppd, s["lat"], s["lon"])
        H = np.radians(hor)
        svf = float(np.mean(np.cos(H) ** 2))          # poster's SVF formula
        svfs[sk] = svf
        eps = s["emissivity"]
        eps_eff = eps * (1.0 - eps * (1.0 - svf))

        S_sh = base.shadowed_insolation(s["lat"], t, az, hor)
        S_un = base.standard_insolation(s["lat"], t)
        S_refl = S_sh + (1.0 - svf) * s["albedo"] * np.asarray(S_un)

        win = best_coupled(archive, sk)
        winners[sk] = win
        kd_star = archive["sites"][sk]["kd_star_used"]
        jobs += [(sk, "baseline", S_sh, eps, win, kd_star),
                 (sk, "ir_selfheat", S_sh, eps_eff, win, kd_star),
                 (sk, "ir_plus_reflected", S_refl, eps_eff, win, kd_star)]

    with mp.Pool(min(6, mp.cpu_count() - 1)) as pool:
        results = pool.map(solve_case, jobs)

    out = {"meta": dict(
        n_inner=24, dem_ppd=ppd,
        model="eps_eff = eps*(1-eps*(1-SVF)) [T_terr ~= T_s]; "
              "reflected = (1-SVF)*albedo*S_unshadowed added to forcing",
        note="terrain illumination = unshadowed S (horizon-forming slopes "
             "are lit when they block our sun)")}
    for sk in ("A15", "A17"):
        rr = {v: r for s_, v, r in results if s_ == sk}
        base_r = rr["baseline"]
        entry = dict(svf=svfs[sk],
                     winner=dict(z1_m=winners[sk]["z1_m"],
                                 z2_m=winners[sk]["z2_m"],
                                 rho=winners[sk]["rho"]),
                     variants=rr)
        for v in ("ir_selfheat", "ir_plus_reflected"):
            dT = np.asarray(rr[v]["T_mean_at_sensors"]) - \
                 np.asarray(base_r["T_mean_at_sensors"])
            entry[f"dT_sensors_{v}_K"] = [float(x) for x in dT]
            entry[f"dT_mean_{v}_K"] = float(dT.mean())
            entry[f"dRMSE_{v}_K"] = float(rr[v]["rmse_K"]
                                          - base_r["rmse_K"])
        out[sk] = entry
        print(f"  {sk}: SVF={svfs[sk]:.4f}  "
              f"IR self-heat dT={entry['dT_mean_ir_selfheat_K']:+.3f} K "
              f"(dRMSE {entry['dRMSE_ir_selfheat_K']:+.3f}); "
              f"+reflected dT={entry['dT_mean_ir_plus_reflected_K']:+.3f} K "
              f"(dRMSE {entry['dRMSE_ir_plus_reflected_K']:+.3f})")

    OUT.write_text(json.dumps(out, indent=1))
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
