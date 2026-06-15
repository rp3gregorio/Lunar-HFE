"""Single source of truth for run configuration and site parameters.

Everything that used to be copy-pasted across the pipeline and figure
scripts -- the per-site table (SITES), the depth grid, the Hayne-form
bundle, the equilibrium-solver settings, the K_d sweep grids, and the
3-layer diagnostic parameters -- lives here so it cannot drift between
files. Cited physical constants live in :mod:`lunar.constants`; this
module composes them into ready-to-use run configuration.

Import it, never redefine it:

    from lunar.config import SITES, GRID, HAYNE, S0, T_LUNAR, DT_STEP
"""
from __future__ import annotations

import numpy as np

from .constants import (
    CHI_RADIATIVE,
    H_PARAMETER,
    K_SURFACE,
    LUNATION_SECONDS,
    SOLAR_CONSTANT,
    T_REFERENCE,
)

# --- forcing / time-stepping -------------------------------------------------
S0 = SOLAR_CONSTANT          # 1361 W m^-2 (Kopp & Lean 2011)
T_LUNAR = LUNATION_SECONDS   # one synodic lunation [s]
DT_STEP = 3600.0             # solver time step [s] (1 hour)

# --- depth grid (geometric) --------------------------------------------------
GRID = dict(z_max=5.0, dz0=0.002, growth=0.08)

# --- Hayne (2017) conductivity-form bundle (the swept K_d is separate) -------
HAYNE = dict(K_S=K_SURFACE, H=H_PARAMETER, CHI=CHI_RADIATIVE, T_REF=T_REFERENCE)

# --- flux-anchored equilibrium solver (lunar.equilibrium) --------------------
EQ_Z_ANCHOR = 0.55      # anchor depth [m], below the rectification zone
EQ_N_INNER = 12         # inner spin-up lunations per outer iteration
EQ_MAX_OUTER = 20       # outer-iteration cap
EQ_ANCHOR_TOL = 0.005   # convergence tolerance on the anchor temperature [K]

# Legacy fixed-spin-up knobs (only for direct solve_pixel callers).
N_LUN_FAST = 30
TOL_FAST = 0.05

# --- per-site configuration (THE single definition) --------------------------
SITES = {
    "A15": dict(tag="A15", label="Apollo 15", lat=26.13, lon=3.63,
                albedo=0.131, emissivity=0.95, Q_BASAL=0.021,
                T_MEAN_EFF=250.0, MIN_DEPTH_CM=80, mission="a15"),
    "A17": dict(tag="A17", label="Apollo 17", lat=20.19, lon=30.77,
                albedo=0.137, emissivity=0.95, Q_BASAL=0.015,
                T_MEAN_EFF=255.0, MIN_DEPTH_CM=80, mission="a17"),
}

# --- K_d sweep grids [W m^-1 K^-1], sized so bootstrap tails sit inside ------
KD_GRIDS = {
    "A15": np.linspace(1.0e-3, 15.0e-3, 28),
    "A17": np.linspace(3.0e-3, 25.0e-3, 30),
}

# --- bootstrap ---------------------------------------------------------------
DEPTH_SIGMA_CM = 2.5     # Nagihara (2018) sensor-placement uncertainty

# --- discrete 3-layer diagnostic model (this work) ---------------------------
TL_Z1, TL_Z2 = 0.02, 0.20             # layer boundaries [m]
TL_RHO_REF = 1800.0                   # Hayne (2017) nominal deep density
TL_RHO_SITE = {"A15": 2000.0, "A17": 1900.0}  # per-site RMSE-optimal deep rho
