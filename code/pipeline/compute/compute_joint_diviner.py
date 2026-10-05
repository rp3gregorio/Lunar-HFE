"""Diviner surface-temperature comparison at the joint (albedo, K_d) fit (2026-10-05).

The joint-fit counterpart of compute_diviner_closure.py and of question 4
of compute_review_diagnostics.py. Three model diurnal cycles per site:
  * the Hayne form at the joint fit (A*, K_d*);
  * the Hayne form at the global K_d = 3.4 with its own fitted albedo;
  * the Martinez & Siegler (2021) forward model at the joint albedo;
each compared with the Diviner GCP (channel of compute_diviner_closure) as a
zonal curve and at the landing-site pixels (+-0.5 and +-1 deg), with the mean
bias split into day (06-18 LT) and night.

Reads:  results/joint_albedo_fit.json, Diviner GCP (code/data/diviner)
Writes: results/joint_diviner.json, ../figures/fig_joint_diviner_closure.pdf
Runtime: ~3 min.

Run with:
    python pipeline/compute/compute_joint_diviner.py
"""
from __future__ import annotations
import json, sys, pathlib, copy
_REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO)); sys.path.insert(0, str(_REPO / "src")); sys.path.insert(0, str(_REPO / "pipeline" / "compute"))

import numpy as np
import compute_diviner_closure as dc
from lunar.config import SITES, HAYNE
from lunar.properties import conductivity_hayne, conductivity_martinez
from lunar.diviner import load_gcp_band, gcp_band_for_latitude, select_diurnal_curve


def stats(lst_obs, T_obs, lst_mod, T_mod):
    order = np.argsort(lst_mod)
    pred = np.interp(lst_obs, lst_mod[order], T_mod[order], period=24.0)
    r = pred - T_obs
    day = (lst_obs >= 6.0) & (lst_obs < 18.0)
    return dict(rmse_K=float(np.sqrt(np.mean(r ** 2))), bias_K=float(r.mean()),
                bias_day_K=float(r[day].mean()), bias_night_K=float(r[~day].mean()), n_bins=int(len(r)))


def main():
    res = json.loads((_REPO / "results" / "joint_albedo_fit.json").read_text())
    out, curves_all = {}, {}
    for name in ("A15", "A17"):
        b = res["sites"][name]["with_diffusivity"]["best"]
        g = res["sites"][name]["with_diffusivity"]["global_test"]
        cfg = SITES[name]
        lo, hi = gcp_band_for_latitude(cfg["lat"])
        band = load_gcp_band(lo, hi, columns=(dc.CHANNEL,))
        curves = {"zonal": select_diurnal_curve(band, cfg["lat"], channel=dc.CHANNEL)}
        for hw in (0.5, 1.0):
            curves[f"site_pm{hw}deg"] = select_diurnal_curve(band, cfg["lat"], channel=dc.CHANNEL,
                                                             longitude_range=(cfg["lon"] - hw, cfg["lon"] + hw))
        cj = copy.deepcopy(cfg); cj["albedo"] = b["A"]
        cg = copy.deepcopy(cfg); cg["albedo"] = g["A_fitted"]
        kj = b["kd_star_mW"] * 1e-3
        models = {
            "hayne_joint": (cj, lambda T, z, k=kj: conductivity_hayne(T, z, Ks=HAYNE["K_S"], Kd=k, H=HAYNE["H"], chi=HAYNE["CHI"])),
            "hayne_global_fittedA": (cg, lambda T, z: conductivity_hayne(T, z, Ks=HAYNE["K_S"], Kd=3.4e-3, H=HAYNE["H"], chi=HAYNE["CHI"])),
            "martinez_forward_jointA": (cj, lambda T, z: conductivity_martinez(T, z=z)),
        }
        r, cur = {}, {}
        for m, (c, kf) in models.items():
            lst_m, T_m = dc.model_surface_cycle(c, kf)
            r[m] = {cn: stats(lo_, To_, lst_m, T_m) for cn, (lo_, To_) in curves.items()}
            cur[m] = (lst_m, T_m)
            z, s = r[m]["zonal"], r[m]["site_pm0.5deg"]
            print(f"  {name} {m:24s}: zonal bias {z['bias_K']:+.2f} (day {z['bias_day_K']:+.2f}, night {z['bias_night_K']:+.2f}) | "
                  f"site bias {s['bias_K']:+.2f} (day {s['bias_day_K']:+.2f}, night {s['bias_night_K']:+.2f}), site RMSE {s['rmse_K']:.2f}", flush=True)
        out[name] = dict(A_joint=b["A"], kd_joint_mW=b["kd_star_mW"], A_global=g["A_fitted"], channel=dc.CHANNEL, models=r)
        curves_all[name] = (curves, cur)
    p = _REPO / "results" / "joint_diviner.json"
    p.write_text(json.dumps(out, indent=1))
    print(f"wrote {p.relative_to(_REPO)}")
    # figure: midnight-centred diurnal cycle, zonal curve and site pixels
    import matplotlib.pyplot as plt
    from matplotlib.lines import Line2D
    from lunar.plotting.style import (JGR_FULL, fmt_axis, legend_below, C_CHAR, C_DIM, C_MS, C_A15, C_A17,
                                      C_HAYNE_FIT, LS_HAYNE_FIT, C_HAYNE_GLOBAL, LS_HAYNE_GLOBAL, LS_MS)
    fig = plt.figure(figsize=(JGR_FULL, 3.4))
    gs = fig.add_gridspec(1, 2, wspace=0.25, left=0.08, right=0.98, top=0.88, bottom=0.17)
    cen = lambda lst: (np.asarray(lst) - 12.0) % 24.0
    sty = {"hayne_joint": dict(color=C_HAYNE_FIT, lw=1.8, ls=LS_HAYNE_FIT),
           "hayne_global_fittedA": dict(color=C_HAYNE_GLOBAL, lw=1.4, ls=LS_HAYNE_GLOBAL),
           "martinez_forward_jointA": dict(color=C_MS, lw=1.6, ls=LS_MS)}
    for col, name in enumerate(("A15", "A17")):
        ax = fig.add_subplot(gs[0, col])
        curves, cur = curves_all[name]
        lo_, To_ = curves["zonal"]; ax.plot(cen(lo_), To_, "o", ms=2.5, color=C_DIM, alpha=0.6)
        lo_, To_ = curves["site_pm0.5deg"]; ax.plot(cen(lo_), To_, "s", ms=3.2, mfc="white",
                                                    mec=(C_A15 if name == "A15" else C_A17), mew=0.8)
        for m, (lst_m, T_m) in cur.items():
            o = np.argsort(cen(lst_m)); ax.plot(cen(lst_m)[o], np.asarray(T_m)[o], **sty[m])
        ax.set_xticks([0, 6, 12, 18, 24], ["12", "18", "0", "6", "12"])
        fmt_axis(ax, xlabel="Local time (h)", ylabel="Surface temperature (K)" if col == 0 else "",
                 title=f"({'ab'[col]})  {SITES[name]['label']}")
    h = [Line2D([], [], **sty["hayne_joint"]), Line2D([], [], **sty["hayne_global_fittedA"]), Line2D([], [], **sty["martinez_forward_jointA"]),
         Line2D([], [], marker="o", ms=3, color=C_DIM, ls="none"), Line2D([], [], marker="s", ms=4.5, mfc="white", mec=C_CHAR, ls="none")]
    l = ["Hayne, joint fit", "Hayne, global $K_d$", "Martínez & Siegler",
         "Diviner, zonal", "Diviner, site pixels"]
    legend_below(fig, h, l)
    f = _REPO.parent / "figures" / "fig_joint_diviner_closure.pdf"
    fig.savefig(f); fig.savefig(f.with_suffix(".png"), dpi=150)
    print(f"  -> {f}")


if __name__ == "__main__":
    main()
