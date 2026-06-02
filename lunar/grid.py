"""Geometric depth grid construction.

The project rule (see .claude/skills/agents/physics.md) is that the subsurface
grid MUST be geometric — uniform spacing is forbidden because it under-resolves
the diurnal skin depth and over-resolves the deep interior.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .constants import DZ0_DEFAULT, GROWTH_DEFAULT, Z_MAX_DEFAULT


@dataclass(frozen=True)
class DepthGrid:
    """A geometric subsurface depth grid.

    Attributes
    ----------
    z_face : np.ndarray
        Cell-face depths [m], shape (N+1,). ``z_face[0] == 0``.
    z_mid : np.ndarray
        Cell-center depths [m], shape (N,).
    dz : np.ndarray
        Cell thicknesses [m], shape (N,). ``dz[i] = z_face[i+1] - z_face[i]``.
    """

    z_face: np.ndarray
    z_mid: np.ndarray
    dz: np.ndarray

    @property
    def n_layers(self) -> int:
        return int(self.z_mid.size)


def make_geometric_grid(
    z_max: float = Z_MAX_DEFAULT,
    dz0: float = DZ0_DEFAULT,
    growth: float = GROWTH_DEFAULT,
) -> DepthGrid:
    """Construct a geometric depth grid.

    Parameters
    ----------
    z_max : float
        Maximum grid depth [m].
    dz0 : float
        Top-layer thickness [m]. Must be <= ~2 mm to resolve the THz skin
        depth at the surface.
    growth : float
        Geometric growth factor. Each successive layer is ``(1 + growth)``
        times thicker than the previous.

    Returns
    -------
    DepthGrid

    Notes
    -----
    Target properties (Hayne 2017; skill physics agent):
      * >= 10 points within one diurnal skin depth (~5 cm)
      * >= 5 points within one H-parameter scale (~6 cm)
      * Sub-cm spacing in the top 5 cm (for TSUKIMI RTM coupling)
    The defaults in :mod:`lunar.constants` satisfy these; values are
    verified by ``tests/test_grid.py``.
    """
    if dz0 <= 0:
        raise ValueError("dz0 must be positive")
    if growth <= 0:
        raise ValueError("growth must be positive (uniform grids are forbidden)")
    if z_max <= dz0:
        raise ValueError("z_max must exceed dz0")

    faces = [0.0]
    dz = dz0
    while faces[-1] < z_max:
        faces.append(faces[-1] + dz)
        dz *= 1.0 + growth
    z_face = np.asarray(faces, dtype=np.float64)
    dz_arr = np.diff(z_face)
    z_mid = 0.5 * (z_face[:-1] + z_face[1:])
    return DepthGrid(z_face=z_face, z_mid=z_mid, dz=dz_arr)
