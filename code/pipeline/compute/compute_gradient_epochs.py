"""How the measured meter-scale gradient depends on the window epoch (2026-10-05).

The retrieval uses per-sensor stability windows, which end at different dates
(Table S4); because the column warmed throughout the record, mostly from the
top, a temperature difference between sensors depends on when each was
averaged. This script compares the observed gradient (OLS over the retained
sensors, with its standard error) for
  * the per-sensor windows used in the paper ("certified"),
  * one shared 1974 window ("common_1974"), and
  * each sensor's value carried back to 1974 along its own trailing slope
    ("translated_1974"),
with the model gradients (joint fit, global K_d = 3.4, Martinez & Siegler
forward), the independent thermoluminescence gradient of the A17 deep drill
core (Sehlke et al. 2026: 1.0 +- 0.5 K/m over 133-291 cm), and the basal flux
at which the joint-fit model would match each observed gradient (same linear
Q_b-vs-gradient relation as compute_joint_fit_checks.py).

Reads:  results/common_epoch_sensitivity.json, results/joint_fit_checks.json
Writes: results/gradient_epochs.json
Runtime: seconds.
"""
from __future__ import annotations
import json, sys, pathlib
_REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO)); sys.path.insert(0, str(_REPO / "src"))

import numpy as np

TL_A17 = dict(gradient_K_per_m=1.0, sigma=0.5, depth_cm=[133, 291], source="Sehlke et al. (2026), thermoluminescence")
EPOCHS = {"certified": "T_certified", "common_1974": "T_common", "translated_1974": "T_translated"}


def ols(z, T):
    X = np.vstack([np.ones_like(z), z]).T
    beta, *_ = np.linalg.lstsq(X, T, rcond=None)
    s2 = float(((T - X @ beta) ** 2).sum() / (len(z) - 2))
    return float(beta[1]), float(np.sqrt(s2 * np.linalg.inv(X.T @ X)[1, 1]))


def main():
    ep = json.loads((_REPO / "results" / "common_epoch_sensitivity.json").read_text())
    chk = json.loads((_REPO / "results" / "joint_fit_checks.json").read_text())
    out = {"tl_a17": TL_A17, "sites": {}}
    for s in ("A15", "A17"):
        S = [r for r in ep[s]["sensors"] if r["depth_cm"] >= 80]
        z = np.array([r["depth_cm"] for r in S]) / 100.0
        c = chk[s]
        model = dict(joint_fit=c["fit_with_diffusivity"]["gradient_model_K_per_m"],
                     global_3p4=c["global_3p4"]["gradient_model_K_per_m"],
                     martinez=c["martinez_forward"]["gradient_model_K_per_m"])
        pts = np.array(c["qb_matching_observed_gradient"]["points"])      # (Q_b, model gradient) at the joint fit
        p = np.polyfit(pts[:, 1], pts[:, 0], 1)
        site = dict(model_gradient_K_per_m=model, observed={})
        obs = {k: ols(z, np.array([r[v] for r in S], float)) for k, v in EPOCHS.items()}
        if s == "A17":
            obs["thermoluminescence"] = (TL_A17["gradient_K_per_m"], TL_A17["sigma"])
        for k, (g, se) in obs.items():
            site["observed"][k] = dict(gradient_K_per_m=g, se=se,
                                       tension_sigma={m: (mg - g) / se for m, mg in model.items()},
                                       qb_matching_mW=float(np.polyval(p, g)))
        out["sites"][s] = site
    path = _REPO / "results" / "gradient_epochs.json"
    path.write_text(json.dumps(out, indent=1))
    for s, site in out["sites"].items():
        mg = site["model_gradient_K_per_m"]
        print(f"{s}: model joint {mg['joint_fit']:.2f}, global {mg['global_3p4']:.2f}, Martinez {mg['martinez']:.2f} K/m")
        for k, o in site["observed"].items():
            t = o["tension_sigma"]
            print(f"   {k:18s} {o['gradient_K_per_m']:+.2f} +- {o['se']:.2f}  tension joint {t['joint_fit']:.1f} sigma, "
                  f"global {t['global_3p4']:.1f}, Martinez {t['martinez']:.1f};  Q_b match {o['qb_matching_mW']:.1f} mW/m2")
    print(f"wrote {path.relative_to(_REPO)}")


if __name__ == "__main__":
    main()
