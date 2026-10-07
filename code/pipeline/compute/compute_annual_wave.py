"""The annual temperature wave in the restored HFE record, measured and forward-modeled (2026-10-06).

The joint retrieval takes its conductivity constraint from the annual-wave
diffusivities of Langseth et al. (1976): four numbers obtained in 1975 by
fitting annual components by eye to 2-3 years of data, from amplitudes only.
This script measures the annual wave again from the full restored record and
compares it with the model directly, without the uniform-medium conversion.

1. Measurement. For every sensor, daily means of the restored record
   (flag 0) from 180 days after emplacement are fitted by least squares with
   a cubic Legendre trend (the long-term warming), four harmonics of the
   synodic month (the diurnal wave and its distortion), and one annual
   harmonic (365.26 d). Uncertainties of the annual cosine/sine pair come from
   a moving-block bootstrap of the residuals (30-day blocks).
2. Forward model. The Hayne column at the site's joint-fit albedo is driven by
   the real insolation (SPICE: DE440 Sun position, solar distance and the
   Moon's orientation, 1966-1977, dt = 1800 s), started from the periodic
   equilibrium profile at the same K_d. Its daily means at each sensor depth
   are fitted with the same model on the same days as the data.
3. Fit. At each K_d the model's complex annual amplitude at sensor i, m_i, is
   compared with the observed one, o_i, after one free complex factor per
   probe (g_p: amplitude scale and phase shift). g_p absorbs everything common
   to a probe -- the size and timing of the surface forcing, the effective
   albedo and emissivity, the borestem -- so K_d is set only by how the wave
   shrinks and lags with depth. chi^2(K_d) = sum_i r_i^T C_i^-1 r_i with
   r_i = o_i - g_p m_i and C_i the bootstrap covariance.

Variants: trend degree 2 and 4, a 365-day start, the A17 Gradient-bridge
sensors to 1977 (with gaps), the albedo +-0.01, a shared factor per site,
and the A17 sensors at or below 130 cm only.
Also reported: the uniform-medium diffusivity per probe from the data alone
(amplitude decay and phase lag, Langseth's method), for comparison with
Langseth et al. (1976).

Reads:  data/apollo/depth/*.tab, data/spice/*, results/joint_albedo_fit.json
Writes: results/annual_wave.json, results/annual_wave_model.npz, results/annual_wave_runs_cache.npz
Runtime: ~3 min on 5 workers; seconds with --reuse (forward runs cached).
"""
from __future__ import annotations
import json, sys, pathlib, time
from multiprocessing import Pool
_REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO)); sys.path.insert(0, str(_REPO / "src"))

import numpy as np
import pandas as pd
from numpy.polynomial import legendre as L

SYN = 29.530589            # mean synodic month [d]
YEAR = 365.2596            # anomalistic year [d] (Sun-Moon distance; the dominant annual forcing)
DEG, N_DIURNAL, START_D, NBOOT, BLOCK = 3, 4, 180.0, 500, 30
T0 = pd.Timestamp("1972-01-01", tz="UTC")
SPICE_START, SPICE_END = "1966-01-01T00:00:00", "1978-01-01T00:00:00"
END_1974 = 1095.0          # 1974-12-31 in days since 1972-01-01
PROBES = {"A15": ("a15p1", "a15p2"), "A17": ("a17p1", "a17p2")}
KD_SCAN = np.round(np.concatenate([np.arange(2.0, 12.01, 0.25), [3.4]]), 3)
KAPPA_LANGSETH = {"A15": (0.87, 0.74), "A17": (1.00, 0.88)}     # 1e-4 cm^2/s, Table 1
# the end sensors of the depth ranges Langseth et al. (1976) give for each probe (35-138, 49-96, 15-185, 16-186 cm)
LANGSETH_PAIRS = {"A15": {("p1", "TG11A"), ("p1", "TG12B"), ("p2", "TG22A"), ("p2", "TG22B")},
                  "A17": {("p1", "TC12"), ("p1", "TG12A"), ("p2", "TC22"), ("p2", "TG22A")}}
CURVE_Z = np.round(np.linspace(0.10, 2.40, 47), 3)                 # dense depths for the figure
AU_KM = 149597870.7
OMEGA = 2 * np.pi / (YEAR * 86400.0)


# ----------------------------------------------------------------------------- data
def load_probe(tag):
    d = pd.read_csv(_REPO / "data" / "apollo" / "depth" / f"{tag}_depth.tab", parse_dates=["Time"])
    d = d[d["flags"] == 0]
    out = {}
    for s, g in d.groupby("sensor"):
        g = g.sort_values("Time")
        t = (g["Time"] - T0).dt.total_seconds().to_numpy() / 86400.0
        day = np.floor(t).astype(int)
        u, inv = np.unique(day, return_inverse=True)
        cnt = np.bincount(inv)
        out[s.strip()] = dict(z=float(g["depth"].iloc[0]) / 100.0, day=u,
                              T=np.bincount(inv, g["T"].to_numpy()) / cnt)
    return out


def design(t, deg, nd):
    tau = 2 * (t - t.min()) / (t.max() - t.min()) - 1
    cols = [L.legval(tau, np.eye(deg + 1)[j]) for j in range(deg + 1)]
    for k in range(1, nd + 1):
        w = 2 * np.pi * k / SYN
        cols += [np.cos(w * t), np.sin(w * t)]
    w = 2 * np.pi / YEAR
    cols += [np.cos(w * t), np.sin(w * t)]
    return np.vstack(cols).T


def annual(t, T, deg=DEG, nboot=0, rng=None):
    """Annual cosine/sine amplitudes (a, b) of T(t) = ... + a cos(wt) + b sin(wt), and their covariance."""
    X = design(t, deg, N_DIURNAL)
    beta, *_ = np.linalg.lstsq(X, T, rcond=None)
    ab = beta[-2:]
    if not nboot:
        return ab, None
    fit = X @ beta; r = T - fit; n = len(T); nb = int(np.ceil(n / BLOCK))
    P = np.linalg.pinv(X)[-2:]
    draws = np.empty((nboot, 2))
    for k in range(nboot):
        st = rng.integers(0, max(1, n - BLOCK), nb)
        rr = np.concatenate([r[s:s + BLOCK] for s in st])[:n]
        draws[k] = P @ (fit + rr)
    return ab, np.cov(draws.T)


def windows(site, variant):
    """(first day, last day) of the analysis window of each sensor for a variant."""
    def w(tag, s, v):
        d0 = v["day"].min() + (365.0 if variant == "start_365" else START_D)
        d1 = v["day"].max()
        if site == "A17" and not (variant == "a17_to_1977" and s.startswith("TG") and s[3] == "1"):
            d1 = min(d1, END_1974)              # A17: the continuous record ends in Dec 1974
        if variant == "common_window":
            d1 = min(d1, END_1974 - 4)          # 1974-12-27, the last ring-bridge sample at both sites
        return d0, d1
    return w


# ----------------------------------------------------------------------------- model
_INSOL = {}


def spice_insolation(site):
    if site in _INSOL:
        return _INSOL[site]
    import spiceypy as spice
    from lunar import ephem
    from lunar.config import SITES, DT_STEP
    from lunar.constants import SOLAR_CONSTANT
    ephem._furnish_kernels()
    lat, lon = np.deg2rad(SITES[site]["lat"]), np.deg2rad(SITES[site]["lon"])
    up = np.array([np.cos(lat) * np.cos(lon), np.cos(lat) * np.sin(lon), np.sin(lat)])
    et0, et1 = spice.str2et(SPICE_START), spice.str2et(SPICE_END)
    et = et0 + np.arange(int((et1 - et0) // DT_STEP)) * DT_STEP
    S = np.empty(et.size)
    for i, ti in enumerate(et):
        p, _ = spice.spkpos("SUN", float(ti), "MOON_ME", "LT+S", "MOON")
        p = np.asarray(p); r = np.linalg.norm(p)
        S[i] = SOLAR_CONSTANT * max(0.0, float(p @ up) / r) / (r / AU_KM) ** 2
    day = np.floor((et - spice.str2et("1972-01-01T00:00:00")) / 86400.0).astype(int)
    _INSOL[site] = (et - et0, S, day)
    return _INSOL[site]


def model_run(job):
    """Daily-mean model temperature at each depth for one (site, A, K_d [mW], overrides)."""
    site, A, kd_mW, depths, ov = job
    from lunar.config import SITES, GRID, DT_STEP, HAYNE, EQ_Z_ANCHOR, EQ_N_INNER, EQ_MAX_OUTER, EQ_ANCHOR_TOL
    from lunar.grid import make_geometric_grid
    from lunar.solver import periodic_time_grid, standard_insolation, PixelInputs, solve_pixel
    from lunar.properties import conductivity_hayne, specific_heat
    from lunar.equilibrium import solve_periodic_equilibrium
    cfg = SITES[site]; kd = kd_mW * 1e-3
    ks, H, chi = HAYNE["K_S"], HAYNE["H"], ov.get("chi", HAYNE["CHI"])
    qb = ov.get("Q_b", cfg["Q_BASAL"])
    G = make_geometric_grid(**GRID)
    tp = periodic_time_grid(DT_STEP)
    eq = solve_periodic_equilibrium(
        grid=G, t=tp, insolation=standard_insolation(cfg["lat"], tp), albedo=A, emissivity=cfg["emissivity"], Q_b=qb,
        K_func=lambda T, zz: conductivity_hayne(T, zz, Ks=ks, Kd=kd, H=H, chi=chi),
        cp_func=lambda T: specific_heat(T, model="hayne"), T_guess=cfg["T_MEAN_EFF"], z_anchor=EQ_Z_ANCHOR,
        n_inner=EQ_N_INNER, max_outer=EQ_MAX_OUTER, anchor_tol_K=EQ_ANCHOR_TOL, hayne_params=(ks, kd, H, chi))
    t, S, day = spice_insolation(site)
    out = solve_pixel(PixelInputs(grid=G, t=t, bc_mode="radiative", insolation=S, albedo=A,
                                  emissivity=cfg["emissivity"], Q_b=qb, T_init=eq.T_mean.copy(),
                                  hayne_params=(ks, kd, H, chi), n_lunations_spinup=1))
    u, inv = np.unique(day, return_inverse=True); cnt = np.bincount(inv)
    zm = G.z_mid; Td = np.empty((len(depths), len(u)))
    for i, z in enumerate(depths):
        j = np.searchsorted(zm, z) - 1; w = (z - zm[j]) / (zm[j + 1] - zm[j])
        Td[i] = np.bincount(inv, out.T[j] * (1 - w) + out.T[j + 1] * w) / cnt
    return site, A, kd_mW, tuple(sorted(ov.items())), u, Td


# ----------------------------------------------------------------------------- fit
def fit_kd(obs, mod, groups, kds, part=None):
    """Profile chi^2 over K_d with one free complex factor per group.

    part = "amp" or "phase" fits only the log-amplitude or only the phase of each
    sensor relative to its group (diagnostic: which half of the wave sets K_d)."""
    if part:
        return fit_kd_part(obs, mod, groups, kds, part)
    chi2 = np.empty(len(kds)); gs = []
    for k, kd in enumerate(kds):
        c2, gk = 0.0, {}
        for gname, keys in groups.items():
            # weighted LS for g = (gr, gi): o ~ [[mr, -mi], [mi, mr]] g
            NtN = np.zeros((2, 2)); Nto = np.zeros(2); rows = []
            for key in keys:
                o, C = obs[key]; m = mod[(kd, key)]
                Mx = np.array([[m[0], -m[1]], [m[1], m[0]]])
                W = np.linalg.inv(C)
                NtN += Mx.T @ W @ Mx; Nto += Mx.T @ W @ o; rows.append((o, W, Mx))
            g = np.linalg.solve(NtN, Nto); gk[gname] = g
            c2 += sum(float((o - Mx @ g) @ W @ (o - Mx @ g)) for o, W, Mx in rows)
        chi2[k] = c2; gs.append(gk)
    return chi2, gs


def fit_kd_part(obs, mod, groups, kds, part):
    """Amplitude-only (log A) or phase-only fit, with one free offset per group."""
    def comp(ab, C):
        A = np.hypot(*ab); J = (np.array([ab[0], ab[1]]) / A**2 if part == "amp"
                                else np.array([-ab[1], ab[0]]) / A**2)
        val = np.log(A) if part == "amp" else np.arctan2(ab[1], ab[0])
        return val, float(J @ C @ J)
    chi2 = np.empty(len(kds))
    for k, kd in enumerate(kds):
        c2 = 0.0
        for keys in groups.values():
            y, v = [], []
            for key in keys:
                o, var = comp(*obs[key]); m, _ = comp(mod[(kd, key)], obs[key][1])
                d = o - m
                if part == "phase":
                    d = (d + np.pi) % (2 * np.pi) - np.pi
                y.append(d); v.append(var)
            y, w = np.array(y), 1 / np.array(v)
            off = float((w * y).sum() / w.sum()) if part == "amp" else float(np.angle((w * np.exp(1j * y)).sum()))
            r = y - off
            if part == "phase":
                r = (r + np.pi) % (2 * np.pi) - np.pi
            c2 += float((w * r**2).sum())
        chi2[k] = c2
    return chi2, [{} for _ in kds]


def profile_summary(kds, chi2, n_data, n_groups, ncomp=2):
    order = np.argsort(kds); x, y = kds[order], chi2[order]
    i = int(np.argmin(y))
    if 0 < i < len(x) - 1:                         # parabola through the three lowest points
        c = np.polyfit(x[i - 1:i + 2], y[i - 1:i + 2], 2)
        best = float(-c[1] / (2 * c[0])) if c[0] > 0 else float(x[i])
    else:
        best = float(x[i])
    fine = np.linspace(x[0], x[-1], 4001); yf = np.interp(fine, x, y); ymin = yf.min()
    dof = max(1, ncomp * (n_data - n_groups) - 1)
    s = max(1.0, ymin / dof)                       # inflate if the fit is worse than the errors allow
    def interval(level):
        ok = fine[yf <= ymin + level * s]
        return [float(ok.min()), float(ok.max())]
    return dict(kd_mW=best, ci68=interval(1.0), ci95=interval(3.84), chi2_min=float(ymin), dof=dof,
                error_scale=float(np.sqrt(s)), at_edge=bool(i in (0, len(x) - 1)),
                dchi2_global=float((np.interp(3.4, x, y) - ymin) / s))


def uniform_kappa(obs, sensors, keys):
    """Langseth's method on the data alone: kappa from amplitude decay and from phase lag (uniform medium)."""
    z = np.array([sensors[k]["z"] for k in keys])
    a = np.array([obs[k][0] for k in keys]); C = [obs[k][1] for k in keys]
    A = np.hypot(a[:, 0], a[:, 1]); ph = np.unwrap(np.arctan2(a[:, 1], a[:, 0]))
    sA = np.array([np.sqrt(np.array([x / Ai, y / Ai]) @ Ci @ np.array([x / Ai, y / Ai])) for (x, y), Ai, Ci in zip(a, A, C)])
    sph = np.array([np.sqrt(np.array([-y / Ai**2, x / Ai**2]) @ Ci @ np.array([-y / Ai**2, x / Ai**2])) for (x, y), Ai, Ci in zip(a, A, C)])
    out = {}
    for name, yv, sv in (("amplitude", np.log(A), sA / A), ("phase", ph, sph)):
        Wt = 1 / sv**2; X = np.vstack([np.ones_like(z), z]).T
        cov = np.linalg.inv(X.T @ (X * Wt[:, None])); beta = cov @ X.T @ (Wt * yv)
        slope, se = abs(beta[1]), float(np.sqrt(cov[1, 1]))
        d = 1 / slope                                       # skin depth [m]
        kap = OMEGA * d**2 / 2 * 1e8                        # [1e-4 cm^2/s]
        out[name] = dict(kappa=float(kap), se=float(2 * kap * se / slope), skin_depth_m=float(d))
    return out


def main():
    t0 = time.time()
    rng = np.random.default_rng(20261006)
    joint = json.loads((_REPO / "results" / "joint_albedo_fit.json").read_text())
    A_fit = {s: joint["sites"][s]["with_diffusivity"]["best"]["A"] for s in ("A15", "A17")}
    kd_joint = {s: joint["sites"][s]["with_diffusivity"]["best"]["kd_star_mW"] for s in ("A15", "A17")}
    sensors = {s: {(tag[-2:], k): v for tag in PROBES[s] for k, v in load_probe(tag).items()} for s in PROBES}

    variants = ["nominal", "common_window", "deg2", "deg4", "start_365", "a17_to_1977", "albedo_minus", "albedo_plus",
                "shared_factor", "family_factor", "amplitude_only", "phase_only", "langseth_pairs",
                "langseth_pairs_amp", "a17_deep_only"]
    # observations per variant (the window and the trend degree change the measurement itself)
    def measure(site, variant):
        w = windows(site, variant); deg = {"deg2": 2, "deg4": 4}.get(variant, DEG); obs, days = {}, {}
        for key, v in sensors[site].items():
            d0, d1 = w(key[0], key[1], v)
            m = (v["day"] >= d0) & (v["day"] <= d1)
            if m.sum() < 200:
                continue
            obs[key] = annual(v["day"][m] + 0.5, v["T"][m], deg=deg, nboot=NBOOT, rng=rng); days[key] = v["day"][m]
        return obs, days, deg

    # forward runs: K_d scan at the fitted albedo, and at +-0.01 for the albedo variants
    jobs = []
    for s in PROBES:
        depths = sorted({v["z"] for v in sensors[s].values()})
        for A in (A_fit[s], A_fit[s] - 0.01, A_fit[s] + 0.01):
            jobs += [(s, round(A, 4), float(kd), depths, {}) for kd in KD_SCAN]
    cache = _REPO / "results" / "annual_wave_runs_cache.npz"
    if "--reuse" in sys.argv and cache.exists():
        c = np.load(cache)
        store = {(s, A, kd): (c[f"{s}_{A:.4f}_{kd:.3f}_u"], c[f"{s}_{A:.4f}_{kd:.3f}_T"]) for s, A, kd, _, _ in jobs}
        print(f"reused {len(store)} forward runs", flush=True)
    else:
        print(f"{len(jobs)} forward runs", flush=True)
        with Pool(5) as pool:
            runs = pool.map(model_run, jobs, chunksize=4)
        store = {(s, A, kd): (u, Td) for s, A, kd, _, u, Td in runs}
        np.savez_compressed(cache, **{f"{s}_{A:.4f}_{kd:.3f}_{n}": a for (s, A, kd), (u, Td) in store.items()
                                      for n, a in (("u", u), ("T", Td))})
    depth_index = {s: sorted({v["z"] for v in sensors[s].values()}) for s in PROBES}
    print(f"  forward runs done ({time.time() - t0:.0f} s)", flush=True)

    out = dict(meta=dict(year_days=YEAR, trend_degree=DEG, diurnal_harmonics=N_DIURNAL, start_days=START_D,
                         n_boot=NBOOT, block_days=BLOCK, kd_scan_mW=KD_SCAN.tolist(), albedo=A_fit,
                         kd_joint_mW=kd_joint, kappa_langseth=KAPPA_LANGSETH),
               sites={})
    npz = {}
    for s in PROBES:
        site = dict(variants={}, sensors={}, uniform_kappa={})
        for variant in variants:
            if s == "A15" and variant in ("a17_to_1977", "a17_deep_only"):
                continue
            obs, days, deg = measure(s, variant)
            if variant == "a17_deep_only":
                obs = {k: v for k, v in obs.items() if sensors[s][k]["z"] >= 1.30}
            if variant.startswith("langseth_pairs"):
                obs = {k: v for k, v in obs.items() if k in LANGSETH_PAIRS[s]}
            A = round(A_fit[s] + {"albedo_minus": -0.01, "albedo_plus": 0.01}.get(variant, 0.0), 4)
            mod = {}
            for kd in KD_SCAN:
                u, Td = store[(s, A, float(kd))]
                for key in obs:
                    T = Td[depth_index[s].index(sensors[s][key]["z"])][np.searchsorted(u, days[key])]
                    mod[(kd, key)] = annual(days[key] + 0.5, T, deg=deg)[0]
            if variant == "shared_factor":
                groups = {"site": list(obs)}
            elif variant == "family_factor":      # one factor per probe AND sensor type (TG, TR, TC)
                groups = {f"{p}_{fam}": [k for k in obs if k[0] == p and k[1][:2] == fam]
                          for p in ("p1", "p2") for fam in ("TG", "TR", "TC")}
            else:
                groups = {p: [k for k in obs if k[0] == p] for p in ("p1", "p2")}
            groups = {g: k for g, k in groups.items() if k}
            chi2, gs = fit_kd(obs, mod, groups, KD_SCAN, part={"amplitude_only": "amp", "phase_only": "phase",
                                                                "langseth_pairs_amp": "amp"}.get(variant))
            if variant in ("nominal", "amplitude_only", "phase_only"):
                npz[f"{s}_chi2_{variant}"] = chi2
            summ = profile_summary(KD_SCAN, chi2, len(obs), len(groups),
                                   ncomp=1 if variant in ("amplitude_only", "phase_only", "langseth_pairs_amp") else 2)
            per_probe = {}
            if variant == "nominal":
                for p, keys in groups.items():
                    c2p, _ = fit_kd({k: obs[k] for k in keys}, mod, {p: keys}, KD_SCAN)
                    per_probe[p] = profile_summary(KD_SCAN, c2p, len(keys), 1)
                kb = KD_SCAN[np.argmin(chi2)]; gb = gs[int(np.argmin(chi2))]
                for key in obs:
                    o, C = obs[key]; m = mod[(kb, key)]; g = gb[key[0] if key[0] in gb else "site"]
                    pred = np.array([[m[0], -m[1]], [m[1], m[0]]]) @ g
                    site["sensors"][f"{key[0]}_{key[1]}"] = dict(
                        z_m=sensors[s][key]["z"], obs_ab=o.tolist(), obs_cov=C.tolist(),
                        obs_amp=float(np.hypot(*o)), obs_phase_deg=float(np.degrees(np.arctan2(o[1], o[0])) % 360),
                        pred_amp=float(np.hypot(*pred)), pred_phase_deg=float(np.degrees(np.arctan2(pred[1], pred[0])) % 360),
                        raw_model_amp=float(np.hypot(*m)), window_days=[int(days[key].min()), int(days[key].max())],
                        n_days=int(len(days[key])))
                site["factors"] = {p: dict(scale=float(np.hypot(*g)), phase_deg=float(np.degrees(np.arctan2(g[1], g[0]))))
                                   for p, g in gb.items()}
            if variant == "common_window":
                for p in ("p1", "p2"):
                    keys = [k for k in obs if k[0] == p and np.hypot(*obs[k][0]) / np.sqrt(np.trace(obs[k][1]) / 2) >= 3]
                    if len(keys) >= 3:
                        site["uniform_kappa"][p] = uniform_kappa(obs, sensors[s], sorted(keys, key=lambda k: sensors[s][k]["z"]))
                        site["uniform_kappa"][p]["sensors"] = [f"{k[1]} ({100 * sensors[s][k]['z']:.0f} cm)" for k in keys]
            site["variants"][variant] = dict(summ, per_probe=per_probe, n_sensors=len(obs))
            print(f"{s} {variant:14s} K_d = {summ['kd_mW']:.2f} [{summ['ci95'][0]:.2f}, {summ['ci95'][1]:.2f}] "
                  f"chi2 {summ['chi2_min']:.1f}/{summ['dof']}  global dchi2 {summ['dchi2_global']:.1f}"
                  + ("".join(f"  {p}: {v['kd_mW']:.2f} [{v['ci95'][0]:.2f}, {v['ci95'][1]:.2f}]" for p, v in per_probe.items())), flush=True)
        # model curves on dense depths for the figure: best annual-wave K_d, the joint fit, the global value
        obs, days, deg = measure(s, "nominal")
        kc = {"annual_wave": site["variants"]["nominal"]["kd_mW"], "joint": kd_joint[s], "global": 3.4}
        runs_c = {n: model_run((s, round(A_fit[s], 4), float(k), sorted(set(CURVE_Z) | set(depth_index[s])), {}))
                  for n, k in kc.items()}
        lo = min(int(d.min()) for d in days.values()); hi = max(int(d.max()) for d in days.values())
        curves = {}
        for n, (_, _, kd, _, u, Td) in runs_c.items():
            zz = sorted(set(CURVE_Z) | set(depth_index[s])); sel = (u >= lo) & (u <= hi)
            mod1 = {}
            for key in obs:
                T = Td[zz.index(sensors[s][key]["z"])][np.searchsorted(u, days[key])]
                mod1[(kd, key)] = annual(days[key] + 0.5, T)[0]
            _, g = fit_kd(obs, mod1, {p: [k for k in obs if k[0] == p] for p in ("p1", "p2")}, [kd])
            ab = np.array([annual(u[sel] + 0.5, Td[zz.index(z)][sel])[0] for z in CURVE_Z])
            curves[n] = dict(kd_mW=float(kd), ab=ab.tolist(), factor={p: v.tolist() for p, v in g[0].items()})
        site["curves"] = dict(z_m=CURVE_Z.tolist(), window_days=[lo, hi], **curves)
        out["sites"][s] = site
        for p, u in site["uniform_kappa"].items():
            print(f"   {s} {p} uniform-medium kappa: amplitude {u['amplitude']['kappa']:.2f} +- {u['amplitude']['se']:.2f}, "
                  f"phase {u['phase']['kappa']:.2f} +- {u['phase']['se']:.2f}  (Langseth {KAPPA_LANGSETH[s][int(p[1]) - 1]:.2f}; {', '.join(u['sensors'])})")
    n15, n17 = out["sites"]["A15"]["variants"]["nominal"], out["sites"]["A17"]["variants"]["nominal"]
    out["contrast_mW"] = n17["kd_mW"] - n15["kd_mW"]
    (_REPO / "results" / "annual_wave.json").write_text(json.dumps(out, indent=1))
    np.savez_compressed(_REPO / "results" / "annual_wave_model.npz", kd_scan_mW=KD_SCAN, **npz)
    print(f"contrast {out['contrast_mW']:+.2f}; wrote results/annual_wave.json ({time.time() - t0:.0f} s)")


if __name__ == "__main__":
    main()
