#!/usr/bin/env python3
"""Why the sensor cut sits at 80 cm — the physics, and the consequence.

(a) The diurnal wave decays as exp(-z/delta). Fitting the solved amplitude
    profile gives delta = 7.5 cm, so 80 cm is ~10.6 e-foldings: a 268 K
    peak-to-peak surface swing arrives as a few millikelvin. Langseth (1976)
    reaches the same depth from the flight data — "Below about 80 cm, the
    nearly 300 K peak-to-peak surface variation is attenuated to a level
    below the noise."

(b) What moving the cut actually does to the answer. 70, 80 and 90 cm agree
    to three decimals at Apollo 17; only 60 cm breaks, because it readmits
    the two sensors at 66 and 67 cm. That is the contamination appearing
    exactly where (a) predicts it.

No instrument noise floor is drawn: the HFE thermometer resolution is not in
this repository's references, and a line I cannot cite has no business on a
defence figure. The millikelvin value at the cut is annotated instead, and
the "below the noise" claim is attributed to Langseth.

Output: figures/fig_depth_cut.pdf
Run:    python code/pipeline/figures/make_depth_cut_figure.py
"""
from __future__ import annotations

import json
import pathlib
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

_REPO = pathlib.Path(__file__).resolve().parents[1].parent
sys.path.insert(0, str(_REPO / "src"))

from lunar.plotting.style import (JGR_FULL, C_A15, C_A17, C_CHAR, C_CORAL,
                                  C_DIM, C_GRID, fmt_axis)

FIGS = _REPO / ".." / "figures"
ENV = _REPO / "results" / "bc_envelope_cache.npz"
SENS = _REPO / "results" / "borestem_sensitivity.json"
ZCUT = 0.80


def main():
    d = np.load(ENV)
    z, amp = d["z"], (d["tmax"] - d["tmin"]) / 2.0

    # skin depth from the model's own decay (ln A is linear in z)
    m = (z > 0.03) & (z < 0.55)
    slope, _ = np.polyfit(z[m], np.log(amp[m]), 1)
    delta = -1.0 / slope
    i80 = int(np.argmin(np.abs(z - ZCUT)))

    fig, (ax, bx) = plt.subplots(
        1, 2, figsize=(JGR_FULL, 3.5), gridspec_kw=dict(width_ratios=[1.25, 1.0]))

    # ---- (a) the attenuation ------------------------------------------------
    # Below ~0.85 m the true amplitude is zero and the stored profile is just
    # solver round-off, which turns UP with depth. Plotting it makes the decay
    # look like it reverses, so the curve stops at the last monotonic point.
    turn = np.where((np.diff(amp) > 0) & (z[:-1] > 0.5))[0]
    zstop = z[turn[0]] if turn.size else 1.05
    keep = z <= zstop
    ax.semilogx(amp[keep] * 1e3, z[keep], lw=2.4, color=C_CHAR, zorder=5)

    for n in range(2, 12, 2):                      # e-folding gridlines
        zz = n * delta
        if zz <= 1.05:
            ax.axhline(zz, lw=0.6, color=C_GRID, zorder=1)
            ax.text(6e4, zz, f"{n}$\\delta$", fontsize=7, color=C_DIM,
                    ha="right", va="bottom", zorder=6)

    ax.axhline(ZCUT, lw=1.6, color=C_CORAL, zorder=4)
    ax.plot([amp[i80] * 1e3], [ZCUT], "o", ms=7, color=C_CORAL, mec="white",
            mew=1.2, zorder=7)
    ax.annotate(f"cut at 80 cm\n{ZCUT/delta:.1f}$\\delta$   "
                f"{amp[i80]*1e3:.1f} mK",
                xy=(amp[i80] * 1e3, ZCUT), xytext=(0.42, 0.11),
                textcoords="axes fraction", fontsize=8.5, color=C_CORAL,
                fontweight="bold", linespacing=1.4, ha="left", va="center",
                arrowprops=dict(arrowstyle="->", color=C_CORAL, lw=1.0),
                zorder=8)
    for zc, lab in ((0.60, "60 cm"), (0.70, "70 cm")):
        i = int(np.argmin(np.abs(z - zc)))
        ax.plot([amp[i] * 1e3], [zc], "o", ms=4.5, color=C_DIM, zorder=6)
        ax.text(amp[i] * 1e3 * 1.9, zc, f"{lab}   {amp[i]*1e3:.0f} mK",
                fontsize=7.5, color=C_DIM, va="center", zorder=6)

    ax.set_xlim(0.8, 3e5)
    ax.set_ylim(1.05, 0.0)
    fmt_axis(ax, xlabel="diurnal half-amplitude  (mK)", ylabel="depth  (m)",
             title=f"(a)  the wave dies as $e^{{-z/\\delta}}$,  "
                   f"$\\delta={delta*100:.1f}$ cm")
    ax.grid(True, which="major", axis="x", lw=0.5, color=C_GRID)

    # ---- (b) what moving the cut does --------------------------------------
    s = json.loads(SENS.read_text())
    cut = np.array(s["cut_cm"], dtype=float)
    bx.plot(cut, s["A15"], "o-", lw=2.0, ms=6, color=C_A15, label="Apollo 15",
            mec="white", mew=1.0, zorder=5)
    bx.plot(cut, s["A17"], "s-", lw=2.0, ms=6, color=C_A17, label="Apollo 17",
            mec="white", mew=1.0, zorder=5)
    bx.axvline(80, lw=1.6, color=C_CORAL, zorder=2)
    bx.text(80.6, 5.65, "adopted", fontsize=8, color=C_CORAL,
            fontweight="bold", ha="left", va="bottom", zorder=6)
    bx.annotate("60 cm readmits the\nsensors at 66 and 67 cm",
                xy=(60, s["A17"][0]), xytext=(66.5, 8.9),
                fontsize=8, color=C_DIM, linespacing=1.4, ha="left",
                arrowprops=dict(arrowstyle="->", color=C_DIM, lw=0.9),
                zorder=7)
    bx.set_xticks([60, 70, 80, 90])
    bx.set_ylim(4.0, 9.4)
    fmt_axis(bx, xlabel="depth cut  (cm)",
             ylabel="retrieved $K_d^{*}$  (mW m$^{-1}$K$^{-1}$)",
             title="(b)  70, 80 and 90 cm agree")
    bx.legend(frameon=True, edgecolor=C_GRID, fontsize=8.5, loc="center left")
    bx.grid(True, lw=0.5, color=C_GRID)

    fig.tight_layout()
    FIGS.mkdir(parents=True, exist_ok=True)
    out = FIGS / "fig_depth_cut.pdf"
    fig.savefig(out)
    plt.close(fig)
    print(f"  delta = {delta*100:.2f} cm;  80 cm = {ZCUT/delta:.2f} e-foldings;"
          f"  amp(80 cm) = {amp[i80]*1e3:.2f} mK")
    print(f"  -> {out.resolve()}")


if __name__ == "__main__":
    main()
