// lib/types.ts
// This file is the single source of truth for all data shapes.
// Share this file with Persons 2 and 3 so everyone uses the same types.

export type Decision = 'pass' | 'flag' | 'kill' | 'pending' | 'running';
export type Application = 'automotive' | 'server' | 'consumer' | 'industrial';
export type PackageType = 'BGA' | 'QFN' | 'QFP' | 'CSP' | 'Flip-Chip' | 'SiP';

export interface PhysicsResult {
  probability_of_failure: number;       // 0.0 to 1.0
  confidence_interval: [number, number]; // [low, high]
  predicted_lifetime: number;
  units: string;
  model_used: string;
  assumptions: string[];
}

export interface CheckpointResult {
  step: number;                         // 1 through 7
  name: string;
  status: Decision;
  tools_run: string[];
  reasons: string[];
  cost_avoided: number;                 // dollars saved by killing/flagging here
  physics_results?: PhysicsResult[];
  debate_triggered?: boolean;
  debate_log?: DebateEntry[];
}

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

export interface FailureMode {
  name: string;
  probability: number;                  // 0.0 to 1.0
  predicted_lifetime_years: number;
  model_used: string;
  threshold_dppm: number;
}

export interface ForwardSimStep {
  step_number: number;
  step_name: string;
  crack_length_mm: number;
  stress_applied: string;
}

export interface ForwardSimResult {
  initial_crack_mm: number;
  critical_threshold_mm: number;
  steps: ForwardSimStep[];
  failure_step: number;                 // step number where failure occurs, -1 if survives
  failure_reason: string;
  cost_saved: number;
}

export interface LotState {
  lot_id: string;
  package_type: PackageType;
  application: Application;
  checkpoints: CheckpointResult[];
  overall_decision: 'ship' | 'hold' | 'reject' | 'in_progress';
  total_cost_avoided: number;
  forward_sim?: ForwardSimResult;
}

export interface FinalReport {
  lot_id: string;
  overall_decision: 'ship' | 'hold' | 'reject';
  overall_probability_of_failure: number;
  failure_modes: FailureMode[];
  narrative: string;
  debate_log: DebateEntry[];
  pdf_url: string;
  predicted_lifetime_years: number;
  confidence_interval: [number, number];
}