"""Tests for griffith_fracture.py."""
import pytest
from packguard_physics.griffith_fracture import assess_crack_growth
from packguard_physics.types import ReliabilityResult


def test_returns_reliability_result():
    r = assess_crack_growth(0.5, 50)
    assert isinstance(r, ReliabilityResult)


def test_crack_above_critical_gives_pfail_1():
    # a_c for K_Ic=0.83, σ=5 MPa: a_c = (1/π)*(0.83/5)² = (1/π)*0.02757 = 0.00878 m = 8.78 mm
    r = assess_crack_growth(crack_length_mm=10.0, applied_stress_MPa=5.0)
    assert r.probability_of_failure == 1.0


def test_small_crack_low_pfail():
    # Very small crack at moderate stress → well below critical → low P(fail)
    r = assess_crack_growth(crack_length_mm=0.01, applied_stress_MPa=50.0)
    assert r.probability_of_failure < 0.2


def test_zero_crack_zero_pfail():
    r = assess_crack_growth(0.0, 50.0)
    assert r.probability_of_failure == 0.0


def test_higher_stress_lower_critical_length():
    low_stress  = assess_crack_growth(1.0, 10.0)
    high_stress = assess_crack_growth(1.0, 100.0)
    assert high_stress.predicted_lifetime < low_stress.predicted_lifetime


def test_negative_crack_raises():
    with pytest.raises(ValueError):
        assess_crack_growth(-1.0, 50.0)


def test_zero_stress_raises():
    with pytest.raises(ValueError):
        assess_crack_growth(1.0, 0.0)


def test_silicon_default_kic():
    r = assess_crack_growth(0.1, 50)
    # a_c = (1/π)*(0.83/50)^2 m = (1/π)*(0.000277) = 8.82e-5 m = 0.0882 mm
    assert r.predicted_lifetime == pytest.approx(0.0882, rel=1e-2)


def test_units_are_mm():
    r = assess_crack_growth(0.5, 50)
    assert r.units == "mm"
