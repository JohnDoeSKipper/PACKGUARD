"""
PackGuard — Lot State Schema
Person 3 owns this file. Share with Person 2 on Day 1.
This is the API contract — do NOT change field names without notifying the team.
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any


class PhysicsOutput(BaseModel):
    """Standardised output from Person 1's physics library."""
    probability_of_failure: float = 0.0          # 0.0–1.0
    confidence_interval: tuple = (0.0, 0.0)      # (low, high) 90% CI
    predicted_lifetime: Optional[float] = None    # years
    units: str = "probability"
    model_used: str = ""                          # e.g. "Coffin-Manson"
    assumptions: List[str] = []
    failure_mode: str = ""                        # e.g. "solder_fatigue"
    # Extra fields for debate protocol
    process_sigma_drift: float = 0.0             # SPC drift in sigma units
    cv_detects_defect: Optional[bool] = None     # None = CV not invoked


class CheckpointResult(BaseModel):
    """Result from one of the 7 inline checkpoints."""
    step: int                                     # 1–7
    name: str                                     # "dicing", "die_attach", etc.
    decision: str                                 # "pass" | "flag" | "kill"
    reasons: List[str] = []
    cost_avoided: float = 0.0                    # USD saved by catching defect here
    physics_outputs: PhysicsOutput = Field(default_factory=PhysicsOutput)
    cv_confidence: Optional[float] = None        # 0.0–1.0, None if CV not called
    cv_invoked: bool = False
    skipped: bool = False                        # True if lot was killed at earlier step


class LotState(BaseModel):
    """
    Complete state of one production lot as it exits the 7-checkpoint pipeline.
    Person 2 produces this; Person 3 consumes it.
    """
    lot_id: str
    package_type: str                             # e.g. "BGA-256", "QFP-64"
    target_application: str                       # "automotive"|"server"|"consumer"|"industrial"
    checkpoints: List[CheckpointResult] = []
    overall_decision: str = "pass"               # worst of all checkpoint decisions
    metadata: Dict[str, Any] = {}


# ── Helper to build a synthetic test lot ──────────────────────────────────────

def make_synthetic_lot(scenario: str = "clean") -> dict:
    """
    Produce one of the 3 demo lots as a plain dict.
    scenario: "clean" | "early_kill" | "debate_trigger"
    """
    base = {
        "lot_id": f"LOT-{scenario.upper()}-001",
        "package_type": "BGA-256",
        "target_application": "automotive",
        "metadata": {"wafer_id": "W-2026-042", "fab_line": "LINE-3"},
    }

    if scenario == "clean":
        base["overall_decision"] = "pass"
        base["checkpoints"] = [
            CheckpointResult(
                step=i, name=_step_name(i), decision="pass",
                reasons=["All metrics within spec"],
                physics_outputs=PhysicsOutput(
                    probability_of_failure=0.000005,
                    confidence_interval=(0.000001, 0.00001),
                    predicted_lifetime=16.2,
                    model_used=_step_model(i),
                    failure_mode=_step_mode(i),
                    process_sigma_drift=0.8,
                )
            ).dict() for i in range(1, 8)
        ]

    elif scenario == "early_kill":
        base["overall_decision"] = "kill"
        cp1 = CheckpointResult(
            step=1, name="dicing", decision="kill",
            reasons=["Crack length 2.1mm > 1.5mm JEDEC limit",
                     "Survival simulator: crack reaches critical fracture at reflow (step 5)"],
            cost_avoided=1847.0,
            physics_outputs=PhysicsOutput(
                probability_of_failure=0.94,
                confidence_interval=(0.88, 0.98),
                predicted_lifetime=0.3,
                model_used="Griffith Crack Propagation",
                failure_mode="die_crack_propagation",
                process_sigma_drift=0.5,
            )
        )
        skipped = [
            CheckpointResult(step=i, name=_step_name(i), decision="pass",
                             reasons=["Skipped — lot killed at step 1"],
                             skipped=True).dict()
            for i in range(2, 8)
        ]
        base["checkpoints"] = [cp1.dict()] + skipped

    elif scenario == "debate_trigger":
        base["overall_decision"] = "flag"
        base["checkpoints"] = []
        for i in range(1, 8):
            drift = 3.2 if i == 3 else 0.9
            cv_ok = True if i == 3 else None
            decision = "flag" if i == 3 else "pass"
            reasons = (["CV: no visible defect", "SPC drift 3.2σ — debate triggered"]
                       if i == 3 else ["Within spec"])
            base["checkpoints"].append(
                CheckpointResult(
                    step=i, name=_step_name(i), decision=decision,
                    reasons=reasons,
                    physics_outputs=PhysicsOutput(
                        probability_of_failure=0.0012 if i == 3 else 0.000004,
                        confidence_interval=(0.0005, 0.002) if i == 3 else (0.000001, 0.00001),
                        predicted_lifetime=14.1 if i == 3 else 16.8,
                        model_used=_step_model(i),
                        failure_mode=_step_mode(i),
                        process_sigma_drift=drift,
                        cv_detects_defect=False if i == 3 else None,
                    ),
                    cv_confidence=0.61 if i == 3 else None,
                    cv_invoked=(i == 3),
                ).dict()
            )

    return base


def _step_name(i):
    return ["", "dicing", "die_attach", "wire_bond",
            "molding", "reflow", "test", "final_gate"][i]

def _step_model(i):
    return ["", "Griffith", "Ideal Gas Law", "Arrhenius IMC",
            "Fluid Dynamics", "Coffin-Manson", "Weibull", "Aggregator"][i]

def _step_mode(i):
    return ["", "die_crack_propagation", "void_thermal", "imc_wire_bond",
            "wire_sweep_short", "solder_fatigue", "infant_mortality", "composite"][i]
