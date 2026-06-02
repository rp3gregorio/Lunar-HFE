"""Grid construction tests.

Requirements from ``.claude/skills/agents/physics.md``:
  * Grid is geometric, not uniform.
  * >= 10 points within one diurnal skin depth (~5 cm).
  * >= 5 points within one H scale height (~6 cm).
  * Sub-cm spacing in the top 5 cm (for the THz RTM coupling).
"""

import numpy as np
import pytest

from lunar.grid import make_geometric_grid


def test_grid_is_geometric():
    g = make_geometric_grid()
    ratios = g.dz[1:] / g.dz[:-1]
    # All ratios should be the same (1 + growth) within rounding.
    assert np.allclose(ratios, ratios[0], rtol=1e-12)
    # And strictly > 1 (no uniform grids allowed).
    assert ratios[0] > 1.0


def test_grid_reaches_z_max():
    g = make_geometric_grid(z_max=3.0)
    assert g.z_face[-1] >= 3.0


def test_grid_top_layer_is_sub_cm():
    g = make_geometric_grid()
    assert g.dz[0] <= 1e-2  # top layer is <= 1 cm (default is 2 mm)


def test_grid_resolves_diurnal_skin_depth():
    g = make_geometric_grid()
    n_in_skin_depth = int((g.z_face <= 0.05).sum())
    assert n_in_skin_depth >= 10


def test_grid_resolves_H_parameter():
    g = make_geometric_grid()
    n_in_H = int((g.z_face <= 0.06).sum())
    assert n_in_H >= 5


def test_grid_rejects_uniform_request():
    with pytest.raises(ValueError):
        make_geometric_grid(growth=0.0)


def test_grid_rejects_zero_top_layer():
    with pytest.raises(ValueError):
        make_geometric_grid(dz0=0.0)
