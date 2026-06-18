"""Phase 2 — what happens to lunar regolith temperature at great depth?

This standalone diagnostic answers a physics question in concrete numbers:

    "If we extend the depth far below the sensors, should the temperature
     converge to a single constant value?"

Short answer (demonstrated below):
  * The diurnal day/night SWING damps to zero within ~1 m (the thermal
    skin depth) -- so all the different times-of-day curves DO merge onto
    a single line.
  * That single line is NOT flat. The cycle-mean temperature keeps rising
    with depth along the geothermal gradient  d<T>/dz = Q_b / K  set by the
    Moon's interior heat flux Q_b. It only flattens if Q_b = 0.
  * Extending the column deeper simply extends that straight, sloped line.

It uses the CERTIFIED flux-anchored equilibrium solver (lunar.equilibrium),
so the deep profile is independent of the starting guess.

Run:  python scripts/analysis/phase2_depth_convergence.py
Out:  output/figures/fig_phase2_depth_convergence.pdf  (+ .png for preview)
"""
from __future__ import annotations

import pathlib
import sys

import numpy as np

_REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO))

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from lunar.config import SITES  # noqa: E402
from lunar.constants import (  # noqa: E402
    CHI_RADIATIVE,
    H_PARAMETER,
    K_SURFACE,
    LUNATION_SECONDS,
    SOLAR_CONSTANT,
    T_REFERENCE,
)
from lunar.grid import make_geometric_grid  # noqa: E402
from lunar.equilibrium import solve_periodic_equilibrium  # noqa: E402
from lunar.properties import conductivity_hayne  # noqa: E402

# Per-site retrieved deep conductivity K_d* [W m^-1 K^-1] (committed result).
KD_STAR = {"A15": 4.58e-3, "A17": 8.12e-3}


def make_k_hayne(kd):
    """Hayne (2017) conductivity at a fixed retrieved K_d*."""
    def k(T, z):
        return conductivity_hayne(T, z, Ks=K_SURFACE, Kd=kd,
                                  H=H_PARAMETER, chi=CHI_RADIATIVE)
    return k


def run_site(tag, z_max):
    """Solve the certified periodic equilibrium for one site to depth z_max.

    Returns the depth grid [m], the full T(z, t) cycle [K], the cycle-mean
    profile [K], and the conductivity function used.
    """
    cfg = SITES[tag]
    grid = make_geometric_grid(z_max=z_max, dz0=0.002, growth=0.08)
    n_t = int(LUNATION_SECONDS / 3600.0) + 1            # one sample per hour
    t = np.linspace(0.0, LUNATION_SECONDS, n_t)
    # Idealized cosine insolation over one synodic lunation (matches pipeline).
    insol = (SOLAR_CONSTANT * np.cos(np.deg2rad(cfg["lat"]))
             * np.maximum(0.0, np.cos(2 * np.pi * t / LUNATION_SECONDS)))
    k_func = make_k_hayne(KD_STAR[tag])
    res = solve_periodic_equilibrium(
        grid=grid, t=t, insolation=insol,
        albedo=cfg["albedo"], emissivity=cfg["emissivity"], Q_b=cfg["Q_BASAL"],
        K_func=k_func, T_guess=cfg["T_MEAN_EFF"],
    )
    return grid.z_mid, res.out.T, res.T_mean, k_func, cfg, res


def amplitude_profile(T_cycle):
    """Half the peak-to-peak diurnal swing at each depth [K]."""
    return 0.5 * (T_cycle.max(axis=1) - T_cycle.min(axis=1))


def skin_depth_estimate(z, amp):
    """Depth at which the swing has fallen to 1/e of the surface swing [m]."""
    target = amp[0] / np.e
    below = np.where(amp <= target)[0]
    return float(z[below[0]]) if below.size else float("nan")


def analytic_deep_line(z, T0, Q_b, k_func, i_start):
    """Integrate d<T>/dz = Q_b / K(<T>, z) downward from index i_start.

    This is the steady geothermal profile -- the straight line the mean
    temperature must follow once the diurnal wave has died out.
    """
    T = T0 * np.ones_like(z)
    for i in range(i_start, z.size - 1):
        dz = z[i + 1] - z[i]
        K = float(np.asarray(k_func(np.array([T[i]]), np.array([z[i]])))[0])
        T[i + 1] = T[i] + Q_b / K * dz
    return T


def main():
    out_dir = _REPO / "output" / "figures"
    out_dir.mkdir(parents=True, exist_ok=True)

    fig, axes = plt.subplots(2, 3, figsize=(15, 8.5))

    print("\nPhase 2 — deep-temperature behaviour (certified equilibrium solver)")
    print("=" * 70)

    for row, tag in enumerate(("A15", "A17")):
        # Production depth (5 m) for the day/night-merging and skin-depth panels.
        z, T_cyc, T_mean, k_func, cfg, res = run_site(tag, z_max=5.0)
        amp = amplitude_profile(T_cyc)
        sd = skin_depth_estimate(z, amp)

        # Extended depth (20 m) to show the deep line just keeps going.
        z2, _, T_mean2, k2, _, _ = run_site(tag, z_max=20.0)
        i_anchor = int(np.argmin(np.abs(z2 - 1.0)))     # 1 m: below the skin
        T_line = analytic_deep_line(z2, T_mean2[i_anchor], cfg["Q_BASAL"],
                                    k2, i_anchor)

        # Measured deep gradient vs the predicted Q_b / K_d.
        mask = z2 >= 5.0
        grad_meas = np.polyfit(z2[mask], T_mean2[mask], 1)[0]   # K per m
        K_deep = float(np.asarray(
            k2(np.array([T_mean2[mask][0]]), np.array([z2[mask][0]])))[0])
        grad_pred = cfg["Q_BASAL"] / K_deep

        print(f"\n{cfg['label']} (Q_b = {cfg['Q_BASAL']*1e3:.0f} mW m^-2, "
              f"K_d* = {KD_STAR[tag]*1e3:.2f} mW m^-1 K^-1)")
        print(f"  surface diurnal swing      : {amp[0]:7.1f} K")
        print(f"  swing at 1 m / 2 m         : {np.interp(1.0, z, amp):7.3f} K"
              f" / {np.interp(2.0, z, amp):.3f} K")
        print(f"  thermal skin depth (1/e)   : {sd:7.3f} m")
        print(f"  deep gradient measured     : {grad_meas:7.3f} K/m")
        print(f"  deep gradient predicted    : {grad_pred:7.3f} K/m  (= Q_b/K_d)")
        print(f"  mean T at 1 m / 5 m / 20 m : "
              f"{np.interp(1.0, z2, T_mean2):.2f} / "
              f"{np.interp(5.0, z2, T_mean2):.2f} / "
              f"{T_mean2[-1]:.2f} K   (rises, not constant)")
        print(f"  equilibrium converged      : {res.converged} "
              f"(anchor drift {res.anchor_drift_K*1e3:.1f} mK)")

        # --- Panel 1: every-few-hours T(z) merging onto one line ------------
        ax = axes[row, 0]
        n_t = T_cyc.shape[1]
        for j in range(0, n_t, max(1, n_t // 10)):
            ax.plot(T_cyc[:, j], z, color="0.7", lw=0.8)
        ax.plot(T_mean, z, "C3", lw=2.2, label="cycle mean")
        ax.axhline(sd, color="C0", ls="--", lw=1, label=f"skin depth ≈ {sd:.2f} m")
        ax.set_ylim(z.max(), 0)
        ax.set_xlabel("temperature [K]")
        ax.set_ylabel("depth [m]")
        ax.set_title(f"{cfg['label']}: day/night curves merge with depth")
        ax.legend(fontsize=8, loc="lower right")

        # --- Panel 2: diurnal swing damps exponentially (skin depth) --------
        ax = axes[row, 1]
        ax.semilogx(np.maximum(amp, 1e-4), z, "C0")
        ax.axvline(amp[0] / np.e, color="0.5", ls=":")
        ax.axhline(sd, color="C0", ls="--", lw=1)
        ax.set_ylim(z.max(), 0)
        ax.set_xlabel("diurnal swing amplitude [K] (log)")
        ax.set_ylabel("depth [m]")
        ax.set_title("the SWING converges to zero")

        # --- Panel 3: extended mean profile -- a sloped line, not flat ------
        ax = axes[row, 2]
        ax.plot(T_mean2, z2, "C3", lw=2.2, label="simulated mean")
        ax.plot(T_line, z2, "k--", lw=1.2,
                label="geothermal line  Q_b/K")
        ax.set_ylim(z2.max(), 0)
        ax.set_xlabel("cycle-mean temperature [K]")
        ax.set_ylabel("depth [m]")
        ax.set_title(f"deep MEAN keeps rising ({grad_meas:.2f} K/m)")
        ax.legend(fontsize=8, loc="lower left")

    fig.suptitle("Phase 2 — deep lunar regolith temperature: "
                 "the daily swing dies out, the mean follows the "
                 "geothermal gradient (does NOT become constant)",
                 fontsize=12)
    fig.tight_layout(rect=(0, 0, 1, 0.97))
    pdf = out_dir / "fig_phase2_depth_convergence.pdf"
    png = out_dir / "fig_phase2_depth_convergence.png"
    fig.savefig(pdf)
    fig.savefig(png, dpi=130)
    print(f"\nSaved: {pdf}")
    print(f"Saved: {png}")


if __name__ == "__main__":
    main()
