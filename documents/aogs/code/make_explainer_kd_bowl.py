"""K_d retrieval bowl under shadowed forcing — the degeneracy, visualized.

Reads the already-computed RMSE(K_d) sweep (aogs_kd_shadowed.json, grids
extended to the physical bounds) and draws the misfit bowl for each site,
marking (a) the letter's certified K_d*, (b) the shadowed-forcing vertex,
and (c) the coupled winner's EFFECTIVE deep conductivity K_c(rho3).
Shows in one picture why 'a K_d' is not unique once density can move.
At A15 markers (a) and (c) coincide (winner rho3 = Hayne rho_d) — that
coincidence is the teaching point; at A17 they separate.

Layout per lunar-figures: line ROLES go to one shared legend BELOW the
panels (legend_below — never on the data); numeric VALUES are small tags
in the top band of each axes, spread by ha so neighbours never touch;
assert_no_overlap guards both axes.

Zero new solves. Output -> deliverables/documents/aogs/talk_figures/
explainer_kd_bowl.{pdf,png}
Run:  .venv/bin/python code/pipeline/figures/make_explainer_kd_bowl.py
"""
from __future__ import annotations

import json
import pathlib
import sys

import matplotlib.pyplot as plt
import numpy as np

sys.path.insert(0, str(next(a for a in pathlib.Path(__file__).resolve().parents if (a / "code" / "src" / "lunar").is_dir()) / "code" / "src"))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[0] / "compute"))
from lunar._bootstrap import find_repo_root  # noqa: E402
from lunar.plotting.style import (JGR_HALF, C_A15, C_A17, C_DIM, C_CHAR,  # noqa: E402
                                  FS_TICK, fmt_axis, legend_below,
                                  assert_no_overlap)
import s2_density_study as ds  # noqa: E402

ROOT = find_repo_root()
AOGS = next(a for a in pathlib.Path(__file__).resolve().parents if a.name == "aogs")
OUT = AOGS / "figures" / "diagrams"; OUT.mkdir(parents=True, exist_ok=True)


def main():
    d = json.loads((AOGS / "results" / "aogs_kd_shadowed.json").read_text())
    kd = json.loads((ROOT / "results" / "kd_retrieval_results.json").read_text())
    study = json.loads((AOGS / "results" / "aogs_density_study.json").read_text())
    win_rho3 = {}
    for sk in ("A15", "A17"):
        recs = [r for r in study["runs"] if r["site"] == sk
                and r["branch"] == "coupled" and r["rho"] != "hayne"]
        win_rho3[sk] = min(recs, key=lambda r: r["rmse_K"])["rho"][2]

    fig, axes = plt.subplots(1, 2, figsize=(JGR_HALF * 1.35, 3.4),
                             constrained_layout=True)
    colors = {"A15": C_A15, "A17": C_A17}
    handles = labels = None
    for ax, sk in zip(axes, ("A15", "A17")):
        s = d["sites"][sk]
        g = np.asarray(s["kd_grid_mW"]); r = np.asarray(s["rmse_K"])
        o = np.argsort(g); g, r = g[o], r[o]
        h_bowl, = ax.plot(g, r, "-o", color=colors[sk], ms=4, lw=1.8)

        kdstar = kd[sk]["kd_star"] * 1e3
        vert = s["kd_star_shadowed_mW"]
        keff = float(ds.kc_of_rho(win_rho3[sk], kd[sk]["kd_star"])) * 1e3
        h_star = ax.axvline(kdstar, color=C_CHAR, lw=1.3, ls="--")
        h_vert = ax.axvline(vert, color=C_DIM, lw=1.3, ls=":")
        h_eff = ax.axvline(keff, color=colors[sk], lw=1.3, ls="-.")

        # numeric tags in the top band; ha spread AND a real horizontal
        # offset from their own vline (the guard counts vlines as data);
        # merged when two markers coincide (the A15 teaching point).
        ymin, ymax = r.min(), r.max()
        ytag = ymax - 0.02 * (ymax - ymin)
        dx = 0.02 * (g.max() - g.min())
        if abs(keff - kdstar) < 0.05:
            ax.text(kdstar - dx, ytag, f"{kdstar:.2f}", color=C_CHAR,
                    fontsize=FS_TICK, ha="right", va="top")
        else:
            lo, hi = sorted((kdstar, keff))
            ax.text(lo - dx, ytag, f"{lo:.2f}",
                    color=C_CHAR if kdstar < keff else colors[sk],
                    fontsize=FS_TICK, ha="right", va="top")
            ax.text(hi + dx, ytag, f"{hi:.2f}",
                    color=colors[sk] if keff > kdstar else C_CHAR,
                    fontsize=FS_TICK, ha="left", va="top")
        ax.text(vert + dx, ytag - 0.10 * (ymax - ymin), f"{vert:.2f}",
                color=C_DIM, fontsize=FS_TICK, ha="left", va="top")

        fmt_axis(ax, xlabel="deep conductivity $K_d$ (mW m$^{-1}$ K$^{-1}$)",
                 ylabel="deep-sensor RMSE (K)" if sk == "A15" else "",
                 title=f"Apollo {sk[1:]}")
        handles = [h_bowl, h_star, h_vert, h_eff]
        labels = ["RMSE($K_d$), shadowed forcing", "letter $K_d^{*}$",
                  "shadowed vertex",
                  "coupled winner's effective $K_c(\\rho_3)$"]

    legend_below(fig, handles, labels, ncols=2)
    fig.canvas.draw()
    for ax in axes:
        assert_no_overlap(ax)

    OUT.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT / "explainer_kd_bowl.pdf")
    import fitz
    fitz.open(OUT / "explainer_kd_bowl.pdf")[0].get_pixmap(dpi=300).save(
        str(OUT / "explainer_kd_bowl.png"))
    plt.close(fig)
    print("wrote explainer_kd_bowl.{pdf,png} (guard passed)")


if __name__ == "__main__":
    main()
