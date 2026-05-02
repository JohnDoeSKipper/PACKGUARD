"""Tests for blacks_equation.py."""
import pytest
from packguard_physics.blacks_equation import predict_electromigration
from packguard_physics.types import ReliabilityResult


def test_returns_reliability_result():
    r = predict_electromigration(1e6, 100)
    assert isinstance(r, ReliabilityResult)


def test_higher_j_gives_higher_pfail():
    # Use service_life=0.05 yr (~438 h) so both are < 1.0 and distinguishable.
    # J=1e5: MTTF >> service → low P(fail); J=1e6: MTTF ≈ service → higher P(fail).
    low  = predict_electromigration(1e5, 100, "Cu", 0.05)
    high = predict_electromigration(1e6, 100, "Cu", 0.05)
    assert high.probability_of_failure > low.probability_of_failure


def test_higher_temp_gives_lower_mttf():
    # Higher T → smaller exp(Ea/kT) → smaller MTTF for same J
    # Wait — higher T actually means smaller exponent argument → lower MTTF
    cool = predict_electromigration(1e6, 50, "Cu", 7)
    hot  = predict_electromigration(1e6, 150, "Cu", 7)
    assert hot.predicted_lifetime < cool.predicted_lifetime


def test_cu_vs_al():
    cu = predict_electromigration(1e6, 100, "Cu", 10)
    al = predict_electromigration(1e6, 100, "Al", 10)
    # Cu has higher Ea (0.9 vs 0.6) → longer MTTF at same J and T
    assert cu.predicted_lifetime > al.predicted_lifetime


def test_invalid_material_raises():
    with pytest.raises(ValueError, match="Unknown material"):
        predict_electromigration(1e6, 100, "Au")


def test_negative_j_raises():
    with pytest.raises(ValueError):
        predict_electromigration(-1e6, 100)


def test_pfail_in_range():
    r = predict_electromigration(1e6, 125, "Al", 5)
    assert 0.0 <= r.probability_of_failure <= 1.0


def test_ci_bounds_valid():
    r = predict_electromigration(1e6, 100)
    lo, hi = r.confidence_interval
    assert 0.0 <= lo <= hi <= 1.0


def test_units_are_hours():
    r = predict_electromigration(1e6, 100)
    assert r.units == "hours"
