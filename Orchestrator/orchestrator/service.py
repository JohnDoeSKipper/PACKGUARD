"""
PackGuard — Orchestrator Service
The brain of checkpoint 7 (Final Gate).

Flow:
  1. Receive lot_state dict from Person 2's pipeline
  2. Run debate protocol (deterministic — no LLM)
  3. Aggregate failure probabilities (deterministic)
  4. Retrieve similar KB cases (vector search)
  5. Call Anthropic API to write the report narrative (LLM = writer only)
  6. Return structured report JSON
"""

import json
import os
import sys
import re

# Allow running from project root
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from lot_schema import LotState
from debate import run_debate
from aggregator import (
    aggregate_failure_probability,
    compute_gate_decision,
    get_threshold,
    estimate_cost_saved,
    dppm_from_probability,
)
from orchestrator.prompt import SYSTEM_PROMPT

# KB retriever is imported lazily (requires FAISS index to exist)
def _retrieve(lot_dict, k=3):
    try:
        from kb.retriever import retrieve_for_lot
        return retrieve_for_lot(lot_dict, k=k)
    except Exception as e:
        print(f"[KB] Retrieval failed: {e}. Continuing without KB context.")
        return []


def _call_anthropic(context: dict) -> dict:
    """Call the Anthropic API and parse the JSON response."""
    try:
        import anthropic
    except ImportError:
        raise ImportError("Run: pip install anthropic")

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise EnvironmentError(
            "ANTHROPIC_API_KEY environment variable not set.\n"
            "Export it: export ANTHROPIC_API_KEY='sk-ant-...'"
        )

    client = anthropic.Anthropic(api_key=api_key)

    model_id = os.environ.get("PACKGUARD_MODEL", "claude-opus-4-7")

    response = client.messages.create(
        model=model_id,
        max_tokens=1500,
        temperature=0,          # CRITICAL: temperature=0 for determinism
        system=SYSTEM_PROMPT,
        messages=[
            {
                "role": "user",
                "content": json.dumps(context, default=str)
            }
        ],
    )

    raw = response.content[0].text

    # Strip any accidental markdown fences
    clean = re.sub(r"```(?:json)?", "", raw).replace("```", "").strip()

    try:
        return json.loads(clean)
    except json.JSONDecodeError as e:
        raise ValueError(f"LLM returned invalid JSON: {e}\nRaw response:\n{raw[:500]}")


def run_orchestrator(lot_dict: dict) -> dict:
    """
    Main orchestration function.

    Args:
        lot_dict: The lot state as a plain dict (from Person 2's pipeline).

    Returns:
        The complete report as a plain dict.
    """
    # ── 1. Parse and validate ─────────────────────────────────────────────────
    lot = LotState(**lot_dict)

    # ── 2. Run debate protocol (deterministic — no LLM) ──────────────────────
    debate_result = run_debate(lot)

    # ── 3. Aggregate failure probabilities ────────────────────────────────────
    per_mode: dict[str, float] = {}
    min_lifetime: float = 999.0
    confidence_low, confidence_high = 0.0, 0.0

    for chk in lot.checkpoints:
        if chk.skipped:
            continue
        po = chk.physics_outputs
        mode = po.failure_mode or f"step_{chk.step}_failure"
        per_mode[mode] = po.probability_of_failure

        lt = po.predicted_lifetime or 999.0
        if lt < min_lifetime:
            min_lifetime = lt
            ci = po.confidence_interval
            if ci and len(ci) == 2:
                confidence_low, confidence_high = float(ci[0]), float(ci[1])

    overall_p_fail = aggregate_failure_probability(per_mode)

    # ── 4. Apply gate threshold ───────────────────────────────────────────────
    threshold = get_threshold(lot.target_application)
    gate_decision = compute_gate_decision(overall_p_fail, lot.target_application)

    # Debate override takes precedence
    if debate_result.override_applied:
        final_decision = {
            "kill": "reject",
            "flag": "hold",
            "pass": "ship",
        }.get(debate_result.final_decision, gate_decision)
    else:
        final_decision = gate_decision

    # ── 5. Retrieve similar KB cases ─────────────────────────────────────────
    kb_cases = _retrieve(lot_dict, k=3)

    # ── 6. Build context for LLM ─────────────────────────────────────────────
    context = {
        "lot_id":             lot.lot_id,
        "package_type":       lot.package_type,
        "target_application": lot.target_application,
        "checkpoints": [
            {
                "step":            c.step,
                "name":            c.name,
                "decision":        c.decision,
                "reasons":         c.reasons,
                "cost_avoided":    c.cost_avoided,
                "skipped":         c.skipped,
                "physics_outputs": {
                    "probability_of_failure": c.physics_outputs.probability_of_failure,
                    "predicted_lifetime":     c.physics_outputs.predicted_lifetime,
                    "model_used":             c.physics_outputs.model_used,
                    "failure_mode":           c.physics_outputs.failure_mode,
                    "process_sigma_drift":    c.physics_outputs.process_sigma_drift,
                },
                "cv_invoked":      c.cv_invoked,
                "cv_confidence":   c.cv_confidence,
            }
            for c in lot.checkpoints
        ],
        "debate": {
            "triggered":         debate_result.triggered,
            "rule_fired":        debate_result.rule_fired,
            "rule_description":  debate_result.rule_description,
            "final_decision":    debate_result.final_decision,
            "override_applied":  debate_result.override_applied,
            "reasoning":         debate_result.reasoning,
            "evidence":          debate_result.evidence,
        },
        "per_mode_probabilities": per_mode,
        "overall_p_fail":         overall_p_fail,
        "dppm_equivalent":        dppm_from_probability(overall_p_fail),
        "gate_decision_before_debate": gate_decision,
        "final_decision":         final_decision,
        "threshold":              threshold,
        "predicted_lifetime_min": min_lifetime if min_lifetime < 999 else None,
        "confidence_interval":    [confidence_low, confidence_high],
        "similar_cases":          kb_cases,
    }

    # ── 7. Call Orchestrator LLM ──────────────────────────────────────────────
    report = _call_anthropic(context)

    # ── 8. Enforce debate override on the report ──────────────────────────────
    # The LLM may sometimes drift — hard-enforce the rule-based decision
    if debate_result.override_applied:
        mapped = {"kill": "reject", "flag": "hold", "pass": "ship"}
        report["final_decision"] = mapped.get(debate_result.final_decision, report.get("final_decision"))
        report["debate_override"] = True

    # ── 9. Inject cost saved ─────────────────────────────────────────────────
    if not report.get("cost_saved_usd"):
        report["cost_saved_usd"] = estimate_cost_saved(lot, lot.checkpoints)

    # ── 10. Attach audit trail ───────────────────────────────────────────────
    report["_audit"] = {
        "lot_id":         lot.lot_id,
        "debate":         context["debate"],
        "per_mode_probs": per_mode,
        "kb_cases_used":  [c.get("id") for c in kb_cases],
        "model_called":   os.environ.get("PACKGUARD_MODEL", "claude-opus-4-7"),
        "temperature":    0,
    }

    return report


# ── CLI quick-test ────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import argparse
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from lot_schema import make_synthetic_lot

    parser = argparse.ArgumentParser(description="Test the orchestrator with a synthetic lot")
    parser.add_argument("--scenario", choices=["clean", "early_kill", "debate_trigger"],
                        default="early_kill")
    args = parser.parse_args()

    print(f"Running orchestrator with scenario: {args.scenario}")
    lot = make_synthetic_lot(args.scenario)

    result = run_orchestrator(lot)
    print(json.dumps(result, indent=2, default=str))
