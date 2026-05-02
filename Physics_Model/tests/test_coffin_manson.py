"""Tests for coffin_manson.py."""
import math
import pytest
from packguard_physics.coffin_manson import predict_solder_fatigue
from packguard_physics.types import ReliabilityResult


def test_returns_reliability_result():
    r = predict_solder_fatigue(100, 1000, 10)
    assert isinstance(r, ReliabilityResult)


def test_sac305_known_nf():
    # Nf = 2.0e7 * (100)^(-2.0) = 2.0e7 / 10000 = 2000 cycles at ΔT=100°C
    r = predict_solder_fatigue(delta_t_celsius=100, cycles_per_year=100, service_life_years=1)
    # total cycles = 100, Nf median = 2000 → should be very low P(fail)
    assert r.predicted_lifetime == pytest.approx(2000.0, rel=1e-3)
    assert r.probability_of_failure < 0.1


def test_automotive_worse_than_consumer():
    automotive = predict_solder_fatigue(190, 1000, 15, "SAC305")
    consumer   = predict_solder_fatigue(40,  200,  3,  "SAC305")
    assert automotive.probability_of_failure > consumer.probability_of_failure


def test_all_alloys_accepted():
    for alloy in ["SAC305", "SAC405", "Sn63Pb37"]:
        r = predict_solder_fatigue(80, 365, 5, alloy)
        assert 0.0 <= r.probability_of_failure <= 1.0


def test_invalid_alloy_raises():
    with pytest.raises(ValueError, match="Unknown alloy"):
        predict_solder_fatigue(80, 365, 5, "FAKE_SOLDER")


def test_negative_delta_t_raises():
    with pytest.raises(ValueError, match="delta_t_celsius must be positive"):
        predict_solder_fatigue(-10, 365, 5)


def test_ci_bounds_ordered():
    r = predict_solder_fatigue(100, 500, 7)
    lo, hi = r.confidence_interval
    assert lo <= r.probability_of_failure <= hi or math.isclose(lo, hi, abs_tol=1e-6)


def test_jedec_jesd22_a104_profile():
    # JESD22-A104 Condition B: ΔT = 125°C, 2 cycles/hour = 17520 cycles/year
    r = predict_solder_fatigue(
        delta_t_celsius=125,
        cycles_per_year=17520,
        service_life_years=1,
        solder_alloy="SAC305",
    )
    # SAC305 Nf at ΔT=125: 26300 * 125^(-2) = 26300/15625 ≈ 1.68 cycles
    # total = 17520 → P(fail) should be very close to 1
    assert r.probability_of_failure > 0.99


def test_summary_string():
    r = predict_solder_fatigue(80, 365, 5)
    s = r.summary()
    assert "coffin_manson" in s
    assert "P(fail)" in s
