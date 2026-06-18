"""Generate the teaching figures for the Beginner's Guide LaTeX project.

This script is *import-only* of the existing ``lunar`` package APIs and the
committed results in ``output/kd_retrieval_results.json``. It does NOT touch
any committed code or data; it only writes new PNG+PDF assets into
``docs/teaching/figures/``.

It produces, in the shared publication style (``lunar.plotting.style``):

  1. fig_skin_depth          -- diurnal swing vs depth (the thermal skin).
  2. fig_mean_profile        -- cycle-mean T(z): the rising geothermal gradient.
  3. fig_conductivity        -- the K(T, z) Hayne form (structural + radiative).
  4. fig_kd_retrieval        -- RMSE vs K_d sweep with the minimum marked.
  5. fig_bootstrap           -- bootstrap K_d* distributions and the contrast.

Run (from the repository root):

    export MPLCONFIGDIR=/tmp/mpl
    python docs/teaching/make_teaching_figures.py
"""
from __future__ import annotations

import json
import pathlib
import sys

import numpy as np

_HERE = pathlib.Path(__file__).resolve().parent
_REPO = _HERE.parents[1]
sys.path.insert(0, str(_REPO))

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from lunar.plotting.style import (  # noqa: E402
    C_A15, C_A17, C_DIM, C_CHAR, C_TEAL, C_CORAL, C_FOREST,
    JGR_HALF, JGR_FULL, fmt_axis,
)
from lunar.config import SITES  # noqa: E402
from lunar.constants import (  # noqa: E402
    CHI_RADIATIVE, H_PARAMETER, K_SURFACE, LUNATION_SECONDS,
    SOLAR_CONSTANT, T_REFERENCE,
)
from lunar.grid import make_geometric_grid  # noqa: E402
from lunar.equilibrium import solve_periodic_equilibrium  # noqa: E402
from lunar.properties import conductivity_hayne  # noqa: E402

FIG = _HERE / "figures"
FIG.mkdir(parents=True, exist_ok=True)

# Per-site retrieved deep conductivity K_d* [W m^-1 K^-1] (committed result).
KD_STAR = {"A15": 4.58e-3, "A17": 8.12e-3}
SITE_COLOR = {"A15": C_A15, "A17": C_A17}


def _save(fig, stem):
    png, pdf = FIG / f"{stem}.png", FIG / f"{stem}.pdf"
    fig.savefig(png, dpi=200)
    fig.savefig(pdf)
    plt.close(fig)
    print(f"  saved {png.name} + {pdf.name}")


def make_k_hayne(kd):
    def k(T, z):
        return conductivity_hayne(T, z, Ks=K_SURFACE, Kd=kd,
                                  H=H_PARAMETER, chi=CHI_RADIATIVE)
    return k


def run_site(tag, z_max=5.0):
    """Certified periodic equilibrium for one site at its retrieved K_d*."""
    cfg = SITES[tag]
    grid = make_geometric_grid(z_max=z_max, dz0=0.002, growth=0.08)
    n_t = int(LUNATION_SECONDS / 3600.0) + 1
    t = np.linspace(0.0, LUNATION_SECONDS, n_t)
    insol = (SOLAR_CONSTANT * np.cos(np.deg2rad(cfg["lat"]))
             * np.maximum(0.0, np.cos(2 * np.pi * t / LUNATION_SECONDS)))
    res = solve_periodic_equilibrium(
        grid=grid, t=t, insolation=insol,
        albedo=cfg["albedo"], emissivity=cfg["emissivity"], Q_b=cfg["Q_BASAL"],
        K_func=make_k_hayne(KD_STAR[tag]), T_guess=cfg["T_MEAN_EFF"],
    )
    return grid.z_mid, res.out.T, res.T_mean, cfg, res


def amplitude_profile(T_cycle):
    return 0.5 * (T_cycle.max(axis=1) - T_cycle.min(axis=1))


def skin_depth(z, amp):
    target = amp[0] / np.e
    below = np.where(amp <= target)[0]
    return float(z[below[0]]) if below.size else float("nan")


# ---------------------------------------------------------------------------
# Compute the two equilibrium-based panels once.
# ---------------------------------------------------------------------------

def main():
    print("Solving certified equilibria (A15, A17)...")
    data = {tag: run_site(tag) for tag in ("A15", "A17")}

    # --- Figure 1: thermal skin depth (diurnal swing damping) --------------
    print("Figure 1: skin depth")
    fig, ax = plt.subplots(figsize=(JGR_HALF, 4.2))
    for tag in ("A15", "A17"):
        z, T_cyc, _, cfg, _ = data[tag]
        amp = amplitude_profile(T_cyc)
        sd = skin_depth(z, amp)
        ax.plot(np.maximum(amp, 1e-3), z, color=SITE_COLOR[tag], lw=2.2,
                label=f"{cfg['label']}  (skin $\\delta\\approx${sd:.2f} m)")
        ax.axhline(sd, color=SITE_COLOR[tag], ls=":", lw=1.0, alpha=0.7)
    ax.set_xscale("log")
    ax.set_ylim(2.5, 0.0)
    fmt_axis(ax, xlabel="diurnal swing amplitude [K]  (log scale)",
             ylabel="depth below surface [m]",
             title="The daily heat wave dies out with depth")
    ax.legend(loc="lower right")
    fig.tight_layout()
    _save(fig, "fig_skin_depth")

    # --- Figure 2: cycle-mean profile (geothermal gradient) ----------------
    print("Figure 2: mean profile")
    fig, ax = plt.subplots(figsize=(JGR_HALF, 4.2))
    for tag in ("A15", "A17"):
        z, _, T_mean, cfg, _ = data[tag]
        ax.plot(T_mean, z, color=SITE_COLOR[tag], lw=2.4, label=cfg["label"])
    ax.set_ylim(5.0, 0.0)
    fmt_axis(ax, xlabel="cycle-mean temperature  $\\langle T\\rangle$ [K]",
             ylabel="depth below surface [m]",
             title="Below the skin, the mean temperature keeps rising")
    ax.legend(loc="upper right")
    fig.tight_layout()
    _save(fig, "fig_mean_profile")

    # --- Figure 3: the conductivity law K(T, z) ----------------------------
    print("Figure 3: conductivity law")
    z = np.linspace(0.0, 0.5, 400)
    fig, ax = plt.subplots(figsize=(JGR_HALF, 4.2))
    for T_fixed, c in ((150.0, C_TEAL), (250.0, C_FOREST), (350.0, C_CORAL)):
        K = conductivity_hayne(np.full_like(z, T_fixed), z, Kd=KD_STAR["A15"])
        ax.plot(z * 100.0, K * 1e3, color=c, lw=2.2, label=f"$T = {T_fixed:.0f}$ K")
    ax.axhline(KD_STAR["A15"] * 1e3, color=C_DIM, ls="--", lw=1.0,
               label="structural $K_d^*$ (A15)")
    fmt_axis(ax, xlabel="depth [cm]",
             ylabel="thermal conductivity $K$ [mW m$^{-1}$ K$^{-1}$]",
             title="Conductivity rises with depth and temperature")
    ax.legend(loc="lower right")
    fig.tight_layout()
    _save(fig, "fig_conductivity")

    # --- Figure 4: the K_d retrieval (RMSE sweep) --------------------------
    print("Figure 4: K_d retrieval (RMSE sweep)")
    res = json.load(open(_REPO / "output" / "kd_retrieval_results.json"))
    fig, ax = plt.subplots(figsize=(JGR_HALF, 4.2))
    for tag in ("A15", "A17"):
        d = res[tag]
        kd = np.asarray(d["kd_grid"]) * 1e3
        rmse = np.asarray(d["rmse_curve"])
        ks = d["kd_star"] * 1e3
        ax.plot(kd, rmse, color=SITE_COLOR[tag], lw=2.2, label=SITES[tag]["label"])
        ax.plot(ks, d["rmse_star"], "o", color=SITE_COLOR[tag], ms=8,
                mec="white", mew=1.2, zorder=5)
        ax.annotate(f"$K_d^* = {ks:.2f}$", xy=(ks, d["rmse_star"]),
                    xytext=(0, -18), textcoords="offset points",
                    ha="center", color=SITE_COLOR[tag], fontsize=9)
    fmt_axis(ax, xlabel="candidate deep conductivity $K_d$ [mW m$^{-1}$ K$^{-1}$]",
             ylabel="model$-$data RMSE [K]",
             title="Retrieval: slide $K_d$ until the model fits the data")
    ax.legend(loc="upper center")
    fig.tight_layout()
    _save(fig, "fig_kd_retrieval")

    # --- Figure 5: bootstrap uncertainty + contrast ------------------------
    print("Figure 5: bootstrap distributions")
    fig, ax = plt.subplots(figsize=(JGR_FULL, 4.0))
    for tag in ("A15", "A17"):
        b = res[tag]["bootstrap"]
        samples = np.asarray(b["samples"]) * 1e3
        ax.hist(samples, bins=40, density=True, color=SITE_COLOR[tag],
                alpha=0.55, label=f"{SITES[tag]['label']}  "
                f"($K_d^* = {res[tag]['kd_star']*1e3:.2f}$)")
        ax.axvline(b["median"] * 1e3, color=SITE_COLOR[tag], lw=1.6, ls="--")
        ax.axvspan(b["ci_lo"] * 1e3, b["ci_hi"] * 1e3, color=SITE_COLOR[tag],
                   alpha=0.12)
    fmt_axis(ax, xlabel="retrieved $K_d^*$ [mW m$^{-1}$ K$^{-1}$]",
             ylabel="bootstrap probability density",
             title="The two sites separate: A17 conducts heat better than A15")
    ax.legend(loc="upper right")
    fig.tight_layout()
    _save(fig, "fig_bootstrap")

    print("\nAll teaching figures written to", FIG)


if __name__ == "__main__":
    main()
