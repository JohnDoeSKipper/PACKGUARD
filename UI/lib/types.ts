// lib/types.ts
// Single source of truth for all data shapes the UI consumes.
//
// Day 2 unification: this file is hand-curated to mirror Pipeline's actual
// JSON output (which now includes @computed_field aliases for Person 3 +
// Person 4 vocabularies). Regenerate the canonical part with:
//
//   npx json-schema-to-typescript ../Pipeline/docs/lot_state_schema.json \
//       -o lib/types_generated.ts
//
// The hand-written interfaces below add UI-only types (FinalReport, etc.)
// and keep field names stable for existing pages and components.

// ── Enums ────────────────────────────────────────────────────────────────────

export type Decision = 'pass' | 'flag' | 'kill' | 'pending' | 'running';
export type Application = 'automotive' | 'server' | 'consumer' | 'industrial';
export type PackageType = 'BGA' | 'QFN' | 'QFP' | 'CSP' | 'Flip-Chip' | 'SiP';
export type DecisionState = 'IN_PROGRESS' | 'PASS' | 'FLAG' | 'KILL';
export type StepName = 'DICING' | 'DIE_ATTACH' | 'WIRE_BOND' | 'MOLDING' | 'REFLOW' | 'TEST' | 'FINAL_GATE';
export type FinalVerdict = 'SHIP' | 'HOLD' | 'REJECT';
export type ToolType = 'deterministic' | 'ai';
// Pipeline @computed_field returns 'in_progress' | 'pass' | 'flag' | 'kill'.
// Older mocks used 'ship' | 'hold' | 'reject'. We accept both.
export type LotStatus =
  | 'in_progress' | 'pass' | 'flag' | 'kill'
  | 'ship' | 'hold' | 'reject';

// ── Physics output (Person 1's ReliabilityResult, augmented) ─────────────────

export interface PhysicsResult {
  probability_of_failure: number;       // 0.0 to 1.0
  confidence_interval: [number, number];
  predicted_lifetime: number;
  units: string;
  model_used: string;
  assumptions: string[];
  inputs?: Record<string, unknown>;
  citations?: string[];
  failure_mode?: string;
  process_sigma_drift?: number;
  cv_detects_defect?: boolean | null;
}

export interface ToolCall {
  tool_name: string;
  tool_type: ToolType;
  output: Record<string, unknown>;
  confidence: number;
  runtime_ms: number;
}

// ── Forward simulation (UI shape — translated by Pipeline @computed_field) ───

export interface ForwardSimStep {
  step_number: number;
  step_name: string;     // Title-cased ("Reflow", "Die Attach")
  crack_length_mm: number;
  stress_applied: string;
}

export interface ForwardSimResult {
  initial_crack_mm: number;
  critical_threshold_mm: number;
  steps: ForwardSimStep[];
  failure_step: number;
  failure_reason: string;
  cost_saved: number;
}

// Pipeline's underlying ForwardSimPrediction (kept available for
// components that want raw access).
export interface ForwardSimPrediction {
  starting_state: Record<string, unknown>;
  steps: Array<{
    step_name: StepName;
    predicted_state: Record<string, unknown>;
    will_fail: boolean;
    failure_mode?: string | null;
  }>;
  fails_at_step: StepName | null;
  failure_reason: string | null;
  cost_avoided_usd: number;
  narrative: string;
}

// ── Checkpoint (Pipeline canonical + UI aliases via @computed_field) ─────────

export interface DebateEntry {
  rule_number: number;
  rule_name: string;
  tool_a: string;
  tool_a_says: string;
  tool_b: string;
  tool_b_says: string;
  winner: string;
  reason: string;
}

export interface CheckpointResult {
  // Pipeline canonical
  checkpoint_id?: number;
  step_name?: StepName;
  tools_called?: ToolCall[];
  action?: 'pass' | 'flag' | 'kill';
  rule_fired?: string | null;
  forward_sim_prediction?: ForwardSimPrediction | null;
  cost_avoided_usd?: number;
  started_at?: string;
  finished_at?: string;
  skipped?: boolean;

  // UI / Person 3 aliases (computed fields on the Pipeline server)
  step: number;
  name: string;                        // Title-cased ("Wire Bond")
  status: Decision;
  decision?: 'pass' | 'flag' | 'kill';
  reasons: string[];
  tools_run: string[];
  cost_avoided: number;
  debate_triggered?: boolean;
  debate_log?: DebateEntry[];
  physics_outputs?: PhysicsResult;     // Synthesised primary physics output
}

// ── Final decision / report ──────────────────────────────────────────────────

export interface FailureMode {
  name: string;
  probability: number;
  predicted_lifetime_years: number;
  model_used: string;
  threshold_dppm: number;
}

export interface FailureModeProbability {
  failure_mode: string;
  physics_model: string;
  p_fail: number;
  confidence_interval: [number, number];
  predicted_lifetime?: number | null;
  units?: string | null;
}

export interface DebateLogEntry {
  trigger: string;
  rule_applied: string;
  tools_in_conflict: string[];
  resolution: string;
  timestamp: string;
}

export interface FinalDecision {
  verdict: FinalVerdict;
  overall_p_fail: number;
  threshold_used: number;
  failure_modes: FailureModeProbability[];
  debate_log: DebateLogEntry[];
  narrative: string;
  recommended_actions: string[];
  pdf_url?: string | null;
  total_cost_avoided_usd: number;
}

// UI-shaped final report — what /orchestrate/{lot_id} returns.
// Some fields are produced by Person 3's LLM prompt; others are added
// by service.py (cost_saved_usd, _audit).
export interface FinalReport {
  lot_id?: string;
  overall_decision: 'ship' | 'hold' | 'reject';
  overall_probability_of_failure: number;
  predicted_lifetime_years: number;
  confidence_interval: [number, number];
  failure_modes: FailureMode[];
  narrative: string;
  recommended_actions?: string[];
  debate_log: DebateEntry[];
  pdf_url?: string;
  cost_saved_usd?: number;
  _audit?: Record<string, unknown>;
}

// ── Inputs / files ───────────────────────────────────────────────────────────

export interface InputFiles {
  xray_images?: string[];
  aoi_images?: string[];
  reflow_csv?: string | null;
  bond_force_log?: string | null;
  test_data_csv?: string | null;
  material_spec_json?: string | null;
}

// ── Top-level lot state ──────────────────────────────────────────────────────

export interface LotState {
  // Pipeline canonical
  lot_id: string;
  package_type: string;
  application: Application;
  lot_size?: number;
  current_step?: number;
  decision_state?: DecisionState;
  input_files?: InputFiles;
  checkpoints: CheckpointResult[];
  final_decision?: FinalDecision | null;
  created_at?: string;
  updated_at?: string;
  metadata?: Record<string, unknown>;

  // UI / Person 3 aliases (computed fields on the Pipeline server)
  target_application?: Application;
  overall_decision: LotStatus;            // 'in_progress' | 'pass' | 'flag' | 'kill'
  total_cost_avoided: number;
  forward_sim?: ForwardSimResult | null;
  final_verdict?: 'ship' | 'hold' | 'reject' | null;
}
