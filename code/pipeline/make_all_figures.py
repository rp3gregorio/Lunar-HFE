#!/usr/bin/env python3
"""Regenerate every figure in the paper and guidebook (plus supplementary).

One command to "draw out the figures." Each generator is run in turn,
timed, and reported; a failure in one does not stop the others. Assumes
the result JSONs already exist in results/ (run the retrieval first:
`python pipeline/compute/retrieve_kd.py`, or `make retrieve`).

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
    ("make_intro_figures",      ["fig_intro_probe"]),
    ("make_anchor_method_figure", ["main"]),  # letter Fig: the anchor method
    ("make_context_map_figure", ["main"]),
    ("make_probe_geometry_figure", ["main"]),  # fig_probe_geometry (guidebook
                                                # Ch.1); was missing from JOBS
                                                # -- a fresh `make figures` run
                                                # could not reproduce it
                                                # (audit 2026-07-05)
    ("make_apollo_timeline",    ["main"]),    # slim redesign (guidebook)
    ("make_apollo_timeline_letter", ["main"]), # original rich design (letter Fig 3)
    ("make_letter_figures",     ["main"]),
    ("make_results_figures",    ["main"]),
    ("make_alpha_sweep_figure", ["main"]),
    ("make_qb_degeneracy_figure", ["main"]),  # measured K_d*(Q_b) map (F-9)
    ("make_dt_ladder_figure",   ["main"]),    # dt certification teaching fig
    ("make_prior_estimates_figure", ["main"]),  # 5-decade K_d context (verified)
    ("make_sweep_worked_figure", ["main"]),    # App-C worked sweep bowl (book)
    ("compute_diviner_closure", ["main"]),    # surface-T closure figure
    ("make_book_figures",       ["main"]),
    ("make_book3d_figures",     ["main"]),    # 3D illustrations + 2D field/wave
    ("make_equilibrium_certification", ["main"]),
    ("make_anchor_convergence",  ["main"]),   # flux-anchored convergence trace (real history)
    ("make_convergence_study",   ["main"]),   # n_inner convergence: K_d* plateau + flux-closure criterion
    ("make_anchor_anatomy",      ["main"]),   # one solve: skin (Step A) / anchor / deep (Step B) + flux=Q_b
    ("make_retrieval_demo",      ["main"]),   # the sweep: A+B per K_d vs Apollo -> RMSE minimum = K_d*
    ("make_anchor_placement",    ["main"]),   # why z0=0.55 m: amplitude + u_rect decay with depth
    ("make_reconstruct_animation", ["filmstrip"]),  # Step-B slope-walk filmstrip (guidebook still)
    ("make_spinup_animation",   ["main"]),    # brute spin-up filmstrip + GIF
    ("make_newmethod_animation", ["main"]),
    ("make_results_animation", ["main"]),  # results-explainer GIF + filmstrip
    ("make_anchor_method_animation", ["main"]),  # step-by-step anchor-method GIF + filmstrip   # anchor-method filmstrip + GIF
    ("make_old_vs_new_animation", ["main"]),  # old-vs-new filmstrip + GIF (was
                                              # unregistered -> went stale across
                                              # two solver revisions; audit 2026-07-04)
    ("make_surface_temp_animation", ["render"]),  # outreach: Sun-driven surface-T
                                                  # globe GIF + filmstrip (figures/anim)
    ("make_speedup_figure",      ["main"]),    # measured wall-clock speed-up
    ("make_baselayer_figure",    ["main"]),    # with/without bedrock base layer
    ("make_equilibrium_demo",    ["main"]),   # guess-independence proof
    ("make_headline_figure",     ["main"]),    # the result in one glance (forest plot)
    ("make_stats_figures",       ["main"]),    # statistics chapter: bootstrap clouds + contrast/p-value
    ("make_svg_figures",        ["main"]),    # hand-authored SVG illustrations (run last: wins)
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
