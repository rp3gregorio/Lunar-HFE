"""Physical constants and default regolith parameters.

All values are SI. Every constant has a source citation in its docstring.
Do not add numbers here without a citation — the project scientific-integrity
rule is that unsourced values are forbidden.
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Universal physical constants
# ---------------------------------------------------------------------------

#: Stefan-Boltzmann constant [W m^-2 K^-4] — CODATA 2018.
SIGMA_SB: float = 5.670374419e-8

#: Solar constant at 1 AU [W m^-2] — Kopp & Lean (2011), GRL 38, L01706.
SOLAR_CONSTANT: float = 1361.0

#: Mean lunar distance from Sun [AU] (treated as 1 AU for the thermal problem).
LUNAR_DISTANCE_AU: float = 1.0

#: Sidereal lunar day / synodic lunation [s] — 29.530589 days.
LUNATION_SECONDS: float = 29.530589 * 86400.0

#: Ice density (crystalline Ih, 100 K) [kg m^-3] — Feistel & Wagner (2006).
RHO_ICE: float = 917.0


# ---------------------------------------------------------------------------
# Regolith thermal parameters (Hayne et al. 2017)
# ---------------------------------------------------------------------------
# Hayne, P. O. et al. (2017). "Global regolith thermophysical properties of
# the Moon from the Diviner Lunar Radiometer Experiment." JGR: Planets 122,
# 2371-2400. doi:10.1002/2017JE005387

#: Surface bulk density [kg m^-3] — Hayne et al. (2017) Table 2.
RHO_SURFACE: float = 1100.0

#: Deep bulk density [kg m^-3] — Hayne et al. (2017) Table 2.
RHO_DEEP: float = 1800.0

#: H-parameter (density/conductivity scale height) [m] — Hayne et al. (2017).
H_PARAMETER: float = 0.06

#: Surface contact conductivity [W m^-1 K^-1] — Hayne et al. (2017) Table 2.
K_SURFACE: float = 7.4e-4

#: Deep contact conductivity [W m^-1 K^-1] — Hayne et al. (2017) Table 2.
#: NOTE: earlier versions of heat1d had an incorrect value here. The correct
#: published value is 3.4e-3.
K_DEEP: float = 3.4e-3

#: Radiative conductivity coefficient chi [dimensionless] — Hayne et al. (2017).
CHI_RADIATIVE: float = 2.7

#: Reference temperature for the radiative term [K] — Hayne et al. (2017).
T_REFERENCE: float = 350.0


# ---------------------------------------------------------------------------
# Boundary conditions
# ---------------------------------------------------------------------------

#: Default Bond albedo (may be tuned per pixel from Diviner).
ALBEDO_DEFAULT: float = 0.12

#: Default thermal emissivity.
EMISSIVITY_DEFAULT: float = 0.95

#: Equatorial geothermal heat flux [W m^-2] — Apollo 15/17 HFE average,
#: Langseth et al. (1976), Nagihara et al. (2018).
Q_B_EQUATORIAL: float = 0.018

#: South-polar geothermal heat flux [W m^-2] — Chang'E-2 MRM inversions,
#: Feng et al. (2020); actual range 0.005-0.012.
Q_B_SOUTH_POLAR: float = 0.012


# ---------------------------------------------------------------------------
# Grid defaults (geometric)
# ---------------------------------------------------------------------------

#: Default maximum depth for the subsurface grid [m].
Z_MAX_DEFAULT: float = 3.0

#: Default thickness of the top layer [m] (2 mm).
DZ0_DEFAULT: float = 0.002

#: Default geometric-growth factor (new_dz = old_dz * (1 + GROWTH)).
GROWTH_DEFAULT: float = 0.15


# ---------------------------------------------------------------------------
# Specific heat polynomial (Hayne 2017, Appendix A / Ledlow 1992 / Hemingway 1981)
# ---------------------------------------------------------------------------
# Source verified against heat1d/python/heat1d/properties.py::updateC equivalent
# (also mirrored verbatim in lunar1Dheat/1DFunctions/updateC.m from
# Martinez & Siegler 2021). The 4th-order polynomial is the standard lunar
# regolith c_p model above ~10 K.
#
# c_p(T) = C0 + C1*T + C2*T^2 + C3*T^3 + C4*T^4  [J kg^-1 K^-1]
#
# Valid for T > ~10 K. Yields negative values for T < ~1.3 K; do NOT use
# below the validity limit.
CP_HAYNE_C0: float = -3.6125
CP_HAYNE_C1: float = 2.7431
CP_HAYNE_C2: float = 2.3616e-3
CP_HAYNE_C3: float = -1.2340e-5
CP_HAYNE_C4: float = 8.9093e-9

# Biele et al. (2022) Int. J. Thermophys. 43:144, Eq. 24.
# Rational function in log-log space that has the correct Debye T^3 limit
# and is positive for all T > 0. Fits Apollo lunar sample data to < 3% for
# 90-1000 K. Coefficient values taken verbatim from heat1d/properties.py.
#
# ln(c_p) = (p1 x^3 + p2 x^2 + p3 x + p4) / (x^2 + q1 x + q2),   x = ln(T)
CP_BIELE_P1: float = 3.0
CP_BIELE_P2: float = -54.45
CP_BIELE_P3: float = 306.8
CP_BIELE_P4: float = -376.6
CP_BIELE_Q1: float = -16.81
CP_BIELE_Q2: float = 87.32


# ---------------------------------------------------------------------------
# Martinez & Siegler (2021) "updated" thermal conductivity — density form.
# ---------------------------------------------------------------------------
# Source verified against lunar1Dheat/1DFunctions/updateRK.m
# (github.com/angelicam01/lunar1Dheat), the accompanying code release for
# Martinez & Siegler (2021), "A Global Thermal Conductivity Model for Lunar
# Regolith at Low Temperatures". The functional form is:
#
#   k_am(T) = A + B*T^-4 + C*T^-3 + D*T^-2 + E*T^-1 + F*T + G*T^2 + H*T^3 + I*T^4
#   K(T, rho) = (A1 * rho + A2) * k_am(T) + (B1 * rho + B2) * T^3
#
# where k_am is the Woods-Robinson et al. (2019) amorphous solid polynomial.
# The first term is the temperature- and density-dependent contact ("phonon")
# conductivity; the second term is the radiative contribution.
#
# Unlike the Hayne (2017) H-parameter form, this model takes bulk density
# directly rather than through an exponential depth profile. It is the
# Martinez-Siegler recommended form for PSR temperatures.

# Woods-Robinson et al. (2019) amorphous-solid conductivity polynomial
# coefficients (for k_am(T) in W m^-1 K^-1).
MS_KAM_A: float = -2.03297e-1
MS_KAM_B: float = -11.472
MS_KAM_C: float = 22.5793
MS_KAM_D: float = -14.3084
MS_KAM_E: float = 3.41742
MS_KAM_F: float = 0.01101
MS_KAM_G: float = -2.80491e-5
MS_KAM_H: float = 3.35837e-8
MS_KAM_I: float = -1.40021e-11

# Martinez & Siegler (2021) density-scaling coefficients for the contact
# and radiative parts of K(T, rho). Values from the LPSC 2022 abstract
# (#2754) Eq. 3, which is the published form.
#
# Note on B1: the LPSC abstract gives 2.0022e-13. The companion code
# release `1DFunctions/updateRK.m` has 2.022e-13 (a missing zero — the
# accompanying derivk.m uses 0.944*2.121e-13 = 2.002e-13, consistent with
# the published value). We use the published value here. See
# docs/martinez_replication_plan.md section 2.2.
MS_A1: float = 5.0821e-6
MS_A2: float = -0.0051
MS_B1: float = 2.0022e-13
MS_B2: float = -1.953e-10
