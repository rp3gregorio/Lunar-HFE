"""The paper's figures from the joint (albedo, K_d) fit (letter and SI, v2.0-jgr numbering).

  fig_joint_intro_column.pdf            Fig. 1: the modeled column (swing depth from review_diagnostics.json)
  fig_joint_apollo_timeline_probes.pdf  Fig. 2: stability-window timeline (site colours)
  fig_joint_subsets.pdf                 Fig. 3: each probe and each thermometer type on its own
  fig_joint_sensors.pdf                 Fig. 4: the models against all the sensors
  fig_joint_constraints.pdf             Fig. 5: what fixes A and K_d at each site
  fig_joint_annual_wave.pdf             Fig. 6: the annual wave in the full record vs the forward model (compute_annual_wave.py)
  fig_joint_mcmc.pdf                    Fig. 7: MCMC posterior: K_d, Q_b, K_d vs rho_d (compute_joint_mcmc.py)
  fig_joint_variants.pdf                Fig. 8: K_d from every variant at each site
  fig_joint_amplitude_vs_depth.pdf      Fig. S3: diurnal amplitude vs depth
  fig_joint_anchor_process.pdf          Fig. S4: the flux-anchored solver step by step, Apollo 15 at the joint fit (~30 s)
  fig_joint_robustness.pdf              Fig. S5: K_d under each changed input, grouped as in Table 2

Figs. 1, 2, S3 and S4 come from the make_intro_column / make_apollo_timeline_letter /
make_letter_figures / make_anchor_process_figure generators, called here.
SI Figs. S1, S2 and S6 come from make_context_map_figure.py, make_study_overview.py
and compute_joint_diviner.py.

Reads results/joint_albedo_fit.json (+ _cache.npz), joint_fit_checks.json,
joint_fit_sensitivities.json, joint_valley.json, joint_mcmc.json, annual_wave.json,
albedo_sensitivity.json, own_diffusivity_fit.json, joint_chi_density.json,
transient_warming.json.
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
SITES2 = lambda make: (make(C_A15), make(C_A17))     # legend entry in both site colours
PAIR_MAP = {tuple: HandlerTuple(ndivide=None, pad=0.3)}
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


D2_68, D2_95, D2_997 = 2.30, 6.18, 11.83     # Delta J for 68, 95, 99.7% regions of two parameters


def fig_constraints(res, cache):
    """Fig. 5: (a, b) the (A, K_d) plane with the three measurements and the fits;
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
        # two-parameter (A, K_d) confidence regions, Delta J = 2.30, 6.18, 11.83 for 68, 95
        # and 99.7% (chi^2 with 2 dof); the same levels for the joint fit below
        ax.contourf(AF, KF, d2, levels=[0, D2_68, D2_95, D2_997, 25, 100], colors=["#F1E6CC", "#F5EDDB", "#F9F3E8", "#FBF8F1", "#FDFBF8"], extend="neither")
        ax.contour(AF, KF, d2, levels=[D2_68, D2_95, D2_997], colors=[C_OBS_T], linewidths=0.6, alpha=0.8)
        ax.contour(AA, KK, Ts - jf.TS_OBS[s], levels=[-5, 5], colors=[C_OBS_TS], linewidths=1.0, linestyles="--")
        ax.contourf(AA, KK, Jk - Jk.min(), levels=[0, 1], colors=[C_OBS_KAPPA], alpha=0.25)
        ax.contour(AA, KK, Jk - Jk.min(), levels=[1], colors=[C_OBS_KAPPA], linewidths=0.9)
        ax.axhline(3.4, color=C_GLOBAL_REF, ls=LS_GLOBAL_REF, lw=1.4, zorder=3)
        # the fits: joint (star, 68% region), temperatures only (open circle), and the
        # temperatures only at the fitted albedo (cross), joined to the star at the same A
        ax.contour(AF, KF, J3f - J3f.min(), levels=[D2_68, D2_95], colors=[C_CHAR], linewidths=[1.3, 1.0],
                   linestyles=["-", (0, (4, 2))])
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
    # one entry per marker: the stars carry the site colours, so the legend shows both
    star = lambda c: Line2D([], [], marker="*", ms=12, color=c, ls="none", mec="white", mew=0.8)
    handles = [Patch(fc="#F1E6CC", ec=C_OBS_T),
               Patch(fc=C_OBS_KAPPA, alpha=0.3, ec=C_OBS_KAPPA),
               Line2D([], [], color=C_OBS_TS, ls="--", lw=1.0),
               (star(C_A15), star(C_A17)),
               Line2D([], [], marker="o", ms=7, mfc="white", mec=C_CHAR, mew=1.2, ls="none"),
               (Line2D([], [], color=C_DIM, lw=0.8, ls=(0, (1, 1.5))),
                Line2D([], [], marker="X", ms=8, color=C_DIM, ls="none", mec="white")),
               Line2D([], [], color=C_GLOBAL_REF, ls=LS_GLOBAL_REF, lw=1.4)]
    labels = ["temperatures only (68, 95, 99.7% regions)", "measured diffusivity ($\\Delta J_\\kappa\\leq1$)",
              "surface mean = measured $\\pm$5 K", "joint fit (68% solid, 95% dashed)",
              "temperatures only: best fit", "temperatures only at the joint-fit $A$ (dotted link)",
              "global $K_d$ = 3.4"]
    # every element of (a, b) has an entry here; (c, d) have their own legend below
    legend_between(fig, top, handles, labels, handler_map={tuple: HandlerTuple(ndivide=None, pad=0.3)})
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


def fig_robustness(res, sens):
    """SI Fig. S5: K_d* refitted under each changed input, grouped as in Table 2 of the letter.
    (Until 2026-10-07 a panel (a) mapped the A17 - A15 difference over the basal-flux
    pairs; it was dropped with the site-difference claim. The map stays in
    joint_fit_sensitivities.json as qb_contrast_map.)"""
    chi_path = RES / "joint_chi_density.json"          # radiative factor and site densities (compute_joint_chi_density.py)
    chid = json.loads(chi_path.read_text()) if chi_path.exists() else None
    # (label, key prefix); key None = group heading. chi = 1.5 is excluded (no physical albedo fits; Table S14)
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
    """Fig. 6: the annual wave in the full record against the forward model (compute_annual_wave.py).
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
    handles = [SITES2(lambda c: Line2D([], [], color=c, lw=1.6)), SITES2(lambda c: Line2D([], [], color=c, lw=1.6, ls="--")),
               SITES2(lambda c: Line2D([], [], color=c, lw=1.6, ls=":")), SITES2(lambda c: Line2D([], [], color=c, lw=1.5, ls="-.")),
               Line2D([], [], color=C_TEAL, ls=":", lw=1.4), SITES2(lambda c: Patch(fc=c, alpha=0.15)),
               SITES2(lambda c: Line2D([], [], marker="o", color=c, mec="white", ls="none")),
               SITES2(lambda c: Line2D([], [], marker="s", color=c, mec="white", ls="none")),
               SITES2(lambda c: Line2D([], [], marker="^", color=c, mec="white", ls="none")),
               SITES2(lambda c: Line2D([], [], marker="o", mfc="white", mec=c, ls="none"))]
    labels = ["annual wave, amplitude and phase", "amplitude only (a, d)", "phase only (a, d)",
              "model at the joint fit", "global $K_d$ = 3.4", "joint-fit 95% interval (a, d)",
              "gradient bridge", "ring bridge", "thermocouple", "below 3$\\sigma$ (amplitude only)"]
    # long handles: each site's half must show a whole dash / dash-dot cycle, or the
    # dashed and dash-dot samples look alike (a reader would swap them)
    legend_below(fig, handles, labels, handlelength=4.6, handler_map=PAIR_MAP)
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
    legend_below(fig, [SITES2(lambda c: Line2D([], [], color=c, ls="--", lw=1.3)),
                       SITES2(lambda c: Patch(fc=c, alpha=0.25, ec=c, lw=1.1))],
                 ["prior", "68% and 95% regions"], handlelength=2.6, handler_map=PAIR_MAP)
    out = FIG / "fig_joint_mcmc.pdf"
    fig.savefig(out); fig.savefig(out.with_suffix(".png"), dpi=150); plt.close(fig)
    print(f"  -> {out}")


def fig_sensors(res, cache):
    """Fig. 4, the models against all the sensors: the meter-scale profiles at the joint fit
    (all sensors), at the global K_d with its own fitted albedo, and Martinez & Siegler.
    TG circles, TR squares; probe 1 filled, probe 2 open. Both sites on the same scale
    (depth range and temperature width), so equal slopes look equal. (Each sensor's offset
    from the joint fit is shown in Fig. 3, by probe and by thermometer type.)"""
    import retrieve_kd as rk
    from lunar.config import SITES
    from lunar.apollo_helpers import extract_sensor_stability
    from compute_joint_fit_checks import bilinear
    mark, msz, zlo, zhi = {"TG": "o", "TR": "s"}, {"TG": 6.6, "TR": 6.0}, 70, 245
    fig = plt.figure(figsize=(JGR_FULL, 3.0))
    gs = fig.add_gridspec(1, 2, wspace=0.30, left=0.10, right=0.97, top=0.90, bottom=0.16)
    prof_ax, prof_rng = {}, {}
    for col, s in enumerate(("A15", "A17")):
        b = res["sites"][s]["with_diffusivity"]["best"]; g = res["sites"][s]["with_diffusivity"]["global_test"]
        prof = cache[f"{s}_prof"]; zc = jf.Z_DENSE * 100
        Tj = bilinear(prof, b["A"], b["kd_star_mW"] * 1e-3); Tg = bilinear(prof, g["A_fitted"], 3.4e-3)
        cfgA = copy.deepcopy(SITES[s]); cfgA["albedo"] = b["A"]
        zm, Tm = rk.run_with(cfgA, k_model="martinez")
        obs = [o for o in extract_sensor_stability(SITES[s]["mission"], min_depth_cm=0)["sensors"]
               if o["depth_cm"] >= SITES[s]["MIN_DEPTH_CM"]]
        c = SITE_COL[s]
        ax = fig.add_subplot(gs[0, col]); prof_ax[s] = ax
        ax.axhspan(0, 80, color=C_EXCL_FILL, lw=0); ax.axhline(80, color=C_EXCL_EDGE, ls="--", lw=0.8)
        ax.plot(Tj, zc, color=C_HAYNE_FIT, lw=2.0, ls=LS_HAYNE_FIT)
        ax.plot(Tg, zc, color=C_HAYNE_GLOBAL, lw=1.6, ls=LS_HAYNE_GLOBAL)
        ax.plot(Tm, zm * 100, color=C_MS, lw=1.6, ls=LS_MS)
        for o in obs:
            kw = dict(mfc=c, mec=c, mew=0.8) if o["probe"] == 1 else dict(mfc="white", mec=c, mew=1.8)
            ax.plot(o["T_eq"], o["depth_cm"], marker=mark[o["stype"]], ms=msz[o["stype"]], ls="none", zorder=5, **kw)
        sel = (zc >= zlo) & (zc <= zhi)
        v = np.concatenate([Tj[sel], Tg[sel], [o["T_eq"] for o in obs]]); prof_rng[s] = (v.min(), v.max())
        ax.set_ylim(zhi, zlo)
        fmt_axis(ax, xlabel="Mean temperature (K)", ylabel="Depth (cm)" if col == 0 else "",
                 title=f"({'ab'[col]})  {SITE_LAB[s]}: all sensors")
    width = max(hi - lo for lo, hi in prof_rng.values()) + 1.2      # same temperature width at both sites
    for s, (lo, hi) in prof_rng.items():
        prof_ax[s].set_xlim(0.5 * (lo + hi) - width / 2, 0.5 * (lo + hi) + width / 2)
    pair = lambda **kw: SITES2(lambda c: Line2D([], [], ls="none", mec=c, **{k: (c if v == "SITE" else v) for k, v in kw.items()}))
    handles = [Line2D([], [], color=C_HAYNE_FIT, lw=2.0), Line2D([], [], color=C_HAYNE_GLOBAL, lw=1.6, ls=LS_HAYNE_GLOBAL),
               Line2D([], [], color=C_MS, lw=1.6, ls=LS_MS), Patch(fc=C_EXCL_FILL, ec=C_EXCL_EDGE, ls="--"),
               pair(marker="o", ms=6.6, mfc="SITE", mew=0.8), pair(marker="s", ms=6.0, mfc="SITE", mew=0.8),
               pair(marker="o", ms=6.6, mfc="SITE", mew=0.8), pair(marker="o", ms=6.6, mfc="white", mew=1.8)]
    labels = ["Hayne, joint fit (all sensors)", "Hayne, global $K_d$ (own $A$)", "Martinez & Siegler", "borestem zone",
              "TG: gradient bridge", "TR: ring bridge", "probe 1: filled", "probe 2: open"]
    legend_below(fig, handles, labels, ncols=4, handlelength=2.6, handler_map=PAIR_MAP)
    fig.canvas.draw()
    for a_ in prof_ax.values():
        assert_no_overlap(a_)
    out = FIG / "fig_joint_sensors.pdf"
    fig.savefig(out); fig.savefig(out.with_suffix(".png"), dpi=150); plt.close(fig)
    print(f"  -> {out}")


def fig_subsets(res, cache):
    """Fig. 3: K_d from each probe and each thermometer type on its own (compute_subset_fits.py).
    Top row, each probe (its sensors, the surface mean and its own diffusivity; A15 probe 2,
    with two sensors, at the all-sensor albedo); bottom row, each thermometer type (TG, TR;
    both diffusivities). (a, b, d, e) the sensors and the model at each subset's fit (solid:
    probe 1 or TG; dashed: probe 2 or TR; thin gray: all sensors); (c, f) K_d and its 95%
    bootstrap interval, against the all-sensor interval (shaded) and the global 3.4 (dotted)."""
    from compute_joint_fit_checks import bilinear
    sf = json.loads((RES / "subset_fits.json").read_text())["sites"]
    mark, msz, zlo, zhi = {"TG": "o", "TR": "s"}, {"TG": 6.0, "TR": 5.5}, 70, 245
    rows = (("probe", ("probe1", "probe2"), ("probe 1", "probe 2")), ("type", ("TG", "TR"), ("TG", "TR")))
    fig = plt.figure(figsize=(JGR_FULL, 5.3))
    gs = fig.add_gridspec(2, 3, width_ratios=[1, 1, 1.15], hspace=0.55, wspace=0.34,
                          left=0.085, right=0.985, top=0.95, bottom=0.08)
    prof_axes, rng = [], {}
    zc = jf.Z_DENSE * 100
    for r, (kind, keys, names) in enumerate(rows):
        for col, s in enumerate(("A15", "A17")):
            ax = fig.add_subplot(gs[r, col]); prof_axes.append((ax, s))
            c = SITE_COL[s]; prof = cache[f"{s}_prof"]
            ax.axhspan(0, 80, color=C_EXCL_FILL, lw=0); ax.axhline(80, color=C_EXCL_EDGE, ls="--", lw=0.8)
            a_ = sf[s]["all"]
            ax.plot(bilinear(prof, a_["A"], a_["kd_mW"] * 1e-3), zc, color=C_DIM, lw=0.9, alpha=0.7, zorder=2)
            vals = []
            for key, ls in zip(keys, ("-", "--")):
                f = sf[s][key]
                Tf = bilinear(prof, f["A"], f["kd_mW"] * 1e-3)
                ax.plot(Tf, zc, color=c, lw=1.7, ls=ls, zorder=3)
                vals += list(Tf[(zc >= zlo) & (zc <= zhi)])
            z_all, T_all = jf.observed(s)
            for sen, z, T in zip(sf[s]["sensors"], z_all * 100, T_all):
                kw = dict(mfc=c, mec=c, mew=0.8) if sen["probe"] == 1 else dict(mfc="white", mec=c, mew=1.6)
                ax.plot(T, z, marker=mark[sen["type"]], ms=msz[sen["type"]], ls="none", zorder=5, **kw)
                vals.append(T)
            rng[(r, s)] = (min(vals), max(vals))
            ax.set_ylim(zhi, zlo)
            lab = "by probe" if kind == "probe" else "by type"
            fmt_axis(ax, xlabel="Mean temperature (K)", ylabel="Depth (cm)" if col == 0 else "",
                     title=f"({'abde'[2 * r + col]})  {SITE_LAB[s]}, {lab}")
        # K_d summary
        ax = fig.add_subplot(gs[r, 2])
        ylab, y = [], 0
        for s in ("A15", "A17"):
            c = SITE_COL[s]; a_ = sf[s]["all"]["kd_bootstrap_mW"]
            ax.fill_between([a_["p2.5"], a_["p97.5"]], y - 0.45, y + 1.45, color=c, alpha=0.15, lw=0, zorder=0)
            for key, name in zip(keys, names):
                f = sf[s][key]; kb = f["kd_bootstrap_mW"]
                if kind == "probe":
                    kw = dict(marker="o", mfc=c if key == "probe1" else "white", mec=c, mew=1.4)
                else:
                    kw = dict(marker=mark[key], mfc=c, mec=c, mew=0.8)
                ax.plot([kb["p2.5"], kb["p97.5"]], [y, y], color=c, lw=1.6, zorder=2)
                ax.plot(f["kd_mW"], y, ms=6.5, ls="none", zorder=4, **kw)
                ylab.append(f"{s} {name}" + ("*" if f["albedo_fixed"] else ""))
                y += 1
            y += 0.4
        ax.axvline(3.4, color=C_GLOBAL_REF, ls=LS_GLOBAL_REF, lw=1.4, zorder=1)
        ax.set_yticks([0, 1, 2.4, 3.4]); ax.set_yticklabels(ylab)
        ax.set_ylim(3.95, -0.6); ax.set_xlim(2.5, 9.0)
        ax.tick_params(axis="y", length=0); ax.grid(axis="y", visible=False)
        fmt_axis(ax, xlabel=r"$K_d$ (mW m$^{-1}$ K$^{-1}$)", title=f"({'cf'[r]})  $K_d$ {'by probe' if kind == 'probe' else 'by type'}")
    # same temperature width at both sites in each row, so equal slopes look equal
    for r in (0, 1):
        width = max(hi - lo for (rr, s), (lo, hi) in rng.items() if rr == r) + 1.0
        for ax, s in prof_axes:
            if (r == 0 and ax in [a for a, _ in prof_axes[:2]]) or (r == 1 and ax in [a for a, _ in prof_axes[2:]]):
                lo, hi = rng[(r, s)]
                ax.set_xlim(0.5 * (lo + hi) - width / 2, 0.5 * (lo + hi) + width / 2)
    pair = lambda **kw: SITES2(lambda c: Line2D([], [], ls="none", mec=c, **{k: (c if v == "SITE" else v) for k, v in kw.items()}))
    handles = [SITES2(lambda c: Line2D([], [], color=c, lw=1.7)), SITES2(lambda c: Line2D([], [], color=c, lw=1.7, ls="--")),
               Line2D([], [], color=C_DIM, lw=0.9, alpha=0.7), SITES2(lambda c: Patch(fc=c, alpha=0.15, lw=0)),
               pair(marker="o", ms=6.0, mfc="SITE", mew=0.8), pair(marker="o", ms=6.0, mfc="white", mew=1.6),
               pair(marker="o", ms=6.0, mfc="SITE", mew=0.8), pair(marker="s", ms=5.5, mfc="SITE", mew=0.8),
               Line2D([], [], color=C_GLOBAL_REF, ls=LS_GLOBAL_REF, lw=1.4)]
    labels = ["fit to probe 1 (a, b) or TG (d, e)", "fit to probe 2 (a, b) or TR (d, e)", "fit to all sensors",
              "all-sensor 95% interval (c, f)", "probe 1 sensor (filled)", "probe 2 sensor (open)",
              "TG: gradient bridge (circle)", "TR: ring bridge (square)", "global $K_d$ = 3.4"]
    legend_below(fig, handles, labels, handlelength=4.0, handler_map=PAIR_MAP)
    fig.canvas.draw()
    for ax in fig.axes:
        if ax.get_legend() is None:
            assert_no_overlap(ax)
    out = FIG / "fig_joint_subsets.pdf"
    fig.savefig(out); fig.savefig(out.with_suffix(".png"), dpi=150); plt.close(fig)
    print(f"  -> {out}")


def variant_rows(res, chk, sens):
    """K_d (mW m^-1 K^-1) at each site from every variant, read from the results files:
    (group, label, {site: dict(best=, lo=, hi=, pts=[...])}). lo/hi: 95% interval or range."""
    R = lambda name: json.loads((RES / name).read_text())
    alb, aw, own = R("albedo_sensitivity.json"), R("annual_wave.json")["sites"], R("own_diffusivity_fit.json")["variants"]
    mc, cd, tw = R("joint_mcmc.json"), R("joint_chi_density.json")["sites"], R("transient_warming.json")["sites"]
    S = ("A15", "A17")
    def rng(pts, best=None):
        pts = [float(p) for p in pts]
        return dict(best=best, lo=min(pts), hi=max(pts), pts=pts)
    rows = []
    sf = json.loads((RES / "subset_fits.json").read_text())["sites"]
    sub = lambda keys: {s: rng([sf[s][k]["kd_mW"] for k in keys]) for s in S}
    rows.append(("Subsets of the sensors", "Each probe on its own (own diffusivity)", sub(("probe1", "probe2"))))
    rows.append(("Subsets of the sensors", "Each thermometer type on its own", sub(("TG", "TR"))))
    wd = {s: res["sites"][s]["with_diffusivity"] for s in S}
    rows.append(("All sensors together", "Joint fit: sensors, surface mean, diffusivity",
                 {s: dict(best=wd[s]["best"]["kd_star_mW"], lo=wd[s]["bootstrap"]["kd_mW"]["p2.5"],
                          hi=wd[s]["bootstrap"]["kd_mW"]["p97.5"], pts=[], headline=True) for s in S}))
    rows.append(("All sensors together", "Heat flow and density also free (MCMC)",
                 {s: dict(best=mc[s]["posterior"]["kd_mW"]["p50"], lo=mc[s]["posterior"]["kd_mW"]["p2.5"],
                          hi=mc[s]["posterior"]["kd_mW"]["p97.5"], pts=[]) for s in S}))
    rows.append(("All sensors together", "Our own annual-wave diffusivities",
                 {s: rng([own[v][s]["kd_star_mW"] for v in own if v != "langseth1976"]) for s in S}))
    const = {s: {round(c["A"], 3): c["kd_star_mW"] for c in alb["cases"] if c["site"] == s and c["family"] == "constant"} for s in S}
    rows.append(("One measurement at a time", "Sensors, albedo fixed at 0.12",
                 {s: dict(best=const[s][0.12], lo=None, hi=None, pts=[]) for s in S}))
    rows.append(("One measurement at a time", "Sensors, albedo fixed, 0.08 to 0.16",
                 {s: rng([v for a, v in const[s].items() if 0.08 <= a <= 0.16]) for s in S}))
    to = {s: res["sites"][s]["temperature_only"] for s in S}
    rows.append(("One measurement at a time", "Sensors and surface mean, albedo fitted",
                 {s: dict(best=to[s]["best"]["kd_star_mW"], lo=to[s]["bootstrap"]["kd_mW"]["p2.5"],
                          hi=to[s]["bootstrap"]["kd_mW"]["p97.5"], pts=[]) for s in S}))
    rows.append(("One measurement at a time", "Annual wave in the full record",
                 {s: dict(best=aw[s]["variants"]["nominal"]["kd_mW"], lo=aw[s]["variants"]["nominal"]["ci95"][0],
                          hi=aw[s]["variants"]["nominal"]["ci95"][1], pts=[]) for s in S}))
    rec = {s: [v["kd_star_mW"] for v in sens["sites"][s]["reanalysis"].values()]
              + [chk[s][f"drift_forward_{t}yr"]["kd_mW"] for t in (1, 2)]
              # the deployment-warming step whose modeled warming rate best matches the measured one
              + [min(tw[s]["cases"].values(), key=lambda c: abs(c["median_rate_ratio_model_over_observed"] - 1))
                 ["surface_as_measured"]["kd_mW"]] for s in S}
    rows.append(("Other checks", "Record reduction: cut, windows, epoch, warming", {s: rng(rec[s]) for s in S}))
    inp = {s: [v["with_diffusivity"]["kd_star_mW"] for k, v in sens["sites"][s]["variants"].items()
               if k not in ("nominal_compact", "chi_1.5")] for s in S}
    rows.append(("Other checks", "Inputs: heat flow, $K_s$, density, $c_p$, $H$, albedo law", {s: rng(inp[s]) for s in S}))
    rows.append(("Other checks", r"Radiative coefficient $\chi$ = 2.2 to 3.2",
                 {s: rng([cd[s][f"chi_{x}"]["kd_star_mW"] for x in ("2.2", "2.45", "2.95", "3.2")] + [wd[s]["best"]["kd_star_mW"]]) for s in S}))
    rows.append(("Other checks", "Measured site densities",
                 {s: dict(best=cd[s]["rho_site"]["kd_star_mW"], lo=None, hi=None, pts=[]) for s in S}))
    return rows


def fig_variants(res, chk, sens):
    """Fig. 8, every variant: K_d at each site, best value and 95% interval or the
    range of its versions; the joint fit's 95% interval shaded; the global 3.4 dotted."""
    rows = variant_rows(res, chk, sens)
    xmin, xmax = 1.0, 9.0
    groups = []
    for g, _, _ in rows:
        if g not in groups:
            groups.append(g)
    ypos, labels, y = [], [], 0.0                      # rows top to bottom, a blank line before each group
    head_y = {}
    for g in groups:
        head_y[g] = y; y += 1.0
        for gg, lab, _ in rows:
            if gg == g:
                ypos.append(y); labels.append(lab); y += 1.0
        y += 0.4
    fig, axes = plt.subplots(1, 2, figsize=(JGR_FULL, 4.4), sharey=True,
                             gridspec_kw=dict(left=0.36, right=0.98, top=0.93, bottom=0.12, wspace=0.08))
    for ax, s in zip(axes, ("A15", "A17")):
        c, cl = SITE_COL[s], {"A15": C_FOREST_L, "A17": C_CORAL_L}[s]
        hl = [r[2][s] for r in rows if r[2][s].get("headline")][0]
        ax.axvspan(hl["lo"], hl["hi"], color=cl, alpha=0.35, lw=0, zorder=0)
        ax.axvline(3.4, color=C_GLOBAL_REF, ls=LS_GLOBAL_REF, lw=1.4, zorder=1)
        for yy, (_, _, d) in zip(ypos, rows):
            v = d[s]; big = v.get("headline", False)
            if v["pts"]:                                # range of versions: thin bar + small dots
                ax.plot([max(v["lo"], xmin), min(v["hi"], xmax)], [yy, yy], color=c, lw=1.2, alpha=0.7, zorder=2)
                pts = [p for p in v["pts"] if xmin <= p <= xmax]
                ax.plot(pts, [yy] * len(pts), "o", ms=3.2, color=c, mec="white", mew=0.4, zorder=3)
            elif v["lo"] is not None:                   # best value with its 95% interval
                ax.plot([max(v["lo"], xmin), min(v["hi"], xmax)], [yy, yy], color=c, lw=2.2 if big else 1.6, zorder=2)
            if v["best"] is not None and xmin <= v["best"] <= xmax:
                ax.plot(v["best"], yy, "D" if big else "o", ms=8.5 if big else 6.0, color=c, mec="white", mew=0.8, zorder=4)
            for edge, hit in ((xmax, max([p for p in [v["hi"], v["best"]] if p is not None]) > xmax),
                              (xmin, min([p for p in [v["lo"], v["best"]] if p is not None]) < xmin)):
                if hit:                                 # continues beyond the axis
                    ax.plot(edge, yy, ">" if edge == xmax else "<", ms=5.5, color=c, mec=c, zorder=4, clip_on=False)
        for g in groups:
            ax.axhline(head_y[g] - 0.3, color=C_GRID, lw=0.8, zorder=0)
        ax.set_xlim(xmin, xmax)
        fmt_axis(ax, xlabel=r"$K_d$ (mW m$^{-1}$ K$^{-1}$)", title=f"({'ab'[s == 'A17']})  {SITE_LAB[s]}")
        ax.grid(axis="y", visible=False)
    ticks = ypos + [head_y[g] for g in groups]
    names = labels + groups
    axes[0].set_yticks(ticks); axes[0].set_yticklabels(names)
    for t in axes[0].get_yticklabels():
        if t.get_text() in groups:
            t.set_fontweight("bold")
        if t.get_text().startswith("Joint fit"):
            t.set_fontweight("bold")
    axes[0].set_ylim(y - 0.2, -0.8)
    axes[0].tick_params(axis="y", length=0)
    handles = [SITES2(lambda c: Line2D([], [], marker="D", ms=7.5, color=c, mec="white", ls="none")),
               SITES2(lambda c: Line2D([], [], marker="o", ms=6.0, color=c, mec="white", lw=1.6)),
               SITES2(lambda c: Line2D([], [], marker="o", ms=3.2, color=c, mec="white", lw=1.2, alpha=0.8)),
               SITES2(lambda c: Patch(fc=c, alpha=0.3, lw=0)),
               Line2D([], [], color=C_GLOBAL_REF, ls=LS_GLOBAL_REF, lw=1.4),
               SITES2(lambda c: Line2D([], [], marker=">", ms=5.5, color=c, ls="none"))]
    labels_l = ["joint fit (headline)", "best value and 95% interval", "range over its versions (dots)",
                "joint fit 95% interval", "global $K_d$ = 3.4", "continues beyond the axis"]
    legend_below(fig, handles, labels_l, ncols=3, handlelength=2.6, handler_map=PAIR_MAP)
    fig.canvas.draw()
    for ax in axes:
        assert_no_overlap(ax)
    out = FIG / "fig_joint_variants.pdf"
    fig.savefig(out); fig.savefig(out.with_suffix(".png"), dpi=150); plt.close(fig)
    print(f"  -> {out}")


def main():
    res, cache, chk, sens = load()
    fig_constraints(res, cache)
    if (RES / "subset_fits.json").exists():
        fig_subsets(res, cache)            # Fig. 3: each probe and each thermometer type on its own
    fig_sensors(res, cache)                # Fig. 4: all sensors against the models
    if sens is not None:
        fig_variants(res, chk, sens)       # Fig. 8: K_d from every variant
    if (RES / "joint_mcmc.json").exists():
        fig_mcmc(res)
    if (RES / "annual_wave.json").exists():
        fig_annual_wave()
    if sens is not None:
        fig_robustness(res, sens)
    else:
        print("  (fig_joint_robustness waits for results/joint_fit_sensitivities.json)")
    # Fig. S4 first, while the house rcParams are in force; then the others and
    # Fig. 1, whose generators set their own rcParams (fonts, legend sizes)
    import make_letter_figures, make_intro_column, make_anchor_process_figure
    import make_apollo_timeline_letter
    make_anchor_process_figure.main()   # Fig. S4: the solver step by step (A15 at the joint fit)
    make_apollo_timeline_letter.main(out_name="fig_joint_apollo_timeline_probes.pdf", site_figures=False)  # Fig. 2
    make_letter_figures.fig_amplitude_vs_depth(out_name="fig_joint_amplitude_vs_depth.pdf")   # Fig. S3
    make_intro_column.main(out_stem="fig_joint_intro_column", font="times")   # Fig. 1 (swing depth at the joint K_d*)


if __name__ == "__main__":
    main()
