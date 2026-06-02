"""
Phase-2 figure regeneration with publication-grade aesthetic
(Anthropic-aligned: warm coral, deep teal, restrained palette,
clean serif typography, generous whitespace).

Reads the numerical results from output/phase2_results.json and
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
C_MS       = "#9E2A1F"     # deep red, distinguishable from coral
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
# phase_a_results.json is the single authoritative results file: it is
# what the manuscript text and tables are built from (bootstrap with
# N_boot = 1500), and it now also carries the cold_trap and
# qb_sensitivity blocks. A previous version read phase2_results.json
# here, which held a *different* bootstrap run (N_boot = 2000, contrast
# CI [3.8,13.3] instead of [-3.2,16.6]) -- so the figures disagreed
# with the text. Do not point this back at phase2_results.json.
RESULTS       = _ROOT / "output" / "phase_a_results.json"
LETTER_FIGS   = _ROOT / "paper" / "letter"     / "figures"
APPENDIX_FIGS = _ROOT / "paper" / "appendix"   / "figures"


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

    bins = np.linspace(2, 19, 60)
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
    ax0.set_xlim(2, 22)
    ax0.set_ylim(0, ymax * 1.10)
    ax0.xaxis.set_minor_locator(mtick.AutoMinorLocator())
    # NB: no in-axes legend — the shared legend is below the figure.

    # ── (b) inter-site contrast distribution ────────────────────────────────
    contrast = (boot17 - boot15)
    cmed, clo, chi_ = np.percentile(contrast, [50, 2.5, 97.5])

    bins2 = np.linspace(-2, 16, 60)
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
    ax1.set_xlim(-2, 17)
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
               bbox_to_anchor=(0.5, 0.005), ncols=3, frameon=True,
               edgecolor=C_GRID, framealpha=0.97, fontsize=8.5,
               handlelength=1.6, borderpad=0.4, columnspacing=1.2,
               labelspacing=0.3,
               title=f"Bootstrap distributions  ($N_{{\\rm boot}} = {len(boot15)}$)",
               title_fontsize=9.0)

    fig.savefig(out_path)
    plt.close(fig)
    print(f"  → {out_path}")


# ══════════════════════════════════════════════════════════════════════════════
# FIGURE 2 — Robustness suite (letter): Q_b sensitivity + joint K_d × H
# ══════════════════════════════════════════════════════════════════════════════
def fig_robustness(d, out_path):
    """JGR:Planets full-width. Three panels: (a) Q_b heatmap spans
    full top row; (b)(c) joint K_d × H per site below. SHARED legend
    below the figure (no in-axes legends)."""
    # Height trimmed from 7.1 to 6.0 in so the figure fits on a page
    # with text rather than being floated onto a near-empty page.
    fig = plt.figure(figsize=(JGR_FULL, 6.0))
    # top=0.93 (legend now BELOW, not above); bottom=0.18 reserves a
    # clear strip for the three-row shared legend.
    gs = fig.add_gridspec(2, 2, height_ratios=[1.0, 0.95],
                          width_ratios=[1.0, 1.0],
                          hspace=0.55, wspace=0.32,
                          left=0.09, right=0.92, top=0.93, bottom=0.18)
    axA = fig.add_subplot(gs[0, :])      # full-width Q_b heatmap
    axB = fig.add_subplot(gs[1, 0])
    axC = fig.add_subplot(gs[1, 1])

    # ── (a) Q_b sensitivity heatmap ─────────────────────────────────────────
    # The deep gradient depends only on the ratio Q_b/K_d, and at steady
    # state K_d*(α·Q_b) = α·K_d*(Q_b) exactly, so the inter-site contrast
    # is the EXACT linear surface
    #     ΔK_d(α15,α17) = K_d_A17* · α17 − K_d_A15* · α15.
    # The pipeline's numerically computed qb_sensitivity grid agrees with
    # this formula to machine precision (max |Δ| = 0 over the full 13×13
    # grid).  We therefore render the whole panel from the formula on a
    # single UNIFORM grid.  (A previous version stitched the computed
    # grid onto an analytic extension with mismatched spacing; the
    # 0.01-wide sliver cell at the α15=0.7 join produced a spurious
    # vertical seam in the heatmap and a kink in the σ contours.)
    qbs = d["qb_sensitivity"]
    alphas = np.array(qbs["alpha_grid"])
    contrast_comp = np.array(qbs["contrast_grid"]) * 1e3   # for verification
    kd_A15_nom = d["A15"]["kd_star"] * 1e3
    kd_A17_nom = d["A17"]["kd_star"] * 1e3
    bs = d["contrast_bootstrap"]
    sigma_c = (bs["ci_hi"] - bs["ci_lo"]) * 1e3 / (2 * 1.96)

    # single uniform grid spanning the full plotted range.
    # Both axes extend down to 0.05 so the diverging colormap shows
    # both the positive (A17 > A15) and negative (A17 < A15) contrast
    # regions; otherwise the panel reads as uniformly red.
    a15_full = np.linspace(0.05, alphas[-1], 60)
    a17_all  = np.linspace(0.05, alphas[-1], 60)
    A15_full, A17_full = np.meshgrid(a15_full, a17_all)
    contrast_full = kd_A17_nom * A17_full - kd_A15_nom * A15_full
    sig_full      = contrast_full / sigma_c

    # sanity check: the analytic surface must match the computed grid
    _A15c, _A17c = np.meshgrid(alphas, alphas)
    _ana_c = kd_A17_nom * _A17c - kd_A15_nom * _A15c
    assert np.abs(_ana_c - contrast_comp.T).max() < 1e-6, \
        "analytic Q_b-degeneracy surface disagrees with computed grid"

    # Diverging colormap anchored at zero so the cool/warm split lines up
    # with the sign of the contrast (negative = A17 less conductive than
    # A15, positive = A17 more conductive). Symmetric ±15 range keeps both
    # halves of the colormap fully used given the data range [-6, +14].
    norm = TwoSlopeNorm(vmin=-7, vcenter=0, vmax=15)
    # rasterized=True embeds the heatmap as a bitmap inside the PDF,
    # which Ghostscript flattens reliably; without this, gouraud-shaded
    # gradients can disappear when the PDF is post-processed (e.g. the
    # /prepress flat PDF used for printer submission).
    im = axA.pcolormesh(a15_full, a17_all, contrast_full,
                        cmap=ANTH_DIVERGE, norm=norm,
                        shading="gouraud", rasterized=True)

    cbar = fig.colorbar(im, ax=axA, pad=0.02, fraction=0.04, aspect=18)
    cbar.ax.set_ylabel(r"$\Delta K_d^{*}$  (mW m$^{-1}$ K$^{-1}$)",
                       fontsize=FS_LABEL, color=C_CHAR)
    cbar.ax.tick_params(labelsize=FS_TICK, colors=C_CHAR)
    cbar.outline.set_edgecolor(C_GRID)

    cs = axA.contour(a15_full, a17_all, sig_full, levels=[2, 4, 7],
                     colors=C_CHAR, linewidths=1.0, linestyles="--",
                     alpha=0.75)
    axA.clabel(cs, fmt=lambda x: f"{int(x)}σ",
               fontsize=FS_TICK, inline=True, inline_spacing=4)

    # Diagonal (global rescaling, a15=a17) only where both axes overlap.
    # Drawn in dark charcoal (not white) so it stays legible over the
    # pale centre of the diverging colour map.
    diag_a = np.linspace(0.05, alphas[-1], 100)
    axA.plot(diag_a, diag_a, color=C_CHAR, lw=2.6, alpha=0.9,
             solid_capstyle="butt")
    axA.plot(1.0, 1.0, "o", color=C_CHAR, markersize=10, mec="white", mew=1.4,
             label="nominal $Q_b$ (both sites)")
    axA.plot(0.7, 1.0, "s", color=C_FOREST, markersize=11, mec="white",
             mew=1.4, label="Saito reanalysis  (A15 −30%)")
    axA.plot([], [], "-", color="white", lw=2.6,
             label="global rescaling diagonal  (contrast invariant)")
    axA.plot([], [], ls="--", color=C_CHAR, lw=1.0,
             label="contrast significance contours (2σ, 4σ, 7σ)")

    fmt_axis(axA,
             xlabel=r"A15 $Q_b$ rescaling factor  $\alpha_{15}$",
             ylabel=r"A17 $Q_b$ rescaling factor  $\alpha_{17}$",
             title=r"(a)  Inter-site $K_d^{*}$ contrast vs. non-uniform $Q_b$")
    axA.set_xlim(0, alphas[-1])
    axA.set_ylim(0, alphas[-1])

    # (no in-axes legend — shared legend below the figure)

    # ── (b)(c) joint K_d × H per site ───────────────────────────────────────
    # The dense 8×8 K_d–H sweep is taken from phase_a_results.json -- the
    # SAME authoritative file the manuscript K_d values come from -- and
    # plotted directly with no extrapolation. (An earlier version read a
    # coarse 3×3 grid from phase2_results.json and quadratically
    # extrapolated it; the two files disagreed, so we now use the dense
    # grid as the single source of truth.)
    _pa = json.loads((_ROOT / "output" / "phase_a_results.json").read_text())

    # Pre-load both joint grids to share colorbar levels
    site_ext = {}
    for name in ["A15", "A17"]:
        j = _pa[name]["joint_kd_h"]
        kd_mw = np.array(j["kd_grid"]) * 1e3
        h_cm  = np.array(j["h_grid"])  * 100
        rmse  = np.array(j["rmse2d"])
        kd_f, h_f, r_f = kd_mw, h_cm, rmse        # no extrapolation
        site_ext[name] = dict(kd_f=kd_f, h_f=h_f, r_f=r_f,
                               kd_mw=kd_mw, h_cm=h_cm, rmse=rmse, j=j)

    vmin_all = min(v["r_f"].min() for v in site_ext.values())
    vmax_all = max(v["r_f"].max() for v in site_ext.values())
    levels_shared = np.linspace(vmin_all, vmax_all, 20)

    cf_handle = None
    for ax, name, label in [(axB, "A15", "(b)  Apollo 15"),
                            (axC, "A17", "(c)  Apollo 17")]:
        e = site_ext[name]
        j = e["j"]

        cf = ax.contourf(e["kd_f"], e["h_f"], e["r_f"],
                         levels=levels_shared, cmap=ANTH_SEQ, alpha=0.92)
        if cf_handle is None:
            cf_handle = cf

        rmse_min = j["rmse_min"]
        # RMSE iso-contours, dark charcoal (legible over the pale map)
        levels_iso = [rmse_min + dx for dx in [0.5, 1.0, 2.0, 3.0]]
        cs = ax.contour(e["kd_f"], e["h_f"], e["r_f"],
                        levels=levels_iso, colors=C_CHAR,
                        linewidths=1.1, alpha=0.8)
        ax.clabel(cs, fmt="%.1f K", fontsize=FS_TICK, inline=True,
                  inline_spacing=4)

        # Joint (K_d, H) RMSE minimum, drawn as a filled diamond (a
        # clean, conventional "best-fit point" marker). When the
        # minimum sits on the H-grid boundary the true minimum is
        # unresolved (H unconstrained); we keep the diamond on the
        # boundary and add a short outward arrow to indicate that the
        # surface is still descending past the edge.
        h_min_cm = j["h_min"] * 100
        h_grid_cm = np.array(j["h_grid"]) * 100
        h_lo, h_hi = h_grid_cm.min(), h_grid_cm.max()
        kd_min_mw = j["kd_min"] * 1e3
        ax.plot(kd_min_mw, h_min_cm, marker="D", markersize=10,
                color=C_CORAL, mec="white", mew=1.3, zorder=6)
        if h_min_cm >= h_hi - 1e-6:          # minimum at the upper edge
            ax.annotate("", xy=(kd_min_mw, h_hi + 0.40),
                        xytext=(kd_min_mw, h_hi - 0.05),
                        arrowprops=dict(arrowstyle="-|>", color=C_CORAL,
                                        lw=1.6), zorder=6,
                        annotation_clip=False)
        elif h_min_cm <= h_lo + 1e-6:        # minimum at the lower edge
            ax.annotate("", xy=(kd_min_mw, h_lo - 0.40),
                        xytext=(kd_min_mw, h_lo + 0.05),
                        arrowprops=dict(arrowstyle="-|>", color=C_CORAL,
                                        lw=1.6), zorder=6,
                        annotation_clip=False)
        ax.axhline(6.0, color=C_CHAR, ls="--", lw=1.1, alpha=0.7)
        kd_1d = d[name]["kd_star"] * 1e3
        ax.plot(kd_1d, 6.0, "o", markersize=11, color=C_TEAL,
                mec="white", mew=1.4, zorder=6)

        fmt_axis(ax,
                 xlabel=r"$K_d$  (mW m$^{-1}$ K$^{-1}$)",
                 ylabel=r"$H$  (cm)" if ax is axB else "",
                 title=label)
        # y-axis spans exactly the swept H range -- no blank strip
        ax.set_ylim(h_lo, h_hi)
        ax.set_xlim(e["kd_mw"][0], e["kd_mw"][-1])

    # shared colorbar for (b) and (c)
    cbar2 = fig.colorbar(cf_handle, ax=[axB, axC], pad=0.02, fraction=0.04,
                         aspect=18)
    cbar2.ax.set_ylabel("RMSE  (K)", fontsize=FS_LABEL, color=C_CHAR)
    cbar2.ax.tick_params(labelsize=FS_TICK, colors=C_CHAR)
    cbar2.outline.set_edgecolor(C_GRID)

    # ── shared legend BELOW the figure ───────────────────────────────────────
    from matplotlib.lines import Line2D
    handles = [
        Line2D([0],[0], marker="o", color="none", markerfacecolor=C_CHAR,
               mec="white", markersize=10,
               label=r"nominal $Q_b$  (both sites)"),
        Line2D([0],[0], marker="s", color="none", markerfacecolor=C_FOREST,
               mec="white", markersize=10,
               label=r"Saito reanalysis  ($\alpha_{15}=0.7$)"),
        Line2D([0],[0], color=C_CHAR, lw=2.4,
               label="global rescaling diagonal  (contrast invariant)"),
        Line2D([0],[0], ls="--", color=C_CHAR, lw=1.0,
               label=r"contrast significance  ($2\sigma$, $4\sigma$, $7\sigma$)"),
        Line2D([0],[0], marker="D", color="none", markerfacecolor=C_CORAL,
               mec="white", markeredgewidth=1.3, markersize=9,
               label=r"joint $(K_d, H)$ RMSE minimum  (panels b, c)"),
        Line2D([0],[0], marker="o", color="none", markerfacecolor=C_TEAL,
               mec="white", markersize=10,
               label=r"1-D $K_d^{*}$ at $H = 6$ cm  (panels b, c)"),
    ]
    fig.legend(handles=handles, loc="lower center",
               bbox_to_anchor=(0.5, 0.005), ncols=3, frameon=True,
               edgecolor=C_GRID, framealpha=0.97, fontsize=8.5,
               handlelength=1.6, borderpad=0.4, columnspacing=1.2,
               labelspacing=0.3)

    # High DPI for the rasterized pcolormesh + opaque white facecolor
    # so the panel survives any downstream PDF flattening (some viewers
    # drop low-DPI rasters embedded with transparency).
    fig.savefig(out_path, dpi=400, facecolor="white")
    plt.close(fig)
    print(f"  → {out_path}")


# ══════════════════════════════════════════════════════════════════════════════
# FIGURE — K_d sweep, SUPERSEDED single-panel version.
#   The letter now uses the two-panel fig_kd_sweep() in
#   make_letter_unified_figs.py.  Kept only for reference; not called
#   by main().  Do not reintroduce: it predates the genuine-M&S fix.
# ══════════════════════════════════════════════════════════════════════════════
def fig_kd_sweep_v2(d, out_path):
    """SUPERSEDED. Single-panel K_d sweep; replaced by the two-panel
    fig_kd_sweep() in make_letter_unified_figs.py."""
    fig, ax = plt.subplots(figsize=(JGR_FULL, 4.2))
    fig.subplots_adjust(left=0.10, right=0.97, top=0.89, bottom=0.15)

    for name, color in [("A15", C_A15), ("A17", C_A17)]:
        s = d[name]
        rmse = np.array(s["rmse_curve"])
        if name == "A15":
            kd_grid = np.linspace(1.5e-3, 9.0e-3, len(rmse)) * 1e3
        else:
            kd_grid = np.linspace(3.0e-3, 18.0e-3, len(rmse)) * 1e3

        from scipy.interpolate import CubicSpline
        cs = CubicSpline(kd_grid, rmse)
        kdfine = np.linspace(kd_grid[0], kd_grid[-1], 400)

        b = s["bootstrap"]
        lo_kd, hi_kd = b["ci_lo"]*1e3, b["ci_hi"]*1e3
        # 95% CI shading along the curve
        kd_in_ci = (kdfine >= lo_kd) & (kdfine <= hi_kd)
        ax.fill_between(kdfine[kd_in_ci], 0, cs(kdfine[kd_in_ci]),
                        color=color, alpha=0.10, zorder=0)

        ax.plot(kdfine, cs(kdfine), "-", color=color, lw=2.0, alpha=0.95,
                label=f"{name}  $K_d^{{*}}={s['kd_star']*1e3:.2f}$  "
                      f"[{lo_kd:.2f}, {hi_kd:.2f}]")
        ax.plot(kd_grid, rmse, "o", color=color, markersize=4.0,
                mec="white", mew=0.5, zorder=3)

        kdstar = s["kd_star"] * 1e3
        rmsestar = s["rmse_star"]
        ax.plot(kdstar, rmsestar, "*", color=color, markersize=18,
                mec="white", mew=1.3, zorder=5)

    # vertical references with legend entries (so they go OUTSIDE)
    ax.axvline(3.4, color=C_TEAL, ls="--", lw=1.2, alpha=0.75, zorder=1,
               label="Hayne 2017 global  $K_d = 3.4$")
    ax.axvline(3.8, color=C_FOREST, ls=":", lw=1.2, alpha=0.75, zorder=1,
               label="Feng 2020 deep value  $K_d = 3.8$")

    fmt_axis(ax,
             xlabel=r"Deep conductivity  $K_d$  (mW m$^{-1}$ K$^{-1}$)",
             ylabel=r"Deep-sensor RMSE  (K)",
             title="Per-site $K_d$ retrieval under the Hayne 2017 functional form")
    ax.set_xlim(0, 22)
    ax.set_ylim(0, 6)
    # Legend INSIDE upper-right
    ax.legend(loc="upper right", fontsize=FS_LEGEND, framealpha=0.95,
              title=r"Sites:  $K_d^{*}$  [95% bootstrap CI]",
              title_fontsize=FS_LEGEND, handlelength=1.4, borderpad=0.5)

    fig.savefig(out_path)
    plt.close(fig)
    print(f"  → {out_path}")


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
# APPENDIX FIGURE — Bayesian posterior (4 panels: 2 sites × {2D, marginal})
# ══════════════════════════════════════════════════════════════════════════════
def fig_posterior(out_path):
    """Read the posterior arrays from the cache file in /tmp if available,
    else recompute from json."""
    # We'll regenerate the posterior from scratch using the K_d sweep curves,
    # because the json doesn't store the (kdv, qbv, P) arrays.
    import sys; sys.path.insert(0, str(_ROOT))
    d = json.loads(RESULTS.read_text())

    # Reload the pipeline's posterior method
    from scripts.pipeline.phase2_pipeline_fast import kd_qb_posterior

    QB_PUB = {"A15": 0.021, "A17": 0.015}
    QB_PRIOR = {"A15": (0.018, 0.005), "A17": (0.013, 0.004)}

    # We need R (residual matrix) which is NOT in json. We need to rerun
    # K_d sweep OR re-derive R from rmse_curve. Since json only has the
    # RMSE curve (not the residuals), build a posterior using the RMSE
    # curve directly.
    # JGR_FULL-wide, page-fitting height. A 12x9 in figure scaled to the
    # text width became ~9 in tall and forced its own near-empty page.
    # hspace is generous because panels (c)/(d) carry a TOP axis (the
    # rescaled Q_b axis) plus a panel title, which must clear the
    # (a)/(b) x-axis labels above them.
    fig = plt.figure(figsize=(JGR_FULL, 6.2))
    gs = fig.add_gridspec(2, 2, hspace=0.78, wspace=0.34,
                          left=0.08, right=0.93, top=0.93, bottom=0.13)
    axes = [[fig.add_subplot(gs[r, c]) for c in (0, 1)] for r in (0, 1)]

    # Per-site explicit grid extents — chosen so the joint posterior is
    # evaluated across the FULL plot box (no blank top/bottom strips).
    KD_EXTENT_MW = {"A15": (1.5, 9.0), "A17": (3.0, 18.0)}
    QB_EXTENT_MW = {"A15": (1.0, 36.0), "A17": (1.0, 30.0)}

    for col, name in enumerate(["A15", "A17"]):
        rmse = np.array(d[name]["rmse_curve"])
        kd_lo_mW, kd_hi_mW = KD_EXTENT_MW[name]
        kd_grid = np.linspace(kd_lo_mW*1e-3, kd_hi_mW*1e-3, len(rmse))
        # Synthetic R: zero-mean residuals scaled to give the right RMSE
        # (this is just to plug into kd_qb_posterior which only needs the
        # diagonal RMSE shape and N).
        N_deep = 7 if name == "A15" else 16
        R = np.zeros((N_deep, len(rmse)))
        # Distribute the squared residual evenly so RMSE matches
        for k, rm in enumerate(rmse):
            R[:, k] = rm   # all identical → RMSE = rm
        qb_lo_mW, qb_hi_mW = QB_EXTENT_MW[name]
        kdv, qbv, P = kd_qb_posterior(
            R, kd_grid, qb_published=QB_PUB[name],
            qb_prior_mean=QB_PRIOR[name][0],
            qb_prior_sigma=QB_PRIOR[name][1],
            kd_range=(kd_lo_mW*1e-3, kd_hi_mW*1e-3),
            qb_range=(qb_lo_mW*1e-3, qb_hi_mW*1e-3))
        kdv_mW = kdv * 1e3
        qbv_mW = qbv * 1e3

        # ── upper: 2D posterior ──────────────────────────────────────────
        ax = axes[0][col]
        ax.contourf(kdv_mW, qbv_mW, P, levels=20, cmap=ANTH_SEQ)
        Pmax = P.max()
        # dark-charcoal posterior-mass contours (legible over the pale map)
        ax.contour(kdv_mW, qbv_mW, P,
                   levels=[Pmax*0.05, Pmax*0.32, Pmax*0.68],
                   colors=C_CHAR, linewidths=0.9,
                   linestyles=["-", "--", ":"], alpha=0.8)

        # mode -- filled diamond (conventional best-fit marker)
        ij = np.unravel_index(np.argmax(P), P.shape)
        ax.plot(kdv_mW[ij[1]], qbv_mW[ij[0]], marker="D",
                markersize=9, color=C_CORAL, mec="white", mew=1.3,
                zorder=6)

        # iso-ratio rays -- dim charcoal, not white
        for grad in [1.0, 2.0, 3.0]:
            ax.plot(kdv_mW, grad * kdv_mW, color=C_DIM, lw=0.6,
                    ls=":", alpha=0.55)

        fmt_axis(ax,
                 xlabel=r"$K_d$  (mW m$^{-1}$ K$^{-1}$)",
                 ylabel=r"$Q_b$  (mW m$^{-2}$)",
                 title=f"({chr(ord('a')+col)})  {name} joint posterior")
        # Lock axis limits to the computed grid extent so the contourf
        # fills the entire panel — no blank strips above/below.
        ax.set_xlim(kdv_mW[0], kdv_mW[-1])
        ax.set_ylim(qbv_mW[0], qbv_mW[-1])
        # legend inside top-right: just one mode marker
        ax.legend(handles=[Line2D([0], [0], marker="D", color="none",
                                  markerfacecolor=C_CORAL, mec="white",
                                  markersize=8, label="posterior mode")],
                  loc="upper right", borderpad=0.5,
                  facecolor="white", framealpha=0.97)

        # ── lower: marginals ──────────────────────────────────────────────
        ax = axes[1][col]
        Pkd = P.sum(axis=0); Pkd /= Pkd.sum() * (kdv_mW[1]-kdv_mW[0])
        Pqb = P.sum(axis=1); Pqb /= Pqb.sum() * (qbv_mW[1]-qbv_mW[0])

        l1 = ax.plot(kdv_mW, Pkd, color=C_TEAL, lw=2.0,
                     label=r"$P(K_d \mid \mathrm{data})$")[0]
        ax2 = ax.twiny()
        # twin top axis for Q_b
        l2 = ax2.plot(qbv_mW, Pqb / Pqb.max() * Pkd.max(),
                      color=C_CORAL, lw=2.0, ls="--",
                      label=r"$P(Q_b \mid \mathrm{data})$  (rescaled)")[0]
        ax2.set_xlim(qbv_mW[0], qbv_mW[-1])

        ax.set_xlabel(r"$K_d$  (mW m$^{-1}$ K$^{-1}$)", color=C_TEAL)
        ax.set_ylabel(r"$P(K_d)$", color=C_TEAL)
        ax.tick_params(axis="x", colors=C_TEAL)
        ax.tick_params(axis="y", colors=C_TEAL)
        ax.set_title(f"({chr(ord('c')+col)})  {name} marginal posteriors")
        ax2.set_xlabel(r"$Q_b$  (mW m$^{-2}$)", color=C_CORAL)
        ax2.tick_params(axis="x", colors=C_CORAL)
        ax2.spines["top"].set_color(C_CORAL)
        ax2.spines["top"].set_visible(True)
        ax.spines["bottom"].set_color(C_TEAL)
        ax.legend([l1, l2],
                  [r"$P(K_d \mid \mathrm{data})$",
                   r"$P(Q_b \mid \mathrm{data})$  (rescaled)"],
                  bbox_to_anchor=(1.0, -0.30), loc="upper right",
                  ncols=2, fontsize=FS_LEGEND, borderpad=0.6)
        ax.grid(color=C_GRID, lw=0.5)
        ax.set_axisbelow(True)
        for s in (ax.spines["left"], ax.spines["bottom"]):
            s.set_color(C_TEAL)

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
                    albedo=0.137, emissivity=0.95, Q_BASAL=0.015,
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
    gs  = fig.add_gridspec(2, 2, height_ratios=[1.15, 0.85],
                           hspace=0.46, wspace=0.32,
                           left=0.10, right=0.97, top=0.94, bottom=0.215)
    axes_full = [fig.add_subplot(gs[0, 0]), fig.add_subplot(gs[0, 1])]
    axes_zoom = [fig.add_subplot(gs[1, 0]), fig.add_subplot(gs[1, 1])]

    # ── run models and collect per-site data first ────────────────────────────
    # Use phase_a_results.json as the single authoritative source for the
    # Hayne K_d* -- this is the same file the manuscript text and Table 1
    # are built from, so the figure and the text cannot drift apart.
    _pa_path = _ROOT / "output" / "phase_a_results.json"
    d_auth = json.loads(_pa_path.read_text())

    site_data = {}
    for name, site_cfg in SITE_CFGS.items():
        kd_r  = d_auth[name]["kd_star"]              # Hayne retrieved K_d*
        print(f"  Running Hayne K_d*={kd_r*1e3:.2f}  for {name} ...", flush=True)
        z_h, T_h = run_profile(site_cfg, make_k_hayne(kd_r))
        print(f"  Running M&S model for {name} ...", flush=True)
        z_m, T_m = run_profile(site_cfg, make_k_ms())

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
        ax_f.text(0.97, site_cfg['MIN_DEPTH_CM'] + 2,
                  "borestem zone", transform=ax_f.get_yaxis_transform(),
                  ha="right", va="bottom", fontsize=FS_TICK - 1.5,
                  color=C_DIM, style="italic")

        fmt_axis(ax_f,
                 xlabel=r"$T$ (K)",
                 ylabel="Depth  (cm)" if col == 0 else "",
                 title=f"({col_labels[col]})  {site_cfg['label']}")
        ax_f.set_ylim(220, 0)
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

        # tight x-axis: span only the deep-region temperature range + margin
        mask_deep = z_h >= MIN_CM
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
    # fig_kd_sweep_v2 is superseded by the two-panel fig_kd_sweep() in
    # make_letter_unified_figs.py and is no longer generated.
    fig_lab_comparison(d, APPENDIX_FIGS / "fig_lab_comparison.pdf")
    # fig_cold_trap_depth is used by BOTH the letter (Fig 9) and the
    # appendix -- write both copies so neither goes stale.
    fig_cold_trap(d, LETTER_FIGS / "fig_cold_trap_depth.pdf")
    fig_cold_trap(d, APPENDIX_FIGS / "fig_cold_trap_depth.pdf")
    fig_posterior(APPENDIX_FIGS / "fig_kd_qb_posterior.pdf")
    print("Done.")

if __name__ == "__main__":
    main()
