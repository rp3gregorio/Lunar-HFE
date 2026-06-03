"""Apollo HFE depth-table loader.

Lightweight reader for the bundled Apollo 15/17 Heat Flow Experiment
depth tables (Nagihara et al. 2018 restoration; PDS Geosciences Node
bundle ``urn:nasa:pds:a15_17_hfe_concatenated``). Returns plain numpy
structured arrays — no pandas / astropy dependency.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np

_DATA = Path(__file__).resolve().parent.parent / "data"


def load_apollo_hfe_depth(mission: str, probe_num: int) -> np.ndarray:
    """Load the depth metadata for one HFE probe.

    Returns a structured array with fields
    ``('time_iso', 'T', 'sensor', 'depth_cm', 'flags')``.
    Depths are reported in centimeters below the regolith surface.

    Parameters
    ----------
    mission : {'a15', 'a17'}
    probe_num : {1, 2}
    """
    if mission not in ("a15", "a17"):
        raise ValueError(f"mission must be 'a15' or 'a17', not {mission!r}")
    if probe_num not in (1, 2):
        raise ValueError("probe_num must be 1 or 2")
    path = _DATA / "apollo" / "depth" / f"{mission}p{probe_num}_depth.tab"
    if not path.is_file():
        raise FileNotFoundError(f"HFE depth file not found: {path}")

    dt = np.dtype(
        [
            ("time_iso", "U24"),
            ("T", np.float64),
            ("sensor", "U8"),
            ("depth_cm", np.float64),
            ("flags", np.int64),
        ]
    )
    return np.genfromtxt(path, delimiter=",", dtype=dt, skip_header=1)
