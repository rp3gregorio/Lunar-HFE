"""
Phase-2 figure regeneration with publication-grade aesthetic
(Anthropic-aligned: warm coral, deep teal, restrained palette,
clean serif typography, generous whitespace).

Reads the numerical results from results/phase2_results.json and
regenerates the new letter/appendix figures.
"""
from __future__ import annotations
import json, pathlib
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.ticker as mtick
from matplotlib.lines import Line2D
from matplotlib.colors import LinearSegmentedColormap, TwoSlopeNorm

# ─── Style — JGR:Planets-compliant figure sizes ──────────────────────────────
# JGR:Planets column widths:  single 95 mm = 3.74 in,
#                             1.5-col 140 mm = 5.51 in,
#                             full   190 mm = 7.48 in.
# We design at FULL-width (7.48 in) and intentionally use a slightly larger
# font budget than the print size requires, so that text is readable when
# AGU's typesetter reduces the figure to the column width.
JGR_FULL    = 7.48      # in  (190 mm full-page width)
JGR_HALF    = 5.51      # in  (140 mm 1.5-column width)
JGR_SINGLE  = 3.74      # in  (95 mm single-column width)

FS_BASE   = 10.0
FS_TITLE  = 11.5
FS_LABEL  = 10.5
FS_TICK   = 9.5
FS_LEGEND = 9.5

plt.rcParams.update({
    "font.family": "serif",
    "font.serif": ["Times", "Times New Roman", "DejaVu Serif"],
    "font.size": FS_BASE,
    "axes.titlesize": FS_TITLE,
    "axes.titleweight": "bold",
    "axes.labelsize": FS_LABEL,
    "axes.linewidth": 0.9,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "axes.edgecolor": "#2A2520",
    "axes.labelcolor": "#2A2520",
    "axes.titlecolor": "#2A2520",
    "axes.titlepad": 10.0,
    "axes.titlelocation": "left",
    "xtick.labelsize": FS_TICK,
    "ytick.labelsize": FS_TICK,
    "xtick.color": "#2A2520",
    "ytick.color": "#2A2520",
    "xtick.major.size": 3.5,
    "ytick.major.size": 3.5,
    "xtick.major.width": 0.8,
    "ytick.major.width": 0.8,
    "xtick.minor.size": 2.0,
    "ytick.minor.size": 2.0,
    "legend.fontsize": FS_LEGEND,
    "legend.title_fontsize": FS_LEGEND,
    "legend.frameon": True,
    "legend.fancybox": False,
    "legend.framealpha": 0.97,
    "legend.edgecolor": "#D4CFC4",
    "legend.borderpad": 0.6,
    "legend.handletextpad": 0.7,
    "figure.facecolor": "white",
    "savefig.facecolor": "white",
    "figure.dpi": 150,
    "savefig.dpi": 300,
    "savefig.bbox": "tight",
    "savefig.pad_inches": 0.15,
    "grid.color": "#E8E5E0",
    "grid.linewidth": 0.6,
    "lines.linewidth": 2.0,
})

# Helper to place a legend OUTSIDE the data area (right of the axes).
def legend_outside(ax, *, loc="right", **kwargs):
    """loc: 'right' → outside right; 'bottom' → below x-axis."""
    if loc == "right":
        defaults = dict(bbox_to_anchor=(1.02, 1.0), loc="upper left",
                        borderaxespad=0.0, frameon=True)
    elif loc == "bottom":
        defaults = dict(bbox_to_anchor=(0.5, -0.18), loc="upper center",
                        borderaxespad=0.0, frameon=True, ncols=2)
    else:
        defaults = dict(loc=loc)
    defaults.update(kwargs)
    return ax.legend(**defaults)

# Anthropic-aligned palette (publication-friendly)
C_CORAL    = "#B85B3A"   # primary warm accent (~Anthropic coral)
C_CORAL_L  = "#E5A88A"   # light coral
C_TEAL     = "#2A6478"   # cool primary
C_TEAL_L   = "#7CA3B0"   # light teal
C_FOREST   = "#3D6E4A"   # tertiary green
C_FOREST_L = "#94B89C"   # light green
C_PLUM     = "#5A4A6A"   # quaternary muted plum
C_CHAR     = "#2A2520"   # warm charcoal text
C_DIM      = "#6E6862"   # secondary text
C_NEUTRAL  = "#A8A29A"   # neutral mid-gray
C_GRID     = "#E8E5E0"   # very pale warm gray

# Site/source-specific:
C_A15      = C_FOREST
C_A17      = C_CORAL
C_HAYNE    = C_TEAL
C_MS       = "#6C4CA6"     # violet: distinct from A17 coral (audit 2026-07-13)
C_LAB      = C_PLUM

# Custom colormap for Q_b heatmap: cool→neutral→warm
ANTH_DIVERGE = LinearSegmentedColormap.from_list(
    "anth_diverge",
    ["#2A6478", "#7CA3B0", "#F5F1EA", "#E5A88A", "#B85B3A", "#7A2F18"]
)
ANTH_SEQ = LinearSegmentedColormap.from_list(
    "anth_seq",
    ["#FAF7F2", "#E5D5C8", "#D9A07C", "#B85B3A", "#7A2F18", "#3A1A0A"]
)

# Output paths
_ROOT         = pathlib.Path(__file__).parents[2]   # Lunar-V2/
# kd_retrieval_results.json is the single authoritative results file: it is
# what the manuscript text and tables are built from (bootstrap with
# N_boot = 1500), and it now also carries the cold_trap and
# qb_sensitivity blocks. A previous version read phase2_results.json
# here, which held a *different* bootstrap run (N_boot = 2000, contrast
# CI [3.8,13.3] instead of [-3.2,16.6]) -- so the figures disagreed
# with the text. Do not point this back at phase2_results.json.
RESULTS       = _ROOT / "results" / "kd_retrieval_results.json"
LETTER_FIGS   = _ROOT / ".." / "figures"
APPENDIX_FIGS = _ROOT / ".." / "figures"  # (legacy alias; unused)


def fmt_axis(ax, *, xlabel="", ylabel="", title=""):
    if xlabel: ax.set_xlabel(xlabel)
    if ylabel: ax.set_ylabel(ylabel)
    if title:  ax.set_title(title)
    ax.grid(axis="both", color=C_GRID, lw=0.5)
    ax.set_axisbelow(True)
    for s in ax.spines.values():
        s.set_color(C_CHAR)


# ══════════════════════════════════════════════════════════════════════════════
# FIGURE 1 — Bootstrap distributions (letter)
# ══════════════════════════════════════════════════════════════════════════════
def fig_bootstrap(d, out_path):
    """JGR:Planets full-width. Two panels stacked; SINGLE shared
    legend below the figure so no in-axes legend competes with data."""
    fig = plt.figure(figsize=(JGR_FULL, 5.5))
    gs = fig.add_gridspec(2, 1, hspace=0.45,
                          left=0.10, right=0.97, top=0.94, bottom=0.22)
    ax0 = fig.add_subplot(gs[0])
    ax1 = fig.add_subplot(gs[1])

    # ── (a) per-site distributions ──────────────────────────────────────────
    boot15 = np.array(d["A15"]["bootstrap"]["samples"]) * 1e3
    boot17 = np.array(d["A17"]["bootstrap"]["samples"]) * 1e3

    # Data-driven binning: span the union of both bootstrap supports
    # (plus the global reference value) so the panel has no dead space
    # regardless of how tight the converged distributions are.
    lo_x = min(boot15.min(), 3.0) - 0.3
    hi_x = boot17.max() + 0.3
    bins = np.linspace(lo_x, hi_x, 50)
    h15, _ = np.histogram(boot15, bins=bins)
    h17, _ = np.histogram(boot17, bins=bins)
    centers = 0.5 * (bins[:-1] + bins[1:])
    width = bins[1] - bins[0]

    a15_med, a15_lo, a15_hi = np.percentile(boot15, [50, 2.5, 97.5])
    a17_med, a17_lo, a17_hi = np.percentile(boot17, [50, 2.5, 97.5])

    ax0.bar(centers, h15, width=width*0.95, color=C_A15, alpha=0.55,
            edgecolor=C_A15, lw=0.4,
            label=f"Apollo 15\n{a15_med:.2f}  [{a15_lo:.2f}, {a15_hi:.2f}]")
    ax0.bar(centers, h17, width=width*0.95, color=C_A17, alpha=0.55,
            edgecolor=C_A17, lw=0.4,
            label=f"Apollo 17\n{a17_med:.2f}  [{a17_lo:.2f}, {a17_hi:.2f}]")

    ax0.axvline(3.4, color=C_CHAR, ls="--", lw=1.1, alpha=0.6,
                label="Hayne 2017  $K_d = 3.4$")
    ymax = max(h15.max(), h17.max())

    fmt_axis(ax0,
             xlabel=r"$K_d^{*}$  (mW m$^{-1}$ K$^{-1}$)",
             ylabel="bootstrap count",
             title="(a)  Per-site bootstrap distributions")
    ax0.set_xlim(lo_x, hi_x)
    ax0.set_ylim(0, ymax * 1.10)
    ax0.xaxis.set_minor_locator(mtick.AutoMinorLocator())
    # NB: no in-axes legend — the shared legend is below the figure.

    # ── (b) inter-site contrast distribution ────────────────────────────────
    contrast = (boot17 - boot15)
    cmed, clo, chi_ = np.percentile(contrast, [50, 2.5, 97.5])

    bins2 = np.linspace(min(contrast.min(), -0.5) - 0.2,
                        contrast.max() + 0.3, 50)
    hC, _ = np.histogram(contrast, bins=bins2)
    centers2 = 0.5 * (bins2[:-1] + bins2[1:])
    width2 = bins2[1] - bins2[0]

    ax1.bar(centers2, hC, width=width2*0.95,
            color=C_A17, alpha=0.55, edgecolor=C_A17, lw=0.4,
            label="$\\Delta K_d^{*}$")
    ax1.axvspan(clo, chi_, color=C_A17, alpha=0.10, zorder=0,
                label=f"95% CI [{clo:.2f}, {chi_:.2f}]")
    ax1.axvline(0, color=C_CHAR, ls="--", lw=1.1, alpha=0.7,
                label="null (zero contrast)")
    ax1.axvline(cmed, color=C_A17, ls="-", lw=1.6,
                label=f"median {cmed:.2f}")

    p_str = "p < 10$^{-3}$" if d["contrast_bootstrap"]["p_value"] < 1e-3 \
            else f"p ≈ {d['contrast_bootstrap']['p_value']:.3g}"
    # plain p-value tag in top-right corner of the data area
    ax1.text(0.97, 0.95, p_str,
             transform=ax1.transAxes, ha="right", va="top",
             fontsize=FS_LABEL, fontweight="bold", color=C_CHAR,
             bbox=dict(boxstyle="round,pad=0.4", facecolor="white",
                       edgecolor=C_GRID, lw=0.6))

    fmt_axis(ax1,
             xlabel=r"$\Delta K_d^{*}$ (A17 − A15)  (mW m$^{-1}$ K$^{-1}$)",
             ylabel="bootstrap count",
             title="(b)  Inter-site contrast distribution")
    ax1.set_xlim(bins2[0], bins2[-1])
    ax1.xaxis.set_minor_locator(mtick.AutoMinorLocator())
    # (no in-axes legend — shared legend below)

    # ── shared legend BELOW the figure ───────────────────────────────────────
    from matplotlib.lines import Line2D
    from matplotlib.patches import Patch
    handles = [
        Patch(facecolor=C_A15, alpha=0.55, edgecolor=C_A15,
              label=f"Apollo 15  median {a15_med:.2f}  [{a15_lo:.2f}, {a15_hi:.2f}]"),
        Patch(facecolor=C_A17, alpha=0.55, edgecolor=C_A17,
              label=f"Apollo 17  median {a17_med:.2f}  [{a17_lo:.2f}, {a17_hi:.2f}]"),
        Line2D([0], [0], ls="--", color=C_CHAR,
               label=r"Hayne 2017  $K_d = 3.4$"),
        Line2D([0], [0], color=C_A17, lw=1.6,
               label=f"contrast median  {cmed:.2f}"),
        Patch(facecolor=C_A17, alpha=0.10,
              label=f"contrast 95% CI  [{clo:.2f}, {chi_:.2f}]"),
    ]
    fig.legend(handles=handles, loc="lower center",
               bbox_to_anchor=(0.5, 0.005), ncols=2, frameon=True,
               edgecolor=C_GRID, framealpha=0.97, fontsize=9.5,
               handlelength=1.8, borderpad=0.55, columnspacing=2.0,
               labelspacing=0.45,
               title=f"Bootstrap distributions  ($N_{{\\rm boot}} = {len(boot15)}$)",
               title_fontsize=10.0)

    fig.savefig(out_path)
    plt.close(fig)
    print(f"  → {out_path}")


# ══════════════════════════════════════════════════════════════════════════════
# FIGURE 2 — Robustness suite (letter): Q_b sensitivity + joint K_d × H
# ══════════════════════════════════════════════════════════════════════════════
def fig_robustness(d, out_path):
    """JGR:Planets full-width, clean three-panel layout.

    (a) FULL-WIDTH direct contrast map over the two basal fluxes, with
        the MCMC Q_b posterior drawn as translucent 68/95% credible
        regions + median star (the posterior lives in flux space, which
        is where it belongs); (b),(c) joint K_d x H RMSE surface per
        site. Shared legend below.

    Redesign 2026-07-06 (revert-to-clean): earlier revisions split the
    top row between the map and a posterior-implied-contrast histogram,
    which halved the map and read as cramped. The map is full-width
    again (the layout the project used before the histogram was added);
    the pushforward P(dK>0)=99.3% is stated in the caption, not forced
    into a second panel. The posterior is filled translucent regions,
    not a scatter cloud, so it reads as one clean shape on the field.
    """
    # assert_no_overlap lives in the house style module, whose import
    # applies the house rcParams; this legacy script styles itself, so
    # snapshot + restore to leave the sibling figures untouched.
    import sys as _sys
    import matplotlib as _mpl
    _rc = _mpl.rcParams.copy()
    _sys.path.insert(0, str(_ROOT / "src"))
    from lunar.plotting.style import assert_no_overlap
    _mpl.rcParams.update(_rc)

    from scipy.interpolate import PchipInterpolator
    from scipy.ndimage import gaussian_filter
    from matplotlib.patches import Rectangle

    fig = plt.figure(figsize=(JGR_FULL, 6.5))
    # A dedicated rightmost colorbar column (col 2) so BOTH rows' colorbars
    # sit in the same vertical band: the map (row 0, spanning cols 0-1) then
    # lines up edge-to-edge with the two panels below (row 1), instead of
    # its own attached colorbar shrinking it out of alignment.
    gs = fig.add_gridspec(2, 3, height_ratios=[1.18, 0.90],
                          width_ratios=[1.0, 1.0, 0.045],
                          hspace=0.50, wspace=0.30,
                          left=0.085, right=0.955, top=0.93, bottom=0.185)
    axA  = fig.add_subplot(gs[0, 0:2])   # Q_b contrast map, aligned over b+c
    caxA = fig.add_subplot(gs[0, 2])     # its colorbar (shared right band)
    axC  = fig.add_subplot(gs[1, 0])     # A15 joint K_d x H
    axD  = fig.add_subplot(gs[1, 1])     # A17 joint K_d x H
    caxCD = fig.add_subplot(gs[1, 2])    # their shared colorbar

    # ── (a) direct degeneracy map ───────────────────────────────────────────
    # DIRECT degeneracy map (audit F-9): the measured K_d*(Q_b) curves
    # from qb_degeneracy.json (one real re-retrieval per point; opposite
    # site responses), NOT the disproved proportional surrogate. Drawn
    # only over the measured domain -- no extrapolation.
    _dg = json.loads((_ROOT / "results" / "qb_degeneracy.json").read_text())
    qb15_pts = np.array([r["qb_mW"] for r in _dg["sites"]["A15"]])
    kd15_pts = np.array([r["kd_star_mW"] for r in _dg["sites"]["A15"]])
    qb17_pts = np.array([r["qb_mW"] for r in _dg["sites"]["A17"]])
    kd17_pts = np.array([r["kd_star_mW"] for r in _dg["sites"]["A17"]])
    kd15_of = PchipInterpolator(qb15_pts, kd15_pts)
    kd17_of = PchipInterpolator(qb17_pts, kd17_pts)
    bs = d["contrast_bootstrap"]
    sigma_c = (bs["ci_hi"] - bs["ci_lo"]) * 1e3 / (2 * 1.96)

    qb15_full = np.linspace(qb15_pts[0], qb15_pts[-1], 60)
    qb17_full = np.linspace(qb17_pts[0], qb17_pts[-1], 60)
    contrast_full = kd17_of(qb17_full)[:, None] - kd15_of(qb15_full)[None, :]
    sig_full = contrast_full / sigma_c

    # diverging map anchored at the zero null (warm = A17 more conductive).
    # vmax fitted to the data so the darkest coral marks the true peak
    # contrast; the field is positive everywhere, so only a sliver of the
    # cool half shows on the colorbar (it never crosses zero in the
    # plausible region -- the direct map does not have the wrong-model
    # proportional zero-crossing).
    _vmax = float(np.ceil(contrast_full.max()))
    norm = TwoSlopeNorm(vmin=-0.15 * _vmax, vcenter=0, vmax=_vmax)
    im = axA.pcolormesh(qb15_full, qb17_full, contrast_full,
                        cmap=ANTH_DIVERGE, norm=norm,
                        shading="gouraud", rasterized=True, zorder=1)
    cbar = fig.colorbar(im, cax=caxA)
    cbar.ax.set_ylabel(r"$\Delta K_d^{*}$  (mW m$^{-1}$ K$^{-1}$)",
                       fontsize=FS_LABEL, color=C_CHAR)
    cbar.ax.tick_params(labelsize=FS_TICK, colors=C_CHAR)
    cbar.outline.set_edgecolor(C_GRID)

    # published per-site Q_b envelope as a dashed box over the full heatmap
    # (reference-design theme: no dimming, a heavier dashed rectangle)
    axA.add_patch(Rectangle((14.0, 10.0), 25.0 - 14.0, 18.0 - 10.0,
                            fill=False, edgecolor=C_CHAR, lw=1.4,
                            linestyle=(0, (6, 3)), alpha=0.9, zorder=2.2))

    # significance contours as thin dashed lines (reference-design theme:
    # several parallel σ levels), labelled inline out in the margins
    cs = axA.contour(qb15_full, qb17_full, sig_full, levels=[2, 4, 6],
                     colors=C_CHAR, linewidths=0.8, linestyles="--",
                     alpha=0.6, zorder=2.3)
    axA.clabel(cs, fmt=lambda x: f"{int(x)}$\\sigma$", fontsize=FS_TICK,
               inline=True, inline_spacing=6)

    # reference flux points
    axA.plot(21.0, 16.0, "o", color=C_CHAR, markersize=9, mec="white",
             mew=1.3, zorder=6)
    axA.plot(14.7, 16.0, "s", color=C_FOREST, markersize=10, mec="white",
             mew=1.3, zorder=6)

    # MCMC joint Q_b posterior as FILLED translucent 68/95% credible
    # regions (highest-density mass containment). Filled shapes read as
    # one clean distribution; the old scatter cloud + line contours
    # stippled the field.
    ch = np.load(_ROOT / "results" / "bayesian_chains.npz")
    rng = np.random.default_rng(0)              # same seed/order as the MCMC script
    nch = min(len(ch["a15_kd"]), len(ch["a17_kd"]))
    i15 = rng.choice(len(ch["a15_kd"]), size=nch, replace=False)
    i17 = rng.choice(len(ch["a17_kd"]), size=nch, replace=False)
    qb15_s, qb17_s = ch["a15_qb"][i15], ch["a17_qb"][i17]
    H2, xe, ye = np.histogram2d(qb15_s, qb17_s, bins=60,
                                range=[[qb15_full[0], qb15_full[-1]],
                                       [qb17_full[0], qb17_full[-1]]])
    Hs = gaussian_filter(H2, sigma=1.8)
    hf = np.sort(Hs.ravel())[::-1]
    cmass = np.cumsum(hf) / hf.sum()
    lev68 = hf[np.searchsorted(cmass, 0.68)]
    lev95 = hf[np.searchsorted(cmass, 0.95)]
    xc, yc = 0.5 * (xe[:-1] + xe[1:]), 0.5 * (ye[:-1] + ye[1:])
    # ELEGANT (2026-07-06): the MCMC posterior is drawn as two THIN teal
    # credible-contour lines (68/95%) plus a compact median star -- NOT a
    # heavy filled blob with a floating detail box. Clean lines read like
    # the significance contours and keep the panel uncluttered; the median
    # coordinates and P-value move to the caption. (This is the direct-map
    # science; the old proportional-degeneracy "rescaling diagonal" that
    # looked tidy was disproved by audit F-9 and is deliberately absent.)
    axA.contour(xc, yc, Hs.T, levels=[lev95, lev68], colors=C_TEAL,
                linewidths=[1.0, 1.5], alpha=0.95, zorder=3.2)
    _st = json.loads((_ROOT / "results" /
                      "bayesian_crosscheck_samples.json").read_text())
    med15, med17 = float(_st["A15"]["qb_q50"]), float(_st["A17"]["qb_q50"])
    axA.plot(med15, med17, "*", markersize=15, color=C_TEAL, mec="white",
             mew=1.2, zorder=8)

    fmt_axis(axA,
             xlabel=r"Apollo 15 basal flux $Q_b$  (mW m$^{-2}$)",
             ylabel=r"Apollo 17 basal flux $Q_b$  (mW m$^{-2}$)",
             title=r"(a)  Inter-site $K_d^{*}$ contrast vs. non-uniform $Q_b$")
    axA.set_xlim(qb15_full[0], qb15_full[-1])
    axA.set_ylim(qb17_full[0], qb17_full[-1])

    # the map now extends below the envelope to frame the star, so the far
    # (implausible) low-A15 / high-A17 corner dips slightly negative -- the
    # claim is that the contrast stays positive WITHIN the published
    # envelope (14-25 x 10-18 mW), which the assertion guards.
    _me = (qb15_full >= 14) & (qb15_full <= 25)
    _mh = (qb17_full >= 10) & (qb17_full <= 18)
    cmin_env = float(contrast_full[np.ix_(_mh, _me)].min())
    assert cmin_env > 0, "contrast crosses zero inside the envelope; check caption"
    p_gt = _st["contrast"]["p_gt"] * 100
    print(f"    (a) min dK_d* inside envelope +{cmin_env:.2f}; full-domain min "
          f"{contrast_full.min():+.2f}; MCMC median ({med15:.1f},{med17:.1f}), "
          f"P(A17>A15)={p_gt:.1f}%  (for caption)")

    # ── (b)(c) joint K_d x H per site ────────────────────────────────────────
    _pa = json.loads((_ROOT / "results" / "kd_retrieval_results.json").read_text())
    site_ext = {}
    for name in ["A15", "A17"]:
        j = _pa[name]["joint_kd_h"]
        site_ext[name] = dict(kd_mw=np.array(j["kd_grid"]) * 1e3,
                              h_cm=np.array(j["h_grid"]) * 100,
                              rmse=np.array(j["rmse2d"]), j=j)
    vmin_all = min(v["rmse"].min() for v in site_ext.values())
    vmax_all = max(v["rmse"].max() for v in site_ext.values())
    levels_shared = np.linspace(vmin_all, vmax_all, 20)

    cf_handle = None
    for ax, name, label in [(axC, "A15", "(b)  Apollo 15"),
                            (axD, "A17", "(c)  Apollo 17")]:
        e = site_ext[name]; j = e["j"]
        cf = ax.contourf(e["kd_mw"], e["h_cm"], e["rmse"],
                         levels=levels_shared, cmap=ANTH_SEQ, alpha=0.92)
        if cf_handle is None:
            cf_handle = cf
        levels_iso = [j["rmse_min"] + dx for dx in [0.5, 1.0, 2.0, 3.0]]
        cs = ax.contour(e["kd_mw"], e["h_cm"], e["rmse"], levels=levels_iso,
                        colors=C_CHAR, linewidths=1.1, alpha=0.8)
        # Label only the two shallowest iso levels, ONE label each, placed
        # manually at ~60% of the x-span on the contour itself: auto
        # placement duplicated labels and clipped/collided them in the
        # steep bottom corner (rule-2 defect caught 2026-07-12). The
        # colorbar carries the deeper values.
        _lo, _hi = e["kd_mw"][0], e["kd_mw"][-1]
        _pts = []
        # deeper level labeled farther right, where its contour has lifted
        # off the bottom axis (at 60% span it hugs the x-axis in panel b)
        for _li, _fx in ((0, 0.60), (1, 0.85)):
            _segs = cs.allsegs[_li]
            if not _segs:
                continue
            _seg = max(_segs, key=len)
            _xt = _lo + _fx * (_hi - _lo)
            _pts.append(tuple(_seg[np.argmin(np.abs(_seg[:, 0] - _xt))]))
        ax.clabel(cs, fmt="%.1f K", fontsize=FS_TICK, inline=True,
                  inline_spacing=4, manual=_pts)

        h_min_cm = j["h_min"] * 100
        h_lo, h_hi = e["h_cm"].min(), e["h_cm"].max()
        kd_min_mw = j["kd_min"] * 1e3
        kd_lo, kd_hi = e["kd_mw"][0], e["kd_mw"][-1]
        kd_span = kd_hi - kd_lo
        # A15's joint minimum is interior; A17's sits AT the sweep edge
        # (kd_min == grid max in kd_retrieval_results.json joint_kd_h),
        # so the edge fallback below is load-bearing for A17.
        edge = kd_min_mw >= kd_hi - 1e-6
        ax.set_xlim(kd_lo, kd_hi + (0.05 * kd_span if edge else 0.0))
        ax.set_ylim(h_lo, h_hi)
        ax.plot(kd_min_mw, h_min_cm, marker="D", markersize=10,
                color=C_CORAL, mec="white", mew=1.3, zorder=6)
        if edge:                       # safety: minimum on the swept edge
            ax.annotate("", xy=(kd_hi + 0.04 * kd_span, h_min_cm),
                        xytext=(kd_hi - 0.02 * kd_span, h_min_cm),
                        arrowprops=dict(arrowstyle="-|>", color=C_CORAL, lw=1.6),
                        zorder=6)
        ax.axhline(6.0, color=C_CHAR, ls="--", lw=1.1, alpha=0.7)
        ax.plot(d[name]["kd_star"] * 1e3, 6.0, "o", markersize=11,
                color=C_TEAL, mec="white", mew=1.4, zorder=6)
        fmt_axis(ax, xlabel=r"$K_d$  (mW m$^{-1}$ K$^{-1}$)",
                 ylabel=r"$H$  (cm)" if ax is axC else "", title=label)

    cbar2 = fig.colorbar(cf_handle, cax=caxCD)
    cbar2.set_ticks(np.arange(0.4, vmax_all, 0.4))
    cbar2.ax.set_ylabel("RMSE  (K)", fontsize=FS_LABEL, color=C_CHAR)
    cbar2.ax.tick_params(labelsize=FS_TICK, colors=C_CHAR)
    cbar2.outline.set_edgecolor(C_GRID)

    # ── shared legend BELOW ──────────────────────────────────────────────────
    handles = [
        Line2D([0],[0], marker="o", color="none", markerfacecolor=C_CHAR,
               mec="white", markersize=9,
               label=r"Langseth (1976) $Q_b$  (21, 16 mW m$^{-2}$)"),
        Line2D([0],[0], marker="s", color="none", markerfacecolor=C_FOREST,
               mec="white", markersize=9,
               label=r"Saito reanalysis  (A15 $-$30%)"),
        Line2D([0],[0], ls="--", color=C_CHAR, lw=0.8, alpha=0.6,
               label=r"contrast significance  ($2\sigma$, $4\sigma$, $6\sigma$)"),
        Line2D([0],[0], ls=(0, (6, 3)), color=C_CHAR, lw=1.4, alpha=0.9,
               label=r"Langseth (1976) $Q_b$ envelope  (a)"),
        Line2D([0],[0], color=C_TEAL, lw=1.5,
               label=r"MCMC $Q_b$ posterior, 68/95% credible  (a)"),
        Line2D([0],[0], marker="*", color="none", markerfacecolor=C_TEAL,
               mec="white", markersize=13, label=r"MCMC posterior median  (a)"),
        Line2D([0],[0], marker="D", color="none", markerfacecolor=C_CORAL,
               mec="white", markeredgewidth=1.3, markersize=8,
               label=r"joint RMSE minimum  (b, c)"),
        Line2D([0],[0], marker="o", color="none", markerfacecolor=C_TEAL,
               mec="white", markersize=9,
               label=r"1-D $K_d^{*}$ at $H = 6$ cm  (b, c)"),
    ]
    fig.legend(handles=handles, loc="lower center",
               bbox_to_anchor=(0.5, 0.0), ncols=3, frameon=True,
               edgecolor=C_GRID, framealpha=0.97, fontsize=8.5,
               handlelength=1.8, borderpad=0.5, columnspacing=1.3,
               labelspacing=0.35)

    fig.canvas.draw()
    for _ax in (axA, axC, axD):
        assert_no_overlap(_ax)

    fig.savefig(out_path, dpi=400, facecolor="white")
    plt.close(fig)
    print(f"  -> {out_path}")



# (The superseded single-panel fig_kd_sweep_v2 was removed; the letter
#  uses the two-panel fig_kd_sweep() in make_letter_figures.py.)


# ══════════════════════════════════════════════════════════════════════════════
# APPENDIX FIGURES — lab comparison + cold-trap (moved from letter)
# ══════════════════════════════════════════════════════════════════════════════
def fig_lab_comparison(d, out_path):
    fig, ax = plt.subplots(figsize=(11.5, 5.0))
    fig.subplots_adjust(left=0.32, right=0.78, top=0.90, bottom=0.16)

    sources = [
        ("Cremers & Birkebak 1971 (lab)", 0.9, 0.2, C_LAB,    "Lab"),
        ("Horai 1981 (lab)",               1.5, 0.4, C_LAB,    "Lab"),
        ("Hemingway 1973 (lab)",           1.2, 0.3, C_LAB,    "Lab"),
        ("Hayne 2017 (orbital, global)",   3.4, 0.5, C_HAYNE,  "Orbital"),
        ("Vasavada 2012 (orbital, deep)",  7.0, 1.5, C_HAYNE,  "Orbital"),
        ("Martínez & Siegler 2021 (orbital, $T,\\rho$-dependent)",
         7.5, 0.5, C_HAYNE, "Orbital"),
        ("This work — A15 (in situ)",
         d["A15"]["bootstrap"]["median"]*1e3,
         (d["A15"]["bootstrap"]["ci_hi"] - d["A15"]["bootstrap"]["ci_lo"])/4*1e3,
         C_A15, "In situ"),
        ("This work — A17 (in situ)",
         d["A17"]["bootstrap"]["median"]*1e3,
         (d["A17"]["bootstrap"]["ci_hi"] - d["A17"]["bootstrap"]["ci_lo"])/4*1e3,
         C_A17, "In situ"),
    ]
    sources.reverse()
    labels = [s[0] for s in sources]
    vals   = [s[1] for s in sources]
    errs   = [s[2] for s in sources]
    cols   = [s[3] for s in sources]

    y = np.arange(len(labels))
    ax.barh(y, vals, xerr=errs, color=cols, alpha=0.78,
            edgecolor=C_CHAR, lw=0.5,
            error_kw=dict(elinewidth=1.0, capsize=3.5, ecolor=C_CHAR))
    ax.set_yticks(y)
    ax.set_yticklabels(labels)
    ax.tick_params(axis="y", left=False)
    fmt_axis(ax,
             xlabel=r"$K_d$  (mW m$^{-1}$ K$^{-1}$)",
             title="$K_d$ estimates across measurement scales")
    ax.set_xlim(0, 14)

    # category legend OUTSIDE on the right of axes
    legend_handles = [
        mpatches.Patch(color=C_LAB,   alpha=0.78, label="Laboratory  (mm scale)"),
        mpatches.Patch(color=C_HAYNE, alpha=0.78, label="Orbital  (km scale)"),
        mpatches.Patch(color=C_A15,   alpha=0.78, label="In situ  Apollo 15"),
        mpatches.Patch(color=C_A17,   alpha=0.78, label="In situ  Apollo 17"),
    ]
    ax.legend(handles=legend_handles,
              bbox_to_anchor=(1.02, 1.0), loc="upper left",
              borderaxespad=0.0,
              title="Measurement type",
              title_fontsize=FS_LABEL, borderpad=0.7,
              handlelength=1.8)

    fig.savefig(out_path)
    plt.close(fig)
    print(f"  → {out_path}")


def fig_cold_trap(d, out_path):
    """Two-panel cold-trap figure.

    (a) z_stable vs K_d with a twinned right-hand y-axis showing the
        column-integrated heat-flow drop  Q_b * z_stable  in K.
        This makes the y-axis physically interpretable in heat-flow
        terms (how much T drop the column buys you) rather than just
        in metres.
    (b) Dimensionless ratio  eta(K_d) = z_stable(K_d) /
        [(T_stable - T_surf) * K_d / Q_b],  the cold-trap depth
        normalised by the analytic deep-limit prediction (constant-K
        Fourier formula).  eta == 1 would mean the deep-limit formula
        is exact; eta > 1 quantifies the extra thermal resistance
        contributed by the K_s shallow layer and the radiative term.
        A flat curve at eta ~ 1.005 confirms the near-linearity
        empirically, and the deviation is what was previously
        invisible on the depth-vs-K_d plot alone.
    """
    ct = d["cold_trap"]
    Kd = np.array(ct["kd_grid"]) * 1e3   # mW/m/K for x-axis
    z  = np.array(ct["depth_stable_m"])
    Qb_polar  = ct["Qb_polar"]                                 # W/m^2
    T_surf    = ct.get("T_surface_polar", 80.0)
    T_stable  = ct.get("T_ice_stable", 110.0)
    dT        = T_stable - T_surf

    # Deep-limit constant-K prediction:  z_dl = dT * K_d / Q_b
    z_deep_limit_m = dT * (Kd * 1e-3) / Qb_polar
    eta = z / z_deep_limit_m   # dimensionless

    fig, (axA, axB) = plt.subplots(
        1, 2, figsize=(JGR_FULL, 4.2),
        gridspec_kw={"wspace": 0.50, "width_ratios": [1.25, 1.0]},
    )
    # bottom=0.36 leaves enough room below the x-axis labels for the
    # legend box (anchored at y=0.02 below); top=0.86 gives panel
    # titles breathing room above the axes.
    fig.subplots_adjust(left=0.085, right=0.93, top=0.86, bottom=0.36)

    # ────────────── Panel (a): depth + twinned heat-flow axis ──────────
    axA.plot(Kd, z, color=C_TEAL, lw=2.4, label="Hayne $K(T,z)$ integration")
    axA.fill_between(Kd, z, 0, color=C_TEAL_L, alpha=0.20)

    refs = [
        (3.4, "Hayne 2017 global  ($K_d = 3.4$)", C_TEAL),
        (d["A15"]["bootstrap"]["median"]*1e3,
         f"A15 retrieval  ($K_d = {d['A15']['bootstrap']['median']*1e3:.2f}$)", C_A15),
        (d["A17"]["bootstrap"]["median"]*1e3,
         f"A17 retrieval  ($K_d = {d['A17']['bootstrap']['median']*1e3:.2f}$)", C_A17),
    ]
    z_max = z.max()
    for kd_v, lab, col in refs:
        z_v = np.interp(kd_v, Kd, z)
        axA.plot([kd_v, kd_v], [0, z_v], color=col, ls="--", lw=1.2, alpha=0.85)
        axA.plot(kd_v, z_v, "o", markersize=10, color=col, mec="white", mew=1.3,
                 zorder=4, label=lab)

    fmt_axis(axA,
             xlabel=r"$K_d$  (mW m$^{-1}$ K$^{-1}$)",
             ylabel=r"Cold-trap depth  $z_\mathrm{stable}$  (m)",
             title=("(a)  Depth where buried ice is thermally stable"))
    axA.set_xlim(2, 12)
    axA.set_ylim(0, z_max * 1.10)

    # Twinned right axis: column-integrated heat-flow drop  Q_b * z  (K)
    axA_r = axA.twinx()
    axA_r.set_ylim(axA.get_ylim()[0] * Qb_polar * 1000,
                   axA.get_ylim()[1] * Qb_polar * 1000)
    axA_r.set_ylabel(r"Column heat-flow $\Delta T = Q_b\,z$  (mK)",
                     color=C_DIM)
    axA_r.tick_params(axis="y", colors=C_DIM, labelsize=FS_TICK)
    axA_r.spines["right"].set_color(C_DIM)
    axA_r.spines["right"].set_visible(True)
    axA_r.spines["top"].set_visible(False)

    # ────────────── Panel (b): dimensionless residual eta ──────────────
    # Coral (not teal) so the eta curve is visually distinct from the
    # depth curve in panel (a) -- they are different quantities.
    axB.plot(Kd, eta, color=C_CORAL, lw=2.4,
             label=r"$\eta(K_d)$ from Hayne $K(T,z)$ integration")
    axB.fill_between(Kd, eta, 1.0, color=C_CORAL_L, alpha=0.18)
    axB.axhline(1.0, color=C_DIM, ls="--", lw=1.0, alpha=0.7)
    axB.text(0.02, 0.04, r"dashed: deep-limit ($K_s\!=\!0$, $\chi\!=\!0$)",
             transform=axB.transAxes,
             ha="left", va="bottom", fontsize=FS_TICK - 0.5,
             color=C_DIM, style="italic")

    for kd_v, lab, col in refs:
        eta_v = np.interp(kd_v, Kd, eta)
        axB.plot([kd_v, kd_v], [1.0, eta_v], color=col, ls="--", lw=1.2,
                 alpha=0.85)
        axB.plot(kd_v, eta_v, "o", markersize=10, color=col, mec="white",
                 mew=1.3, zorder=4)

    fmt_axis(axB,
             xlabel=r"$K_d$  (mW m$^{-1}$ K$^{-1}$)",
             ylabel=r"$\eta = z_\mathrm{stable}/(\Delta T\cdot K_d/Q_b)$",
             title=("(b)  Deviation from the constant-$K$ Fourier limit"))
    axB.set_xlim(2, 12)
    # Tight y-range around eta = 1 so the small deviation is visible
    eta_min, eta_max = float(eta.min()), float(eta.max())
    pad = max(0.002, 0.15 * (eta_max - eta_min))
    axB.set_ylim(min(1.0, eta_min) - pad, eta_max + pad)
    axB.yaxis.set_major_formatter(mtick.FormatStrFormatter("%.3f"))

    # Shared legend BELOW the figure in its own box
    fig.legend(loc="lower center", bbox_to_anchor=(0.5, 0.02),
               ncols=4, frameon=True, edgecolor=C_GRID,
               framealpha=0.97, fontsize=FS_LEGEND,
               title=(f"Polar $Q_b = {Qb_polar*1e3:.0f}$ mW m$^{{-2}}$, "
                      f"$T_\\mathrm{{surf}} = {T_surf:.0f}$ K, "
                      f"$T_\\mathrm{{stable}} = {T_stable:.0f}$ K   "
                      "(Schorghofer & Aharonson 2005)"),
               title_fontsize=FS_LABEL, borderpad=0.6,
               handlelength=1.6, columnspacing=1.6)

    fig.savefig(out_path)
    plt.close(fig)
    print(f"  → {out_path}")




# ══════════════════════════════════════════════════════════════════════════════
# FIGURE — Thermal profile comparison: two conductivity models
#   (Hayne retrieved K_d* | genuine Martinez & Siegler 2021 forward)
# ══════════════════════════════════════════════════════════════════════════════
def fig_thermal_profiles(d, out_path):
    """Depth-temperature profiles against the Apollo HFE deep sensors at
    both sites, for two conductivity models: the Hayne (2017)
    smooth-exponential form at its per-site retrieved K_d*, and the
    parameter-free Martinez & Siegler (2021) T,rho-dependent model
    (make_k_ms below).  Runs the forward model from scratch."""
    import sys; sys.path.insert(0, str(pathlib.Path(__file__).parents[2]))
    from copy import deepcopy
    from lunar.grid import make_geometric_grid
    from lunar.solver import PixelInputs, solve_pixel
    from lunar.properties import conductivity_hayne, specific_heat
    from lunar.constants import (K_SURFACE, H_PARAMETER, CHI_RADIATIVE,
                                  T_REFERENCE, LUNATION_SECONDS)
    from lunar.apollo_helpers import extract_sensor_stability

    # ── forward-model settings (match pipeline) ───────────────────────────
    GRID   = dict(z_max=5.0, dz0=0.002, growth=0.08)
    DT     = 3600.0
    N_LUN  = 30
    TOL    = 0.01
    T_LUN  = LUNATION_SECONDS
    S0_    = 1361.0
    CHI    = CHI_RADIATIVE
    T_REF  = T_REFERENCE

    SITE_CFGS = {
        'A15': dict(label='Apollo 15', mission='a15', lat=26.13,
                    albedo=0.131, emissivity=0.95, Q_BASAL=0.021,
                    T_MEAN_EFF=252.0, MIN_DEPTH_CM=80),
        'A17': dict(label='Apollo 17', mission='a17', lat=20.19,
                    albedo=0.137, emissivity=0.95, Q_BASAL=0.016,
                    T_MEAN_EFF=255.0, MIN_DEPTH_CM=80),
    }
    # ── Genuine Martinez & Siegler (2021) conductivity model ──────────────
    # K_MS(T,rho) = (A1 rho + A2) k_am(T) + (B1 rho + B2) T^3
    # verified against their Zenodo code (lunar1Dheat v1.6, updateRK.m).
    MS_AM = dict(A=-2.03297e-1, B=-11.472, C=22.5793, D=-14.3084,
                 E=3.41742, F=0.01101, G=-2.80491e-5, H=3.35837e-8,
                 I=-1.40021e-11)
    MS_A1, MS_A2 = 5.0821e-6, -0.0051
    MS_B1, MS_B2 = 2.022e-13, -1.953e-10
    MS_RHO_S, MS_RHO_D, MS_H = 1100.0, 1800.0, 0.054

    def make_k_hayne(kd):
        def k(T, z):
            return conductivity_hayne(T, z, Ks=K_SURFACE, Kd=kd,
                                      H=H_PARAMETER, chi=CHI)
        return k

    def make_k_ms():
        am = MS_AM
        def k(T, z):
            T_a = np.broadcast_to(np.asarray(T, float),
                                  np.asarray(z, float).shape).astype(float)
            z_a = np.asarray(z, float)
            k_am = (am['A'] + am['B']*T_a**-4 + am['C']*T_a**-3
                    + am['D']*T_a**-2 + am['E']*T_a**-1 + am['F']*T_a
                    + am['G']*T_a**2 + am['H']*T_a**3 + am['I']*T_a**4)
            rho = MS_RHO_D - (MS_RHO_D - MS_RHO_S) * np.exp(-z_a / MS_H)
            return (MS_A1*rho + MS_A2)*k_am + (MS_B1*rho + MS_B2)*T_a**3
        return k

    def run_profile(site_cfg, k_func):
        grid  = make_geometric_grid(**GRID)
        z_mid = grid.z_mid
        N_t   = int(T_LUN / DT) + 1
        t_s   = np.linspace(0.0, T_LUN, N_t)
        cos_l = np.cos(np.deg2rad(site_cfg['lat']))
        insol = S0_ * cos_l * np.maximum(0.0, np.cos(2*np.pi * t_s / T_LUN))
        K_init = k_func(np.full_like(z_mid, site_cfg['T_MEAN_EFF']), z_mid)
        T_init = (site_cfg['T_MEAN_EFF']
                  + site_cfg['Q_BASAL'] * np.cumsum(grid.dz / K_init))
        out = solve_pixel(PixelInputs(
            grid=grid, t=t_s, bc_mode='radiative',
            insolation=insol, albedo=site_cfg['albedo'],
            emissivity=site_cfg['emissivity'], Q_b=site_cfg['Q_BASAL'],
            T_init=T_init, n_lunations_spinup=N_LUN, spinup_tol_K=TOL,
            K_func=k_func, cp_func=lambda T: specific_heat(T, model='hayne'),
        ))
        return z_mid * 100, out.T.mean(axis=1)   # depth in cm, mean T profile

    # ── 2×2 grid: top = full profile, bottom = deep-only zoom ────────────────
    # Legend goes BELOW the plots so it cannot overlap any axis labels.
    # bottom=0.215 reserves a clear strip for the legend box; the
    # panel (c)/(d) x-axis labels sit above it inside the gridspec.
    # The long explanatory note that used to be the legend title now
    # lives in the LaTeX caption, so the legend box stays compact.
    fig = plt.figure(figsize=(JGR_FULL, 5.6))
    gs  = fig.add_gridspec(2, 2, height_ratios=[0.82, 1.18],
                           hspace=0.46, wspace=0.32,
                           left=0.10, right=0.97, top=0.94, bottom=0.215)
    axes_full = [fig.add_subplot(gs[0, 0]), fig.add_subplot(gs[0, 1])]
    axes_zoom = [fig.add_subplot(gs[1, 0]), fig.add_subplot(gs[1, 1])]

    # ── run models and collect per-site data first ────────────────────────────
    # Use kd_retrieval_results.json as the single authoritative source for the
    # Hayne K_d* -- this is the same file the manuscript text and Table 1
    # are built from, so the figure and the text cannot drift apart.
    _pa_path = _ROOT / "results" / "kd_retrieval_results.json"
    d_auth = json.loads(_pa_path.read_text())

    # Forward profiles come from the SAME pipeline driver as the
    # retrieval (converged periodic equilibrium + the verified Martinez
    # coefficients in lunar.properties). The local run_profile /
    # make_k_* helpers above are retained for reference only; they used
    # the superseded fixed-length spin-up and an unverified B1 variant.
    from pipeline.compute.retrieve_kd import (SITES as _PIPE_SITES,
                                              run_with as _pipe_run_with)
    site_data = {}
    for name, site_cfg in SITE_CFGS.items():
        kd_r  = d_auth[name]["kd_star"]              # Hayne retrieved K_d*
        print(f"  Running Hayne K_d*={kd_r*1e3:.2f}  for {name} ...", flush=True)
        z_h_m, T_h = _pipe_run_with(_PIPE_SITES[name], kd=kd_r)
        z_h = z_h_m * 100
        print(f"  Running M&S model for {name} ...", flush=True)
        z_m_m, T_m = _pipe_run_with(_PIPE_SITES[name], k_model='martinez')
        z_m = z_m_m * 100

        obs_raw = extract_sensor_stability(site_cfg['mission'], min_depth_cm=0)
        sensors = obs_raw['sensors']
        z_obs = np.array([s['depth_cm'] for s in sensors])
        T_obs = np.array([s['T_eq']     for s in sensors])
        T_err = np.array([s['T_std']    for s in sensors])
        deep  = z_obs >= site_cfg['MIN_DEPTH_CM']
        site_data[name] = dict(kd_r=kd_r,
                                z_h=z_h, T_h=T_h, z_m=z_m, T_m=T_m,
                                z_obs=z_obs, T_obs=T_obs, T_err=T_err, deep=deep)

    legend_handles = []
    col_labels = ['a', 'b', 'c', 'd']

    for col, (name, site_cfg) in enumerate(SITE_CFGS.items()):
        sd     = site_data[name]
        kd_r   = sd['kd_r']
        z_h, T_h = sd['z_h'], sd['T_h']
        z_m, T_m = sd['z_m'], sd['T_m']
        z_obs, T_obs, T_err = sd['z_obs'], sd['T_obs'], sd['T_err']
        deep   = sd['deep']
        C_site = C_A15 if name == "A15" else C_A17

        # ── TOP ROW: full profile (0–220 cm) ─────────────────────────────────
        ax_f = axes_full[col]

        # Plot the Hayne curve without a label (the legend below uses
        # one combined entry listing both per-site K_d* values, since
        # the curve is the same Hayne form at two different K_d*).
        lH, = ax_f.plot(T_h, z_h, color=C_TEAL, lw=2.0)
        lM, = ax_f.plot(T_m, z_m, color=C_MS,   lw=2.0, ls="--",
                        label="Martínez & Siegler (2021) forward")

        ax_f.errorbar(T_obs[~deep], z_obs[~deep], xerr=T_err[~deep],
                      fmt="o", ms=5, color=C_NEUTRAL, mec=C_NEUTRAL,
                      elinewidth=0.8, capsize=2.5, zorder=2)
        lD = ax_f.errorbar(T_obs[deep], z_obs[deep], xerr=T_err[deep],
                           fmt="o", ms=6.5, color=C_site, mec="white", mew=0.9,
                           elinewidth=0.9, capsize=3, zorder=3,
                           label="HFE deep sensors (used in retrieval)")

        ax_f.axhspan(0, site_cfg['MIN_DEPTH_CM'], color=C_GRID, alpha=0.45, zorder=0)
        # left edge of the band is empty at both sites (profiles and excluded
        # markers all sit centre-right); the old right-edge spot hit a marker
        ax_f.text(0.03, site_cfg['MIN_DEPTH_CM'] + 2,
                  "borestem zone", transform=ax_f.get_yaxis_transform(),
                  ha="left", va="bottom", fontsize=FS_TICK - 1.5,
                  color=C_DIM, style="italic")

        fmt_axis(ax_f,
                 xlabel=r"$T$ (K)",
                 ylabel="Depth  (cm)" if col == 0 else "",
                 title=f"({col_labels[col]})  {site_cfg['label']}")
        ax_f.set_ylim(220, 0)
        # Fixed common x-range: the huge within-window scatter bar of one
        # excluded shallow A17 sensor otherwise stretches the axis ~12 K.
        ax_f.set_xlim(214, 266)
        ax_f.yaxis.set_minor_locator(mtick.AutoMinorLocator())
        ax_f.xaxis.set_minor_locator(mtick.AutoMinorLocator())

        # ── BOTTOM ROW: deep-only zoom, tight x-axis ──────────────────────────
        ax_z = axes_zoom[col]

        MIN_CM = site_cfg['MIN_DEPTH_CM']
        # depth range: from just above borestem boundary to 220 cm
        ax_z.set_ylim(220, MIN_CM - 3)

        # model curves — only the deep portion matters visually
        ax_z.plot(T_h, z_h, color=C_TEAL,   lw=2.2)
        ax_z.plot(T_m, z_m, color=C_MS,     lw=2.2, ls="--")

        ax_z.errorbar(T_obs[deep], z_obs[deep], xerr=T_err[deep],
                      fmt="o", ms=7, color=C_site, mec="white", mew=1.0,
                      elinewidth=1.0, capsize=3.5, zorder=3)

        # tight x-axis: span only the temperature range actually shown
        # (borestem base to the 220-cm panel floor) + margin; the model
        # column continues to 500 cm and would otherwise drag the axis
        # ~6 K past the visible curves.
        mask_deep = (z_h >= MIN_CM) & (z_h <= 220.0)
        T_all_deep = np.concatenate([T_h[mask_deep], T_m[mask_deep],
                                     T_obs[deep] - T_err[deep],
                                     T_obs[deep] + T_err[deep]])
        margin = max(0.6, (T_all_deep.max() - T_all_deep.min()) * 0.12)
        ax_z.set_xlim(T_all_deep.min() - margin, T_all_deep.max() + margin)

        # dashed reference line at borestem boundary; label on the
        # right edge of the panel (out of the data points' way)
        ax_z.axhline(MIN_CM, color=C_DIM, lw=0.8, ls=":", alpha=0.7)
        ax_z.text(0.98, MIN_CM - 1,
                  f"borestem base ({MIN_CM} cm)",
                  transform=ax_z.get_yaxis_transform(),
                  ha="right", va="top", fontsize=FS_TICK - 2,
                  color=C_DIM, style="italic")

        fmt_axis(ax_z,
                 xlabel=r"$T$ (K)",
                 ylabel="Depth  (cm)" if col == 0 else "",
                 title=f"({col_labels[col+2]})  {site_cfg['label']},  deep-sensor zoom")
        ax_z.yaxis.set_minor_locator(mtick.AutoMinorLocator())
        ax_z.xaxis.set_minor_locator(mtick.AutoMinorLocator())

        if col == 0:
            legend_handles = [lM, lD,
                Line2D([0],[0], marker="o", color="none",
                       markerfacecolor=C_NEUTRAL, markersize=6,
                       label="HFE shallow sensors (borestem-excluded)")]

    # Build a single Hayne legend entry that names both per-site
    # K_d* values (one Hayne curve per site, drawn in the same teal,
    # so a single entry conveys the form + both retrieved knobs).
    kd_a15 = site_data["A15"]["kd_r"] * 1e3
    kd_a17 = site_data["A17"]["kd_r"] * 1e3
    hayne_label = (rf"Hayne (2017), $K_d^{{*}}$: A15 = {kd_a15:.2f}, "
                   rf"A17 = {kd_a17:.2f} mW m$^{{-1}}$ K$^{{-1}}$")
    lH_combined = Line2D([0], [0], color=C_TEAL, lw=2.0,
                          label=hayne_label)
    legend_handles = [lH_combined] + legend_handles

    # ── shared legend BELOW the figure (user preference) ─────────────────────
    # No legend title: the explanatory note is in the LaTeX caption so
    # the box stays compact and clears the panel (c)/(d) x-axis labels.
    fig.legend(handles=legend_handles, loc="lower center",
               bbox_to_anchor=(0.5, 0.012), ncols=2, frameon=True,
               edgecolor=C_GRID, framealpha=0.97, fontsize=8.5,
               handlelength=2.0, borderpad=0.5, columnspacing=1.4,
               labelspacing=0.3)

    fig.savefig(out_path)
    plt.close(fig)
    print(f"  → {out_path}")


# ══════════════════════════════════════════════════════════════════════════════
# Main
# ══════════════════════════════════════════════════════════════════════════════
def main():
    d = json.loads(RESULTS.read_text())
    print("Regenerating Phase-2 figures with publication-grade aesthetic:")
    fig_bootstrap(d, LETTER_FIGS / "fig_bootstrap.pdf")
    fig_robustness(d, LETTER_FIGS / "fig_robustness.pdf")
    fig_thermal_profiles(d, LETTER_FIGS / "fig_thermal_profiles.pdf")  # used by guidebook Ch.5
    # NOTE: fig_lab_comparison and fig_cold_trap are not referenced by any
    # manuscript, and fig_cold_trap needs a 'cold_trap' JSON block that the
    # current pipeline no longer writes. Both functions remain defined for
    # ad-hoc use, but main() only regenerates the figures the paper uses.
    print("Done.")

if __name__ == "__main__":
    main()
