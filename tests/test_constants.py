"""Sanity checks for physical constants.

These are simple guards — if someone changes a value, a test should
fail loudly so the change is explicit in a PR rather than silent.
"""

from lunar import constants as C


def test_stefan_boltzmann():
    # CODATA 2018: sigma = 5.670374419e-8
    assert abs(C.SIGMA_SB - 5.670374419e-8) < 1e-18


def test_hayne_regolith_defaults():
    # Hayne et al. (2017), Table 2. The K_d value 3.4e-3 was historically
    # wrong in the project — guard against regression.
    assert C.RHO_SURFACE == 1100.0
    assert C.RHO_DEEP == 1800.0
    assert C.H_PARAMETER == 0.06
    assert C.K_SURFACE == 7.4e-4
    assert C.K_DEEP == 3.4e-3
    assert C.CHI_RADIATIVE == 2.7


def test_geothermal_defaults_nonzero():
    # The zero-flux bottom BC is a known bug — both defaults must be > 0.
    assert C.Q_B_EQUATORIAL > 0.0
    assert C.Q_B_SOUTH_POLAR > 0.0
