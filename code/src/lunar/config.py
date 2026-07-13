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
# Solver time step [s]. RE-BASELINED 3600 -> 1800 on 2026-07-03 (audit
# AUDIT_2026-07-03 F-5): 3600 s was not temporally converged. The dominant
# O(dt) error was the MISSING WRAP STEP in the cycle chaining (solve_pixel:
# the periodic grid spans [0, P-dt]; skipping the final t[-1] -> P step
# slipped the phase by dt per lunation and made even the periodic attractor
# first-order: +61 mK/halving at 1800 s, which biased K_d*(A17) by +0.6 mW).
# With the wrap step + CN_PICARD_SWEEPS below, the attractor drift is
# ~ -4 mK/halving. Certification is in K_d* space via commensurate ladders
# (pipeline/compute/dt_ladder.py -> results/dt_kdstar_certification*.json);
# re-run the ladder if any of these values change.
DT_STEP = 1800.0
# Midpoint-Picard corrector sweeps per Crank-Nicolson step (solver._step).
# Each sweep re-solves the step with K, c_p evaluated at 0.5*(T_prev + T_new)
# (implicit-midpoint prescription) and the surface Newton re-anchored at the
# implicit T_new[0]. 0 = the pre-2026-07-03 frozen-property linearisation.
# Attractor dt drift per halving at dt=1800 (A15, 6000-lunation C++ ladder):
# sweeps 1/2/4/8 -> -8.6/-4.2/-2.2/-2.0 mK; 2 sweeps sit within ~2 mK of the
# fixed point (~0.02 mW on K_d*(A17)) at 3 tridiagonal solves per step.
# Keep in sync with the C++ port (cpp/solver.cpp reads it from the blob).
CN_PICARD_SWEEPS = 2

# --- depth grid (geometric) --------------------------------------------------
GRID = dict(z_max=5.0, dz0=0.002, growth=0.08)

# --- K_d retrieval sweep grids [W m^-1 K^-1] ---------------------------------
# A WIDE coarse span (so the bootstrap upper-tail percentiles sit inside the
# swept range, not at the grid edge) UNION a DENSE 0.2 mW band bracketing the
# minimum so the 3-point parabola vertex is grid-converged. A uniform 28/30-pt
# grid (0.5-0.76 mW) biased the vertex HIGH by a coarse-parabola artifact (A15:
# 4.641 coarse vs 4.603 dense; ~0.04 mW). SINGLE-SOURCED here so the retrieval,
# headline-RMSE, and sensitivity scripts cannot drift apart (they previously held
# three different hardcoded grids -- the same duplication that hid the Q_b bug).
# NB (2026-07-06 audit): the two A15 linspaces both hit 3.8e-3 but differ in
# the last floating-point bit, so np.unique keeps BOTH (29 pts, one ~0-width
# gap). Verified inert: the near-twin sits 0.8 mW below the vertex bracket,
# so K_d* is unaffected; cost is one duplicate solve. Deduping would shrink
# the grid and trip the KD_GRIDS staleness guard against certified results,
# so leave as-is until the next full re-baseline (then round before unique).
KD_GRIDS = {
    "A15": np.unique(np.concatenate([
        np.linspace(1.0e-3, 15.0e-3, 16), np.linspace(3.6e-3, 6.0e-3, 13)])),
    "A17": np.unique(np.concatenate([
        np.linspace(3.0e-3, 25.0e-3, 18), np.linspace(6.0e-3, 8.6e-3, 14)])),
}

# --- Hayne (2017) conductivity-form bundle (the swept K_d is separate) -------
HAYNE = dict(K_S=K_SURFACE, H=H_PARAMETER, CHI=CHI_RADIATIVE, T_REF=T_REFERENCE)

# --- flux-anchored equilibrium solver (lunar.equilibrium) --------------------
EQ_Z_ANCHOR = 0.55      # anchor depth [m], below the rectification zone
# Inner spin-up lunations per outer iteration. Set by a convergence study
# (2026-06-30). The retrieved K_d* converges to a plateau in n_inner; convergence
# is judged on K_d* STABILITY (|dK_d*|<0.005 mW), not a fixed cycle count. With the
# Step A domain truncation (equilibrium.solve_periodic_equilibrium time-steps only
# the skin [0, z_anchor+0.15] and reconstructs the deep column) the truncated method
# reaches the SAME value as the old full-column solve, validated unbiased (A15 at
# n=128: 4.606 truncated vs 4.608 full). A17 plateaus by n~48-64 (7.17/7.16 at
# n=48/64); A15 has lower K -> lower diffusivity -> converges SLOWER (4.600/4.605/
# 4.606 at n=64/96/128), so the SLOWER site sets n_inner. 96 puts both on the
# plateau (~13 s/solve). OLD n_inner=12 (closure ~6%) biased K_d*(A17) HIGH ~0.4 mW;
# the OLD full-column Step A needed n~200 (and ~3-4x the cost) for the same answer.
# See the n_inner study and the project_ninner_underresolution memory.
EQ_N_INNER = 96         # inner spin-up lunations per outer iteration (converged, truncated Step A)
EQ_MAX_OUTER = 20       # outer-iteration cap
EQ_ANCHOR_TOL = 0.005   # convergence tolerance on the anchor temperature [K]

# --- per-site configuration (THE single definition) --------------------------
# Q_BASAL = site basal geothermal heat flux [W m^-2], from Langseth et al. (1976)
# revised values: A15 (Hadley Rille) 2.1 uW cm^-2 = 0.021 (regionally
# representative); A17 (Taurus-Littrow) 1.6 uW cm^-2 = 0.016 (borehole value;
# the regional topo-corrected estimate is 1.4 = 0.014). Nagihara et al. (2018)
# supplies the restored record + depth uncertainty, NOT the flux magnitude.
SITES = {
    "A15": dict(tag="A15", label="Apollo 15", lat=26.13, lon=3.63,
                albedo=0.131, emissivity=0.95, Q_BASAL=0.021,
                T_MEAN_EFF=250.0, MIN_DEPTH_CM=80, mission="a15"),
    "A17": dict(tag="A17", label="Apollo 17", lat=20.19, lon=30.77,
                albedo=0.137, emissivity=0.95, Q_BASAL=0.016,
                T_MEAN_EFF=255.0, MIN_DEPTH_CM=80, mission="a17"),
}

# (K_d sweep grids KD_GRIDS are defined once near the top, beside GRID.)

# --- bootstrap ---------------------------------------------------------------
DEPTH_SIGMA_CM = 2.5     # Nagihara (2018) sensor-placement uncertainty

# --- discrete 3-layer diagnostic model (this work) ---------------------------
TL_Z1, TL_Z2 = 0.02, 0.20             # layer boundaries [m]
TL_RHO_REF = 1800.0                   # Hayne (2017) nominal deep density
TL_RHO_SITE = {"A15": 2000.0, "A17": 1900.0}  # per-site RMSE-optimal deep rho
