"""Run the analysis from the notebooks.

Each analysis step is one script in ``code/pipeline/``. A notebook cell calls
``step(...)`` with that script, and the script's own printout streams into the
notebook while it runs. The run mode, set once at the top of each notebook,
decides what actually runs:

  "show"   run nothing; read the stored results (the repository ships them).
           Minutes.
  "quick"  run every step that takes a few minutes, and the long ones in their
           fast form where they have one (re-analysing the stored model runs);
           the remaining long steps show their stored results. About 30 min.
  "full"   run every step from scratch, as the paper did. About 6 h on a
           six-core laptop.

Figures are made in every mode when they are missing (a fresh clone has
none), and remade in "quick" and "full". On macOS each run is wrapped in
``caffeinate`` so the computer does not sleep during a long step.

``Checks`` puts each value next to the number printed in the paper.
"""
from __future__ import annotations

import json
import pathlib
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


def _run(script: str, args: tuple[str, ...]) -> None:
    path = PIPELINE / script
    cmd = [sys.executable, "-u", str(path), *args]
    if sys.platform == "darwin" and shutil.which("caffeinate"):
        cmd = ["caffeinate", "-dims", *cmd]          # keep the Mac (and screen) awake
    t0 = time.time()
    proc = subprocess.Popen(cmd, cwd=CODE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                            text=True, bufsize=1)
    for line in proc.stdout:
        print(line, end="", flush=True)
    rc = proc.wait()
    if rc != 0:
        raise RuntimeError(f"{script} stopped with an error (exit code {rc}); its output is above.")
    print(f"--- {pathlib.Path(script).name} finished in {time.time() - t0:.0f} s", flush=True)


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
        msg = f"{name} needs {', '.join(lacking)}, which is not downloaded (see notebook 00)"
        if _mode == "full":
            raise FileNotFoundError(msg)
        print(f"■ {msg}; stored result used, {_stored(writes)}.")
        return
    if _mode == "full":
        print(f"▶ {name}: running ({_minutes(minutes)})", flush=True)
        _run(script, args)
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
            needs: tuple[str, ...] = ()) -> None:
    """Make figures: always when any is missing, and again in "quick" and "full".

    makes  the figures it writes, under figures/ ("fig_x" means fig_x.pdf; "anim/x.gif" as given)
    needs  input files (under code/) it needs, e.g. the LOLA map for SI Figure S1
    """
    makes = (makes,) if isinstance(makes, str) else tuple(makes)
    missing = [m for m in makes if not (FIGURES / (m if "." in m else f"{m}.pdf")).exists()]
    lacking = [n for n in needs if not (CODE / n).exists()]
    if lacking:
        print(f"■ {pathlib.Path(script).name} needs {', '.join(lacking)}, which is not downloaded (see notebook 00).")
        return
    if _mode == "show" and not missing:
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
            from decimal import Decimal, ROUND_HALF_UP
            n = int(fmt.split(".")[1].rstrip("f"))
            d = Decimal(repr(float(value))).quantize(Decimal(1).scaleb(-n), rounding=ROUND_HALF_UP)
            shown = format(abs(d) if d == 0 else d, fmt)    # no "-0.00"
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
        return not bad
