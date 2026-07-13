#!/usr/bin/env python3
"""Build cropped, insertable PowerPoint figure assets.

These are not full slides. They are transparent-background figures meant to
be placed inside the user's own slide layouts.

Run:
    python pipeline/figures/make_ppt_images.py
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
from matplotlib.lines import Line2D
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch, Rectangle

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

DPI = 300

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
C_SKIN = "#FFF1E9"
C_USED = "#EEF6F7"
C_DEEP = "#F3F0E8"
C_PANEL = "#FFFFFF"

plt.rcParams.update(
    {
        "font.family": "serif",
        "font.serif": ["Times", "Times New Roman", "DejaVu Serif"],
        "mathtext.fontset": "dejavuserif",
        "figure.facecolor": "none",
        "savefig.facecolor": "none",
        "axes.facecolor": C_PANEL,
        "axes.edgecolor": C_CHAR,
        "axes.labelcolor": C_CHAR,
        "axes.titlecolor": C_CHAR,
        "xtick.color": C_CHAR,
        "ytick.color": C_CHAR,
        "font.size": 12,
        "axes.titlesize": 13.5,
        "axes.labelsize": 11,
        "xtick.labelsize": 9.5,
        "ytick.labelsize": 9.5,
        "legend.fontsize": 9.5,
    }
)


def save(fig: plt.Figure, stem: str):
    OUT.mkdir(parents=True, exist_ok=True)
    png = OUT / f"{stem}.png"
    pdf = OUT / f"{stem}.pdf"
    fig.savefig(png, dpi=DPI, transparent=True, bbox_inches="tight", pad_inches=0.04)
    fig.savefig(pdf, transparent=True, bbox_inches="tight", pad_inches=0.04)
    plt.close(fig)
    print(f"wrote {png}")
    print(f"wrote {pdf}")


def root_ax(fig: plt.Figure):
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")
    return ax


def card(ax, xy, wh, text, *, edge=C_GRID, face=C_PANEL, color=C_CHAR, fs=12,
         weight="normal", lw=1.2):
    x, y = xy
    w, h = wh
    patch = FancyBboxPatch(
        (x, y),
        w,
        h,
        boxstyle="round,pad=0.010,rounding_size=0.014",
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
        linespacing=1.12,
        zorder=6,
    )
    return patch


def arrow(ax, start, end, *, color=C_DIM, lw=1.7, scale=12):
    ax.add_patch(
        FancyArrowPatch(
            start,
            end,
            transform=ax.transAxes,
            arrowstyle="-|>",
            mutation_scale=scale,
            linewidth=lw,
            color=color,
            shrinkA=5,
            shrinkB=5,
            zorder=7,
        )
    )


def style_plot(ax, *, grid=True):
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color(C_CHAR)
    ax.spines["bottom"].set_color(C_CHAR)
    if grid:
        ax.grid(color=C_GRID, linewidth=0.55)
        ax.set_axisbelow(True)


def sensor_depths(stem: str):
    path = ROOT / "data" / "apollo" / "depth" / f"{stem}_depth.tab"
    seen: dict[str, float] = {}
    with path.open(newline="") as f:
        for row in csv.DictReader(f):
            seen.setdefault(row["sensor"], float(row["depth"]))
    return sorted(seen.items(), key=lambda item: item[1])


def image_hayne_layers():
    fig = plt.figure(figsize=(11.2, 5.35), dpi=DPI)
    ax0 = root_ax(fig)

    card(
        ax0,
        (0.015, 0.805),
        (0.285, 0.115),
        "$\\rho(z)=\\rho_d-(\\rho_d-\\rho_s)e^{-z/H}$",
        edge=C_FOREST_L,
        color=C_FOREST,
        fs=12.5,
        weight="bold",
    )
    card(
        ax0,
        (0.365, 0.805),
        (0.305, 0.115),
        "$K_c(z)=K_s+(K_d-K_s)(1-e^{-z/H})$",
        edge=C_TEAL_L,
        color=C_TEAL,
        fs=12.5,
        weight="bold",
    )
    card(
        ax0,
        (0.735, 0.805),
        (0.250, 0.115),
        "$K(T,z)=K_c(z)[1+\\chi(T/T_{ref})^3]$",
        edge=C_CORAL_L,
        color=C_CORAL,
        fs=12.5,
        weight="bold",
    )
    arrow(ax0, (0.305, 0.862), (0.360, 0.862), color=C_DIM)
    arrow(ax0, (0.675, 0.862), (0.730, 0.862), color=C_DIM)
    ax0.text(
        0.018,
        0.750,
        "$H=0.06$ m, $K_s=0.74$, $K_d^{publ.}=3.4$ mW m$^{-1}$ K$^{-1}$, "
        "$\\rho_s=1100$, $\\rho_d=1800$ kg m$^{-3}$, $\\chi=2.7$",
        transform=ax0.transAxes,
        fontsize=10.5,
        color=C_DIM,
    )

    z = np.linspace(0.0, 1.0, 400)
    rho = density_hayne(z)
    kc = K_DEEP - (K_DEEP - K_SURFACE) * np.exp(-z / H_PARAMETER)
    rho_n = (rho - RHO_SURFACE) / (RHO_DEEP - RHO_SURFACE)
    kc_n = (kc - K_SURFACE) / (K_DEEP - K_SURFACE)

    axA = fig.add_axes([0.035, 0.185, 0.290, 0.470])
    axA.axhspan(0, H_PARAMETER, color=C_CORAL, alpha=0.10, lw=0)
    axA.axhspan(H_PARAMETER, 4 * H_PARAMETER, color=C_TEAL, alpha=0.075, lw=0)
    axA.plot(rho_n, z * 100, color=C_FOREST, lw=2.3, label="$\\rho(z)$")
    axA.plot(kc_n, z * 100, color=C_TEAL, lw=2.3, label="$K_c(z)$")
    for depth, label, col in [
        (H_PARAMETER * 100, "$1H=6$ cm", C_CORAL),
        (4 * H_PARAMETER * 100, "$4H=24$ cm", C_TEAL),
        (80, "80 cm cut", C_DIM),
    ]:
        axA.axhline(depth, color=col, lw=1.0, ls=(0, (5, 4)))
        axA.text(1.015, depth, label, transform=axA.get_yaxis_transform(),
                 fontsize=8.5, color=col, va="center")
    axA.set_ylim(100, 0)
    axA.set_xlim(0, 1.05)
    axA.set_xlabel("fraction of asymptote")
    axA.set_ylabel("depth (cm)")
    axA.set_title("smooth depth transition", loc="left", fontweight="bold")
    axA.legend(loc="lower right", frameon=True, edgecolor=C_GRID)
    style_plot(axA)

    axB = fig.add_axes([0.390, 0.185, 0.245, 0.470])
    T = np.linspace(80, 370, 400)
    mult = 1.0 + CHI_RADIATIVE * (T / T_REFERENCE) ** 3
    axB.plot(T, mult, color=C_CORAL, lw=2.5)
    for temp in [150, 250, 350]:
        m = 1.0 + CHI_RADIATIVE * (temp / T_REFERENCE) ** 3
        axB.scatter([temp], [m], color=C_CORAL, s=36, zorder=4)
        axB.text(temp + 5, m + 0.04, f"{m:.2f}x", color=C_CORAL, fontsize=8.8)
    axB.set_xlim(80, 370)
    axB.set_ylim(1.0, 3.95)
    axB.set_xlabel("temperature (K)")
    axB.set_ylabel("radiative multiplier")
    axB.set_title("temperature multiplier", loc="left", fontweight="bold")
    style_plot(axB)

    axC = fig.add_axes([0.710, 0.185, 0.265, 0.470])
    for kd, label, col in [
        (3.40e-3, "published 3.40", C_DIM),
        (4.60e-3, "A15 4.60", C_FOREST),
        (7.08e-3, "A17 7.08", C_CORAL),
    ]:
        kval = conductivity_hayne(np.full_like(z, 250.0), z, Kd=kd) * 1000
        axC.plot(kval, z * 100, color=col, lw=2.3, label=label)
    axC.axhline(80, color=C_DIM, lw=1.0, ls=(0, (5, 4)))
    axC.set_ylim(100, 0)
    axC.set_xlim(0.5, 14.8)
    axC.set_xlabel("$K(T=250\\,K,z)$ (mW m$^{-1}$ K$^{-1}$)")
    axC.set_yticklabels([])
    axC.set_title("retrieved knob shifts $K_d$", loc="left", fontweight="bold")
    axC.legend(loc="lower right", frameon=True, edgecolor=C_GRID)
    style_plot(axC)

    save(fig, "fig_hayne_layers")


def image_probe_geometry():
    fig = plt.figure(figsize=(8.4, 4.55), dpi=DPI)
    ax = fig.add_axes([0.09, 0.14, 0.86, 0.78])
    ax.axhspan(0, 80, color=C_SKIN, lw=0)
    ax.axhspan(80, 234, color=C_USED, lw=0)
    ax.axhspan(234, 250, color=C_DEEP, lw=0)
    ax.axhline(80, color=C_CORAL, lw=1.6, ls=(0, (6, 4)))
    ax.text(4.16, 76, "$z=80$ cm cut", color=C_CORAL, fontsize=11, ha="right")
    for label, stem, x, col in [
        ("A15 P1", "a15p1", 0.9, C_FOREST),
        ("A15 P2", "a15p2", 1.6, C_FOREST),
        ("A17 P1", "a17p1", 3.0, C_TEAL),
        ("A17 P2", "a17p2", 3.7, C_TEAL),
    ]:
        ax.plot([x, x], [0, 250], color=C_NEUTRAL, lw=4.6, solid_capstyle="round", zorder=2)
        for _, depth in sensor_depths(stem):
            if depth < 80:
                ax.scatter([x], [depth], s=62, facecolor="white", edgecolor=C_CORAL, lw=1.8, zorder=4)
            else:
                ax.scatter([x], [depth], s=62, facecolor=col, edgecolor="white", lw=0.9, zorder=4)
        ax.text(x, -12, label, ha="center", va="top", fontsize=11.5, fontweight="bold")
    ax.text(0.43, 36, "excluded\nshallow zone", color=C_CORAL, fontsize=10.7,
            fontweight="bold", va="center")
    ax.text(0.43, 154, "meter-scale\nretrieval zone", color=C_TEAL, fontsize=10.7,
            fontweight="bold", va="center")
    handles = [
        Line2D([0], [0], marker="o", lw=0, markerfacecolor="white",
               markeredgecolor=C_CORAL, markeredgewidth=1.8, markersize=7, label="excluded"),
        Line2D([0], [0], marker="o", lw=0, markerfacecolor=C_TEAL,
               markeredgecolor="white", markersize=7, label="used"),
    ]
    ax.legend(handles=handles, loc="lower right", frameon=True, edgecolor=C_GRID)
    ax.set_xlim(0.30, 4.25)
    ax.set_ylim(250, -18)
    ax.set_ylabel("depth (cm)")
    ax.set_xticks([])
    ax.set_yticks([0, 80, 130, 185, 234])
    style_plot(ax, grid=False)
    save(fig, "fig_probe_geometry")


def image_thermal_process():
    fig = plt.figure(figsize=(9.8, 3.85), dpi=DPI)
    ax = fig.add_axes([0.03, 0.10, 0.94, 0.82])
    ax.set_xlim(0, 10)
    ax.set_ylim(260, -58)
    ax.axis("off")
    ax.add_patch(Rectangle((0, -58), 10, 58, facecolor="#F7FAFA", edgecolor="none"))
    ax.add_patch(Rectangle((0, 0), 10, 260, facecolor="#F4EEE3", edgecolor="none"))
    for z0, z1, col, alpha in [
        (0, 10, C_CORAL, 0.12),
        (10, 80, C_CORAL, 0.075),
        (80, 234, C_TEAL, 0.105),
        (234, 260, C_FOREST, 0.085),
    ]:
        ax.add_patch(Rectangle((0, z0), 10, z1 - z0, facecolor=col, alpha=alpha, edgecolor="none"))
    ax.plot([0, 10], [0, 0], color=C_CHAR, lw=1.8)
    ax.plot([0, 10], [80, 80], color=C_CORAL, lw=1.6, ls=(0, (6, 4)))
    ax.plot([0, 10], [234, 234], color="white", lw=1.1, ls=(0, (5, 4)))

    for y, head, note, col in [
        (5, "diurnal skin", "day-night wave", C_CORAL),
        (45, "borestem zone", "excluded", C_CORAL),
        (150, "meter-scale zone", "$T_{eq}$ sensors", C_TEAL),
        (247, "deep regolith", "$Q_b$ controls slope", C_FOREST),
    ]:
        ax.text(0.32, y, head, color=col, fontsize=12.5, fontweight="bold", va="center")
        ax.text(1.80, y, note, color=C_DIM, fontsize=10.8, va="center")

    ax.scatter([0.92], [-37], s=620, facecolor="#F3CC67", edgecolor="#C99731", lw=1.1, zorder=5)
    ax.text(0.92, -37, "Sun", color="#8B641E", fontsize=9.0, ha="center", va="center",
            fontweight="bold", zorder=6)
    ax.annotate("absorbed sunlight", xy=(2.45, -3), xytext=(2.12, -37),
                color="#9B6E21", fontsize=10.5,
                arrowprops=dict(arrowstyle="-|>", color="#C99731", lw=1.7))
    for x in [4.0, 4.45, 4.9]:
        ax.annotate("", xy=(x, -42), xytext=(x - 0.12, -8),
                    arrowprops=dict(arrowstyle="-|>", color=C_CORAL, lw=1.7))
    ax.text(5.25, -37, "thermal radiation\nto space", color=C_CORAL, fontsize=10.5, va="center")

    x_probe = 3.15
    ax.plot([x_probe, x_probe], [0, 234], color=C_NEUTRAL, lw=5.2, solid_capstyle="round", zorder=3)
    for d in [14, 66, 130, 140, 167, 177, 185, 195, 223, 234]:
        if d < 80:
            ax.scatter([x_probe], [d], s=54, facecolor="white", edgecolor=C_CORAL, lw=1.5, zorder=4)
        else:
            ax.scatter([x_probe], [d], s=54, facecolor=C_TEAL, edgecolor="white", lw=0.8, zorder=4)
    ax.text(x_probe + 0.27, 47, "borestem", color=C_DIM, fontsize=10, va="center")

    z = np.linspace(0, 238, 500)
    amp = np.exp(-z / 22.0)
    x_wave = 5.35 + 0.43 * amp * np.sin(z / 6.8)
    ax.plot(x_wave, z, color=C_CORAL, lw=2.5)
    ax.text(5.92, 38, "temperature wave\nattenuates", color=C_CORAL,
            fontsize=11.5, fontweight="bold", va="center")
    ax.plot([7.25, 7.45, 7.72, 7.98], [80, 130, 185, 234], color=C_TEAL, lw=3.0)
    ax.text(8.12, 155, "cycle-mean\n$\\langle T(z)\\rangle$", color=C_TEAL,
            fontsize=11.5, fontweight="bold", va="center")
    for x in [8.6, 9.05, 9.5]:
        ax.annotate("", xy=(x, 230), xytext=(x, 258),
                    arrowprops=dict(arrowstyle="-|>", color=C_FOREST, lw=2.0))
    ax.text(9.05, 266, "basal heat flux $Q_b$", color=C_FOREST,
            fontsize=11.8, fontweight="bold", ha="center", va="top")
    ax.text(9.65, 10, "10 cm", color=C_DIM, fontsize=9.5)
    ax.text(9.65, 80, "80 cm", color=C_DIM, fontsize=9.5, va="bottom")
    ax.text(9.65, 234, "234 cm", color=C_DIM, fontsize=9.5, va="bottom")
    save(fig, "fig_thermal_process")


def image_retrieval_pipeline():
    fig = plt.figure(figsize=(10.4, 4.8), dpi=DPI)
    ax0 = root_ax(fig)

    for xy, text, col in [
        ((0.04, 0.705), "Apollo HFE data\n$T(z,t)$", C_FOREST),
        ((0.325, 0.705), "Hayne thermophysics\n$K(T,z),\\rho(z),c_p(T)$", C_TEAL),
        ((0.610, 0.705), "Published heat flux\n$Q_b$ for each site", C_PLUM),
    ]:
        card(ax0, xy, (0.205, 0.145), text, edge=col, fs=11.8, weight="bold")

    steps = [
        ((0.035, 0.425), "1\nstable windows\n$T_{eq}$ per sensor", C_FOREST),
        ((0.288, 0.425), "2\nforward solve\ntrial $K_d$", C_TEAL),
        ((0.541, 0.425), "3\nscore RMSE\nvs. Apollo", C_CORAL),
        ((0.794, 0.425), "4\nminimum +\nuncertainty", C_PLUM),
    ]
    for i, (xy, text, col) in enumerate(steps):
        card(ax0, xy, (0.180, 0.160), text, edge=col, fs=11.7, weight="bold")
        if i < len(steps) - 1:
            arrow(ax0, (xy[0] + 0.185, xy[1] + 0.080), (steps[i + 1][0][0] - 0.004, xy[1] + 0.080))
    for start_x in [0.145, 0.430, 0.715]:
        arrow(ax0, (start_x, 0.700), (0.388, 0.595), color=C_DIM, lw=1.35, scale=10)

    ax = fig.add_axes([0.08, 0.070, 0.445, 0.250])
    with (RESULTS / "kd_retrieval_results.json").open() as f:
        data = json.load(f)
    for site, col, label in [("A15", C_FOREST, "Apollo 15"), ("A17", C_CORAL, "Apollo 17")]:
        kd = np.array(data[site]["kd_grid"]) * 1000.0
        rmse = np.array(data[site]["rmse_curve"])
        order = np.argsort(kd)
        ax.plot(kd[order], rmse[order], color=col, lw=2.2, label=label)
        kstar = data[site]["kd_star"] * 1000.0
        rstar = data[site]["rmse_star"]
        ax.scatter([kstar], [rstar], s=42, color=col, edgecolor="white", lw=0.7, zorder=5)
        ax.text(kstar + 0.18, rstar + 0.10, f"{kstar:.2f}", color=col, fontsize=9.2,
                fontweight="bold")
    ax.set_xlim(1, 15)
    ax.set_ylim(0.25, 6.8)
    ax.set_xlabel("$K_d$ (mW m$^{-1}$ K$^{-1}$)")
    ax.set_ylabel("RMSE (K)")
    ax.set_title("RMSE minimum", loc="left", fontweight="bold")
    ax.legend(loc="upper right", frameon=True, edgecolor=C_GRID)
    style_plot(ax)

    card(
        ax0,
        (0.620, 0.115),
        (0.300, 0.160),
        "$K_d^*$  (mW m$^{-1}$ K$^{-1}$)\nApollo 15   4.60\nApollo 17   7.08",
        edge=C_TEAL,
        color=C_TEAL,
        fs=12.0,
        weight="bold",
    )
    save(fig, "fig_retrieval_pipeline")


def image_anchor_vs_bruteforce():
    fig = plt.figure(figsize=(8.8, 4.25), dpi=DPI)
    ax0 = root_ax(fig)
    with (RESULTS / "speedup_benchmark.json").open() as f:
        speed = json.load(f)

    card(ax0, (0.030, 0.130), (0.425, 0.750), "", edge=C_GRID)
    card(ax0, (0.545, 0.130), (0.425, 0.750), "", edge=C_GRID)
    ax0.text(0.070, 0.805, "brute force", transform=ax0.transAxes, fontsize=17.5,
             fontweight="bold", color=C_CORAL, zorder=10)
    ax0.text(0.585, 0.805, "flux-anchored", transform=ax0.transAxes, fontsize=17.5,
             fontweight="bold", color=C_TEAL, zorder=10)

    def column(x0, y0, w, h, *, anchor_line=False):
        ax0.add_patch(Rectangle((x0, y0), w, h, transform=ax0.transAxes,
                                facecolor="#E8DDCA", edgecolor=C_DIM, lw=1.1, zorder=8))
        ax0.add_patch(Rectangle((x0, y0 + 0.84 * h), w, 0.16 * h,
                                transform=ax0.transAxes, facecolor=C_CORAL,
                                alpha=0.14, edgecolor="none", zorder=9))
        if anchor_line:
            ya = y0 + 0.89 * h
            ax0.plot([x0, x0 + w], [ya, ya], transform=ax0.transAxes,
                     color=C_TEAL, lw=1.5, ls=(0, (5, 3)), zorder=10)
        return x0, y0, w, h

    bx, by, bw, bh = column(0.140, 0.255, 0.100, 0.445)
    for offs, col in [(0.016, C_CORAL), (0.032, C_CORAL_L), (0.053, C_NEUTRAL), (0.066, C_NEUTRAL)]:
        ax0.plot([bx + offs, bx + offs + 0.032], [by + bh, by],
                 transform=ax0.transAxes, color=col, lw=1.6, zorder=11)
    ax0.text(0.305, 0.645, "time-step the\nwhole column", transform=ax0.transAxes,
             ha="left", fontsize=11.0, color=C_CORAL, fontweight="bold", zorder=10)
    ax0.text(0.305, 0.500, "deep cells relax\nby slow diffusion", transform=ax0.transAxes,
             ha="left", fontsize=10.2, color=C_DIM, zorder=10)
    card(
        ax0,
        (0.285, 0.270),
        (0.135, 0.095),
        f"~{speed['N_converge_lun']:,}\nlunations",
        edge=C_CORAL_L,
        face="#FFF8F4",
        color=C_CORAL,
        fs=11.8,
        weight="bold",
    )

    cx, cy, cw, ch = column(0.635, 0.255, 0.100, 0.445, anchor_line=True)
    t = np.linspace(0, 1, 100)
    ax0.plot(cx + 0.045 + 0.013 * np.sin(28 * t) * np.exp(-3.5 * t),
             cy + ch * (1 - 0.16 * t), transform=ax0.transAxes,
             color=C_CORAL, lw=1.9, zorder=11)
    ax0.plot([cx + 0.054, cx + 0.074], [cy + 0.89 * ch, cy],
             transform=ax0.transAxes, color=C_TEAL, lw=2.5, zorder=11)
    arrow(ax0, (0.745, 0.655), (0.775, 0.655), color=C_CORAL, lw=1.6)
    ax0.text(0.790, 0.655, "Step A:\nshallow skin", transform=ax0.transAxes,
             fontsize=10.8, color=C_CORAL, va="center", zorder=10)
    arrow(ax0, (0.745, 0.475), (0.775, 0.415), color=C_TEAL, lw=1.6)
    ax0.text(0.790, 0.405, "Step B:\ndeep profile\nfrom closure", transform=ax0.transAxes,
             fontsize=10.8, color=C_TEAL, va="center", zorder=10)
    card(
        ax0,
        (0.775, 0.500),
        (0.120, 0.100),
        f"~{speed['speedup_per_solve']:.0f}x\nper solve",
        edge=C_TEAL_L,
        face="#F5FAFB",
        color=C_TEAL,
        fs=11.5,
        weight="bold",
    )
    save(fig, "fig_anchor_vs_bruteforce")


def main():
    image_hayne_layers()
    image_probe_geometry()
    image_thermal_process()
    image_retrieval_pipeline()
    image_anchor_vs_bruteforce()


if __name__ == "__main__":
    main()
