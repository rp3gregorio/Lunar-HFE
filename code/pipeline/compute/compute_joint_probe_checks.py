"""Three checks on what the diffusivity and the original Apollo calibration can support (2026-10-05).

Re-analyses the committed joint-fit grid (results/joint_albedo_fit_cache.npz); no new solves.

  1. Per-probe K_d: each annual-wave diffusivity of Langseth et al. (1976, Table 1) on its own,
     converted to K_d at the site's fitted albedo (the K_d at which the model diffusivity over
     that probe's depth range equals the measured value; +-1 sigma from the stated errors).
  2. Transient diffusivities: the same conversion for the "transient results" of the same table
     (recovery from the drilling disturbance), at the deepest ranges listed for each probe. The
     A15 ranges start at the surface; the stored profile starts at 5 cm, so they are taken from 5 cm.
  3. The original calibration: Hayne et al. (2017, App. A3) set K_d = 3.4 so that the model met
     the Keihm et al. (1973) diurnal means within +-5 K (surface 211 / 216 K; 252 K at 0.8 m at
     A15, 256 K at 1.3 m at A17) at a prescribed albedo. Here: the K_d range that passes the same
     test at the constant A = 0.12 and at the jointly fitted albedo.

Reads:  results/joint_albedo_fit_cache.npz, results/joint_albedo_fit.json
Writes: results/joint_probe_checks.json
Runtime: seconds.
"""
from __future__ import annotations
import json, sys, pathlib
_REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO)); sys.path.insert(0, str(_REPO / "src")); sys.path.insert(0, str(_REPO / "pipeline" / "compute"))

import numpy as np
from lunar.config import HAYNE
from lunar.constants import RHO_SURFACE, RHO_DEEP
from lunar.properties import conductivity_hayne, specific_heat, density_hayne
import compute_joint_albedo_fit as jf

# Langseth et al. (1976) Table 1, transient results at the deepest ranges: (z_top m, z_bottom m, kappa [1e-4 cm^2/s])
TRANSIENT = {"A15": [(0.05, 1.38, 0.71), (0.05, 0.96, 0.60)],
             "A17": [(1.30, 1.77, 0.70), (1.85, 2.33, 0.75), (1.31, 1.78, 0.65), (1.86, 2.34, 0.63)]}
# Keihm et al. (1973a,b) via Hayne et al. (2017) App. A3: (depth m, diurnal-mean T K); tolerance +-5 K
KEIHM_DEEP = {"A15": (0.8, 252.0), "A17": (1.3, 256.0)}
KEIHM_TOL = 5.0
A_HAYNE = 0.12


def main():
    c = np.load(_REPO / "results" / "joint_albedo_fit_cache.npz")
    res = json.loads((_REPO / "results" / "joint_albedo_fit.json").read_text())
    A, K = c["A_grid"], c["kd_grid"] * 1e3
    Z = jf.Z_DENSE
    ks, H, chi = HAYNE["K_S"], HAYNE["H"], HAYNE["CHI"]
    rho = density_hayne(Z, rho_s=RHO_SURFACE, rho_d=RHO_DEEP, H=H)
    ok = K <= jf.KD_CERTIFIED_MAX * 1e3

    def kappa_curve(s, ia, z1, z2):
        zz = np.linspace(z1, z2, 200)
        out = np.empty(len(K))
        for ik, kd in enumerate(K):
            T = c[f"{s}_prof"][ia, ik]
            kz = conductivity_hayne(T, Z, Ks=ks, Kd=kd * 1e-3, H=H, chi=chi) / (rho * specific_heat(T, model="hayne")) * 1e8
            out[ik] = np.interp(zz, Z, kz).mean()
        return out

    def kd_at(curve, kobs):
        return float(np.interp(kobs, curve[ok], K[ok]))

    out = {"sites": {}}
    for s in ("A15", "A17"):
        A_star = res["sites"][s]["with_diffusivity"]["best"]["A"]
        ia = int(np.argmin(abs(A - A_star)))
        site = {"A_used": float(A[ia]), "per_probe_annual": [], "transient": []}
        for p, (z1, z2, kobs, sig) in enumerate(jf.KAPPA_OBS[s]):
            cv = kappa_curve(s, ia, z1, z2)
            site["per_probe_annual"].append(dict(probe=p + 1, depth_cm=[z1 * 100, z2 * 100], kappa_obs=kobs, sigma=sig,
                                                 kd_mW=kd_at(cv, kobs), kd_1sigma_mW=[kd_at(cv, kobs - sig), kd_at(cv, kobs + sig)]))
        k1, k2 = jf.KAPPA_OBS[s][0][2:], jf.KAPPA_OBS[s][1][2:]
        site["probe_difference_in_sigma"] = abs(k1[0] - k2[0]) / float(np.hypot(k1[1], k2[1]))
        for z1, z2, kobs in TRANSIENT[s]:
            site["transient"].append(dict(depth_cm=[z1 * 100, z2 * 100], kappa_obs=kobs, kd_mW=kd_at(kappa_curve(s, ia, z1, z2), kobs)))
        # the original calibration test: one deep temperature and the surface mean, each within +-5 K
        zd, Td = KEIHM_DEEP[s]
        Tdeep = np.array([[np.interp(zd, Z, c[f"{s}_prof"][i, k]) for k in range(len(K))] for i in range(len(A))])
        Ts = c[f"{s}_Ts"]
        passes = (abs(Tdeep - Td) <= KEIHM_TOL) & (abs(Ts - jf.TS_OBS[s]) <= KEIHM_TOL) & ok[None, :]
        for name, a in (("A_0.12", A_HAYNE), ("A_fitted", A_star)):
            i = int(np.argmin(abs(A - a)))
            kk = K[passes[i]]
            site[f"keihm_test_{name}"] = dict(A=float(A[i]), kd_pass_mW=[float(kk.min()), float(kk.max())] if kk.size else None,
                                              n_pass=int(kk.size), n_tested=int(ok.sum()))
        out["sites"][s] = site
    for s in ("A15", "A17"):
        v = [t["kd_mW"] for t in out["sites"][s]["transient"]]
        out["sites"][s]["transient_kd_range_mW"] = [min(v), max(v)]
        out["sites"][s]["transient_kd_mean_mW"] = float(np.mean(v))
    path = _REPO / "results" / "joint_probe_checks.json"
    path.write_text(json.dumps(out, indent=1))
    for s, d in out["sites"].items():
        pp = ", ".join(f"probe {q['probe']}: {q['kd_mW']:.2f}" for q in d["per_probe_annual"])
        print(f"{s}: per-probe {pp} (difference {d['probe_difference_in_sigma']:.2f} sigma); "
              f"transient {d['transient_kd_range_mW'][0]:.2f}-{d['transient_kd_range_mW'][1]:.2f} (mean {d['transient_kd_mean_mW']:.2f})")
        for name in ("A_0.12", "A_fitted"):
            t = d[f"keihm_test_{name}"]
            print(f"    +-5 K Keihm test at A={t['A']}: K_d passing {t['kd_pass_mW']} ({t['n_pass']}/{t['n_tested']} grid values)")
    print(f"wrote {path.relative_to(_REPO)}")


if __name__ == "__main__":
    main()
