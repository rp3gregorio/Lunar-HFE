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

Variants built:
  fig_context_map.pdf      same layout, 6.69 x 5.3 in
  fig_apollo_timeline.pdf  the two DEEPEST probes only (one per site,
                           the ones whose OLS slope the caption quotes),
                           on a page ~55% the original height
  fig_kd_sweep.pdf         same layout, 6.69 x 3.7 in
  fig_robustness.pdf       same layout, 6.69 x 5.7 in

Run:  .venv/bin/python code/pipeline/figures/make_abstract_figures.py
"""
from __future__ import annotations

import json
import pathlib

import matplotlib.pyplot as plt

from lunar._bootstrap import find_repo_root

ROOT = find_repo_root()                       # .../code
ABS_FIGS = (ROOT.parent / "deliverables" / "documents" / "abstract"
            / "figures")

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
    """Figure 1 as THREE orthographic nearside globes in a row.

    The same 'Moon from Earth' nearside disk, shown as three data layers
    so the figure reads as a compact strip: (a) Clementine albedo mosaic,
    (b) modeled diurnal-mean surface temperature (from the solver), and
    (c) LOLA topography (real DEM). Both boreholes are marked on every
    globe (named once in the shared legend), and callouts are avoided so
    nothing sits on the small disks.
    """
    import numpy as np
    from matplotlib.patches import Circle
    from matplotlib.lines import Line2D
    import make_context_map_figure as m
    from lunar.plotting.style import assert_no_overlap, C_GRID

    n = 460
    lat, lon, inside = _ortho_latlon(n)

    def masked(field_disk):
        return np.ma.array(field_disk, mask=~inside)

    # (a) albedo mosaic -> RGBA disk
    img = m.load_moon()
    samp = _sample_equirect(img, lat, lon)
    if samp.dtype.kind in "ui":
        samp = samp / 255.0
    rgb = (np.repeat(samp[..., None], 3, axis=2) if samp.ndim == 2
           else samp[..., :3].astype(float))
    if rgb.max() > 1.0:
        rgb = rgb / 255.0
    albedo_rgba = np.dstack([rgb, inside.astype(float)])
    albedo_rgba[~inside] = [1.0, 1.0, 1.0, 0.0]

    # (b) modeled diurnal-MEAN surface temperature. Computed by the real
    # solver at a latitude ladder (cached) and mapped by |lat|, so it is
    # a latitude-only field: a warm equatorial band grading to cold poles
    # -- the layer whose color scale reveals cold vs warm (unlike the
    # noon snapshot, which crushed everything but the sub-solar spot).
    lat_deg, tmean = _mean_surface_temp_by_lat()
    temp = np.interp(np.abs(lat), lat_deg, tmean)

    # (c) LOLA topography (real DEM)
    elev = masked(_sample_equirect(_load_lola_dem(), lat, lon))

    fig, axes = plt.subplots(1, 3, figsize=(ABSTRACT_W, 3.35))
    fig.subplots_adjust(left=0.01, right=0.99, top=0.90, bottom=0.24,
                        wspace=0.08)

    def decorate(ax):
        """graticule + limb + site markers, shared by all three globes."""
        g = dict(color="0.85", lw=0.4, alpha=0.5, zorder=2)
        t = np.linspace(-90, 90, 160)
        for L in (-30, 0, 30, 60):
            ax.plot(np.cos(np.radians(L)) * np.sin(np.radians(t)),
                    np.full_like(t, np.sin(np.radians(L))), **g)
        for M in (-60, -30, 0, 30, 60):
            ax.plot(np.cos(np.radians(t)) * np.sin(np.radians(M)),
                    np.sin(np.radians(t)), **g)
        ax.add_patch(Circle((0, 0), 1.0, fill=False, ec=C_GRID, lw=1.0,
                            zorder=5))
        for name, s in m.SITES.items():
            la, lo = np.radians(s["lat"]), np.radians(s["lon"])
            ax.plot(np.cos(la) * np.sin(lo), np.sin(la), "o",
                    color=m.SITE_COLOR[name], ms=7, mec="white", mew=1.3,
                    zorder=6)
        ax.set_xlim(-1.08, 1.08)
        ax.set_ylim(-1.12, 1.12)
        ax.set_aspect("equal")
        ax.axis("off")

    axA, axB, axC = axes
    axA.imshow(albedo_rgba, extent=(-1, 1, -1, 1), origin="upper",
               interpolation="bilinear", zorder=1)
    # clip the low end to a percentile so the equator->mid-latitude
    # gradient spreads across the colormap (the tiny polar caps saturate
    # to the coldest blue) -- the colorbar still labels true values
    from matplotlib.colors import LightSource, Normalize
    import matplotlib.cm as cm
    tvis = np.asarray(temp)[inside]
    vlo = float(np.floor(np.percentile(tvis, 6) / 10) * 10)
    vhi = float(np.ceil(tvis.max() / 10) * 10)
    tnorm, tcmap = Normalize(vmin=vlo, vmax=vhi), plt.get_cmap("RdYlBu_r")
    # COMPOSITE: color = modeled mean temperature, relief shading = LOLA
    # topography -- every crater shows as shaded relief while the hue
    # carries the (latitude) temperature field.
    dem_disk = _sample_equirect(_load_lola_dem(), lat, lon)
    ls = LightSource(azdeg=315, altdeg=45)
    trgb = tcmap(tnorm(np.asarray(temp)))[..., :3]
    shaded = ls.shade_rgb(trgb, dem_disk, blend_mode="soft", vert_exag=0.6)
    temp_rgba = np.dstack([shaded, inside.astype(float)])
    temp_rgba[~inside] = [1.0, 1.0, 1.0, 0.0]
    axB.imshow(temp_rgba, extent=(-1, 1, -1, 1), origin="upper",
               interpolation="bilinear", zorder=1)
    imB = cm.ScalarMappable(norm=tnorm, cmap=tcmap)   # for the colorbar
    imB.set_array([])
    imC = axC.imshow(elev, extent=(-1, 1, -1, 1), origin="upper",
                     cmap="gist_earth", interpolation="bilinear", zorder=1)
    for ax, title in ((axA, "(a) albedo (Clementine)"),
                      (axB, "(b) mean surface temperature"),
                      (axC, "(c) topography (LOLA)")):
        decorate(ax)
        ax.set_title(title, fontsize=9.5, pad=3)

    # slim colorbars on dedicated axes at ONE shared height, so (b) and
    # (c) line up (per-axis fig.colorbar would stagger them)
    cbar_y, cbar_h = 0.115, 0.038
    for im, ax, label, ext in ((imB, axB, "mean T (K)", "min"),
                               (imC, axC, "elevation (km)", "neither")):
        pos = ax.get_position()
        cax = fig.add_axes([pos.x0 + 0.035, cbar_y, pos.width - 0.07, cbar_h])
        cb = fig.colorbar(im, cax=cax, orientation="horizontal", extend=ext)
        cb.set_label(label, fontsize=8, labelpad=1)
        cb.ax.tick_params(labelsize=7)

    # site legend tucked under panel (a), which has no colorbar
    posA = axA.get_position()
    handles = [Line2D([0], [0], marker="o", color="none", markersize=7,
                      markerfacecolor=m.SITE_COLOR[s], mec="white", mew=1.3,
                      label=m.SITES[s]["label"]) for s in ("A15", "A17")]
    fig.legend(handles=handles, loc="center", ncols=1, frameon=False,
               fontsize=8.5, bbox_to_anchor=(posA.x0 + posA.width / 2, 0.11),
               handletextpad=0.4, labelspacing=0.5)

    fig.canvas.draw()
    for ax in axes:
        assert_no_overlap(ax)
    out = ABS_FIGS / "fig_context_map.pdf"
    fig.savefig(out)
    plt.close(fig)
    print(f"  -> {out} (albedo/mean-T/LOLA; T range "
          f"{vlo:.0f}-{vhi:.0f} K)")


def build_timeline():
    import make_apollo_timeline_letter as m
    m.OUT = ABS_FIGS
    # Keep the deepest probe of each site (the sensors the abstract's
    # caption talks about) and lift the A17 block into the vacated A15
    # probe-2 slot; then crop the page below the second gantt strip.
    b15, b17 = m._BLOCKS[0], dict(m._BLOCKS[2])
    shift = b17["upper"][0] - m._BLOCKS[1]["upper"][0]   # 312.2 - 181.1
    b17["upper"] = tuple(y - shift for y in b17["upper"])
    b17["gantt"] = tuple(y - shift for y in b17["gantt"])
    old_blocks, old_h = m._BLOCKS, m._PAGE_H
    m._BLOCKS = [b15, b17]
    m._PAGE_H = b17["gantt"][1] + 75.0        # room for legend row
    try:
        m.main()
    finally:
        m._BLOCKS, m._PAGE_H = old_blocks, old_h
    # the generator's fixed output name -> the name the abstract includes
    (ABS_FIGS / "fig_apollo_timeline_probes.pdf").replace(
        ABS_FIGS / "fig_apollo_timeline.pdf")


def build_kd_sweep():
    """Sweep figure with the legend INSIDE the axes (upper right).

    The plot's upper-right quadrant is empty (both RMSE bowls stay
    below ~2.5 K past K_d ~ 9), so the legend fits there without
    covering any curve or the axis labels -- verified by the style
    module's assert_no_overlap guard, which fails the build otherwise.
    Moving it inside also removes the below-axes legend strip that
    could crowd the x-axis title at abstract scale.
    """
    import make_letter_figures as m
    from lunar.plotting.style import assert_no_overlap

    m.LETTER_FIGS = ABS_FIGS
    saved_fig = {}

    def _legend_inside(fig, handles, labels, **_kw):
        ax = fig.axes[0]
        # stop the two reference verticals (Hayne 3.4 / Feng 3.8) below
        # the legend band so they don't run up behind the box
        for ln in ax.lines:
            xd = ln.get_xdata()
            if len(xd) == 2 and xd[0] == xd[1]:      # an axvline
                ln.set_ydata([0.0, 0.62])            # axes-fraction coords
        ax.legend(handles, labels, loc="upper center",
                  bbox_to_anchor=(0.56, 0.99), ncols=2, frameon=True,
                  edgecolor=m.C_GRID, framealpha=0.95, fontsize=8.5,
                  handlelength=1.9, columnspacing=1.4, borderaxespad=0.4,
                  title=r"stars: retrieved $K_d^{*}$;  error bars: 95% bootstrap CI",
                  title_fontsize=8.5)
        fig.canvas.draw()
        assert_no_overlap(ax)                 # legend must not touch data
        saved_fig["fig"] = fig

    old = m.legend_below
    m.legend_below = _legend_inside
    try:
        with _SizedFigure((ABSTRACT_W, 4.1)):
            m.fig_kd_sweep()
    finally:
        m.legend_below = old


def build_robustness():
    """Figure 4 = bootstrap (a) + annotated 2-D contrast map (b), compact.

    Per user direction: the map is NOT elongated (compact 2-panel row),
    and every element is explained by a small text box INSIDE the panel
    rather than by a legend the reader must decode. Restored from the
    earlier design: the dashed 2/4/6-sigma significance contours and the
    Saito et al. reanalysis point (the independent flux study). Callout
    positions are hand-measured empty zones and the render is inspected;
    the style guard additionally checks panel (a).
    """
    import numpy as np
    from matplotlib.colors import TwoSlopeNorm
    from scipy.interpolate import PchipInterpolator
    from scipy.ndimage import gaussian_filter
    from lunar.plotting.style import (ANTH_DIVERGE, C_CHAR, C_TEAL, C_GRID,
                                      C_A15, C_A17, C_FOREST, fmt_axis,
                                      assert_no_overlap)
    import make_results_figures as m

    root = m._ROOT
    d = json.loads(m.RESULTS.read_text())

    fig = plt.figure(figsize=(ABSTRACT_W, 3.05))
    gs = fig.add_gridspec(1, 3, width_ratios=[1.0, 1.30, 0.05],
                          left=0.085, right=0.925, top=0.89, bottom=0.155,
                          wspace=0.42)
    axb = fig.add_subplot(gs[0, 0])
    axm = fig.add_subplot(gs[0, 1])
    cax = fig.add_subplot(gs[0, 2])
    NOTE = dict(fontsize=6.8, color=C_CHAR, ha="center", va="center",
                bbox=dict(boxstyle="round,pad=0.25", fc="white",
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
    im = axm.pcolormesh(x, y, contrast, cmap=ANTH_DIVERGE, norm=norm,
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


def main():
    ABS_FIGS.mkdir(parents=True, exist_ok=True)
    print("Rebuilding abstract figures at true print size "
          f"({ABSTRACT_W} in wide) -> {ABS_FIGS}")
    build_context_map()
    build_timeline()
    build_kd_sweep()
    build_robustness()
    print("Done.")


if __name__ == "__main__":
    main()
