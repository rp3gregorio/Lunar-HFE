"""Letter figures for the joint (albedo, K_d) retrieval (2026-10-05).

  fig_joint_constraints.pdf      Fig. 3: what fixes A and K_d at each site
  fig_joint_bootstrap.pdf        bootstrap distributions and the contrast (not in the paper since 2026-10-07)
  fig_joint_thermal_profiles.pdf Fig. 4: T(z) at the joint fit, the global value, Martinez
  fig_joint_robustness.pdf       Fig. S5: K_d under each changed input, grouped as in Table 3
  fig_joint_mcmc.pdf             Fig. 6: MCMC posterior: K_d, Q_b, K_d vs rho_d (compute_joint_mcmc.py)
  fig_joint_annual_wave.pdf      Fig. 5: the annual wave in the full record vs the forward model (compute_annual_wave.py)
  fig_joint_mean_T_profile.pdf   (not in the paper) the two global models at the config (fitted) albedos
  fig_joint_alpha_sweep.pdf      (not in the paper) Martinez density sweep (reads results/headline_rmse.json)
  fig_joint_intro_column.pdf     Fig. 1: the modeled column (swing depth from review_diagnostics.json)
  fig_joint_anchor_method.pdf    Fig. S2: the flux-anchored solver, Apollo 15 at the joint fit (~3 min)
  fig_joint_apollo_timeline_probes.pdf  Fig. 2: stability-window timeline (site colours)
  fig_joint_amplitude_vs_depth.pdf      Fig. S3: diurnal amplitude vs depth

Figs. 1, 2, S2, S3 and the two figures not in the paper reuse the make_intro_column / make_apollo_timeline_letter /
make_anchor_method_figure / make_letter_figures / make_alpha_sweep_figure generators
under new names, so the older-named copies
used by other documents (thesis, v1.1 letter) are kept.

Reads results/joint_albedo_fit.json (+ _cache.npz), joint_fit_checks.json,
joint_fit_sensitivities.json, joint_valley.json, headline_rmse.json.
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
from matplotlib.legend_handler import HandlerTuple
from matplotlib.patches import Patch
from lunar.plotting.style import *          # noqa: F401,F403 (rcParams + palette)
import compute_joint_albedo_fit as jf

FIG = _REPO.parent / "figures"
RES = _REPO / "results"
SITE_COL = {"A15": C_A15, "A17": C_A17}
SITE_LAB = {"A15": "Apollo 15", "A17": "Apollo 17"}
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


def fine_map(J, A, K, nA=241, nK=801):
    """Cubic resampling of a (nA, nK) map along both axes, for smooth contours and profiles."""
    from scipy.interpolate import CubicSpline
    Af, J1 = fine_along_A(J, A, nA)
    Kf = np.linspace(K[0], K[-1], nK)
    return Af, Kf, CubicSpline(K, J1, axis=1)(Kf)


def refined_profile(J, A):
    """Profile over K_d: the minimum over A at each K_d, refined by a parabola in A."""
    return np.array([jf.vertex(A, J[:, k], int(np.argmin(J[:, k])))[1] for k in range(J.shape[1])])


def fig_constraints(res, cache):
    """Fig. 3: (a, b) the (A, K_d) plane with the three measurements and the fits;
    (c, d) the misfit along K_d (profile: best albedo at each K_d)."""
    A, K = jf.A_GRID, jf.KD_GRID * 1e3
    KLIM = (1.0, 17.0)                     # one K_d range in all four panels
    valley = json.loads((RES / "joint_valley.json").read_text())   # temperatures only at the fitted A
    fig = plt.figure(figsize=(JGR_FULL, 6.2))
    gs = fig.add_gridspec(2, 2, height_ratios=[1.2, 0.85], hspace=0.42, wspace=0.25,
                          left=0.08, right=0.955, top=0.95, bottom=0.09)
    top = []
    for col, s in enumerate(("A15", "A17")):
        ax = fig.add_subplot(gs[0, col]); top.append(ax)
        J2 = np.array(res["sites"][s]["temperature_only"]["J_map"]); J3 = np.array(res["sites"][s]["with_diffusivity"]["J_map"])
        Ts = cache[f"{s}_Ts"]; kap = cache[f"{s}_kap"]
        kobs = np.array([p[2] for p in jf.KAPPA_OBS[s]]); ksig = np.array([p[3] for p in jf.KAPPA_OBS[s]])
        Jk = (((kap - kobs) / ksig) ** 2).sum(axis=-1)
        Af, Kf, J2f = fine_map(J2, A, K)
        _, _, J3f = fine_map(J3, A, K)
        AA, KK = np.meshgrid(A, K, indexing="ij")
        AF, KF = np.meshgrid(Af, Kf, indexing="ij")
        d2 = J2f - J2f.min()
        # sensor temperatures alone (ochre), the diffusivity (blue), the surface mean (grey dashed)
        ax.contourf(AF, KF, d2, levels=[0, 1, 4, 9, 25, 100], colors=["#F1E6CC", "#F5EDDB", "#F9F3E8", "#FBF8F1", "#FDFBF8"], extend="neither")
        ax.contour(AF, KF, d2, levels=[1, 4, 9], colors=[C_OBS_T], linewidths=0.6, alpha=0.8)
        ax.contour(AA, KK, Ts - jf.TS_OBS[s], levels=[-5, 5], colors=[C_OBS_TS], linewidths=1.0, linestyles="--")
        ax.contourf(AA, KK, Jk - Jk.min(), levels=[0, 1], colors=[C_OBS_KAPPA], alpha=0.25)
        ax.contour(AA, KK, Jk - Jk.min(), levels=[1], colors=[C_OBS_KAPPA], linewidths=0.9)
        ax.axhline(3.4, color=C_GLOBAL_REF, ls=LS_GLOBAL_REF, lw=1.4, zorder=3)
        # the fits: joint (star, 68% region), temperatures only (open circle), and the
        # temperatures only at the fitted albedo (cross), joined to the star at the same A
        ax.contour(AF, KF, J3f - J3f.min(), levels=[2.30], colors=[C_CHAR], linewidths=1.3)
        b3 = res["sites"][s]["with_diffusivity"]["best"]; b2 = res["sites"][s]["temperature_only"]["best"]
        v = valley[s]
        ax.plot([v["A"], v["A"]], [b3["kd_star_mW"], v["kd_temperatures_only_mW"]], color=C_DIM, lw=0.8, ls=(0, (1, 1.5)), zorder=5)
        ax.plot(v["A"], v["kd_temperatures_only_mW"], marker="X", ms=8, color=C_DIM, mec="white", mew=0.6, zorder=6, ls="none")
        ax.plot(b2["A"], b2["kd_star_mW"], marker="o", ms=7, mfc="white", mec=C_CHAR, mew=1.2, zorder=6, ls="none")
        ax.plot(b3["A"], b3["kd_star_mW"], marker="*", ms=14, color=SITE_COL[s], mec="white", mew=0.8, zorder=7, ls="none")
        ax.set_xlim(A[0], A[-1]); ax.set_ylim(*KLIM)
        fmt_axis(ax, xlabel="Effective albedo $A$", ylabel=r"$K_d$ (mW m$^{-1}$ K$^{-1}$)" if col == 0 else "",
                 title=f"({'ab'[col]})  {SITE_LAB[s]}")
        # (c, d): misfit along K_d, the albedo re-optimized at each K_d
        ax = fig.add_subplot(gs[1, col])
        # profile = lowest misfit over the albedo at each K_d, on the smooth map
        curves = {}
        for v_, Jf, ls, lw in (("temperature_only", J2f, "--", 1.4), ("with_diffusivity", J3f, "-", 1.9)):
            pr = Jf.min(axis=0)
            if v_ == "temperature_only":
                # the A17 temperature-only valley is narrower than the albedo grid step, which
                # leaves a < 0.5 ripple in the profile; smooth it for display (sigma 0.3 mW)
                from scipy.ndimage import gaussian_filter1d
                pr = gaussian_filter1d(pr, 0.3 / (Kf[1] - Kf[0]), mode="nearest")
            pr = pr - pr.min()
            ax.plot(Kf, pr, ls=ls, color=SITE_COL[s], lw=lw)
            curves[v_] = pr
        for L, lab in ((1.0, "68%"), (3.84, "95%")):
            ax.axhline(L, color=C_DIM, lw=0.7, ls=(0, (2, 2)), zorder=1)
            ax.text(1.012, L, lab, transform=ax.get_yaxis_transform(), fontsize=8, color=C_DIM,
                    ha="left", va="center", clip_on=False)
        ax.axvline(3.4, color=C_GLOBAL_REF, ls=LS_GLOBAL_REF, lw=1.4)
        ax.set_xlim(*KLIM); ax.set_ylim(0, 30)
        fmt_axis(ax, xlabel=r"$K_d$ (mW m$^{-1}$ K$^{-1}$)", ylabel=r"$\Delta J$ (misfit above best)" if col == 0 else "",
                 title=f"({'cd'[col]})  {SITE_LAB[s]}: misfit along $K_d$")
    handles = [Line2D([], [], color=C_OBS_TS, ls="--", lw=1.0),
               Patch(fc=C_OBS_KAPPA, alpha=0.3, ec=C_OBS_KAPPA),
               (Patch(fc="#F1E6CC", ec=C_OBS_T), Line2D([], [], marker="o", ms=6, mfc="white", mec=C_CHAR, ls="none")),
               (Line2D([], [], color=C_CHAR, lw=1.3), Line2D([], [], marker="*", ms=11, color=C_CHAR, ls="none", mec="white")),
               Line2D([], [], marker="X", ms=8, color=C_DIM, ls="none", mec="white"),
               Line2D([], [], color=C_GLOBAL_REF, ls=LS_GLOBAL_REF, lw=1.4)]
    labels = ["surface mean $\\pm$5 K", "diffusivity ($\\Delta J_\\kappa\\leq1$)",
              "temperatures only ($\\Delta J$ = 1, 4, 9; best fit)", "joint fit (68% region)",
              "temperatures only, fitted $A$", "global $K_d$ = 3.4"]
    legend_between(fig, top, handles, labels)
    # (c, d): one entry per curve type, each drawn in both site colours
    pair = lambda ls, lw: (Line2D([], [], color=C_A15, ls=ls, lw=lw), Line2D([], [], color=C_A17, ls=ls, lw=lw))
    legend_below(fig, [pair("-", 1.9), pair("--", 1.4),
                       Line2D([], [], color=C_DIM, lw=0.7, ls=(0, (2, 2))),
                       Line2D([], [], color=C_GLOBAL_REF, ls=LS_GLOBAL_REF, lw=1.4)],
                 ["with diffusivity (joint fit)", "temperatures only", r"$\Delta J$ = 1 (68%), 3.84 (95%)", "global $K_d$ = 3.4"],
                 handlelength=3.0, handler_map={tuple: HandlerTuple(ndivide=None, pad=0.4)})
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
        l.append(f"{SITE_LAB[s]}: {q['p50']:.2f} [{q['p2.5']:.2f}, {q['p97.5']:.2f}]")
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
    h += [(Patch(fc=C_NEUTRAL, alpha=0.4), Line2D([], [], color=C_CONTRAST, lw=1.6))]
    l += [f"contrast: {cc['median']:+.2f} [{cc['p2_5']:+.2f}, {cc['p97_5']:+.2f}]"]
    fmt_axis(ax2, xlabel=r"$\Delta K_d^{*}$ (A17 $-$ A15)", ylabel="bootstrap count", title="(b)  Inter-site contrast")
    legend_below(fig, h, l)
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
        # meter-scale band: A15 sensors end at 139 cm, so its panel stops at 175 cm
        band = (75, 175) if s == "A15" else (75, 245)
        for row, (zlo, zhi) in enumerate(((0, 300), band)):
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
    labels = ["Hayne, joint fit", "Hayne, global $K_d$ (own $A$)", "Martínez & Siegler",
              "sensor, used", "sensor, borestem zone", "borestem zone"]
    legend_below(fig, handles, labels)
    out = FIG / "fig_joint_thermal_profiles.pdf"
    fig.savefig(out); fig.savefig(out.with_suffix(".png"), dpi=150); plt.close(fig)
    print(f"  -> {out}")


def fig_robustness(res, sens):
    """K_d* refitted under each changed input, grouped as in Table 3 of the letter.
    (Until 2026-10-07 a panel (a) mapped the A17 - A15 difference over the basal-flux
    pairs; it was dropped with the site-difference claim. The map stays in
    joint_fit_sensitivities.json as qb_contrast_map.)"""
    chi_path = RES / "joint_chi_density.json"          # radiative factor and site densities (compute_joint_chi_density.py)
    chid = json.loads(chi_path.read_text()) if chi_path.exists() else None
    # (label, key prefix); key None = group heading. chi = 1.5 is excluded (no physical albedo fits; Text S12)
    rows = [("Measured inputs", None),
            ("basal flux $Q_b$, site range", "Qb"),
            ("density $\\rho_d$ 1700–2000 kg m$^{-3}$", "rho_d"),
            ("measured core densities", "rho_site"),
            ("heat capacity $c_p$ $\\pm$3%", "cp_x"),
            ("surface conductivity $K_s$ $\\pm$30%", "Ks"),
            ("Methodological choices", None),
            ("borestem cut $z_b$ 70–90 cm", "zb"),
            ("window threshold", "thr"),
            ("window start", ("floor_", "fallback_")),
            ("common 1974 window", "epoch_T_common"),
            ("Conditionality", None),
            ("radiative coefficient $\\chi$ 2.2–3.2", "chi_"),
            ("compaction depth $H$ 3–10 cm", "H_"),
            ("angular albedo laws", "form")]
    if not chid:
        rows = [r for r in rows if r[1] not in ("rho_site", "chi_")]
    fig, ax = plt.subplots(figsize=(JGR_FULL, 4.4))
    fig.subplots_adjust(left=0.36, right=0.97, top=0.98, bottom=0.12)
    for s, dy in (("A15", -0.14), ("A17", 0.14)):
        b = res["sites"][s]["with_diffusivity"]
        k0 = b["best"]["kd_star_mW"]; q = b["bootstrap"]["kd_mW"]
        ax.axvspan(q["p2.5"], q["p97.5"], color=SITE_COL[s], alpha=0.10, lw=0)
        ax.axvline(k0, color=SITE_COL[s], lw=1.2)
        V = {**{k: v["with_diffusivity"]["kd_star_mW"] for k, v in sens["sites"][s]["variants"].items()},
             **{k: v["kd_star_mW"] for k, v in sens["sites"][s]["reanalysis"].items()}}
        if chid:
            V = {k: v for k, v in V.items() if not k.startswith("chi_")}
            V.update({k: v["kd_star_mW"] for k, v in chid["sites"][s].items()
                      if (k.startswith("chi_") and k != "chi_1.5") or k == "rho_site"})
        for i, (lab, key) in enumerate(rows):
            if key is None:
                continue
            vals = [v for k, v in V.items() if k.startswith(key) and k != "nominal_compact"]
            if vals:
                ax.plot([min(vals), max(vals)], [i + dy] * 2, color=SITE_COL[s], lw=2.2, solid_capstyle="round")
                ax.plot(vals, [i + dy] * len(vals), "o", ms=4, color=SITE_COL[s], mec="white", mew=0.5)
    ax.axvline(3.4, color=C_GLOBAL_REF, ls=LS_GLOBAL_REF, lw=1.4)
    ax.set_yticks([i for i, r in enumerate(rows) if r[1] is not None], [r[0] for r in rows if r[1] is not None])
    ax.set_ylim(len(rows) - 0.5, -0.6)
    ax.set_xlim(3.2, 6.9)
    fmt_axis(ax, xlabel=r"$K_d^{*}$ (mW m$^{-1}$ K$^{-1}$)")
    ax.grid(axis="y", visible=False)
    from matplotlib.transforms import blended_transform_factory
    head = blended_transform_factory(fig.transFigure, ax.transData)
    for i, (lab, key) in enumerate(rows):          # group headings: italic, flush left, with a rule above
        if key is None:
            ax.text(0.015, i, lab, transform=head, ha="left", va="center", fontstyle="italic", color=C_DIM)
            if i:
                ax.axhline(i - 0.5, color=C_GRID, lw=0.8)
    handles = [(Line2D([], [], color=C_A15, lw=2.2), Line2D([], [], ls="", marker="o", ms=4, color=C_A15, mec="white", mew=0.5)),
               (Line2D([], [], color=C_A17, lw=2.2), Line2D([], [], ls="", marker="o", ms=4, color=C_A17, mec="white", mew=0.5)),
               Line2D([], [], color=C_DIM, lw=1.2), Patch(fc=C_DIM, alpha=0.15),
               Line2D([], [], color=C_GLOBAL_REF, ls=LS_GLOBAL_REF, lw=1.4)]
    labels = ["Apollo 15", "Apollo 17", "adopted fit", "bootstrap 95% interval", "global $K_d$ = 3.4"]
    legend_below(fig, handles, labels, handler_map={tuple: HandlerTuple(ndivide=1)})
    out = FIG / "fig_joint_robustness.pdf"
    fig.savefig(out); fig.savefig(out.with_suffix(".png"), dpi=150); plt.close(fig)
    print(f"  -> {out}")


def fig_annual_wave():
    """Fig. 5: the annual wave in the full record against the forward model (compute_annual_wave.py).
    Left: chi^2 profile over K_d (all sensors: amplitude and phase; amplitude only; phase only).
    Middle and right: amplitude and phase lag against depth, data divided by the fitted probe factor,
    with the model at the annual-wave best fit, at the joint fit and at the global K_d."""
    aw = json.loads((RES / "annual_wave.json").read_text())
    prof = np.load(RES / "annual_wave_model.npz"); kds = prof["kd_scan_mW"]; o = np.argsort(kds)
    fig = plt.figure(figsize=(JGR_FULL, 5.4))
    gs = fig.add_gridspec(2, 3, width_ratios=[1.05, 1, 1], hspace=0.42, wspace=0.34, left=0.075, right=0.985, top=0.95, bottom=0.10)
    MK = {"TG": "o", "TR": "s", "TC": "^"}
    for r, s in enumerate(("A15", "A17")):
        col = SITE_COL[s]; site = aw["sites"][s]; V = site["variants"]
        ax0, ax1, ax2 = (fig.add_subplot(gs[r, c]) for c in range(3))
        # (left) chi^2 profiles, each scaled by its own error factor
        lo, hi = aw["meta"]["kd_joint_mW"][s], None
        jb = json.loads((RES / "joint_albedo_fit.json").read_text())["sites"][s]["with_diffusivity"]["bootstrap"]["kd_mW"]
        ax0.axvspan(jb["p2.5"], jb["p97.5"], color=col, alpha=0.12, lw=0)
        for v, ls in (("nominal", "-"), ("amplitude_only", "--"), ("phase_only", ":")):
            c2 = prof[f"{s}_chi2_{v}"][o]; sc = V[v]["error_scale"] ** 2
            ax0.plot(kds[o], (c2 - c2.min()) / sc, ls=ls, color=col, lw=1.6)
        ax0.axhline(3.84, color=C_DIM, lw=0.8, ls="-", alpha=0.6)
        ax0.axvline(3.4, color=C_TEAL, ls=":", lw=1.4)
        ax0.set_xlim(2.5, 9.0); ax0.set_ylim(0, 40)
        fmt_axis(ax0, xlabel=r"$K_d$ (mW m$^{-1}$ K$^{-1}$)", ylabel=r"$\Delta\chi^2$",
                 title=f"({'ad'[r]})  {SITE_LAB[s]}: fit over $K_d$")
        # (middle, right) data in the model frame of the best fit
        cv = site["curves"]; z = np.array(cv["z_m"])
        gbest = {p: complex(*f) for p, f in cv["annual_wave"]["factor"].items()}
        ref = np.unwrap(np.angle(np.array([complex(*ab) for ab in cv["annual_wave"]["ab"]])))
        for name, ls, cc in (("annual_wave", "-", col), ("joint", "-.", col), ("global", ":", C_TEAL)):
            m = np.array([complex(*ab) for ab in cv[name]["ab"]]) * (complex(*cv[name]["factor"]["p1"]) / gbest["p1"])
            ph = np.unwrap(np.angle(m)); ph += 2 * np.pi * np.round((ref[0] - ph[0]) / (2 * np.pi))
            ax1.plot(np.abs(m), z * 100, ls=ls, color=cc, lw=1.5)
            ax2.plot(np.degrees(ph - ref[0]), z * 100, ls=ls, color=cc, lw=1.5)
        for key, d in site["sensors"].items():
            p, sname = key.split("_"); g = gbest[p]
            ob = complex(*d["obs_ab"]) / g; C = np.array(d["obs_cov"]) / abs(g) ** 2
            A = abs(ob); sA = float(np.sqrt(np.array([ob.real, ob.imag]) @ C @ np.array([ob.real, ob.imag]))) / A
            sph = float(np.sqrt(np.array([-ob.imag, ob.real]) @ C @ np.array([-ob.imag, ob.real]))) / A ** 2
            if A < 3 * sA:          # below 3 sigma: amplitude only (open), no phase
                ax1.errorbar(A, d["z_m"] * 100, xerr=min(sA, 0.9 * A), marker=MK[sname[:2]], ms=4.5, mfc="white",
                             mec=col, color=col, ls="none", elinewidth=0.7, alpha=0.8)
                continue
            zi = np.interp(d["z_m"], z, ref); ph = np.angle(ob); ph += 2 * np.pi * np.round((zi - ph) / (2 * np.pi))
            ax1.errorbar(A, d["z_m"] * 100, xerr=sA, marker=MK[sname[:2]], ms=5, color=col, mec="white", mew=0.7, ls="none", elinewidth=0.9)
            ax2.errorbar(np.degrees(ph - ref[0]), d["z_m"] * 100, xerr=np.degrees(sph), marker=MK[sname[:2]], ms=5,
                         color=col, mec="white", mew=0.7, ls="none", elinewidth=0.9)
        ax1.set_xscale("log"); ax1.set_xlim(3e-4, 3.0)
        for ax in (ax1, ax2):
            ax.set_ylim(245, 0)
        fmt_axis(ax1, xlabel="annual amplitude (model scale, K)", ylabel="Depth (cm)", title=f"({'be'[r]})  Amplitude")
        fmt_axis(ax2, xlabel="phase lag (deg)", title=f"({'cf'[r]})  Phase lag")
    handles = [Line2D([], [], color=C_DIM, lw=1.6), Line2D([], [], color=C_DIM, lw=1.6, ls="--"),
               Line2D([], [], color=C_DIM, lw=1.6, ls=":"), Line2D([], [], color=C_DIM, lw=1.5, ls="-."),
               Line2D([], [], color=C_TEAL, ls=":", lw=1.4), Patch(fc=C_DIM, alpha=0.15),
               Line2D([], [], marker="o", color=C_DIM, ls="none"), Line2D([], [], marker="s", color=C_DIM, ls="none"),
               Line2D([], [], marker="^", color=C_DIM, ls="none"), Line2D([], [], marker="o", mfc="white", mec=C_DIM, ls="none")]
    labels = ["annual wave, amplitude and phase", "amplitude only (a, d)", "phase only (a, d)",
              "model at the joint fit", "global $K_d$ = 3.4", "joint-fit 95% interval (a, d)",
              "gradient bridge", "ring bridge", "thermocouple", "below 3$\\sigma$ (amplitude only)"]
    legend_below(fig, handles, labels)
    out = FIG / "fig_joint_annual_wave.pdf"
    fig.savefig(out); fig.savefig(out.with_suffix(".png"), dpi=150); plt.close(fig)
    print(f"  -> {out}")


def fig_mcmc(res):
    """MCMC posterior of the joint retrieval (compute_joint_mcmc.py), with A, K_d, Q_b and
    rho_d sampled at each site: (a) K_d, (b) the contrast, (c) Q_b against its prior,
    (d) K_d against rho_d. The joint fit and its bootstrap 95% interval are overlaid in (a, b)."""
    from scipy.ndimage import gaussian_filter
    from matplotlib.transforms import blended_transform_factory as blend
    mc = json.loads((RES / "joint_mcmc.json").read_text())
    ch = np.load(RES / "joint_mcmc_chains.npz")
    grid = mc["meta"]["grid"]
    fig = plt.figure(figsize=(JGR_FULL, 5.6))
    gs = fig.add_gridspec(2, 2, hspace=0.45, wspace=0.26, left=0.08, right=0.98, top=0.95, bottom=0.09)
    ax1, ax2, ax3, ax4 = (fig.add_subplot(gs[i, j]) for i in range(2) for j in range(2))
    boot_bar = dict(lw=1.6, solid_capstyle="butt")
    h1, l1 = [], []
    for k, s in enumerate(("A15", "A17")):
        c = ch[s]; col = SITE_COL[s]; q = mc[s]["posterior"]["kd_mW"]
        # (a) K_d posterior; above it, the joint fit (star) and its bootstrap 95 % interval
        ax1.hist(c[:, 3], bins=np.arange(3.0, 8.51, 0.1), density=True, color=col, alpha=0.75, ec="white", lw=0.3)
        bs = res["sites"][s]["with_diffusivity"]["bootstrap"]["kd_mW"]; best = res["sites"][s]["with_diffusivity"]["best"]["kd_star_mW"]
        tr = blend(ax1.transData, ax1.transAxes); y = 0.95 - 0.07 * k
        ax1.plot([bs["p2.5"], bs["p97.5"]], [y, y], color=col, transform=tr, **boot_bar)
        ax1.plot(best, y, marker="*", ms=10, color=col, mec="white", mew=0.6, transform=tr, ls="none", zorder=5)
        h1.append(Patch(fc=col, alpha=0.75)); l1.append(f"{SITE_LAB[s]}: {q['p50']:.2f} [{q['p2.5']:.2f}, {q['p97.5']:.2f}]")
        # (c) Q_b posterior and its Gaussian prior
        q0, qs = mc[s]["prior"]["Qb_mW"]
        ax3.hist(c[:, 1], bins=np.arange(3.0, 31.01, 0.5), density=True, color=col, alpha=0.75, ec="white", lw=0.3)
        x = np.linspace(3, 31, 400)
        ax3.plot(x, np.exp(-0.5 * ((x - q0) / qs) ** 2) / (qs * np.sqrt(2 * np.pi)), color=col, ls="--", lw=1.3)
        # (d) K_d vs rho_d: 68 / 95 % regions
        H, xe, ye = np.histogram2d(c[:, 2], c[:, 3], bins=60, range=[[1450, 2350], [3.0, 8.5]])
        H = gaussian_filter(H, 1.2).T
        f = np.sort(H.ravel())[::-1]; cdf = np.cumsum(f) / f.sum()
        lv = [f[np.searchsorted(cdf, qq)] for qq in (0.95, 0.68)]
        xc, yc = 0.5 * (xe[1:] + xe[:-1]), 0.5 * (ye[1:] + ye[:-1])
        ax4.contourf(xc, yc, H, levels=[lv[0], lv[1], H.max() * 1.01], colors=[col, col], alpha=0.25)
        ax4.contour(xc, yc, H, levels=lv, colors=[col], linewidths=[0.8, 1.3])
    ax1.axvline(3.4, color=C_TEAL, ls=":", lw=1.4)
    h1.append(Line2D([], [], color=C_TEAL, ls=":", lw=1.4)); l1.append("global $K_d$ = 3.4")
    ax1.set_xlim(3.0, 8.0); ax1.set_ylim(0, ax1.get_ylim()[1] * 1.3)
    fmt_axis(ax1, xlabel=r"$K_d$ (mW m$^{-1}$ K$^{-1}$)", ylabel="posterior density", title="(a)  Per-site $K_d$")
    # (b) contrast from independent draws of the two posteriors (as in compute_joint_mcmc.py)
    rng = np.random.default_rng([42, 9])
    m = min(len(ch["A15"]), len(ch["A17"]))
    dc = ch["A17"][rng.permutation(len(ch["A17"]))[:m], 3] - ch["A15"][rng.permutation(len(ch["A15"]))[:m], 3]
    cq = mc["contrast_mW"]; cb = res["contrast"]["with_diffusivity"]
    ax2.axvspan(cq["p2.5"], cq["p97.5"], color=C_NEUTRAL, alpha=0.25, lw=0)
    ax2.hist(dc, bins=np.arange(-1.5, 3.51, 0.1), density=True, color=C_DIM, alpha=0.8, ec="white", lw=0.3)
    ax2.axvline(0, color=C_CHAR, lw=0.9, ls="--")
    ax2.axvline(cq["p50"], color=C_CONTRAST, lw=1.6)
    tr = blend(ax2.transData, ax2.transAxes)
    ax2.plot([cb["p2_5"], cb["p97_5"]], [0.95, 0.95], color=C_CHAR, transform=tr, **boot_bar)
    ax2.plot(cb["median"], 0.95, marker="*", ms=10, color=C_CHAR, mec="white", mew=0.6, transform=tr, ls="none", zorder=5)
    ax2.set_xlim(-1.5, 3.5); ax2.set_ylim(0, ax2.get_ylim()[1] * 1.3)
    fmt_axis(ax2, xlabel=r"$\Delta K_d$ (A17 $-$ A15)", ylabel="", title="(b)  Inter-site contrast")
    h1 += [(Patch(fc=C_NEUTRAL, alpha=0.4), Line2D([], [], color=C_CONTRAST, lw=1.6)),
           (Line2D([], [], color=C_CHAR, **boot_bar), Line2D([], [], marker="*", ms=10, color=C_CHAR, mec="white", ls="none"))]
    l1 += [f"contrast: {cq['p50']:+.2f} [{cq['p2.5']:+.2f}, {cq['p97.5']:+.2f}]".replace("-", "\u2212"),
           "joint fit, bootstrap 95%"]
    ax2.text(0.03, 0.86, f"P($\\Delta K_d\\leq0$) = {cq['p_leq0']:.3f}", transform=ax2.transAxes, ha="left", va="top",
             fontsize=FS_TICK, bbox=dict(fc="white", ec=C_GRID, pad=3), zorder=6)
    ax3.set_xlim(3, 31)
    fmt_axis(ax3, xlabel=r"$Q_b$ (mW m$^{-2}$)", ylabel="posterior density", title="(c)  Basal heat flux")
    ax4.set_xlim(1450, 2350); ax4.set_ylim(3.0, 8.5)
    fmt_axis(ax4, xlabel=r"$\rho_d$ (kg m$^{-3}$)", ylabel=r"$K_d$ (mW m$^{-1}$ K$^{-1}$)", title=r"(d)  $K_d$ and deep density")
    legend_between(fig, [ax1, ax2], h1, l1)
    legend_below(fig, [Line2D([], [], color=C_DIM, ls="--", lw=1.3),
                       (Patch(fc=C_DIM, alpha=0.25, ec=C_DIM, lw=1.3), Patch(fc=C_DIM, alpha=0.12, ec=C_DIM, lw=0.8))],
                 ["prior (site color)", "68% and 95% regions"])
    out = FIG / "fig_joint_mcmc.pdf"
    fig.savefig(out); fig.savefig(out.with_suffix(".png"), dpi=150); plt.close(fig)
    print(f"  -> {out}")


def main():
    res, cache, chk, sens = load()
    fig_constraints(res, cache)
    fig_bootstrap(res)
    fig_profiles(res, cache, chk)
    if (RES / "joint_mcmc.json").exists():
        fig_mcmc(res)
    if (RES / "annual_wave.json").exists():
        fig_annual_wave()
    if sens is not None:
        fig_robustness(res, sens)
    else:
        print("  (fig_joint_robustness waits for results/joint_fit_sensitivities.json)")
    # Fig. S2 first, while the house rcParams are in force; then the others and
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
