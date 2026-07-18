"""Density-sweep figure for the AOGS briefing: every swept coupled 3-layer
density profile, drawn as a staircase and coloured by how well it fits the
Apollo deep sensors (dark = low RMSE = good). Best fit bold; Hayne dotted.

Reads  AOGS/results/aogs_density_study.json  (the 650-config sweep).
Writes AOGS/figures/poster/poster_density_sweep.pdf

Move-proof paths (search by marker/name), so the bundle can live anywhere.
Run:  <repo>/.venv/bin/python make_density_sweep_figure.py
"""
import json
import pathlib
import sys

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.cm import ScalarMappable
from matplotlib.colors import Normalize

# reach the lunar package (code/src/lunar) wherever this bundle sits
sys.path.insert(0, str(next(a for a in pathlib.Path(__file__).resolve().parents
                            if (a / "code" / "src" / "lunar").is_dir()) / "code" / "src"))

from lunar.plotting.style import (JGR_FULL, C_A15, C_A17, C_HAYNE, C_GRID,  # noqa: E402
                                  WARM_SEQ, fmt_axis, assert_no_overlap)
from lunar.properties import density_hayne  # noqa: E402

AOGS = next(a for a in pathlib.Path(__file__).resolve().parents if a.name == "aogs")
SITE = {"A15": C_A15, "A17": C_A17}


def main():
    runs = json.loads((AOGS / "results" / "aogs_density_study.json").read_text())["runs"]
    z = np.linspace(0.0, 1.0, 400)
    fig, axes = plt.subplots(1, 2, figsize=(JGR_FULL, 4.3), constrained_layout=True)

    for ax, sk in zip(axes, ("A15", "A17")):
        recs = [r for r in runs if r["site"] == sk and r["branch"] == "coupled"
                and r["rho"] != "hayne"]
        rmse = np.array([r["rmse_K"] for r in recs])
        cmap = WARM_SEQ.reversed()                     # best = dark, poor = faded
        norm = Normalize(rmse.min(), np.percentile(rmse, 85))
        for i in np.argsort(rmse)[::-1]:               # best drawn last (on top)
            r = recs[i]; r1, r2, r3 = r["rho"]; z1, z2 = r["z1_m"], r["z2_m"]
            prof = np.where(z < z1, r1, np.where(z < z2, r2, r3))
            ax.step(prof, z, where="post", color=cmap(norm(rmse[i])), lw=0.8, alpha=0.6)
        b = min(recs, key=lambda r: r["rmse_K"])
        r1, r2, r3 = b["rho"]; z1, z2 = b["z1_m"], b["z2_m"]
        ax.step(np.where(z < z1, r1, np.where(z < z2, r2, r3)), z, where="post",
                color=SITE[sk], lw=2.8, label=f"best fit ({b['rmse_K']:.2f} K)")
        ax.plot(density_hayne(z), z, ":", color=C_HAYNE, lw=2.2, label="Hayne continuous")
        ax.set_xlim(1050, 1980); ax.invert_yaxis()
        fmt_axis(ax, xlabel=r"density (kg m$^{-3}$)",
                 ylabel="depth (m)" if sk == "A15" else "",
                 title=f"Apollo {sk[1:]} — 162 swept coupled profiles")
        ax.legend(loc="lower left", fontsize=8, frameon=True, edgecolor=C_GRID)
        sm = ScalarMappable(norm=norm, cmap=cmap); sm.set_array([])
        fig.colorbar(sm, ax=ax, shrink=0.85, pad=0.02).set_label(
            "deep-sensor RMSE (K)", fontsize=9)
        fig.canvas.draw(); assert_no_overlap(ax)

    out = AOGS / "figures" / "poster" / "poster_density_sweep.pdf"
    fig.savefig(out)
    plt.close(fig)
    print("wrote", out)


if __name__ == "__main__":
    main()
