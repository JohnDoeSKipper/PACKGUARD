"""
PackGuard — Prompt Consistency Test
Verifies that the Orchestrator returns the same final_decision
across 10 identical runs of the same lot state.

Run:
    ANTHROPIC_API_KEY=sk-ant-... python tests/test_consistency.py

If ANTHROPIC_API_KEY is not set, it tests just the deterministic
parts (debate + aggregator) and skips the LLM call.
"""

import sys, os, json, time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from lot_schema import make_synthetic_lot, LotState
from debate import run_debate
from aggregator import aggregate_failure_probability, compute_gate_decision


# ── Deterministic consistency (always runs) ───────────────────────────────────

def test_deterministic_consistency(scenario: str = "early_kill", runs: int = 10):
    """
    Debate + aggregator must return bit-identical results every run.
    This does NOT call the Anthropic API.
    """
    print(f"\n{'='*60}")
    print(f"Deterministic consistency test — scenario: {scenario}")
    print(f"Running {runs} times...")

    lot_dict = make_synthetic_lot(scenario)
    lot = LotState(**lot_dict)

    per_mode = {
        c.physics_outputs.failure_mode: c.physics_outputs.probability_of_failure
        for c in lot.checkpoints if not c.skipped and c.physics_outputs.failure_mode
    }

    results = []
    for i in range(runs):
        debate = run_debate(lot)
        p_fail = aggregate_failure_probability(per_mode)
        decision = compute_gate_decision(p_fail, lot.target_application)
        final = {"kill":"reject","flag":"hold","pass":"ship"}.get(debate.final_decision, decision) \
                if debate.override_applied else decision
        results.append({
            "run": i+1,
            "debate_triggered": debate.triggered,
            "rule_fired": debate.rule_fired,
            "overall_p_fail": p_fail,
            "final_decision": final,
        })

    decisions = [r["final_decision"] for r in results]
    p_fails   = [r["overall_p_fail"] for r in results]

    print(f"\nResults:")
    for r in results:
        print(f"  Run {r['run']:2d}: decision={r['final_decision']:6s}  "
              f"p_fail={r['overall_p_fail']:.8f}  rule={r['rule_fired']}")

    assert len(set(decisions)) == 1, \
        f"FAIL: Inconsistent decisions across runs: {set(decisions)}"
    assert max(p_fails) - min(p_fails) == 0.0, \
        f"FAIL: P(fail) variance: {max(p_fails)-min(p_fails)}"

    print(f"\n✓ PASS: All {runs} runs returned decision='{decisions[0]}' "
          f"with P(fail)={p_fails[0]:.8f}")
    return True


# ── LLM consistency (runs only if ANTHROPIC_API_KEY is set) ──────────────────

def test_llm_consistency(scenario: str = "early_kill", runs: int = 5):
    """
    Orchestrator LLM (temperature=0) must return the same final_decision
    across multiple runs of the same lot state.
    """
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("\n[SKIP] LLM consistency test — ANTHROPIC_API_KEY not set")
        print("       Set it to run the full test: export ANTHROPIC_API_KEY=sk-ant-...")
        return None

    print(f"\n{'='*60}")
    print(f"LLM consistency test — scenario: {scenario}")
    print(f"Running {runs} Anthropic API calls (temperature=0)...")

    from orchestrator.service import run_orchestrator
    lot_dict = make_synthetic_lot(scenario)

    decisions = []
    p_fails   = []

    for i in range(runs):
        print(f"  Run {i+1}/{runs}...", end=" ", flush=True)
        t0 = time.time()
        report = run_orchestrator(lot_dict)
        elapsed = time.time() - t0
        d = report.get("final_decision", "?")
        p = report.get("overall_p_fail", 0)
        decisions.append(d)
        p_fails.append(p)
        print(f"decision={d}  p_fail={p:.6f}  ({elapsed:.1f}s)")

    print(f"\nResults summary:")
    print(f"  Decisions:  {decisions}")
    print(f"  P(fail) range: {min(p_fails):.6f} – {max(p_fails):.6f}")

    assert len(set(decisions)) == 1, \
        f"FAIL: LLM returned inconsistent decisions: {set(decisions)}"
    assert max(p_fails) - min(p_fails) < 0.05, \
        f"FAIL: P(fail) variance {max(p_fails)-min(p_fails):.4f} exceeds 5% tolerance"

    print(f"\n✓ PASS: All {runs} LLM runs returned decision='{decisions[0]}'")
    return True


# ── Main ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    all_passed = True

    for scenario in ["clean", "early_kill", "debate_trigger"]:
        try:
            test_deterministic_consistency(scenario, runs=10)
        except AssertionError as e:
            print(f"\n✗ FAIL: {e}")
            all_passed = False

    try:
        test_llm_consistency("early_kill", runs=5)
    except AssertionError as e:
        print(f"\n✗ FAIL: {e}")
        all_passed = False

    print(f"\n{'='*60}")
    print("ALL CONSISTENCY TESTS PASSED ✓" if all_passed else "SOME TESTS FAILED ✗")
    sys.exit(0 if all_passed else 1)
