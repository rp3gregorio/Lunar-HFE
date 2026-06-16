#!/usr/bin/env python3
"""Render the figures needed by the progress deck to PNG (slides/assets/),
plus two new explanatory diagrams. Run from the repo root:

    python slides/build_assets.py
"""
from __future__ import annotations
import sys, subprocess, pathlib
import numpy as np

_REPO = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_REPO))
ASSETS = _REPO / "slides" / "assets"
ASSETS.mkdir(parents=True, exist_ok=True)

LETTER = _REPO / "paper" / "letter" / "figures"
OUTFIG = _REPO / "output" / "figures"
CGUIDE = _REPO / "docs" / "code_guide" / "figures"

# committed PDF -> asset name
PDFS = {
    "fig_context_map":              LETTER / "fig_context_map.pdf",
    "fig_apollo_timeline":          LETTER / "fig_apollo_timeline.pdf",
    "fig_amplitude_vs_depth":       LETTER / "fig_amplitude_vs_depth.pdf",
    "fig_intro_probe":              LETTER / "fig_intro_probe.pdf",
    "fig_dataflow":                 CGUIDE / "fig_dataflow.pdf",
    "fig_equilibrium_demo":         OUTFIG / "fig_equilibrium_demo.pdf",
    "fig_equilibrium_certification":OUTFIG / "fig_equilibrium_certification.pdf",
    "fig_kd_sweep":                 LETTER / "fig_kd_sweep.pdf",
    "fig_bootstrap":                LETTER / "fig_bootstrap.pdf",
    "fig_thermal_profiles":         LETTER / "fig_thermal_profiles.pdf",
    "fig_robustness":               LETTER / "fig_robustness.pdf",
    "fig_kd_qb_posterior":          OUTFIG / "fig_kd_qb_posterior.pdf",
    "fig_diviner_closure":          LETTER / "fig_diviner_closure.pdf",
    "fig_alpha_sweep":              LETTER / "fig_alpha_sweep.pdf",
    "fig_architecture":             CGUIDE / "fig_architecture.pdf",
}


def render_pdf(pdf: pathlib.Path, png: pathlib.Path, dpi: int = 200) -> str:
    if not pdf.exists():
        return f"MISSING {pdf}"
    try:                                   # preferred: PyMuPDF, crisp at any DPI
        import fitz
        doc = fitz.open(str(pdf))
        z = dpi / 72.0
        doc[0].get_pixmap(matrix=fitz.Matrix(z, z), alpha=False).save(str(png))
        doc.close()
        return "fitz"
    except Exception:
        pass
    # fallback: macOS sips (lower res but always present on darwin)
    r = subprocess.run(["sips", "-s", "format", "png", str(pdf), "--out", str(png)],
                       capture_output=True, text=True)
    return "sips" if r.returncode == 0 else f"FAIL {r.stderr[:80]}"


# --------------------------------------------------------------------------
# Two new diagrams (matplotlib, repo palette)
# --------------------------------------------------------------------------
def _diagrams():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
    from lunar.plotting.style import C_A15, C_A17, C_HAYNE, C_CHAR, C_DIM

    def box(ax, x, y, w, h, txt, fc, ec, fs=10):
        ax.add_patch(FancyBboxPatch((x, y), w, h,
                     boxstyle="round,pad=0.02,rounding_size=0.05",
                     facecolor=fc, edgecolor=ec, lw=1.3))
        ax.text(x + w/2, y + h/2, txt, ha="center", va="center", fontsize=fs, color=C_CHAR)

    # ---- seq_vs_parallel ----
    fig, ax = plt.subplots(figsize=(11, 5.2)); ax.set_xlim(0, 22); ax.set_ylim(0, 11); ax.axis("off")
    ax.text(0.3, 10.4, "One equilibrium solve  =  sequential", fontsize=13, fontweight="bold", color=C_A15)
    ax.text(0.3, 9.7, "each lunation needs the previous one  ->  cannot be split  ->  1 core", fontsize=10, color=C_DIM)
    xs = [0.6 + i*2.6 for i in range(4)]
    for i, x in enumerate(xs):
        lab = "lun 1" if i == 0 else ("lun N" if i == 3 else f"lun {i+1}")
        box(ax, x, 7.6, 1.9, 1.1, lab if i != 2 else "…", "#EAF1ED", C_A15, fs=9)
        if i < 3:
            ax.add_patch(FancyArrowPatch((x+1.9, 8.15), (x+2.6, 8.15),
                         arrowstyle="-|>", mutation_scale=14, color=C_DIM, lw=1.6))
    ax.text(11.4, 8.15, "one core, start -> finish", fontsize=9, color=C_DIM, va="center", style="italic")

    ax.text(0.3, 6.2, "The retrieval  =  many INDEPENDENT solves", fontsize=13, fontweight="bold", color=C_A17)
    ax.text(0.3, 5.5, "each trial $K_d$ / bootstrap resample is independent  ->  spread across all cores", fontsize=10, color=C_DIM)
    labels = ["$K_d$=3.0", "$K_d$=4.6", "$K_d$=6.0", "$K_d$=8.1", "…", "resample"]
    for i in range(6):
        x = 0.6 + i*3.5
        box(ax, x, 3.4, 3.1, 1.2, labels[i], "#FdEee7", C_A17, fs=9)
        ax.add_patch(FancyArrowPatch((x+1.55, 3.4), (x+1.55, 2.4),
                     arrowstyle="-|>", mutation_scale=12, color=C_DIM, lw=1.4))
        ax.text(x+1.55, 1.9, f"core {i+1}", ha="center", fontsize=8.5, color=C_DIM)
    ax.text(11, 0.7, "more cores -> the whole batch finishes sooner (not any single solve)",
            ha="center", fontsize=10.5, color=C_CHAR, style="italic")
    fig.tight_layout(); fig.savefig(ASSETS/"seq_vs_parallel.png", dpi=200, bbox_inches="tight"); plt.close(fig)

    # ---- speedup_stack ----
    fig, ax = plt.subplots(figsize=(11, 4.6)); ax.set_xlim(0, 24); ax.set_ylim(0, 10); ax.axis("off")
    ax.text(12, 9.2, "Three independent speed-ups — they multiply", ha="center", fontsize=13,
            fontweight="bold", color=C_CHAR)
    items = [("Algorithm", "flux-anchored shortcut", "~30×", "DONE", C_A15),
             ("Compilation", "C++  (or numba on _step)", "~10–100×", "available", C_HAYNE),
             ("Parallelism", "independent solves / cores", "× N cores", "available", C_A17)]
    for i, (title, sub, fac, status, c) in enumerate(items):
        x = 0.6 + i*7.7
        box(ax, x, 3.2, 6.6, 3.4, "", "#F6F4F1", c)
        ax.text(x+3.3, 5.7, title, ha="center", fontsize=12.5, fontweight="bold", color=c)
        ax.text(x+3.3, 5.0, sub, ha="center", fontsize=9.5, color=C_DIM)
        ax.text(x+3.3, 4.15, fac, ha="center", fontsize=16, fontweight="bold", color=C_CHAR)
        ax.text(x+3.3, 3.5, status, ha="center", fontsize=9, color=c, style="italic")
        if i < 2:
            ax.text(x+7.0, 4.9, "×", ha="center", fontsize=22, color=C_DIM)
    ax.text(12, 2.1, "single forward solve stays sequential — but you rarely need just one",
            ha="center", fontsize=10.5, color=C_CHAR, style="italic")
    fig.tight_layout(); fig.savefig(ASSETS/"speedup_stack.png", dpi=200, bbox_inches="tight"); plt.close(fig)
    print("  -> seq_vs_parallel.png, speedup_stack.png")


def main():
    print("Rendering figure PDFs -> PNG:")
    for name, pdf in PDFS.items():
        how = render_pdf(pdf, ASSETS / f"{name}.png")
        print(f"  {name:32s} [{how}]")
    print("Building new diagrams:")
    _diagrams()
    print(f"\nassets in {ASSETS}")


if __name__ == "__main__":
    main()
