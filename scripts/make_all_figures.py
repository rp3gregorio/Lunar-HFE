#!/usr/bin/env python3
"""Regenerate every figure in the paper, appendix, and guidebook.

One command to "draw out the figures." Each generator is run in turn,
timed, and reported; a failure in one does not stop the others. Assumes
the result JSONs already exist in output/ (run the retrieval first:
`python scripts/pipeline/retrieve_kd.py`, or `make retrieve`).

Run:  python scripts/make_all_figures.py    (or: make figures)
"""
from __future__ import annotations
import importlib, sys, time, pathlib

_REPO = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_REPO))
sys.path.insert(0, str(_REPO / "scripts" / "figures"))
sys.path.insert(0, str(_REPO / "scripts" / "pipeline"))

# (module, callables) — each module's figure entry point(s), in run order.
JOBS = [
    ("make_intro_figures",      ["fig_intro_models", "fig_intro_probe"]),
    ("make_context_map_figure", ["main"]),
    ("make_apollo_timeline",    ["main"]),
    ("make_letter_figures",     ["main"]),
    ("make_results_figures",    ["main"]),
    ("make_alpha_sweep_figure", ["main"]),
    ("compute_diviner_closure", ["main"]),    # surface-T closure figure
    ("make_book_figures",       ["main"]),
    ("make_primer_figures",     ["main"]),
    ("make_equilibrium_certification", ["main"]),
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
