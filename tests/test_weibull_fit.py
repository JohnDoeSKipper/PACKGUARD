"""Tests for weibull_fit.py."""
import pytest
from packguard_physics.weibull_fit import fit_weibull
from packguard_physics.types import ReliabilityResult


_WEAR_OUT_DATA = [800, 850, 900, 950, 1000, 1050, 1100, 1150, 1200]   # tight, β >> 1
_INFANT_DATA   = [5, 10, 2, 50, 8, 3, 100, 7, 15]                     # spread left, β < 1


def test_returns_reliability_result():
    r = fit_weibull([100, 200, 150, 80, 300])
    assert isinstance(r, ReliabilityResult)


def test_wear_out_data_gives_high_beta():
    r = fit_weibull(_WEAR_OUT_DATA)
    assert r.inputs["beta"] > 1.0


def test_infant_mortality_data_gives_low_beta():
    r = fit_weibull(_INFANT_DATA)
    assert r.inputs["beta"] < 1.5  # should be near or below 1


def test_eta_is_characteristic_life():
    r = fit_weibull([100, 200, 150, 80, 300])
    assert r.inputs["eta"] == pytest.approx(r.predicted_lifetime, rel=1e-6)


def test_pfail_at_eta_is_0632():
    r = fit_weibull([100, 200, 150, 80, 300])
    assert r.probability_of_failure == pytest.approx(0.6321, abs=1e-3)


def test_too_few_points_raises():
    with pytest.raises(ValueError, match="At least 3"):
        fit_weibull([100, 200])


def test_negative_ttf_raises():
    with pytest.raises(ValueError, match="positive"):
        fit_weibull([100, -50, 200])


def test_censored_filtering():
    ttf = [100, 200, 500, 150, 300]
    censored = [False, False, True, False, False]  # 500 is censored
    r = fit_weibull(ttf, censored=censored)
    assert r.inputs["n_censored"] == 1
    assert r.inputs["n_failures"] == 4


def test_censored_wrong_length_raises():
    with pytest.raises(ValueError, match="same length"):
        fit_weibull([100, 200, 300], [False, False])


def test_units_are_hours():
    r = fit_weibull([100, 200, 150])
    assert r.units == "hours"
