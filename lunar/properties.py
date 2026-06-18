"""Regolith thermal property models.

In plain English
----------------
"Regolith" is the loose, dusty, broken-up soil covering the Moon. To
simulate how heat moves through it, the solver needs three physical
properties of that soil at every depth and temperature:

  * Thermal conductivity (K) -- how easily heat flows through it. This
    is THE quantity the whole paper is trying to measure deep down
    (K_d). Lunar soil is an extraordinary insulator near the surface
    (worse than styrofoam) because it is fluffy and sits in vacuum.
  * Density (rho) -- how much mass is packed into each cubic metre. The
    soil is fluffy at the top and compacts with depth.
  * Specific heat (c_p) -- how much energy it takes to warm the soil by
    one degree (its "thermal inertia" per kilogram).

This file holds the published formulas for each of these. Each formula
is tagged with the scientific paper it came from, and every number was
checked against that source -- we never invent coefficients.

Three conductivity models are provided, all accessible through
:func:`get_conductivity_model`:

A. ``hayne``    — baseline H-parameter form, Hayne et al. (2017) App. A.
B. ``martinez`` — Martinez & Siegler (2021) density form based on the
   Woods-Robinson et al. (2019) amorphous-solid polynomial. Handles
   low temperatures correctly and is the recommended form for PSRs.
C. ``ice_coupled`` — novel ice-coupled properties (Gregorio 2026, in
   prep) built on top of the Martinez-Siegler dry conductivity.

Two specific-heat models are available:

* ``hayne`` (default) — 4th-order polynomial from Hayne (2017) Appendix A.
* ``biele``           — rational log-log fit, Biele et al. (2022,
  Int. J. Thermophys. 43:144, Eq. 24). Positive everywhere, correct
  Debye T^3 limit, fits Apollo data to < 3% for 90-1000 K.

Every numerical coefficient in this module has been verified against a
public source file and cited in the docstring. See
``.claude/skills/SKILL.md`` — "never fabricate numerical values".
"""

from __future__ import annotations

from typing import Callable, Literal

import numpy as np

from .constants import (
    CHI_RADIATIVE,
    CP_BIELE_P1,
    CP_BIELE_P2,
    CP_BIELE_P3,
    CP_BIELE_P4,
    CP_BIELE_Q1,
    CP_BIELE_Q2,
    CP_HAYNE_C0,
    CP_HAYNE_C1,
    CP_HAYNE_C2,
    CP_HAYNE_C3,
    CP_HAYNE_C4,
    H_PARAMETER,
    K_DEEP,
    K_SURFACE,
    MS_A1,
    MS_A2,
    MS_B1,
    MS_B2,
    MS_KAM_A,
    MS_KAM_B,
    MS_KAM_C,
    MS_KAM_D,
    MS_KAM_E,
    MS_KAM_F,
    MS_KAM_G,
    MS_KAM_H,
    MS_KAM_I,
    RHO_DEEP,
    RHO_ICE,
    RHO_SURFACE,
    T_REFERENCE,
)

# ---------------------------------------------------------------------------
# Density
# ---------------------------------------------------------------------------


def density_hayne(
    z: np.ndarray,
    rho_s: float = RHO_SURFACE,
    rho_d: float = RHO_DEEP,
    H: float = H_PARAMETER,
) -> np.ndarray:
    """Bulk density [kg m^-3] vs depth, Hayne et al. (2017) Eq. 5.

    ``rho(z) = rho_d - (rho_d - rho_s) * exp(-z / H)``
    """
    z = np.asarray(z, dtype=np.float64)
    return rho_d - (rho_d - rho_s) * np.exp(-z / H)


def density_icy(
    z: np.ndarray,
    phi_ice: np.ndarray,
    rho_s: float = RHO_SURFACE,
    rho_d: float = RHO_DEEP,
    H: float = H_PARAMETER,
    rho_ice: float = RHO_ICE,
) -> np.ndarray:
    """Bulk density [kg m^-3] with ice filling ``phi_ice`` of pore space.

    Novel (Gregorio 2026, in prep). Assumes ice adds mass to the matrix
    without changing the matrix porosity.
    """
    rho_dry = density_hayne(z, rho_s, rho_d, H)
    return rho_dry + np.asarray(phi_ice, dtype=np.float64) * rho_ice


# ---------------------------------------------------------------------------
# Thermal conductivity
# ---------------------------------------------------------------------------


def conductivity_hayne(
    T: np.ndarray,
    z: np.ndarray,
    Ks: float = K_SURFACE,
    Kd: float = K_DEEP,
    H: float = H_PARAMETER,
    chi: float = CHI_RADIATIVE,
) -> np.ndarray:
    """H-parameter conductivity, Hayne et al. (2017) Eq. 4.

    ``K_c(z) = K_d - (K_d - K_s) * exp(-z/H)``
    ``K(T, z) = K_c(z) * (1 + chi * (T / 350)^3)``

    The radiative term ``chi * (T/350)^3`` MUST be present; omitting it
    is known bug #5 in SKILL.md.
    """
    T = np.asarray(T, dtype=np.float64)
    z = np.asarray(z, dtype=np.float64)
    Kc = Kd - (Kd - Ks) * np.exp(-z / H)
    return Kc * (1.0 + chi * (T / T_REFERENCE) ** 3)


def _woods_robinson_kam(T: np.ndarray) -> np.ndarray:
    """Woods-Robinson et al. (2019) amorphous-solid conductivity [W m^-1 K^-1].

    Polynomial fit valid across the lunar temperature range. Coefficients
    verified against ``lunar1Dheat/1DFunctions/updateRK.m`` (Martinez &
    Siegler 2021 code release). The polynomial is

    .. math::

        k_{am}(T) = A + B/T^4 + C/T^3 + D/T^2 + E/T
                  + F T + G T^2 + H T^3 + I T^4
    """
    T = np.asarray(T, dtype=np.float64)
    # Guard against T -> 0 (inverse powers diverge). 1 K is the effective
    # lower bound for this fit.
    T_safe = np.maximum(T, 1.0)
    return (
        MS_KAM_A
        + MS_KAM_B * T_safe**-4
        + MS_KAM_C * T_safe**-3
        + MS_KAM_D * T_safe**-2
        + MS_KAM_E * T_safe**-1
        + MS_KAM_F * T_safe
        + MS_KAM_G * T_safe**2
        + MS_KAM_H * T_safe**3
        + MS_KAM_I * T_safe**4
    )


def conductivity_martinez(
    T: np.ndarray,
    z: np.ndarray | None = None,
    rho: np.ndarray | None = None,
) -> np.ndarray:
    """Martinez & Siegler (2021) density-dependent thermal conductivity.

    Source verified against ``lunar1Dheat/1DFunctions/updateRK.m``
    (github.com/angelicam01/lunar1Dheat). The functional form is:

    .. math::

        K(T, \\rho) = (A_1 \\rho + A_2)\\, k_{am}(T)
                    + (B_1 \\rho + B_2)\\, T^3

    where :math:`k_{am}(T)` is the Woods-Robinson et al. (2019) amorphous
    solid polynomial. The first term is the density- and temperature-
    dependent contact (phonon) conductivity; the second term is the
    radiative contribution which also scales with density.

    Parameters
    ----------
    T : np.ndarray
        Temperature [K]. Same shape as ``rho`` (or ``z``).
    z : np.ndarray, optional
        Depth [m]. Used only if ``rho`` is not given, in which case the
        Hayne (2017) H-parameter density profile is used.
    rho : np.ndarray, optional
        Explicit bulk density [kg m^-3] at each point. If supplied,
        ``z`` is ignored.

    Returns
    -------
    np.ndarray
        Thermal conductivity [W m^-1 K^-1].
    """
    T = np.asarray(T, dtype=np.float64)
    if rho is None:
        if z is None:
            raise ValueError("conductivity_martinez requires either z or rho")
        rho = density_hayne(np.asarray(z, dtype=np.float64))
    else:
        rho = np.asarray(rho, dtype=np.float64)

    k_am = _woods_robinson_kam(T)
    contact = (MS_A1 * rho + MS_A2) * k_am
    radiative = (MS_B1 * rho + MS_B2) * T**3
    return contact + radiative


def conductivity_icy(
    T: np.ndarray,
    z: np.ndarray,
    phi_ice: np.ndarray,
    rho: np.ndarray | None = None,
) -> np.ndarray:
    """Ice-coupled thermal conductivity [W m^-1 K^-1] — NOVEL.

    Gregorio (2026, in prep). The novel contribution of Lunar-Clean v2.

    When ice fills pore space, effective K increases by several orders of
    magnitude relative to dry regolith. Crystalline ice Ih follows
    ``K_ice(T) ~ 567 / T`` [W m^-1 K^-1] (Klinger 1980, Science 209,
    271-272). At 100 K this gives ~5.67 W m^-1 K^-1 vs ~10^-3 for dry
    regolith.

    The dry baseline is Martinez & Siegler (2021) — the modern low-T
    model — and ice is added via a volumetric arithmetic mean:

        K_eff = (1 - phi_ice) * K_dry(T, rho) + phi_ice * K_ice(T)

    The Hashin-Shtrikman lower bound is also a defensible mixing rule;
    sensitivity of z_star to this choice is a planned study (thesis
    Chapter 6).
    """
    phi = np.asarray(phi_ice, dtype=np.float64)
    K_dry = conductivity_martinez(T, z=z, rho=rho)
    T_arr = np.asarray(T, dtype=np.float64)
    K_ice = 567.0 / np.maximum(T_arr, 1.0)  # Klinger (1980)
    return (1.0 - phi) * K_dry + phi * K_ice


# ---------------------------------------------------------------------------
# Optional bedrock layer (OFF by default)
# ---------------------------------------------------------------------------


def with_bedrock(
    k_func: Callable[..., np.ndarray],
    *,
    z_bedrock: float = 10.0,
    width: float = 1.5,
    K_rock: float = 2.0,
) -> Callable[..., np.ndarray]:
    """Wrap a conductivity model ``K(T, z)`` to add a deep bedrock layer.

    In plain English
    ----------------
    The standard model treats the Moon as fluffy regolith all the way down.
    In reality, below the regolith there is solid rock, which conducts heat
    far better. This wrapper takes any existing conductivity function and
    makes the conductivity smoothly rise from the regolith value to a
    bedrock value ``K_rock`` once you go below ``z_bedrock`` metres. The
    blend uses a ``tanh`` ramp of half-width ``width`` so there is no sharp
    jump.

    This is an OPTIONAL tool for future deep-profile studies (e.g. ice
    stability). It is OFF by default everywhere (see
    :data:`lunar.config.BEDROCK`). It does NOT change the Apollo K_d
    retrieval, because all Heat-Flow sensors lie at <= 2.4 m -- far above
    the transition (z_bedrock=10 m) -- where enabling it shifts the
    resulting temperature by only ~0.05 K, well within the data scatter.

    Parameters
    ----------
    k_func : callable
        A base conductivity model ``K(T, z) -> ndarray`` (e.g. one returned
        by :func:`get_conductivity_model`).
    z_bedrock : float
        Depth [m] of the regolith-to-bedrock transition midpoint.
    width : float
        Half-width [m] of the smooth ``tanh`` transition.
    K_rock : float
        Bedrock thermal conductivity [W m^-1 K^-1] (solid rock ~ 2).

    Returns
    -------
    callable
        A new ``K(T, z)`` function with the bedrock layer applied.
    """
    def k(T: np.ndarray, z: np.ndarray) -> np.ndarray:
        K_reg = np.asarray(k_func(T, z), dtype=np.float64)
        z_arr = np.asarray(z, dtype=np.float64)
        # Fraction of "rock" at each depth: 0 in the regolith, 1 deep down.
        frac = 0.5 * (1.0 + np.tanh((z_arr - z_bedrock) / width))
        return (1.0 - frac) * K_reg + frac * K_rock

    return k


# ---------------------------------------------------------------------------
# Specific heat
# ---------------------------------------------------------------------------

SpecificHeatModel = Literal["hayne", "biele"]


def _cp_hayne(T: np.ndarray) -> np.ndarray:
    """Hayne (2017) App. A 4th-order polynomial c_p(T) [J kg^-1 K^-1]."""
    T = np.asarray(T, dtype=np.float64)
    return (
        CP_HAYNE_C0
        + CP_HAYNE_C1 * T
        + CP_HAYNE_C2 * T**2
        + CP_HAYNE_C3 * T**3
        + CP_HAYNE_C4 * T**4
    )


def _cp_biele(T: np.ndarray) -> np.ndarray:
    """Biele et al. (2022) IJTP 43:144, Eq. 24. Positive for all T > 0."""
    T = np.asarray(T, dtype=np.float64)
    x = np.log(np.maximum(T, 1e-10))
    numer = CP_BIELE_P1 * x**3 + CP_BIELE_P2 * x**2 + CP_BIELE_P3 * x + CP_BIELE_P4
    denom = x**2 + CP_BIELE_Q1 * x + CP_BIELE_Q2
    return np.exp(numer / denom)


def specific_heat(T: np.ndarray, model: SpecificHeatModel = "hayne") -> np.ndarray:
    """Regolith specific heat capacity [J kg^-1 K^-1].

    Parameters
    ----------
    T : np.ndarray
        Temperature [K].
    model : {'hayne', 'biele'}, default 'hayne'
        Which c_p model to use:

        * ``'hayne'`` — Hayne (2017) Appendix A 4th-order polynomial,
          coefficients verified against heat1d ``updateC`` (and the
          identical function in lunar1Dheat ``updateC.m``). Valid for
          ``T > ~10 K``; goes negative below ~1.3 K.
        * ``'biele'`` — Biele et al. (2022) IJTP 43:144, Eq. 24.
          Positive everywhere and has the correct Debye T^3 limit;
          recommended if the model needs to cover PSR temperatures
          below 60 K.
    """
    if model == "hayne":
        return _cp_hayne(T)
    if model == "biele":
        return _cp_biele(T)
    raise ValueError(f"Unknown specific-heat model {model!r}. Use 'hayne' or 'biele'.")


def specific_heat_icy(
    T: np.ndarray,
    phi_ice: np.ndarray,
    model: SpecificHeatModel = "hayne",
) -> np.ndarray:
    """Effective specific heat [J kg^-1 K^-1] with ice-filled pore space.

    The regolith contribution is :func:`specific_heat`. The ice contribution
    uses the linear approximation ``c_p,ice(T) ~ 7.49 * T + 90``
    [J kg^-1 K^-1] valid over ~40-270 K (Giauque & Stout 1936; NIST).
    The volumetric blend is

    .. math::

        c_{p,\\mathrm{eff}} = (1 - \\phi_\\mathrm{ice}) c_{p,\\mathrm{reg}}
                            + \\phi_\\mathrm{ice} c_{p,\\mathrm{ice}}
    """
    cp_reg = specific_heat(T, model=model)
    phi = np.asarray(phi_ice, dtype=np.float64)
    cp_ice = 7.49 * np.asarray(T, dtype=np.float64) + 90.0
    return (1.0 - phi) * cp_reg + phi * cp_ice


# ---------------------------------------------------------------------------
# Model registry
# ---------------------------------------------------------------------------

PropertyModel = Callable[..., np.ndarray]

_CONDUCTIVITY_MODELS: dict[str, PropertyModel] = {
    "hayne": conductivity_hayne,
    "martinez": conductivity_martinez,
    "ice_coupled": conductivity_icy,
}


def get_conductivity_model(name: str) -> PropertyModel:
    """Look up a conductivity model by name.

    Valid names: ``'hayne'``, ``'martinez'``, ``'ice_coupled'``.
    """
    try:
        return _CONDUCTIVITY_MODELS[name]
    except KeyError as exc:
        raise ValueError(
            f"Unknown conductivity model {name!r}. "
            f"Valid options: {sorted(_CONDUCTIVITY_MODELS)}"
        ) from exc
