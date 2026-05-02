"""Tests for pecks_model.py."""
import pytest
from packguard_physics.pecks_model import predict_humidity_failure
from packguard_physics.types import ReliabilityResult


def test_returns_reliability_result():
    r = predict_humidity_failure(85, 85, 3, 5)
    assert isinstance(r, ReliabilityResult)


def test_higher_rh_gives_shorter_ttf():
    low_rh  = predict_humidity_failure(50, 85, 3, 5)
    high_rh = predict_humidity_failure(95, 85, 3, 5)
    assert high_rh.predicted_lifetime < low_rh.predicted_lifetime


def test_higher_rh_gives_higher_pfail():
    low_rh  = predict_humidity_failure(30, 60, 1, 1)
    high_rh = predict_humidity_failure(90, 60, 1, 1)
    assert high_rh.probability_of_failure >= low_rh.probability_of_failure


def test_msl1_has_no_penalty():
    r = predict_humidity_failure(60, 25, 1, 20)
    assert r.probability_of_failure < 0.5  # MSL1 = unlimited, very long TTF


def test_msl6_high_stress():
    r = predict_humidity_failure(85, 85, 6, 5)
    # MSL6 is only 6h safe exposure; 5 years >> 6h → high P(fail)
    assert r.probability_of_failure > 0.5


def test_invalid_rh_raises():
    with pytest.raises(ValueError, match="relative_humidity_pct"):
        predict_humidity_failure(110, 85, 3)


def test_invalid_msl_raises():
    with pytest.raises(ValueError, match="msl_rating"):
        predict_humidity_failure(85, 85, 7)


def test_pfail_in_range():
    r = predict_humidity_failure(60, 40, 2, 3)
    assert 0.0 <= r.probability_of_failure <= 1.0


def test_units_are_hours():
    r = predict_humidity_failure(85, 85, 3)
    assert r.units == "hours"
