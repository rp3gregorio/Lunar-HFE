"""High-resolution follow-up to audit_qb_basins.py: the narrow A15 basin at Q_b = 10.

Why
---
At Q_b = 10 mW m^-2 the A15 RMSE(K_d) curve has a narrow lower basin near
K_d ~ 1.2 that the 0.3 mW grid of audit_qb_basins.py steps over, so that
audit (and the stored qb_degeneracy.json value, 7.74) report the secondary
basin. Section 2.4 of the letter cites the narrow branch ("by Q_b = 10 the
deeper one has migrated to a narrow branch at K_d ~ 1.2"). This script
re-solves it directly at 0.1 mW spacing, records the flux closure and
convergence of every solve, and compares it with the secondary basin.

Before 2026-10-04 these numbers lived only as hand-written blocks in
qb_basin_audit.json ("high_resolution_followup") and qb_degeneracy.json
("caveats"), which a fresh run of those scripts drops. They are now written
here, by code.

Reads:  results/qb_degeneracy.json (stored A15 K_d* at Q_b = 10)
Writes: results/qb_basin_followup.json
Runtime: ~1 min.

Run with:
    python pipeline/compute/audit_qb_basin_followup.py
"""
from __future__ import annotations
import json, pathlib, sys, time
import numpy as np

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from lunar.apollo_helpers import extract_sensor_stability
from lunar.config import (SITES, GRID, DT_STEP, HAYNE, EQ_Z_ANCHOR,
                          EQ_N_INNER, EQ_MAX_OUTER, EQ_ANCHOR_TOL)
from lunar.grid import make_geometric_grid
from lunar.solver import periodic_time_grid, standard_insolation
from lunar.properties import conductivity_hayne, specific_heat
from lunar.equilibrium import solve_periodic_equilibrium
from retrieve_kd import _interp_profile_at_depths

SITE, QB = "A15", 10.0e-3
SCAN = np.round(np.arange(0.90, 2.2001, 0.10), 2) * 1e-3   # 0.1 mW, direct solves
KD_SECONDARY = 7.70e-3                                       # the basin the coarse grids report


def solve(cfg, kd, G, t, insol):
    """The run_with() Hayne call, keeping the convergence diagnostics."""
    eq = solve_periodic_equilibrium(
        grid=G, t=t, insolation=insol, albedo=cfg["albedo"],
        emissivity=cfg["emissivity"], Q_b=QB,
        K_func=lambda T, z: conductivity_hayne(T, z, Ks=HAYNE["K_S"], Kd=kd,
                                               H=HAYNE["H"], chi=HAYNE["CHI"]),
        cp_func=lambda T: specific_heat(T, model="hayne"), T_guess=cfg["T_MEAN_EFF"],
        z_anchor=EQ_Z_ANCHOR, n_inner=EQ_N_INNER, max_outer=EQ_MAX_OUTER,
        anchor_tol_K=EQ_ANCHOR_TOL, hayne_params=(HAYNE["K_S"], kd, HAYNE["H"], HAYNE["CHI"]))
    return eq


def main():
    t0 = time.time()
    cfg = SITES[SITE]
    obs = extract_sensor_stability(cfg["mission"], min_depth_cm=cfg["MIN_DEPTH_CM"])
    m = np.asarray(obs["deep_mask"], bool)
    z = np.asarray(obs["depth_cm_all"])[m] / 100.0
    Tobs = np.asarray(obs["T_eq_all"])[m]
    G = make_geometric_grid(**GRID)
    t = periodic_time_grid(DT_STEP)
    insol = standard_insolation(cfg["lat"], t)

    def rmse_of(eq):
        Tm = _interp_profile_at_depths(z, G.z_mid, eq.T_mean, context="basin follow-up")
        return float(np.sqrt(np.mean((Tm - Tobs) ** 2)))

    rows = []
    for kd in SCAN:
        eq = solve(cfg, float(kd), G, t, insol)
        rows.append(dict(kd_mW=float(kd * 1e3), rmse_K=rmse_of(eq),
                         flux_closure=float(eq.flux_closure), converged=bool(eq.converged)))
        print(f"  K_d={kd*1e3:4.2f}  RMSE={rows[-1]['rmse_K']:.4f}  closure={eq.flux_closure:.2%}"
              f"  converged={eq.converged}", flush=True)
    i = int(np.argmin([r["rmse_K"] for r in rows]))
    lo = rows[i]
    eq2 = solve(cfg, KD_SECONDARY, G, t, insol)
    sec = dict(kd_mW=KD_SECONDARY * 1e3, rmse_K=rmse_of(eq2),
               flux_closure=float(eq2.flux_closure), converged=bool(eq2.converged))
    stored = json.loads((ROOT / "results" / "qb_degeneracy.json").read_text())["sites"][SITE]
    stored_kd = next(r["kd_star_mW"] for r in stored if abs(r["qb_mW"] - QB * 1e3) < 1e-6) \
        if isinstance(stored, list) and "qb_mW" in stored[0] else None
    deeper = lo["rmse_K"] < sec["rmse_K"]
    interior = 0 < i < len(rows) - 1
    out = dict(
        site=SITE, qb_mW=QB * 1e3,
        scan=dict(kd_mW=[r["kd_mW"] for r in rows], rmse_K=[r["rmse_K"] for r in rows],
                  flux_closure=[r["flux_closure"] for r in rows],
                  converged=[r["converged"] for r in rows]),
        narrow_basin=dict(lo, interior=interior,
                          neighbours_rmse_K=[rows[i - 1]["rmse_K"], rows[i + 1]["rmse_K"]] if interior else None),
        secondary_basin=sec,
        narrow_basin_is_deeper=bool(deeper),
        stored_qb_degeneracy_kd_mW=stored_kd,
        reading=(f"At Q_b = {QB*1e3:.0f} the A15 objective is bimodal: a narrow basin at "
                 f"K_d = {lo['kd_mW']:.2f} (RMSE {lo['rmse_K']:.4f} K, closure {lo['flux_closure']:.2%}, "
                 f"converged={lo['converged']}) is {'deeper' if deeper else 'shallower'} than the "
                 f"{sec['kd_mW']:.2f} basin (RMSE {sec['rmse_K']:.4f} K) that the 0.3 mW audit grid and "
                 f"qb_degeneracy.json report. The A15 envelope is [14, 25] mW m^-2 and Fig. 10a is "
                 f"rendered from Q_b(A15) = 13 upward, so no reported number uses the Q_b = 10 entry; "
                 f"do not interpolate through it. Any future low-Q_b A15 scan needs <= 0.1 mW spacing."),
        runtime_s=round(time.time() - t0, 1))
    p = ROOT / "results" / "qb_basin_followup.json"
    p.write_text(json.dumps(out, indent=1))
    print(out["reading"])
    print(f"wrote {p.relative_to(ROOT)} [{time.time()-t0:.0f} s]", flush=True)


if __name__ == "__main__":
    main()
