#!/usr/bin/env python3
"""Diviner GCP surface-temperature closure test (manuscript Fig. 9, Sec. 3.3).

For each Apollo site, compares the modelled diurnal skin temperature
against the Diviner Global Cumulative Product diurnal composite at the
site latitude:

  * Hayne (2017) form at the per-site retrieved K_d*
    (read from output/kd_retrieval_results.json), and
  * Martinez & Siegler (2021) K(T, rho) forward at published
    coefficients (no fitted knob).

Both models use the Table-1 site parameters (albedo, emissivity, Q_b)
and the same idealized diurnal forcing as the retrieval. The GCP is
external to the retrieval (it enters neither the bootstrap nor the
deep-sensor RMSE), so this is an out-of-sample check of the diurnal
forcing chain only.

Inputs (fetch first if missing):
    data/diviner/gcp/global_cumul_avg_cyl_20n30n_002.tab   (A15, 26.13 N)
    data/diviner/gcp/global_cumul_avg_cyl_10n20n_002.tab   (A17, 20.19 N)
    -> python scripts/fetch_diviner.py
    output/kd_retrieval_results.json
    -> python scripts/pipeline/retrieve_kd.py

Writes:
    output/diviner_closure.json
    paper/letter/figures/fig_diviner_closure.pdf

Run with:
    python scripts/pipeline/compute_diviner_closure.py
"""
from __future__ import annotations
import json, sys, pathlib

_REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO))
sys.path.insert(0, str(_REPO / "scripts" / "figures"))
sys.path.insert(0, str(_REPO / "scripts" / "pipeline"))

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from lunar.diviner import (load_gcp_band, select_diurnal_curve,
                           gcp_band_for_latitude)
from lunar.equilibrium import solve_periodic_equilibrium
from lunar.grid import make_geometric_grid
from lunar.solver import PixelInputs, solve_pixel
from lunar.properties import (conductivity_hayne, conductivity_martinez,
                              specific_heat)

from scripts.pipeline.retrieve_kd import SITES, HAYNE, S0, T_LUNAR, GRID

from lunar.plotting.style import (   # type: ignore
    C_A15, C_A17, C_HAYNE, C_MS, C_CHAR, C_DIM, C_GRID,
    FS_TICK, FS_LEGEND, FS_LABEL, fmt_axis,
)

DT_COARSE = 3600.0   # equilibrium iteration step
DT_FINE   = 600.0    # output-cycle step (smooth diurnal curve)
CHANNEL   = "tbol"   # bolometric brightness temperature


def model_surface_cycle(site_cfg, k_func):
    """Periodic skin-temperature cycle T_s(LST) for one site/model."""
    grid_ = make_geometric_grid(**GRID)
    cpf = lambda T: specific_heat(T, model="hayne")
    cos_lat = np.cos(np.deg2rad(site_cfg["lat"]))

    def forcing(dt):
        n_t = int(T_LUNAR / dt) + 1
        t = np.linspace(0.0, T_LUNAR, n_t)
        insol = S0 * cos_lat * np.maximum(0.0, np.cos(2 * np.pi * t / T_LUNAR))
        return t, insol

    t_c, insol_c = forcing(DT_COARSE)
    eq = solve_periodic_equilibrium(
        grid=grid_, t=t_c, insolation=insol_c,
        albedo=site_cfg["albedo"], emissivity=site_cfg["emissivity"],
        Q_b=site_cfg["Q_BASAL"], K_func=k_func, cp_func=cpf,
        T_guess=site_cfg["T_MEAN_EFF"])

    # Two fine-step lunations from the converged state; keep the last.
    t_f, insol_f = forcing(DT_FINE)
    out = solve_pixel(PixelInputs(
        grid=grid_, t=t_f, bc_mode="radiative",
        insolation=insol_f, albedo=site_cfg["albedo"],
        emissivity=site_cfg["emissivity"], Q_b=site_cfg["Q_BASAL"],
        T_init=eq.T_mean, n_lunations_spinup=2, spinup_tol_K=0.0,
        K_func=k_func, cp_func=cpf))
    T_s = out.T_surface
    # t = 0 is local noon (insolation peak): LST = 12 + 24 t / P (h)
    lst = (12.0 + 24.0 * t_f / T_LUNAR) % 24.0
    return lst, T_s


def gcp_curve(lat):
    lo, hi = gcp_band_for_latitude(lat)
    band = load_gcp_band(lo, hi, columns=(CHANNEL,))
    return select_diurnal_curve(band, lat, channel=CHANNEL)


def closure_stats(lst_obs, T_obs, lst_mod, T_mod):
    """Full-cycle RMSE / mean bias of model vs GCP on the GCP LST grid."""
    order = np.argsort(lst_mod)
    T_pred = np.interp(lst_obs, lst_mod[order], T_mod[order], period=24.0)
    resid = T_pred - T_obs
    return float(np.sqrt(np.mean(resid ** 2))), float(np.mean(resid))


def main():
    kd = json.loads((_REPO / "output" / "kd_retrieval_results.json").read_text())
    results = {}
    curves = {}
    for name in ("A15", "A17"):
        cfg = SITES[name]
        kd_star = float(kd[name]["kd_star"])
        print(f"=== {name} (lat {cfg['lat']:+.2f}, K_d* = {kd_star*1e3:.2f} mW/m/K) ===",
              flush=True)
        lst_obs, T_obs = gcp_curve(cfg["lat"])

        k_hayne = lambda T, z, kd_=kd_star: conductivity_hayne(
            T, z, Ks=HAYNE["K_S"], Kd=kd_, H=HAYNE["H"], chi=HAYNE["CHI"])
        k_ms = lambda T, z: conductivity_martinez(T, z=z)

        lst_h, T_h = model_surface_cycle(cfg, k_hayne)
        lst_m, T_m = model_surface_cycle(cfg, k_ms)

        rmse_h, bias_h = closure_stats(lst_obs, T_obs, lst_h, T_h)
        rmse_m, bias_m = closure_stats(lst_obs, T_obs, lst_m, T_m)
        print(f"  Hayne site-fit : RMSE = {rmse_h:6.2f} K, bias = {bias_h:+6.2f} K")
        print(f"  Martinez fwd   : RMSE = {rmse_m:6.2f} K, bias = {bias_m:+6.2f} K")

        results[name] = dict(
            lat=cfg["lat"], channel=CHANNEL, kd_star_W_m_K=kd_star,
            hayne_site_fit={"rmse_K": rmse_h, "bias_K": bias_h},
            martinez_forward={"rmse_K": rmse_m, "bias_K": bias_m},
            n_gcp_points=int(len(lst_obs)))
        curves[name] = (lst_obs, T_obs, lst_h, T_h, lst_m, T_m,
                        rmse_h, bias_h, rmse_m, bias_m)

    out_path = _REPO / "output" / "diviner_closure.json"
    out_path.write_text(json.dumps(results, indent=2))
    print(f"wrote {out_path}", flush=True)

    # ── figure: midnight-centred diurnal closure, two panels ───────────
    fig, axes = plt.subplots(1, 2, figsize=(11.5, 4.4),
                             gridspec_kw={"wspace": 0.24})
    fig.subplots_adjust(left=0.07, right=0.985, top=0.92, bottom=0.24)

    def to_centered(lst):
        """Shift LST so midnight sits at panel centre (noon at edges)."""
        return (lst - 12.0) % 24.0

    for ax, name in zip(axes, ("A15", "A17")):
        (lst_obs, T_obs, lst_h, T_h, lst_m, T_m,
         rmse_h, bias_h, rmse_m, bias_m) = curves[name]
        x_obs = to_centered(lst_obs)
        ax.plot(x_obs, T_obs, "o", color=C_DIM, markersize=2.2, alpha=0.5,
                label="Diviner GCP composite", rasterized=True, zorder=1)
        for lst, T, color, ls, lab in (
                (lst_h, T_h, C_HAYNE, "-",
                 "Hayne form at per-site $K_d^{*}$"),
                (lst_m, T_m, C_MS, "--",
                 "Martínez & Siegler (2021) forward")):
            x = to_centered(lst)
            order = np.argsort(x)
            ax.plot(x[order], T[order], ls, color=color, lw=1.8,
                    label=lab, zorder=3)
        ax.axvspan(6.0, 18.0, color="0.88", alpha=0.45, zorder=0)  # night
        ax.text(0.985, 0.97,
                f"Hayne fit: {rmse_h:.1f} K / {bias_h:+.1f} K\n"
                f"Martínez:  {rmse_m:.1f} K / {bias_m:+.1f} K",
                transform=ax.transAxes, ha="right", va="top",
                fontsize=FS_TICK,
                bbox=dict(boxstyle="round,pad=0.3", facecolor="white",
                          edgecolor=C_GRID, alpha=0.95))
        ax.set_xticks([0, 6, 12, 18, 24])
        ax.set_xticklabels(["12", "18", "0", "6", "12"])
        ax.set_xlim(0, 24)
        fmt_axis(ax, xlabel="Local solar time (h)",
                 ylabel="Surface temperature (K)" if name == "A15" else "",
                 title=f"({'ab'[name == 'A17']})  {SITES[name]['label']}")

    h, l = axes[0].get_legend_handles_labels()
    fig.legend(h, l, loc="lower center", bbox_to_anchor=(0.5, 0.0),
               ncols=3, frameon=True, edgecolor=C_GRID, framealpha=0.97,
               fontsize=FS_LEGEND, handlelength=2.0, borderpad=0.5)

    fig_path = _REPO / "paper" / "letter" / "figures" / "fig_diviner_closure.pdf"
    fig.savefig(fig_path, dpi=300)
    plt.close(fig)
    print(f"wrote {fig_path}", flush=True)


if __name__ == "__main__":
    main()
