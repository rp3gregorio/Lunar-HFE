#!/usr/bin/env python3
"""Clean slide graphics for the Apollo Kd presentation.

These are deterministic, PowerPoint-first figures. They avoid generated
backgrounds and keep labels outside the plotted data whenever possible.

Run:
    python pipeline/figures/make_ppt_graphs_clean.py
"""
from __future__ import annotations

import csv
import json
import pathlib
import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Circle, FancyArrowPatch, FancyBboxPatch, Rectangle
from matplotlib.lines import Line2D


ROOT = pathlib.Path(__file__).resolve().parents[2]
OUT = ROOT / "results" / "figures"
RESULTS = ROOT / "results"
sys.path.insert(0, str(ROOT / "src"))

from lunar.constants import (  # noqa: E402
    CHI_RADIATIVE,
    H_PARAMETER,
    K_DEEP,
    K_SURFACE,
    RHO_DEEP,
    RHO_SURFACE,
    T_REFERENCE,
)
from lunar.properties import conductivity_hayne, density_hayne  # noqa: E402


DPI = 240
SLIDE_W, SLIDE_H = 16.0, 9.0

C_CORAL = "#B85B3A"
C_CORAL_L = "#E5A88A"
C_TEAL = "#2A6478"
C_TEAL_L = "#7CA3B0"
C_FOREST = "#3D6E4A"
C_FOREST_L = "#94B89C"
C_PLUM = "#5A4A6A"
C_CHAR = "#2A2520"
C_DIM = "#6E6862"
C_NEUTRAL = "#A8A29A"
C_GRID = "#E8E5E0"
C_BG = "#FAF8F3"
C_SKIN = "#FFF1E9"
C_USED = "#EEF6F7"
C_DEEP = "#F3F0E8"

plt.rcParams.update(
    {
        "font.family": "serif",
        "font.serif": ["Times", "Times New Roman", "DejaVu Serif"],
        "mathtext.fontset": "dejavuserif",
        "figure.facecolor": C_BG,
        "savefig.facecolor": C_BG,
        "axes.facecolor": "white",
        "axes.edgecolor": C_CHAR,
        "axes.labelcolor": C_CHAR,
        "axes.titlecolor": C_CHAR,
        "xtick.color": C_CHAR,
        "ytick.color": C_CHAR,
        "font.size": 13,
        "axes.titlesize": 15,
        "axes.labelsize": 12,
        "xtick.labelsize": 10.5,
        "ytick.labelsize": 10.5,
        "legend.fontsize": 10.5,
        "savefig.bbox": "standard",
    }
)


def slide():
    fig = plt.figure(figsize=(SLIDE_W, SLIDE_H), dpi=DPI, facecolor=C_BG)
    ax = fig.add_axes([0, 0, 1, 1], facecolor=C_BG)
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")
    return fig, ax


def save(fig, stem: str):
    OUT.mkdir(parents=True, exist_ok=True)
    png = OUT / f"{stem}.png"
    pdf = OUT / f"{stem}.pdf"
    fig.savefig(png, dpi=DPI, facecolor=C_BG)
    fig.savefig(pdf, facecolor=C_BG)
    plt.close(fig)
    print(f"wrote {png}")
    print(f"wrote {pdf}")


def title(ax, text: str, subtitle: str):
    ax.text(0.045, 0.935, text, fontsize=30, fontweight="bold", color=C_CHAR, va="top")
    ax.text(0.046, 0.872, subtitle, fontsize=15.5, color=C_DIM, va="top")


def card(ax, xy, wh, text, *, edge=C_GRID, face="white", color=C_CHAR, fs=12.5,
         weight="normal", lw=1.25):
    x, y = xy
    w, h = wh
    patch = FancyBboxPatch(
        (x, y),
        w,
        h,
        boxstyle="round,pad=0.012,rounding_size=0.012",
        transform=ax.transAxes,
        facecolor=face,
        edgecolor=edge,
        linewidth=lw,
        zorder=5,
    )
    ax.add_patch(patch)
    ax.text(
        x + w / 2,
        y + h / 2,
        text,
        transform=ax.transAxes,
        ha="center",
        va="center",
        fontsize=fs,
        color=color,
        fontweight=weight,
        linespacing=1.15,
        zorder=6,
    )
    return patch


def arrow_fig(ax, start, end, *, color=C_DIM, lw=1.8, scale=13):
    ax.add_patch(
        FancyArrowPatch(
            start,
            end,
            transform=ax.transAxes,
            arrowstyle="-|>",
            mutation_scale=scale,
            linewidth=lw,
            color=color,
            shrinkA=6,
            shrinkB=6,
            zorder=7,
        )
    )


def style_plot(ax, *, grid=True):
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color(C_CHAR)
    ax.spines["bottom"].set_color(C_CHAR)
    if grid:
        ax.grid(color=C_GRID, linewidth=0.6)
        ax.set_axisbelow(True)


def sensor_depths(stem: str):
    path = ROOT / "data" / "apollo" / "depth" / f"{stem}_depth.tab"
    seen: dict[str, float] = {}
    with path.open(newline="") as f:
        for row in csv.DictReader(f):
            seen.setdefault(row["sensor"], float(row["depth"]))
    return sorted(seen.items(), key=lambda item: item[1])


def fig_hayne_layers():
    fig, ax0 = slide()
    title(
        ax0,
        "How the Hayne column is built",
        "The model is a smooth exponential depth structure plus a temperature-dependent radiative multiplier.",
    )

    # Formula rail.
    card(
        ax0,
        (0.055, 0.700),
        (0.255, 0.09),
        "$\\rho(z)=\\rho_d-(\\rho_d-\\rho_s)e^{-z/H}$",
        edge=C_FOREST_L,
        color=C_FOREST,
        fs=14,
        weight="bold",
    )
    card(
        ax0,
        (0.365, 0.700),
        (0.280, 0.09),
        "$K_c(z)=K_s+(K_d-K_s)(1-e^{-z/H})$",
        edge=C_TEAL_L,
        color=C_TEAL,
        fs=14,
        weight="bold",
    )
    card(
        ax0,
        (0.700, 0.700),
        (0.245, 0.09),
        "$K(T,z)=K_c(z)[1+\\chi(T/T_{ref})^3]$",
        edge=C_CORAL_L,
        color=C_CORAL,
        fs=14,
        weight="bold",
    )
    arrow_fig(ax0, (0.315, 0.745), (0.360, 0.745), color=C_DIM)
    arrow_fig(ax0, (0.650, 0.745), (0.695, 0.745), color=C_DIM)
    ax0.text(
        0.055,
        0.665,
        "$H=0.06$ m, $K_s=0.74$, $K_d^{publ.}=3.4$ mW m$^{-1}$ K$^{-1}$, "
        "$\\rho_s=1100$, $\\rho_d=1800$ kg m$^{-3}$, $\\chi=2.7$, $T_{ref}=350$ K",
        transform=ax0.transAxes,
        fontsize=12.2,
        color=C_DIM,
    )

    # Panel A: normalized depth structure.
    z = np.linspace(0.0, 1.0, 400)
    rho = density_hayne(z)
    kc = K_DEEP - (K_DEEP - K_SURFACE) * np.exp(-z / H_PARAMETER)
    rho_n = (rho - RHO_SURFACE) / (RHO_DEEP - RHO_SURFACE)
    kc_n = (kc - K_SURFACE) / (K_DEEP - K_SURFACE)

    axA = fig.add_axes([0.065, 0.155, 0.265, 0.425])
    axA.axhspan(0, H_PARAMETER, color=C_CORAL, alpha=0.10, lw=0)
    axA.axhspan(H_PARAMETER, 4 * H_PARAMETER, color=C_TEAL, alpha=0.075, lw=0)
    axA.axhspan(0.80, 1.0, color=C_DEEP, alpha=0.95, lw=0)
    axA.plot(rho_n, z * 100, color=C_FOREST, lw=2.6, label="$\\rho(z)$")
    axA.plot(kc_n, z * 100, color=C_TEAL, lw=2.6, label="$K_c(z)$")
    for depth, label, col in [
        (H_PARAMETER * 100, "$1H=6$ cm", C_CORAL),
        (4 * H_PARAMETER * 100, "$4H=24$ cm", C_TEAL),
        (80, "retrieval cut", C_DIM),
    ]:
        axA.axhline(depth, color=col, lw=1.1, ls=(0, (5, 4)))
        axA.text(1.02, depth, label, transform=axA.get_yaxis_transform(),
                 fontsize=9.5, color=col, va="center")
    axA.set_ylim(100, 0)
    axA.set_xlim(0, 1.05)
    axA.set_xlabel("fraction of asymptote")
    axA.set_ylabel("depth (cm)")
    axA.set_title("1. Depth structure approaches deep values", loc="left", fontweight="bold")
    axA.legend(loc="lower right", frameon=True, edgecolor=C_GRID)
    style_plot(axA)

    # Panel B: radiative multiplier.
    axB = fig.add_axes([0.392, 0.155, 0.235, 0.425])
    T = np.linspace(80, 370, 400)
    mult = 1.0 + CHI_RADIATIVE * (T / T_REFERENCE) ** 3
    axB.plot(T, mult, color=C_CORAL, lw=2.8)
    for temp in [150, 250, 350]:
        m = 1.0 + CHI_RADIATIVE * (temp / T_REFERENCE) ** 3
        axB.scatter([temp], [m], color=C_CORAL, s=45, zorder=4)
        axB.text(temp + 6, m + 0.05, f"{m:.2f}x", color=C_CORAL, fontsize=10.5)
    axB.set_xlim(80, 370)
    axB.set_ylim(1.0, 3.95)
    axB.set_xlabel("temperature (K)")
    axB.set_ylabel("multiplier")
    axB.set_title("2. Temperature opens radiative paths", loc="left", fontweight="bold")
    style_plot(axB)

    # Panel C: full K profiles at T = 250 K.
    axC = fig.add_axes([0.705, 0.155, 0.255, 0.425])
    kd_vals = [
        (3.40e-3, "published 3.40", C_DIM),
        (4.60e-3, "Apollo 15 4.60", C_FOREST),
        (7.08e-3, "Apollo 17 7.08", C_CORAL),
    ]
    for kd, label, col in kd_vals:
        kval = conductivity_hayne(np.full_like(z, 250.0), z, Kd=kd) * 1000
        axC.plot(kval, z * 100, color=col, lw=2.5, label=label)
    axC.axhline(80, color=C_DIM, lw=1.1, ls=(0, (5, 4)))
    axC.text(0.98, 80, "meter-scale sensors below", transform=axC.get_yaxis_transform(),
             ha="right", va="bottom", color=C_DIM, fontsize=9.5)
    axC.set_ylim(100, 0)
    axC.set_xlim(0.5, 14.8)
    axC.set_xlabel("$K(T=250\\,K,z)$ (mW m$^{-1}$ K$^{-1}$)")
    axC.set_yticklabels([])
    axC.set_title("3. The retrieved knob shifts the asymptote", loc="left", fontweight="bold")
    axC.legend(loc="lower right", frameon=True, edgecolor=C_GRID)
    style_plot(axC)

    ax0.text(
        0.055,
        0.050,
        "Key point for the talk: Hayne does not define hard geological layers. "
        "It defines a smooth compaction/conductivity transition with scale height H.\n"
        "Below the Apollo cut the shape is fixed; the retrieval changes the deep asymptote $K_d$.",
        transform=ax0.transAxes,
        fontsize=12.2,
        color=C_CHAR,
        fontweight="bold",
    )
    save(fig, "slide_hayne_layers")


def fig_probe_geometry():
    fig, ax0 = slide()
    title(
        ax0,
        "Apollo HFE measurement geometry",
        "Open markers are excluded shallow/borestem sensors; filled markers are the meter-scale data used in the retrieval.",
    )

    ax = fig.add_axes([0.065, 0.150, 0.615, 0.620])
    ax.set_facecolor("white")
    ax.axhspan(0, 80, color=C_SKIN, lw=0)
    ax.axhspan(80, 234, color=C_USED, lw=0)
    ax.axhspan(234, 250, color=C_DEEP, lw=0)
    ax.axhline(80, color=C_CORAL, lw=1.8, ls=(0, (6, 4)))
    ax.text(3.86, 76, "$z=80$ cm borestem cut", color=C_CORAL, fontsize=12.5, ha="right")

    probes = [
        ("A15 P1", "a15p1", 0.9, C_FOREST),
        ("A15 P2", "a15p2", 1.6, C_FOREST),
        ("A17 P1", "a17p1", 3.0, C_TEAL),
        ("A17 P2", "a17p2", 3.7, C_TEAL),
    ]
    for label, stem, x, col in probes:
        ax.plot([x, x], [0, 250], color=C_NEUTRAL, lw=5, solid_capstyle="round", zorder=2)
        for _, depth in sensor_depths(stem):
            if depth < 80:
                ax.scatter([x], [depth], s=78, facecolor="white", edgecolor=C_CORAL, lw=2.0, zorder=4)
            else:
                ax.scatter([x], [depth], s=78, facecolor=col, edgecolor="white", lw=1.0, zorder=4)
        ax.text(x, -12, label, ha="center", va="top", fontsize=12.5, fontweight="bold")
    ax.set_xlim(0.35, 4.25)
    ax.set_ylim(250, -20)
    ax.set_ylabel("depth (cm)")
    ax.set_xticks([])
    ax.set_yticks([0, 80, 130, 185, 234])
    ax.text(0.42, 34, "excluded\nshallow zone", color=C_CORAL, fontsize=12,
            fontweight="bold", va="center")
    ax.text(0.42, 154, "meter-scale\nretrieval zone", color=C_TEAL, fontsize=12,
            fontweight="bold", va="center")
    handles = [
        Line2D([0], [0], marker="o", lw=0, markerfacecolor="white",
               markeredgecolor=C_CORAL, markeredgewidth=2, markersize=8,
               label="excluded"),
        Line2D([0], [0], marker="o", lw=0, markerfacecolor=C_TEAL,
               markeredgecolor="white", markersize=8, label="used"),
    ]
    ax.legend(handles=handles, loc="lower right", frameon=True, edgecolor=C_GRID)
    style_plot(ax, grid=False)

    card(
        ax0,
        (0.720, 0.605),
        (0.225, 0.145),
        "Apollo 15\n7 used sensors\n84-139 cm",
        edge=C_FOREST_L,
        color=C_FOREST,
        fs=15,
        weight="bold",
    )
    card(
        ax0,
        (0.720, 0.395),
        (0.225, 0.145),
        "Apollo 17\n16 used sensors\n130-234 cm",
        edge=C_TEAL_L,
        color=C_TEAL,
        fs=15,
        weight="bold",
    )
    card(
        ax0,
        (0.720, 0.185),
        (0.225, 0.145),
        "Why cut at 80 cm?\nshallow amplitudes show\nborestem contamination",
        edge=C_CORAL_L,
        color=C_CORAL,
        fs=12.5,
        weight="bold",
    )
    save(fig, "slide_probe_geometry")


def fig_thermal_layers():
    fig, ax0 = slide()
    title(
        ax0,
        "Thermal process through the regolith",
        "The surface oscillates strongly; below the cut the cycle-mean profile carries the geothermal-flux signal.",
    )

    # Cross-section as an axes with data coordinates in depth.
    ax = fig.add_axes([0.055, 0.160, 0.890, 0.590])
    ax.set_xlim(0, 10)
    ax.set_ylim(260, -38)
    ax.axis("off")
    ax.add_patch(Rectangle((0, -38), 10, 38, facecolor="#F7FAFA", edgecolor="none"))
    ax.add_patch(Rectangle((0, 0), 10, 260, facecolor="#F4EEE3", edgecolor="none"))
    for z0, z1, col, alpha in [(0, 10, C_CORAL, 0.12), (10, 80, C_CORAL, 0.075),
                               (80, 234, C_TEAL, 0.105), (234, 260, C_FOREST, 0.085)]:
        ax.add_patch(Rectangle((0, z0), 10, z1 - z0, facecolor=col, alpha=alpha, edgecolor="none"))
    ax.plot([0, 10], [0, 0], color=C_CHAR, lw=2.0)
    ax.plot([0, 10], [80, 80], color=C_CORAL, lw=1.8, ls=(0, (6, 4)))
    ax.plot([0, 10], [234, 234], color=C_GRID, lw=1.5, ls=(0, (5, 4)))

    # Left zone labels.
    for y, head, note, col in [
        (5, "diurnal skin", "day-night wave", C_CORAL),
        (45, "borestem zone", "excluded", C_CORAL),
        (150, "meter-scale zone", "$T_{eq}$ sensors", C_TEAL),
        (247, "deep regolith", "$Q_b$ controls slope", C_FOREST),
    ]:
        ax.text(0.32, y, head, color=col, fontsize=14.5, fontweight="bold", va="center")
        ax.text(1.82, y, note, color=C_DIM, fontsize=12.5, va="center")

    # Surface forcing.
    ax.scatter([0.92], [-25], s=980, facecolor="#F3CC67", edgecolor="#C99731",
               lw=1.2, zorder=5)
    ax.text(0.92, -25, "Sun", color="#8B641E", fontsize=11.5,
            ha="center", va="center", fontweight="bold", zorder=6)
    ax.annotate("absorbed sunlight", xy=(2.45, -3), xytext=(2.20, -25),
                color="#9B6E21", fontsize=12.5,
                arrowprops=dict(arrowstyle="-|>", color="#C99731", lw=2.0))
    for x in [4.1, 4.55, 5.0]:
        ax.annotate("", xy=(x, -31), xytext=(x - 0.12, -6),
                    arrowprops=dict(arrowstyle="-|>", color=C_CORAL, lw=2.0))
    ax.text(5.35, -25, "thermal radiation\nto space", color=C_CORAL, fontsize=12.5, va="center")

    # Probe and sensors.
    x_probe = 3.15
    ax.plot([x_probe, x_probe], [0, 234], color=C_NEUTRAL, lw=6, solid_capstyle="round", zorder=3)
    for d in [14, 66, 130, 140, 167, 177, 185, 195, 223, 234]:
        if d < 80:
            ax.scatter([x_probe], [d], s=65, facecolor="white", edgecolor=C_CORAL, lw=1.8, zorder=4)
        else:
            ax.scatter([x_probe], [d], s=65, facecolor=C_TEAL, edgecolor="white", lw=1.0, zorder=4)
    ax.text(x_probe + 0.28, 48, "borestem", color=C_DIM, fontsize=11.5, va="center")

    # Wave and mean profile.
    z = np.linspace(0, 238, 500)
    amp = np.exp(-z / 22.0)
    x_wave = 5.35 + 0.43 * amp * np.sin(z / 6.8)
    ax.plot(x_wave, z, color=C_CORAL, lw=2.8)
    ax.text(5.92, 38, "temperature wave\nattenuates", color=C_CORAL,
            fontsize=13.5, fontweight="bold", va="center")
    z2 = np.array([80, 130, 185, 234])
    x2 = np.array([7.25, 7.45, 7.72, 7.98])
    ax.plot(x2, z2, color=C_TEAL, lw=3.2)
    ax.text(8.12, 155, "cycle-mean\n$\\langle T(z)\\rangle$", color=C_TEAL,
            fontsize=13.5, fontweight="bold", va="center")
    for x in [8.6, 9.05, 9.5]:
        ax.annotate("", xy=(x, 230), xytext=(x, 258),
                    arrowprops=dict(arrowstyle="-|>", color=C_FOREST, lw=2.4))
    ax.text(9.05, 267, "basal heat flux $Q_b$", color=C_FOREST,
            fontsize=14, fontweight="bold", ha="center", va="top")
    ax.text(9.65, 10, "10 cm", color=C_DIM, fontsize=11)
    ax.text(9.65, 80, "80 cm", color=C_DIM, fontsize=11, va="bottom")
    ax.text(9.65, 234, "234 cm", color=C_DIM, fontsize=11, va="bottom")

    card(
        ax0,
        (0.365, 0.055),
        (0.270, 0.075),
        "$\\rho c_p\\,\\partial_tT=\\partial_z(K\\,\\partial_zT)$",
        edge=C_GRID,
        fs=14,
        weight="bold",
    )
    card(
        ax0,
        (0.670, 0.055),
        (0.220, 0.075),
        "$-K\\,\\partial_zT=Q_b$",
        edge=C_TEAL_L,
        color=C_TEAL,
        fs=15,
        weight="bold",
    )
    save(fig, "slide_thermal_layers")


def fig_retrieval_pipeline():
    fig, ax0 = slide()
    title(
        ax0,
        "Retrieval pipeline",
        "A physical forward model is wrapped by a one-parameter search over $K_d$.",
    )

    top = [
        ((0.070, 0.690), "Apollo HFE data\n$T(z,t)$", C_FOREST),
        ((0.310, 0.690), "Hayne thermophysics\n$K(T,z),\\rho(z),c_p(T)$", C_TEAL),
        ((0.550, 0.690), "Published heat flux\n$Q_b$ for each site", C_PLUM),
    ]
    for xy, text, col in top:
        card(ax0, xy, (0.190, 0.105), text, edge=col, color=C_CHAR, fs=13.2, weight="bold")

    steps = [
        ((0.060, 0.470), "1\nstable windows\n$T_{eq}$ per sensor", C_FOREST),
        ((0.285, 0.470), "2\nforward solve\ntrial $K_d$", C_TEAL),
        ((0.510, 0.470), "3\nscore RMSE\nvs. Apollo", C_CORAL),
        ((0.735, 0.470), "4\nminimum +\nuncertainty", C_PLUM),
    ]
    for i, (xy, text, col) in enumerate(steps):
        card(ax0, xy, (0.170, 0.130), text, edge=col, color=C_CHAR, fs=13.5, weight="bold")
        if i < len(steps) - 1:
            arrow_fig(ax0, (xy[0] + 0.175, xy[1] + 0.065), (steps[i + 1][0][0] - 0.005, xy[1] + 0.065))
    for start_x in [0.165, 0.405, 0.645]:
        arrow_fig(ax0, (start_x, 0.680), (0.370, 0.608), color=C_DIM, lw=1.4, scale=11)

    card(
        ax0,
        (0.775, 0.680),
        (0.165, 0.105),
        "$K_d^*$  (mW m$^{-1}$ K$^{-1}$)\nA15  4.60\nA17  7.08",
        edge=C_TEAL,
        color=C_TEAL,
        fs=12.8,
        weight="bold",
    )

    ax = fig.add_axes([0.085, 0.120, 0.440, 0.255])
    with (RESULTS / "kd_retrieval_results.json").open() as f:
        data = json.load(f)
    for site, col, label in [("A15", C_FOREST, "Apollo 15"), ("A17", C_CORAL, "Apollo 17")]:
        kd = np.array(data[site]["kd_grid"]) * 1000.0
        rmse = np.array(data[site]["rmse_curve"])
        order = np.argsort(kd)
        ax.plot(kd[order], rmse[order], color=col, lw=2.5, label=label)
        kstar = data[site]["kd_star"] * 1000.0
        rstar = data[site]["rmse_star"]
        ax.scatter([kstar], [rstar], s=55, color=col, edgecolor="white", lw=0.8, zorder=5)
        ax.text(kstar + 0.18, rstar + 0.10, f"{kstar:.2f}", color=col, fontsize=10.5,
                fontweight="bold")
    ax.set_xlim(1, 15)
    ax.set_ylim(0.25, 6.8)
    ax.set_xlabel("$K_d$ (mW m$^{-1}$ K$^{-1}$)")
    ax.set_ylabel("RMSE (K)")
    ax.set_title("The retrieved value is the RMSE minimum", loc="left", fontweight="bold")
    ax.legend(loc="upper right", frameon=True, edgecolor=C_GRID)
    style_plot(ax)

    card(
        ax0,
        (0.600, 0.145),
        (0.315, 0.170),
        "Interpretation:\nchange $K_d$, rerun the column,\ncompare only the meter-scale sensors.",
        edge=C_GRID,
        fs=13.2,
        color=C_CHAR,
    )
    save(fig, "slide_retrieval_pipeline")


def fig_anchor_vs_bruteforce():
    fig, ax0 = slide()
    title(
        ax0,
        "Flux-anchored solve vs. brute-force spin-up",
        "Same steady-state target; the shortcut avoids waiting for deep diffusion to relax.",
    )

    with (RESULTS / "speedup_benchmark.json").open() as f:
        speed = json.load(f)

    # Panel frames.
    card(ax0, (0.060, 0.150), (0.400, 0.585), "", edge=C_GRID, face="white")
    card(ax0, (0.540, 0.150), (0.400, 0.585), "", edge=C_GRID, face="white")
    ax0.text(0.085, 0.690, "brute force", transform=ax0.transAxes, fontsize=22,
             fontweight="bold", color=C_CORAL, zorder=10)
    ax0.text(0.565, 0.690, "flux-anchored", transform=ax0.transAxes, fontsize=22,
             fontweight="bold", color=C_TEAL, zorder=10)

    def column(x0, y0, w, h, *, anchor=False):
        ax0.add_patch(Rectangle((x0, y0), w, h, transform=ax0.transAxes,
                                facecolor="#E8DDCA", edgecolor=C_DIM, lw=1.2, zorder=8))
        ax0.add_patch(Rectangle((x0, y0 + 0.84 * h), w, 0.16 * h,
                                transform=ax0.transAxes, facecolor=C_CORAL,
                                alpha=0.15, edgecolor="none", zorder=9))
        if anchor:
            ya = y0 + 0.89 * h
            ax0.plot([x0, x0 + w], [ya, ya], transform=ax0.transAxes,
                     color=C_TEAL, lw=1.6, ls=(0, (5, 3)), zorder=10)
            ax0.text(x0 + w + 0.015, ya, "anchor\n0.55 m", transform=ax0.transAxes,
                     fontsize=10.5, color=C_TEAL, va="center")
        return x0, y0, w, h

    bx, by, bw, bh = column(0.145, 0.235, 0.095, 0.365)
    for offs, col in [(0.015, C_CORAL), (0.030, C_CORAL_L), (0.048, C_NEUTRAL), (0.060, C_NEUTRAL)]:
        ax0.plot([bx + offs, bx + offs + 0.03], [by + bh, by],
                 transform=ax0.transAxes, color=col, lw=1.8, zorder=11)
    ax0.text(0.305, 0.565, "time-step the\nwhole column", transform=ax0.transAxes,
             ha="center", fontsize=13.5, color=C_CORAL, fontweight="bold", zorder=10)
    ax0.text(0.305, 0.445, "deep cells relax\nonly by slow diffusion", transform=ax0.transAxes,
             ha="center", fontsize=12.8, color=C_DIM, zorder=10)
    card(
        ax0,
        (0.282, 0.275),
        (0.135, 0.090),
        f"~{speed['N_converge_lun']:,}\nlunations",
        edge=C_CORAL_L,
        face="#FFF8F4",
        color=C_CORAL,
        fs=13.8,
        weight="bold",
    )

    cx, cy, cw, ch = column(0.625, 0.235, 0.095, 0.365, anchor=True)
    # Skin wiggle and reconstructed line.
    t = np.linspace(0, 1, 100)
    ax0.plot(cx + 0.042 + 0.013 * np.sin(28 * t) * np.exp(-3.5 * t),
             cy + ch * (1 - 0.16 * t), transform=ax0.transAxes,
             color=C_CORAL, lw=2.1, zorder=11)
    ax0.plot([cx + 0.052, cx + 0.070], [cy + 0.89 * ch, cy],
             transform=ax0.transAxes, color=C_TEAL, lw=2.7, zorder=11)
    ax0.text(0.775, 0.615, "Step A:\ntime-step shallow skin", transform=ax0.transAxes,
             fontsize=13.0, color=C_CORAL, va="center", zorder=10)
    ax0.text(0.775, 0.365, "Step B:\nreconstruct deep profile\nfrom flux closure",
             transform=ax0.transAxes, fontsize=13.0, color=C_TEAL, va="center", zorder=10)
    arrow_fig(ax0, (0.728, 0.615), (0.765, 0.615), color=C_CORAL)
    arrow_fig(ax0, (0.728, 0.430), (0.765, 0.375), color=C_TEAL)
    card(
        ax0,
        (0.757, 0.455),
        (0.115, 0.085),
        f"~{speed['speedup_per_solve']:.0f}x\nper solve",
        edge=C_TEAL_L,
        face="#F5FAFB",
        color=C_TEAL,
        fs=13.5,
        weight="bold",
    )

    card(
        ax0,
        (0.215, 0.055),
        (0.570, 0.070),
        "The method changes the route to equilibrium, not the equilibrium condition.",
        edge=C_GRID,
        fs=14.2,
        weight="bold",
    )
    save(fig, "slide_anchor_vs_bruteforce")


def main():
    fig_hayne_layers()
    fig_probe_geometry()
    fig_thermal_layers()
    fig_retrieval_pipeline()
    fig_anchor_vs_bruteforce()


if __name__ == "__main__":
    main()
