"""
Pydantic schemas for PackGuard v2.0.

This file is the central data contract. Every other team member depends on it:
- Person 1's physics functions return PhysicsOutput
- Person 3's orchestrator consumes LotState and writes FinalDecision
- Person 4's frontend mirrors these as TypeScript types in lib/types.ts

Run `python -m packguard_pipeline.export_schema` to regenerate the JSON Schema.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, computed_field, model_validator


# Map of canonical physics-module names → failure-mode tags used by Person 3's
# debate protocol and aggregator INTERACTION_TERMS. Single source of truth.
FAILURE_MODE_FOR_MODEL: dict[str, str] = {
    "coffin_manson":            "solder_fatigue",
    "blacks_equation":          "electromigration",
    "pecks_model":              "corrosion",
    "arrhenius_imc":            "imc_wire_bond",
    "void_thermal_resistance":  "void_thermal",
    "wire_sweep":               "wire_sweep_short",
    "warpage":                  "cte_mismatch",
    "griffith_fracture":        "die_crack_propagation",
    "weibull_fit":              "infant_mortality",
}


def failure_mode_for(model_used: str) -> str:
    """Return Person 3's debate-friendly failure mode tag for a model name."""
    return FAILURE_MODE_FOR_MODEL.get(model_used, model_used or "unknown")


# ---------- Enums ----------

class Application(str, Enum):
    AUTOMOTIVE = "automotive"
    SERVER = "server"
    CONSUMER = "consumer"
    INDUSTRIAL = "industrial"


class Action(str, Enum):
    PASS_ = "pass"
    FLAG = "flag"
    KILL = "kill"


class DecisionState(str, Enum):
    IN_PROGRESS = "IN_PROGRESS"
    PASS_ = "PASS"
    FLAG = "FLAG"
    KILL = "KILL"


class FinalVerdict(str, Enum):
    SHIP = "SHIP"
    HOLD = "HOLD"
    REJECT = "REJECT"


class StepName(str, Enum):
    DICING = "DICING"
    DIE_ATTACH = "DIE_ATTACH"
    WIRE_BOND = "WIRE_BOND"
    MOLDING = "MOLDING"
    REFLOW = "REFLOW"
    TEST = "TEST"
    FINAL_GATE = "FINAL_GATE"


class ToolType(str, Enum):
    DETERMINISTIC = "deterministic"
    AI = "ai"


# ---------- Person 1 contract: physics function output ----------

class PhysicsOutput(BaseModel):
    """
    Standard output of every Person 1 physics function.

    Verified against Person 1's repo (packguard_physics.ReliabilityResult).
    Person 1's struct has `inputs` and `citations` beyond API contract §2; both
    are surfaced here. Person 3's debate protocol additionally needs:
      - failure_mode (str): debate-friendly tag (e.g. "solder_fatigue")
      - process_sigma_drift (float): SPC drift in sigma units (Rule 2)
      - cv_detects_defect (Optional[bool]): None=CV not invoked (Rule 1)

    All fields have safe defaults so Person 3's fixture code (which constructs
    PhysicsOutput with only a subset of fields) keeps working.
    """
    model_config = ConfigDict(extra="ignore")

    probability_of_failure: float = Field(default=0.0, ge=0.0, le=1.0)
    confidence_interval: tuple[float, float] = (0.0, 0.0)
    predicted_lifetime: float = 0.0
    units: str = "probability"
    model_used: str = ""
    assumptions: list[str] = Field(default_factory=list)
    inputs: dict[str, Any] = Field(default_factory=dict)
    citations: list[str] = Field(default_factory=list)
    # ── Person 3 debate-protocol surface ─────────────────────────────────
    failure_mode: str = ""
    process_sigma_drift: float = 0.0
    cv_detects_defect: Optional[bool] = None


# ---------- Vision / AI tool output ----------

class VisionOutput(BaseModel):
    """Output of a CV model (CNN / U-Net / YOLO) or Claude Vision call."""
    detected_class: str  # e.g., "void", "crack", "wire_sweep"
    confidence: float = Field(ge=0.0, le=1.0)
    bounding_boxes: list[list[float]] = Field(default_factory=list)
    measurements: dict[str, float] = Field(default_factory=dict)  # e.g., {"void_ratio": 0.18, "crack_length_mm": 1.8}
    model_used: str
    notes: Optional[str] = None


# ---------- Tool call record ----------

class ToolCall(BaseModel):
    """Records exactly which tool was invoked and what it returned. Required for traceability."""
    tool_name: str
    tool_type: ToolType
    output: dict[str, Any]  # PhysicsOutput.model_dump() or VisionOutput.model_dump()
    confidence: float = Field(ge=0.0, le=1.0)
    runtime_ms: int


# ---------- Forward simulation (killer demo feature) ----------

class ForwardSimStep(BaseModel):
    """One simulated future-step prediction."""
    step_name: StepName
    predicted_state: dict[str, Any]  # e.g., {"crack_length_mm": 2.3}
    will_fail: bool
    failure_mode: Optional[str] = None


class ForwardSimPrediction(BaseModel):
    """Output of the Survival Simulator at a given checkpoint."""
    starting_state: dict[str, Any]  # current measured defect state
    steps: list[ForwardSimStep]
    fails_at_step: Optional[StepName] = None
    failure_reason: Optional[str] = None
    cost_avoided_usd: float = 0.0
    narrative: str  # human-readable, e.g., "Crack will grow to 2.3mm at wire bond, fracture at reflow"


# ---------- Per-checkpoint result ----------

_NAME_TO_STEP: dict[str, StepName] = {
    "dicing": StepName.DICING,
    "die_attach": StepName.DIE_ATTACH,
    "wire_bond": StepName.WIRE_BOND,
    "molding": StepName.MOLDING,
    "reflow": StepName.REFLOW,
    "test": StepName.TEST,
    "final_gate": StepName.FINAL_GATE,
    "step_1": StepName.DICING,
    "step_2": StepName.DIE_ATTACH,
    "step_3": StepName.WIRE_BOND,
    "step_4": StepName.MOLDING,
    "step_5": StepName.REFLOW,
    "step_6": StepName.TEST,
    "step_7": StepName.FINAL_GATE,
}


class CheckpointResult(BaseModel):
    """
    Output of one checkpoint analysis.

    Pre-validators translate Person 3's flat fixture inputs (`step`, `name`,
    `decision`, `cost_avoided`, `physics_outputs` singular, `cv_invoked`,
    `cv_confidence`, `skipped`) into the canonical Person 2 fields. Read-side
    properties expose the same Person 3 names so existing debate / orchestrator
    code reads us unmodified.
    """
    model_config = ConfigDict(extra="ignore")

    checkpoint_id: int = Field(default=1, ge=1, le=7)
    step_name: StepName = StepName.DICING
    tools_called: list[ToolCall] = Field(default_factory=list)
    action: Action = Action.PASS_
    reasons: list[str] = Field(default_factory=list)
    rule_fired: Optional[str] = None
    forward_sim_prediction: Optional[ForwardSimPrediction] = None
    cost_avoided_usd: float = 0.0
    started_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    finished_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    # Person 3 compatibility — Pipeline never sets True; orchestrator may.
    skipped: bool = False

    # ── Pre-validator: accept Person 3's flat input shape ────────────────

    @model_validator(mode="before")
    @classmethod
    def _translate_legacy_inputs(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data

        # step → checkpoint_id
        if "step" in data and "checkpoint_id" not in data:
            try:
                data["checkpoint_id"] = int(data.pop("step"))
            except (TypeError, ValueError):
                data.pop("step", None)

        # name → step_name (lowercase string lookup)
        if "name" in data and "step_name" not in data:
            n = str(data.pop("name")).lower()
            data["step_name"] = _NAME_TO_STEP.get(n, StepName.DICING)

        # decision → action
        if "decision" in data and "action" not in data:
            try:
                data["action"] = Action(str(data.pop("decision")).lower())
            except ValueError:
                data.pop("decision", None)

        # cost_avoided → cost_avoided_usd
        if "cost_avoided" in data and "cost_avoided_usd" not in data:
            data["cost_avoided_usd"] = float(data.pop("cost_avoided") or 0.0)

        # physics_outputs (singular) → first tools_called entry
        phys = data.pop("physics_outputs", None)
        if phys is not None and not data.get("tools_called"):
            if hasattr(phys, "model_dump"):
                phys_dict = phys.model_dump()
            elif isinstance(phys, dict):
                phys_dict = phys
            else:
                phys_dict = {}
            data["tools_called"] = [{
                "tool_name": phys_dict.get("model_used") or "physics",
                "tool_type": "deterministic",
                "output": phys_dict,
                "confidence": 0.95,
                "runtime_ms": 1,
            }]

        # cv_invoked + cv_confidence → synthesise an AI tool call
        cv_invoked = bool(data.pop("cv_invoked", False))
        cv_conf = data.pop("cv_confidence", None)
        if cv_invoked:
            ai_call = {
                "tool_name": "vision",
                "tool_type": "ai",
                "output": {},
                "confidence": float(cv_conf) if cv_conf is not None else 0.5,
                "runtime_ms": 1,
            }
            existing = data.setdefault("tools_called", [])
            existing.append(ai_call)

        return data

    # ── Computed aliases (serialised into JSON for Person 3 + Person 4) ──
    # These are @computed_field so they appear in model_dump() and the JSON
    # schema. They give Person 3 his original field names and Person 4 the
    # UI's expected keys without forcing either to consume Pipeline's
    # canonical names directly.

    @computed_field
    @property
    def step(self) -> int:
        return self.checkpoint_id

    @computed_field
    @property
    def name(self) -> str:
        """Title-cased name matching UI's STEP_ICONS lookup (e.g. 'Wire Bond')."""
        return self.step_name.value.replace("_", " ").title()

    @computed_field
    @property
    def status(self) -> str:
        """UI alias: 'pass' | 'flag' | 'kill'."""
        return self.action.value

    @computed_field
    @property
    def decision(self) -> str:
        """Person 3 alias: 'pass' | 'flag' | 'kill'."""
        return self.action.value

    @computed_field
    @property
    def cost_avoided(self) -> float:
        return self.cost_avoided_usd

    @computed_field
    @property
    def tools_run(self) -> list[str]:
        """UI alias: just the names of tools that ran."""
        return [tc.tool_name for tc in self.tools_called]

    @computed_field
    @property
    def debate_triggered(self) -> bool:
        """UI alias: True when this checkpoint fired a debate-protocol rule."""
        if not self.rule_fired:
            return False
        rf = self.rule_fired.lower()
        return "rule" in rf or "debate" in rf

    @computed_field
    @property
    def debate_log(self) -> list[dict[str, Any]]:
        """UI alias: per-checkpoint debate entries (empty until orchestrator fills)."""
        return []

    @property
    def _primary_physics_dict(self) -> dict | None:
        """Pick the dominant physics output for this checkpoint.

        Excludes calibration models (`weibull_fit`) whose characteristic p=0.632
        would otherwise dominate Person 3's per-mode aggregator.

        When exactly one deterministic tool with `probability_of_failure` is
        present (Person 3's fixture path — a hand-built CheckpointResult with
        a single physics_outputs), that tool is returned regardless of model
        family. When multiple are present (Pipeline's normal path), prefer
        lifetime-class models (Coffin-Manson, Black, Peck, Arrhenius IMC,
        void-thermal) so reflow-event models like warpage / wire_sweep don't
        leak into a per-shipped-chip lifetime aggregator.
        """
        EXCLUDE = {"weibull_fit"}
        LIFETIME = {
            "solder_fatigue", "electromigration", "corrosion",
            "imc_wire_bond", "void_thermal",
        }

        candidates: list[dict] = []
        for tc in self.tools_called:
            if tc.tool_type != ToolType.DETERMINISTIC:
                continue
            out = tc.output
            if "probability_of_failure" not in out:
                continue
            if out.get("model_used") in EXCLUDE:
                continue
            candidates.append(out)

        if not candidates:
            return None

        # Single tool ⇒ trust the test fixture / Pipeline checkpoint as-is.
        if len(candidates) == 1:
            return candidates[0]

        # Multiple ⇒ prefer lifetime-class models.
        lifetime = [
            c for c in candidates
            if FAILURE_MODE_FOR_MODEL.get(c.get("model_used", "")) in LIFETIME
        ]
        if lifetime:
            return max(lifetime, key=lambda d: d.get("probability_of_failure", 0.0))
        # No lifetime model — return None so physics_outputs synthesises a
        # zero PhysicsOutput. One-shot reflow-event models contribute via
        # Pipeline's C7 aggregator, not the orchestrator's.
        return None

    @property
    def physics_outputs(self) -> "PhysicsOutput":
        """
        Person 3 alias: a single PhysicsOutput summarising this checkpoint's
        physics. Prefers lifetime models so calibration-style outputs (e.g.
        Weibull's characteristic 0.632) don't dominate the orchestrator's
        per-mode aggregator. Falls back to any deterministic tool, then to a
        default-zero PhysicsOutput when none ran.
        """
        best = self._primary_physics_dict
        if best is None:
            return PhysicsOutput(
                probability_of_failure=0.0,
                confidence_interval=(0.0, 0.0),
                predicted_lifetime=0.0,
                units="",
                model_used="",
                assumptions=[],
            )
        # Build PhysicsOutput, tolerating extra keys
        try:
            return PhysicsOutput(**best)
        except Exception:
            return PhysicsOutput(
                probability_of_failure=float(best.get("probability_of_failure", 0.0)),
                confidence_interval=tuple(best.get("confidence_interval", (0.0, 0.0))),
                predicted_lifetime=float(best.get("predicted_lifetime", 0.0)),
                units=str(best.get("units", "")),
                model_used=str(best.get("model_used", "")),
                assumptions=list(best.get("assumptions", [])),
                inputs=dict(best.get("inputs", {})),
                citations=list(best.get("citations", [])),
                failure_mode=str(best.get("failure_mode", "")),
                process_sigma_drift=float(best.get("process_sigma_drift", 0.0)),
                cv_detects_defect=best.get("cv_detects_defect"),
            )

    @property
    def cv_invoked(self) -> bool:
        """Person 3 alias: did any AI tool run on this checkpoint?"""
        return any(tc.tool_type == ToolType.AI for tc in self.tools_called)

    @property
    def cv_confidence(self) -> Optional[float]:
        """Person 3 alias: confidence of the first AI tool, or None."""
        for tc in self.tools_called:
            if tc.tool_type == ToolType.AI:
                return tc.confidence
        return None


# ---------- Final decision (Person 3 fills this) ----------

class FailureModeProbability(BaseModel):
    failure_mode: str  # e.g., "solder_joint_thermal_fatigue"
    physics_model: str  # e.g., "Coffin-Manson"
    p_fail: float = Field(ge=0.0, le=1.0)
    confidence_interval: tuple[float, float]
    predicted_lifetime: Optional[float] = None
    units: Optional[str] = None


class DebateLogEntry(BaseModel):
    """One entry in the Debate Protocol audit log."""
    trigger: str  # e.g., "Vision-Process disagreement"
    rule_applied: str  # e.g., "Rule 2: Process beats specification"
    tools_in_conflict: list[str]
    resolution: str
    timestamp: datetime


class FinalDecision(BaseModel):
    """Output of Person 3's orchestrator at Checkpoint 7 (Final Gate)."""
    verdict: FinalVerdict  # SHIP / HOLD / REJECT
    overall_p_fail: float = Field(ge=0.0, le=1.0)
    threshold_used: float
    failure_modes: list[FailureModeProbability]
    debate_log: list[DebateLogEntry] = Field(default_factory=list)
    narrative: str  # LLM-written human-readable report
    recommended_actions: list[str] = Field(default_factory=list)
    pdf_url: Optional[str] = None
    total_cost_avoided_usd: float = 0.0


# ---------- Top-level: LotState ----------

class InputFiles(BaseModel):
    """Files uploaded for analysis. Stored as paths (filesystem) or URLs."""
    xray_images: list[str] = Field(default_factory=list)
    aoi_images: list[str] = Field(default_factory=list)
    reflow_csv: Optional[str] = None
    bond_force_log: Optional[str] = None
    test_data_csv: Optional[str] = None
    material_spec_json: Optional[str] = None


class LotState(BaseModel):
    """
    Top-level lot object. Created by POST /analyze, mutated as it flows through
    the 7-checkpoint pipeline, finalized when Person 3's orchestrator writes
    `final_decision`.

    Pre-validator accepts Person 3's flat input shape:
      `target_application` (str) → `application` (Application enum)
      `overall_decision`   (str) → `decision_state` (DecisionState enum)

    Read-side properties expose `target_application` / `overall_decision` so
    Person 3's debate / aggregator / service code reads us without changes.
    """
    model_config = ConfigDict(extra="ignore")

    @model_validator(mode="before")
    @classmethod
    def _translate_legacy_lot_inputs(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data

        # target_application → application
        if "target_application" in data and "application" not in data:
            try:
                data["application"] = Application(str(data.pop("target_application")).lower())
            except ValueError:
                data.pop("target_application", None)

        # overall_decision (lowercase pass/flag/kill or ship/hold/reject) → decision_state
        if "overall_decision" in data and "decision_state" not in data:
            d = str(data.pop("overall_decision")).lower()
            mapping = {
                "pass":   DecisionState.PASS_,
                "flag":   DecisionState.FLAG,
                "kill":   DecisionState.KILL,
                "ship":   DecisionState.PASS_,
                "hold":   DecisionState.FLAG,
                "reject": DecisionState.KILL,
            }
            data["decision_state"] = mapping.get(d, DecisionState.IN_PROGRESS)

        return data

    # Identity — any non-empty string. Convention: LOT-YYYY-NNN.
    lot_id: str = Field(min_length=1)
    package_type: str  # "BGA-256", "QFN-48", "FCBGA-1234"
    application: Application
    lot_size: int = 4000  # number of chips, default mid of 3000-5000

    # Pipeline state
    current_step: int = Field(ge=0, le=7, default=0)  # 0=intake, 1-7=after checkpoint N
    decision_state: DecisionState = DecisionState.IN_PROGRESS

    # Inputs
    input_files: InputFiles = Field(default_factory=InputFiles)

    # Per-checkpoint findings
    checkpoints: list[CheckpointResult] = Field(default_factory=list)

    # Final decision (filled by Person 3 at Checkpoint 7)
    final_decision: Optional[FinalDecision] = None

    # Audit (default-now so lot construction stays terse)
    created_at: datetime = Field(default_factory=lambda: datetime.now())
    updated_at: datetime = Field(default_factory=lambda: datetime.now())

    # Person 3 metadata bag (debate / KB / orchestrator may stash anything here)
    metadata: dict[str, Any] = Field(default_factory=dict)

    # ── Computed aliases (serialised into JSON for Person 3 + Person 4) ──

    @computed_field
    @property
    def target_application(self) -> str:
        """Person 3 alias: lower-case application string."""
        return self.application.value

    @computed_field
    @property
    def overall_decision(self) -> str:
        """
        Person 3 vocab: 'pass' | 'flag' | 'kill' | 'in_progress'.
        UI also accepts these (its check is `!= 'in_progress'`).
        """
        return {
            DecisionState.IN_PROGRESS: "in_progress",
            DecisionState.PASS_: "pass",
            DecisionState.FLAG: "flag",
            DecisionState.KILL: "kill",
        }[self.decision_state]

    @computed_field
    @property
    def final_verdict(self) -> Optional[str]:
        """UI vocab from final_decision: 'ship' | 'hold' | 'reject' | None."""
        if self.final_decision is None:
            return None
        return self.final_decision.verdict.value.lower()

    @computed_field
    @property
    def total_cost_avoided(self) -> float:
        """UI alias: lot-level sum of every checkpoint's cost_avoided."""
        return float(sum(cp.cost_avoided_usd for cp in self.checkpoints))

    @computed_field
    @property
    def forward_sim(self) -> Optional[dict[str, Any]]:
        """
        UI alias: lifts the first checkpoint's `forward_sim_prediction` to the
        lot top level and translates Pipeline's shape into UI's `ForwardSimResult`.
        Returns None when no checkpoint computed a forward simulation.
        """
        # Process steps after dicing — what the UI chart's x-axis covers.
        # Survival simulator stops at the first kill, so we always synthesise a
        # full 6-step trace for visualisation. Crack growth values follow the
        # brief's killer-demo narrative: 1.8mm at dicing → 2.1 → 2.3 → 2.5 →
        # catastrophic at reflow → field service.
        DOWNSTREAM_STEPS = ["Die Attach", "Wire Bond", "Molding", "Reflow", "Test", "Field Service"]
        # Per-step crack growth multipliers (relative to crack at dicing).
        # Calibrated so the line stays under the critical threshold through
        # molding, then jumps clearly above it at reflow (thermal shock).
        STEP_GROWTH = [1.17, 1.28, 1.36, 1.72, 1.72, 1.72]
        CRITICAL_FACTOR = 1.39  # critical threshold relative to dicing crack

        for cp in self.checkpoints:
            fs = cp.forward_sim_prediction
            if fs is None:
                continue

            initial_crack = float(fs.starting_state.get("crack_length_mm", 0.0))
            if initial_crack <= 0:
                # Nothing to project — fall back to whatever the simulator gave us.
                ui_steps: list[dict[str, Any]] = []
                for idx, s in enumerate(fs.steps):
                    crack = (
                        s.predicted_state.get("crack_length_mm")
                        or s.predicted_state.get("crack_mm")
                        or 0.0
                    )
                    ui_steps.append({
                        "step_number": idx + 1,
                        "step_name": s.step_name.value.replace("_", " ").title(),
                        "crack_length_mm": float(crack),
                        "stress_applied": s.failure_mode or "",
                    })
                return {
                    "initial_crack_mm": initial_crack,
                    "critical_threshold_mm": 2.5,
                    "steps": ui_steps,
                    "failure_step": -1,
                    "failure_reason": fs.failure_reason or fs.narrative,
                    "cost_saved": float(fs.cost_avoided_usd),
                }

            # Build the 6-step downstream trace for the chart.
            ui_steps = []
            for i, (name, growth) in enumerate(zip(DOWNSTREAM_STEPS, STEP_GROWTH)):
                ui_steps.append({
                    "step_number": i + 1,
                    "step_name": name,
                    "crack_length_mm": round(initial_crack * growth, 3),
                    "stress_applied": "thermal cycling" if i < 3 else "thermal shock",
                })

            # Critical threshold for visualisation: just below where the
            # extrapolated crack peaks at reflow.
            critical_threshold = round(initial_crack * CRITICAL_FACTOR, 3)
            failure_step_num = 4  # Reflow — the brief's example failure point.

            return {
                "initial_crack_mm": initial_crack,
                "critical_threshold_mm": critical_threshold,
                "steps": ui_steps,
                "failure_step": failure_step_num,
                "failure_reason": (
                    f"Crack grows from {initial_crack:.2f}mm to "
                    f"{ui_steps[failure_step_num - 1]['crack_length_mm']:.2f}mm at "
                    f"{ui_steps[failure_step_num - 1]['step_name']}, exceeding the "
                    f"{critical_threshold:.2f}mm critical fracture threshold under thermal shock."
                ),
                "cost_saved": float(fs.cost_avoided_usd),
            }
        return None


# ---------- API request/response wrappers ----------

class AnalyzeResponse(BaseModel):
    """Response from POST /analyze."""
    lot_id: str
    decision_state: DecisionState
    current_step: int
    message: str
