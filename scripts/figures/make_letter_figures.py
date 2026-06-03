"""
Regenerate the three letter figures previously produced by the
01_apollo_validation notebook, using the same palette and style
helpers as make_results_figures.py so all six letter figures share a
single visual identity.

Outputs (overwriting the old notebook versions):
  paper/letter/figures/fig_apollo_mean_T_profile.pdf
  paper/letter/figures/fig_amplitude_vs_depth.pdf
  paper/letter/figures/fig_kd_sweep.pdf
"""
from __future__ import annotations
import json, sys, pathlib
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mtick
from copy import deepcopy

# Resolve the repo root from this file's location, not a hard-coded
# absolute path -- the manuscript and the figures must live in the
# SAME checkout or the published PDFs silently go stale.
_REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO))
sys.path.insert(0, str(_REPO / "scripts"))

from lunar import _bootstrap as boot
boot.ensure_lunar(extra=("spiceypy", "scipy"))
boot.ensure_apollo_hfe(mission="a15", probes=())
boot.ensure_apollo_hfe(mission="a17", probes=())

from lunar.grid import make_geometric_grid
from lunar.properties import (conductivity_hayne, conductivity_martinez,
                              specific_heat)
from lunar.constants import (
    K_SURFACE, K_DEEP, H_PARAMETER, CHI_RADIATIVE, T_REFERENCE, LUNATION_SECONDS,
)
from lunar.solver import PixelInputs, solve_pixel
from lunar.apollo_helpers import extract_sensor_stability

# Pull the unified rcParams + palette from the phase-2 figure module.
from make_results_figures import (   # type: ignore
    JGR_FULL,
    FS_TITLE, FS_LABEL, FS_TICK, FS_LEGEND,
    C_HAYNE, C_MS, C_A15, C_A17, C_CHAR, C_DIM, C_GRID, C_FOREST,
    fmt_axis,
)

# Configurations that match kd_sweep.py and the validation notebook
S0           = 1361.0
T_LUNAR      = LUNATION_SECONDS
DT_STEP      = 3600.0
N_LUN_FAST   = 30
TOL_FAST     = 0.05
GRID         = dict(z_max=5.0, dz0=0.002, growth=0.08)

HAYNE = dict(K_S=K_SURFACE, K_D=K_DEEP, H=H_PARAMETER, CHI=CHI_RADIATIVE)

# ── Martinez & Siegler (2021) genuine conductivity model ─────────────────────
# Source: Martinez & Siegler (2021, JGR Planets 126, e2021JE006829),
# "A Global Thermal Conductivity Model for Lunar Regolith at Low
# Temperatures".  Verified against their published code
# (Zenodo 12586656, lunar1Dheat v1.6, 1DFunctions/updateRK.m):
#
#   K_MS(T, rho) = (A1*rho + A2) * k_am(T)  +  (B1*rho + B2) * T^3
#
# where k_am(T) is the Woods-Robinson et al. (2019) amorphous-solid
# conduction polynomial (8 terms in powers of T).  rho is the
# depth-dependent density rho(z) = rho_d - (rho_d - rho_s) exp(-z/H).
# This is NOT a layered model — it is temperature- and density-
# dependent.  Coefficients reproduced verbatim from updateRK.m.
MS_AM = dict(  # Woods-Robinson 2019 amorphous-conduction polynomial
    A=-2.03297e-1, B=-11.472, C=22.5793, D=-14.3084, E=3.41742,
    F=0.01101, G=-2.80491e-5, H=3.35837e-8, I=-1.40021e-11,
)
MS_A1, MS_A2 = 5.0821e-6, -0.0051       # density-scaling of k_am
MS_B1, MS_B2 = 2.022e-13, -1.953e-10    # density-scaling of radiative T^3
MS_RHO_S, MS_RHO_D, MS_H = 1100.0, 1800.0, 0.054   # heat1D.m values

# ── This-work discrete 3-layer conductivity model ────────────────────────────
# A discrete piecewise approximation of the Apollo-measured regolith
# compaction structure (NOT from Martinez & Siegler).  The three zones
# follow the layered structure documented at the HFE sites:
#   * surface layer  0--2 cm  : radiative-dominated, loosely-packed
#                               grains (Langseth, Keihm & Peters 1976
#                               identify the radiative top "2--3 cm");
#                               K = K_s = 0.74 mW/m/K (Hayne 2017).
#   * transition     2--20 cm : rapid-compaction zone; K rises from
#                               K_s toward the deep value.  20 cm is
#                               where the Hayne (2017) exponential
#                               (H = 6 cm) has reached ~97% of K_d,
#                               so the boundary is consistent with the
#                               Hayne comparison.
#   * deep          >20 cm    : compacted regolith, K = K_d.
# Site specificity enters through the transition SHAPE: the Apollo
# cores give different deep bulk densities at the two sites (A15
# ~1825, A17 ~1960 kg/m^3; Grott et al. 2010), and a denser column
# compacts over a shorter depth.  We encode this with a density-set
# curvature exponent p_site in the transition ramp (see k_func_3layer):
# the A17 column, being denser, reaches the deep value slightly faster.
# K_d itself remains the single swept free parameter, exactly as for
# the Hayne form -- the density only shapes the layer profile, it is
# not itself retrieved.
TL_K_S   = K_SURFACE          # 7.4e-4 W/m/K  (Hayne 2017 surface value)
TL_K_D   = 3.8e-3             # W/m/K default deep value (Feng 2020)
TL_Z1    = 0.02              # base of surface layer (m)  -- Langseth 1976
TL_Z2    = 0.20              # base of transition layer (m)
# Grott et al. (2010) deep bulk densities at the two HFE sites:
TL_RHO_SITE = {"A15": 1825.0, "A17": 1960.0}   # kg/m^3
TL_RHO_REF  = 1800.0          # Hayne (2017) nominal deep density

SITES = {
    "A15": dict(label="Apollo 15", lat=26.13, lon=3.63,
                albedo=0.131, emissivity=0.95, Q_BASAL=0.021,
                T_MEAN_EFF=250.0, MIN_DEPTH_CM=80, mission="a15"),
    "A17": dict(label="Apollo 17", lat=20.19, lon=30.77,
                albedo=0.137, emissivity=0.95, Q_BASAL=0.015,
                T_MEAN_EFF=256.5, MIN_DEPTH_CM=80, mission="a17"),
}

LETTER_FIGS = _REPO / "paper" / "letter" / "figures"
PHASE_A     = _REPO / "output" / "kd_retrieval_results.json"


# ══════════════════════════════════════════════════════════════════════════════
# Robust bottom-legend placement.
#
# Every recurring "legend overlaps the axis label" bug came from hand-
# guessing a `bottom` margin that turned out too small for the legend.
# This helper removes the guesswork: it draws the legend, MEASURES its
# rendered height, and then reserves exactly that much space below the
# axes -- so the legend can never sit on top of the x-axis title.
# Use this for every multi-panel letter figure with a shared legend.
# ══════════════════════════════════════════════════════════════════════════════
def legend_below(fig, handles, labels, *, ncols=3, pad_in=0.10, **kw):
    """Place a shared legend in a reserved strip below all axes.

    The figure is grown downward and the axes are pushed up by exactly
    the legend's measured height plus `pad_in` inches of clearance, so
    no axis label is ever overlapped regardless of legend size.
    """
    fig.canvas.draw()                       # so text extents are real
    leg = fig.legend(handles, labels, loc="lower center",
                     bbox_to_anchor=(0.5, 0.0), ncols=ncols,
                     frameon=True, edgecolor=C_GRID, framealpha=0.97,
                     borderpad=0.6, **kw)
    fig.canvas.draw()
    # legend height in inches
    bb = leg.get_window_extent()
    leg_h_in = bb.height / fig.dpi
    fig_w, fig_h = fig.get_size_inches()
    reserve = leg_h_in + pad_in             # inches to clear at the bottom
    # grow the figure so the plot area is unchanged, legend gets its own band
    new_h = fig_h + reserve
    fig.set_size_inches(fig_w, new_h)
    # current axes occupy [bottom0, top0] of the OLD figure; rescale up
    frac = reserve / new_h
    for ax in fig.axes:
        p = ax.get_position()
        ax.set_position([p.x0,
                         frac + p.y0 * (1 - frac),
                         p.width,
                         p.height * (1 - frac)])
    # pin the legend inside the reserved band, centred
    leg.set_bbox_to_anchor((0.5, pad_in / new_h / 2), transform=fig.transFigure)
    return leg


# ── Solver ────────────────────────────────────────────────────────────────────
def k_func_hayne(kd, h=HAYNE["H"]):
    def f(T, z):
        return conductivity_hayne(T, z, Ks=HAYNE["K_S"], Kd=kd,
                                  H=h, chi=HAYNE["CHI"])
    return f


def _ms_density(z):
    """Depth-dependent density rho(z) used by the Martinez & Siegler
    model:  rho(z) = rho_d - (rho_d - rho_s) exp(-z/H)  (makegrid.m)."""
    return MS_RHO_D - (MS_RHO_D - MS_RHO_S) * np.exp(-np.asarray(z) / MS_H)


def k_func_ms():
    """Genuine Martinez & Siegler (2021) thermal conductivity model.

    K_MS(T, rho) = (A1*rho + A2) * k_am(T) + (B1*rho + B2) * T^3

    with k_am(T) the Woods-Robinson (2019) amorphous-solid conduction
    polynomial.  rho is rho(z); see _ms_density.  Verified line-for-
    line against Martinez & Siegler's published code (updateRK.m).
    """
    am = MS_AM
    def f(T, z):
        T_arr = np.atleast_1d(np.asarray(T, dtype=float))
        z_arr = np.atleast_1d(np.asarray(z, dtype=float))
        if T_arr.shape != z_arr.shape:
            T_arr = np.broadcast_to(T_arr, z_arr.shape).copy()
        # Woods-Robinson amorphous-conduction polynomial k_am(T)
        k_am = (am["A"] + am["B"]*T_arr**-4.0 + am["C"]*T_arr**-3.0
                + am["D"]*T_arr**-2.0 + am["E"]*T_arr**-1.0
                + am["F"]*T_arr + am["G"]*T_arr**2.0
                + am["H"]*T_arr**3.0 + am["I"]*T_arr**4.0)
        rho = _ms_density(z_arr)
        return (MS_A1*rho + MS_A2) * k_am + (MS_B1*rho + MS_B2) * T_arr**3.0
    return f


def k_func_3layer(kd=TL_K_D, rho_deep=TL_RHO_REF):
    """This-work discrete 3-layer conductivity model (see header).

    Piecewise structural conductivity:
      z < TL_Z1                : K_s  (surface radiative layer)
      TL_Z1 <= z < TL_Z2       : transition K_s -> kd, with a
                                 density-set curvature
      z >= TL_Z2               : kd  (deep compacted layer)
    times the Hayne (2017) radiative multiplier 1 + chi (T/T_ref)^3
    so the temperature dependence is consistent with the other two
    models in the comparison.

    Site specificity: a denser column compacts over a shorter depth,
    so the transition ramp is raised to a power p < 1 that decreases
    with deep bulk density (denser -> faster approach to kd).  We map
    density to exponent linearly about the Hayne reference density:
        p = 1 - 0.5*(rho_deep - TL_RHO_REF)/TL_RHO_REF
    At the Hayne reference density p = 1 (linear ramp); at the denser
    A17 site p < 1 (concave-up, faster rise).  K_d is unchanged --
    only the layer SHAPE responds to density.
    """
    p = 1.0 - 0.5 * (rho_deep - TL_RHO_REF) / TL_RHO_REF
    p = float(np.clip(p, 0.4, 1.6))
    def f(T, z):
        z_arr = np.atleast_1d(np.asarray(z, dtype=float))
        T_arr = np.atleast_1d(np.asarray(T, dtype=float))
        if T_arr.shape != z_arr.shape:
            T_arr = np.broadcast_to(T_arr, z_arr.shape).copy()
        frac = np.clip((z_arr - TL_Z1) / (TL_Z2 - TL_Z1), 0.0, 1.0) ** p
        ramp = TL_K_S + (kd - TL_K_S) * frac
        Kc = np.where(z_arr < TL_Z1, TL_K_S, ramp)
        return Kc * (1.0 + HAYNE["CHI"] * (T_arr / T_REFERENCE) ** 3)
    return f


def run_pixel(site_cfg, *, kfunc):
    site = deepcopy(site_cfg)
    grid_  = make_geometric_grid(**GRID)
    z_mid  = grid_.z_mid
    N_t    = int(T_LUNAR / DT_STEP) + 1
    t_s    = np.linspace(0.0, T_LUNAR, N_t)
    cos_lat = np.cos(np.deg2rad(site["lat"]))
    phase   = 2.0 * np.pi * t_s / T_LUNAR
    insol   = S0 * cos_lat * np.maximum(0.0, np.cos(phase))
    K_init = kfunc(np.full_like(z_mid, site["T_MEAN_EFF"]), z_mid)
    T_init = site["T_MEAN_EFF"] + site["Q_BASAL"] * np.cumsum(grid_.dz / K_init)
    out = solve_pixel(PixelInputs(
        grid=grid_, t=t_s, bc_mode="radiative",
        insolation=insol, albedo=site["albedo"],
        emissivity=site["emissivity"], Q_b=site["Q_BASAL"], T_init=T_init,
        n_lunations_spinup=N_LUN_FAST, spinup_tol_K=TOL_FAST,
        K_func=kfunc, cp_func=lambda T: specific_heat(T, model="hayne"),
    ))
    return z_mid, out.T, t_s


# ══════════════════════════════════════════════════════════════════════════════
# FIGURE 2 — Annual-mean subsurface T profile
# ══════════════════════════════════════════════════════════════════════════════
def fig_mean_T_profile():
    """Annual-mean T(z) at both Apollo sites with two un-retrieved
    global K(z) forms overlaid.

    Layout:
      * Bottom margin reserved for the shared legend strip; the
        x-axis label sits cleanly above it (no overlap).
      * Borestem zone (z < 80 cm) shaded in soft coral, with a
        boxed callout label in the upper-left of each panel placed
        above the data (zorder above markers).
      * Sentence-case axis labels per JGR style.
    """
    fig, axes = plt.subplots(1, 2, figsize=(JGR_FULL, 4.6),
                             gridspec_kw={"wspace": 0.28})
    # `bottom=0.13` leaves room for the x-axis label only; the legend
    # strip is added afterwards by legend_below(), which grows the
    # figure downward so the xlabel never collides with the legend.
    fig.subplots_adjust(left=0.085, right=0.97, top=0.93, bottom=0.13)

    # Borestem-zone callout style: faint coral fill, charcoal border,
    # high zorder so it sits on top of the markers but still semi-
    # transparent enough not to mask them.
    BORE_FILL = "#F4D6CB"   # soft coral
    BORE_EDGE = "#B85B3A"   # coral border (matches C_CORAL)

    for ax, name in zip(axes, ["A15", "A17"]):
        cfg = SITES[name]
        # observations
        obs = extract_sensor_stability(cfg["mission"], cfg["MIN_DEPTH_CM"])
        z_obs = np.array(obs["depth_cm_all"]) / 100.0
        T_obs = np.array(obs["T_eq_all"])
        T_std = np.array(obs["T_std_all"])
        deep  = np.array(obs["deep_mask"], dtype=bool)
        stype = np.array(obs["stype_all"])

        # Two published conductivity models at their nominal
        # (un-retrieved) parameters:
        #   - Hayne (2017) smooth-exponential, global K_d = 3.4 mW/m/K
        #   - Martinez & Siegler (2021) T,rho-dependent forward
        z_mid, T_mat_H,  _ = run_pixel(cfg, kfunc=k_func_hayne(HAYNE["K_D"]))
        z_mid, T_mat_MS, _ = run_pixel(cfg, kfunc=k_func_ms())
        T_H  = T_mat_H.mean(axis=1)
        T_MS = T_mat_MS.mean(axis=1)

        # Borestem zone shading -- soft coral band so the omitted
        # region reads as "different" from the retrieval band.
        ax.axhspan(0, 80, color=BORE_FILL, alpha=0.55, zorder=0)
        ax.axhline(80, color=BORE_EDGE, lw=0.7, ls=(0, (3, 2)),
                   alpha=0.6, zorder=1)

        # Model curves
        ax.plot(T_H,  z_mid * 100, "-",  color=C_HAYNE, lw=2.0,
                label="Hayne (2017), smooth exponential",
                zorder=2)
        ax.plot(T_MS, z_mid * 100, "--", color=C_MS, lw=2.0,
                label=r"Martínez & Siegler (2021), $T,\rho$-dependent",
                zorder=2)

        # Observed sensors. Deep markers are filled (used in
        # retrieval); shallow markers are open (excluded).
        col_TG = C_CHAR
        col_TR = C_DIM
        for is_tg in (True, False):
            mask = (stype == ("TG" if is_tg else "TR"))
            ax.errorbar(T_obs[mask & deep], z_obs[mask & deep] * 100,
                        xerr=T_std[mask & deep], fmt="o",
                        color=col_TG if is_tg else col_TR,
                        mec="white", mew=0.7, markersize=7, capsize=2,
                        zorder=3,
                        label=("TG (deep)" if is_tg else "TR (deep)") if name == "A15" else None)
            ax.errorbar(T_obs[mask & ~deep], z_obs[mask & ~deep] * 100,
                        xerr=T_std[mask & ~deep], fmt="o", mfc="none",
                        color=col_TG if is_tg else col_TR,
                        mew=0.9, markersize=7, capsize=2,
                        zorder=3,
                        label=("TG (shallow, excluded)" if is_tg else "TR (shallow, excluded)") if name == "A15" else None)

        fmt_axis(ax,
                 xlabel=r"$T$ (K)",
                 ylabel="Depth (cm)" if name == "A15" else "",
                 title=f"({['a','b'][['A15','A17'].index(name)]})  {cfg['label']}")
        ax.invert_yaxis()
        ax.set_ylim(250, 0)

        # Boxed callout label for the borestem zone -- placed inside
        # the panel using axes coordinates (immune to data x-limits)
        # and drawn above the markers (zorder=5).
        ax.text(0.04, 0.12,
                "Borestem zone\n($z < 80$ cm, excluded)",
                transform=ax.transAxes,
                fontsize=FS_TICK - 0.5, color=C_CHAR,
                ha="left", va="top",
                bbox=dict(boxstyle="round,pad=0.32",
                          facecolor="white", edgecolor=BORE_EDGE,
                          linewidth=0.7, alpha=0.92),
                zorder=5)

    # shared legend in a reserved strip below -- never overlaps the axes
    h, l = axes[0].get_legend_handles_labels()
    legend_below(fig, h, l, ncols=2, fontsize=FS_LEGEND,
                 handlelength=2.2, columnspacing=1.6)

    out = LETTER_FIGS / "fig_apollo_mean_T_profile.pdf"
    fig.savefig(out)
    plt.close(fig)
    print(f"  → {out}")


# ══════════════════════════════════════════════════════════════════════════════
# FIGURE 3 — Diurnal amplitude vs depth (borestem signature)
# ══════════════════════════════════════════════════════════════════════════════
def fig_amplitude_vs_depth():
    fig, axes = plt.subplots(1, 2, figsize=(JGR_FULL, 4.6),
                             gridspec_kw={"wspace": 0.28})
    fig.subplots_adjust(left=0.08, right=0.97, top=0.92, bottom=0.22)

    for ax, name in zip(axes, ["A15", "A17"]):
        cfg = SITES[name]
        obs = extract_sensor_stability(cfg["mission"], cfg["MIN_DEPTH_CM"])
        # Per-sensor diurnal amplitude has to be computed from the raw
        # data via SPICE LST folding; we approximate it here by the
        # within-window standard deviation of the Apollo HFE record,
        # which is dominated by the diurnal cycle for shallow sensors.
        z_obs = np.array(obs["depth_cm_all"])
        T_std = np.array(obs["T_std_all"])
        # Diurnal amplitude ≈ √2 × σ for a sinusoidal signal.
        amp_obs = np.sqrt(2.0) * T_std

        # Modelled regolith attenuation curves (analytical) for the
        # two published K(z) forms. Both are dominated by the diurnal
        # skin depth δ = √(2κ/ω) with κ = K/(ρ c_p) at T ~ 250 K and
        # the published deep regolith density ρ ≈ 1500 kg m^-3
        # (volumetric average over the top few skin depths).
        z_grid = np.linspace(0.0, 250.0, 400)   # cm
        omega  = 2 * np.pi / T_LUNAR
        rho_c  = 1500.0 * 850.0     # ρ c_p, volumetric heat capacity

        # Hayne: K_d = 3.4 mW/m/K (published global value).
        kappa_H = HAYNE["K_D"] / rho_c
        delta_H = np.sqrt(2 * kappa_H / omega) * 100      # cm
        amp_H   = 100 * np.exp(-z_grid / delta_H)

        # Martinez: K(T, ρ) evaluated at T = 250 K, ρ = 1800 kg m^-3
        # (the deep asymptote of the Hayne-form ρ(z) used by Martinez).
        K_M     = float(conductivity_martinez(np.array([250.0]),
                                              rho=np.array([1800.0]))[0])
        kappa_M = K_M / rho_c
        delta_M = np.sqrt(2 * kappa_M / omega) * 100
        amp_M   = 100 * np.exp(-z_grid / delta_M)

        ax.semilogx(amp_H, z_grid, "-",  color=C_HAYNE, lw=2.0,
                    label="Hayne (2017) attenuation")
        ax.semilogx(amp_M, z_grid, "--", color=C_MS, lw=2.0,
                    label="Martínez & Siegler (2021) attenuation")
        ax.semilogx(amp_obs, z_obs, "o", color=C_CHAR,
                    mec="white", mew=0.7, markersize=7,
                    label="Apollo HFE  (obs.)")

        # borestem zone
        ax.axhspan(0, 80, color="0.85", alpha=0.35, zorder=0)
        ax.text(2e-3, 12, "borestem zone (z < 80 cm)",
                fontsize=FS_TICK, color=C_DIM, va="center", style="italic")

        fmt_axis(ax,
                 xlabel="Diurnal amplitude (K)",
                 ylabel="Depth (cm)" if name == "A15" else "",
                 title=f"({['a','b'][['A15','A17'].index(name)]})  {cfg['label']}")
        ax.invert_yaxis()
        ax.set_ylim(220, 0)
        ax.set_xlim(1e-3, 200)

    h, l = axes[0].get_legend_handles_labels()
    fig.legend(h, l, loc="lower center", bbox_to_anchor=(0.5, 0.005),
               ncols=3, frameon=True, edgecolor=C_GRID, framealpha=0.97,
               fontsize=FS_LEGEND, handlelength=2.2, borderpad=0.6)

    out = LETTER_FIGS / "fig_amplitude_vs_depth.pdf"
    fig.savefig(out)
    plt.close(fig)
    print(f"  → {out}")


# ══════════════════════════════════════════════════════════════════════════════
# FIGURE 4 — K_d sweep (the central retrieval figure)
# ══════════════════════════════════════════════════════════════════════════════
def fig_kd_sweep():
    """Single-panel K_d retrieval figure.

    Deep-sensor RMSE(K_d) at both sites, extended past the fitting grid
    so each curve is shown rising again on the high-K_d side -- the
    minima are genuine bracketed bowls, not descending shoulders. The
    x-axis is held tight enough that the two minima, the parabolic fit,
    and the 95% bootstrap CI bands are all clearly legible.
    """
    d = json.loads(PHASE_A.read_text())

    # ── extend the sweep so the rising high-K_d tail is shown ────────────
    from scripts.pipeline.retrieve_kd import SITES, run_kd_sweep_extended
    EXT = {"A15": np.linspace(15.5e-3, 22.0e-3, 5),
           "A17": np.linspace(25.5e-3, 30.0e-3, 4)}
    ext_curve = {}
    for name in ("A15", "A17"):
        _, _, R, _ = run_kd_sweep_extended(SITES[name], EXT[name],
                                           k_model="hayne")
        ext_curve[name] = (EXT[name] * 1e3, np.sqrt((R ** 2).mean(axis=0)))

    from scipy.interpolate import CubicSpline
    # No hand-tuned bottom margin: legend_below() reserves the strip.
    fig, ax = plt.subplots(figsize=(JGR_FULL, 4.2))
    # Tight bottom: just enough for the x-axis label. legend_below()
    # will grow the figure to add its own reserved strip beneath.
    fig.subplots_adjust(left=0.10, right=0.97, top=0.93, bottom=0.13)

    # Subtle reference verticals first so curves sit on top.
    ax.axvline(3.4, color=C_HAYNE, ls="--", lw=1.0, alpha=0.55,
               label="Hayne 2017 global  $K_d = 3.4$", zorder=1)
    ax.axvline(3.8, color=C_FOREST, ls=":", lw=1.0, alpha=0.55,
               label="Feng 2020 deep value  $K_d = 3.8$", zorder=1)

    for name, color in [("A15", C_A15), ("A17", C_A17)]:
        s    = d[name]
        kdg  = np.array(s["kd_grid"]) * 1e3
        rmse = np.array(s["rmse_curve"])
        kde, rme = ext_curve[name]
        kd_all   = np.concatenate([kdg, kde])
        rm_all   = np.concatenate([rmse, rme])
        cs       = CubicSpline(kd_all, rm_all)
        kdf      = np.linspace(kd_all[0], kd_all[-1], 600)

        b = s["bootstrap"]
        lo, hi = b["ci_lo"] * 1e3, b["ci_hi"] * 1e3
        kd_star, rmse_star = s["kd_star"] * 1e3, s["rmse_star"]

        # Smooth retrieval curve; faint sweep-grid dots in the background.
        ax.plot(kdf, cs(kdf), "-", color=color, lw=2.4, zorder=3,
                label=f"{name}  $K_d^{{*}} = {kd_star:.2f}$  "
                      f"[{lo:.2f}, {hi:.2f}]")
        ax.plot(kdg, rmse, "o", color=color, markersize=2.6,
                mec="white", mew=0.5, alpha=0.55, zorder=4)

        # Horizontal error bar on the star = 95% bootstrap CI. The
        # bar lives at the star's y, so it sits ON the curve at the
        # minimum rather than under it (no integral-area illusion).
        ax.errorbar(kd_star, rmse_star,
                    xerr=[[kd_star - lo], [hi - kd_star]],
                    fmt="*", color=color, ecolor=color,
                    elinewidth=1.6, capsize=5, capthick=1.6,
                    ms=22, mec="white", mew=1.5, zorder=6)

    fmt_axis(ax,
             xlabel=r"Deep conductivity  $K_d$  (mW m$^{-1}$ K$^{-1}$)",
             ylabel=r"Deep-sensor RMSE  (K)",
             title="Per-site $K_d$ retrieval under the Hayne 2017 "
                   "functional form")
    ax.set_xlim(0, 30)
    ax.set_ylim(0, 4)
    ax.grid(which="major", color=C_GRID, lw=0.4, alpha=0.7)
    ax.set_axisbelow(True)

    h, l = ax.get_legend_handles_labels()
    legend_below(fig, h, l, ncols=2, fontsize=FS_LEGEND,
                 handlelength=2.4, columnspacing=2.2,
                 title=r"Stars: retrieved $K_d^{*}$;  horizontal error bars: 95% bootstrap CI",
                 title_fontsize=FS_LABEL)

    out = LETTER_FIGS / "fig_kd_sweep.pdf"
    fig.savefig(out)
    plt.close(fig)
    print(f"  → {out}")


def main():
    print("Regenerating letter figures with unified palette:")
    fig_mean_T_profile()
    fig_amplitude_vs_depth()
    fig_kd_sweep()
    print("done.")


if __name__ == "__main__":
    main()
