#!/usr/bin/env python3
"""Study overview chart (SI figure): the joint (albedo, K_d) fit in one diagram.

A TikZ schematic, not a data plot: pipeline/figures/tikz/study_overview.tex is
compiled with pdflatex. Its numbers are typed into the source by hand (see the
header there for the results files they come from), so update it whenever
those results change.

Needs pdflatex (TeX Live / MacTeX). Without it the committed PDF is kept and
a message says so.

Writes figures/fig_study_overview.pdf.
"""
from __future__ import annotations
import pathlib
import shutil
import subprocess
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[2]      # code/
TIKZ = ROOT / "pipeline" / "figures" / "tikz"
OUT = ROOT.parent / "figures" / "fig_study_overview.pdf"


def main():
    pdflatex = shutil.which("pdflatex")
    if pdflatex is None:
        print(f"  pdflatex not found -- kept the committed {OUT.name}")
        return
    with tempfile.TemporaryDirectory() as tmp:
        run = subprocess.run([pdflatex, "-interaction=nonstopmode", "-halt-on-error",
                              f"-output-directory={tmp}", "study_overview_standalone.tex"],
                             cwd=TIKZ, capture_output=True, text=True)
        if run.returncode != 0:
            tail = "\n".join(run.stdout.splitlines()[-15:])
            raise RuntimeError(f"pdflatex failed on study_overview_standalone.tex:\n{tail}")
        shutil.copyfile(pathlib.Path(tmp) / "study_overview_standalone.pdf", OUT)
    print(f"  -> {OUT}")


if __name__ == "__main__":
    main()
