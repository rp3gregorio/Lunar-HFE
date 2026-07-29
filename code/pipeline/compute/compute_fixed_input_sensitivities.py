#!/usr/bin/env python3
"""Fixed-input sensitivities for the K_d* error budget (Table 4 rows
sigma_chi, sigma_H, sigma_Ks, sigma_rho).

Each component re-runs the full K_d retrieval at the perturbed input and
reports the half-range (or one-sided shift) of K_d*:

  sigma_chi : a LOW-chi stress test, one-sided |shift|, against the
              adopted 2.7 (Hayne 2017 App. A).
              PROVENANCE NOTE (audited 2026-07-27): this row was
              labelled "chi = 1.48, the Vasavada et al. (2012)
              normalisation -- the actual published disagreement".
              That is wrong. Vasavada et al. (2012) publish chi = 2.7,
              the SAME value as Hayne, and state it explicitly: "we
              increase c to 2.7 (from 1.5) at the surface in the
              revised model". 1.48 appears in neither paper; 1.5 is
              their superseded pre-revision value. There is no
              published disagreement to cite.
              The RESULT is unaffected. At both 1.48 and 1.50 the RMSE
              minimum rails against the sweep boundary at both sites
              (A15 -> 1.000, A17 -> 25.000, bit-identical), so no
              interior retrieval exists at low chi either way. The
              conclusion -- K_d* is conditional on the adopted chi --
              is robust to the alternative value chosen. See
              documents/notes/ERROR_BUDGET_PROVENANCE.md.
  sigma_H   : half-range of the per-H parabolic K_d* across the joint
              (K_d, H) grid already computed by retrieve_kd.py (no new
              solver runs).
  sigma_Ks  : K_s +/- 30 % (Cremers & Birkebak 1971 lab scatter),
              half-range.
  sigma_rho : rho_d in {1700, 2000} kg m^-3 (Mitchell 1973; Carrier
              1991 Apollo-core envelope), entering rho(z) and hence
              rho*c_p only (the Hayne K(T,z) has no explicit rho),
              half-range.

Writes results/fixed_input_sensitivities.json, consumed by
compute_error_budget.py.

Run with:
    python pipeline/compute/compute_fixed_input_sensitivities.py
"""
from __future__ import annotations
import json, sys, pathlib

_REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO))
sys.path.insert(0, str(_REPO / "src"))
sys.path.insert(0, str(_REPO / "pipeline" / "figures"))

import numpy as np

from lunar.apollo_helpers import extract_sensor_stability
from lunar.properties import conductivity_hayne, specific_heat, density_hayne
from lunar.solver import periodic_time_grid, standard_insolation
from lunar.constants import RHO_SURFACE, RHO_DEEP
from lunar.equilibrium import solve_periodic_equilibrium
from lunar.grid import make_geometric_grid
from pipeline.compute.retrieve_kd import (
    SITES, HAYNE, GRID, S0, T_LUNAR, DT_STEP, KD_GRIDS,
    kd_star_from_residuals,
    EQ_Z_ANCHOR, EQ_N_INNER, EQ_MAX_OUTER, EQ_ANCHOR_TOL,
)

KD_GRID = KD_GRIDS   # single-sourced from lunar.config (dense vertex grid)


def deep_obs(cfg):
    obs = extract_sensor_stability(cfg["mission"],
                                   min_depth_cm=cfg["MIN_DEPTH_CM"])
    deep = np.asarray(obs["deep_mask"], dtype=bool)
    return (np.asarray(obs["depth_cm_all"])[deep] / 100.0,
            np.asarray(obs["T_eq_all"])[deep])


def retrieve(cfg, kd_grid, *, chi=None, ks=None, rho_d=None):
    """K_d* with one Hayne input perturbed (chi, K_s, or rho_d)."""
    chi = HAYNE["CHI"] if chi is None else chi
    ks = HAYNE["K_S"] if ks is None else ks
    grid_ = make_geometric_grid(**GRID)
    t = periodic_time_grid(DT_STEP)   # commensurate lunation grid (audit 2026-07-03)
    insol = standard_insolation(cfg["lat"], t)
    cpf = lambda T: specific_heat(T, model="hayne")
    rho_func = (None if rho_d is None
                else (lambda z: density_hayne(z, rho_d=rho_d)))
    z_obs, T_obs = deep_obs(cfg)
    R = np.empty((len(z_obs), len(kd_grid)))
    for k, kd in enumerate(kd_grid):
        kf = (lambda T, z, kd_=kd: conductivity_hayne(
            T, z, Ks=ks, Kd=kd_, H=HAYNE["H"], chi=chi))
        eq = solve_periodic_equilibrium(
            grid=grid_, t=t, insolation=insol,
            albedo=cfg["albedo"], emissivity=cfg["emissivity"],
            Q_b=cfg["Q_BASAL"], K_func=kf, cp_func=cpf,
            rho_func=rho_func, T_guess=cfg["T_MEAN_EFF"],
            z_anchor=EQ_Z_ANCHOR, n_inner=EQ_N_INNER,
            max_outer=EQ_MAX_OUTER, anchor_tol_K=EQ_ANCHOR_TOL,
            # compiled march: every perturbation here is still the standard
            # Hayne FORM, just with different parameter values, so it rides
            # the fast kernel (6-tuple exposes the densities); K_func/rho_func
            # above still serve the equilibrium diagnostics
            hayne_params=(ks, kd, HAYNE["H"], chi, RHO_SURFACE,
                          RHO_DEEP if rho_d is None else rho_d))
        R[:, k] = np.interp(z_obs, grid_.z_mid, eq.T_mean) - T_obs
    kd_star, _ = kd_star_from_residuals(R, kd_grid)
    return kd_star * 1e3   # mW/m/K


def sigma_h_from_joint(site_results):
    """Half-range of the per-H parabolic K_d* over the joint grid."""
    j = site_results["joint_kd_h"]
    kd_g = np.array(j["kd_grid"])
    rmse = np.array(j["rmse2d"])     # (n_h, n_kd)
    kd_stars = []
    for row in rmse:
        i = int(np.argmin(row))
        if 0 < i < len(kd_g) - 1:
            x, y = kd_g[i-1:i+2], row[i-1:i+2]
            denom = (x[0]-x[1])*(x[0]-x[2])*(x[1]-x[2])
            a = (x[2]*(y[1]-y[0]) + x[1]*(y[0]-y[2]) + x[0]*(y[2]-y[1])) / denom
            b = (x[2]**2*(y[0]-y[1]) + x[1]**2*(y[2]-y[0]) + x[0]**2*(y[1]-y[2])) / denom
            kd_stars.append(-b / (2*a) if a > 0 else kd_g[i])
        else:
            kd_stars.append(kd_g[i])
    kd_stars = np.array(kd_stars) * 1e3
    return float((kd_stars.max() - kd_stars.min()) / 2.0)


def main():
    res = json.loads((_REPO / "results" / "kd_retrieval_results.json").read_text())
    out = {}
    for s in ("A15", "A17"):
        cfg = SITES[s]
        grid = KD_GRID[s]
        nominal = res[s]["kd_star"] * 1e3
        print(f"=== {s} (nominal K_d* = {nominal:.2f}) ===", flush=True)

        kd_chi = retrieve(cfg, grid, chi=1.48)
        print(f"  chi=1.48      -> K_d* = {kd_chi:.3f}", flush=True)
        kd_ks_lo = retrieve(cfg, grid, ks=HAYNE["K_S"] * 0.7)
        kd_ks_hi = retrieve(cfg, grid, ks=HAYNE["K_S"] * 1.3)
        print(f"  Ks -/+30%     -> K_d* = {kd_ks_lo:.3f} / {kd_ks_hi:.3f}",
              flush=True)
        kd_rho_lo = retrieve(cfg, grid, rho_d=1700.0)
        kd_rho_hi = retrieve(cfg, grid, rho_d=2000.0)
        print(f"  rho_d 1700/2000 -> K_d* = {kd_rho_lo:.3f} / {kd_rho_hi:.3f}",
              flush=True)
        sigma_h = sigma_h_from_joint(res[s])
        out[s] = dict(
            nominal_mW=nominal,
            sigma_chi=abs(kd_chi - nominal),
            kd_at_chi_1p48=kd_chi,
            sigma_Ks=abs(kd_ks_hi - kd_ks_lo) / 2.0,
            kd_at_Ks_lo=kd_ks_lo, kd_at_Ks_hi=kd_ks_hi,
            sigma_rho=abs(kd_rho_hi - kd_rho_lo) / 2.0,
            kd_at_rho_1700=kd_rho_lo, kd_at_rho_2000=kd_rho_hi,
            sigma_H=sigma_h,
        )
        print(f"  sigma: chi={out[s]['sigma_chi']:.3f} "
              f"H={sigma_h:.3f} Ks={out[s]['sigma_Ks']:.3f} "
              f"rho={out[s]['sigma_rho']:.3f}", flush=True)

    path = _REPO / "results" / "fixed_input_sensitivities.json"
    path.write_text(json.dumps(out, indent=2))
    print(f"wrote {path}", flush=True)


if __name__ == "__main__":
    main()
