"""Bayesian (MCMC) version of the joint (albedo, K_d) retrieval (2026-10-05).

The joint retrieval (compute_joint_albedo_fit.py) fits the effective albedo A
and K_d at each site with the basal flux and the deep density held at their
adopted values; their effect enters the paper as error-budget rows. Here they
are sampled instead, so one posterior carries all of it:

  parameters (per site)  A, K_d, Q_b, rho_d
  likelihood             the joint objective: L = exp(-J/2), J as in
                         compute_joint_albedo_fit.objective (sensor variance
                         marginalized with a Jeffreys prior, which gives the
                         same RSS^(-n/2) form; surface mean; two diffusivities)
  priors                 A, K_d flat inside the grid; Q_b Gaussian, the
                         Langseth et al. (1976) site value +- 15 % (as in
                         bayesian_crosscheck.py); rho_d Gaussian 1800 +- 100
                         kg m^-3, which also absorbs the +-3 % c_p spread,
                         since only rho*c_p enters the heat equation and the
                         diffusivity. The two sites are sampled independently
                         (no shared density).

Phase 1 (--grid) solves the model on a grid of (A, K_d, Q_b, rho_d) with the
production solver and saves it to results/joint_mcmc_grid.npz, row by row, so
an interrupted run resumes where it stopped. Phase 2 (--sample) interpolates
that grid and runs emcee.

Reads:  results/joint_albedo_fit.json (for the nominal comparison)
Writes: results/joint_mcmc_grid.npz, results/joint_mcmc.json,
        results/joint_mcmc_chains.npz
Runtime: grid ~2 h on 5 workers (912 rows); sampling ~1 min.

Run with:
    python pipeline/compute/compute_joint_mcmc.py            # grid (resumes) + sample
    python pipeline/compute/compute_joint_mcmc.py --sample   # sample only
"""
from __future__ import annotations
import json, sys, pathlib, time
from multiprocessing import Pool
_REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO)); sys.path.insert(0, str(_REPO / "src")); sys.path.insert(0, str(_REPO / "pipeline" / "compute"))

import numpy as np
import compute_joint_albedo_fit as jf

N_WORKERS = 5
A_G = np.round(np.arange(0.115, 0.16001, 0.0025), 4)                  # 19
KD_G = np.round(np.arange(3.0, 9.0001, 0.25), 4) * 1e-3                # 25
# the first run (8-21 at A17, 1550-2050) cut the A17 posterior at Q_b = 8 and
# rho_d = 2050; the grid now reaches 5 and 2300 so no posterior touches an edge
QB_G = {"A15": np.array([13.0, 17.0, 21.0, 25.0, 29.0]),               # mW m^-2
        "A17": np.array([5.0, 8.0, 11.0, 14.0, 16.0, 18.0, 21.0])}
RHO_G = np.array([1550.0, 1800.0, 2050.0, 2300.0])                     # kg m^-3
QB_NOM = {"A15": 21.0, "A17": 16.0}
QB_PRIOR_FRAC = 0.15
RHO_PRIOR = (1800.0, 100.0)
N_WALKERS, N_STEPS, N_BURN, SEED = 32, 4000, 1000, 42
GRID = _REPO / "results" / "joint_mcmc_grid.npz"
NAMES = ("Tz", "Ts", "kap")


def rows():
    return [(s, float(A), float(q), float(r)) for s in ("A15", "A17")
            for q in QB_G[s] for r in RHO_G for A in A_G]


def solve(job):
    s, A, q, r = job
    out = jf.solve_row((s, A, {"Q_b": q * 1e-3, "rho_d": r, "kd_grid": KD_G.tolist()}))
    Tz, prof, Ts, clos, kap = out[2:]
    return job, Tz, Ts, kap


def build_grid():
    done = {}
    if GRID.exists():
        c = np.load(GRID, allow_pickle=False)
        for k, job in enumerate(c["jobs"]):
            j = (str(job[0]), float(job[1]), float(job[2]), float(job[3]))
            done[j] = (c[f"r{k}_Tz"], c[f"r{k}_Ts"], c[f"r{k}_kap"])
    todo = [j for j in rows() if j not in done]
    print(f"grid: {len(done)} rows cached, {len(todo)} to solve ({len(todo) * len(KD_G)} solves)", flush=True)
    t0 = time.time()

    def save():
        keys = list(done)
        np.savez_compressed(GRID, jobs=np.array([[k[0], k[1], k[2], k[3]] for k in keys], dtype=object).astype(str),
                            **{f"r{i}_{n}": done[k][m] for i, k in enumerate(keys) for m, n in enumerate(NAMES)})
    if todo:
        with Pool(N_WORKERS) as pool:
            for i, (job, Tz, Ts, kap) in enumerate(pool.imap_unordered(solve, todo, chunksize=1)):
                done[job] = (Tz, Ts, kap)
                if (i + 1) % 20 == 0 or i + 1 == len(todo):
                    save()
                    print(f"  {i+1}/{len(todo)} rows ({time.time()-t0:.0f} s)", flush=True)
    return done


def site_arrays(done, s):
    """Grid arrays indexed [A, Q_b, rho, K_d, ...] for one site."""
    nA, nQ, nR, nK = len(A_G), len(QB_G[s]), len(RHO_G), len(KD_G)
    z, _ = jf.observed(s)
    Tz = np.empty((nA, nQ, nR, nK, len(z))); Ts = np.empty((nA, nQ, nR, nK)); kap = np.empty((nA, nQ, nR, nK, 2))
    for ia, A in enumerate(A_G):
        for iq, q in enumerate(QB_G[s]):
            for ir, r in enumerate(RHO_G):
                t, ts, k = done[(s, float(A), float(q), float(r))]
                Tz[ia, iq, ir], Ts[ia, iq, ir], kap[ia, iq, ir] = t, ts, k
    return Tz, Ts, kap


def sample(done):
    import emcee
    from scipy.interpolate import RegularGridInterpolator as RGI
    out, chains = {}, {}
    for si, s in enumerate(("A15", "A17")):
        z, Tobs = jf.observed(s)
        n = len(Tobs)
        kobs = np.array([p[2] for p in jf.KAPPA_OBS[s]]); ksig = np.array([p[3] for p in jf.KAPPA_OBS[s]])
        Tz, Ts, kap = site_arrays(done, s)
        axes = (A_G, QB_G[s], RHO_G, KD_G * 1e3)
        iTz, iTs, ikap = RGI(axes, Tz), RGI(axes, Ts), RGI(axes, kap)
        lo = np.array([A_G[0], QB_G[s][0], RHO_G[0], KD_G[0] * 1e3])
        hi = np.array([A_G[-1], QB_G[s][-1], RHO_G[-1], KD_G[-1] * 1e3])
        q0, qs = QB_NOM[s], QB_PRIOR_FRAC * QB_NOM[s]

        def log_post(p):
            if np.any(p < lo) or np.any(p > hi):
                return -np.inf
            A, q, r, kd = p
            Tm = iTz(p)[0]; tsm = float(iTs(p)[0]); km = ikap(p)[0]
            rss = float(((Tm - Tobs) ** 2).sum())
            J = n * np.log(rss / n) + ((tsm - jf.TS_OBS[s]) / jf.SIGMA_TS) ** 2 + (((km - kobs) / ksig) ** 2).sum()
            prior = -0.5 * ((q - q0) / qs) ** 2 - 0.5 * ((r - RHO_PRIOR[0]) / RHO_PRIOR[1]) ** 2
            return -0.5 * J + prior

        b = json.loads((_REPO / "results" / "joint_albedo_fit.json").read_text())["sites"][s]["with_diffusivity"]["best"]
        rng = np.random.default_rng([SEED, si])
        start = np.array([b["A"], q0, RHO_PRIOR[0], b["kd_star_mW"]])
        p0 = start + rng.normal(0, 1, (N_WALKERS, 4)) * np.array([0.002, 0.5, 20.0, 0.1])
        p0 = np.clip(p0, lo + 1e-6, hi - 1e-6)
        sampler = emcee.EnsembleSampler(N_WALKERS, 4, log_post)
        sampler.random_state = np.random.RandomState(SEED + si).get_state()
        sampler.run_mcmc(p0, N_STEPS, progress=False)
        ch = sampler.get_chain(discard=N_BURN, flat=True)
        acc = float(np.mean(sampler.acceptance_fraction))
        try:
            tau = sampler.get_autocorr_time(discard=N_BURN, quiet=True).tolist()
        except Exception:
            tau = None
        names = ("A", "Qb_mW", "rho_d", "kd_mW")
        pct = lambda v: dict(zip(("p2.5", "p16", "p50", "p84", "p97.5"), np.percentile(v, [2.5, 16, 50, 84, 97.5]).tolist()))
        out[s] = dict(acceptance=acc, autocorr=tau, n_samples=int(len(ch)),
                      prior=dict(Qb_mW=[q0, qs], rho_d=list(RHO_PRIOR)),
                      posterior={nm: pct(ch[:, i]) for i, nm in enumerate(names)},
                      corr_kd_rho=float(np.corrcoef(ch[:, 3], ch[:, 2])[0, 1]))
        chains[s] = ch
        q = out[s]["posterior"]
        print(f"  {s}: K_d {q['kd_mW']['p50']:.2f} [{q['kd_mW']['p2.5']:.2f}, {q['kd_mW']['p97.5']:.2f}]  "
              f"A {q['A']['p50']:.4f}  Q_b {q['Qb_mW']['p50']:.1f} [{q['Qb_mW']['p2.5']:.1f}, {q['Qb_mW']['p97.5']:.1f}] "
              f"(prior {q0:.0f}+-{qs:.1f})  rho {q['rho_d']['p50']:.0f}  acc {acc:.2f}  tau {tau}", flush=True)
    # contrast from independent draws of the two posteriors
    rng = np.random.default_rng([SEED, 9])
    m = min(len(chains["A15"]), len(chains["A17"]))
    c = chains["A17"][rng.permutation(len(chains["A17"]))[:m], 3] - chains["A15"][rng.permutation(len(chains["A15"]))[:m], 3]
    out["contrast_mW"] = dict(zip(("p2.5", "p16", "p50", "p84", "p97.5"), np.percentile(c, [2.5, 16, 50, 84, 97.5]).tolist()))
    out["contrast_mW"]["p_leq0"] = float(np.mean(c <= 0))
    out["meta"] = dict(n_walkers=N_WALKERS, n_steps=N_STEPS, n_burn=N_BURN, seed=SEED,
                       grid=dict(A=A_G.tolist(), kd_mW=(KD_G * 1e3).tolist(), Qb_mW={k: v.tolist() for k, v in QB_G.items()},
                                 rho_d=RHO_G.tolist()))
    q = out["contrast_mW"]
    print(f"  contrast {q['p50']:+.2f} [{q['p2.5']:+.2f}, {q['p97.5']:+.2f}], P(<=0) = {q['p_leq0']:.4f}", flush=True)
    (_REPO / "results" / "joint_mcmc.json").write_text(json.dumps(out, indent=1))
    np.savez_compressed(_REPO / "results" / "joint_mcmc_chains.npz", **chains)
    print("wrote results/joint_mcmc.json, results/joint_mcmc_chains.npz")


def main():
    done = build_grid() if "--sample" not in sys.argv else None
    if done is None:
        c = np.load(GRID, allow_pickle=False); done = {}
        for k, job in enumerate(c["jobs"]):
            done[(str(job[0]), float(job[1]), float(job[2]), float(job[3]))] = (c[f"r{k}_Tz"], c[f"r{k}_Ts"], c[f"r{k}_kap"])
    missing = [j for j in rows() if j not in done]
    if missing:
        print(f"grid incomplete ({len(missing)} rows missing); run without --sample to finish it")
        return
    sample(done)


if __name__ == "__main__":
    main()
