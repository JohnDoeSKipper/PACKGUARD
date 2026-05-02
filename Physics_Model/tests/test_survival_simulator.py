"""Tests for survival_simulator.py."""
import pytest
from packguard_physics.survival_simulator import (
    simulate_defect,
    simulate_batch,
    SimulationTrace,
    StepResult,
)


def test_returns_simulation_trace():
    trace = simulate_defect(initial_crack_mm=0.0, profile="consumer")
    assert isinstance(trace, SimulationTrace)


def test_clean_defect_survives_consumer():
    trace = simulate_defect(initial_crack_mm=0.0, profile="consumer")
    assert trace.survived is True
    assert trace.kill_step is None


def test_always_has_six_steps_when_alive():
    trace = simulate_defect(initial_crack_mm=0.0, profile="consumer")
    assert len(trace.steps) == 6


def test_large_crack_fails_before_field_service():
    # 1.8 mm crack at automotive stress → should fail at reflow or earlier
    trace = simulate_defect(initial_crack_mm=1.8, profile="automotive", solder_alloy="SAC305")
    assert not trace.survived
    assert trace.kill_step is not None


def test_steps_stop_after_kill():
    trace = simulate_defect(initial_crack_mm=1.8, profile="automotive")
    # Once killed, no more steps should appear
    killed_at = None
    for i, step in enumerate(trace.steps):
        if step.defect_killed:
            killed_at = i
            break
    if killed_at is not None:
        assert len(trace.steps) == killed_at + 1


def test_zero_crack_automotive_may_survive_or_fail():
    # Zero crack + automotive → up to field service, result depends on solder fatigue
    trace = simulate_defect(initial_crack_mm=0.0, profile="automotive", solder_alloy="Sn63Pb37")
    assert isinstance(trace.survived, bool)


def test_all_steps_have_valid_pfail():
    trace = simulate_defect(initial_crack_mm=0.0, profile="server")
    for step in trace.steps:
        assert isinstance(step, StepResult)
        assert 0.0 <= step.p_fail <= 1.0


def test_multiple_profiles_accepted():
    for profile in ["automotive", "server", "consumer"]:
        trace = simulate_defect(profile=profile)
        assert len(trace.steps) > 0


def test_invalid_profile_raises():
    with pytest.raises(ValueError, match="Unknown profile"):
        simulate_defect(profile="space")


def test_simulate_batch():
    defects = [
        {"initial_crack_mm": 0.0},
        {"initial_crack_mm": 0.5},
        {"initial_crack_mm": 1.8},
    ]
    results = simulate_batch(defects, profile="automotive")
    assert len(results) == 3
    # Largest crack most likely to fail
    assert results[2].survived is False or results[1].survived is False


def test_killer_demo_scenario():
    """1.8 mm crack, automotive profile, SAC305 — must fail before field service."""
    trace = simulate_defect(
        initial_crack_mm=1.8,
        profile="automotive",
        solder_alloy="SAC305",
        void_fraction=0.0,
    )
    trace.print_trace()

    assert not trace.survived, "Killer demo: 1.8 mm crack should fail before field service"
    assert trace.kill_step in ("die_attach", "wire_bond", "molding", "reflow", "burn_in"), \
        f"Expected pre-field failure, got: {trace.kill_step}"
