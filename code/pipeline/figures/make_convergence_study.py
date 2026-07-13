"""Strict n_inner convergence of the production (truncated Step A) solver.

The retrieval is only trustworthy if the answer stops moving as we lengthen the
inner spin-up n_inner. Two stacked panels, both real solves at Apollo 17
(results/convergence_scan.json):

 (a) the retrieved K_d*(A17) vs n_inner: it falls from ~7.5 (under-resolved,
     n_inner=12) and reaches a PLATEAU at 7.16 mW/m/K. Convergence is judged on
     K_d* STABILITY -- |dK_d*| < 0.005 mW between successive n_inner -- shown by
     the shaded band; the production setting n_inner=96 sits inside it.
 (b) the flux-closure residual |<K dT/dz> - Q_b| / Q_b vs n_inner: an INDEPENDENT
     diagnostic. It falls below 0.5% of Q_b well before n_inner=96 and then floors
     at the grid limit (~0.12%). It corroborates (a) but is not the primary
     criterion, because the floor means closure alone cannot certify convergence.

Data: results/convergence_scan.json (real solves; scratchpad/convergence_scan.py).
Run: python pipeline/figures/make_convergence_study.py
"""
import json
import pathlib
import sys
import numpy as np
import matplotlib.pyplot as plt
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "src"))
from lunar.plotting.style import (  # noqa: E402
    JGR_HALF, C_A17, C_DIM, C_GRID, fmt_axis, FS_TICK, FS_LEGEND,
    assert_no_overlap,
)

ROOT = pathlib.Path(__file__).resolve().parents[2]
OUT = ROOT / ".." / "figures"
N_PROD = 96      # production EQ_N_INNER
KD_TOL = 0.005   # convergence criterion on K_d* [mW/m/K]
CLO_THR = 0.5    # flux-closure reporting threshold [% of Q_b]


def main():
    data = json.loads((ROOT / "results" / "convergence_scan.json").read_text())
    n = np.array(data["n_inner"], dtype=float)
    a17 = data["series"]["A17_new"]           # production truncated-Step-A method
    kd = np.array(a17["kd_star"])
    clo = np.array(a17["closure_pct"])
    kd_conv = kd[-1]                          # converged plateau (largest n_inner)
    clo_floor = clo[-1]

    fig, (axA, axB) = plt.subplots(
        2, 1, figsize=(JGR_HALF, 5.3), sharex=True, constrained_layout=True)

    # ---- panel (a): the retrieved result reaches a plateau -------------------
    axA.axhspan(kd_conv - 0.02, kd_conv + 0.02, color=C_DIM, alpha=0.15, lw=0,
                zorder=0)
    axA.axhline(kd_conv, color=C_DIM, ls="--", lw=1.0, alpha=0.85, zorder=1)
    axA.axvline(N_PROD, color=C_DIM, ls=":", lw=1.0, zorder=1)
    axA.plot(n, kd, "o-", color=C_A17, mfc=C_A17, mec="white", mew=1.2, ms=6,
             lw=2.0, zorder=4)
    axA.set_xscale("log")
    axA.set_xlim(10, 130)
    axA.set_ylim(7.12, 7.64)
    fmt_axis(axA, ylabel=r"retrieved $K_d^{*}$(A17)  (mW m$^{-1}$ K$^{-1}$)",
             title=r"(a)  the retrieved result reaches a plateau")
    axA.text(0.965, 0.60,
             "criterion:\n" r"$|\Delta K_d^{*}| < 0.005$ mW" "\nbetween successive $n$",
             transform=axA.transAxes, ha="right", va="center", fontsize=FS_LEGEND,
             color=C_DIM, linespacing=1.35)
    axA.text(0.855, 0.94, r"production $n_\mathrm{inner}{=}96$",
             transform=axA.transAxes, ha="right", va="top", fontsize=FS_LEGEND,
             color=C_DIM)

    # ---- panel (b): the flux-closure residual corroborates -------------------
    axB.axhline(CLO_THR, color=C_DIM, ls=":", lw=1.2, zorder=1)
    axB.plot(n, clo, "s-", color=C_A17, mfc=C_A17, mec="white", mew=1.2, ms=6,
             lw=2.0, zorder=4)
    axB.set_xscale("log")
    axB.set_xlim(10, 130)
    axB.set_ylim(0, 3.3)
    fmt_axis(axB, xlabel=r"inner spin-up length  $n_\mathrm{inner}$  (lunations)",
             ylabel=r"flux closure  (% of $Q_b$)",
             title=r"(b)  the flux-closure residual falls below 0.5%")
    axB.text(0.965, 0.23, r"0.5% of $Q_b$", transform=axB.transAxes, ha="right",
             va="center", fontsize=FS_LEGEND, color=C_DIM)
    axB.text(0.965, 0.47, r"floors at $\approx$%.2f%% (grid limit)" % clo_floor,
             transform=axB.transAxes, ha="right", va="center", fontsize=FS_LEGEND,
             color=C_DIM)

    fig.canvas.draw()
    assert_no_overlap(axA)
    assert_no_overlap(axB)
    OUT.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT / "fig_convergence_study.pdf")
    plt.close(fig)
    print(f"  -> {OUT / 'fig_convergence_study.pdf'}  (Kd* plateau {kd_conv:.4f}, "
          f"closure floor {clo_floor:.3f}%)")


if __name__ == "__main__":
    main()
