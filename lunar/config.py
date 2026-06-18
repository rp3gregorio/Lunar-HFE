"""Single source of truth for run configuration and site parameters.

In plain English
----------------
Think of this file as the project's "settings menu." Every knob the
simulation can turn -- which two Apollo sites we model, how deep the
soil column goes, how finely we slice it, and how long the simulator
runs before we trust its answer -- is defined here, in ONE place. Other
files import these settings instead of re-typing them, so a number can
never accidentally disagree between two parts of the code. If you ever
want to change "what the experiment is," you almost always change it
here and nowhere else.

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
# One entry per Apollo borehole. Field meanings, in plain English:
#   lat/lon     - where on the Moon the borehole is (degrees)
#   albedo      - how reflective the surface is (0 = black, 1 = mirror)
#   emissivity  - how efficiently the surface radiates heat away (~0.95)
#   Q_BASAL     - heat seeping up from the Moon's deep interior [W m^-2]
#   T_MEAN_EFF  - only a starting guess for the deep temperature; the
#                 equilibrium solver erases its influence (see equilibrium.py)
#   MIN_DEPTH_CM- shallowest sensor depth we trust for the deep-K_d fit
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

# --- optional bedrock layer (OFF by default) ---------------------------------
# A toggle for FUTURE deep-profile work (e.g. ice-stability studies), where
# the temperature far below the regolith matters. When ``enabled`` is False
# (the default) the model is regolith-only and the Apollo K_d retrieval is
# byte-for-byte unchanged -- every Heat-Flow sensor sits at <= 2.4 m, far
# above the transition, so enabling bedrock (at z_bedrock_m=10 m) shifts
# sensor-depth temperatures by only ~0.05 K, well within the measurement
# scatter. When enabled, conductivity below ``z_bedrock_m`` smoothly
# ramps from the regolith value to ``K_rock`` (solid-rock conductivity).
# See :func:`lunar.properties.with_bedrock` and run_with(bedrock=...).
BEDROCK = dict(
    enabled=False,      # master toggle -- keep False for the published paper
    z_bedrock_m=10.0,   # depth where regolith gives way to bedrock [m]
    width_m=1.5,        # half-width of the smooth transition [m]
    K_rock=2.0,         # bedrock thermal conductivity [W m^-1 K^-1]
)
