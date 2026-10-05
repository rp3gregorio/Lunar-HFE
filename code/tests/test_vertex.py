"""K_d* vertex routine (retrieve_kd.kd_star_from_residuals).

Regression for audit 2026-10-04: a merged grid built with np.unique over two
constructions of the same K_d can keep last-bit twins. When the RMSE minimum
sat on such a twin, the 3-point parabola was singular and returned a vertex
outside its bracket (7.81 for a true minimum at 6.5 mW m^-1 K^-1).
"""
import pathlib
import sys

import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "pipeline" / "compute"))
from retrieve_kd import kd_star_from_residuals  # noqa: E402


def _residuals(grid, k_true=6.5e-3, curv=4e4):
    # one "sensor" whose residual makes RMSE(K_d) a parabola centred on k_true
    return np.sqrt(0.2 + curv * (grid - k_true) ** 2)[None, :]


def test_vertex_recovers_parabola_minimum():
    grid = np.round(np.arange(5.0, 8.01, 0.1), 7) * 1e-3
    ks, rs = kd_star_from_residuals(_residuals(grid, 6.53e-3), grid, warn_coarse=False)
    assert abs(ks - 6.53e-3) < 0.01e-3
    assert rs >= np.sqrt(0.2) - 1e-9


def test_last_bit_twin_does_not_corrupt_vertex():
    coarse = np.arange(1.0, 26.01, 0.5) * 1e-3                 # 6.5e-3 built one way
    dense = np.round(np.arange(5.5e-3, 7.5001e-3, 0.1e-3), 7)   # ... and another
    grid = np.unique(np.concatenate([coarse, dense]))
    assert np.sum(np.diff(grid) < 1e-12) >= 1                  # the twin is present
    R = _residuals(grid)
    R[:, np.isclose(grid, 6.5e-3, rtol=0, atol=1e-12)] = R[:, np.argmin(np.abs(grid - 6.5e-3))]
    ks, _ = kd_star_from_residuals(R, grid, warn_coarse=False)
    assert abs(ks - 6.5e-3) < 0.05e-3

