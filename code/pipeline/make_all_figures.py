#!/usr/bin/env python3
"""Regenerate every figure of the paper (letter and SI).

One command to "draw out the figures." Each generator is run in turn,
timed, and reported; a failure in one does not stop the others. Assumes
the results JSONs exist in results/ (the repository ships them; `make aux`
or the notebook recomputes them). SI Figure S6 is drawn by
compute/compute_joint_diviner.py, which needs the Diviner data.

Run:  python pipeline/make_all_figures.py    (or: make figures)
"""
from __future__ import annotations
import importlib, sys, time, pathlib

_REPO = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_REPO))
sys.path.insert(0, str(_REPO / "src"))
sys.path.insert(0, str(_REPO / "pipeline" / "figures"))
sys.path.insert(0, str(_REPO / "pipeline" / "compute"))

# (module, callables) — each module's figure entry point(s), in run order.
JOBS = [
    ("make_joint_figures",           ["main"]),   # letter Figs 1-8, SI Figs S3, S4, S5
    ("make_context_map_figure",      ["main"]),   # SI Fig S1 (needs the LOLA map: REPRODUCING.md, Step 3)
    ("make_study_overview",          ["main"]),   # SI Fig S2 (TikZ, needs pdflatex)
    ("make_spinup_animation",        ["main"]),   # optional_anchor_method notebook: brute-force spin-up
    ("make_anchor_method_animation", ["main"]),   # optional_anchor_method notebook: the flux-anchored method
]


def main():
    print("Regenerating all figures...\n")
    t_all = time.perf_counter()
    ok, fail = [], []
    for modname, funcs in JOBS:
        t0 = time.perf_counter()
        try:
            mod = importlib.import_module(modname)
            for fn in funcs:
                getattr(mod, fn)()
            dt = time.perf_counter() - t0
            ok.append((modname, dt))
            print(f"  [ok]   {modname:32s} {dt:6.1f} s")
        except Exception as e:
            dt = time.perf_counter() - t0
            fail.append((modname, f"{type(e).__name__}: {e}"))
            print(f"  [FAIL] {modname:32s} {dt:6.1f} s  -- {type(e).__name__}: {e}")
    print(f"\nDone in {time.perf_counter()-t_all:.1f} s "
          f"({len(ok)} ok, {len(fail)} failed).")
    if fail:
        print("Failures:")
        for m, e in fail:
            print(f"  - {m}: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
