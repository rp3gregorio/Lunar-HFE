"""AOGS study: DEM-shadowed forcing + 3-layer density sensitivity.

For the AOGS presentation: a sensitivity analysis of the 1-D thermal
model at the Apollo 15 / 17 boreholes where

  1. the solar forcing is modified by local-horizon SHADOWING computed
     from the LOLA DEM (sun below the terrain horizon -> no direct
     insolation), and
  2. the continuous Hayne density profile rho(z) is replaced by a
     DISCRETIZED 3-layer profile (surface / intermediate / deep), and
     the layer densities are swept over literature-plausible values.

Each candidate is solved to certified periodic equilibrium with the
flux-anchored solver (custom rho_func + custom insolation; the K(T,z)
form is held at the per-site certified K_d* from
results/kd_retrieval_results.json) and scored by RMSE against the
stable-window deep-sensor equilibrium temperatures — the same data
reduction as the letter.

Outputs -> results/aogs_sensitivity.json  (everything Part I of the
notebook 08_aogs_study.ipynb plots: horizon profiles, shadowed
forcing samples, density profiles, per-combo RMSE, best combos, and an
n_inner certification check).

Run:  .venv/bin/python code/pipeline/compute/aogs_sensitivity.py
(~10 min on 8 cores; results are cached — delete the JSON to force.)

HONESTY NOTES
- LOLA LDEM 16 ppd is ~1.9 km/px: the great Apennine front (A15) is
  resolved, but the near-field Taurus--Littrow massifs (A17, ~2 km high
  within ~10 km) are undersampled, so A17 horizons are a LOWER BOUND.
- Densities enter through the volumetric heat capacity rho*cp only
  (K is held fixed), so this isolates the pure heat-capacity
  sensitivity; small RMSE differences are themselves a result.
"""
from __future__ import annotations

import functools
import json
import multiprocessing as mp
import pathlib
import sys

import numpy as np

sys.path.insert(0, str(next(a for a in pathlib.Path(__file__).resolve().parents if (a / "code" / "src" / "lunar").is_dir()) / "code" / "src"))

from lunar._bootstrap import find_repo_root  # noqa: E402
from lunar.config import DT_STEP, GRID, HAYNE, SITES  # noqa: E402
from lunar.grid import make_geometric_grid  # noqa: E402
from lunar.solver import periodic_time_grid, standard_insolation  # noqa: E402
from lunar.properties import conductivity_hayne, specific_heat  # noqa: E402
from lunar.equilibrium import solve_periodic_equilibrium  # noqa: E402
from lunar.apollo_helpers import extract_sensor_stability  # noqa: E402
from lunar.constants import SOLAR_CONSTANT  # noqa: E402

ROOT = find_repo_root()
AOGS = next(a for a in pathlib.Path(__file__).resolve().parents if a.name == "aogs")   # this bundle (self-contained)
OUT = AOGS / "results" / "aogs_sensitivity.json"
R_MOON_KM = 1737.4

# ── the discretization under test (EDIT HERE) ────────────────────────────────
Z1, Z2 = 0.10, 0.50                      # layer boundaries [m]: skin|mid|deep
RHO_L1 = [1100.0, 1300.0, 1500.0]        # surface layer candidates [kg m^-3]
RHO_L2 = [1400.0, 1600.0, 1800.0]        # intermediate layer
RHO_L3 = [1700.0, 1800.0, 1900.0]        # deep layer
N_INNER_SWEEP = 24                       # per-solve inner lunations (checked
N_INNER_CERT = 96                        # against the production 96 below)
N_AZ = 90                                # horizon azimuth bins


# ── DEM + horizons ───────────────────────────────────────────────────────────
DEM_SCALE_KM = 0.5 / 1000.0   # LOLA LDEM digital number -> km (0.5 m per DN)


def load_dem():
    """LOLA LDEM at the FINEST resolution available, memory-mapped.

    Auto-selects the highest-ppd ``ldem_<ppd>.img`` in ``data/lola/`` — so
    dropping in a finer global-cylindrical LOLA DEM (64 / 128 / 256 / 512 ppd),
    or an SLDEM2015 crop reprojected to the same equirectangular int16 layout,
    upgrades every horizon/shadowing result with NO code change. The file is
    memory-mapped (raw int16 DN; scaled to km at sample time by DEM_SCALE_KM),
    so even a multi-GB global DEM loads lazily: only the ~10^4 points sampled per
    site are read from disk. Returns (dem, ppd). See ``data/lola/README.md``.

    16 ppd (~1.9 km/px) does NOT resolve the near-field Taurus--Littrow massifs
    and its horizons are still rising with resolution (4 -> 16 ppd), so they are
    a LOWER BOUND — prefer the finest DEM you can supply.
    """
    cands = []
    for p in sorted((AOGS / "data" / "lola").glob("ldem_*.img")):
        try:
            cands.append((int(p.stem.split("_")[1]), p))
        except (IndexError, ValueError):
            continue
    if not cands:
        raise FileNotFoundError("no LOLA ldem_<ppd>.img under data/lola/")
    ppd, p = max(cands)                                   # finest available
    n_lat = 180 * ppd
    dem = np.memmap(p, dtype="<i2", mode="r").reshape(n_lat, 2 * n_lat)
    return dem, ppd


def _dem_sample(dem, ppd, lat, lon):
    """Bilinear sample of the equirectangular DEM at (lat, lon) degrees [km].

    ``dem`` is raw int16 DN (a memmap); the DEM_SCALE_KM factor converts the
    interpolated value to kilometres here, keeping the memmap unmaterialised.
    """
    h, w = dem.shape
    r = (90.0 - np.asarray(lat)) * ppd - 0.5
    c = (np.asarray(lon) + 180.0) * ppd - 0.5
    r0 = np.clip(np.floor(r).astype(int), 0, h - 2)
    c0 = np.clip(np.floor(c).astype(int), 0, w - 2)
    fr, fc = np.clip(r - r0, 0, 1), np.clip(c - c0, 0, 1)
    return DEM_SCALE_KM * (
        (1 - fr) * (1 - fc) * dem[r0, c0] + (1 - fr) * fc * dem[r0, c0 + 1]
        + fr * (1 - fc) * dem[r0 + 1, c0] + fr * fc * dem[r0 + 1, c0 + 1])


def horizon_profile(dem, ppd, lat0, lon0, r_max_km=150.0, dr_km=None):
    """Terrain horizon elevation angle [deg] vs azimuth (from N, eastward).

    Rays march outward from the site; the elevation angle to each DEM
    sample includes the R^2/(2R_moon) curvature drop. The horizon is the
    max over the ray (floored at 0 = flat horizon). The ray step defaults to
    one DEM pixel (capped at 1 km, so 16 ppd is unchanged) — a finer DEM is
    then marched at its own resolution rather than skipping pixels.
    """
    if dr_km is None:
        dr_km = min(1.0, 2.0 * np.pi * R_MOON_KM / 360.0 / ppd)  # <= 1 pixel
    az = np.linspace(0.0, 360.0, N_AZ, endpoint=False)
    h0 = float(_dem_sample(dem, ppd, lat0, lon0))
    r = np.arange(dr_km, r_max_km + dr_km, dr_km)
    horizon = np.zeros_like(az)
    for i, a in enumerate(np.radians(az)):
        dlat = np.degrees((r / R_MOON_KM) * np.cos(a))
        dlon = np.degrees((r / R_MOON_KM) * np.sin(a)
                          / max(np.cos(np.radians(lat0)), 1e-6))
        hh = _dem_sample(dem, ppd, lat0 + dlat, lon0 + dlon)
        drop = r ** 2 / (2.0 * R_MOON_KM)          # curvature of the sphere
        elev = np.degrees(np.arctan2(hh - h0 - drop, r))
        horizon[i] = max(0.0, float(elev.max()))
    return az, horizon


def sun_track(lat_deg, t):
    """Solar (elevation, azimuth-from-north) [deg] over the lunation.

    Sub-solar point on the equator (declination 0), hour angle
    h = 2 pi t / T_lunar (noon at t = 0): sin e = cos(lat) cos(h);
    A = atan2(-sin h, -sin(lat) cos h). The ONE place this geometry
    lives — shadowed_insolation and the poster's sun-path overlay
    both read it from here.
    """
    from lunar.constants import LUNATION_SECONDS
    phi = np.radians(lat_deg)
    h = 2.0 * np.pi * np.asarray(t) / LUNATION_SECONDS
    sin_e = np.cos(phi) * np.cos(h)
    elev = np.degrees(np.arcsin(np.clip(sin_e, -1, 1)))
    A = np.degrees(np.arctan2(-np.sin(h), -np.sin(phi) * np.cos(h))) % 360.0
    return elev, A


def shadowed_insolation(lat_deg, t, az_deg, horizon_deg):
    """standard_insolation with samples below the terrain horizon zeroed.

    standard_insolation already equals S0*sin(e) on the dayside, so
    shadowing only zeroes the blocked samples (albedo stays inside the
    solver -- the house forcing convention).
    """
    S = standard_insolation(lat_deg, t)
    elev, A = sun_track(lat_deg, t)
    hor_at = np.interp(A, az_deg, horizon_deg, period=360.0)
    return np.where(elev > hor_at, S, 0.0)


# ── density profiles ─────────────────────────────────────────────────────────
def rho_3layer(z, r1, r2, r3):
    z = np.asarray(z, dtype=float)
    return np.where(z < Z1, r1, np.where(z < Z2, r2, r3))


def density_combos():
    combos = []
    for r1 in RHO_L1:
        for r2 in RHO_L2:
            for r3 in RHO_L3:
                if r1 <= r2 <= r3:               # physically ordered packing
                    combos.append((r1, r2, r3))
    return combos


# ── one forward solve ────────────────────────────────────────────────────────
def run_case(args):
    (site_key, forcing_key, prof_id, rho_spec, insol, kd_star,
     n_inner) = args
    s = SITES[site_key]
    g = make_geometric_grid(**GRID)
    t = periodic_time_grid(DT_STEP)
    K = functools.partial(conductivity_hayne, Ks=HAYNE["K_S"], Kd=kd_star,
                          H=HAYNE["H"], chi=HAYNE["CHI"])
    cp = functools.partial(specific_heat, model="hayne")
    if rho_spec == "hayne":
        rho = None                                # solver default rho(z)
    else:
        rho = functools.partial(rho_3layer, r1=rho_spec[0], r2=rho_spec[1],
                                r3=rho_spec[2])
    eq = solve_periodic_equilibrium(
        g, np.asarray(t), np.asarray(insol), s["albedo"], s["emissivity"],
        s["Q_BASAL"], K_func=K, cp_func=cp, rho_func=rho, n_inner=n_inner)

    res = extract_sensor_stability(s["mission"], s["MIN_DEPTH_CM"])
    deep = res["deep_mask"]
    z_cm = np.asarray(res["depth_cm_all"])[deep]
    T_obs = np.asarray(res["T_eq_all"])[deep]
    T_mod = np.interp(z_cm / 100.0, g.z_mid, eq.T_mean)
    rmse = float(np.sqrt(np.mean((T_mod - T_obs) ** 2)))
    return dict(site=site_key, forcing=forcing_key, profile=prof_id,
                rho=(list(rho_spec) if rho_spec != "hayne" else "hayne"),
                rmse_K=rmse, anchor_K=float(eq.anchor_K),
                converged=bool(eq.converged), n_outer=int(eq.n_outer),
                flux_closure=float(eq.flux_closure),
                T_model_at_sensors=[float(v) for v in T_mod],
                T_mean_profile=[float(v) for v in eq.T_mean])


def main():
    dem, ppd = load_dem()
    t = periodic_time_grid(DT_STEP)
    kd = json.loads((ROOT / "results" / "kd_retrieval_results.json")
                    .read_text())

    sites_meta, forcings, jobs = {}, {}, []
    for sk in ("A15", "A17"):
        s = SITES[sk]
        az, hor = horizon_profile(dem, ppd, s["lat"], s["lon"])
        S_std = standard_insolation(s["lat"], t)
        S_shd = shadowed_insolation(s["lat"], t, az, hor)
        loss = 1.0 - S_shd.sum() / S_std.sum()
        obs = extract_sensor_stability(s["mission"], s["MIN_DEPTH_CM"])
        dm = obs["deep_mask"]
        sites_meta[sk] = dict(lat=s["lat"], lon=s["lon"],
                              sensor_depth_cm=[float(v) for v in
                                               np.asarray(obs["depth_cm_all"])[dm]],
                              sensor_T_eq=[float(v) for v in
                                           np.asarray(obs["T_eq_all"])[dm]],
                              sensor_T_std=[float(v) for v in
                                            np.asarray(obs["T_std_all"])[dm]],
                              horizon_az_deg=az.tolist(),
                              horizon_deg=hor.tolist(),
                              horizon_max_deg=float(hor.max()),
                              insolation_energy_loss=float(loss),
                              kd_star_used=kd[sk]["kd_star"])
        forcings[(sk, "standard")] = S_std
        forcings[(sk, "shadowed")] = S_shd

    combos = density_combos()
    for sk in ("A15", "A17"):
        for fk in ("standard", "shadowed"):
            insol = forcings[(sk, fk)]
            jobs.append((sk, fk, "hayne-continuous", "hayne", insol,
                         kd[sk]["kd_star"], N_INNER_SWEEP))
            for c in combos:
                pid = f"{int(c[0])}/{int(c[1])}/{int(c[2])}"
                jobs.append((sk, fk, pid, c, insol, kd[sk]["kd_star"],
                             N_INNER_SWEEP))

    print(f"AOGS sweep: {len(jobs)} solves "
          f"({len(combos)} 3-layer combos + Hayne baseline, 2 sites, "
          f"2 forcings; DEM {ppd} ppd) ...")
    with mp.Pool(min(8, mp.cpu_count() - 1)) as pool:
        rows = pool.map(run_case, jobs)

    # certification: best combo per site re-run at the production n_inner
    cert = {}
    for sk in ("A15", "A17"):
        best = min((r for r in rows
                    if r["site"] == sk and r["forcing"] == "shadowed"
                    and r["profile"] != "hayne-continuous"),
                   key=lambda r: r["rmse_K"])
        c = tuple(best["rho"])
        chk = run_case((sk, "shadowed", best["profile"], c,
                        forcings[(sk, "shadowed")], kd[sk]["kd_star"],
                        N_INNER_CERT))
        cert[sk] = dict(best_profile=best["profile"],
                        rmse_sweep=best["rmse_K"], rmse_n96=chk["rmse_K"],
                        drift_K=abs(best["rmse_K"] - chk["rmse_K"]))
        print(f"  {sk}: best {best['profile']}  RMSE {best['rmse_K']:.3f} K "
              f"(n_inner {N_INNER_SWEEP}) vs {chk['rmse_K']:.3f} K (96)")

    # small forcing samples for the notebook's insolation panel (2 days
    # of samples around sunrise keep the JSON light)
    samp = {}
    for sk in ("A15", "A17"):
        step = max(1, len(t) // 600)
        samp[sk] = dict(t_days=(np.asarray(t)[::step] / 86400).tolist(),
                        S_standard=forcings[(sk, "standard")][::step].tolist(),
                        S_shadowed=forcings[(sk, "shadowed")][::step].tolist())

    OUT.write_text(json.dumps(dict(
        meta=dict(z1_m=Z1, z2_m=Z2, rho_l1=RHO_L1, rho_l2=RHO_L2,
                  z_mid_m=[float(v) for v in
                           make_geometric_grid(**GRID).z_mid],
                  rho_l3=RHO_L3, n_inner_sweep=N_INNER_SWEEP,
                  dem_ppd=ppd, n_az=N_AZ, solar_constant=SOLAR_CONSTANT,
                  note="K held at per-site certified K_d*; densities enter "
                       "via rho*cp only. A17 horizons are a lower bound at "
                       "this DEM resolution."),
        sites=sites_meta, certification=cert, forcing_samples=samp,
        runs=rows), indent=1))
    print(f"wrote {OUT} ({len(rows)} runs)")


if __name__ == "__main__":
    main()
