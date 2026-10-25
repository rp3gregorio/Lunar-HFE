"""Run configuration and site parameters, defined once.

The per-site table (SITES), the depth grid, the Hayne-form parameters, the
equilibrium-solver settings, the K_d sweep grids and the parameters of the
3-layer diagnostic model. Cited physical constants live in
:mod:`lunar.constants`; this module composes them into run settings.

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
# Solver time step [s]. Each lunation is chained to the next through the final
# step t[-1] -> P; without it the phase slips by dt per lunation and the periodic
# state carries an O(dt) error. With that step and CN_PICARD_SWEEPS below, the
# periodic state moves by about -4 mK per halving of the step.
# certify_joint_numerics.py halves the step twice at the joint fit (SI Table S3;
# K_d* moves by <= 0.001 mW m^-1 K^-1 per halving). Re-run it if these change.
DT_STEP = 1800.0
# Midpoint-Picard corrector sweeps per Crank-Nicolson step (solver._step). Each
# sweep re-solves the step with K and c_p at 0.5*(T_prev + T_new) and re-anchors
# the surface Newton iteration at the implicit T_new[0]; 0 gives the frozen-
# property linearisation. Drift of the periodic state per halving of dt at
# 1800 s (A15, 6000 lunations): 1/2/4/8 sweeps -> -8.6/-4.2/-2.2/-2.0 mK, so two
# sweeps sit within ~2 mK of the fixed point at three tridiagonal solves per
# step. The C++ port (cpp/solver.cpp) uses the same value.
CN_PICARD_SWEEPS = 2

# --- depth grid (geometric) --------------------------------------------------
GRID = dict(z_max=5.0, dz0=0.002, growth=0.08)

# --- K_d sweep grids [W m^-1 K^-1] -------------------------------------------
# A wide coarse span, so the bootstrap percentiles stay inside the swept range,
# joined with a dense 0.2 mW band around the minimum, so the 3-point parabola
# vertex is grid-converged (a uniform 0.5 mW grid biased it high by ~0.04 mW).
# The two A15 linspaces both reach 3.8e-3 but differ in the last floating-point
# bit, so np.unique keeps both; the near-twin lies 0.8 mW below the vertex
# bracket and does not affect K_d*. It is kept so the grid matches the stored
# results.
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
# Inner spin-up lunations per outer iteration. Step A time-steps only the top
# z_anchor + 0.15 m and reconstructs the deep column (lunar.equilibrium). K_d*
# reaches a plateau in n_inner (judged by |dK_d*| < 0.005 mW m^-1 K^-1); A15,
# with the lower diffusivity, converges more slowly and sets the value. At the
# joint fit, 64 and 128 move K_d* by <= 0.0002 (certify_joint_numerics.py,
# SI Table S3); 96 is on the plateau at both sites, at ~13 s per solve.
EQ_N_INNER = 96         # inner spin-up lunations per outer iteration (converged, truncated Step A)
EQ_MAX_OUTER = 20       # outer-iteration cap
EQ_ANCHOR_TOL = 0.005   # convergence tolerance on the anchor temperature [K]

# --- per-site configuration -------------------------------------------------
# Q_BASAL: basal heat flow [W m^-2], the revised values of Langseth et al. (1976):
# 2.1 uW cm^-2 at A15 (mean of the two probes) and 1.6 uW cm^-2 at A17 (probe 1;
# 1.4 after their topographic correction). Nagihara et al. (2018) restored the
# record; the fluxes are Langseth's.
# albedo: effective constant Bond albedo, fitted jointly with K_d to the sensor
# temperatures, the measured mean surface temperature and the annual-wave
# diffusivity of Langseth et al. (1976) by compute_joint_albedo_fit.py
# (results/joint_albedo_fit.json: 0.13626 / 0.13748; letter Section 3.1).
SITES = {
    "A15": dict(tag="A15", label="Apollo 15", lat=26.13, lon=3.63,
                albedo=0.1363, emissivity=0.95, Q_BASAL=0.021,
                T_MEAN_EFF=250.0, MIN_DEPTH_CM=80, mission="a15"),
    "A17": dict(tag="A17", label="Apollo 17", lat=20.19, lon=30.77,
                albedo=0.1375, emissivity=0.95, Q_BASAL=0.016,
                T_MEAN_EFF=255.0, MIN_DEPTH_CM=80, mission="a17"),
}

# --- bootstrap ---------------------------------------------------------------
DEPTH_SIGMA_CM = 2.5     # adopted sensor-placement envelope, set at the probe-rod diameter (Nagihara et al. 2018: "2.5-cm diameter" rods); no per-sensor depth error is published

# --- discrete 3-layer diagnostic model (this work) ---------------------------
TL_Z1, TL_Z2 = 0.02, 0.20             # layer boundaries [m]
TL_RHO_REF = 1800.0                   # Hayne (2017) nominal deep density
TL_RHO_SITE = {"A15": 2000.0, "A17": 1900.0}  # per-site RMSE-optimal deep rho
