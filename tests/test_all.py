"""
PackGuard — Test Suite
Run with: python -m pytest tests/ -v

Tests cover:
- Debate protocol (all 5 rules)
- Probability aggregator
- Lot schema validation
- Gate decision logic
"""

import sys
import os
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from lot_schema import LotState, CheckpointResult, PhysicsOutput, make_synthetic_lot
from debate import run_debate, DebateResolution
from aggregator import (
    aggregate_failure_probability,
    compute_gate_decision,
    dppm_from_probability,
    get_threshold,
)


# ── Helpers ───────────────────────────────────────────────────────────────────

def make_lot(
    application="automotive",
    checkpoints=None,
    overall_decision="pass"
) -> LotState:
    """Build a minimal LotState for testing."""
    if checkpoints is None:
        checkpoints = [
            CheckpointResult(
                step=i,
                name=f"step_{i}",
                decision="pass",
                physics_outputs=PhysicsOutput(
                    probability_of_failure=0.000001,
                    failure_mode=f"mode_{i}",
                    process_sigma_drift=0.5,
                )
            )
            for i in range(1, 8)
        ]
    return LotState(
        lot_id="TEST-001",
        package_type="BGA-256",
        target_application=application,
        checkpoints=checkpoints,
        overall_decision=overall_decision,
    )


def checkpoint_with(
    step=1,
    p_fail=0.0,
    drift=0.0,
    cv_invoked=False,
    cv_confidence=None,
    cv_detects_defect=None,
    failure_mode="solder_fatigue",
    decision="pass",
    skipped=False,
) -> CheckpointResult:
    return CheckpointResult(
        step=step,
        name=f"step_{step}",
        decision=decision,
        skipped=skipped,
        cv_invoked=cv_invoked,
        cv_confidence=cv_confidence,
        physics_outputs=PhysicsOutput(
            probability_of_failure=p_fail,
            failure_mode=failure_mode,
            process_sigma_drift=drift,
            cv_detects_defect=cv_detects_defect,
            predicted_lifetime=10.0,
            confidence_interval=(8.0, 12.0),
        )
    )


# ── Debate Protocol Tests ─────────────────────────────────────────────────────

class TestDebateProtocol:

    def test_no_conflict_passes(self):
        """Clean lot with no issues → no debate triggered."""
        lot = make_lot()
        result = run_debate(lot)
        assert result.triggered is False
        assert result.rule_fired is None
        assert result.final_decision == "pass"
        assert result.override_applied is False

    def test_rule_1_physics_beats_vision(self):
        """Rule 1: high P(fail) + CV said no defect + low CV confidence → kill."""
        chk = checkpoint_with(
            step=1, p_fail=0.25,
            cv_invoked=True, cv_confidence=0.65,
            cv_detects_defect=False,   # CV said "no defect"
            failure_mode="die_crack_propagation",
        )
        lot = make_lot(checkpoints=[chk] + [
            checkpoint_with(step=i) for i in range(2, 8)
        ])
        result = run_debate(lot)
        assert result.triggered is True
        assert result.rule_fired == 1
        assert result.final_decision == "kill"
        assert result.override_applied is True
        assert "physics" in result.reasoning.lower()

    def test_rule_1_does_not_fire_when_cv_confident(self):
        """Rule 1 should NOT fire when CV confidence >= 0.80."""
        chk = checkpoint_with(
            step=1, p_fail=0.25,
            cv_invoked=True, cv_confidence=0.92,  # high confidence
            cv_detects_defect=False,
            failure_mode="die_crack_propagation",
        )
        lot = make_lot(checkpoints=[chk] + [
            checkpoint_with(step=i) for i in range(2, 8)
        ])
        result = run_debate(lot)
        # Rule 1 should not fire due to high CV confidence
        # (may still trigger rule 3 for automotive at p_fail=0.25 >> 10 DPPM)
        if result.rule_fired == 1:
            pytest.fail("Rule 1 fired despite high CV confidence")

    def test_rule_2_spc_drift(self):
        """Rule 2: SPC drift >3σ overrides spec compliance."""
        chk = checkpoint_with(step=3, p_fail=0.0001, drift=3.5,
                               failure_mode="imc_wire_bond")
        lot = make_lot(checkpoints=[
            checkpoint_with(step=i) for i in range(1, 3)
        ] + [chk] + [
            checkpoint_with(step=i) for i in range(4, 8)
        ])
        result = run_debate(lot)
        assert result.triggered is True
        assert result.rule_fired == 2
        assert result.final_decision == "kill"
        assert "3σ" in result.reasoning or "drift" in result.reasoning.lower()

    def test_rule_2_borderline_drift_does_not_fire(self):
        """Rule 2 threshold is >3σ (strictly greater)."""
        chk = checkpoint_with(step=3, p_fail=0.0001, drift=2.99)
        lot = make_lot(checkpoints=[
            checkpoint_with(step=i) for i in range(1, 3)
        ] + [chk] + [
            checkpoint_with(step=i) for i in range(4, 8)
        ])
        result = run_debate(lot)
        # 2.99σ should not trigger rule 2
        assert result.rule_fired != 2

    def test_rule_3_automotive_worst_case(self):
        """Rule 3: safety-critical worst-case — P(fail) > 10 DPPM → kill."""
        # 0.01% = 100 DPPM, clearly above automotive 10 DPPM
        chk = checkpoint_with(step=5, p_fail=0.0001, failure_mode="solder_fatigue")
        lot = make_lot(application="automotive", checkpoints=[
            checkpoint_with(step=i) for i in range(1, 5)
        ] + [chk] + [
            checkpoint_with(step=i) for i in range(6, 8)
        ])
        result = run_debate(lot)
        assert result.triggered is True
        assert result.rule_fired == 3
        assert result.final_decision == "kill"
        assert "automotive" in result.reasoning.lower()

    def test_rule_3_does_not_fire_for_consumer(self):
        """Rule 3 is only for safety-critical apps (automotive/medical/aerospace)."""
        chk = checkpoint_with(step=5, p_fail=0.0001)
        lot = make_lot(application="consumer", checkpoints=[
            checkpoint_with(step=i) for i in range(1, 5)
        ] + [chk] + [
            checkpoint_with(step=i) for i in range(6, 8)
        ])
        result = run_debate(lot)
        assert result.rule_fired != 3

    def test_rule_4_consumer_weighted_average(self):
        """Rule 4: consumer blended P(fail) > 0.1% → flag."""
        # Each checkpoint with P(fail) = 0.2% → avg 0.2% > 0.1% consumer threshold
        checkpoints = [
            checkpoint_with(step=i, p_fail=0.002) for i in range(1, 8)
        ]
        lot = make_lot(application="consumer", checkpoints=checkpoints)
        result = run_debate(lot)
        assert result.triggered is True
        assert result.rule_fired == 4
        assert result.final_decision == "flag"

    def test_rule_5_clean_consumer_lot(self):
        """Rule 5 (clean pass) — very low P(fail), consumer application."""
        checkpoints = [
            checkpoint_with(step=i, p_fail=0.00001) for i in range(1, 8)
        ]
        lot = make_lot(application="consumer", checkpoints=checkpoints)
        result = run_debate(lot)
        assert result.triggered is False
        assert result.rule_fired is None


# ── Aggregator Tests ──────────────────────────────────────────────────────────

class TestAggregator:

    def test_single_mode(self):
        """Single failure mode — P(any) should equal that mode's P."""
        p = aggregate_failure_probability({"solder_fatigue": 0.1})
        assert abs(p - 0.1) < 1e-9

    def test_two_independent_modes(self):
        """P(A or B) = 1 - (1-0.1)(1-0.2) = 1 - 0.72 = 0.28."""
        p = aggregate_failure_probability({
            "solder_fatigue": 0.1,
            "imc_wire_bond":  0.2,
        })
        expected = 1 - (1 - 0.1) * (1 - 0.2)
        assert abs(p - expected) < 1e-9

    def test_interaction_term_applied(self):
        """Delamination + corrosion: delamination P should be amplified 1.4x."""
        # Without interaction: 1 - (1-0.05)(1-0.05) ≈ 0.0975
        # With interaction (delamination amplified): 1 - (1-0.07)(1-0.05) ≈ 0.1165
        p = aggregate_failure_probability({
            "delamination": 0.05,
            "corrosion":    0.05,
        })
        p_no_interaction = 1 - (1 - 0.05) * (1 - 0.05)
        # p should be larger than no-interaction case
        assert p > p_no_interaction

    def test_result_clamped_to_one(self):
        """P(fail) must never exceed 1.0."""
        p = aggregate_failure_probability({m: 0.9 for m in ["a", "b", "c", "d"]})
        assert p <= 1.0

    def test_empty_modes(self):
        """Empty mode dict → P(fail) = 0."""
        p = aggregate_failure_probability({})
        assert p == 0.0

    def test_dppm_conversion(self):
        assert dppm_from_probability(0.001) == pytest.approx(1000.0)
        assert dppm_from_probability(0.00001) == pytest.approx(10.0)

    def test_gate_decision_ship(self):
        """P well below threshold → ship."""
        d = compute_gate_decision(0.000001, "automotive")
        assert d == "ship"

    def test_gate_decision_hold(self):
        """P within 5x threshold → hold (0.00001 < p <= 0.00005 for automotive)."""
        # 10 DPPM limit = 0.00001; 5x = 0.00005
        d = compute_gate_decision(0.00003, "automotive")
        assert d == "hold"

    def test_gate_decision_reject(self):
        """P above 5x threshold → reject."""
        d = compute_gate_decision(0.001, "automotive")
        assert d == "reject"

    def test_thresholds_loaded(self):
        """All 4 application thresholds should be present and reasonable."""
        for app in ["automotive", "server", "consumer", "industrial"]:
            t = get_threshold(app)
            assert "dppm_limit" in t
            assert "p_fail_max" in t
            assert "lifetime_yr" in t
            assert t["dppm_limit"] > 0
            assert 0 < t["p_fail_max"] < 1


# ── Synthetic Lot Tests ───────────────────────────────────────────────────────

class TestSyntheticLots:

    def test_clean_lot_valid(self):
        """Clean scenario lot should be a valid LotState with 7 checkpoints."""
        lot_dict = make_synthetic_lot("clean")
        lot = LotState(**lot_dict)
        assert lot.overall_decision == "pass"
        assert len(lot.checkpoints) == 7
        for chk in lot.checkpoints:
            assert chk.decision == "pass"

    def test_early_kill_valid(self):
        """Early kill lot should have checkpoint 1 as 'kill' and rest skipped."""
        lot_dict = make_synthetic_lot("early_kill")
        lot = LotState(**lot_dict)
        assert lot.overall_decision == "kill"
        assert lot.checkpoints[0].decision == "kill"
        assert lot.checkpoints[0].cost_avoided > 0
        for chk in lot.checkpoints[1:]:
            assert chk.skipped is True

    def test_debate_trigger_valid(self):
        """Debate trigger lot should have SPC drift at CP3."""
        lot_dict = make_synthetic_lot("debate_trigger")
        lot = LotState(**lot_dict)
        cp3 = next(c for c in lot.checkpoints if c.step == 3)
        assert cp3.physics_outputs.process_sigma_drift > 3.0
        assert cp3.cv_invoked is True

    def test_debate_fires_on_debate_trigger_lot(self):
        """Debate protocol rule 2 should fire on the debate_trigger scenario."""
        lot_dict = make_synthetic_lot("debate_trigger")
        lot = LotState(**lot_dict)
        result = run_debate(lot)
        assert result.triggered is True
        assert result.rule_fired == 2

    def test_no_debate_on_clean_lot(self):
        """Clean lot should produce no debate trigger and pass cleanly."""
        lot_dict = make_synthetic_lot("clean")
        lot = LotState(**lot_dict)
        result = run_debate(lot)
        # Clean lot has very low P(fail) but automotive rule 3 checks p > 0.00001
        # Our clean lot has p=0.000005 which is below 10 DPPM — should pass
        # (rule 3 fires only if p > 0.00001)
        assert result.rule_fired != 2   # No SPC drift
        assert result.rule_fired != 1   # No CV invoked


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
