"""Tests for the optional bedrock layer (lunar.properties.with_bedrock).

The bedrock layer is a toggle for future deep-profile / ice-stability work.
These tests lock in two guarantees:

  1. It is OFF by default, so the published Apollo K_d retrieval is unchanged.
  2. When ON, it leaves shallow (sensor-depth) conductivity essentially
     unchanged but raises the deep conductivity toward the bedrock value.
"""
import numpy as np

from lunar.config import BEDROCK
from lunar.properties import conductivity_hayne, with_bedrock


def _base_k():
    """A Hayne conductivity model at the A15 retrieved K_d*."""
    def k(T, z):
        return conductivity_hayne(T, z, Kd=4.58e-3)
    return k


def test_bedrock_off_by_default():
    """The published configuration must keep bedrock disabled."""
    assert BEDROCK["enabled"] is False


def test_sensor_depth_temperature_unchanged():
    """The key guarantee: enabling bedrock shifts the steady temperature at
    the Heat-Flow sensor depths (<= 2.4 m) by < 0.02 K, so the K_d retrieval
    is unaffected. We integrate the steady mean-flux profile
    d<T>/dz = Q_b / K with and without the bedrock layer and compare."""
    Q_b = 0.021                                   # A15 basal flux [W m^-2]
    base = _base_k()
    wrapped = with_bedrock(base, z_bedrock=10.0, width=1.5, K_rock=2.0)
    z = np.linspace(0.3, 2.4, 3000)               # through the sensor range

    def integrate(k_func):
        T = np.empty_like(z)
        T[0] = 250.0
        for i in range(z.size - 1):
            K = float(np.asarray(k_func(np.array([T[i]]),
                                        np.array([z[i]])))[0])
            T[i + 1] = T[i] + Q_b / K * (z[i + 1] - z[i])
        return T

    T_no = integrate(base)
    T_bed = integrate(wrapped)
    assert np.max(np.abs(T_no - T_bed)) < 0.02


def test_deep_conductivity_approaches_bedrock():
    """Far below the transition the conductivity tends to K_rock."""
    base = _base_k()
    K_rock = 2.0
    wrapped = with_bedrock(base, z_bedrock=10.0, width=1.5, K_rock=K_rock)
    z = np.array([40.0])
    T = np.array([265.0])
    K_deep = float(wrapped(T, z)[0])
    assert K_deep > 1.9          # essentially bedrock
    assert abs(K_deep - K_rock) < 0.1


def test_transition_is_monotonic():
    """Conductivity increases monotonically with depth across the ramp."""
    base = _base_k()
    wrapped = with_bedrock(base, z_bedrock=10.0, width=1.5, K_rock=2.0)
    z = np.linspace(1.0, 30.0, 60)
    T = np.full_like(z, 260.0)
    K = np.asarray(wrapped(T, z))
    assert np.all(np.diff(K) >= -1e-12)
