"""How K_d* is retrieved (guidebook helper; answers 'where does Apollo enter?').

Self-contained: runs real Step A+B solves (lunar.equilibrium via retrieve_kd) and
plots two panels for Apollo 17:
 (a) a FAN of forward-model profiles, one per candidate K_d -- no Apollo data goes
     into them; below the anchor they spread, and the Apollo deep sensors (the only
     place data enters) pick out the one that threads them;
 (b) the RMSE(K_d) misfit curve, whose minimum is K_d*.
House style module; no text on the data; every number from a real solve.
"""
import pathlib
import sys

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

_REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO / "src"))
sys.path.insert(0, str(_REPO / "pipeline" / "compute"))
import retrieve_kd as R                                            # noqa: E402
from lunar.config import SITES, KD_GRIDS                          # noqa: E402
from lunar.apollo_helpers import extract_sensor_stability         # noqa: E402
from lunar.plotting.style import (                                # noqa: E402
    JGR_HALF, C_A17, C_CHAR, C_DIM, C_GRID, fmt_axis, FS_LEGEND,
    assert_no_overlap, legend_below,
)

OUT = _REPO / ".." / "figures"
ANCHOR_M = 0.55
KD_FAN = [5.0e-3, 6.0e-3, 7.08e-3, 8.5e-3, 10.0e-3]      # candidate K_d for panel (a)
# misfit curve for panel (b): the REAL dense retrieval grid (restricted to the bowl
# window) so the vertex lands on the headline K_d* (7.08), consistent with App C.
_g = KD_GRIDS["A17"]
KD_RMSE = _g[(_g >= 4.5e-3) & (_g <= 10.5e-3)]


def _solves():
    import json
    cache = OUT.parent / "fig_retrieval_demo.json"
    canon = OUT.parent / "kd_retrieval_results.json"
    # STALENESS GUARD (2026-07-04): a cache older than the canonical
    # retrieval is a lie -- the chain once re-rendered this figure from
    # solves of a superseded solver. Recompute unless the cache is newer.
    fresh = (cache.exists() and canon.exists()
             and cache.stat().st_mtime > canon.stat().st_mtime)
    if fresh:                                # reuse cached solves for fast re-render
        d = json.loads(cache.read_text())
        prof = {float(k): (np.array(v["z"]), np.array(v["T"]))
                for k, v in d["profiles"].items()}
        return (np.array(d["z_obs"]), np.array(d["T_obs"]), prof,
                np.array(d["rmse"]), d["kd_star"], d["rmse_star"])
    site = SITES["A17"]
    obs = extract_sensor_stability(site["mission"], min_depth_cm=site["MIN_DEPTH_CM"])
    deep = np.asarray(obs["deep_mask"], bool)
    z_obs = np.asarray(obs["depth_cm_all"])[deep] / 100.0
    T_obs = np.asarray(obs["T_eq_all"])[deep]
    profiles = {}
    for kd in KD_FAN:
        z_mid, T_mean = R.run_with(site, kd=kd, k_model="hayne")
        profiles[round(kd * 1e3, 2)] = (z_mid, T_mean)
    Rmat = np.empty((len(z_obs), len(KD_RMSE)))
    rmse = []
    for k, kd in enumerate(KD_RMSE):
        z_mid, T_mean = R.run_with(site, kd=kd, k_model="hayne")   # cached
        res = np.interp(z_obs, z_mid, T_mean) - T_obs
        Rmat[:, k] = res
        rmse.append(float(np.sqrt((res ** 2).mean())))
    kd_star, rmse_star = R.kd_star_from_residuals(Rmat, KD_RMSE)
    cache.write_text(json.dumps(dict(
        z_obs=z_obs.tolist(), T_obs=T_obs.tolist(),
        profiles={f"{k:.2f}": dict(z=v[0].tolist(), T=v[1].tolist())
                  for k, v in profiles.items()},
        rmse=list(rmse), kd_star=float(kd_star * 1e3), rmse_star=float(rmse_star))))
    return z_obs, T_obs, profiles, np.array(rmse), kd_star * 1e3, rmse_star


def main():
    z_obs, T_obs, profiles, rmse, kd_star, rmse_star = _solves()
    fan = [round(k * 1e3, 2) for k in KD_FAN]
    norm = (np.array(fan) - min(fan)) / (max(fan) - min(fan))

    fig, (axL, axR) = plt.subplots(1, 2, figsize=(JGR_HALF, 3.5))
    fig.subplots_adjust(left=0.10, right=0.975, top=0.90, bottom=0.14, wspace=0.34)

    # (a) candidate-profile fan vs the Apollo sensors -----------------------
    for kd, x in zip(fan, norm):
        z_mid, T_mean = profiles[kd]
        m = (z_mid >= 0.42) & (z_mid <= 2.45)         # deep zoom, where K_d matters
        best = abs(kd - kd_star) < 0.25
        axL.plot(T_mean[m], z_mid[m], color=(C_A17 if best else C_DIM),
                 lw=(2.6 if best else 1.2), alpha=(1.0 if best else 0.45 + 0.5 * x),
                 zorder=(4 if best else 2))
    axL.plot(T_obs, z_obs, "o", color=C_CHAR, ms=5, zorder=5)
    axL.axhline(ANCHOR_M, color=C_DIM, ls="--", lw=1.0, zorder=3)
    axL.set_ylim(2.45, 0.42)
    axL.set_xlim(253.4, 258.3)
    fmt_axis(axL, xlabel=r"$\langle T\rangle$  (K)", ylabel="depth  (m)",
             title="(a)  sweep: one A+B profile per $K_d$")
    handles = [
        Line2D([0], [0], color=C_DIM, lw=1.4, label="candidates"),
        Line2D([0], [0], color=C_A17, lw=2.6, label=r"$K_d^{*}$ fit"),
        Line2D([0], [0], marker="o", color="none", markerfacecolor=C_CHAR,
               ms=5, label="Apollo"),
        Line2D([0], [0], color=C_DIM, ls="--", lw=1.0, label="anchor"),
    ]
    # panel (a) fills its axes (the fan) -> shared legend BELOW, never on the data

    # (b) RMSE(K_d) -> minimum ---------------------------------------------
    kd = KD_RMSE * 1e3
    axR.plot(kd, rmse, "o-", color=C_A17, mfc=C_A17, mec="white", ms=5, lw=1.8,
             zorder=3)
    # the retrieved value lives in the panel title (fully outside the data);
    # the star + dotted vline mark the spot without any in-axes text box
    # (the previous xytext pushed a label left of the axis, onto the y-ticks)
    axR.axvline(kd_star, color=C_DIM, ls=":", lw=1.1, zorder=1)
    axR.plot([kd_star], [rmse_star], "*", color=C_CHAR, ms=12, zorder=4)
    fmt_axis(axR, xlabel=r"candidate $K_d$  (mW m$^{-1}$K$^{-1}$)",
             ylabel="RMSE vs Apollo  (K)",
             title=rf"(b)  smallest misfit: $K_d^{{*}}={kd_star:.2f}$")

    legend_below(fig, handles, [h.get_label() for h in handles], ncols=4)
    fig.canvas.draw()
    assert_no_overlap(axL)            # programmatic text-on-data guard
    assert_no_overlap(axR)
    OUT.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT / "fig_retrieval_demo.pdf")
    plt.close(fig)
    print("wrote", OUT / "fig_retrieval_demo.pdf", f"(K_d*={kd_star:.3f})")


if __name__ == "__main__":
    main()
