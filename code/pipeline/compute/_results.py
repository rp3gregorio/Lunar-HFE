"""Read-side accessors for canonical results/ artifacts.

Benchmark and diagnostic scripts need "the retrieved K_d*" as an INPUT
(e.g. to time a solve at the production operating point). Hardcoding it is
how three scripts silently ran at a stale 4.603e-3 across two re-baselines
-- the same duplication failure as the Q_b bug. Import from here instead;
the retrieval json (written ONLY by retrieve_kd.py) is the single source.
"""
from __future__ import annotations

import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[2]
_RETRIEVAL = ROOT / "results" / "kd_retrieval_results.json"


def retrieved_kd_star(site: str = "A15") -> float:
    """K_d* [W m^-1 K^-1] for `site` from the canonical retrieval artifact.

    Raises loudly if the artifact is missing -- run `make retrieve` first;
    do NOT fall back to a hardcoded value here.
    """
    if not _RETRIEVAL.exists():
        raise FileNotFoundError(
            f"{_RETRIEVAL} not found -- run `make retrieve` before scripts "
            "that consume the retrieved K_d*")
    return float(json.loads(_RETRIEVAL.read_text())[site]["kd_star"])
