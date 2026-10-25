"""SI Figure S3: the daily temperature swing against depth at both sites.

The measured swing of each sensor is sqrt(2) times the standard deviation of its
temperature within the stability window (exact for a sine wave). Above 80 cm the
borestems carry the daily swing down and the measured swings exceed the
regolith's; below, they fall to the noise level of the record. The two model
curves are the analytic attenuation exp(-z/delta) of a 100 K surface swing, with
the diurnal skin depth delta = sqrt(2 kappa / omega) at 250 K and 1800 kg m^-3.

Called by make_joint_figures.py; writes figures/fig_joint_amplitude_vs_depth.pdf.
"""
from __future__ import annotations

import pathlib
import sys

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.legend_handler import HandlerTuple
from matplotlib.lines import Line2D
from matplotlib.patches import Patch

_REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO / "src"))

from lunar.apollo_helpers import extract_sensor_stability
from lunar.config import SITES
from lunar.constants import CHI_RADIATIVE, K_DEEP, LUNATION_SECONDS, T_REFERENCE
from lunar.properties import conductivity_martinez
from lunar.plotting import style as _st
from lunar.plotting.style import (C_A15, C_A17, C_DIM, C_EXCL_FILL, C_HAYNE_GLOBAL,
                                  C_MS, C_NEUTRAL, LS_HAYNE_GLOBAL, LS_MS,
                                  assert_no_overlap, fmt_axis, legend_below)

OUT = _REPO.parent / "figures"
T_MID, RHO_DEEP, CP_MID = 250.0, 1800.0, 670.0   # K, kg m^-3, J kg^-1 K^-1 (Hayne c_p at 250 K)
NOISE_K = 0.05      # Langseth & Keihm (1977, Section V-C): daily variation insignificant below this


def skin_depth_cm(K):
    """Diurnal skin depth sqrt(2 kappa / omega) for conductivity K (W m^-1 K^-1)."""
    kappa = K / (RHO_DEEP * CP_MID)
    return np.sqrt(2 * kappa / (2 * np.pi / LUNATION_SECONDS)) * 100


def main(out_name="fig_joint_amplitude_vs_depth.pdf"):
    fig, axes = plt.subplots(1, 2, figsize=(_st.TEXT_W - 0.04, 4.4), sharey=True,
                             gridspec_kw={"wspace": 0.06})
    fig.subplots_adjust(left=0.10, right=0.975, top=0.92, bottom=0.12)
    XLIM = (2e-2, 150.0)
    YLIM = (245.0, 0.0)          # down past the deepest sensor (A17, 234 cm)
    z_grid = np.linspace(0.0, 250.0, 400)   # cm

    # Hayne et al. (2017) at the global K_d, with the radiative factor at 250 K
    delta_H = skin_depth_cm(K_DEEP * (1.0 + CHI_RADIATIVE * (T_MID / T_REFERENCE) ** 3))
    # Martinez & Siegler (2021) at 250 K and the deep density
    delta_M = skin_depth_cm(float(conductivity_martinez(np.array([T_MID]),
                                                        rho=np.array([RHO_DEEP]))[0]))
    amp_H = 100 * np.exp(-z_grid / delta_H)
    amp_M = 100 * np.exp(-z_grid / delta_M)

    for k, (ax, name) in enumerate(zip(axes, ["A15", "A17"])):
        cfg = SITES[name]
        obs = extract_sensor_stability(cfg["mission"], cfg["MIN_DEPTH_CM"])
        z_obs = np.array(obs["depth_cm_all"])
        amp_obs = np.sqrt(2.0) * np.array(obs["T_std_all"])

        ax.semilogx(amp_H, z_grid, ls=LS_HAYNE_GLOBAL, color=C_HAYNE_GLOBAL, lw=2.0,
                    label="Hayne, global $K_d$")
        ax.semilogx(amp_M, z_grid, ls=LS_MS, color=C_MS, lw=2.0,
                    label="Martínez & Siegler")

        # borestem-zone sensors (open), with a dotted leader from the modeled
        # swing at their depth: its length is the excess the borestem carries
        stem = z_obs < cfg["MIN_DEPTH_CM"]
        for z_i, a_i in zip(z_obs[stem], amp_obs[stem]):
            a_model = 100.0 * np.exp(-z_i / delta_H)
            ax.plot([max(a_model, XLIM[0]), a_i], [z_i, z_i], ls=":",
                    color=C_DIM, lw=1.1, zorder=1.5)
        col = C_A15 if name == "A15" else C_A17
        ax.semilogx(amp_obs[stem], z_obs[stem], "o", mfc="white",
                    mec=col, mew=1.2, markersize=7, ls="none")
        ax.semilogx(amp_obs[~stem], z_obs[~stem], "o", color=col,
                    mec="white", mew=0.7, markersize=7, ls="none")

        ax.axvline(NOISE_K, color=C_NEUTRAL, ls=(0, (4, 2)), lw=1.0, zorder=0.6)
        ax.axhspan(0, cfg["MIN_DEPTH_CM"], color=C_EXCL_FILL, zorder=0)

        if name == "A17":   # name the excess once, on the deepest borestem sensor
            i_deep = int(np.argmax(z_obs[stem]))
            z_x, a_x = z_obs[stem][i_deep], amp_obs[stem][i_deep]
            a_m = max(100.0 * np.exp(-z_x / delta_H), XLIM[0])
            ax.annotate("heat-short excess",
                        xy=(np.sqrt(a_m * a_x), z_x), xytext=(0.32, 112),
                        color=C_DIM, style="italic", ha="left", va="center",
                        arrowprops=dict(arrowstyle="-", color=C_DIM, lw=0.8))

        fmt_axis(ax, xlabel="Diurnal amplitude (K)",
                 ylabel="Depth (cm)" if name == "A15" else "",
                 title=f"({'ab'[k]})  {cfg['label']}")
        ax.set_ylim(*YLIM)
        ax.set_xlim(*XLIM)

    h = [Line2D([], [], ls=LS_HAYNE_GLOBAL, color=C_HAYNE_GLOBAL, lw=2.0),
         Line2D([], [], ls=LS_MS, color=C_MS, lw=2.0),
         tuple(Line2D([], [], marker="o", ls="none", color=c, mec="white", ms=7) for c in (C_A15, C_A17)),
         tuple(Line2D([], [], marker="o", ls="none", mfc="white", mec=c, ms=7) for c in (C_A15, C_A17)),
         Line2D([], [], color=C_NEUTRAL, ls=(0, (4, 2)), lw=1.0), Patch(fc=C_EXCL_FILL)]
    l = ["Hayne, global $K_d$", "Martínez & Siegler", "meter-scale sensor",
         "borestem-zone sensor", "0.05 K: insignificant daily swing", "borestem zone"]
    legend_below(fig, h, l, pad_in=0.30, handlelength=2.6,
                 handler_map={tuple: HandlerTuple(ndivide=None, pad=0.3)})

    fig.canvas.draw()
    assert_no_overlap(axes[0])
    assert_no_overlap(axes[1])
    out = OUT / out_name
    fig.savefig(out)
    plt.close(fig)
    print(f"  -> {out}")


if __name__ == "__main__":
    main()
