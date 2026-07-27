"""Regenerate the GEDES-abstract figures at their TRUE printed size.

The extended abstract (deliverables/documents/abstract/) is A4 with a
170 mm (6.69 in) text width, narrower than the JGR_FULL = 7.48 in the
letter figures are designed for. Including a JGR-width PDF at a
``width=0.8\\linewidth`` fraction shrinks every font with it, so instead
this driver RE-RUNS the real generators with the canvas set to the size
the figure will actually print at -- fonts then render at 100% of their
intended point size. Data, styling, and the no-overlap guard are the
generators' own; nothing scientific is re-derived here.

Outputs go ONLY to deliverables/documents/abstract/figures/ (the
Overleaf bundle). The canonical copies in code/results/figures/ used by
the letter/guidebook/thesis are never touched.

Variants built (ALL single-column, ~3.3 in wide, for the two-column body):
  fig_context_map.pdf      single composite globe (mean-T over LOLA relief)
  fig_apollo_timeline.pdf  the letter's full-detail 4-probe figure
                           (traces + drift fit + windows), scaled to column
  fig_method.pdf           flux-anchored solver schematic (Step A/B/loop)
  fig_kd_sweep.pdf         RMSE-vs-K_d, legend inside the axes
  fig_profile_fit.pdf      subsurface T(z) fit: data vs Hayne & M&S models
                           (two site panels stacked; runs the solver)
  fig_robustness.pdf       bootstrap over contrast map, stacked

Run:  .venv/bin/python code/pipeline/figures/make_abstract_figures.py
"""
from __future__ import annotations

import json
import pathlib

import matplotlib.pyplot as plt

from lunar._bootstrap import find_repo_root

ROOT = find_repo_root()                       # .../code
# The abstract keeps its OWN self-contained figures dir (Overleaf-ready,
# no symlink) so its custom figures -- the three-orthographic-globe context
# map, the A4-sized timeline/sweep/robustness -- never collide with the
# letter's identically named figures in the shared top-level figures/.
# (The 2026-07-13 reorg had briefly symlinked this to ../../figures, which
# let the letter's 2D fig_context_map.pdf overwrite the abstract's globes.)
ABS_FIGS = ROOT.parent / "documents" / "gedes" / "abstract" / "figures"

ABSTRACT_W = 6.69                             # A4 text width (170 mm), inches


class _SizedFigure:
    """Context manager: force the next plt.figure/plt.subplots figsize."""

    def __init__(self, figsize):
        self.figsize = figsize

    def __enter__(self):
        self._figure, self._subplots = plt.figure, plt.subplots
        plt.figure = lambda *a, **k: self._figure(
            *a, **{**k, "figsize": self.figsize})
        plt.subplots = lambda *a, **k: self._subplots(
            *a, **{**k, "figsize": self.figsize})
        return self

    def __exit__(self, *exc):
        plt.figure, plt.subplots = self._figure, self._subplots


def _ortho_latlon(n):
    """Disk-pixel (lat, lon) and off-limb mask for a nearside orthographic
    projection centered on the sub-Earth point (0 deg, 0 deg)."""
    import numpy as np
    gy, gx = np.mgrid[0:n, 0:n].astype(float)
    x = (gx - (n - 1) / 2) / ((n - 1) / 2)
    y = -(gy - (n - 1) / 2) / ((n - 1) / 2)
    rho = np.hypot(x, y)
    inside = rho <= 1.0
    lat = np.degrees(np.arcsin(np.clip(y, -1, 1)))
    lon = np.degrees(np.arctan2(x, np.sqrt(np.clip(1 - rho ** 2, 0, 1))))
    return lat, lon, inside


def _sample_equirect(field, lat, lon):
    """Nearest-neighbor sample of an equirectangular field at (lat, lon)."""
    import numpy as np
    h, w = field.shape[:2]
    col = np.clip(((lon + 180) / 360 * (w - 1)).astype(int), 0, w - 1)
    row = np.clip(((90 - lat) / 180 * (h - 1)).astype(int), 0, h - 1)
    return field[row, col]


def _mean_surface_temp_by_lat():
    """Diurnal-MEAN skin temperature vs latitude, from the real solver.

    Runs the model's forward march (fast Hayne kernel) at a ladder of
    latitudes and averages the true skin temperature over one lunation,
    so the map layer is a genuine model output -- not an analytic
    stand-in. Cached to results/ so figure rebuilds are instant.
    Values are symmetric in latitude; nominal Hayne properties and
    equatorial Q_b are used (the skin mean is insensitive to K_d/Q_b).
    """
    import numpy as np
    cache = ROOT / "results" / "abstract_mean_surface_T.json"
    if cache.exists():
        d = json.loads(cache.read_text())
        return np.array(d["lat_deg"]), np.array(d["T_mean_K"])

    from lunar.config import HAYNE, GRID, DT_STEP, SITES
    from lunar.constants import Q_B_EQUATORIAL
    from lunar.grid import make_geometric_grid
    from lunar.solver import (solve_pixel, PixelInputs, standard_insolation,
                              periodic_time_grid)
    g = make_geometric_grid(**GRID)
    t = periodic_time_grid(DT_STEP)
    Ks, H, chi = HAYNE["K_S"], HAYNE["H"], HAYNE["CHI"]
    Kd = 0.0034                                   # nominal global value
    A = float(np.mean([SITES[s]["albedo"] for s in ("A15", "A17")]))
    lats = np.append(np.arange(0.0, 90.0, 5.0), 89.0)
    tmean = []
    for lat in lats:
        insol = standard_insolation(float(lat), t)
        out = solve_pixel(PixelInputs(
            grid=g, t=t, bc_mode="radiative", insolation=insol,
            albedo=A, emissivity=0.95, Q_b=Q_B_EQUATORIAL,
            n_lunations_spinup=80, spinup_tol_K=0.05, spinup_depth_m=0.15,
            hayne_params=(Ks, Kd, H, chi)))
        skin = out.T_surface if out.T_surface is not None else out.T[0]
        tmean.append(float(skin.mean()))
    cache.write_text(json.dumps(
        {"lat_deg": lats.tolist(), "T_mean_K": tmean, "albedo": A,
         "note": "diurnal-mean skin temperature vs |lat|, nominal Hayne "
                 "props, equatorial Q_b; from lunar.solver.solve_pixel"},
        indent=1))
    return lats, np.array(tmean)


def _load_lola_dem():
    """LOLA LDEM 4 ppd (1440x720), 16-bit LSB; height (m) = DN*0.5.

    Bundled real topography from PDS (same host as the Diviner data).
    Returns elevation in km relative to the 1737.4 km reference sphere.
    """
    import numpy as np
    p = ROOT / "data" / "lola" / "ldem_4.img"
    dn = np.fromfile(p, dtype="<i2").reshape(720, 1440)
    return dn * 0.5 / 1000.0                      # meters -> km


def build_context_map():
    """Figure 1 as ONE single-column orthographic nearside globe.

    A single composite 'Moon from Earth' disk sized for one text column
    (~3.3 in): the color is the modeled diurnal-mean surface temperature
    (from the solver) and the relief shading is real LOLA topography, so
    the one globe carries both the thermal field and the terrain that sets
    the two sites apart (Apollo 15 at the Hadley mare/highland margin,
    Apollo 17 in the Taurus-Littrow embayment).  Both boreholes are marked
    and named in the legend; callouts are avoided so nothing sits on the
    disk.  The full three-layer strip (albedo / temperature / topography)
    is kept in the thesis, which has room to span the page.
    """
    import numpy as np
    from matplotlib.patches import Circle
    from matplotlib.lines import Line2D
    from matplotlib.colors import LightSource, Normalize
    import matplotlib.cm as cm
    import make_context_map_figure as m
    from lunar.plotting.style import assert_no_overlap, C_GRID, C_CHAR

    n = 520
    lat, lon, inside = _ortho_latlon(n)

    # modeled diurnal-MEAN surface temperature (solver, latitude ladder);
    # mapped by |lat| -> warm equatorial band grading to cold poles
    lat_deg, tmean = _mean_surface_temp_by_lat()
    temp = np.interp(np.abs(lat), lat_deg, tmean)
    tvis = np.asarray(temp)[inside]
    vlo = float(np.floor(np.percentile(tvis, 6) / 10) * 10)
    vhi = float(np.ceil(tvis.max() / 10) * 10)
    tnorm, tcmap = Normalize(vmin=vlo, vmax=vhi), plt.get_cmap("RdYlBu_r")

    # COMPOSITE: hue = mean temperature, relief shading = LOLA topography
    dem_disk = _sample_equirect(_load_lola_dem(), lat, lon)
    ls = LightSource(azdeg=315, altdeg=45)
    trgb = tcmap(tnorm(np.asarray(temp)))[..., :3]
    shaded = ls.shade_rgb(trgb, dem_disk, blend_mode="soft", vert_exag=0.6)
    temp_rgba = np.dstack([shaded, inside.astype(float)])
    temp_rgba[~inside] = [1.0, 1.0, 1.0, 0.0]

    fig = plt.figure(figsize=(3.32, 3.86))
    ax = fig.add_axes([0.02, 0.205, 0.96, 0.72])
    ax.imshow(temp_rgba, extent=(-1, 1, -1, 1), origin="upper",
              interpolation="bilinear", zorder=1)

    g = dict(color="0.85", lw=0.4, alpha=0.5, zorder=2)
    tt = np.linspace(-90, 90, 160)
    for L in (-30, 0, 30, 60):
        ax.plot(np.cos(np.radians(L)) * np.sin(np.radians(tt)),
                np.full_like(tt, np.sin(np.radians(L))), **g)
    for M in (-60, -30, 0, 30, 60):
        ax.plot(np.cos(np.radians(tt)) * np.sin(np.radians(M)),
                np.sin(np.radians(tt)), **g)
    ax.add_patch(Circle((0, 0), 1.0, fill=False, ec=C_GRID, lw=1.0, zorder=5))
    for name, s in m.SITES.items():
        la, lo = np.radians(s["lat"]), np.radians(s["lon"])
        px, py = np.cos(la) * np.sin(lo), np.sin(la)
        # dark halo underlay so the coral A17 marker stays visible over the
        # warm (red) side of the temperature globe, then white-edged dot
        ax.plot(px, py, "o", color=C_CHAR, ms=11, mec="none", zorder=6)
        ax.plot(px, py, "o", color=m.SITE_COLOR[name], ms=7.5, mec="white",
                mew=1.3, zorder=6.1)
    ax.set_xlim(-1.08, 1.08)
    ax.set_ylim(-1.12, 1.12)
    ax.set_aspect("equal")
    ax.axis("off")
    ax.set_title("Nearside: mean surface $T$ over LOLA relief",
                 fontsize=9.2, pad=2)

    imB = cm.ScalarMappable(norm=tnorm, cmap=tcmap)
    imB.set_array([])
    cax = fig.add_axes([0.17, 0.145, 0.66, 0.032])
    cb = fig.colorbar(imB, cax=cax, orientation="horizontal", extend="min")
    cb.set_label("mean surface temperature (K)", fontsize=8, labelpad=1)
    cb.ax.tick_params(labelsize=7)

    handles = [Line2D([0], [0], marker="o", color="none", markersize=7,
                      markerfacecolor=m.SITE_COLOR[s], mec="white", mew=1.3,
                      label=m.SITES[s]["label"]) for s in ("A15", "A17")]
    fig.legend(handles=handles, loc="center", ncols=2, frameon=False,
               fontsize=8.5, bbox_to_anchor=(0.5, 0.045),
               handletextpad=0.4, columnspacing=1.4)

    fig.canvas.draw()
    assert_no_overlap(ax)
    out = ABS_FIGS / "fig_context_map.pdf"
    fig.savefig(out)
    plt.close(fig)
    print(f"  -> {out} (single composite globe; T range "
          f"{vlo:.0f}-{vhi:.0f} K)")


def build_timeline():
    """Full four-probe HFE timeline -- the letter's original, information-dense
    figure: for every probe (A15-P1/P2, A17-P1/P2) each sensor's raw
    temperature trace (depth-colored; borestem sensors a pale grey underlay)
    with the deepest-sensor drift-slope fit dashed, above a per-sensor Gantt
    strip of the selected stability window inside the full archived record.

    It is a wide, tall, information-dense figure (~8.5 x 9.5 in), so in the
    two-column abstract it is placed as a FULL-WIDTH float (spanning both
    columns) rather than shrunk into a single 3.3-in column, which would
    render its 8 pt sensor labels at ~3 pt.  Rendered from live data by the
    letter timeline generator into the abstract's figures/ and copied to the
    name the abstract includes; the per-site halves it also emits are the
    thesis's, not the abstract's, so they are removed.
    """
    import shutil
    import make_apollo_timeline_letter as m
    m.OUT = ABS_FIGS
    m.main()                          # writes fig_apollo_timeline_probes.pdf (+ halves)
    shutil.copyfile(ABS_FIGS / "fig_apollo_timeline_probes.pdf",
                    ABS_FIGS / "fig_apollo_timeline.pdf")
    for extra in ("fig_apollo_timeline_probes.pdf",
                  "fig_apollo_timeline_a15.pdf", "fig_apollo_timeline_a17.pdf"):
        (ABS_FIGS / extra).unlink(missing_ok=True)
    print("  -> fig_apollo_timeline.pdf (full-detail 4-probe, full-width float)")


def build_kd_sweep():
    """Single-COLUMN RMSE-vs-K_d retrieval figure (3.4 in wide) so it sits
    INSIDE one column of the two-column body rather than spanning both.

    Drawn self-contained at column width: the letter's full-width
    fig_kd_sweep carries a legend title plus four long CI labels that
    cannot fit a 3.4-in axes, so here the CI is carried by the horizontal
    error bars and Table 1, and the legend is a compact two-row strip
    below the axes (grown by legend_below so it never touches the data).
    Every value is read from the certified kd_retrieval_results.json.
    """
    import numpy as np
    from scipy.interpolate import PchipInterpolator
    from lunar.plotting.style import (C_A15, C_A17, C_HAYNE, C_GRID,
                                      fmt_axis, assert_no_overlap)
    import make_letter_figures as m            # for the certified JSON path

    d = json.loads(m.PHASE_A.read_text())

    fig, ax = plt.subplots(figsize=(3.40, 2.72))
    fig.subplots_adjust(left=0.165, right=0.965, top=0.965, bottom=0.165)

    # the abstract compares only against Hayne's global value (the sole
    # deep-K reference named in the prose and Table 1), so a single
    # reference vertical -- drawn first so the retrieval curves sit on top
    ax.axvline(3.4, color=C_HAYNE, ls="--", lw=1.1, alpha=0.65, zorder=1,
               label=r"Hayne 2017 global  $3.4$")

    for name, color in [("A15", C_A15), ("A17", C_A17)]:
        s = d[name]
        kdg = np.array(s["kd_grid"]) * 1e3
        rmse = np.array(s["rmse_curve"])
        cs = PchipInterpolator(kdg, rmse)       # shape-preserving (see letter)
        kdf = np.linspace(kdg[0], kdg[-1], 600)
        b = s["bootstrap"]
        # 1σ (16–84 percentile) so the bar reaches the same place as the
        # ^{+..}_{-..} statistical error quoted in the text (Eq. 2); the wider
        # 95% interval is kept for Table 1 only.
        lo, hi = np.percentile(np.array(b["samples"]) * 1e3, [16, 84])
        kd_star, rmse_star = s["kd_star"] * 1e3, s["rmse_star"]
        ax.plot(kdf, cs(kdf), "-", color=color, lw=2.0, zorder=3,
                label=fr"{name}  $K_d^{{*}}\!=\!{kd_star:.2f}$")
        ax.plot(kdg, rmse, "o", color=color, ms=2.2, mec="white", mew=0.4,
                alpha=0.5, zorder=4)
        ax.errorbar(kd_star, rmse_star,
                    xerr=[[kd_star - lo], [hi - kd_star]],
                    fmt="*", color=color, ecolor=color, elinewidth=1.3,
                    capsize=3.5, capthick=1.3, ms=15, mec="white", mew=1.1,
                    zorder=6)

    fmt_axis(ax, xlabel=r"$K_d$  (mW m$^{-1}$ K$^{-1}$)",
             ylabel=r"Deep-sensor RMSE  (K)", title="")
    ax.set_xlim(0, 16)
    ax.set_ylim(0, 3.15)         # headroom so the top-center band clears both curves
    ax.grid(which="major", color=C_GRID, lw=0.4, alpha=0.7)
    ax.set_axisbelow(True)

    # legend INSIDE the axes: with the raised y-limit the top-center band
    # (above both misfit bowls, below the curves' rising branches) is empty,
    # so it holds the legend without covering data -- freeing the below-axes
    # strip for more text.  Guarded by assert_no_overlap.
    h, l = ax.get_legend_handles_labels()
    order = [1, 2, 0]                             # A15, A17, then Hayne
    h, l = [h[i] for i in order], [l[i] for i in order]
    ax.legend(h, l, loc="upper center", bbox_to_anchor=(0.50, 0.99), ncols=1,
              frameon=True, edgecolor=C_GRID, framealpha=0.96, fontsize=8.2,
              handlelength=1.7, labelspacing=0.35, borderpad=0.5)
    fig.canvas.draw()
    assert_no_overlap(ax)                         # legend must not touch data
    fig.savefig(ABS_FIGS / "fig_kd_sweep.pdf")
    plt.close(fig)
    print(f"  -> fig_kd_sweep.pdf (single-column, legend inside)")


def build_robustness():
    """Figure 4 = bootstrap (a) over the annotated 2-D contrast map (b),
    STACKED into a single column (~3.35 in wide) so it sits inside one
    column of the two-column body rather than spanning both.

    Every map element is explained by a small text box INSIDE the panel
    rather than by a legend the reader must decode: the dashed 2/4/6-sigma
    significance contours, the Saito et al. reanalysis point (the
    independent flux study), the Langseth flux point, and the MCMC
    posterior.  Callout positions are hand-measured empty zones and the
    render is inspected; the style guard additionally checks panel (a).
    """
    import numpy as np
    from matplotlib.colors import TwoSlopeNorm
    from scipy.interpolate import PchipInterpolator
    from scipy.ndimage import gaussian_filter
    from lunar.plotting.style import (WARM_DIVERGE, C_CHAR, C_TEAL, C_GRID,
                                      C_A15, C_A17, C_FOREST, fmt_axis,
                                      assert_no_overlap)
    import make_results_figures as m

    root = m._ROOT
    d = json.loads(m.RESULTS.read_text())

    fig = plt.figure(figsize=(3.35, 5.45))
    gs = fig.add_gridspec(2, 1, height_ratios=[1.0, 1.24],
                          left=0.165, right=0.88, top=0.955, bottom=0.068,
                          hspace=0.58)   # clear gap: (a) x-label vs (b) title
    axb = fig.add_subplot(gs[0])
    gsm = gs[1].subgridspec(1, 2, width_ratios=[1.0, 0.045], wspace=0.06)
    axm = fig.add_subplot(gsm[0])
    cax = fig.add_subplot(gsm[1])
    NOTE = dict(fontsize=6.4, color=C_CHAR, ha="center", va="center",
                bbox=dict(boxstyle="round,pad=0.22", fc="white",
                          ec=C_GRID, lw=0.7, alpha=0.95), zorder=9)

    # ---- (a) per-site bootstrap distributions -----------------------------
    boot15 = np.array(d["A15"]["bootstrap"]["samples"]) * 1e3
    boot17 = np.array(d["A17"]["bootstrap"]["samples"]) * 1e3
    m15, l15, h15 = np.percentile(boot15, [50, 2.5, 97.5])
    m17, l17, h17 = np.percentile(boot17, [50, 2.5, 97.5])
    lo = min(boot15.min(), 3.0) - 0.5
    hi = boot17.max() + 0.4
    bins = np.linspace(lo, hi, 42)
    axb.hist(boot15, bins=bins, color=C_A15, alpha=0.55, edgecolor=C_A15,
             lw=0.3, label="Apollo 15")
    axb.hist(boot17, bins=bins, color=C_A17, alpha=0.55, edgecolor=C_A17,
             lw=0.3, label="Apollo 17")
    axb.plot([3.4, 3.4], [0, 250], color=C_CHAR, ls="--", lw=1.0, alpha=0.6)
    axb.annotate("Hayne 2017\nglobal 3.4", xy=(3.42, 252),
                 xytext=(3.05, 330), **NOTE,
                 arrowprops=dict(arrowstyle="-", color=C_CHAR, lw=0.7))
    axb.set_ylim(0, 400)
    axb.set_xlim(lo, hi)
    fmt_axis(axb, xlabel=r"$K_d^{*}$ (mW m$^{-1}$ K$^{-1}$)",
             ylabel="bootstrap count",
             title=r"(a) bootstrap: per-site $K_d^{*}$")
    axb.legend(fontsize=7.5, frameon=True, edgecolor=C_GRID,
               loc="upper right", handlelength=1.1, labelspacing=0.4,
               borderpad=0.4)

    # ---- (b) annotated contrast map ---------------------------------------
    dg = json.loads((root / "results" / "qb_degeneracy.json").read_text())
    qb15 = np.array([r["qb_mW"] for r in dg["sites"]["A15"]])
    kd15 = np.array([r["kd_star_mW"] for r in dg["sites"]["A15"]])
    qb17 = np.array([r["qb_mW"] for r in dg["sites"]["A17"]])
    kd17 = np.array([r["kd_star_mW"] for r in dg["sites"]["A17"]])
    k15, k17 = PchipInterpolator(qb15, kd15), PchipInterpolator(qb17, kd17)
    bs = d["contrast_bootstrap"]
    sig = (bs["ci_hi"] - bs["ci_lo"]) * 1e3 / (2 * 1.96)
    x = np.linspace(qb15[0], qb15[-1], 120)
    y = np.linspace(qb17[0], qb17[-1], 120)
    contrast = k17(y)[:, None] - k15(x)[None, :]
    vmax = float(np.ceil(contrast.max()))
    norm = TwoSlopeNorm(vmin=min(-0.15 * vmax, float(contrast.min())),
                        vcenter=0, vmax=vmax)
    im = axm.pcolormesh(x, y, contrast, cmap=WARM_DIVERGE, norm=norm,
                        shading="gouraud", rasterized=True, zorder=1)
    cb = fig.colorbar(im, cax=cax)
    cb.set_label(r"$\Delta K_d^{*}$ = A17 $-$ A15 (mW m$^{-1}$ K$^{-1}$)",
                 fontsize=8)
    cb.ax.tick_params(labelsize=7)

    # significance contours (restored) + the zero line, labelled inline
    cs = axm.contour(x, y, contrast / sig, levels=[2, 4, 6], colors=C_CHAR,
                     linewidths=0.8, linestyles="--", alpha=0.6, zorder=2.3)
    axm.clabel(cs, fmt=lambda v: f"{int(v)}$\\sigma$", fontsize=7,
               inline=True, inline_spacing=5)
    c0 = axm.contour(x, y, contrast, levels=[0.0], colors=C_CHAR,
                     linewidths=1.6, zorder=3)

    # MCMC posterior: filled 68/95% credible regions, labelled on-line
    ch = np.load(root / "results" / "bayesian_chains.npz")
    rng = np.random.default_rng(0)
    nch = min(ch["a15_kd"].size, ch["a17_kd"].size)
    H2, xe, ye = np.histogram2d(
        ch["a15_qb"][rng.choice(ch["a15_kd"].size, nch, replace=False)],
        ch["a17_qb"][rng.choice(ch["a17_kd"].size, nch, replace=False)],
        bins=60, range=[[x[0], x[-1]], [y[0], y[-1]]])
    Hs = gaussian_filter(H2, 1.8)
    hf = np.sort(Hs.ravel())[::-1]
    cmass = np.cumsum(hf) / hf.sum()
    l68, l95 = hf[np.searchsorted(cmass, 0.68)], hf[np.searchsorted(cmass, 0.95)]
    xc, yc = 0.5 * (xe[:-1] + xe[1:]), 0.5 * (ye[:-1] + ye[1:])
    XC, YC = np.meshgrid(xc, yc)
    axm.contourf(XC, YC, Hs.T, levels=[l95, Hs.max()], colors=[C_TEAL],
                 alpha=0.20, zorder=3.1)
    axm.contourf(XC, YC, Hs.T, levels=[l68, Hs.max()], colors=[C_TEAL],
                 alpha=0.22, zorder=3.2)
    cl = axm.contour(XC, YC, Hs.T, levels=[l95, l68], colors="white",
                     linewidths=0.8, alpha=0.9, zorder=3.3)
    axm.clabel(cl, fmt={l95: "95%", l68: "68%"}, fontsize=6.5,
               inline=True, inline_spacing=2, colors=C_CHAR)
    st = json.loads((root / "results"
                     / "bayesian_crosscheck_samples.json").read_text())
    med15, med17 = float(st["A15"]["qb_q50"]), float(st["A17"]["qb_q50"])
    axm.plot(med15, med17, "*", ms=12, color=C_TEAL, mec="white", mew=1.1,
             zorder=6)

    # reference points
    axm.plot(21, 16, "o", color=C_CHAR, ms=8, mec="white", mew=1.3, zorder=6)
    axm.plot(14.7, 16, "s", color=C_FOREST, ms=9, mec="white", mew=1.3,
             zorder=6)

    # in-panel text-box callouts (measured empty zones; render-checked)
    axm.annotate("Langseth et al.\n(1976) fluxes", xy=(21.2, 16.2),
                 xytext=(23.1, 18.2), **NOTE,
                 arrowprops=dict(arrowstyle="-", color=C_CHAR, lw=0.7))
    axm.annotate("Saito et al.\nreanalysis", xy=(14.6, 16.25),
                 xytext=(12.4, 18.8), **NOTE,
                 arrowprops=dict(arrowstyle="-", color=C_FOREST, lw=0.7))
    axm.annotate("$\\Delta = 0$:\nno difference", xy=(10.35, 9.8),
                 xytext=(12.6, 8.6), **NOTE,
                 arrowprops=dict(arrowstyle="-", color=C_CHAR, lw=0.7))
    axm.annotate("MCMC: most likely\nfluxes (star = median)",
                 xy=(19.9, 11.0), xytext=(22.7, 9.0), **NOTE,
                 arrowprops=dict(arrowstyle="-", color=C_TEAL, lw=0.8))

    fmt_axis(axm, xlabel=r"Apollo 15 basal flux $Q_b$ (mW m$^{-2}$)",
             ylabel=r"Apollo 17 basal flux $Q_b$ (mW m$^{-2}$)",
             title="(b) contrast: is Apollo 17 more conductive?")
    axm.set_xlim(x[0], x[-1])
    axm.set_ylim(y[0], y[-1])

    fig.canvas.draw()
    assert_no_overlap(axb)
    print(f"    bootstrap A15 {m15:.2f} [{l15:.2f}, {h15:.2f}]  "
          f"A17 {m17:.2f} [{l17:.2f}, {h17:.2f}];  annotated map: Langseth "
          f"{float(k17(16)-k15(21)):.2f} ({float((k17(16)-k15(21))/sig):.1f} sigma), "
          f"Saito {float(k17(16)-k15(14.7)):.2f}")
    fig.savefig(ABS_FIGS / "fig_robustness.pdf", dpi=400)
    plt.close(fig)


def build_profile_fit():
    """Single-column subsurface T(z) fit -- the actual result the RMSE bowl
    only summarizes.  Annual-mean temperature vs depth at each site with the
    observations (deep = filled, used; shallow = open, borestem-excluded),
    the Hayne (2017) global smooth-exponential model, and the Martinez &
    Siegler (2021) T,rho-dependent model, over the shaded borestem zone.
    The two published global forms bracket-but-miss the deep sensors, which
    is what the per-site retrieval corrects, and their agreement shows the
    contrast is not an artifact of one conductivity form.  Two site panels
    STACKED for one column; every value from lunar.* at build time.
    """
    import numpy as np
    from lunar.plotting.style import (C_HAYNE, C_MS, C_CHAR, C_DIM,
                                      fmt_axis, legend_below, assert_no_overlap,
                                      FS_LEGEND, FS_TICK)
    import make_letter_figures as m

    BORE_FILL, BORE_EDGE = "#F4D6CB", "#B85B3A"
    fig, axes = plt.subplots(2, 1, figsize=(3.35, 5.0))
    fig.subplots_adjust(left=0.155, right=0.965, top=0.955, bottom=0.10,
                        hspace=0.36)

    for ax, name in zip(axes, ["A15", "A17"]):
        cfg = m.SITES[name]
        obs = m.extract_sensor_stability(cfg["mission"], cfg["MIN_DEPTH_CM"])
        z_obs = np.array(obs["depth_cm_all"]) / 100.0
        T_obs = np.array(obs["T_eq_all"])
        T_std = np.array(obs["T_std_all"])
        deep = np.array(obs["deep_mask"], dtype=bool)
        z_mid, T_mat_H, _ = m.run_pixel(cfg, kfunc=m.k_func_hayne(m.HAYNE["K_D"]))
        z_mid, T_mat_MS, _ = m.run_pixel(cfg, kfunc=m.k_func_ms())
        T_H, T_MS = T_mat_H.mean(axis=1), T_mat_MS.mean(axis=1)

        ax.axhspan(0, 80, color=BORE_FILL, alpha=0.55, zorder=0)
        ax.axhline(80, color=BORE_EDGE, lw=0.7, ls=(0, (3, 2)), alpha=0.6,
                   zorder=1)
        ax.plot(T_H, z_mid * 100, "-", color=C_HAYNE, lw=1.8, zorder=2,
                label="Hayne (2017) global 3.4")
        ax.plot(T_MS, z_mid * 100, "--", color=C_MS, lw=1.8, zorder=2,
                label="Martínez & Siegler (2021)")
        ax.errorbar(T_obs[deep], z_obs[deep] * 100, xerr=T_std[deep], fmt="o",
                    color=C_CHAR, mec="white", mew=0.7, markersize=5.5,
                    capsize=2, zorder=3,
                    label="deep sensor (used)" if name == "A15" else None)
        ax.errorbar(T_obs[~deep], z_obs[~deep] * 100, xerr=T_std[~deep],
                    fmt="o", mfc="none", color=C_DIM, mew=0.9, markersize=5.5,
                    capsize=2, zorder=3,
                    label="shallow (excluded)" if name == "A15" else None)

        fmt_axis(ax, xlabel=r"$T$ (K)", ylabel="Depth (cm)",
                 title=f"({['a', 'b'][['A15', 'A17'].index(name)]})  "
                       f"{cfg['label']}")
        ax.set_ylim(250, 0)
        shown = z_mid <= 2.50
        T_deepest = max(float(T_H[shown].max()), float(T_MS[shown].max()))
        ax.set_xlim(float(T_obs.min()) - 3.0,
                    max(float(T_obs.max()), T_deepest) + 1.5)
        ax.text(0.965, 0.95, "borestem\n$z<80$ cm", transform=ax.transAxes,
                fontsize=FS_TICK - 1.0, color=C_CHAR, ha="right", va="top",
                bbox=dict(boxstyle="round,pad=0.26", facecolor="white",
                          edgecolor=BORE_EDGE, lw=0.7, alpha=0.92), zorder=5)

    h, l = axes[0].get_legend_handles_labels()
    legend_below(fig, h, l, ncols=2, fontsize=FS_LEGEND - 0.7, handlelength=1.7,
                 columnspacing=1.3)
    fig.canvas.draw()
    for ax in axes:
        assert_no_overlap(ax)
    fig.savefig(ABS_FIGS / "fig_profile_fit.pdf")
    plt.close(fig)
    print("  -> fig_profile_fit.pdf (subsurface T(z) fit, stacked)")


def build_method_schematic():
    """Single-column schematic of the flux-anchored solver (the method).

    A downward spine: Step A time-steps ONLY the diurnal skin and reads the
    cycle-mean at the anchor; Step B reconstructs the deep column by
    integrating the closure ODE from the anchor down; the outer loop repeats
    until the anchor temperature stops drifting.  Numbers are the certified
    inputs (anchor 0.55 m, tol 5 mK, ~4 cycles).
    """
    from matplotlib.patches import FancyBboxPatch
    from lunar.plotting.style import C_CHAR, C_DIM, C_TEAL, C_FOREST

    fig, ax = plt.subplots(figsize=(3.35, 2.82))
    ax.set_xlim(0, 1)
    ax.set_ylim(0.20, 0.995)   # trim the empty band below the last box so the
    ax.axis("off")             # tight-bbox crop doesn't leave a caption gap

    boxes = [
        ("Step A — skin forward-solve", C_TEAL,
         "time-step the top ${\\sim}0.7$ m only\n"
         "(Crank–Nicolson + Newton surface),\n"
         r"read cycle-mean $\langle T\rangle$ at $z_0=0.55$ m"),
        ("Step B — closure reconstruction", C_TEAL, None),   # placed specially
        ("Converged periodic steady state", C_FOREST,
         "repeat until anchor drift $<5$ mK\n"
         "(${\\sim}4$ cycles; ${\\sim}2500\\times$ faster than brute force)"),
    ]
    x0, BW = 0.055, 0.685
    BH = [0.215, 0.255, 0.150]
    gap = 0.075
    y = 0.985
    centers = []
    for idx, ((title, edge, body), bh) in enumerate(zip(boxes, BH)):
        y -= bh
        ax.add_patch(FancyBboxPatch((x0, y), BW, bh,
                     boxstyle="round,pad=0.012", facecolor="white",
                     edgecolor=edge, linewidth=1.6, zorder=3))
        cx = x0 + BW / 2
        ax.text(cx, y + bh - 0.033, title, ha="center", va="center",
                fontsize=8.2, fontweight="bold", color=C_CHAR, zorder=4)
        if idx == 1:                       # Step B: equation over caption
            ax.text(cx, y + bh * 0.50,
                    r"$\dfrac{d\langle T\rangle}{dz}"
                    r"=\dfrac{Q_b-u_{\rm rect}}{K(\langle T\rangle,z)}$",
                    ha="center", va="center", fontsize=9.0, color=C_CHAR,
                    zorder=4)
            ax.text(cx, y + 0.030,
                    "integrate downward from the\nanchor to 5 m (RK2)",
                    ha="center", va="center", fontsize=7.0, color=C_DIM,
                    linespacing=1.3, zorder=4)
        else:
            ax.text(cx, y + (bh - 0.055) / 2, body, ha="center", va="center",
                    fontsize=7.0, color=C_DIM, linespacing=1.4, zorder=4)
        centers.append((cx, y, y + bh))
        y -= gap

    arrow = dict(arrowstyle="-|>", color=C_CHAR, lw=1.4, mutation_scale=12,
                 shrinkA=0, shrinkB=0)
    for i in range(len(centers) - 1):
        cx = centers[i][0]
        ax.annotate("", xy=(cx, centers[i + 1][2] + 0.006),
                    xytext=(cx, centers[i][1] - 0.006), arrowprops=arrow,
                    zorder=2)
    # loop-back channel on the right: converged -> Step A
    xr, xc = x0 + BW + 0.014, x0 + BW + 0.085
    yconv = (centers[2][1] + centers[2][2]) / 2
    yA = (centers[0][1] + centers[0][2]) / 2
    ax.plot([xr, xc], [yconv, yconv], color=C_CHAR, lw=1.4,
            solid_capstyle="round", zorder=2)
    ax.plot([xc, xc], [yconv, yA], color=C_CHAR, lw=1.4,
            solid_capstyle="round", zorder=2)
    ax.annotate("", xy=(xr, yA), xytext=(xc, yA), arrowprops=arrow, zorder=2)
    ax.text(xc + 0.012, (yconv + yA) / 2, "next\ncycle", fontsize=6.6,
            color=C_DIM, ha="left", va="center", linespacing=1.2, zorder=4)

    fig.subplots_adjust(left=0.005, right=0.995, top=0.995, bottom=0.005)
    fig.savefig(ABS_FIGS / "fig_method.pdf")
    plt.close(fig)
    print("  -> fig_method.pdf (flux-anchored solver schematic)")


def main():
    ABS_FIGS.mkdir(parents=True, exist_ok=True)
    print("Rebuilding abstract figures as single-column (~3.3 in wide) "
          f"floats -> {ABS_FIGS}")
    build_context_map()
    build_method_schematic()
    build_profile_fit()
    build_timeline()
    build_kd_sweep()
    build_robustness()
    print("Done.")


if __name__ == "__main__":
    main()
