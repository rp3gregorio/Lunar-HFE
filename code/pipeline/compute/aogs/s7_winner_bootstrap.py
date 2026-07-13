"""Winner-stability bootstrap for the AOGS density study — zero new solves.

The 650-run archive (aogs_density_study.json) stores every config's
T_model_at_sensors alongside each site's observed sensor T_eq and T_std.
That makes the letter-style bootstrap free: resample the deep sensors
with replacement (adding the per-sensor observational sigma), recompute
every config's RMSE from the stored model temperatures, and re-pick the
argmin. The fraction of draws in which the production winner survives is
the "winner stability"; the spread of the best-RMSE across draws is the
uncertainty band the poster's point values were missing.

Mirrors the letter's bootstrap philosophy (kd_retrieval_results.json
['bootstrap']) applied to the discrete-layer sweep.

Outputs -> results/aogs_winner_bootstrap.json
Run:  .venv/bin/python code/pipeline/compute/aogs_winner_bootstrap.py  (~2 s)
"""
from __future__ import annotations

import json
import pathlib
import sys

import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3] / "src"))
from lunar._bootstrap import find_repo_root  # noqa: E402

ROOT = find_repo_root()
IN = ROOT / "results" / "aogs_density_study.json"
OUT = ROOT / "results" / "aogs_winner_bootstrap.json"
N_BOOT = 10_000
SEED = 0


def main():
    d = json.loads(IN.read_text())
    rng = np.random.default_rng(SEED)
    out = {"meta": {"n_boot": N_BOOT, "seed": SEED,
                    "method": "sensor resample w/ replacement + N(0, T_std) "
                              "noise; argmin over stored T_model_at_sensors"}}

    for site in ("A15", "A17"):
        obs = np.asarray(d["sites"][site]["sensor_T_eq"])
        std = np.asarray(d["sites"][site]["sensor_T_std"])
        n_sen = len(obs)
        for branch in ("cp", "coupled"):
            recs = [r for r in d["runs"]
                    if r["site"] == site and r["branch"] == branch
                    and r["rho"] != "hayne"]
            T = np.asarray([r["T_model_at_sensors"] for r in recs])  # (n_cfg, n_sen)
            labels = [f"z={int(r['z1_m']*100)}/{int(r['z2_m']*100)} "
                      f"rho={'/'.join(str(int(x)) for x in r['rho'])}"
                      for r in recs]
            prod_win = int(np.argmin([r["rmse_K"] for r in recs]))

            wins = np.zeros(len(recs), dtype=int)
            best_rmse = np.empty(N_BOOT)
            for b in range(N_BOOT):
                idx = rng.integers(0, n_sen, n_sen)              # resample sensors
                o = obs[idx] + rng.normal(0.0, std[idx])          # + obs noise
                rmse = np.sqrt(((T[:, idx] - o) ** 2).mean(axis=1))
                k = int(np.argmin(rmse))
                wins[k] += 1
                best_rmse[b] = rmse[k]

            order = np.argsort(wins)[::-1][:5]
            out[f"{site}_{branch}"] = {
                "production_winner": labels[prod_win],
                "winner_stability": float(wins[prod_win] / N_BOOT),
                "top5": [{"config": labels[i], "share": float(wins[i] / N_BOOT)}
                         for i in order],
                "best_rmse_median_K": float(np.median(best_rmse)),
                "best_rmse_ci95_K": [float(np.percentile(best_rmse, 2.5)),
                                     float(np.percentile(best_rmse, 97.5))],
            }
            t5 = out[f"{site}_{branch}"]["top5"]
            print(f"{site} {branch:8s} winner {labels[prod_win]:34s} "
                  f"stability {wins[prod_win]/N_BOOT:5.1%}  "
                  f"best-RMSE {np.median(best_rmse):.2f} "
                  f"[{np.percentile(best_rmse,2.5):.2f},"
                  f"{np.percentile(best_rmse,97.5):.2f}] K")
            for e in t5[:3]:
                print(f"    {e['share']:6.1%}  {e['config']}")

    OUT.write_text(json.dumps(out, indent=1))
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
