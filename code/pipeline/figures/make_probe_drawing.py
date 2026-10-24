#!/usr/bin/env python3
"""SI Figure S2: the heat-flow probe, reproduced from Langseth and Keihm (1977).

Appendix C, Figure 1 of the Lunar Heat-Flow Experiment Final Technical Report
(NASA CR-151619; NTRS 19780010035, copyright determination "public use
permitted"): one probe in its borestem, with a gradient sensor and its heater
at each end of both probe halves and the two remote (ring) sensors between
them, and the thermocouples on the cable above.

The scan is reproduced unaltered, cropped to the drawing (the report's own
figure label left out). The crop is kept in code/data/apollo/langseth1977/;
the report PDF, in code/references/, is not tracked, so the crop is cut from
it only when the stored crop is missing.

Run with::

  python3 pipeline/figures/make_probe_drawing.py
"""
from __future__ import annotations
import pathlib
import sys

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from PIL import Image

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
from lunar.plotting import style  # noqa: E402,F401  (house rcParams)

OUT = ROOT / ".." / "figures"
CROP = ROOT / "data" / "apollo" / "langseth1977" / "probe_appendixC_fig1.png"
REPORT = ROOT / "references" / "apollo_hfe_final_technical_report.pdf"
PAGE, CLIP, DPI = 252, (80, 14, 612, 650), 300     # Appendix C, Figure 1 (report p. 247); points
WIDTH = 5.6                                          # in: labels of the scan at about 7 pt


def crop():
    """The stored crop, cut from the report first if it is missing."""
    if not CROP.exists():
        import fitz
        page = fitz.open(REPORT)[PAGE - 1]
        CROP.parent.mkdir(parents=True, exist_ok=True)
        page.get_pixmap(dpi=DPI, clip=fitz.Rect(*CLIP), colorspace=fitz.csGRAY).save(CROP)
    return np.asarray(Image.open(CROP).convert("L"))


def main(out_name="fig_probe_drawing.pdf"):
    img = crop()
    h, w = img.shape
    fig = plt.figure(figsize=(WIDTH, WIDTH * h / w))
    ax = fig.add_axes([0, 0, 1, 1])
    ax.imshow(img, cmap="gray", vmin=0, vmax=255, interpolation="none")
    ax.set_axis_off()
    OUT.mkdir(parents=True, exist_ok=True)
    dst = OUT / out_name
    fig.savefig(dst, dpi=w / WIDTH)                  # the scan at its own resolution
    plt.close(fig)
    print(f"wrote {dst.resolve()}  ({WIDTH:.2f} x {WIDTH * h / w:.2f} in)")


if __name__ == "__main__":
    main()
