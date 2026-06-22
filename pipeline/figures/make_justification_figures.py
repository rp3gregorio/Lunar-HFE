#!/usr/bin/env python3
"""Two figures for the justification write-up (docs/guidebook/):

  fig_models.pdf      -- Hayne (2017) and Martinez (2021) K(T,z): replicate
                         both forms; show where the global K_d sits and how
                         our per-site values shift the deep asymptote.
  fig_convergence.pdf -- brute force converges onto the shortcut as the
                         lunation count increases ("the increasing-lunations
                         graph"): error at 1 m vs lunations, two guesses.

Saves into results/figures/. Run from the repo root.
"""
from __future__ import annotations
import sys, pathlib
import numpy as np

_REPO = pathlib.Path(__file__).resolve().parents[1].parent
sys.path.insert(0, str(_REPO))
sys.path.insert(0, str(_REPO / "src"))
sys.path.insert(0, str(_REPO / "pipeline" / "figures"))

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from lunar.properties import conductivity_hayne, conductivity_martinez, density_hayne
from lunar.constants import K_SURFACE, K_DEEP, H_PARAMETER
from lunar.plotting.style import C_A15, C_A17, C_HAYNE, C_CHAR, C_DIM, C_GRID, fmt_axis

OUT = _REPO / "results" / "figures"
OUT.mkdir(parents=True, exist_ok=True)


def fig_models():
    z = np.linspace(0, 2.0, 400)
    Ks, H = K_SURFACE, H_PARAMETER
    def kc(kd):                                    # contact conductivity K_c(z); asymptote = K_d
        return (kd - (kd - Ks) * np.exp(-z / H)) * 1e3

    fig, (axA, axB) = plt.subplots(1, 2, figsize=(10.0, 4.6))
    # (a) contact conductivity vs depth -> the deep asymptote IS K_d
    axA.plot(kc(3.4e-3), z, color=C_HAYNE, lw=2.4, label="Hayne: $K_d=3.4$")
    axA.plot(kc(4.58e-3), z, color=C_A15, lw=2.2, ls="--", label="A15: $K_d^*=4.58$")
    axA.plot(kc(8.12e-3), z, color=C_A17, lw=2.2, ls="--", label="A17: $K_d^*=8.12$")
    axA.set_xlim(0, 9); axA.set_ylim(2.0, -0.05)        # surface (z=0) at top
    fmt_axis(axA, xlabel="contact conductivity  $K_c(z)$  [mW m$^{-1}$ K$^{-1}$]",
             ylabel="depth  $z$  [m]")
    axA.set_title(r"(a)  the deep asymptote is $K_d$:  $K_c=K_d-(K_d-K_s)e^{-z/H}$",
                  loc="left", fontsize=9.5, color=C_CHAR)
    # legend tucked into the open gap between the A15 and A17 verticals
    axA.legend(fontsize=8.2, frameon=True, edgecolor=C_GRID, framealpha=0.97,
               loc="center", bbox_to_anchor=(0.72, 0.42), handlelength=1.5,
               borderpad=0.5, labelspacing=0.35)
    # surface annotation: left of every curve, clear space
    axA.annotate("surface\n$K_s=0.74$", xy=(0.80, 0.06), xytext=(1.7, 0.52),
                 fontsize=8, color=C_DIM, ha="left", va="center",
                 arrowprops=dict(arrowstyle="->", color=C_DIM, lw=0.8))
    # 'global -> per-site' shift: arrow in the open gap, text above it
    axA.text(6.35, 1.66, r"global $\rightarrow$ per-site", fontsize=8,
             color=C_DIM, ha="center", va="center")
    axA.annotate("", xy=(8.02, 1.85), xytext=(4.66, 1.85),
                 arrowprops=dict(arrowstyle="->", color=C_DIM, lw=0.8))

    # (b) K vs T at fixed depth (radiative term)
    T = np.linspace(100, 400, 300)
    axB.plot(T, conductivity_hayne(T, np.full_like(T, 1.0), Kd=3.4e-3) * 1e3,
             color=C_HAYNE, lw=2.2, label="Hayne  ($z=1$ m)")
    axB.plot(T, conductivity_martinez(T, z=np.full_like(T, 1.0)) * 1e3,
             color=C_DIM, lw=2.0, ls=":", label="Martínez  ($z=1$ m)")
    axB.set_xlim(100, 400)
    fmt_axis(axB, xlabel="temperature  $T$  [K]",
             ylabel="thermal conductivity  $K$  [mW m$^{-1}$ K$^{-1}$]")
    axB.set_title(r"(b)  radiative rise  $\propto\,\chi\,(T/350)^3$", loc="left",
                  fontsize=10, color=C_CHAR)
    axB.legend(fontsize=8.5, frameon=True, edgecolor=C_GRID, framealpha=0.97,
               loc="upper left")

    fig.tight_layout()
    fig.savefig(OUT / "fig_models.pdf", bbox_inches="tight")
    plt.close(fig)
    print("  -> fig_models.pdf")


def fig_convergence():
    import make_equilibrium_demo as demo
    res = demo.compute_curves(n_grid=(50, 100, 200, 400, 800, 1200),
                              guesses=(240.0, 260.0), parallel=True)
    fig, ax = plt.subplots(figsize=(8.2, 4.6))
    cmap = {240.0: C_A15, 260.0: C_A17}
    for gk, rec in res["curves"].items():
        ax.loglog(rec[:, 0], rec[:, 2], "-o", ms=4, color=cmap.get(gk, C_DIM),
                  label=f"brute force, start {gk:.0f} K")
    ax.axhline(0.03, ls="--", lw=1.5, color=C_HAYNE)
    ax.text(60, 0.034, "shortcut tolerance (0.03 K) — reached in ~9 s",
            fontsize=9, color=C_HAYNE)
    ax.set_xlabel("brute-force spin-up length  [lunations]")
    ax.set_ylabel(r"error vs. shortcut at 1 m,  $|\langle T\rangle - \langle T\rangle_{\rm short}|$  [K]")
    ax.set_title("Increasing the lunations drives brute force onto the shortcut",
                 loc="left", fontsize=11, color=C_CHAR)
    ax.legend(fontsize=9, frameon=False)
    ax.grid(alpha=0.25, which="both")
    fig.tight_layout()
    fig.savefig(OUT / "fig_convergence.pdf", bbox_inches="tight")
    plt.close(fig)
    print(f"  -> fig_convergence.pdf  (brute-force wall {res['wall_parallel']:.0f}s on "
          f"{res['n_workers']} cores)")


if __name__ == "__main__":
    print("Building justification figures:")
    fig_models()
    fig_convergence()
    print("done.")
