#!/usr/bin/env python3
"""Does the near-surface layer explain the annual-wave amplitude mismatch?

The annual-wave fit (compute_annual_wave.py) needs one free complex factor per
probe: the model wave is 1.5-2.5 times larger than the measured one (factor
scale 0.40-0.68). The flat 1-D column sets the annual surface forcing through
the near-surface layer of the Hayne form, so this test reruns the same forward
model and fit with that layer changed, everything else as in the nominal fit
(joint-fit albedo, measured annual waves with their bootstrap covariances):

    H   = 3, 6 (nominal), 10 cm          (the error-budget range)
    K_s = 0.5, 0.7, 1 (nominal), 1.3, 2 x 0.74 mW m-1 K-1

For each variant it reports the free factor per probe (scale and timing) at
the best annual-wave K_d and at the joint-fit K_d, and the annual-wave K_d
itself. If the factor moved towards 1 for a plausible layer, the mismatch
would point to the near-surface form; if not, it lies elsewhere (terrain,
borestem, the forcing itself).

Writes results/annual_wave_surface_test.json.
Runtime: ~5 min on 5 workers.
"""
from __future__ import annotations
import json, sys, pathlib, time
from multiprocessing import Pool
_REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO)); sys.path.insert(0, str(_REPO / "src"))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import numpy as np
import compute_annual_wave as aw

KD_SCAN = np.round(np.concatenate([np.arange(3.0, 9.01, 0.25), [3.4]]), 3)
KS0, H0 = 7.4e-4, 0.06
VARIANTS = {"nominal": {}, "H_3cm": {"H": 0.03}, "H_10cm": {"H": 0.10},
            "Ks_x0.5": {"ks": 0.5 * KS0}, "Ks_x0.7": {"ks": 0.7 * KS0},
            "Ks_x1.3": {"ks": 1.3 * KS0}, "Ks_x2": {"ks": 2.0 * KS0}}


def model_run(job):
    """aw.model_run with the near-surface layer (K_s, H) overridden in both the
    equilibrium start and the 1966-1977 forward run."""
    site, A, kd_mW, depths, ov, vname = job
    from lunar.config import SITES, GRID, DT_STEP, HAYNE
    from lunar.grid import make_geometric_grid
    from lunar.solver import periodic_time_grid, standard_insolation, PixelInputs, solve_pixel
    from lunar.equilibrium import solve_hayne_equilibrium
    cfg = SITES[site]; kd = kd_mW * 1e-3
    ks, H, chi = ov.get("ks", HAYNE["K_S"]), ov.get("H", HAYNE["H"]), HAYNE["CHI"]
    G = make_geometric_grid(**GRID)
    tp = periodic_time_grid(DT_STEP)
    eq = solve_hayne_equilibrium(
        G, tp, standard_insolation(cfg["lat"], tp), albedo=A, emissivity=cfg["emissivity"], Q_b=cfg["Q_BASAL"],
        kd=kd, ks=ks, H=H, chi=chi, T_guess=cfg["T_MEAN_EFF"])
    t, S, day = aw.spice_insolation(site)
    out = solve_pixel(PixelInputs(grid=G, t=t, bc_mode="radiative", insolation=S, albedo=A,
                                  emissivity=cfg["emissivity"], Q_b=cfg["Q_BASAL"], T_init=eq.T_mean.copy(),
                                  hayne_params=(ks, kd, H, chi), n_lunations_spinup=1))
    u, inv = np.unique(day, return_inverse=True); cnt = np.bincount(inv)
    zm = G.z_mid; Td = np.empty((len(depths), len(u)))
    for i, z in enumerate(depths):
        j = np.searchsorted(zm, z) - 1; w = (z - zm[j]) / (zm[j + 1] - zm[j])
        Td[i] = np.bincount(inv, out.T[j] * (1 - w) + out.T[j + 1] * w) / cnt
    return site, vname, kd_mW, u, Td


def main():
    t0 = time.time()
    from lunar.config import HAYNE
    assert abs(HAYNE["K_S"] - KS0) < 1e-9 and abs(HAYNE["H"] - H0) < 1e-9, "nominal layer changed"
    rng = np.random.default_rng(20261006)                       # same seed as the nominal fit
    joint = json.loads((_REPO / "results" / "joint_albedo_fit.json").read_text())
    A_fit = {s: round(joint["sites"][s]["with_diffusivity"]["best"]["A"], 4) for s in aw.PROBES}
    kd_joint = {s: joint["sites"][s]["with_diffusivity"]["best"]["kd_star_mW"] for s in aw.PROBES}
    sensors = {s: {(tag[-2:], k): v for tag in aw.PROBES[s] for k, v in aw.load_probe(tag).items()} for s in aw.PROBES}

    # the measured annual waves, exactly as in the nominal fit
    obs, days = {}, {}
    for s in aw.PROBES:
        w = aw.windows(s, "nominal"); obs[s], days[s] = {}, {}
        for key, v in sensors[s].items():
            d0, d1 = w(key[0], key[1], v); m = (v["day"] >= d0) & (v["day"] <= d1)
            if m.sum() < 200:
                continue
            obs[s][key] = aw.annual(v["day"][m] + 0.5, v["T"][m], nboot=aw.NBOOT, rng=rng); days[s][key] = v["day"][m]
    print(f"measured annual waves ready ({time.time() - t0:.0f} s)", flush=True)

    depths = {s: sorted({v["z"] for v in sensors[s].values()}) for s in aw.PROBES}
    jobs = [(s, A_fit[s], float(kd), depths[s], ov, vn) for vn, ov in VARIANTS.items()
            for s in aw.PROBES for kd in KD_SCAN]
    print(f"{len(jobs)} forward runs ({len(VARIANTS)} variants x 2 sites x {len(KD_SCAN)} K_d)", flush=True)
    store = {}
    from lunar.progress import bar
    with Pool(5) as pool:
        for s, vn, kd, u, Td in bar(pool.imap_unordered(model_run, jobs, chunksize=2), total=len(jobs), desc="forward runs", unit="runs"):
            store[(s, vn, kd)] = (u, Td)

    out = dict(meta=dict(kd_scan_mW=KD_SCAN.tolist(), albedo=A_fit, kd_joint_mW=kd_joint, K_s_nominal=KS0, H_nominal=H0,
                         note="free complex factor per probe: scale < 1 means the model wave is too large; "
                              "lag_days > 0 means the model wave must be delayed"), sites={})
    year = aw.YEAR
    for s in aw.PROBES:
        groups = {p: [k for k in obs[s] if k[0] == p] for p in ("p1", "p2")}
        kj = float(KD_SCAN[np.argmin(np.abs(KD_SCAN - kd_joint[s]))])
        res = {}
        for vn in VARIANTS:
            mod = {}
            for kd in KD_SCAN:
                u, Td = store[(s, vn, float(kd))]
                for key in obs[s]:
                    T = Td[depths[s].index(sensors[s][key]["z"])][np.searchsorted(u, days[s][key])]
                    mod[(kd, key)] = aw.annual(days[s][key] + 0.5, T)[0]
            chi2, gs = aw.fit_kd(obs[s], mod, groups, KD_SCAN)
            summ = aw.profile_summary(KD_SCAN, chi2, len(obs[s]), len(groups))
            ib = int(np.argmin(chi2)); ij = int(np.where(KD_SCAN == kj)[0][0])
            fac = lambda g: dict(scale=float(np.hypot(*g)), lag_days=float(np.degrees(np.arctan2(g[1], g[0])) / 360 * year))
            shallow = min(obs[s], key=lambda k: sensors[s][k]["z"])
            res[vn] = dict(kd_mW=summ["kd_mW"], ci95=summ["ci95"], dchi2_global=summ["dchi2_global"],
                           chi2_min=summ["chi2_min"], dof=summ["dof"],
                           factor_at_best={p: fac(g) for p, g in gs[ib].items()},
                           factor_at_joint_kd={p: fac(g) for p, g in gs[ij].items()},
                           model_amp_shallowest_K=float(np.hypot(*mod[(KD_SCAN[ib], shallow)])),
                           obs_amp_shallowest_K=float(np.hypot(*obs[s][shallow][0])),
                           shallowest_sensor=f"{shallow[0]} {shallow[1]} ({100 * sensors[s][shallow]['z']:.0f} cm)")
            f = res[vn]["factor_at_best"]
            print(f"{s} {vn:8s} K_d {summ['kd_mW']:.2f} [{summ['ci95'][0]:.2f}, {summ['ci95'][1]:.2f}]  "
                  f"chi2 {summ['chi2_min']:.0f}/{summ['dof']}  factor p1 {f['p1']['scale']:.2f} ({f['p1']['lag_days']:+.0f} d), "
                  f"p2 {f['p2']['scale']:.2f} ({f['p2']['lag_days']:+.0f} d)  global dchi2 {summ['dchi2_global']:.0f}", flush=True)
        out["sites"][s] = res
    (_REPO / "results" / "annual_wave_surface_test.json").write_text(json.dumps(out, indent=1))
    print(f"wrote results/annual_wave_surface_test.json ({time.time() - t0:.0f} s)")


if __name__ == "__main__":
    main()
