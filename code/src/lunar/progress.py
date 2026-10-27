"""Progress bars for the long pipeline steps: count done, time elapsed, time left.

The scripts run as subprocesses of the notebooks (lunar.notebook passes their
output through with the carriage returns kept, so each bar redraws in place)
or from a terminal. Wrapping a loop in ``bar`` changes nothing it computes.
"""
from __future__ import annotations

from tqdm import tqdm

_FORMAT = ("{desc}: {percentage:3.0f}% |{bar:20}| {n_fmt}/{total_fmt} {unit}  "
           "[{elapsed} elapsed, about {remaining} left]")


def bar(iterable=None, *, total: int | None = None, desc: str = "", unit: str = "rows"):
    """``tqdm`` with the pipeline's format; redraws at most every 2 s."""
    return tqdm(iterable, total=total, desc=desc, unit=unit, bar_format=_FORMAT,
                mininterval=2.0, smoothing=0.1, ascii=" #")
