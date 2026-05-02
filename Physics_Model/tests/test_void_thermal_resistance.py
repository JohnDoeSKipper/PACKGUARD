"""Tests for void_thermal_resistance.py."""
import pytest
from packguard_physics.void_thermal_resistance import assess_void_impact
from packguard_physics.types import ReliabilityResult


def test_returns_reliability_result():
    r = assess_void_impact(0.3)
    assert isinstance(r, ReliabilityResult)


def test_higher_void_fraction_higher_pfail():
    low  = assess_void_impact(0.05)
    high = assess_void_impact(0.60)
    assert high.probability_of_failure >= low.probability_of_failure


def test_zero_voids_low_temp():
    r = assess_void_impact(0.0, power_dissipation_W=1.0)
    # T_j = 25 + 1*1.0 = 26°C, well below 125°C → very low P(fail)
    assert r.probability_of_failure < 0.01


def test_clustered_worse_than_dispersed():
    dispersed  = assess_void_impact(0.4, "dispersed")
    clustered  = assess_void_impact(0.4, "clustered")
    assert clustered.probability_of_failure >= dispersed.probability_of_failure


def test_invalid_distribution_raises():
    with pytest.raises(ValueError, match="void_distribution"):
        assess_void_impact(0.3, "random")


def test_void_fraction_out_of_range_raises():
    with pytest.raises(ValueError):
        assess_void_impact(1.0)


def test_pfail_in_range():
    r = assess_void_impact(0.5)
    assert 0.0 <= r.probability_of_failure <= 1.0


def test_units_are_celsius():
    r = assess_void_impact(0.2)
    assert r.units == "celsius"


def test_predicted_lifetime_is_junction_temp():
    r = assess_void_impact(0.0, nominal_thermal_resistance_K_per_W=2.0,
                           ambient_temp_C=25.0, power_dissipation_W=10.0)
    # R_eff = 2.0, T_j = 25 + 10*2.0 = 45°C
    assert r.predicted_lifetime == pytest.approx(45.0, abs=0.1)
