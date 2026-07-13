#!/usr/bin/env python3
"""Q_b prior-width sensitivity of the Bayesian ordering probability.

The letter quotes the ordering P(K_d*(A17) > K_d*(A15)) as a function of
the Gaussian Q_b prior width. This script makes that scan a REPRODUCIBLE
ARTIFACT (audit 2026-07-13, codex F7: the scan previously existed only
as a source-code comment): it importance-reweights the archived
(Jacobian-corrected) MCMC chains from bayesian_crosscheck.py to
alternative prior widths, instead of re-running the sampler.

Reweighting is exact for the prior factor: the posterior at width s'
differs from the run posterior (width s_run = 0.15*Q_b) only by
N(qb; mu, s') / N(qb; mu, s_run), evaluated per sample and per site.
Effective sample sizes are reported so degenerate reweightings are
visible.

Reads  results/bayesian_chains.npz  (corrected run)
Writes results/qb_prior_width_scan.json

Run: python code/pipeline/compute/qb_prior_width_scan.py
"""
from __future__ import annotations

import json
import pathlib
import sys

import numpy as np

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
from lunar.config import SITES  # noqa: E402

CHAINS = ROOT / "results" / "bayesian_chains.npz"
OUT = ROOT / "results" / "qb_prior_width_scan.json"
RUN_WIDTH_FRAC = 0.15          # the width bayesian_crosscheck.py ran at
SCAN_FRACS = (0.10, 0.15, 0.25, 0.40)


def log_norm(x, mu, sig):
    return -0.5 * ((x - mu) / sig) ** 2 - np.log(sig)


def weighted_quantile(x, w, q):
    i = np.argsort(x)
    c = np.cumsum(w[i])
    return float(x[i][np.searchsorted(c, q * c[-1])])


def main():
    d = np.load(CHAINS)
    kd = {"A15": d["a15_kd"], "A17": d["a17_kd"]}
    qb = {"A15": d["a15_qb"], "A17": d["a17_qb"]}
    mu = {"A15": 1e3 * SITES["A15"]["Q_BASAL"], "A17": 1e3 * SITES["A17"]["Q_BASAL"]}

    rows = []
    for f in SCAN_FRACS:
        w, ess = {}, {}
        for s in ("A15", "A17"):
            lw = (log_norm(qb[s], mu[s], f * mu[s])
                  - log_norm(qb[s], mu[s], RUN_WIDTH_FRAC * mu[s]))
            wi = np.exp(lw - lw.max())
            w[s] = wi / wi.sum()
            ess[s] = float(1.0 / np.sum(w[s] ** 2))
        # independent-site ordering probability under the reweighted draws
        i = np.argsort(kd["A15"])
        k15s, w15s = kd["A15"][i], w["A15"][i]
        cw = np.concatenate([[0.0], np.cumsum(w15s)])
        frac_below = cw[np.searchsorted(k15s, kd["A17"])] / cw[-1]
        p_gt = float(np.sum(w["A17"] * frac_below))
        # weighted contrast median via independent quantile difference is not
        # exact; report the median of the reweighted PAIRED difference using
        # a common random permutation (chains are same length, independent).
        rng = np.random.default_rng(0)
        j = rng.permutation(len(kd["A15"]))
        diff = kd["A17"] - kd["A15"][j]
        wd = w["A17"] * w["A15"][j]
        med = weighted_quantile(diff, wd, 0.5)
        lo = weighted_quantile(diff, wd, 0.025)
        rows.append(dict(width_frac=f, p_gt=round(p_gt, 4),
                         contrast_median=round(med, 3),
                         contrast_q025=round(lo, 3),
                         ess_A15=round(ess["A15"], 0),
                         ess_A17=round(ess["A17"], 0)))
        print(f"  width {int(100*f)}%: P(A17>A15) = {p_gt:.4f}, "
              f"contrast median = {med:+.2f}, q025 = {lo:+.2f}, "
              f"ESS = {ess['A15']:.0f}/{ess['A17']:.0f}")

    OUT.write_text(json.dumps(dict(
        method="importance reweighting of the Jacobian-corrected chains "
               "(bayesian_chains.npz) to alternative Gaussian Q_b prior "
               "widths; run width 15% of Q_b",
        run_width_frac=RUN_WIDTH_FRAC, rows=rows), indent=2))
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
