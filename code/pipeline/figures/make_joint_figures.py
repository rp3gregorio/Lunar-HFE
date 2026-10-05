"""Letter figures for the joint (albedo, K_d) retrieval (2026-10-05).

  fig_joint_constraints.pdf      Fig. 3: what fixes A and K_d at each site
  fig_joint_bootstrap.pdf        Fig. 4: bootstrap distributions and the contrast
  fig_joint_thermal_profiles.pdf Fig. 5: T(z) at the joint fit, the global value, Martinez
  fig_joint_robustness.pdf       Fig. 6: Q_b contrast map and K_d under each systematic
  fig_joint_mean_T_profile.pdf   Fig. S4: the two global models at the config (fitted) albedos
  fig_joint_alpha_sweep.pdf      Fig. S5: Martinez density sweep (reads results/headline_rmse.json)
  fig_joint_intro_column.pdf     Fig. 1: the modeled column (swing depth from review_diagnostics.json)
  fig_joint_anchor_method.pdf    Fig. S2: the flux-anchored solver, Apollo 15 at the joint fit (~3 min)
  fig_joint_apollo_timeline_probes.pdf  Fig. 2: stability-window timeline (site colours)
  fig_joint_amplitude_vs_depth.pdf      Fig. S3: diurnal amplitude vs depth

Figs. 1, 2, S2-S5 reuse the make_intro_column / make_apollo_timeline_letter /
make_anchor_method_figure / make_letter_figures / make_alpha_sweep_figure generators
under new names, so the older-named copies
used by other documents (thesis, v1.1 letter) are kept.

Reads results/joint_albedo_fit.json (+ _cache.npz), joint_fit_checks.json,
joint_fit_sensitivities.json, albedo_sensitivity.json, headline_rmse.json.
Writes to the top-level figures/ folder.

Run with:
    python pipeline/figures/make_joint_figures.py
"""
from __future__ import annotations
import json, sys, pathlib, copy
_REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO)); sys.path.insert(0, str(_REPO / "src")); sys.path.insert(0, str(_REPO / "pipeline" / "compute"))

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import Patch
from lunar.plotting.style import *          # noqa: F401,F403 (rcParams + palette)
import compute_joint_albedo_fit as jf

FIG = _REPO.parent / "figures"
RES = _REPO / "results"
SITE_COL = {"A15": C_A15, "A17": C_A17}
SITE_LAB = {"A15": "Apollo 15", "A17": "Apollo 17"}
DRAFT_A = {"A15": 0.131, "A17": 0.137}   # the v1.1 fixed albedos, shown for comparison (Fig. 3 cross)


def fixed_albedo_points():
    """(A, K_d*) of the temperature-only retrieval at the v1.1 fixed albedos,
    from compute_albedo_sensitivity.py (its COMPARISON_ALBEDOS rows)."""
    cases = json.loads((RES / "albedo_sensitivity.json").read_text())["cases"]
    return {s: (A, next(c["kd_star_mW"] for c in cases if c["site"] == s and c["family"] == "constant"
                        and abs(c["A"] - A) < 1e-9)) for s, A in DRAFT_A.items()}


def load():
    res = json.loads((RES / "joint_albedo_fit.json").read_text())
    cache = np.load(RES / "joint_albedo_fit_cache.npz")
    chk = json.loads((RES / "joint_fit_checks.json").read_text())
    sp = RES / "joint_fit_sensitivities.json"
    sens = json.loads(sp.read_text()) if sp.exists() else None
    return res, cache, chk, sens


def fine_along_A(J, A, n=241):
    """Cubic resampling of a (nA, nK) map along the albedo axis, where the valley is narrow."""
    from scipy.interpolate import CubicSpline
    Af = np.linspace(A[0], A[-1], n)
    return Af, CubicSpline(A, J, axis=0)(Af)


def refined_profile(J, A):
    """Profile over K_d: the minimum over A at each K_d, refined by a parabola in A."""
    return np.array([jf.vertex(A, J[:, k], int(np.argmin(J[:, k])))[1] for k in range(J.shape[1])])


def fig_constraints(res, cache):
    A, K = jf.A_GRID, jf.KD_GRID * 1e3
    DRAFT = fixed_albedo_points()
    fig = plt.figure(figsize=(JGR_FULL, 6.0))
    gs = fig.add_gridspec(2, 2, height_ratios=[1.25, 0.85], hspace=0.42, wspace=0.28,
                          left=0.09, right=0.98, top=0.95, bottom=0.08)
    ylim = {"A15": (1.0, 16.0), "A17": (1.0, 24.0)}
    for col, s in enumerate(("A15", "A17")):
        ax = fig.add_subplot(gs[0, col])
        J2 = np.array(res["sites"][s]["temperature_only"]["J_map"]); J3 = np.array(res["sites"][s]["with_diffusivity"]["J_map"])
        Ts = cache[f"{s}_Ts"]; kap = cache[f"{s}_kap"]
        kobs = np.array([p[2] for p in jf.KAPPA_OBS[s]]); ksig = np.array([p[3] for p in jf.KAPPA_OBS[s]])
        Jk = (((kap - kobs) / ksig) ** 2).sum(axis=-1)
        Af, J2f = fine_along_A(J2, A)
        _, J3f = fine_along_A(J3, A)
        AA, KK = np.meshgrid(A, K, indexing="ij")
        AF, KF = np.meshgrid(Af, K, indexing="ij")
        d2 = J2f - J2f.min()
        ax.contourf(AF, KF, d2, levels=[0, 1, 4, 9, 25, 100], colors=["#F1E6CC", "#F5EDDB", "#F9F3E8", "#FBF8F1", "#FDFBF8"], extend="neither")
        ax.contour(AF, KF, d2, levels=[1, 4, 9], colors=[C_OBS_T], linewidths=0.6, alpha=0.8)
        tsm = jf.TS_OBS[s]
        ax.contourf(AA, KK, np.abs(Ts - tsm), levels=[0, 5], colors=[C_NEUTRAL], alpha=0.22)
        ax.contour(AA, KK, Ts - tsm, levels=[-5, 5], colors=[C_OBS_TS], linewidths=0.9, linestyles="--")
        ax.contourf(AA, KK, Jk - Jk.min(), levels=[0, 1], colors=[C_OBS_KAPPA], alpha=0.22)
        ax.contour(AA, KK, Jk - Jk.min(), levels=[1, 4], colors=[C_OBS_KAPPA], linewidths=[0.9, 0.6])
        ax.contour(AF, KF, J3f - J3f.min(), levels=[2.30], colors=[C_CHAR], linewidths=1.3)
        b3 = res["sites"][s]["with_diffusivity"]["best"]; b2 = res["sites"][s]["temperature_only"]["best"]
        ax.plot(b3["A"], b3["kd_star_mW"], marker="*", ms=13, color=SITE_COL[s], mec="white", mew=0.8, zorder=6, ls="none")
        ax.plot(b2["A"], b2["kd_star_mW"], marker="o", ms=7, mfc="white", mec=C_CHAR, mew=1.2, zorder=6, ls="none")
        ax.plot(*DRAFT[s], marker="X", ms=8, color=C_DIM, mec="white", mew=0.6, zorder=6, ls="none")
        ax.axhline(3.4, color=C_TEAL, ls=":", lw=1.4, zorder=3)
        ax.set_xlim(A[0], A[-1]); ax.set_ylim(*ylim[s])
        fmt_axis(ax, xlabel="Effective albedo $A$", ylabel=r"$K_d$ (mW m$^{-1}$ K$^{-1}$)" if col == 0 else "",
                 title=f"({'ab'[col]})  {SITE_LAB[s]}")
        ax = fig.add_subplot(gs[1, col])
        for v, ls, lab in (("temperature_only", "--", "temperatures only"), ("with_diffusivity", "-", "with diffusivity")):
            pr = refined_profile(np.array(res["sites"][s][v]["J_map"]), A); pr = pr - pr.min()
            ax.plot(K, pr, ls=ls, color=SITE_COL[s], lw=1.8 if ls == "-" else 1.4)
        for L in (1.0, 3.84):
            ax.axhline(L, color=C_DIM, lw=0.7, ls=(0, (2, 2)))
        ax.axvline(3.4, color=C_TEAL, ls=":", lw=1.4)
        ax.set_xlim(*ylim[s]); ax.set_ylim(0, 30)
        fmt_axis(ax, xlabel=r"$K_d$ (mW m$^{-1}$ K$^{-1}$)", ylabel=r"$\Delta J$ (profile)" if col == 0 else "",
                 title=f"({'cd'[col]})  {SITE_LAB[s]}: profile likelihood")
    handles = [Patch(fc=C_NEUTRAL, alpha=0.35, ec=C_OBS_TS, ls="--"), Patch(fc=C_OBS_KAPPA, alpha=0.3, ec=C_OBS_KAPPA),
               Patch(fc="#F1E6CC", ec=C_OBS_T), Line2D([], [], color=C_CHAR, lw=1.3),
               Line2D([], [], marker="*", ms=11, color=C_CHAR, ls="none", mec="white"),
               Line2D([], [], marker="o", ms=7, mfc="white", mec=C_CHAR, ls="none"),
               Line2D([], [], marker="X", ms=8, color=C_DIM, ls="none", mec="white"),
               Line2D([], [], color=C_TEAL, ls=":", lw=1.4),
               Line2D([], [], color=C_CHAR, ls="-", lw=1.8), Line2D([], [], color=C_CHAR, ls="--", lw=1.4)]
    labels = ["measured surface mean $\\pm$5 K", "measured diffusivity ($\\Delta J_\\kappa\\leq1$)",
              "temperatures only ($\\Delta J$ = 1, 4, 9)", "joint fit, 68% region", "joint best fit",
              "best fit, temperatures only", "fixed albedo 0.131 / 0.137", "global $K_d$ = 3.4",
              "(c, d) with diffusivity", "(c, d) temperatures only"]
    legend_below(fig, handles, labels, ncols=3)
    out = FIG / "fig_joint_constraints.pdf"
    fig.savefig(out); fig.savefig(out.with_suffix(".png"), dpi=150); plt.close(fig)
    print(f"  -> {out}")


def fig_bootstrap(res):
    fig = plt.figure(figsize=(JGR_FULL, 3.3))
    gs = fig.add_gridspec(1, 2, wspace=0.28, left=0.09, right=0.98, top=0.88, bottom=0.20)
    ax1, ax2 = fig.add_subplot(gs[0, 0]), fig.add_subplot(gs[0, 1])
    bins = np.arange(3.5, 7.51, 0.1)
    h, l = [], []
    for s in ("A15", "A17"):
        bs = res["sites"][s]["with_diffusivity"]["bootstrap"]
        x = np.array(bs["samples_kd_mW"]); q = bs["kd_mW"]
        ax1.hist(x, bins=bins, color=SITE_COL[s], alpha=0.75, ec="white", lw=0.4)
        h.append(Patch(fc=SITE_COL[s], alpha=0.75))
        l.append(f"{SITE_LAB[s]}  median {q['p50']:.2f} [{q['p2.5']:.2f}, {q['p97.5']:.2f}]")
    ax1.axvline(3.4, color=C_TEAL, ls=":", lw=1.4)
    h.append(Line2D([], [], color=C_TEAL, ls=":", lw=1.4)); l.append("global $K_d$ = 3.4")
    ax1.set_xlim(3.0, 7.5)
    fmt_axis(ax1, xlabel=r"$K_d^{*}$ (mW m$^{-1}$ K$^{-1}$)", ylabel="bootstrap count", title="(a)  Per-site joint retrieval")
    c = np.array(res["sites"]["A17"]["with_diffusivity"]["bootstrap"]["samples_kd_mW"]) - np.array(res["sites"]["A15"]["with_diffusivity"]["bootstrap"]["samples_kd_mW"])
    cc = res["contrast"]["with_diffusivity"]
    ax2.axvspan(cc["p2_5"], cc["p97_5"], color=C_NEUTRAL, alpha=0.25, lw=0)
    ax2.hist(c, bins=np.arange(-1.0, 3.01, 0.1), color=C_DIM, alpha=0.8, ec="white", lw=0.4)
    ax2.axvline(0, color=C_CHAR, lw=0.9, ls="--")
    ax2.axvline(cc["median"], color=C_CHAR, lw=1.6)
    ax2.text(0.03, 0.93, f"P($\\Delta K_d^*\\leq0$) = {cc['p_leq0']:.3f}", transform=ax2.transAxes, ha="left", va="top",
             fontsize=FS_TICK, bbox=dict(fc="white", ec=C_GRID, pad=3), zorder=6)
    h += [Line2D([], [], color=C_CONTRAST, lw=1.6), Patch(fc=C_NEUTRAL, alpha=0.4)]
    l += [f"contrast median {cc['median']:+.2f}", f"contrast 95% [{cc['p2_5']:+.2f}, {cc['p97_5']:+.2f}]"]
    fmt_axis(ax2, xlabel=r"$\Delta K_d^{*}$ (A17 $-$ A15)", ylabel="bootstrap count", title="(b)  Inter-site contrast")
    legend_below(fig, h, l, ncols=2)
    out = FIG / "fig_joint_bootstrap.pdf"
    fig.savefig(out); fig.savefig(out.with_suffix(".png"), dpi=150); plt.close(fig)
    print(f"  -> {out}")


def fig_profiles(res, cache, chk):
    import retrieve_kd as rk
    from lunar.config import SITES
    from lunar.apollo_helpers import extract_sensor_stability
    from compute_joint_fit_checks import bilinear
    fig = plt.figure(figsize=(JGR_FULL, 5.4))
    gs = fig.add_gridspec(2, 2, height_ratios=[0.8, 1.2], hspace=0.45, wspace=0.30, left=0.10, right=0.97, top=0.94, bottom=0.10)
    for col, s in enumerate(("A15", "A17")):
        b = res["sites"][s]["with_diffusivity"]["best"]; g = res["sites"][s]["with_diffusivity"]["global_test"]
        prof = cache[f"{s}_prof"]
        Tj = bilinear(prof, b["A"], b["kd_star_mW"] * 1e-3); Tg = bilinear(prof, g["A_fitted"], 3.4e-3)
        cfgA = copy.deepcopy(SITES[s]); cfgA["albedo"] = b["A"]
        zm, Tm = rk.run_with(cfgA, k_model="martinez")
        obs = extract_sensor_stability(SITES[s]["mission"], min_depth_cm=0)["sensors"]
        zo = np.array([o["depth_cm"] for o in obs]); To = np.array([o["T_eq"] for o in obs]); eo = np.array([o["T_std"] for o in obs])
        deep = zo >= SITES[s]["MIN_DEPTH_CM"]
        for row, (zlo, zhi) in enumerate(((0, 300), (75, 245))):
            ax = fig.add_subplot(gs[row, col])
            ax.axhspan(0, 80, color=C_EXCL_FILL, lw=0)
            ax.axhline(80, color=C_EXCL_EDGE, ls="--", lw=0.8)
            zc = jf.Z_DENSE * 100
            ax.plot(Tj, zc, color=C_HAYNE_FIT, lw=2.0, ls=LS_HAYNE_FIT)
            ax.plot(Tg, zc, color=C_HAYNE_GLOBAL, lw=1.6, ls=LS_HAYNE_GLOBAL)
            ax.plot(Tm, zm * 100, color=C_MS, lw=1.6, ls=LS_MS)
            ax.errorbar(To[deep], zo[deep], xerr=eo[deep], fmt="o", ms=5, color=SITE_COL[s], mec="white", mew=0.7, ecolor=SITE_COL[s], elinewidth=0.8, zorder=5)
            ax.errorbar(To[~deep], zo[~deep], xerr=eo[~deep], fmt="o", ms=5, mfc="white", mec=SITE_COL[s], ecolor=SITE_COL[s], elinewidth=0.8, zorder=5)
            ax.set_ylim(zhi, zlo)
            sel = (zc >= zlo) & (zc <= zhi)
            if row == 1:
                vals = np.concatenate([Tj[sel], Tg[sel], To[deep]])
                ax.set_xlim(vals.min() - 0.8, vals.max() + 0.8)
            fmt_axis(ax, xlabel="Mean temperature (K)" if row == 1 else "", ylabel="Depth (cm)" if col == 0 else "",
                     title=f"({'abcd'[2*row+col]})  {SITE_LAB[s]}" + (": meter-scale band" if row == 1 else ""))
    handles = [Line2D([], [], color=C_TEAL, lw=2.0), Line2D([], [], color=C_TEAL_L, lw=1.6, ls="--"),
               Line2D([], [], color=C_MS, lw=1.6, ls=":"),
               Line2D([], [], marker="o", color=C_CHAR, ls="none", mec="white"), Line2D([], [], marker="o", mfc="white", mec=C_CHAR, ls="none"),
               Patch(fc=C_EXCL_FILL, ec=C_EXCL_EDGE, ls="--")]
    labels = ["Hayne form, joint fit ($A$, $K_d^*$)", "Hayne form, global $K_d$ = 3.4 (its fitted $A$)",
              "Martínez & Siegler forward (joint $A$)", "HFE sensors, retained", "HFE sensors, borestem zone", "borestem zone ($z<80$ cm)"]
    legend_below(fig, handles, labels, ncols=3)
    out = FIG / "fig_joint_thermal_profiles.pdf"
    fig.savefig(out); fig.savefig(out.with_suffix(".png"), dpi=150); plt.close(fig)
    print(f"  -> {out}")


def fig_robustness(res, sens):
    fig = plt.figure(figsize=(JGR_FULL, 3.9))
    gs = fig.add_gridspec(1, 2, width_ratios=[1.0, 1.15], wspace=0.62, left=0.08, right=0.98, top=0.90, bottom=0.16)
    ax1, ax2 = fig.add_subplot(gs[0, 0]), fig.add_subplot(gs[0, 1])
    m = sens["qb_contrast_map"]
    q15, q17, C = np.array(m["qb_A15"]), np.array(m["qb_A17"]), np.array(m["contrast_mW"])
    im = ax1.imshow(C.T, origin="lower", cmap=NEUTRAL_SEQ, aspect="auto", vmin=0, vmax=max(2.0, C.max()))
    ax1.set_xticks(range(len(q15)), [f"{q:g}" for q in q15]); ax1.set_yticks(range(len(q17)), [f"{q:g}" for q in q17])
    for i in range(len(q15)):
        for j in range(len(q17)):
            ax1.text(i, j, f"{C[i, j]:+.2f}", ha="center", va="center", fontsize=8, color=C_CHAR)
    i0, j0 = list(q15).index(21.0), list(q17).index(16.0)
    ax1.add_patch(plt.Rectangle((i0 - 0.5, j0 - 0.5), 1, 1, fill=False, ec=C_CHAR, lw=1.6))
    fmt_axis(ax1, xlabel=r"$Q_b$ A15 (mW m$^{-2}$)", ylabel=r"$Q_b$ A17 (mW m$^{-2}$)", title=r"(a)  $\Delta K_d^*$ over the $Q_b$ envelope")
    ax1.grid(False)
    rows = [("$Q_b$ envelope", "Qb"), ("$K_s$ $\\pm$30%", "Ks"), ("$\\rho_d$ 1700 / 2000", "rho_d"), ("$c_p$ $\\pm$3%", "cp_x"),
            ("$z_b$ 70 / 90 cm", "zb"), ("window threshold", "thr"), ("window start / fallback", ("floor_", "fallback_")), ("common-1974 epoch", "epoch_T_common"),
            ("$H$ 3 / 10 cm", "H_"), ("angular albedo form", "form")]
    for s, dy in (("A15", -0.15), ("A17", 0.15)):
        b = res["sites"][s]["with_diffusivity"]
        k0 = b["best"]["kd_star_mW"]; q = b["bootstrap"]["kd_mW"]
        ax2.axvspan(q["p2.5"], q["p97.5"], color=SITE_COL[s], alpha=0.10, lw=0)
        ax2.axvline(k0, color=SITE_COL[s], lw=1.2)
        V = {**{k: v["with_diffusivity"]["kd_star_mW"] for k, v in sens["sites"][s]["variants"].items()},
             **{k: v["kd_star_mW"] for k, v in sens["sites"][s]["reanalysis"].items()}}
        for i, (lab, key) in enumerate(rows):
            vals = [v for k, v in V.items() if k.startswith(key) and k != "nominal_compact"]
            if vals:
                ax2.plot([min(vals), max(vals)], [i + dy] * 2, color=SITE_COL[s], lw=2.2, solid_capstyle="round")
                ax2.plot(vals, [i + dy] * len(vals), "o", ms=4, color=SITE_COL[s], mec="white", mew=0.5)
    ax2.set_yticks(range(len(rows)), [r[0] for r in rows]); ax2.invert_yaxis()
    ax2.axvline(3.4, color=C_TEAL, ls=":", lw=1.4)
    fmt_axis(ax2, xlabel=r"$K_d^{*}$ (mW m$^{-1}$ K$^{-1}$)", title="(b)  Joint $K_d^*$ under each systematic")
    handles = [Line2D([], [], color=C_A15, lw=2.2), Line2D([], [], color=C_A17, lw=2.2),
               Patch(fc=C_DIM, alpha=0.15), Line2D([], [], color=C_TEAL, ls=":", lw=1.4), Patch(fc="white", ec=C_CHAR, lw=1.6)]
    labels = ["Apollo 15", "Apollo 17", "bootstrap 95% (shaded)", "global $K_d$ = 3.4", "(a) adopted fluxes 21 / 16"]
    legend_below(fig, handles, labels, ncols=5)
    out = FIG / "fig_joint_robustness.pdf"
    fig.savefig(out); fig.savefig(out.with_suffix(".png"), dpi=150); plt.close(fig)
    print(f"  -> {out}")


def main():
    res, cache, chk, sens = load()
    fig_constraints(res, cache)
    fig_bootstrap(res)
    fig_profiles(res, cache, chk)
    if sens is not None:
        fig_robustness(res, sens)
    else:
        print("  (fig_joint_robustness waits for results/joint_fit_sensitivities.json)")
    # Fig. S2 first, while the house rcParams are in force; then S4, S5 and
    # Fig. 1, whose generators set their own rcParams (fonts, legend sizes)
    import make_letter_figures, make_alpha_sweep_figure, make_intro_column, make_anchor_method_figure
    import make_apollo_timeline_letter
    make_anchor_method_figure.main(out_name="fig_joint_anchor_method.pdf")   # Fig. S2 (A15 at the joint fit)
    make_apollo_timeline_letter.main(out_name="fig_joint_apollo_timeline_probes.pdf", site_figures=False)  # Fig. 2
    make_letter_figures.fig_amplitude_vs_depth(out_name="fig_joint_amplitude_vs_depth.pdf")   # Fig. S3
    make_letter_figures.fig_mean_T_profile(out_name="fig_joint_mean_T_profile.pdf")
    make_alpha_sweep_figure.main(out_name="fig_joint_alpha_sweep.pdf")
    make_intro_column.main(out_stem="fig_joint_intro_column", font="times")   # Fig. 1 (swing depth at the joint K_d*)


if __name__ == "__main__":
    main()
