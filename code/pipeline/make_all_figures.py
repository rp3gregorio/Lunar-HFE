#!/usr/bin/env python3
"""Draw every figure of the paper (letter and SI) into figures/.

Each generator runs in its own Python process, so the matplotlib settings of
one cannot leak into the next, and is timed; a failure in one does not stop
the others. The generators read code/results/, which the repository ships.

Run:  python code/pipeline/make_all_figures.py    (or: make figures)
"""
from __future__ import annotations
import pathlib
import subprocess
import sys
import time

FIGURES = pathlib.Path(__file__).resolve().parent / "figures"

JOBS = [
    "make_joint_figures.py",       # Figures 1-4, SI Figures S3-S7
    "make_context_map_figure.py",  # SI Figure S1 (needs the LOLA map, code/data/README.md)
    "make_probe_drawing.py",       # SI Figure S2 (Langseth & Keihm 1977, Appendix C, Figure 1)
]


def main():
    print("Drawing the figures...\n")
    t_all = time.perf_counter()
    failed = []
    for script in JOBS:
        t0 = time.perf_counter()
        r = subprocess.run([sys.executable, str(FIGURES / script)])
        dt = time.perf_counter() - t0
        print(f"  [{'ok' if r.returncode == 0 else 'FAIL'}] {script:28s} {dt:6.1f} s\n")
        if r.returncode:
            failed.append(script)
    print(f"Done in {time.perf_counter() - t_all:.1f} s ({len(JOBS) - len(failed)} ok, {len(failed)} failed).")
    if failed:
        print("Failed: " + ", ".join(failed))
        sys.exit(1)


if __name__ == "__main__":
    main()
