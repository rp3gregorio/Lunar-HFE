"""Read-side accessors for canonical results/ artifacts.

Benchmark scripts need the retrieved K_d* as an input (to time a solve at
the production operating point). They read it here, from the retrieval json
written by retrieve_kd.py, instead of hard-coding a value.
"""
from __future__ import annotations

import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[2]
_RETRIEVAL = ROOT / "results" / "kd_retrieval_results.json"


def retrieved_kd_star(site: str = "A15") -> float:
    """K_d* [W m^-1 K^-1] for `site` from the canonical retrieval artifact.

    Raises loudly if the artifact is missing -- run retrieve_kd.py (make analysis) first;
    do NOT fall back to a hardcoded value here.
    """
    if not _RETRIEVAL.exists():
        raise FileNotFoundError(
            f"{_RETRIEVAL} not found -- run retrieve_kd.py (make analysis) before scripts "
            "that consume the retrieved K_d*")
    return float(json.loads(_RETRIEVAL.read_text())[site]["kd_star"])
