"""Writer for results/aogs_crossite.json — homogeneous baseline + cross-site.

AUDIT 2026-07-12: this JSON existed with NO committed writer (it was
produced by a scratch session), violating the writer-script law while
feeding four poster numbers (\\rmsehom*, \\xferat*). This script restores
provenance: it computes the documented recipe (AOGS_FINDINGS.md §4),
compares against the archived values, and rewrites the JSON with full
metadata.

Recipe (pinned by reproduction — see meta.recipe in the output):
  homogeneous   constant contact conductivity K_c = the site's certified
                K_d* (radiative chi(T/350)^3 term KEPT — it is part of the
                Hayne K(T,z) form, not a layering choice), constant
                rho = 1800 kg m^-3, Hayne cp(T), DEM-shadowed forcing.
  cross-site    the other site's best density-coupled STRUCTURE (rho triple
                + z1/z2 boundaries) transplanted, with K_c(rho) evaluated at
                the TARGET site's certified K_d* — a structure-only transfer
                (deep conductivity remains a site property), scored against
                the target's deep sensors under its shadowed forcing.
                (Reproduces the archived 1.6354 / 1.7273 K exactly; the
                full transplant with the home K_d* would give 1.43 / 1.38.)
  native_best   copied from aogs_density_study.json for convenience.

All solves at the study's n_inner=24 (differences/ratios quoted on the
poster compare like-for-like within the n=24 family; the study's best
configs are separately certified at n=96 in aogs_density_study.json).

Run:  .venv/bin/python code/pipeline/compute/aogs_crossite.py [--verify-only]
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
from lunar.properties import specific_heat  # noqa: E402
from lunar.equilibrium import solve_periodic_equilibrium  # noqa: E402
from lunar.apollo_helpers import extract_sensor_stability  # noqa: E402

import s1_sensitivity as base  # noqa: E402
import s2_density_study as ds  # noqa: E402

ROOT = find_repo_root()
OUT = ROOT / "results" / "aogs_crossite.json"
N_INNER = 24
RHO_HOM = 1800.0


def K_homogeneous(T, z, kd_star):
    """Constant K_c = K_d* with the Hayne radiative term (chi(T/350)^3)."""
    kc = np.full_like(np.asarray(z, float), kd_star)
    return kc * (1.0 + HAYNE["CHI"] * (np.asarray(T, float)
                                       / HAYNE["T_REF"]) ** 3)


def solve_rmse(args):
    """One certified solve -> deep-sensor RMSE at `site` (its own forcing)."""
    (label, site, K, rho, insol) = args
    s = SITES[site]
    g = make_geometric_grid(**GRID)
    t = periodic_time_grid(DT_STEP)
    cp = functools.partial(specific_heat, model="hayne")
    eq = solve_periodic_equilibrium(
        g, np.asarray(t), np.asarray(insol), s["albedo"], s["emissivity"],
        s["Q_BASAL"], K_func=K, cp_func=cp, rho_func=rho, n_inner=N_INNER)
    obs = extract_sensor_stability(s["mission"], s["MIN_DEPTH_CM"])
    dm = obs["deep_mask"]
    T_obs = np.asarray(obs["T_eq_all"])[dm]
    T_mod = np.interp(np.asarray(obs["depth_cm_all"])[dm] / 100.0,
                      g.z_mid, eq.T_mean)
    return label, float(np.sqrt(np.mean((T_mod - T_obs) ** 2)))


def main(verify_only=False):
    study = json.loads(
        (ROOT / "results" / "aogs_density_study.json").read_text())
    dem, ppd = base.load_dem()
    t = periodic_time_grid(DT_STEP)

    forc, kd, best = {}, {}, {}
    for sk in ("A15", "A17"):
        s = SITES[sk]
        az, hor = base.horizon_profile(dem, ppd, s["lat"], s["lon"])
        forc[sk] = base.shadowed_insolation(s["lat"], t, az, hor)
        kd[sk] = study["sites"][sk]["kd_star_used"]
        best[sk] = min((r for r in study["runs"] if r["site"] == sk
                        and r["branch"] == "coupled" and r["rho"] != "hayne"),
                       key=lambda r: r["rmse_K"])

    jobs = []
    for sk in ("A15", "A17"):
        jobs.append((f"{sk}_homogeneous", sk,
                     functools.partial(K_homogeneous, kd_star=kd[sk]),
                     functools.partial(ds.rho_layered, z1=0.0, z2=0.0,
                                       r1=RHO_HOM, r2=RHO_HOM, r3=RHO_HOM),
                     forc[sk]))
    for src, dst in (("A15", "A17"), ("A17", "A15")):
        w = best[src]
        r1, r2, r3 = w["rho"]
        jobs.append((f"{src}_config_at_{dst}", dst,
                     functools.partial(ds.K_coupled, z1=w["z1_m"],
                                       z2=w["z2_m"], r1=r1, r2=r2, r3=r3,
                                       kd_star=kd[dst]),   # target K_d*: structure-only transfer
                     functools.partial(ds.rho_layered, z1=w["z1_m"],
                                       z2=w["z2_m"], r1=r1, r2=r2, r3=r3),
                     forc[dst]))

    with mp.Pool(min(4, mp.cpu_count() - 1)) as pool:
        res = dict(pool.map(solve_rmse, jobs))

    old = json.loads(OUT.read_text()) if OUT.exists() else {}
    print("key                     new      archived   |diff|")
    for k, v in res.items():
        o = old.get(k)
        d = abs(v - o) if o is not None else float("nan")
        print(f"{k:22s} {v:8.4f}  {o if o is not None else 'n/a':>9}  {d:.4f}"
              if o is not None else f"{k:22s} {v:8.4f}       n/a")

    if verify_only:
        return

    out = dict(
        meta=dict(
            writer="aogs_crossite.py",
            n_inner=N_INNER, dem_ppd=ppd, rho_homogeneous=RHO_HOM,
            recipe=dict(
                homogeneous="K_c const = site K_d* (radiative term kept), "
                            "rho const = 1800, Hayne cp, shadowed forcing",
                crossite="other site's best coupled STRUCTURE (rho + "
                         "boundaries) with K_c(rho) at the TARGET site's "
                         "K_d*; scored at the target site under its "
                         "shadowed forcing"),
        ),
        **{k: v for k, v in res.items()},
        native_best={sk: best[sk]["rmse_K"] for sk in ("A15", "A17")},
    )
    OUT.write_text(json.dumps(out, indent=1))
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main(verify_only="--verify-only" in sys.argv)
