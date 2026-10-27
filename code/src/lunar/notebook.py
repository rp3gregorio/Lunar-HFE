"""Run the analysis from the notebooks in code/notebooks/.

Each analysis step is one script in ``code/pipeline/``. A notebook cell calls
``step(...)`` with that script, and the script's own printout streams into the
notebook while it runs. The run mode, set once at the top of the notebook,
decides what actually runs:

  "show"   run nothing; read the stored results (the repository ships them).
           Minutes.
  "quick"  run every step that takes a few minutes, and the long ones in their
           fast form where they have one (re-analysing the stored model runs);
           the remaining long steps show their stored results. About 45 min.
  "full"   run every step from scratch, as the paper did. About 6 h on a
           six-core laptop.

Figures are made in every mode when they are missing (a fresh clone has
none), and remade in "quick" and "full", or always with ``always=True``. On macOS each run is wrapped in
``caffeinate`` so the computer does not sleep during a long step.

``Checks`` puts each value next to the number printed in the paper, and
``summary()`` counts every check the notebook has shown.

In "full" mode each step first prints where the run stands (step k of n, the
time left for the whole run and when it should finish, rescaled to this
computer's speed as steps complete), the long scripts draw progress bars with
their own time left, and ``timing()`` lists every step's time at the end.
"""
from __future__ import annotations

import codecs
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys
import time

from lunar._bootstrap import find_repo_root

CODE = find_repo_root()                    # .../code
REPO = CODE.parent                         # repository root (holds figures/)
PIPELINE = CODE / "pipeline"
RESULTS = CODE / "results"
FIGURES = REPO / "figures"

MODES = ("show", "quick", "full")
QUICK_MAX_MIN = 6                          # "quick" runs steps up to this long
_mode = "show"
_shown: dict[str, list] = {}               # every Checks table shown, by title (for summary())
SNAPSHOT = RESULTS / "before_full_run"     # the results as they were before a full run
# caches two steps reuse without being asked (to resume an interrupted run); a
# full run moves them into the snapshot so that it recomputes them
AUTO_CACHES = ("joint_chi_density_cache.npz", "joint_mcmc_grid.npz")
# what legitimately changes from run to run: timings and the commit stamp
_VOLATILE = re.compile(r"runtime_s|git_commit|ms_per_lun|runs_s$|speedup")
_plan: list[tuple[str, float]] = []        # the full run's (script, usual minutes), from plan()
_timing: dict[str, tuple[float, float]] = {}   # script -> (usual minutes, minutes this run)


def set_mode(mode: str) -> None:
    """Choose what the ``step`` cells run: "show", "quick" or "full"."""
    global _mode
    if mode not in MODES:
        raise ValueError(f"mode must be one of {MODES}, not {mode!r}")
    _mode = mode
    print(f"Run mode: {mode!r}. " + {
        "show": "Nothing is recomputed; every step shows its stored result.",
        "quick": "Short steps run; long steps run in their fast form or show their stored result.",
        "full": "Every step runs from scratch (about 6 h in all).",
    }[mode])


def mode() -> str:
    return _mode


def _minutes(m: float) -> str:
    return "seconds" if m < 1 else f"about {m:g} min" if m < 90 else f"about {m / 60:.1f} h"


def _run(script: str, args: tuple[str, ...]) -> float:
    path = PIPELINE / script
    cmd = [sys.executable, "-u", str(path), *args]
    if sys.platform == "darwin" and shutil.which("caffeinate"):
        cmd = ["caffeinate", "-dims", *cmd]          # keep the Mac (and screen) awake
    t0 = time.time()
    # the scripts draw with matplotlib's file backend, as from a terminal; without
    # this they inherit the notebook kernel's inline backend, whose screen
    # resolution changes how a measured legend strip rounds (Figure 4 grew 0.7 pt)
    env = {**os.environ, "MPLBACKEND": "Agg"}
    proc = subprocess.Popen(cmd, cwd=CODE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, env=env)
    # passed through as it arrives, carriage returns kept, so a progress bar
    # redraws in place (in a notebook and in a terminal) instead of piling up lines
    dec = codecs.getincrementaldecoder("utf-8")(errors="replace")
    while chunk := proc.stdout.read1(4096):
        sys.stdout.write(dec.decode(chunk))
        sys.stdout.flush()
    sys.stdout.write(dec.decode(b"", final=True))
    rc = proc.wait()
    if rc != 0:
        raise RuntimeError(f"{script} stopped with an error (exit code {rc}); its output is above.")
    print(f"--- {pathlib.Path(script).name} finished in {_clock(time.time() - t0)}", flush=True)
    return time.time() - t0


def _clock(seconds: float) -> str:
    m, s = divmod(int(round(seconds)), 60)
    h, m = divmod(m, 60)
    return f"{h} h {m:02d} min" if h else f"{m} min {s:02d} s" if m else f"{s} s"


def plan(steps) -> None:
    """The steps of the full run with their usual minutes (the ``minutes`` of each
    ``step``), so that each step can say how much of the run is left."""
    global _plan
    _plan = [(s, float(m)) for s, m in steps]
    if _mode == "full":
        _snapshot()
        total = sum(m for _, m in _plan)
        print(f"Full run: {len(_plan)} steps. Their listed times, rounded up, add up to {total / 60:.1f} h; "
              f"each step rescales the estimate to this computer.")


def _announce(script: str, minutes: float) -> None:
    """Before a step of the full run: where the run stands and when it should end."""
    names = [s for s, _ in _plan]
    if script not in names:
        return
    k = names.index(script) + 1
    left = sum(m for s, m in _plan if s not in _timing)               # this step and the rest
    done_usual = sum(u for u, _ in _timing.values())
    done_real = sum(a for _, a in _timing.values())
    speed = done_real / done_usual if done_usual >= 10 else 1.0       # this computer vs the reference
    left_real = left * speed
    end = time.strftime("%H:%M", time.localtime(time.time() + 60 * left_real))
    note = f", {speed:.2f} x the usual times so far" if done_usual >= 10 else ""
    print(f"[step {k} of {len(_plan)}] started {time.strftime('%H:%M')}; "
          f"the whole run has about {_clock(60 * left_real)} left{note}, ending around {end}.", flush=True)


def _snapshot() -> None:
    """Before a full run: copy every results file into SNAPSHOT and move the two
    self-reused caches there, so the run starts from scratch and can be compared
    with what it replaced. An existing snapshot (an interrupted run) is kept, and
    so are the caches the run has rebuilt since, so a rerun resumes."""
    if SNAPSHOT.exists():
        print(f"Kept the snapshot of {time.strftime('%Y-%m-%d %H:%M', time.localtime(SNAPSHOT.stat().st_mtime))} "
              f"in {SNAPSHOT.relative_to(CODE)}; delete that folder to start a new comparison.")
        return
    SNAPSHOT.mkdir()
    n = 0
    for f in RESULTS.glob("*.json"):
        shutil.copy2(f, SNAPSHOT / f.name)
        n += 1
    moved = [c for c in AUTO_CACHES if (RESULTS / c).exists()]
    for c in moved:
        shutil.move(RESULTS / c, SNAPSHOT / c)
    print(f"Copied {n} results files to {SNAPSHOT.relative_to(CODE)} for the comparison at the end"
          + (f"; moved {', '.join(moved)} there, so they are recomputed." if moved else "."))


def _strip(o):
    if isinstance(o, dict):
        return {k: _strip(v) for k, v in o.items() if not _VOLATILE.search(k)}
    if isinstance(o, list):
        return [_strip(v) for v in o]
    return o


def _diff(a, b, path="", out=None):
    """Paths where two parsed JSON trees differ, with the size of numeric differences."""
    out = [] if out is None else out
    if isinstance(a, dict) and isinstance(b, dict):
        for k in sorted(set(a) | set(b)):
            if k not in a or k not in b:
                out.append((f"{path}/{k}", "only in one"))
            else:
                _diff(a[k], b[k], f"{path}/{k}", out)
    elif isinstance(a, list) and isinstance(b, list) and len(a) == len(b):
        for i, (x, y) in enumerate(zip(a, b)):
            _diff(x, y, f"{path}[{i}]", out)
    elif a != b:
        both = all(isinstance(v, (int, float)) and not isinstance(v, bool) for v in (a, b))
        out.append((path or "/", abs(a - b) if both else "changed"))
    return out


def compare_with_snapshot():
    """Every results file against its copy from before the full run (timings and
    the commit stamp left out): identical; the same to rounding (every number
    within a relative 1e-8, or 1e-10 near zero, as when another Python or numpy
    version computes it);
    different (where, by how much); or not rewritten by this run. A table."""
    import pandas as pd
    if not SNAPSHOT.exists():
        print("No snapshot: it is made when a full run starts.")
        return None
    t_snap = SNAPSHOT.stat().st_mtime
    rows = []
    for old in sorted(SNAPSHOT.glob("*.json")):
        new = RESULTS / old.name
        if not new.exists():
            rows.append((old.name, "missing now", "")); continue
        if new.stat().st_mtime < t_snap:
            rows.append((old.name, "not rewritten by this run", "")); continue
        a, b = _strip(json.loads(old.read_text())), _strip(json.loads(new.read_text()))
        d = _diff(a, b)
        if not d:
            rows.append((old.name, "identical", ""))
        elif _rounding_only(a, b):
            rel = _largest_relative(a, b)
            rows.append((old.name, f"same to rounding (largest relative difference {rel:.1g})", ""))
        else:
            num = [x for _, x in d if isinstance(x, float) or isinstance(x, int)]
            where = ", ".join(p for p, _ in d[:3]) + (" ..." if len(d) > 3 else "")
            rows.append((old.name, f"{len(d)} values differ" + (f", largest {max(num):.3g}" if num else ""), where))
    df = pd.DataFrame(rows, columns=["results file", "against the snapshot", "first differences"])
    redone = df[df["against the snapshot"] != "not rewritten by this run"]
    same = (redone["against the snapshot"] == "identical").sum()
    near = redone["against the snapshot"].str.startswith("same to rounding").sum()
    print(f"{len(redone)} results files rewritten by this run: {same} identical to the snapshot, "
          f"{near} the same to rounding, {len(redone) - same - near} different. "
          f"Files no step of this run writes are listed as not rewritten.")
    return df


def _numbers(o):
    """The numbers of a parsed JSON tree, in order, with its non-numeric leaves."""
    if isinstance(o, dict):
        for k in sorted(o):
            yield from _numbers(o[k])
    elif isinstance(o, list):
        for v in o:
            yield from _numbers(v)
    else:
        yield o


def _rounding_only(a, b, rel: float = 1e-8, tiny: float = 1e-10) -> bool:
    """Same structure and text; every number within ``rel`` (relative) or, for
    numbers near zero, within ``tiny`` (absolute)."""
    xa, xb = list(_numbers(a)), list(_numbers(b))
    if len(xa) != len(xb):
        return False
    for x, y in zip(xa, xb):
        num = all(isinstance(v, (int, float)) and not isinstance(v, bool) for v in (x, y))
        if not num:
            if x != y:
                return False
        elif abs(x - y) > max(rel * max(abs(x), abs(y)), tiny):
            return False
    return True


def _largest_relative(a, b) -> float:
    return max((abs(x - y) / max(abs(x), abs(y), 1e-12)
                for x, y in zip(_numbers(a), _numbers(b))
                if all(isinstance(v, (int, float)) and not isinstance(v, bool) for v in (x, y))), default=0.0)


def timing():
    """Each step of this run next to its usual time (a table), and the total."""
    import pandas as pd
    rows = [(s, u, a) for s, (u, a) in _timing.items()]
    if not rows:
        print("No step has run in this session.")
        return None
    df = pd.DataFrame(rows, columns=["step", "usual (min)", "this run (min)"]).round(1)
    u, a = df["usual (min)"].sum(), df["this run (min)"].sum()
    print(f"{len(rows)} steps: {a / 60:.2f} h this run, {u / 60:.2f} h usual.")
    return df


def run(script: str, *args: str) -> None:
    """Run one pipeline script now, whatever the mode (e.g. a download)."""
    _run(script, args)


def _stored(writes: tuple[str, ...]) -> str:
    out = []
    for w in writes:
        p = RESULTS / w
        out.append(f"results/{w} ({time.strftime('%Y-%m-%d', time.localtime(p.stat().st_mtime))})"
                   if p.exists() else f"results/{w} MISSING")
    return ", ".join(out)


def step(script: str, minutes: float, writes: str | tuple[str, ...] = (), args: tuple[str, ...] = (),
         quick: tuple[str, ...] | None = None, quick_needs: str | None = None,
         needs: tuple[str, ...] = ()) -> None:
    """Run one pipeline script, or show its stored result, depending on the mode.

    script       path under code/pipeline/, e.g. "compute/compute_joint_albedo_fit.py"
    minutes      how long a full run takes (for the printout, and for "quick")
    writes       the results file(s) it writes, shown when it does not run
    quick        arguments for the fast form used in "quick" mode (e.g. ("--reuse",))
    quick_needs  a file (under code/) the fast form needs; without it "quick" shows the stored result
    needs        input files (under code/) the script needs to run, e.g. the Diviner tiles
    """
    writes = (writes,) if isinstance(writes, str) else tuple(writes)
    name = pathlib.Path(script).name
    lacking = [n for n in needs if not (CODE / n).exists()]
    if lacking and _mode != "show":
        msg = f"{name} needs {', '.join(lacking)}, which is not downloaded (see section 1.5 of 1_run_analysis.ipynb)"
        if _mode == "full":
            raise FileNotFoundError(msg)
        print(f"■ {msg}; stored result used, {_stored(writes)}.")
        return
    if _mode == "full":
        _announce(script, minutes)
        print(f"▶ {name}: running ({_minutes(minutes)})", flush=True)
        _timing[script] = (minutes, _run(script, args) / 60)
        return
    if _mode == "quick":
        if quick is not None and (quick_needs is None or (CODE / quick_needs).exists()):
            print(f"▶ {name} {' '.join(quick)}: running the fast form (full run {_minutes(minutes)})", flush=True)
            _run(script, tuple(quick))
            return
        if minutes <= QUICK_MAX_MIN:
            print(f"▶ {name}: running ({_minutes(minutes)})", flush=True)
            _run(script, args)
            return
    missing = [w for w in writes if not (RESULTS / w).exists()]
    if missing:
        raise FileNotFoundError(f"{name}: no stored {', '.join(missing)}; set the mode to 'full' to compute it.")
    print(f"■ {name}: stored result used, {_stored(writes)}. A full run takes {_minutes(minutes)}.")


def figures(script: str, makes: str | tuple[str, ...], minutes: float = 1, args: tuple[str, ...] = (),
            needs: tuple[str, ...] = (), always: bool = False) -> None:
    """Make figures: when any is missing, again in "quick" and "full", and every time if ``always``.

    makes  the figures it writes, under figures/ ("fig_x" means fig_x.pdf; "anim/x.gif" as given)
    needs  input files (under code/) it needs, e.g. the LOLA map for SI Figure S1
    """
    makes = (makes,) if isinstance(makes, str) else tuple(makes)
    missing = [m for m in makes if not (FIGURES / (m if "." in m else f"{m}.pdf")).exists()]
    lacking = [n for n in needs if not (CODE / n).exists()]
    if lacking:
        print(f"■ {pathlib.Path(script).name} needs {', '.join(lacking)}, which is not downloaded (see section 1.5 of 1_run_analysis.ipynb).")
        return
    if _mode == "show" and not missing and not always:
        print(f"■ {pathlib.Path(script).name}: figures already made ({', '.join(makes)}).")
        return
    print(f"▶ {pathlib.Path(script).name}: making figures ({_minutes(minutes)})", flush=True)
    _run(script, args)


def show(fig: str, width: int = 900) -> None:
    """Display figures/<fig>.pdf in the notebook (first page, as an image)."""
    from IPython.display import Image, display
    p = FIGURES / f"{fig}.pdf"
    if not p.exists():
        print(f"figures/{fig}.pdf is not made yet; run the figure cell above.")
        return
    import fitz                                    # PyMuPDF (installed with the dev extras)
    pix = fitz.open(p)[0].get_pixmap(dpi=110, alpha=False)
    display(Image(data=pix.tobytes("png"), width=width))


def load(name: str) -> dict:
    """Read results/<name> (JSON)."""
    return json.loads((RESULTS / name).read_text())


def rounded(value: float, fmt: str = ".2f") -> str:
    """``value`` as the paper prints it: rounded half up (5.25 -> 5.3), no "-0.00"."""
    from decimal import Decimal, ROUND_HALF_UP
    n = int(fmt.lstrip("+").split(".")[1].rstrip("f"))
    d = Decimal(repr(float(value))).quantize(Decimal(1).scaleb(-n), rounding=ROUND_HALF_UP)
    return format(abs(d) if d == 0 else d, fmt)


def span(values, fmt: str = ".1f") -> str:
    """The range of ``values`` as printed in the paper, e.g. "4.5-6.6"."""
    v = [float(x) for x in values]
    return f"{rounded(min(v), fmt)}-{rounded(max(v), fmt)}"


class Checks:
    """Each value next to the number printed in the paper.

    ``add(label, value, paper, fmt)`` rounds ``value`` the way the paper does
    (half up, ``fmt`` as in ``format(value, fmt)``) and compares the text. A
    paper value written "<0.05" passes when the size of the value is below 0.05.
    ``add_text`` compares text built in the notebook (e.g. a range "4.9-6.1").
    """

    def __init__(self, title: str = "") -> None:
        self.title, self.rows = title, []

    def add(self, label: str, value: float, paper: str, fmt: str = ".2f") -> None:
        if paper.startswith("<"):
            ok, shown = abs(value) < float(paper[1:]), format(value, ".2g")
        elif "e" in fmt:                                # 7e-19: compare mantissa and exponent
            m, e = format(value, fmt).split("e")
            shown = f"{m}e{int(e)}"
            ok = shown == paper
        else:                                           # round half up, as printed (5.25 -> 5.3)
            shown = rounded(value, fmt)
            ok = shown == paper
        self.rows.append((label, shown, paper, "✓" if ok else "✗ differs"))

    def add_text(self, label: str, shown: str, paper: str) -> None:
        self.rows.append((label, shown, paper, "✓" if shown == paper else "✗ differs"))

    def show(self):
        import pandas as pd
        from IPython.display import display
        df = pd.DataFrame(self.rows, columns=["quantity", "this repository", "paper", "match"])
        if self.title:
            print(self.title)
        display(df.style.hide(axis="index"))
        bad = [r[0] for r in self.rows if r[3] != "✓"]
        print("All values match the paper." if not bad else f"{len(bad)} value(s) differ: {', '.join(bad)}")
        _shown[self.title] = list(self.rows)
        return not bad


def summary() -> bool:
    """Count every check shown so far; list any value that differs from the paper."""
    rows = [(t, r) for t, rs in _shown.items() for r in rs]
    bad = [(t, r) for t, r in rows if r[3] != "✓"]
    print(f"{len(rows)} values checked against the paper in {len(_shown)} tables: "
          f"{len(rows) - len(bad)} match, {len(bad)} differ.")
    for t, r in bad:
        print(f"  ✗ {t} {r[0]}: this repository {r[1]}, paper {r[2]}")
    return not bad
