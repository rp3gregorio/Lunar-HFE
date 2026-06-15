#!/usr/bin/env python3
"""Run the full reproduction through the 5 notebooks, timing each part.

Executes every notebook in order with the heavy toggles (auxiliary
sensitivity sweeps + Bayesian MCMC) turned ON, so this is a complete
end-to-end reproduction. The committed notebooks are NOT modified --
toggles are flipped in memory only. All figures and output JSONs are
regenerated in the repo as a side effect.

Writes a timing report to docs/RUNTIME.md (updated after each notebook,
so partial results survive an interruption).

Run:  python scripts/run_all_timed.py
"""
from __future__ import annotations
import time, datetime, pathlib, re
import nbformat
from nbconvert.preprocessors import ExecutePreprocessor

REPO = pathlib.Path(__file__).resolve().parents[1]
NBDIR = REPO / "notebooks"
REPORT = REPO / "docs" / "RUNTIME.md"
ORDER = ["00_setup", "01_methods", "02_retrieval", "03_results", "04_discussion"]
PART = {
    "00_setup":      "Environment & data integrity checks",
    "01_methods":    "Methods figures (Figs 1-4) + Table 1",
    "02_retrieval":  "Retrieval + bootstrap + ALL sensitivity sweeps + MCMC",
    "03_results":    "Results figures (Figs 5-9) + Diviner closure + Tables 2-3",
    "04_discussion": "Discussion figures (Figs 10-11) + Table 4",
}


def fmt(sec):
    m, s = divmod(int(round(sec)), 60)
    return f"{m} min {s:2d} s" if m else f"{s} s"


def parse_aux(nb):
    """Pull per-script timings printed inside 02 ('=== x ===' / 'ok in N min')."""
    lines = []
    for c in nb.cells:
        if c.cell_type != "code":
            continue
        for o in c.get("outputs", []):
            txt = o.get("text", "") or "".join(o.get("data", {}).get("text/plain", ""))
            for m in re.finditer(r"===\s*(\S+\.py)\s*===\s*\n\s*ok in ([\d.]+) min", txt):
                lines.append((m.group(1), float(m.group(2)) * 60))
            for m in re.finditer(r"Phase A complete in ([\d.]+) min", txt):
                lines.append(("retrieve_kd.py (Phase A)", float(m.group(1)) * 60))
            for m in re.finditer(r"Phase B MCMC complete in ([\d.]+) min", txt):
                lines.append(("bayesian_crosscheck.py (MCMC)", float(m.group(1)) * 60))
    return lines


def write_report(results, aux, started, finished=None):
    REPORT.parent.mkdir(exist_ok=True)
    L = []
    L.append("# Runtime report — full pipeline reproduction\n")
    L.append(f"Run started: {started}  ")
    L.append(f"\nMachine: executed via `scripts/run_all_timed.py` "
             "(notebooks in order, all toggles ON).\n")
    L.append("\n## Per-notebook (each 'part')\n")
    L.append("| Part | What it does | Time | Status |")
    L.append("|---|---|---|---|")
    total = 0.0
    for name, dt, ok, err in results:
        total += dt
        L.append(f"| `{name}` | {PART[name]} | {fmt(dt)} | "
                 f"{'OK' if ok else 'FAILED'} |")
    L.append(f"| **TOTAL** | full reproduction | **{fmt(total)}** | |")
    if aux:
        L.append("\n## Inside `02_retrieval` — per-script breakdown\n")
        L.append("| Script | Time |")
        L.append("|---|---|")
        for nm, sec in aux:
            L.append(f"| `{nm}` | {fmt(sec)} |")
    fails = [(n, e) for n, d, ok, e in results if not ok]
    if fails:
        L.append("\n## Failures\n")
        for n, e in fails:
            L.append(f"- **{n}**: {e}")
    if finished:
        L.append(f"\nRun finished: {finished}")
    REPORT.write_text("\n".join(L) + "\n")


def main():
    started = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    results, aux = [], []
    for name in ORDER:
        print(f"\n===== executing {name} =====", flush=True)
        nb = nbformat.read(NBDIR / f"{name}.ipynb", as_version=4)
        for c in nb.cells:
            if c.cell_type == "code":
                c.source = (c.source.replace("RUN_AUXILIARY = False", "RUN_AUXILIARY = True")
                                    .replace("RUN_MCMC = False", "RUN_MCMC = True"))
        ep = ExecutePreprocessor(timeout=21600, kernel_name="python3")
        t0 = time.perf_counter()
        ok, err = True, ""
        try:
            ep.preprocess(nb, {"metadata": {"path": str(NBDIR)}})
        except Exception as e:
            ok, err = False, f"{type(e).__name__}: {str(e)[:250]}"
        dt = time.perf_counter() - t0
        results.append((name, dt, ok, err))
        if name == "02_retrieval":
            aux = parse_aux(nb)
        print(f"  -> {name}: {fmt(dt)}  ok={ok} {err}", flush=True)
        write_report(results, aux, started)   # incremental
    finished = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    write_report(results, aux, started, finished)
    print(f"\nDONE. Report -> {REPORT}", flush=True)


if __name__ == "__main__":
    main()
