"""
PackGuard — Debate Protocol
5 deterministic Python rules that resolve tool conflicts.
NO LLM is involved in any decision here — pure logic.
The LLM is the writer; these rules are the judge.
"""

from dataclasses import dataclass, field
from typing import Optional
from lot_schema import LotState, CheckpointResult


SAFETY_CRITICAL_APPS = {"automotive", "aerospace", "medical"}


@dataclass
class DebateResolution:
    triggered: bool
    rule_fired: Optional[int]
    rule_description: str
    final_decision: str           # "pass" | "flag" | "kill"
    override_applied: bool
    reasoning: str
    evidence: dict = field(default_factory=dict)


def run_debate(lot: LotState) -> DebateResolution:
    """
    Apply the 5 debate rules in priority order.
    Returns the FIRST rule that fires, or a clean pass if none fire.
    """
    checkpoints = {c.step: c for c in lot.checkpoints if not c.skipped}
    app = lot.target_application.lower()

    # ── Rule 1: Physics beats vision ─────────────────────────────────────────
    # If deterministic physics predicts failure (>15% P(fail)) but CV
    # said "no defect" with low confidence, physics wins.
    for step, chk in checkpoints.items():
        p_fail = chk.physics_outputs.probability_of_failure
        cv_conf = chk.cv_confidence or 1.0
        cv_ok = chk.physics_outputs.cv_detects_defect  # False = CV said "no defect"

        if p_fail > 0.15 and chk.cv_invoked and cv_ok is False and cv_conf < 0.80:
            return DebateResolution(
                triggered=True,
                rule_fired=1,
                rule_description="Physics beats vision — deterministic model overrides visual result",
                final_decision="kill",
                override_applied=True,
                reasoning=(
                    f"Step {step} ({chk.name}): physics model '{chk.physics_outputs.model_used}' "
                    f"predicts P(fail)={p_fail:.2%} but CV reported no defect at only "
                    f"{cv_conf:.0%} confidence. Visual inspection cannot see latent damage. "
                    "Rule 1 fires — physics result stands."
                ),
                evidence={
                    "step": step,
                    "p_fail": p_fail,
                    "cv_confidence": cv_conf,
                    "model": chk.physics_outputs.model_used,
                },
            )

    # ── Rule 2: Process beats specification ───────────────────────────────────
    # SPC drift >3σ means the process will be out-of-spec soon even if it
    # passes today's test. Drift beats a green spec result.
    for step, chk in checkpoints.items():
        drift = chk.physics_outputs.process_sigma_drift
        if drift > 3.0:
            return DebateResolution(
                triggered=True,
                rule_fired=2,
                rule_description="Process beats specification — SPC drift >3σ overrides spec compliance",
                final_decision="kill",
                override_applied=True,
                reasoning=(
                    f"Step {step} ({chk.name}): SPC shows process drifted {drift:.1f}σ from centre. "
                    "A process drifting 3σ today will be out of specification tomorrow. "
                    "Rule 2 fires — specification compliance is overridden."
                ),
                evidence={"step": step, "sigma_drift": drift},
            )

    # ── Rule 3: Worst-case wins for safety-critical ───────────────────────────
    # For AEC-Q100 / medical / aerospace: if ANY tool reports P(fail) above
    # the 10 DPPM threshold, kill — no averaging, no blending.
    if app in SAFETY_CRITICAL_APPS:
        worst_step, worst_p = None, 0.0
        for step, chk in checkpoints.items():
            p = chk.physics_outputs.probability_of_failure
            if p > worst_p:
                worst_p, worst_step = p, step

        # 10 DPPM = 0.001% = 0.00001
        if worst_p > 0.00001:
            return DebateResolution(
                triggered=True,
                rule_fired=3,
                rule_description="Worst-case wins for safety-critical application (AEC-Q100)",
                final_decision="kill",
                override_applied=True,
                reasoning=(
                    f"Automotive lot: most pessimistic estimate is step {worst_step} at "
                    f"P(fail)={worst_p:.6%} — exceeds 10 DPPM threshold. "
                    "For safety-critical applications, the worst-case tool result always wins. "
                    "Rule 3 fires."
                ),
                evidence={"worst_step": worst_step, "worst_p_fail": worst_p,
                          "dppm_equivalent": worst_p * 1_000_000},
            )

    # ── Rule 4: Weighted average for non-safety-critical ─────────────────────
    # For consumer/industrial: blend the tool outputs. If the blended
    # result exceeds the looser threshold, flag (not kill).
    if app in {"consumer", "industrial"}:
        p_vals = [c.physics_outputs.probability_of_failure for c in checkpoints.values()]
        avg_p = sum(p_vals) / len(p_vals) if p_vals else 0.0
        # Consumer threshold: 1000 DPPM = 0.1%
        threshold = 0.001 if app == "consumer" else 0.00005
        if avg_p > threshold:
            return DebateResolution(
                triggered=True,
                rule_fired=4,
                rule_description=f"Weighted average for {app} application exceeds threshold",
                final_decision="flag",
                override_applied=False,
                reasoning=(
                    f"Blended P(fail) across all steps = {avg_p:.4%}, exceeds "
                    f"{app} threshold of {threshold:.4%}. "
                    "Rule 4 fires — lot is flagged for additional inspection."
                ),
                evidence={"avg_p_fail": avg_p, "threshold": threshold},
            )

    # ── Rule 5: No conflict — clean pass ─────────────────────────────────────
    return DebateResolution(
        triggered=False,
        rule_fired=None,
        rule_description="No conflict detected — all tools agree",
        final_decision="pass",
        override_applied=False,
        reasoning="All deterministic models and CV agree within tolerance. No debate rule fired.",
        evidence={},
    )
