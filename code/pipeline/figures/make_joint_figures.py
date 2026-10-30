"""Figures of the letter and the SI that come from the joint (albedo, K_d) fit.

  fig_joint_apollo_timeline_probes.pdf  Figure 1: the record and each sensor's stability window
  fig_joint_intro_column.pdf            Figure 2: the model column, density and conductivity
  fig_joint_subsets.pdf                 Figure 3: each probe, each thermometer type and all the sensors
  fig_joint_constraints.pdf             Figure 4: what fixes A and K_d at each site
  fig_joint_amplitude_vs_depth.pdf      SI Figure S3: the daily swing against depth
  fig_joint_anchor_process.pdf          SI Figure S4: the flux-anchored solver, step by step
  fig_joint_annual_wave.pdf             SI Figure S5: the annual wave, measured and modeled
  fig_joint_mcmc.pdf                    SI Figure S6: MCMC posteriors
  fig_joint_variants.pdf                SI Figure S7: K_d from every variant

Figures 1, 2, S3 and S4 have their own generators (make_apollo_timeline_letter,
make_intro_column, make_daily_swing_figure, make_anchor_process_figure), called
from main(). SI Figures S1 and S2 come from make_context_map_figure.py and
make_probe_drawing.py.

Reads results/joint_albedo_fit.json (+ _cache.npz), joint_fit_checks.json,
joint_fit_sensitivities.json, subset_fits.json (+ _draws.npz), joint_mcmc.json,
annual_wave.json, albedo_sensitivity.json, own_diffusivity_fit.json,
joint_chi_density.json, transient_warming.json. Writes to figures/.

Run with:
    python code/pipeline/figures/make_joint_figures.py                       # every figure
    python code/pipeline/figures/make_joint_figures.py --only subsets,constraints
"""
from __future__ import annotations
import json, sys, pathlib, copy
_REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO)); sys.path.insert(0, str(_REPO / "src")); sys.path.insert(0, str(_REPO / "pipeline" / "compute"))

import numpy as np
import matplotlib
matplotlib.use("Agg")             # the same output on every platform and from the notebooks
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.legend_handler import HandlerTuple
from matplotlib.patches import Patch
from lunar.plotting.style import *          # noqa: F401,F403 (rcParams + palette)
from lunar.plotting import style as _style
W_LETTER = TEXT_W - 0.04                    # letter figures: the text width, printed at 100 %
import compute_joint_albedo_fit as jf

FIG = _REPO.parent / "figures"
RES = _REPO / "results"
SITE_COL = {"A15": C_A15, "A17": C_A17}
SITE_LIGHT = {"A15": C_FOREST_L, "A17": C_CORAL_L}     # light site tints: shaded ranges
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
    """Fig. 4 (GRL Fig. 3): (a, b) the (A, K_d) plane with the three measurements and the fits;
    (c, d) the misfit along K_d (profile: best albedo at each K_d). One legend below, three
    columns: temperatures alone (row 1), the joint fit (row 2), references (row 3)."""
    A, K = jf.A_GRID, jf.KD_GRID * 1e3
    KLIM = (1.0, 17.0)                     # one K_d range in all four panels
    valley = json.loads((RES / "joint_valley.json").read_text())   # temperatures only at the fitted A
    fig = plt.figure(figsize=(W_LETTER, 4.0))
    gs = fig.add_gridspec(2, 2, height_ratios=[1.2, 0.85], hspace=0.68, wspace=0.25,
                          left=0.10, right=0.97, top=0.955, bottom=0.11)
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
        ax.plot(v["A"], v["kd_temperatures_only_mW"], marker="X", ms=6, color=C_DIM, mec="white", mew=0.5, zorder=6, ls="none")
        ax.plot(b2["A"], b2["kd_star_mW"], marker="o", ms=5.5, mfc="white", mec=C_CHAR, mew=1.1, zorder=6, ls="none")
        # small enough that the 68% region (solid) around it stays readable
        ax.plot(b3["A"], b3["kd_star_mW"], marker="*", ms=9, color=SITE_COL[s], mec="white", mew=0.5, zorder=7, ls="none")
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
            inK = (Kf >= KLIM[0]) & (Kf <= KLIM[1])   # drawn only over the axis range, so no
            ax.plot(Kf[inK], pr[inK], ls=ls, color=SITE_COL[s], lw=lw)   # clipped part runs under the % labels
            curves[v_] = pr
        for L in (1.0, 3.84):                   # 68% and 95%, named in the legend
            ax.axhline(L, color=C_DIM, lw=0.7, ls=(0, (2, 2)), zorder=1)
        ax.axvline(3.4, color=C_GLOBAL_REF, ls=LS_GLOBAL_REF, lw=1.4)
        ax.set_xlim(*KLIM); ax.set_ylim(0, 30)
        fmt_axis(ax, xlabel=r"$K_d$ (mW m$^{-1}$ K$^{-1}$)", ylabel=r"$\Delta J$ (misfit above best)" if col == 0 else "",
                 title=f"({'cd'[col]})  {SITE_LAB[s]}: misfit along $K_d$")
    # ONE legend strip below the four panels, three columns read row by row: the
    # temperatures alone (row 1), the joint fit (row 2), the references (row 3). Each concept
    # once; where it appears in two forms the entry carries both handles (shading in a-b and
    # dashed curve in c-d; star in a-b and solid curve in c-d). The shading levels and the
    # meaning of Delta J = 1, 3.84 are in the caption, which keeps the labels short.
    star = lambda c: Line2D([], [], marker="*", ms=10, color=c, ls="none", mec="white", mew=0.5)
    pair = lambda ls, lw: (Line2D([], [], color=C_A15, ls=ls, lw=lw), Line2D([], [], color=C_A17, ls=ls, lw=lw))
    entries = [
        ((Patch(fc="#F1E6CC", ec=C_OBS_T),) + pair("--", 1.4), "temperatures alone"),
        (Line2D([], [], marker="o", ms=5.5, mfc="white", mec=C_CHAR, mew=1.1, ls="none"), "their best fit"),
        ((Line2D([], [], color=C_DIM, lw=0.8, ls=(0, (1, 1.5))),
          Line2D([], [], marker="X", ms=6, color=C_DIM, ls="none", mec="white")), "at the fitted albedo"),
        ((star(C_A15), star(C_A17)) + pair("-", 1.9), "joint fit"),
        ((Line2D([], [], color=C_CHAR, lw=1.3), Line2D([], [], color=C_CHAR, lw=1.0, ls=(0, (4, 2)))), "68%, 95% regions"),
        (Patch(fc=C_OBS_KAPPA, alpha=0.3, ec=C_OBS_KAPPA), "measured diffusivity"),
        (Line2D([], [], color=C_OBS_TS, ls="--", lw=1.0), "surface mean $\\pm$5 K"),
        (Line2D([], [], color=C_DIM, lw=0.7, ls=(0, (2, 2))), r"$\Delta J$ = 1, 3.84"),
        (Line2D([], [], color=C_GLOBAL_REF, ls=LS_GLOBAL_REF, lw=1.4), "global $K_d$ = 3.4"),
    ]
    legend_below(fig, [h for h, _ in entries], [l for _, l in entries], ncols=3, handlelength=2.6,
                 columnspacing=1.2, handler_map={tuple: HandlerTuple(ndivide=None, pad=0.25)})
    fig.canvas.draw()
    for ax in fig.axes:
        assert_no_overlap(ax)
    out = FIG / "fig_joint_constraints.pdf"
    fig.savefig(out); fig.savefig(out.with_suffix(".png"), dpi=150); plt.close(fig)
    print(f"  -> figures/{out.name}")


def fig_annual_wave():
    """SI Fig. S5: the annual wave in the full record against the forward model (compute_annual_wave.py).
    Left: chi^2 profile over K_d (all sensors: amplitude and phase; amplitude only; phase only).
    Middle and right: amplitude and phase lag against depth, data divided by the fitted probe factor,
    with the model at the annual-wave best fit, at the joint fit and at the global K_d."""
    aw = json.loads((RES / "annual_wave.json").read_text())
    prof = np.load(RES / "annual_wave_model.npz"); kds = prof["kd_scan_mW"]; o = np.argsort(kds)
    fig = plt.figure(figsize=(W_LETTER, 5.4))
    gs = fig.add_gridspec(2, 3, width_ratios=[1.05, 1, 1], hspace=0.42, wspace=0.34, left=0.075, right=0.985, top=0.95, bottom=0.10)
    MK = {"TG": "o", "TR": "s", "TC": "^"}
    lag_axes = []
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
        lag_axes.append(ax2)
    lo = min(ax.get_xlim()[0] for ax in lag_axes); hi = max(ax.get_xlim()[1] for ax in lag_axes)
    for ax in lag_axes:                       # the same phase-lag scale at both sites
        ax.set_xlim(lo, hi)
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
    print(f"  -> figures/{out.name}")


def fig_mcmc(res):
    """MCMC posterior of the joint retrieval (compute_joint_mcmc.py), with A, K_d, Q_b and
    rho_d sampled at each site: (a) K_d, (b) the contrast, (c) Q_b against its prior,
    (d) K_d against rho_d. The joint fit and its bootstrap 95% interval are overlaid in (a, b)."""
    from scipy.ndimage import gaussian_filter
    from matplotlib.transforms import blended_transform_factory as blend
    mc = json.loads((RES / "joint_mcmc.json").read_text())
    ch = np.load(RES / "joint_mcmc_chains.npz")
    fig = plt.figure(figsize=(W_LETTER, 5.6))
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
             bbox=dict(fc="white", ec=C_GRID, pad=3), zorder=6)
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
    print(f"  -> figures/{out.name}")


def half_up(v, n=1):
    """v rounded half-up to n decimals, as Table 1 of the letter prints it."""
    from decimal import Decimal, ROUND_HALF_UP
    return str(Decimal(repr(float(v))).quantize(Decimal(1).scaleb(-n), rounding=ROUND_HALF_UP))


def fig_subsets(res, cache):
    """Fig. 3: each probe, each thermometer type and all the sensors (compute_subset_fits.py).
    One panel per site and subset (columns: probe 1, probe 2, TG, TR, all sensors; rows: A15,
    A17), each showing ONLY that subset's sensors and the model at that subset's fit (solid),
    with its K_d and 95% interval and its fitted albedo A written under the panel title, and
    shaded the range of the
    model over that interval: at each depth, the central 95% of the profiles of the 1500
    bootstrap fits (A and K_d drawn together, results/subset_fits_draws.npz). Subset panels also
    show the fit to all the sensors (thin gray); the all-sensor panels add the global K_d = 3.4
    with its own fitted albedo (dashed) and Martinez & Siegler at the joint albedo (dotted).
    Probes: their own diffusivity; types and all sensors: both. A15 probe 2 (two sensors) is
    fitted with the albedo held at the all-sensor value. Each site row has its own temperature
    axis, both rows the same width, so the sensors of each site fill their panels. The numbers
    are in Table 1 of the letter."""
    import retrieve_kd as rk
    from lunar.config import SITES
    from compute_joint_fit_checks import bilinear
    sf = json.loads((RES / "subset_fits.json").read_text())["sites"]
    draws = np.load(RES / "subset_fits_draws.npz")
    mark, msz, zlo, zhi = {"TG": "o", "TR": "s"}, {"TG": 5.6, "TR": 5.1}, 70, 245
    cols = (("probe1", "Probe 1"), ("probe2", "Probe 2"), ("TG", "TG"), ("TR", "TR"), ("all", "All"))
    fig = plt.figure(figsize=(W_LETTER, 5.0))
    gs = fig.add_gridspec(2, 5, hspace=0.62, wspace=0.12, left=0.11, right=0.99, top=0.88, bottom=0.10)
    zc = jf.Z_DENSE * 100
    vis = (zc >= zlo - 2) & (zc <= zhi + 2)         # curves drawn only over the depths shown
    rng, axes = {}, {}
    for r, s in enumerate(("A15", "A17")):
        c = SITE_COL[s]; prof = cache[f"{s}_prof"]
        z_all, T_all = jf.observed(s)
        sens = sf[s]["sensors"]
        a_ = sf[s]["all"]
        T_allfit = bilinear(prof, a_["A"], a_["kd_mW"] * 1e-3)
        g = res["sites"][s]["with_diffusivity"]["global_test"]
        T_glob = bilinear(prof, g["A_fitted"], 3.4e-3)
        cfgA = copy.deepcopy(SITES[s]); cfgA["albedo"] = a_["A"]
        zm, Tm = rk.run_with(cfgA, k_model="martinez")
        vals = list(T_all) + list(T_allfit[(zc >= zlo) & (zc <= zhi)]) + list(T_glob[(zc >= zlo) & (zc <= zhi)])
        for j, (key, name) in enumerate(cols):
            ax = fig.add_subplot(gs[r, j], sharey=axes.get((r, 0)) if j else None); axes[(r, j)] = ax
            ax.axhspan(0, 80, color=C_EXCL_FILL, lw=0); ax.axhline(80, color=C_EXCL_EDGE, ls="--", lw=0.8)
            f = sf[s][key]
            if key == "all":
                # the other two models at the very back (behind the shaded range, the fit and
                # the sensors), wide enough to read
                ax.plot(T_glob[vis], zc[vis], color=C_HAYNE_GLOBAL, lw=2.2, ls=LS_HAYNE_GLOBAL, zorder=0.8)
                vm = (zm * 100 >= zlo - 2) & (zm * 100 <= zhi + 2)
                ax.plot(Tm[vm], zm[vm] * 100, color=C_MS, lw=2.2, ls=LS_MS, zorder=0.8)
            else:
                ax.plot(T_allfit[vis], zc[vis], color=C_DIM, lw=0.9, alpha=0.7, zorder=2)
            Tf = bilinear(prof, f["A"], f["kd_mW"] * 1e-3)
            ens = np.array([bilinear(prof, a, k * 1e-3) for a, k in zip(draws[f"{s}_{key}_A"], draws[f"{s}_{key}_kd_mW"])])
            band = np.percentile(ens, [2.5, 97.5], axis=0)
            ax.fill_betweenx(zc[vis], band[0][vis], band[1][vis], color=SITE_LIGHT[s], alpha=0.55, lw=0, zorder=1)
            ax.plot(Tf[vis], zc[vis], color=c, lw=1.8, zorder=3)
            vals += list(Tf[(zc >= zlo) & (zc <= zhi)])
            for sen, z, T in zip(sens, z_all * 100, T_all):
                inside = (key == "all" or (key.startswith("probe") and sen["probe"] == int(key[-1]))
                          or sen["type"] == key)
                if not inside:
                    continue
                kw = dict(mfc=c, mec=c, mew=0.8) if sen["probe"] == 1 else dict(mfc="white", mec=c, mew=1.5)
                ax.plot(T, z, marker=mark[sen["type"]], ms=msz[sen["type"]], ls="none", zorder=5, **kw)
            ax.set_ylim(zhi, zlo)
            fmt_axis(ax, xlabel="$T$ (K)" if r == 1 else "", ylabel=f"{SITE_LAB[s]}: depth (cm)" if j == 0 else "",
                     title=f"({'abcdefghij'[5 * r + j]})  {name}")
            # the panel's K_d and 95% interval and its fitted albedo, as in Table 1 of the letter, under
            # the title (outside the data, which the shaded range leaves no clear corner for)
            kb = f["kd_bootstrap_mW"]
            ax.set_title(ax.get_title(loc="left"), loc="left", pad=31)
            alb = f"$A$ = {half_up(f['A'], 3)}"
            for line, dy in ((f"{half_up(f['kd_mW'])} [{half_up(kb['p2.5'])}, {half_up(kb['p97.5'])}]", 17), (alb, 3)):
                ax.annotate(line, xy=(0, 1), xycoords="axes fraction", xytext=(0, dy), textcoords="offset points",
                            ha="left", va="bottom", color=C_CHAR, annotation_clip=False)
            if j:
                ax.tick_params(labelleft=False)
        rng[s] = (min(vals), max(vals))
    width = max(hi - lo for lo, hi in rng.values()) + 1.2        # one temperature width for both site rows,
                                                                 # with room for the markers at either end
    for (r, j), ax in axes.items():
        lo, hi = rng[("A15", "A17")[r]]
        mid = 0.5 * (lo + hi)
        ax.set_xlim(mid - width / 2, mid + width / 2)
        ax.xaxis.set_major_locator(plt.MultipleLocator(2))
    pair = lambda **kw: SITES2(lambda c: Line2D([], [], ls="none", mec=c, **{k: (c if v == "SITE" else v) for k, v in kw.items()}))
    handles = [pair(marker="o", ms=5.6, mfc="SITE", mew=0.8), pair(marker="s", ms=5.1, mfc="SITE", mew=0.8),
               pair(marker="o", ms=5.6, mfc="SITE", mew=0.8), pair(marker="o", ms=5.6, mfc="white", mew=1.5),
               SITES2(lambda c: Line2D([], [], color=c, lw=1.8)), Line2D([], [], color=C_DIM, lw=0.9, alpha=0.7),
               Line2D([], [], color=C_HAYNE_GLOBAL, lw=2.2, ls=LS_HAYNE_GLOBAL), Line2D([], [], color=C_MS, lw=2.2, ls=LS_MS),
               Patch(fc=C_EXCL_FILL, ec=C_EXCL_EDGE, ls="--")]
    labels = ["TG sensor", "TR sensor", "probe 1 (filled)", "probe 2 (open)",
              "fit to the panel's sensors", "fit to all the sensors", "global $K_d$ = 3.4 (e, j)",
              "Martinez & Siegler (e, j)", "borestem zone"]
    # probe 1 and probe 2 in one entry (filled, then open, in both site colours), so the nine
    # entries fill three rows of three
    handles[2:4] = [handles[2] + handles[3]]
    labels[2:4] = ["probe 1 filled, 2 open"]
    handles.insert(4, tuple(Patch(fc=SITE_LIGHT[x], alpha=0.55, lw=0) for x in ("A15", "A17")))
    labels.insert(4, "95% range of the fits")
    legend_below(fig, handles, labels, ncols=3, handlelength=2.6, handler_map=PAIR_MAP)
    fig.canvas.draw()
    for ax in axes.values():
        assert_no_overlap(ax)
    out = FIG / "fig_joint_subsets.pdf"
    fig.savefig(out); fig.savefig(out.with_suffix(".png"), dpi=150); plt.close(fig)
    print(f"  -> figures/{out.name}")


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
    rows.append(("Subsets of the sensors", "Each probe", sub(("probe1", "probe2"))))
    rows.append(("Subsets of the sensors", "Each thermometer type", sub(("TG", "TR"))))
    wd = {s: res["sites"][s]["with_diffusivity"] for s in S}
    rows.append(("All sensors together", "Joint fit",
                 {s: dict(best=wd[s]["best"]["kd_star_mW"], lo=wd[s]["bootstrap"]["kd_mW"]["p2.5"],
                          hi=wd[s]["bootstrap"]["kd_mW"]["p97.5"], pts=[], headline=True) for s in S}))
    rows.append(("All sensors together", "MCMC, heat flow and density free",
                 {s: dict(best=mc[s]["posterior"]["kd_mW"]["p50"], lo=mc[s]["posterior"]["kd_mW"]["p2.5"],
                          hi=mc[s]["posterior"]["kd_mW"]["p97.5"], pts=[]) for s in S}))
    rows.append(("All sensors together", "Our annual-wave diffusivities",
                 {s: rng([own[v][s]["kd_star_mW"] for v in own if v != "langseth1976"]) for s in S}))
    const = {s: {round(c["A"], 3): c["kd_star_mW"] for c in alb["cases"] if c["site"] == s and c["family"] == "constant"} for s in S}
    rows.append(("One measurement at a time", "Albedo fixed at 0.12",
                 {s: dict(best=const[s][0.12], lo=None, hi=None, pts=[]) for s in S}))
    rows.append(("One measurement at a time", "Albedo fixed, 0.08 to 0.16",
                 {s: rng([v for a, v in const[s].items() if 0.08 <= a <= 0.16]) for s in S}))
    to = {s: res["sites"][s]["temperature_only"] for s in S}
    rows.append(("One measurement at a time", "Temperatures alone",
                 {s: dict(best=to[s]["best"]["kd_star_mW"], lo=to[s]["bootstrap"]["kd_mW"]["p2.5"],
                          hi=to[s]["bootstrap"]["kd_mW"]["p97.5"], pts=[]) for s in S}))
    rows.append(("One measurement at a time", "Annual wave alone",
                 {s: dict(best=aw[s]["variants"]["nominal"]["kd_mW"], lo=aw[s]["variants"]["nominal"]["ci95"][0],
                          hi=aw[s]["variants"]["nominal"]["ci95"][1], pts=[]) for s in S}))
    rec = {s: [v["kd_star_mW"] for v in sens["sites"][s]["reanalysis"].values()]
              + [chk[s][f"drift_forward_{t}yr"]["kd_mW"] for t in (1, 2)]
              # the deployment-warming step whose modeled warming rate best matches the measured one
              + [min(tw[s]["cases"].values(), key=lambda c: abs(c["median_rate_ratio_model_over_observed"] - 1))
                 ["surface_as_measured"]["kd_mW"]] for s in S}
    rows.append(("Other checks", "Record reduction", {s: rng(rec[s]) for s in S}))
    inp = {s: [v["with_diffusivity"]["kd_star_mW"] for k, v in sens["sites"][s]["variants"].items()
               if k not in ("nominal_compact", "chi_1.5")] for s in S}
    rows.append(("Other checks", "Inputs", {s: rng(inp[s]) for s in S}))
    rows.append(("Other checks", r"$\chi$ = 2.2 to 3.2",
                 {s: rng([cd[s][f"chi_{x}"]["kd_star_mW"] for x in ("2.2", "2.45", "2.95", "3.2")] + [wd[s]["best"]["kd_star_mW"]]) for s in S}))
    rows.append(("Other checks", "Site densities",
                 {s: dict(best=cd[s]["rho_site"]["kd_star_mW"], lo=None, hi=None, pts=[]) for s in S}))
    return rows


def fig_variants(res, chk, sens):
    """SI Fig. S7, every variant: K_d at each site, best value and 95% interval or the
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
    fig, axes = plt.subplots(1, 2, figsize=(W_LETTER, 4.4), sharey=True,
                             gridspec_kw=dict(left=0.38, right=0.98, top=0.93, bottom=0.12, wspace=0.08))
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
    labels_l = ["joint fit", "best value, 95% interval", "range of the versions",
                "joint fit, 95% interval", "global $K_d$ = 3.4", "beyond the axis"]
    legend_below(fig, handles, labels_l, ncols=3, handlelength=2.2, handler_map=PAIR_MAP)
    fig.canvas.draw()
    for ax in axes:
        assert_no_overlap(ax)
    out = FIG / "fig_joint_variants.pdf"
    fig.savefig(out); fig.savefig(out.with_suffix(".png"), dpi=150); plt.close(fig)
    print(f"  -> figures/{out.name}")


FIGURE_NAMES = ("constraints", "subsets", "variants", "mcmc", "annual_wave",         # results
                "anchor_process", "timeline", "daily_swing", "intro_column")       # design and method


def main(only=None):
    """Draw every figure, or only those named in ``only`` (see FIGURE_NAMES)."""
    want = lambda name: only is None or name in only
    _style.use_document_fonts()          # every text at the letter's 11 pt
    res, cache, chk, sens = load()
    if want("constraints"):
        fig_constraints(res, cache)        # Fig. 4
    if want("subsets") and (RES / "subset_fits.json").exists():
        fig_subsets(res, cache)            # Fig. 3: each probe, each thermometer type and all the sensors
    if want("variants") and sens is not None:
        fig_variants(res, chk, sens)       # SI Fig. S7: K_d from every variant
    if want("mcmc") and (RES / "joint_mcmc.json").exists():
        fig_mcmc(res)                      # SI Fig. S6
    if want("annual_wave") and (RES / "annual_wave.json").exists():
        fig_annual_wave()                  # SI Fig. S5
    # SI Fig. S4 first, while the house rcParams are in force; then the
    # generators that set their own rcParams (fonts, legend sizes)
    import make_daily_swing_figure, make_intro_column, make_anchor_process_figure
    import make_apollo_timeline_letter
    if want("anchor_process"):
        make_anchor_process_figure.main()   # SI Fig. S4: the solver step by step (A15 at the joint fit)
    if want("timeline"):
        make_apollo_timeline_letter.main(out_name="fig_joint_apollo_timeline_probes.pdf", site_figures=False)  # Fig. 1
    if want("daily_swing"):
        make_daily_swing_figure.main()      # SI Fig. S3: the daily swing against depth
    if want("intro_column"):
        make_intro_column.main()            # Fig. 2


if __name__ == "__main__":
    # python make_joint_figures.py [--only constraints,subsets]
    only = None
    if "--only" in sys.argv:
        only = set(sys.argv[sys.argv.index("--only") + 1].split(","))
        unknown = only - set(FIGURE_NAMES)
        if unknown:
            sys.exit(f"unknown figure name(s): {', '.join(sorted(unknown))}; choose from {', '.join(FIGURE_NAMES)}")
    main(only)
