"""Tests for api.py Orchestrator facade."""
import pytest
from packguard_physics.api import run_all_models, run_survival_simulation
from packguard_physics.types import ReliabilityResult
from packguard_physics.survival_simulator import SimulationTrace


_FULL_STATE = {
    "delta_t_celsius": 100,
    "cycles_per_year": 1000,
    "service_life_years": 10,
    "solder_alloy": "SAC305",
    "current_density_A_per_cm2": 1e6,
    "temperature_celsius": 85,
    "conductor_material": "Cu",
    "relative_humidity_pct": 60,
    "msl_rating": 3,
    "wire_bond_temps_C": [150, 200],
    "wire_bond_times_h": [100, 50],
    "wire_pad_metallurgy": "Au-Al",
    "crack_length_mm": 0.05,
    "applied_stress_MPa": 30,
    "void_fraction": 0.2,
    "void_distribution": "dispersed",
    "nominal_thermal_resistance_K_per_W": 1.0,
    "max_junction_temp_C": 125.0,
    "ambient_temp_C": 25.0,
    "power_dissipation_W": 5.0,
    "wire_length_mm": 1.5,
    "wire_diameter_um": 25,
    "resin_viscosity_Pa_s": 5.0,
    "fill_velocity_m_per_s": 0.03,
    "wire_pitch_mm": 0.1,
    "die_cte_ppm_per_C": 2.6,
    "substrate_cte_ppm_per_C": 18,
    "package_size_mm": 20,
    "peak_reflow_temp_C": 260,
    "time_to_failure_hours": [800, 850, 900, 950, 1000, 1100, 1200],
}


def test_run_all_models_returns_dict():
    results = run_all_models(_FULL_STATE)
    assert isinstance(results, dict)
    assert len(results) > 0


def test_all_results_are_reliability_results():
    results = run_all_models(_FULL_STATE)
    for name, r in results.items():
        assert isinstance(r, ReliabilityResult), f"{name} did not return ReliabilityResult"


def test_all_ten_models_triggered():
    results = run_all_models(_FULL_STATE)
    expected = {
        "coffin_manson", "blacks_equation", "pecks_model", "arrhenius_imc",
        "griffith_fracture", "void_thermal_resistance", "wire_sweep",
        "warpage", "weibull_fit",
    }
    assert expected == set(results.keys())


def test_empty_state_returns_empty():
    results = run_all_models({})
    assert results == {}


def test_partial_state_skips_missing_models():
    state = {"delta_t_celsius": 100, "cycles_per_year": 1000, "service_life_years": 5}
    results = run_all_models(state)
    assert "coffin_manson" in results
    assert "blacks_equation" not in results


def test_bad_value_skipped_gracefully():
    state = dict(_FULL_STATE)
    state["delta_t_celsius"] = -99  # invalid — will raise ValueError inside
    results = run_all_models(state)
    assert "coffin_manson" not in results  # skipped, not crashed


def test_run_survival_simulation_returns_trace():
    trace = run_survival_simulation({"crack_length_mm": 0.0, "profile": "consumer"})
    assert isinstance(trace, SimulationTrace)


def test_run_survival_simulation_no_crack_returns_none():
    result = run_survival_simulation({"profile": "automotive"})
    assert result is None


def test_run_survival_simulation_bad_profile_returns_none():
    result = run_survival_simulation({"crack_length_mm": 0.5, "profile": "MARS"})
    assert result is None


def test_weibull_skipped_if_fewer_than_3_points():
    state = {"time_to_failure_hours": [100, 200]}
    results = run_all_models(state)
    assert "weibull_fit" not in results
