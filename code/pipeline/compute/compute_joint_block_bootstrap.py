"""Probe-level bootstrap of the joint (albedo, K_d) retrieval (2026-10-05).

The production bootstrap (compute_joint_albedo_fit.py) resamples sensors with
replacement and gives each sensor its own +-2.5 cm depth jitter, i.e. it treats
the sensors as independent. Sensors on one probe were emplaced together, so a
placement error is shared along the probe, and a probe-level temperature offset
(A15 probe 2 reads ~2 K below probe 1 at 87-97 cm) is shared too. This script
repeats the bootstrap with the sensors grouped by probe:

  production   the production scheme, reproduced exactly (a check of this script);
  stratified   sensors resampled WITHIN each probe, so every draw keeps both
               probes in their observed proportion; per-sensor depth jitter;
  probe_block  stratified, and ONE depth offset per probe shared by all its
               sensors (the probe moves as a unit).

The surface mean and the diffusivities are redrawn as in production. No new
solves: the solved grid of compute_joint_albedo_fit.py is reused.

Reads:  results/joint_albedo_fit.json, results/joint_albedo_fit_cache.npz
Writes: results/joint_block_bootstrap.json
Runtime: ~1 min.

Run with:
    python pipeline/compute/compute_joint_block_bootstrap.py
"""
from __future__ import annotations
import json, sys, pathlib
_REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO)); sys.path.insert(0, str(_REPO / "src")); sys.path.insert(0, str(_REPO / "pipeline" / "compute"))

import numpy as np
import compute_joint_albedo_fit as jf

SCHEMES = ("production", "stratified", "probe_block")


def probes_of(site):
    import retrieve_kd as rk
    from lunar.config import SITES
    cfg = SITES[site]
    o = rk.extract_sensor_stability(cfg["mission"], min_depth_cm=cfg["MIN_DEPTH_CM"])
    m = np.asarray(o["deep_mask"], bool)
    z = np.asarray(o["depth_cm_all"])[m] / 100.0
    p = np.array([sd["probe"] for sd in o["sensors"]])[m]
    assert np.allclose(z, jf.observed(site)[0]), "sensor order differs from jf.observed"
    return p


def draw(scheme, rng, z, probe):
    n = len(z)
    if scheme == "production":
        idx = rng.integers(0, n, size=n)
        dz = rng.normal(0.0, jf._DEPTH_SIGMA_M, size=n)
        return idx, z[idx] + dz[idx]
    idx = np.concatenate([rng.choice(np.flatnonzero(probe == q), size=int(np.sum(probe == q)), replace=True)
                          for q in np.unique(probe)])
    if scheme == "stratified":
        dz = rng.normal(0.0, jf._DEPTH_SIGMA_M, size=n)
        return idx, z[idx] + dz[idx]
    off = {q: rng.normal(0.0, jf._DEPTH_SIGMA_M) for q in np.unique(probe)}      # probe_block
    return idx, z[idx] + np.array([off[q] for q in probe[idx]])


def run(site, scheme, cache):
    z, Tobs = jf.observed(site)
    probe = probes_of(site)
    prof, Ts, kap = cache[f"{site}_prof"], cache[f"{site}_Ts"], cache[f"{site}_kap"]
    kobs = np.array([p[2] for p in jf.KAPPA_OBS[site]]); ksig = np.array([p[3] for p in jf.KAPPA_OBS[site]])
    # the production streams (seed 42 for sensors; an independent stream per site for the data)
    rng = np.random.default_rng(jf.SEED if scheme == "production" else [jf.SEED, 7, SCHEMES.index(scheme)])
    rng_d = np.random.default_rng([jf.SEED, 1, ("A15", "A17").index(site)])
    kb, ab = np.empty(jf.N_BOOT), np.empty(jf.N_BOOT)
    for b in range(jf.N_BOOT):
        idx, zj = draw(scheme, rng, z, probe)
        j0 = np.clip(np.searchsorted(jf.Z_DENSE, zj) - 1, 0, len(jf.Z_DENSE) - 2)
        w = (zj - jf.Z_DENSE[j0]) / (jf.Z_DENSE[j0 + 1] - jf.Z_DENSE[j0])
        Tm = prof[..., j0] * (1 - w) + prof[..., j0 + 1] * w
        ts_b = jf.TS_OBS[site] + rng_d.normal(0.0, jf.SIGMA_TS)
        kb_obs = kobs + rng_d.normal(0.0, 1.0, size=len(kobs)) * ksig
        J, _ = jf.objective(Tm, Tobs[idx], Ts, ts_b, kap=kap, kobs=kb_obs, ksig=ksig)
        ab[b], kb[b], _, _ = jf.best_point(J, jf.A_GRID, jf.KD_GRID)
    return kb * 1e3, ab


def pct(v):
    return dict(zip(("p2.5", "p16", "p50", "p84", "p97.5"), np.percentile(v, [2.5, 16, 50, 84, 97.5]).tolist()))


def main():
    res = json.loads((_REPO / "results" / "joint_albedo_fit.json").read_text())
    cache = np.load(_REPO / "results" / "joint_albedo_fit_cache.npz")
    out = {"n_boot": jf.N_BOOT, "depth_sigma_cm": jf._DEPTH_SIGMA_M * 100, "schemes": {}}
    for scheme in SCHEMES:
        d, k = {}, {}
        for s in ("A15", "A17"):
            k[s], a = run(s, scheme, cache)
            d[s] = dict(kd_mW=pct(k[s]), A=pct(a))
            q = d[s]["kd_mW"]
            print(f"  {scheme:12s} {s}: K_d median {q['p50']:.2f} [{q['p2.5']:.2f}, {q['p97.5']:.2f}]  "
                  f"(68%: {q['p16']:.2f}-{q['p84']:.2f})", flush=True)
        c = k["A17"] - k["A15"]
        d["contrast_mW"] = dict(**pct(c), p_leq0=float(np.mean(c <= 0)))
        q = d["contrast_mW"]
        print(f"  {scheme:12s} contrast {q['p50']:+.2f} [{q['p2.5']:+.2f}, {q['p97.5']:+.2f}], P(<=0) = {q['p_leq0']:.4f}", flush=True)
        out["schemes"][scheme] = d
    # the production scheme must reproduce the production bootstrap
    for s in ("A15", "A17"):
        ref = res["sites"][s]["with_diffusivity"]["bootstrap"]["kd_mW"]
        got = out["schemes"]["production"][s]["kd_mW"]
        assert all(abs(ref[q] - got[q]) < 1e-9 for q in ref), f"production scheme does not reproduce {s}"
    print("  production scheme reproduces results/joint_albedo_fit.json exactly")
    p = _REPO / "results" / "joint_block_bootstrap.json"
    p.write_text(json.dumps(out, indent=1))
    print(f"wrote {p.relative_to(_REPO)}")


if __name__ == "__main__":
    main()
