#!/usr/bin/env python3
"""Two introduction figures for the letter, in the Anthropic design idiom.

  fig_intro_models.pdf   -- the three conductivity models compared:
                            (a) bulk-density profile rho(z),
                            (b) thermal-conductivity profile K(z).
  fig_intro_probe.pdf    -- schematic of an Apollo HFE borestem and its
                            gradient- and ring-bridge sensors in the
                            regolith column.

Both are vector PDFs sized for the JGR single-column text width and use
the shared warm palette of the other letter figures. Self-contained:
no pipeline data required.

Run from the repo root:
  python scripts/figures/make_intro_figures.py
"""
from __future__ import annotations
import pathlib

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, Rectangle, FancyArrowPatch
from matplotlib.lines import Line2D

# ── shared design tokens (match make_results_figures.py) ────────────────────────
JGR_FULL = 7.48
C_CORAL  = "#B85B3A"
C_CORAL_L= "#E5A88A"
C_TEAL   = "#2A6478"
C_TEAL_L = "#7CA3B0"
C_FOREST = "#3D6E4A"
C_FOREST_L="#94B89C"
C_CHAR   = "#2A2520"
C_DIM    = "#6E6862"
C_GRID   = "#E8E5E0"
C_PAPER  = "#FBFAF8"     # warm near-white panel background
FS_LABEL = 10.5
FS_TICK  = 9.5
FS_TITLE = 11.0

plt.rcParams.update({
    "font.family": "serif",
    "font.serif": ["Latin Modern Roman", "Times New Roman", "DejaVu Serif"],
    "mathtext.fontset": "cm",
    "axes.edgecolor": C_DIM,
    "axes.labelcolor": C_CHAR,
    "text.color": C_CHAR,
    "xtick.color": C_CHAR,
    "ytick.color": C_CHAR,
    "axes.linewidth": 0.8,
})

OUT = pathlib.Path(__file__).resolve().parents[2] / "paper" / "letter" / "figures"

# ── regolith model parameters (Hayne 2017; this-work 3-layer) ────────────────
RHO_S, RHO_D = 1100.0, 1800.0      # Hayne surface / deep bulk density
H_PARAM      = 0.06                 # Hayne e-folding depth (m)
RHO_D_SITE   = {"A15": 1825.0, "A17": 1960.0}   # 3-layer per-site deep density
TL_Z1, TL_Z2 = 0.02, 0.20           # 3-layer boundaries (m)


def rho_hayne(z):
    """Hayne (2017) exponential density profile."""
    return RHO_D - (RHO_D - RHO_S) * np.exp(-z / H_PARAM)


def rho_three_layer(z, rho_deep):
    """This-work discrete 3-layer density profile: a loose surface layer,
    a compaction ramp, and a compacted deep layer at rho_deep."""
    z = np.asarray(z, float)
    rho_mid = 0.5 * (RHO_S + rho_deep)
    out = np.empty_like(z)
    out[z < TL_Z1] = RHO_S
    ramp = (z >= TL_Z1) & (z < TL_Z2)
    frac = (z[ramp] - TL_Z1) / (TL_Z2 - TL_Z1)
    out[ramp] = RHO_S + (rho_deep - RHO_S) * frac
    out[z >= TL_Z2] = rho_deep
    _ = rho_mid
    return out


# ════════════════════════════════════════════════════════════════════════════
# FIGURE 1 of intro -- conductivity-model comparison
# ════════════════════════════════════════════════════════════════════════════
def fig_intro_models():
    z = np.linspace(0.0, 2.0, 400)            # depth, m
    z_cm = z * 100.0

    fig, (axA, axB) = plt.subplots(
        1, 2, figsize=(JGR_FULL, 3.7))
    fig.subplots_adjust(left=0.085, right=0.975, top=0.86, bottom=0.30,
                        wspace=0.30)

    # ── panel (a): bulk-density profiles ────────────────────────────────────
    # y-axis limited to the top 60 cm, where the three models actually
    # differ; below 20 cm every profile is flat, so plotting to 200 cm
    # just wastes the panel and crowds the layer labels.
    axA.set_facecolor(C_PAPER)
    axA.plot(rho_hayne(z), z_cm, color=C_TEAL, lw=2.6,
             label="Hayne (2017): smooth exponential")
    axA.plot(rho_three_layer(z, RHO_D_SITE["A15"]), z_cm,
             color=C_FOREST, lw=2.4, ls="--",
             label=r"This work, 3-layer: A15 ($\rho_d=1825$)")
    axA.plot(rho_three_layer(z, RHO_D_SITE["A17"]), z_cm,
             color=C_CORAL, lw=2.4, ls=":",
             label=r"This work, 3-layer: A17 ($\rho_d=1960$)")

    # mark the 3-layer boundaries and label the three layers in clear space
    for zb in (TL_Z1, TL_Z2):
        axA.axhline(zb * 100, color=C_DIM, lw=0.7, ls=(0, (1, 2)),
                    alpha=0.7, zorder=0)
    axA.text(1960, TL_Z1 * 50, "surface\nlayer", fontsize=FS_TICK - 1.5,
             color=C_DIM, style="italic", va="center", ha="right",
             linespacing=0.95)
    axA.text(1960, (TL_Z1 + TL_Z2) * 50, "compaction\ntransition",
             fontsize=FS_TICK - 1.5, color=C_DIM, style="italic",
             va="center", ha="right", linespacing=0.95)
    axA.text(1960, 44, "compacted\ndeep layer", fontsize=FS_TICK - 1.5,
             color=C_DIM, style="italic", va="center", ha="right",
             linespacing=0.95)

    axA.set_xlabel(r"Bulk density $\rho$  (kg m$^{-3}$)", fontsize=FS_LABEL)
    axA.set_ylabel("Depth  (cm)", fontsize=FS_LABEL)
    axA.set_title("(a)  Density profile", fontsize=FS_TITLE,
                  fontweight="bold", pad=6)
    axA.set_ylim(60, 0)
    axA.set_xlim(1050, 2000)
    axA.tick_params(labelsize=FS_TICK)
    axA.grid(color=C_GRID, lw=0.5)
    axA.set_axisbelow(True)

    # ── panel (b): conductivity profiles (schematic, room-T) ────────────────
    # K(z) shapes only -- absolute scale is the retrieval target, so we show
    # normalised shape: surface K_s to a deep K_d, same two architectures.
    axB.set_facecolor(C_PAPER)
    Ks, Kd = 0.0074, 0.034            # representative W/m/K (x10^-3 shown)
    K_hayne = (Kd - (Kd - Ks) * np.exp(-z / H_PARAM)) * 1e3
    # 3-layer K(z): flat-ramp-flat, same boundaries
    def K_three(zz):
        zz = np.asarray(zz, float)
        out = np.empty_like(zz)
        out[zz < TL_Z1] = Ks
        ramp = (zz >= TL_Z1) & (zz < TL_Z2)
        frac = (zz[ramp] - TL_Z1) / (TL_Z2 - TL_Z1)
        out[ramp] = Ks + (Kd - Ks) * frac
        out[zz >= TL_Z2] = Kd
        return out * 1e3
    # panel (b) shows the two K(z) architectures (shape, not the
    # site-specific retrieved value); labels live in the shared legend.
    axB.plot(K_hayne, z_cm, color=C_TEAL, lw=2.6)
    axB.plot(K_three(z), z_cm, color=C_CHAR, lw=2.4, ls="--")
    axB.text(36, 6, "smooth\nexponential", fontsize=FS_TICK - 1.5,
             color=C_TEAL, ha="right", va="center", style="italic",
             linespacing=0.95)
    axB.text(20, 40, "discrete\n3-layer", fontsize=FS_TICK - 1.5,
             color=C_CHAR, ha="center", va="center", style="italic",
             linespacing=0.95)

    axB.set_xlabel(r"Thermal conductivity $K$  (mW m$^{-1}$ K$^{-1}$)",
                   fontsize=FS_LABEL)
    axB.set_ylabel("Depth  (cm)", fontsize=FS_LABEL)
    axB.set_title("(b)  Conductivity architecture", fontsize=FS_TITLE,
                  fontweight="bold", pad=6)
    axB.set_ylim(60, 0)
    axB.set_xlim(0, 40)
    axB.tick_params(labelsize=FS_TICK)
    axB.grid(color=C_GRID, lw=0.5)
    axB.set_axisbelow(True)

    # shared legend below -- only the three density-panel curves
    handles, labels = axA.get_legend_handles_labels()
    fig.legend(handles, labels, loc="lower center",
               bbox_to_anchor=(0.5, 0.005), ncols=3, frameon=True,
               edgecolor=C_GRID, framealpha=0.97, fontsize=FS_TICK - 1,
               handlelength=2.2, columnspacing=1.6, borderpad=0.6)

    out = OUT / "fig_intro_models.pdf"
    fig.savefig(out)
    plt.close(fig)
    print(f"  -> {out}")


# ════════════════════════════════════════════════════════════════════════════
# FIGURE 2 of intro -- Apollo HFE probe schematic
# ════════════════════════════════════════════════════════════════════════════
def _draw_probe_schematic(ax):
    """Draw the Apollo HFE probe schematic into a single axes.
    Factored out so it can sit in a multi-panel figure."""
    # depth axis runs 0 (surface) downward to 250 cm
    z_top, z_bot = -18.0, 250.0
    ax.set_xlim(0, 100)
    ax.set_ylim(z_bot, z_top)
    ax.axis("off")

    # ── sky / surface / regolith bands ──────────────────────────────────────
    ax.add_patch(Rectangle((0, z_top), 100, -z_top, facecolor="#F4F1EC",
                           edgecolor="none", zorder=0))                # space
    # regolith: a continuous depth gradient (many thin slices, no gaps),
    # darkening smoothly with depth to suggest increasing compaction
    # Background gradient: light tan at the surface, deep warm brown at
    # depth, to make the increasing compaction visually obvious.
    n_slice = 160
    edges = np.linspace(0.0, z_bot, n_slice + 1)
    for k in range(n_slice):
        f = k / (n_slice - 1)                       # 0 at surface, 1 deep
        r = 0.96 - 0.30 * f
        g = 0.91 - 0.34 * f
        b = 0.84 - 0.36 * f
        ax.add_patch(Rectangle((0, edges[k]), 100, edges[k + 1] - edges[k],
                               facecolor=(r, g, b),
                               edgecolor="none", zorder=0))
    # surface line
    ax.plot([0, 100], [0, 0], color=C_CHAR, lw=1.6, zorder=3)
    ax.text(2, -8, "Lunar surface", fontsize=FS_TICK, color=C_CHAR,
            style="italic", va="center")
    ax.text(2, 230, "compacted deep regolith", fontsize=FS_TICK - 1,
            color="#FBFAF8", style="italic", va="center", alpha=0.95,
            zorder=3)

    # ── the borestem (fibreglass tube the probe sits in) ────────────────────
    stem_x, stem_w = 33.0, 5.0
    ax.add_patch(FancyBboxPatch((stem_x, 2), stem_w, 224,
                 boxstyle="round,pad=0,rounding_size=1.2",
                 facecolor="#D9D2C6", edgecolor=C_DIM, lw=1.0, zorder=2))
    # the borestem protrudes slightly above the surface
    ax.add_patch(Rectangle((stem_x, -14), stem_w, 16,
                 facecolor="#D9D2C6", edgecolor=C_DIM, lw=1.0, zorder=2))
    ax.text(stem_x + stem_w / 2, -16, "borestem",
            fontsize=FS_TICK - 1, color=C_DIM, ha="center", va="bottom")

    # borestem-affected zone (upper 80 cm) -- the part excluded from retrieval
    ax.add_patch(Rectangle((0, 0), 100, 80, facecolor=C_CORAL,
                           alpha=0.10, edgecolor="none", zorder=1))
    ax.plot([0, 100], [80, 80], color=C_CORAL, lw=1.1, ls="--", zorder=3)
    # Borestem-zone label sits along the right edge of the panel,
    # rotated vertically so it does not clash with the sensor-name
    # leader lines (which terminate around x = 75).
    ax.text(96, 40, "borestem zone ($z<80$ cm, excluded)",
            fontsize=FS_TICK - 1.5, color=C_CORAL, ha="center",
            va="center", style="italic", rotation=270, zorder=4)

    # ── the sensor positions (representative Apollo-15 Probe-1 depths) ──────
    # Sensors come in two electrical types:
    #   TG = gradient-bridge (teal),
    #   TR = ring-bridge     (blue).
    # Shallow sensors (z < 80 cm) are excluded by the borestem cut and are
    # drawn hollow in neutral grey to make their exclusion visible at a
    # glance.
    C_TG = "#2A6478"   # teal (matches phase2 figures)
    C_TR = "#3563A1"   # cooler blue, distinct from teal
    sensors = [
        (35,  "TR11A",  "TR", True),
        (45,  "TR11A'", "TR", True),
        (84,  "TG11B",  "TG", False),
        (91,  "TG12A",  "TG", False),
        (101, "TR12A",  "TR", False),
        (129, "TR12B",  "TR", False),
        (139, "TG12B",  "TG", False),
    ]
    cx = stem_x + stem_w / 2
    for depth, name, kind, excluded in sensors:
        if excluded:
            face, edge, txt_col = "white", C_DIM, C_DIM
        else:
            face = C_TG if kind == "TG" else C_TR
            edge, txt_col = "white", C_CHAR
        # Thicker, more visible sensor markers
        ax.add_patch(FancyBboxPatch((cx - 3.8, depth - 2.2), 7.6, 4.4,
                     boxstyle="round,pad=0,rounding_size=0.9",
                     facecolor=face, edgecolor=edge, lw=1.2, zorder=4))
        # leader line + label to the right
        ax.annotate(f"{name}  ({depth} cm)",
                    xy=(cx + 3.8, depth), xytext=(62, depth),
                    fontsize=FS_TICK - 1, color=txt_col,
                    va="center", ha="left",
                    arrowprops=dict(arrowstyle="-", color=C_DIM, lw=0.7,
                                    shrinkA=0, shrinkB=2))

    # depth scale on the left (a clean vertical axis line + ticks)
    ax.plot([10, 10], [0, z_bot], color=C_CHAR, lw=0.9, zorder=3)
    for zt in (0, 50, 100, 150, 200, 250):
        ax.plot([8.0, 10], [zt, zt], color=C_CHAR, lw=0.9, zorder=3)
        ax.text(6.8, zt, f"{zt}", fontsize=FS_TICK - 1, ha="right",
                va="center", color=C_CHAR)
    ax.text(3.2, 125, "Depth  (cm)", fontsize=FS_TICK, ha="center",
            va="center", color=C_CHAR, rotation=90)

    # Sensor-type legend lives in a shared figure-level strip below
    # the panels (see fig_intro_probe); no in-panel legend box here.

    ax.set_title("(a)  Apollo HFE probe configuration",
                 fontsize=FS_TITLE, fontweight="bold", pad=8)


# ════════════════════════════════════════════════════════════════════════════
# K(z) comparison panel: Hayne (2017) vs Mart{\'\i}nez & Siegler (2021)
# ════════════════════════════════════════════════════════════════════════════
# Both forms evaluated at a representative deep-lunar temperature
# T_0 = 250 K (the in-situ HFE deep-sensor mean is 250-256 K) and at
# the same Hayne-form rho(z), so the visible difference is the K-form
# itself, not the density input.  Coefficients held at the published
# values in Table~1 (no per-site retrieval here -- this panel is
# strictly a published-baseline comparison).

# Hayne (2017) Appendix A constants
_KS_HAYNE  = 7.4e-4    # W m^-1 K^-1, surface conductivity
_KD_HAYNE  = 3.4e-3    # W m^-1 K^-1, deep asymptote
_CHI_HAYNE = 2.7       # radiative coefficient
_TREF      = 350.0     # K, Hayne radiative normalisation

# Mart{\'\i}nez & Siegler (2021) published coefficients
_MS_A1, _MS_A2 = 5.0821e-6, -0.0051        # contact term
_MS_B1, _MS_B2 = 2.022e-13, -1.953e-10     # radiative term
# Woods-Robinson amorphous polynomial k_am(T), Mart{\'\i}nez 2021 App.
_MS_KAM = dict(
    A=-2.03297e-1, B=-11.472, C=22.5793, D=-14.3084, E=3.41742,
    F=0.01101, G=-2.80491e-5, H=3.35837e-8, I=-1.40021e-11)


def _k_hayne(T, z):
    """Hayne (2017) K(T, z) in W m^-1 K^-1."""
    T = np.asarray(T, float); z = np.asarray(z, float)
    rad = 1.0 + _CHI_HAYNE * (T / _TREF) ** 3
    env = _KS_HAYNE + (_KD_HAYNE - _KS_HAYNE) * (1.0 - np.exp(-z / H_PARAM))
    return env * rad


def _kam(T):
    r"""Woods-Robinson amorphous polynomial as used by Mart{\'\i}nez 2021."""
    T = np.asarray(T, float)
    a = _MS_KAM
    return (a["A"] + a["B"] * T**-4 + a["C"] * T**-3 + a["D"] * T**-2
            + a["E"] * T**-1 + a["F"] * T + a["G"] * T**2
            + a["H"] * T**3 + a["I"] * T**4)


def _k_martinez(T, z):
    r"""Mart{\'\i}nez \& Siegler (2021) K(T, rho(z)) in W m^-1 K^-1, with
    rho(z) the published Hayne-form exponential density profile."""
    T = np.asarray(T, float); z = np.asarray(z, float)
    rho = RHO_D - (RHO_D - RHO_S) * np.exp(-z / H_PARAM)
    contact   = (_MS_A1 * rho + _MS_A2) * _kam(T)
    radiative = (_MS_B1 * rho + _MS_B2) * T ** 3
    return contact + radiative


def _draw_kz_comparison(ax):
    """Right-hand panel of Fig 1: K(z) at T_0 = 250 K, both models."""
    T0 = 250.0                      # representative deep-lunar T (K)
    z_cm = np.linspace(0.0, 200.0, 400)
    z_m  = z_cm / 100.0

    K_hayne = _k_hayne(T0, z_m) * 1e3        # mW m^-1 K^-1
    K_mart  = _k_martinez(T0, z_m) * 1e3

    ax.set_facecolor(C_PAPER)
    ax.plot(K_hayne, z_cm, color=C_TEAL, lw=2.4,
            label=r"Hayne (2017): $K_d^\mathrm{publ.}=3.4$")
    ax.plot(K_mart,  z_cm, color=C_CORAL, lw=2.2, ls="--",
            label="Martínez & Siegler (2021): " r"$K(T,\rho)$")

    # mark the K_s (surface) and K_d^publ. (deep) anchor values lightly
    ax.axvline(_KS_HAYNE * 1e3 * (1 + _CHI_HAYNE * (T0/_TREF)**3),
               color=C_DIM, ls=(0, (1, 2)), lw=0.6, alpha=0.6)
    ax.axvline(_KD_HAYNE * 1e3 * (1 + _CHI_HAYNE * (T0/_TREF)**3),
               color=C_DIM, ls=(0, (1, 2)), lw=0.6, alpha=0.6)

    # borestem zone shading (matches the left panel's coral band)
    ax.axhspan(0, 80, color=C_CORAL, alpha=0.08, zorder=0)
    ax.plot(ax.get_xlim(), [80, 80], color=C_CORAL, lw=0.8,
            ls=(0, (4, 2)), alpha=0.55, zorder=1)

    ax.set_xlabel(r"$K$ at $T=250$ K  (mW m$^{-1}$ K$^{-1}$)",
                  fontsize=FS_LABEL)
    ax.set_ylabel("Depth  (cm)", fontsize=FS_LABEL)
    ax.set_ylim(200, 0)
    ax.set_xlim(0, max(K_hayne.max(), K_mart.max()) * 1.10)
    ax.set_title("(b)  Published $K(z)$: Hayne vs Martínez & Siegler",
                 fontsize=FS_TITLE, fontweight="bold", pad=8)
    ax.tick_params(labelsize=FS_TICK)
    ax.grid(color=C_GRID, lw=0.5)
    ax.set_axisbelow(True)
    # K(z) model legend lives in the shared figure-level strip below
    # (see fig_intro_probe); no in-panel legend here.


# ════════════════════════════════════════════════════════════════════════════
# Combined Fig 1: probe schematic (left) + K(z) comparison (right)
# ════════════════════════════════════════════════════════════════════════════
def fig_intro_probe():
    r"""Two-panel introduction figure: (a) Apollo HFE probe schematic,
    (b) published K(z) comparison between the Hayne (2017) form and
    the Mart{\'\i}nez \\& Siegler (2021) form, both evaluated at
    T = 250 K and at the same Hayne-form rho(z) so the visible
    difference is the K-formulation alone."""
    # Use a slightly wider figure so both panels can be the same visible
    # size without colliding.
    fig = plt.figure(figsize=(JGR_FULL + 0.5, 5.2))
    # Layout: two equally-sized visible blocks of width 0.42 each.
    # Panel (a)'s axes IS its visible block (no axis labels).
    # Panel (b)'s plot rectangle is narrower than 0.42 because its
    # y-axis labels live to the LEFT of the plot — so we make panel (b)
    # plot rectangle = 0.36 wide, and the y-axis labels add ~0.06,
    # bringing its visible block to ~0.42 too.
    ax_probe = fig.add_axes([0.04, 0.22, 0.42, 0.70])
    ax_kz    = fig.add_axes([0.56, 0.22, 0.42, 0.70])
    _draw_kz_comparison(ax_kz)
    # Embed the user-supplied probe schematic JPG (cropped to remove
    # white margins) and stretch it to fill the panel.
    from PIL import Image, ImageChops
    src_path = "/Users/rp3gregorio/Downloads/Apollo HFE probe configuration.jpg"
    pil_img = Image.open(src_path).convert("RGB")
    bg = Image.new("RGB", pil_img.size, (255, 255, 255))
    diff = ImageChops.difference(pil_img, bg)
    bbox = diff.point(lambda p: 0 if p < 15 else 255).getbbox()
    if bbox is not None:
        pil_img = pil_img.crop(bbox)
    probe_img = np.asarray(pil_img)
    ax_probe.imshow(probe_img, aspect="auto", interpolation="lanczos")
    ax_probe.set_aspect("auto")
    ax_probe.axis("off")

    # Shared figure-level legend strip below both panels.
    # Two row groups: (top) panel-(a) sensor types and borestem zone;
    # (bottom) panel-(b) K(z) model curves.
    deep_h = Line2D([0], [0], marker="s", color="white", lw=0,
                    ms=8, markerfacecolor=C_TEAL, mec="white", mew=0.9,
                    label="Deep sensor (used in retrieval)")
    shal_h = Line2D([0], [0], marker="s", color="white", lw=0,
                    ms=8, markerfacecolor=C_DIM, mec="white", mew=0.9,
                    label="Shallow sensor (borestem, excluded)")
    bore_h = Rectangle((0, 0), 1, 1, facecolor=C_CORAL, alpha=0.18,
                       edgecolor=C_CORAL, lw=1.1, linestyle="--",
                       label="Borestem zone ($z < 80$ cm)")
    hay_h  = Line2D([0], [0], color=C_TEAL, lw=2.4,
                    label=r"Hayne (2017) $K(z)$ at $K_d^{\mathrm{publ.}}=3.4$")
    mar_h  = Line2D([0], [0], color=C_CORAL, lw=2.2, ls="--",
                    label="Martínez & Siegler (2021) " r"$K(T,\rho)$")
    fig.legend(handles=[deep_h, shal_h, bore_h, hay_h, mar_h],
               loc="lower center", bbox_to_anchor=(0.5, 0.005),
               ncols=3, frameon=True, edgecolor=C_GRID, framealpha=0.97,
               fontsize=FS_TICK - 1, handlelength=2.2, borderpad=0.6,
               columnspacing=1.8)

    out = OUT / "fig_intro_probe.pdf"
    # High DPI keeps the embedded panel-(a) image crisp at column width.
    fig.savefig(out, dpi=450)
    plt.close(fig)
    print(f"  -> {out}")


if __name__ == "__main__":
    print("Generating introduction figures:")
    fig_intro_models()
    fig_intro_probe()
    print("Done.")
