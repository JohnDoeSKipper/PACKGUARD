"""
PackGuard — Lot State Schema (Orchestrator-side bridge module).

Day 2 unification: this file used to define its own `PhysicsOutput`,
`CheckpointResult`, and `LotState` Pydantic models. They diverged from the
canonical schema that Person 2's Pipeline produces. To eliminate that drift
this module now **re-exports the canonical models** from
`packguard_pipeline.models`, and continues to expose `make_synthetic_lot()`
so existing tests, the `/scenarios/{name}` endpoint, and CLI quick-tests
keep working unchanged.

The canonical models include backward-compatible Person 3 aliases:
  - `LotState.target_application` (string view of `application`)
  - `LotState.overall_decision` (lower-case view of `decision_state`)
  - `CheckpointResult.step / .name / .decision / .cost_avoided`
  - `CheckpointResult.physics_outputs` (a synthesised single PhysicsOutput
    summarising the dominant deterministic tool call on that checkpoint)
  - `CheckpointResult.cv_invoked / .cv_confidence / .skipped`
  - `PhysicsOutput.failure_mode / .process_sigma_drift / .cv_detects_defect`

So `debate.py`, `aggregator.py`, `orchestrator/service.py` continue to read
the same field paths they read before — they just point at the unified model.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from packguard_pipeline.models import (  # noqa: F401  re-exports
    Action,
    Application,
    CheckpointResult,
    DecisionState,
    FAILURE_MODE_FOR_MODEL,
    FailureModeProbability,
    FinalDecision,
    FinalVerdict,
    ForwardSimPrediction,
    ForwardSimStep,
    InputFiles,
    LotState,
    PhysicsOutput,
    StepName,
    ToolCall,
    ToolType,
    failure_mode_for,
)

__all__ = [
    "Action",
    "Application",
    "CheckpointResult",
    "DecisionState",
    "FailureModeProbability",
    "FinalDecision",
    "FinalVerdict",
    "ForwardSimPrediction",
    "ForwardSimStep",
    "InputFiles",
    "LotState",
    "PhysicsOutput",
    "StepName",
    "ToolCall",
    "ToolType",
    "failure_mode_for",
    "make_synthetic_lot",
]


# ── Synthetic lot factory ────────────────────────────────────────────────────

_SCENARIO_TO_LOT: dict[str, tuple[str, Application]] = {
    "clean":           ("LOT-2026-001", Application.CONSUMER),
    "early_kill":      ("LOT-2026-002", Application.AUTOMOTIVE),
    "debate_trigger":  ("LOT-2026-003", Application.SERVER),
    # Older alias used by some tests:
    "debate":          ("LOT-2026-003", Application.SERVER),
}


def make_synthetic_lot(scenario: str = "clean") -> dict:
    """
    Run Person 2's Pipeline against a hand-constructed empty LotState seeded
    with the demo lot_id pattern. Returns the resulting `LotState` as a
    plain JSON-safe dict (what `/scenarios/{name}` returns and what
    `run_orchestrator()` accepts).

    Args:
        scenario: "clean" | "early_kill" | "debate_trigger" | "debate"

    Raises:
        ValueError on unknown scenario.
    """
    if scenario not in _SCENARIO_TO_LOT:
        raise ValueError(
            f"Unknown scenario '{scenario}'. "
            f"Valid: {sorted(set(_SCENARIO_TO_LOT) - {'debate'})}"
        )

    lot_id, application = _SCENARIO_TO_LOT[scenario]

    # Lazy import — avoids requiring Pipeline's heavy deps just to import this file
    from packguard_pipeline.checkpoints import ALL_CHECKPOINTS
    from packguard_pipeline.pipeline import CheckpointPipeline

    now = datetime.now(timezone.utc)
    lot = LotState(
        lot_id=lot_id,
        package_type="BGA-256",
        application=application,
        input_files=InputFiles(),
        created_at=now,
        updated_at=now,
        metadata={"wafer_id": "W-2026-042", "fab_line": "LINE-3"},
    )
    pipeline = CheckpointPipeline(ALL_CHECKPOINTS)
    lot = pipeline.run(lot)
    return lot.model_dump(mode="json")
