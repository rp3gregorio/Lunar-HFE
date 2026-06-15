"""
Phase B-1: replace the analytical (K_d, Q_b) posterior surrogate with
a real `emcee` MCMC run at each Apollo site.

The likelihood is the same as the surrogate — Gaussian in the
profile-fit RMSE — so the science answer should match. The benefit is
defensibility: the posterior is now a proper Markov-chain sample with
convergence diagnostics, autocorrelation lengths, and sample-based
percentiles. The output figure is a 2-site corner plot with marginal
KDEs and joint contours.

Output:
  output/figures/fig_kd_qb_posterior.pdf
  output/bayesian_crosscheck_samples.json (posterior summary statistics)

Runtime: ~30 s with 32 walkers × 4000 steps × 2 sites (likelihood is
analytical via the cached RMSE-vs-K_d spline from kd_retrieval_results.json).
"""
from __future__ import annotations
import json, sys, pathlib, time
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

import emcee
import corner

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "scripts"))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "scripts" / "figures"))
from lunar.plotting.style import (   # type: ignore
    JGR_FULL,
    FS_TITLE, FS_LABEL, FS_TICK, FS_LEGEND,
    C_HAYNE, C_MS, C_A15, C_A17, C_CHAR, C_DIM, C_GRID, C_CORAL,
    fmt_axis,
)

PHASE_A = pathlib.Path(__file__).resolve().parents[2] / "output/kd_retrieval_results.json"
OUT_FIG = pathlib.Path(__file__).resolve().parents[2] / "output/figures/fig_kd_qb_posterior.pdf"
OUT_JSON = pathlib.Path(__file__).resolve().parents[2] / "output/bayesian_crosscheck_samples.json"

# ── Site parameters ──────────────────────────────────────────────────────────
from lunar.config import SITES  # single source of truth


def make_log_posterior(site, kd_grid_spline, qb_pub,
                        qb_prior_mean, qb_prior_sigma,
                        N_obs, sigma_data=0.5,
                        kd_lim=(1e-3, 30e-3),
                        qb_lim=(2e-3, 40e-3)):
    """Closure returning log P(K_d, Q_b | data) under:
    - degeneracy-aware likelihood: deep profile is invariant under
      (K_d, Q_b) -> (alpha K_d, alpha Q_b). The RMSE at any (K_d, Q_b)
      equals the RMSE at K_eff = K_d * (Q_b_pub / Q_b) under the
      published Q_b, so we evaluate the spline at K_eff.
    - Gaussian prior on Q_b from the Saito/Nagihara reanalysis;
      flat prior on K_d within [1, 30] mW/m/K."""
    log_kd_lo, log_kd_hi = np.log(kd_lim[0]), np.log(kd_lim[1])
    log_qb_lo, log_qb_hi = np.log(qb_lim[0]), np.log(qb_lim[1])

    def log_post(theta):
        log_kd, log_qb = theta
        if not (log_kd_lo <= log_kd <= log_kd_hi):  return -np.inf
        if not (log_qb_lo <= log_qb <= log_qb_hi):  return -np.inf
        kd = np.exp(log_kd)
        qb = np.exp(log_qb)
        kd_eff = kd * (qb_pub / qb)
        rmse = float(kd_grid_spline(kd_eff))
        if not np.isfinite(rmse):  return -np.inf
        # likelihood
        log_L = -0.5 * N_obs * (rmse / sigma_data) ** 2
        # Gaussian prior on Q_b
        log_pr = -0.5 * ((qb - qb_prior_mean) / qb_prior_sigma) ** 2
        # Jacobian for log-uniform prior on K_d (flat in log space →
        # log-prior on K_d is a constant inside bounds)
        return log_L + log_pr

    return log_post


def run_mcmc(name, site, kd_grid, rmse_curve, n_obs):
    from scipy.interpolate import CubicSpline
    spline = CubicSpline(kd_grid, rmse_curve, extrapolate=True)
    log_post = make_log_posterior(
        name, spline, site["qb_published"],
        site["qb_prior_mean"], site["qb_prior_sigma"], n_obs)

    n_walkers = 32
    n_dim     = 2
    n_steps   = 4000
    n_burn    = 1000

    rng = np.random.default_rng(seed=42 if name == "A15" else 17)
    init_kd = rng.uniform(np.log(2e-3), np.log(15e-3), n_walkers)
    init_qb = rng.normal(np.log(site["qb_prior_mean"]),
                          0.15, n_walkers)
    p0 = np.column_stack([init_kd, init_qb])

    print(f"  [{name}] running emcee: {n_walkers} walkers × {n_steps} steps ...",
          flush=True)
    sampler = emcee.EnsembleSampler(n_walkers, n_dim, log_post)
    sampler.run_mcmc(p0, n_steps, progress=False)

    chain = sampler.get_chain(discard=n_burn, flat=True)
    samples_kd = np.exp(chain[:, 0]) * 1e3   # mW/m/K
    samples_qb = np.exp(chain[:, 1]) * 1e3   # mW/m^2

    # autocorrelation
    try:
        tau = sampler.get_autocorr_time(tol=20, quiet=True)
        eff_n = (n_steps - n_burn) * n_walkers / max(tau)
    except emcee.autocorr.AutocorrError:
        tau = [np.nan, np.nan]
        eff_n = float("nan")

    summary = dict(
        n_walkers=n_walkers, n_steps=n_steps, n_burn=n_burn,
        autocorr_tau=[float(t) for t in tau],
        effective_n=float(eff_n),
        kd_q16=float(np.percentile(samples_kd, 16)),
        kd_q50=float(np.percentile(samples_kd, 50)),
        kd_q84=float(np.percentile(samples_kd, 84)),
        kd_q025=float(np.percentile(samples_kd, 2.5)),
        kd_q975=float(np.percentile(samples_kd, 97.5)),
        qb_q16=float(np.percentile(samples_qb, 16)),
        qb_q50=float(np.percentile(samples_qb, 50)),
        qb_q84=float(np.percentile(samples_qb, 84)),
    )
    print(f"  [{name}] K_d posterior: median = {summary['kd_q50']:.2f} "
          f"(16/84 = {summary['kd_q16']:.2f}/{summary['kd_q84']:.2f}, "
          f"95% = {summary['kd_q025']:.2f}–{summary['kd_q975']:.2f})",
          flush=True)
    print(f"  [{name}] Q_b posterior: median = {summary['qb_q50']:.2f} "
          f"(16/84 = {summary['qb_q16']:.2f}/{summary['qb_q84']:.2f}) "
          f"mW/m^2",
          flush=True)
    return samples_kd, samples_qb, summary


def main():
    if not PHASE_A.exists():
        sys.exit(f"need {PHASE_A}")
    d = json.loads(PHASE_A.read_text())

    print("Phase B-1: emcee MCMC for the joint (K_d, Q_b) posterior",
          flush=True)

    samples = {}
    summary_all = {}
    for name in ("A15", "A17"):
        sk = d[name]
        kd_grid = np.array(sk["kd_grid"])
        rmse    = np.array(sk["rmse_curve"])
        N_obs   = 7 if name == "A15" else 16
        s_kd, s_qb, smry = run_mcmc(name, SITES[name], kd_grid, rmse, N_obs)
        samples[name] = (s_kd, s_qb)
        summary_all[name] = smry

    # ── Figure: 2-site corner panels stacked ─────────────────────────────────
    fig = plt.figure(figsize=(JGR_FULL, 9.0))
    gs  = fig.add_gridspec(2, 2, height_ratios=[1.0, 1.0],
                           width_ratios=[1.0, 1.0],
                           hspace=0.50, wspace=0.32,
                           left=0.10, right=0.95, top=0.95, bottom=0.13)

    panel_labels = [("(a)", "(c)"), ("(b)", "(d)")]
    for col, (name, _ignore) in enumerate([("A15", "(a)"), ("A17", "(b)")]):
        s_kd, s_qb = samples[name]
        col_site   = SITES[name]["colour"]

        # 2-D posterior with marginals — small inline corner plot
        ax_main = fig.add_subplot(gs[0, col])
        ax_kd   = fig.add_subplot(gs[1, col])

        # 2-D scatter + contour
        H, xed, yed = np.histogram2d(s_kd, s_qb, bins=60)
        H = H.T
        # smoothed histogram
        from scipy.ndimage import gaussian_filter
        H_smooth = gaussian_filter(H, sigma=1.5)
        ax_main.contourf(xed[:-1] + 0.5*(xed[1]-xed[0]),
                         yed[:-1] + 0.5*(yed[1]-yed[0]),
                         H_smooth, levels=18, cmap="rocket_r"
                         if False else "Reds", alpha=0.85)
        # 1- and 2-sigma contours
        levels = [0.05, 0.32, 0.68] * np.array([H_smooth.max()])
        ax_main.contour(xed[:-1] + 0.5*(xed[1]-xed[0]),
                         yed[:-1] + 0.5*(yed[1]-yed[0]),
                         H_smooth, levels=[H_smooth.max()*x for x in (0.05, 0.32, 0.68)],
                         colors="white", linewidths=0.8)

        # MAP marker (median)
        med_kd = np.median(s_kd)
        med_qb = np.median(s_qb)
        ax_main.plot(med_kd, med_qb, "*", markersize=15, color=C_CORAL,
                     mec="white", mew=1.3, zorder=5)

        # iso-ratio rays (Q_b/K_d = const → equilibrium gradient)
        kd_line = np.linspace(*ax_main.get_xlim(), 100)
        for grad in [1.0, 2.0, 3.0]:
            ax_main.plot(kd_line, grad * kd_line, ls=":", lw=0.7,
                         color="0.4", alpha=0.6)

        joint_lbl, marg_lbl = panel_labels[col]
        fmt_axis(ax_main,
                 xlabel=r"$K_d$  (mW m$^{-1}$ K$^{-1}$)",
                 ylabel=r"$Q_b$  (mW m$^{-2}$)",
                 title=f"{joint_lbl}  Apollo {name[1:]}  —  joint posterior")

        # marginal K_d (with KDE)
        ax_kd.hist(s_kd, bins=60, density=True, color=col_site,
                   alpha=0.55, edgecolor=col_site, lw=0.4)
        # 16/50/84 percentile lines
        for q, ls in [(16, ":"), (50, "-"), (84, ":")]:
            v = np.percentile(s_kd, q)
            ax_kd.axvline(v, color=C_CHAR, lw=1.0, ls=ls, alpha=0.85)
        # Stats in the title text (above the axes) so they NEVER overlap
        # the histogram, regardless of where the distribution has support.
        q16, q84 = np.percentile(s_kd, 16), np.percentile(s_kd, 84)
        q025, q975 = np.percentile(s_kd, 2.5), np.percentile(s_kd, 97.5)
        title_main = f"{marg_lbl}  Apollo {name[1:]} — marginal $P(K_d)$"
        title_sub = (f"median {med_kd:.2f},  68\\% [{q16:.2f}, {q84:.2f}],  "
                     f"95\\% [{q025:.2f}, {q975:.2f}]")
        fmt_axis(ax_kd,
                 xlabel=r"$K_d$  (mW m$^{-1}$ K$^{-1}$)",
                 ylabel=r"$P(K_d \mid \mathrm{data})$",
                 title="")
        ax_kd.set_title(title_main, pad=18)
        ax_kd.text(0.5, 1.005, title_sub, transform=ax_kd.transAxes,
                   ha="center", va="bottom", fontsize=FS_TICK,
                   color=C_DIM)

    # ── shared legend BELOW ──────────────────────────────────────────────────
    from matplotlib.lines import Line2D
    handles = [
        Line2D([0],[0], marker="*", color="none", markerfacecolor=C_CORAL,
               mec="white", markersize=14, label="posterior median"),
        Line2D([0],[0], color="white", lw=1.5,
               label=r"posterior 1-, 2-, 3-$\sigma$ contours"),
        Line2D([0],[0], ls=":", color="0.4",
               label=r"iso-ratio rays  $Q_b/K_d = \mathrm{const}$"),
        Line2D([0],[0], color=C_CHAR, lw=1.0, ls="-",
               label="median  (marginal)"),
        Line2D([0],[0], color=C_CHAR, lw=1.0, ls=":",
               label="16/84 percentiles  (marginal)"),
    ]
    fig.legend(handles=handles, loc="lower center",
               bbox_to_anchor=(0.5, 0.01), ncols=3, frameon=True,
               edgecolor=C_GRID, framealpha=0.97, fontsize=FS_LEGEND,
               handlelength=2.0, borderpad=0.6, columnspacing=1.6,
               title=r"emcee MCMC  ($N_{\rm walkers}=32$, $N_{\rm steps}=4000$, burn-in 1000; Saito $Q_b$ prior)",
               title_fontsize=FS_LABEL)

    fig.savefig(OUT_FIG)
    plt.close(fig)
    print(f"\nSaved: {OUT_FIG}", flush=True)

    # ── Companion figure: clean two-site comparison + contrast posterior ────
    summary_all['contrast'] = make_comparison_figure(samples, summary_all)

    OUT_JSON.write_text(json.dumps(summary_all, indent=2))
    print(f"Saved: {OUT_JSON}", flush=True)


# ═════════════════════════════════════════════════════════════════════════════
#  Two-site posterior comparison (overlay + contrast distribution)
# ═════════════════════════════════════════════════════════════════════════════
def make_comparison_figure(samples, summary):
    """Two-panel side-by-side comparison.

    (a) Both sites' marginal P(K_d) overlaid as filled KDE curves with
        66% (16-84) shaded ranges and median lines.  Annotation gives
        the posterior probability that A17 > A15.
    (b) Posterior of the contrast K_d^{A17} − K_d^{A15}, computed by
        sampling from each marginal independently (the two sites' data
        are independent, so the joint factors).  Median, 66%, 95%
        ranges shaded; vertical line at zero for reference.
    """
    from scipy.stats import gaussian_kde

    fig = plt.figure(figsize=(JGR_FULL, 4.4))
    gs = fig.add_gridspec(1, 2, wspace=0.26,
                          left=0.08, right=0.98, top=0.88, bottom=0.28)
    axA = fig.add_subplot(gs[0])
    axB = fig.add_subplot(gs[1])

    s15_kd, _ = samples["A15"]
    s17_kd, _ = samples["A17"]

    # ── Panel (a): two-site overlay ─────────────────────────────────────────
    x_grid = np.linspace(0, max(s17_kd.max(), s15_kd.max()) * 1.05, 600)
    kde15 = gaussian_kde(s15_kd, bw_method=0.25)(x_grid)
    kde17 = gaussian_kde(s17_kd, bw_method=0.25)(x_grid)

    # Normalise each KDE to its own maximum so both peaks are visible
    # on a shared axis; the annotated P(A17>A15) is computed from the
    # raw samples, so the comparison is still quantitatively correct.
    for s, kde, color, label in [
        (s15_kd, kde15 / kde15.max(), C_A15, "Apollo 15"),
        (s17_kd, kde17 / kde17.max(), C_A17, "Apollo 17"),
    ]:
        axA.fill_between(x_grid, 0, kde, color=color, alpha=0.28,
                         linewidth=0)
        axA.plot(x_grid, kde, color=color, lw=1.7, label=label)
        med = np.median(s)
        q16, q84 = np.percentile(s, [16, 84])
        axA.axvline(med, color=color, ls="-", lw=1.2, alpha=0.85)
        # 66% range as a thin shaded band just below zero
        axA.plot([q16, q84], [-0.04, -0.04], color=color, lw=4,
                 solid_capstyle="butt", alpha=0.85)

    # P(A17 > A15) by Monte-Carlo on the marginals (same length, paired
    # samples — they were drawn from the same chain length so the
    # ordering is arbitrary but the marginal probability is well-defined)
    n = min(len(s15_kd), len(s17_kd))
    rng = np.random.default_rng(0)
    idx15 = rng.choice(len(s15_kd), size=n, replace=False)
    idx17 = rng.choice(len(s17_kd), size=n, replace=False)
    p_gt = float(np.mean(s17_kd[idx17] > s15_kd[idx15]))

    fmt_axis(axA,
             xlabel=r"$K_d$  (mW m$^{-1}$ K$^{-1}$)",
             ylabel=r"posterior density (normalised)",
             title="(a)  Two-site posterior overlay")
    axA.set_ylim(-0.10, 1.18)

    # ── Panel (b): contrast posterior ───────────────────────────────────────
    contrast = s17_kd[idx17] - s15_kd[idx15]
    med_c = float(np.median(contrast))
    q16_c, q84_c = np.percentile(contrast, [16, 84])
    q025_c, q975_c = np.percentile(contrast, [2.5, 97.5])

    bins = np.linspace(contrast.min(), contrast.max(), 70)
    axB.hist(contrast, bins=bins, density=True, color=C_CORAL,
             alpha=0.55, edgecolor=C_CORAL, lw=0.4)
    # 66% and 95% shaded slabs (no in-axes legend — moved below)
    axB.axvspan(q025_c, q975_c, color=C_CORAL, alpha=0.12)
    axB.axvspan(q16_c, q84_c, color=C_CORAL, alpha=0.22)
    axB.axvline(med_c, color=C_CHAR, lw=1.5)
    axB.axvline(0.0, color=C_DIM, ls="--", lw=1.2)
    fmt_axis(axB,
             xlabel=r"$K_d^{\rm A17} - K_d^{\rm A15}$  (mW m$^{-1}$ K$^{-1}$)",
             ylabel=r"$P(\Delta K_d \mid \mathrm{data})$",
             title="(b)  Posterior of the inter-site contrast")
    # No subtitle on the axes — the contrast stats are folded into the
    # shared legend title below the figure (cleaner layout).
    contrast_stats = (
        rf"$P(K_d^{{\rm A17}} > K_d^{{\rm A15}}) = {p_gt*100:.1f}\%$   |   "
        rf"$\Delta K_d$ posterior:  "
        rf"median ${med_c:+.2f}$,  "
        rf"68% [${q16_c:+.2f}, {q84_c:+.2f}$],  "
        rf"95% [${q025_c:+.2f}, {q975_c:+.2f}$]  "
        rf"(mW m$^{{-1}}$ K$^{{-1}}$)"
    )

    fig.suptitle("emcee MCMC posteriors — direct comparison of the two sites",
                 fontsize=FS_TITLE, color=C_CHAR, y=0.98)

    # Shared legend BELOW the figure (in its own box).  The contrast
    # stats that previously sat above panel (b) are folded into the
    # legend title here, so all stats live in one block.
    from matplotlib.lines import Line2D
    from matplotlib.patches import Patch
    handles = [
        Line2D([0],[0], color=C_A15, lw=2.0, label="Apollo 15  (panel a)"),
        Line2D([0],[0], color=C_A17, lw=2.0, label="Apollo 17  (panel a)"),
        Patch(facecolor=C_CORAL, alpha=0.22, edgecolor="none",
              label="66% credible interval  (panel b)"),
        Patch(facecolor=C_CORAL, alpha=0.12, edgecolor="none",
              label="95% credible interval  (panel b)"),
        Line2D([0],[0], color=C_CHAR, lw=1.5, label="posterior median"),
        Line2D([0],[0], color=C_DIM, ls="--", lw=1.2,
               label=r"$\Delta K_d = 0$  (null)"),
    ]
    fig.legend(handles=handles, loc="lower center",
               bbox_to_anchor=(0.5, 0.005), ncols=3, frameon=True,
               edgecolor=C_GRID, framealpha=0.97, fontsize=8.5,
               handlelength=1.6, borderpad=0.4, columnspacing=1.2,
               labelspacing=0.3,
               title=contrast_stats, title_fontsize=8.5)

    out = pathlib.Path(__file__).resolve().parents[2] / "output/figures/fig_posterior_compare.pdf"
    fig.savefig(out)
    plt.close(fig)
    print(f"Saved: {out}", flush=True)
    print(f"  contrast: P(A17>A15)={p_gt*100:.1f}%  median={med_c:+.2f}  "
          f"68% [{q16_c:+.2f},{q84_c:+.2f}]  95% [{q025_c:+.2f},{q975_c:+.2f}]", flush=True)
    return dict(p_gt=float(p_gt), median=float(med_c),
                q16=float(q16_c), q84=float(q84_c),
                q025=float(q025_c), q975=float(q975_c))


if __name__ == "__main__":
    main()
