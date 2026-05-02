"""Tests for warpage.py."""
import pytest
from packguard_physics.warpage import predict_warpage
from packguard_physics.types import ReliabilityResult


def test_returns_reliability_result():
    r = predict_warpage(2.6, 18, 25, 260)
    assert isinstance(r, ReliabilityResult)


def test_larger_cte_mismatch_more_warpage():
    small_mismatch = predict_warpage(2.6, 5,  25, 260)
    large_mismatch = predict_warpage(2.6, 18, 25, 260)
    assert large_mismatch.predicted_lifetime > small_mismatch.predicted_lifetime


def test_larger_package_more_warpage():
    small = predict_warpage(2.6, 18, 10, 260)
    large = predict_warpage(2.6, 18, 40, 260)
    assert large.predicted_lifetime > small.predicted_lifetime


def test_matched_cte_zero_warpage():
    r = predict_warpage(2.6, 2.6, 25, 260)
    assert r.predicted_lifetime == pytest.approx(0.0, abs=1e-9)
    assert r.probability_of_failure == pytest.approx(0.0, abs=0.01)


def test_exceeds_jedec_spec():
    # Very large package + big CTE mismatch → warpage >> 0.2 mm → high P(fail)
    r = predict_warpage(2.6, 20, 50, 260)
    assert r.probability_of_failure > 0.9


def test_zero_package_size_raises():
    with pytest.raises(ValueError):
        predict_warpage(2.6, 18, 0, 260)


def test_units_are_mm():
    r = predict_warpage(2.6, 18, 25, 260)
    assert r.units == "mm"


def test_pfail_in_range():
    r = predict_warpage(2.6, 18, 25, 260)
    assert 0.0 <= r.probability_of_failure <= 1.0
