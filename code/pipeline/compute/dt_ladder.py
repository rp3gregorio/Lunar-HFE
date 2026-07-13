#!/usr/bin/env python3
"""dt ladder: certify K_d* convergence in the reported quantity.

House doctrine says certify THE REPORTED QUANTITY, not a proxy: sensor-band
<T> can look converged while K_d* still moves (and vice versa -- the flux
closure is grid-floored at ~0.25%). This script re-runs a small K_d sweep at
each requested time step on COMMENSURATE lunation grids
(``solver.periodic_time_grid``) and reports the vertex K_d* per dt, plus the
successive differences. Convergence criterion: |dK_d*| < 0.05 mW per halving.

History (results/dt_kdstar_certification_A17wide.json): with the
frozen-property march the A17 ladder was first order -- 7.699 / 7.397 /
7.251 mW at dt = 1800/900/450 s, Richardson limit 7.104 mW. That measurement
motivated ``config.CN_PICARD_SWEEPS`` (midpoint-property corrector in
``solver._step``); this script is the acceptance test for it and must be
re-run whenever DT_STEP, CN_PICARD_SWEEPS, or the solver march changes.

Writes results/dt_kdstar_certification_<tag>.json.
Run: python pipeline/compute/dt_ladder.py --site A17 --dts 1800 900
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys

import numpy as np

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from lunar.apollo_helpers import extract_sensor_stability
from lunar.config import (SITES, GRID, HAYNE, DT_STEP, CN_PICARD_SWEEPS,
                          EQ_Z_ANCHOR, EQ_N_INNER, EQ_MAX_OUTER, EQ_ANCHOR_TOL)
from lunar.equilibrium import solve_periodic_equilibrium
from lunar.grid import make_geometric_grid
from lunar.properties import conductivity_hayne, specific_heat
from lunar.solver import periodic_time_grid, standard_insolation

from retrieve_kd import _interp_profile_at_depths, kd_star_from_residuals

# Default 6-point brackets centred on the expected minima (dense enough that
# the vertex guard in kd_star_from_residuals stays quiet: spacing < 0.30 mW).
DEFAULT_BRACKETS = {"A15": (4.3e-3, 4.9e-3, 6), "A17": (6.7e-3, 7.5e-3, 6)}


def kd_star_at_dt(site_cfg, kd_grid, dt):
    """One mini K_d sweep at time step ``dt`` -> (K_d*, rmse per kd)."""
    obs = extract_sensor_stability(site_cfg["mission"],
                                   min_depth_cm=site_cfg["MIN_DEPTH_CM"])
    z_obs = np.asarray(obs["depth_cm_all"]) / 100.0
    T_obs = np.asarray(obs["T_eq_all"])
    deep = np.asarray(obs["deep_mask"], dtype=bool)
    z_deep, T_deep = z_obs[deep], T_obs[deep]

    grid_ = make_geometric_grid(**GRID)
    t_s = periodic_time_grid(dt)
    insol = standard_insolation(site_cfg["lat"], t_s)

    R = np.empty((z_deep.size, len(kd_grid)))
    for k, kd in enumerate(kd_grid):
        def k_func(T, z, kd=kd):
            return conductivity_hayne(T, z, Ks=HAYNE["K_S"], Kd=kd,
                                      H=HAYNE["H"], chi=HAYNE["CHI"])
        eq = solve_periodic_equilibrium(
            grid=grid_, t=t_s, insolation=insol,
            albedo=site_cfg["albedo"], emissivity=site_cfg["emissivity"],
            Q_b=site_cfg["Q_BASAL"], K_func=k_func,
            cp_func=lambda T: specific_heat(T, model="hayne"),
            T_guess=site_cfg["T_MEAN_EFF"],
            z_anchor=EQ_Z_ANCHOR, n_inner=EQ_N_INNER,
            max_outer=EQ_MAX_OUTER, anchor_tol_K=EQ_ANCHOR_TOL,
            hayne_params=(HAYNE["K_S"], kd, HAYNE["H"], HAYNE["CHI"]),
        )
        T_pred = _interp_profile_at_depths(
            z_deep, grid_.z_mid, eq.T_mean,
            context=f"{site_cfg['label']} dt ladder (dt={dt:g})")
        R[:, k] = T_pred - T_deep
    rmse = np.sqrt(np.mean(R**2, axis=0))
    kd_star, _ = kd_star_from_residuals(R, np.asarray(kd_grid))
    return float(kd_star), rmse


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--site", choices=sorted(SITES), required=True)
    ap.add_argument("--dts", type=float, nargs="+", default=[DT_STEP, DT_STEP / 2],
                    help="time steps [s], largest first (default: DT_STEP and half)")
    ap.add_argument("--bracket", type=float, nargs=3, metavar=("LO", "HI", "N"),
                    help="K_d bracket lo hi n_points [W/m/K] (default per site)")
    ap.add_argument("--tag", default=None, help="output-file suffix")
    args = ap.parse_args()

    site_cfg = SITES[args.site]
    lo, hi, npts = args.bracket if args.bracket else DEFAULT_BRACKETS[args.site]
    kd_grid = np.linspace(lo, hi, int(npts))

    rows = []
    for dt in args.dts:
        kd_star, rmse = kd_star_at_dt(site_cfg, kd_grid, dt)
        rows.append({"dt_s": dt, "kd_star": kd_star, "rmse": rmse.tolist()})
        print(f"{args.site} dt={dt:6g}: K_d* = {kd_star*1e3:.4f} mW  "
              f"rmse={np.round(rmse, 4)}", flush=True)

    for a, b in zip(rows, rows[1:]):
        d_mw = (b["kd_star"] - a["kd_star"]) * 1e3
        print(f"dK_d*({a['dt_s']:g}->{b['dt_s']:g}) = {d_mw:+.4f} mW", flush=True)

    tag = args.tag or f"{args.site}_picard{CN_PICARD_SWEEPS}"
    out = ROOT / "results" / f"dt_kdstar_certification_{tag}.json"
    out.write_text(json.dumps({
        "site": args.site, "kd_grid": kd_grid.tolist(), "rows": rows,
        "cn_picard_sweeps": CN_PICARD_SWEEPS, "eq_n_inner": EQ_N_INNER,
        "criterion_mw": 0.05,
        "note": "commensurate grids (periodic_time_grid); vertex from "
                "kd_star_from_residuals on the bracket above",
    }, indent=2))
    print(f"wrote {out.relative_to(ROOT)}", flush=True)


if __name__ == "__main__":
    main()
