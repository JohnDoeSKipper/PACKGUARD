"""Tests for arrhenius_imc.py."""
import pytest
from packguard_physics.arrhenius_imc import predict_imc_thickness
from packguard_physics.types import ReliabilityResult


def test_returns_reliability_result():
    r = predict_imc_thickness([150], [100], "Au-Al")
    assert isinstance(r, ReliabilityResult)


def test_higher_temp_gives_thicker_imc():
    cool = predict_imc_thickness([100], [1000], "Au-Al")
    hot  = predict_imc_thickness([250], [1000], "Au-Al")
    assert hot.predicted_lifetime > cool.predicted_lifetime


def test_longer_time_gives_thicker_imc():
    short = predict_imc_thickness([150], [10],   "Au-Al")
    long_ = predict_imc_thickness([150], [1000], "Au-Al")
    assert long_.predicted_lifetime > short.predicted_lifetime


def test_all_metallurgies_accepted():
    for met in ["Au-Al", "Cu-Al", "Au-Au"]:
        r = predict_imc_thickness([175], [200], met)
        assert r.predicted_lifetime > 0


def test_mismatched_lengths_raise():
    with pytest.raises(ValueError, match="equal length"):
        predict_imc_thickness([150, 200], [100])


def test_empty_input_raises():
    with pytest.raises(ValueError, match="At least one"):
        predict_imc_thickness([], [])


def test_unknown_metallurgy_raises():
    with pytest.raises(ValueError, match="Unknown metallurgy"):
        predict_imc_thickness([150], [100], "Au-Cu")


def test_pfail_approaches_1_at_critical():
    # Very high temp + long time → thick IMC → P(fail) near 1
    r = predict_imc_thickness([350], [50000], "Au-Al")
    assert r.probability_of_failure > 0.9


def test_units_are_micrometers():
    r = predict_imc_thickness([150], [100])
    assert r.units == "micrometers"
