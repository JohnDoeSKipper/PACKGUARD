"""Tests for wire_sweep.py."""
import pytest
from packguard_physics.wire_sweep import predict_wire_sweep
from packguard_physics.types import ReliabilityResult


def test_returns_reliability_result():
    r = predict_wire_sweep(2.0, 25, 10.0, 0.05)
    assert isinstance(r, ReliabilityResult)


def test_longer_wire_more_deflection():
    short = predict_wire_sweep(1.0, 25, 10.0, 0.05)
    long_ = predict_wire_sweep(4.0, 25, 10.0, 0.05)
    assert long_.predicted_lifetime > short.predicted_lifetime


def test_higher_velocity_more_deflection():
    slow = predict_wire_sweep(2.0, 25, 10.0, 0.01)
    fast = predict_wire_sweep(2.0, 25, 10.0, 0.10)
    assert fast.predicted_lifetime > slow.predicted_lifetime


def test_thicker_wire_less_deflection():
    thin  = predict_wire_sweep(2.0, 18, 10.0, 0.05)
    thick = predict_wire_sweep(2.0, 50, 10.0, 0.05)
    assert thick.predicted_lifetime < thin.predicted_lifetime


def test_copper_less_sweep_than_gold():
    gold   = predict_wire_sweep(2.0, 25, 10.0, 0.05, wire_material="gold")
    copper = predict_wire_sweep(2.0, 25, 10.0, 0.05, wire_material="copper")
    # Copper has higher E → less deflection
    assert copper.predicted_lifetime < gold.predicted_lifetime


def test_invalid_material_raises():
    with pytest.raises(ValueError, match="wire_material"):
        predict_wire_sweep(2.0, 25, 10.0, 0.05, wire_material="silver")


def test_negative_length_raises():
    with pytest.raises(ValueError):
        predict_wire_sweep(-1.0, 25, 10.0, 0.05)


def test_units_are_mm():
    r = predict_wire_sweep(2.0, 25, 10.0, 0.05)
    assert r.units == "mm"


def test_short_wire_low_velocity_survives():
    # 1mm wire at 0.005 m/s → δ well below 10% of span (0.1mm)
    r = predict_wire_sweep(1.0, 25, 5.0, 0.005)
    assert r.probability_of_failure < 0.3
