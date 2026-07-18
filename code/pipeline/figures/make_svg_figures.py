#!/usr/bin/env python3
"""Convert hand-authored SVG *illustrations* to PDF for the guidebook.

Conceptual diagrams (the physical setup, equation interpretations) are authored
as clean vector SVG in pipeline/figures/svg/*.svg and converted here to
../figures/<name>.pdf (top-level shared home) with svglib + reportlab (pure Python -- no system
cairo). Data figures stay in matplotlib; this is only for illustrations.

Math/Greek goes in the LaTeX caption, not the SVG (reportlab's base fonts lack
those glyphs); SVG text is kept to plain words for clean conversion.

Run:  python pipeline/figures/make_svg_figures.py
"""
from __future__ import annotations
import pathlib

from svglib.svglib import svg2rlg
from reportlab.graphics import renderPDF

_HERE = pathlib.Path(__file__).resolve().parent
SVG_DIR = _HERE / "svg"
OUT = _HERE.parents[1] / ".." / "figures"


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    svgs = sorted(SVG_DIR.glob("*.svg"))
    print(f"Converting {len(svgs)} SVG illustrations -> PDF:")
    for svg in svgs:
        drawing = svg2rlg(str(svg))
        out = OUT / (svg.stem + ".pdf")
        renderPDF.drawToFile(drawing, str(out))
        print("  ->", out.name)
    print("done.")


if __name__ == "__main__":
    main()
