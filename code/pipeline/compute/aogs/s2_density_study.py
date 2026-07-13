"""AOGS extensive density study: swept layer boundaries x two branches.

Extends aogs_sensitivity.py (which fixed the layer boundaries at
10/50 cm and held K at the certified per-site K_d*) into the full
study the AOGS talk needs:

  CONFIGURATIONS   3-layer density profiles whose BOUNDARIES are swept
                   (z1 in {5, 10, 20} cm, z2 in {30, 50, 80} cm) along
                   with the layer densities (rho1 <= rho2 <= rho3 over
                   literature-plausible values) -> 9 x 18 = 162
                   configurations per site per branch.

  BRANCH "cp"      densities enter the volumetric heat capacity rho*cp
                   only; K(T,z) stays the standard Hayne form at the
                   site's certified K_d* (as in the first sweep).

  BRANCH "coupled" densities ALSO set the contact conductivity through
                   the Hayne model's own internal K_c(rho) relation:
                   the model writes K_c(z) and rho(z) with the SAME
                   e^{-z/H} kernel, so eliminating the kernel gives
                       K_c(rho) = K_d - (K_d - K_s)(rho_d - rho)/(rho_d - rho_s),
                   linear between the (K_s, rho_s) and (K_d, rho_d)
                   endpoints, with K_d = the site's certified K_d*.
                   No new constants are introduced; rho > rho_d
                   extrapolates the same line (flagged in meta).

  FORCING          DEM-shadowed only (per aogs_sensitivity horizons).

Scoring: RMSE against the stable-window deep-sensor temperatures.
Certification: best configuration per site x branch re-run at the
production inner spin-up n=96.

Outputs -> results/aogs_density_study.json (read by notebook
08_aogs_study.ipynb, Part II).

Run:  .venv/bin/python code/pipeline/compute/aogs_density_study.py
(~45 min on 8 cores; ~650 certified equilibrium solves.)
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
from lunar.config import DT_STEP, GRID, HAYNE, SITES  # noqa: E402
from lunar.grid import make_geometric_grid  # noqa: E402
from lunar.solver import periodic_time_grid  # noqa: E402
from lunar.properties import conductivity_hayne, specific_heat  # noqa: E402
from lunar.equilibrium import solve_periodic_equilibrium  # noqa: E402
from lunar.apollo_helpers import extract_sensor_stability  # noqa: E402
from lunar.constants import RHO_SURFACE, RHO_DEEP, K_SURFACE  # noqa: E402

import s1_sensitivity as base  # noqa: E402  (DEM/horizon/shadow machinery)

ROOT = find_repo_root()
OUT = ROOT / "results" / "aogs_density_study.json"

# ── the swept configuration space (EDIT HERE) ────────────────────────────────
Z1_GRID = [0.05, 0.10, 0.20]             # skin|mid boundary [m]
Z2_GRID = [0.30, 0.50, 0.80]             # mid|deep boundary [m]
RHO1 = [1100.0, 1300.0, 1500.0]          # surface layer [kg m^-3]
RHO2 = [1500.0, 1700.0]                  # intermediate layer
RHO3 = [1700.0, 1800.0, 1900.0]          # deep layer
N_INNER_SWEEP = 24
N_INNER_CERT = 96


def rho_layered(z, z1, z2, r1, r2, r3):
    z = np.asarray(z, dtype=float)
    return np.where(z < z1, r1, np.where(z < z2, r2, r3))


def kc_of_rho(rho, kd_star):
    """The Hayne model's internal contact-conductivity--density relation.

    K_c(z) = K_d - (K_d - K_s) e^{-z/H} and rho(z) = rho_d -
    (rho_d - rho_s) e^{-z/H} share the kernel e^{-z/H}; eliminating it:
    K_c = K_d - (K_d - K_s) (rho_d - rho)/(rho_d - rho_s). Linear, and
    exact at both published endpoints.
    """
    frac = (RHO_DEEP - np.asarray(rho, float)) / (RHO_DEEP - RHO_SURFACE)
    return kd_star - (kd_star - K_SURFACE) * frac


def K_coupled(T, z, z1, z2, r1, r2, r3, kd_star):
    """Layered-density conductivity: Hayne radiative term x K_c(rho)."""
    rho = rho_layered(z, z1, z2, r1, r2, r3)
    kc = kc_of_rho(rho, kd_star)
    return kc * (1.0 + HAYNE["CHI"] * (np.asarray(T, float)
                                       / HAYNE["T_REF"]) ** 3)


def combos():
    return [(r1, r2, r3) for r1 in RHO1 for r2 in RHO2 for r3 in RHO3
            if r1 <= r2 <= r3]


def run_case(args):
    (site_key, branch, z1, z2, rho_spec, insol, kd_star, n_inner) = args
    s = SITES[site_key]
    g = make_geometric_grid(**GRID)
    t = periodic_time_grid(DT_STEP)
    cp = functools.partial(specific_heat, model="hayne")
    if rho_spec == "hayne":                       # continuous baseline
        rho = None
        K = functools.partial(conductivity_hayne, Ks=HAYNE["K_S"],
                              Kd=kd_star, H=HAYNE["H"], chi=HAYNE["CHI"])
    else:
        r1, r2, r3 = rho_spec
        rho = functools.partial(rho_layered, z1=z1, z2=z2, r1=r1, r2=r2,
                                r3=r3)
        if branch == "coupled":
            K = functools.partial(K_coupled, z1=z1, z2=z2, r1=r1, r2=r2,
                                  r3=r3, kd_star=kd_star)
        else:                                     # "cp": K stays Hayne
            K = functools.partial(conductivity_hayne, Ks=HAYNE["K_S"],
                                  Kd=kd_star, H=HAYNE["H"],
                                  chi=HAYNE["CHI"])
    eq = solve_periodic_equilibrium(
        g, np.asarray(t), np.asarray(insol), s["albedo"], s["emissivity"],
        s["Q_BASAL"], K_func=K, cp_func=cp, rho_func=rho, n_inner=n_inner)

    obs = extract_sensor_stability(s["mission"], s["MIN_DEPTH_CM"])
    dm = obs["deep_mask"]
    z_cm = np.asarray(obs["depth_cm_all"])[dm]
    T_obs = np.asarray(obs["T_eq_all"])[dm]
    T_mod = np.interp(z_cm / 100.0, g.z_mid, eq.T_mean)
    return dict(site=site_key, branch=branch, z1_m=z1, z2_m=z2,
                rho=(list(rho_spec) if rho_spec != "hayne" else "hayne"),
                rmse_K=float(np.sqrt(np.mean((T_mod - T_obs) ** 2))),
                anchor_K=float(eq.anchor_K), converged=bool(eq.converged),
                flux_closure=float(eq.flux_closure),
                T_model_at_sensors=[float(v) for v in T_mod],
                T_mean_profile=[float(v) for v in eq.T_mean])


def main():
    dem, ppd = base.load_dem()
    t = periodic_time_grid(DT_STEP)
    kd = json.loads((ROOT / "results" / "kd_retrieval_results.json")
                    .read_text())

    forcing, sites_meta = {}, {}
    for sk in ("A15", "A17"):
        s = SITES[sk]
        az, hor = base.horizon_profile(dem, ppd, s["lat"], s["lon"])
        forcing[sk] = base.shadowed_insolation(s["lat"], t, az, hor)
        obs = extract_sensor_stability(s["mission"], s["MIN_DEPTH_CM"])
        dm = obs["deep_mask"]
        sites_meta[sk] = dict(
            kd_star_used=kd[sk]["kd_star"],
            sensor_depth_cm=[float(v) for v in
                             np.asarray(obs["depth_cm_all"])[dm]],
            sensor_T_eq=[float(v) for v in np.asarray(obs["T_eq_all"])[dm]],
            sensor_T_std=[float(v) for v in
                          np.asarray(obs["T_std_all"])[dm]])

    cs = combos()
    jobs = []
    for sk in ("A15", "A17"):
        jobs.append((sk, "cp", 0.0, 0.0, "hayne", forcing[sk],
                     kd[sk]["kd_star"], N_INNER_SWEEP))
        for br in ("cp", "coupled"):
            for z1 in Z1_GRID:
                for z2 in Z2_GRID:
                    for c in cs:
                        jobs.append((sk, br, z1, z2, c, forcing[sk],
                                     kd[sk]["kd_star"], N_INNER_SWEEP))
    print(f"AOGS density study: {len(jobs)} solves "
          f"({len(Z1_GRID)}x{len(Z2_GRID)} boundaries x {len(cs)} density "
          f"combos x 2 branches x 2 sites, shadowed forcing) ...")
    with mp.Pool(min(8, mp.cpu_count() - 1)) as pool:
        rows = pool.map(run_case, jobs)

    cert = {}
    for sk in ("A15", "A17"):
        for br in ("cp", "coupled"):
            best = min((r for r in rows if r["site"] == sk
                        and r["branch"] == br and r["rho"] != "hayne"),
                       key=lambda r: r["rmse_K"])
            chk = run_case((sk, br, best["z1_m"], best["z2_m"],
                            tuple(best["rho"]), forcing[sk],
                            kd[sk]["kd_star"], N_INNER_CERT))
            cert[f"{sk}/{br}"] = dict(
                z1_m=best["z1_m"], z2_m=best["z2_m"], rho=best["rho"],
                rmse_sweep=best["rmse_K"], rmse_n96=chk["rmse_K"],
                drift_K=abs(best["rmse_K"] - chk["rmse_K"]))
            print(f"  {sk}/{br}: best z1={best['z1_m']:.2f} "
                  f"z2={best['z2_m']:.2f} rho={best['rho']}  "
                  f"RMSE {best['rmse_K']:.3f} K (n96: {chk['rmse_K']:.3f})")

    OUT.write_text(json.dumps(dict(
        meta=dict(z1_grid=Z1_GRID, z2_grid=Z2_GRID, rho1=RHO1, rho2=RHO2,
                  rho3=RHO3, n_inner_sweep=N_INNER_SWEEP, dem_ppd=ppd,
                  forcing="DEM-shadowed",
                  z_mid_m=[float(v) for v in
                           make_geometric_grid(**GRID).z_mid],
                  coupling="K_c(rho) = K_d* - (K_d* - K_s)(rho_d - rho)/"
                           "(rho_d - rho_s): the Hayne form's internal "
                           "linear K_c-rho relation (exact at both "
                           "published endpoints; rho>rho_d extrapolates "
                           "the same line)"),
        sites=sites_meta, certification=cert, runs=rows), indent=1))
    print(f"wrote {OUT} ({len(rows)} runs)")


if __name__ == "__main__":
    main()
