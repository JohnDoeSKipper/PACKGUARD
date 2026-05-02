// lib/mockData.ts
// Realistic fake data for the 3 demo scenarios.
// These allow the demo to run perfectly without needing the backend live.

import { LotState, FinalReport } from './types';

export const CLEAN_LOT: LotState = {
  lot_id: 'LOT-2026-001',
  package_type: 'BGA',
  application: 'automotive',
  overall_decision: 'ship',
  total_cost_avoided: 0,
  checkpoints: [
    { step: 1, name: 'Dicing', status: 'pass', tools_run: ['Edge Chip Classifier', 'Griffith Crack Model', 'Survival Simulator'], reasons: ['Max crack: 0.3 mm — within JEDEC limit of 1.5 mm', 'Survival simulator: all steps — PASS'], cost_avoided: 0 },
    { step: 2, name: 'Die Attach', status: 'pass', tools_run: ['Void Ratio Calculator', 'Thermal Resistance Estimator', 'Ideal Gas Law'], reasons: ['Void ratio: 8.2% — below 25% JEDEC threshold', 'Voids dispersed uniformly — no hot spot risk'], cost_avoided: 0 },
    { step: 3, name: 'Wire Bond', status: 'pass', tools_run: ['Pull/Shear SPC', 'Arrhenius IMC Model', 'Vision Agent'], reasons: ['Cpk: 1.61 — process stable', 'Predicted IMC at 15 yr: 3.1 µm — below 5 µm limit'], cost_avoided: 0 },
    { step: 4, name: 'Molding', status: 'pass', tools_run: ['Wire Sweep Calculator', 'Cure Shrinkage Stress Model', 'Vision Agent'], reasons: ['Max wire deflection: 4.2% of pitch — below 10% limit', 'Interface stress: within adhesion strength'], cost_avoided: 0 },
    { step: 5, name: 'Reflow', status: 'pass', tools_run: ["Coffin-Manson", "Black's Equation", "Peck's Model", 'dT/dt Analysis', 'FFT Thermal'], reasons: ['Predicted Nf: 1,840 cycles — above 1,000 cycle spec', 'MTTF electromigration: 14.2 yr', 'No popcorn risk — MSL-3 compliant'], cost_avoided: 0 },
    { step: 6, name: 'Test', status: 'pass', tools_run: ['Western Electric SPC', 'Weibull Fit', 'Knowledge Agent'], reasons: ['Weibull β: 2.3 — wear-out population, healthy', 'No SPC violations'], cost_avoided: 0 },
    { step: 7, name: 'Final Gate', status: 'pass', tools_run: ['P(fail) Aggregator', 'Threshold Engine', 'Orchestrator LLM'], reasons: ['Overall P(fail): 0.0003 — below automotive threshold of 0.001', 'All failure modes within spec'], cost_avoided: 0 },
  ],
};

export const EARLY_KILL: LotState = {
  lot_id: 'LOT-2026-002',
  package_type: 'BGA',
  application: 'automotive',
  overall_decision: 'reject',
  total_cost_avoided: 1847,
  forward_sim: {
    initial_crack_mm: 1.8,
    critical_threshold_mm: 2.0,
    steps: [
      { step_number: 1, step_name: 'Dicing', crack_length_mm: 1.8, stress_applied: 'None' },
      { step_number: 2, step_name: 'Die Attach', crack_length_mm: 2.05, stress_applied: 'Thermal cure: σ = E·α·ΔT·(1-ν)⁻¹' },
      { step_number: 3, step_name: 'Wire Bond', crack_length_mm: 2.18, stress_applied: 'Hertzian contact stress' },
      { step_number: 4, step_name: 'Molding', crack_length_mm: 2.29, stress_applied: 'Hydrostatic pressure + shrinkage' },
      { step_number: 5, step_name: 'Reflow', crack_length_mm: 3.1, stress_applied: 'Thermal shock at 245°C' },
    ],
    failure_step: 2,
    failure_reason: 'Crack exceeds critical fracture length (2.0 mm) during die attach thermal cure. Catastrophic fracture predicted at Reflow (245°C thermal shock).',
    cost_saved: 1847,
  },
  checkpoints: [
    { step: 1, name: 'Dicing', status: 'kill', tools_run: ['Edge Chip Classifier', 'Griffith Crack Model', 'Survival Simulator', 'Vision Agent'], reasons: ['Crack detected: 1.8 mm', 'Survival Simulator: crack will grow to 2.05 mm at Die Attach, exceeding critical threshold of 2.0 mm', 'Catastrophic fracture predicted at Reflow'], cost_avoided: 1847 },
    { step: 2, name: 'Die Attach', status: 'pending', tools_run: [], reasons: ['Lot killed at Step 1 — not reached'], cost_avoided: 0 },
    { step: 3, name: 'Wire Bond', status: 'pending', tools_run: [], reasons: ['Lot killed at Step 1 — not reached'], cost_avoided: 0 },
    { step: 4, name: 'Molding', status: 'pending', tools_run: [], reasons: ['Lot killed at Step 1 — not reached'], cost_avoided: 0 },
    { step: 5, name: 'Reflow', status: 'pending', tools_run: [], reasons: ['Lot killed at Step 1 — not reached'], cost_avoided: 0 },
    { step: 6, name: 'Test', status: 'pending', tools_run: [], reasons: ['Lot killed at Step 1 — not reached'], cost_avoided: 0 },
    { step: 7, name: 'Final Gate', status: 'pending', tools_run: [], reasons: ['Lot killed at Step 1 — not reached'], cost_avoided: 0 },
  ],
};

export const DEBATE_TRIGGER: LotState = {
  lot_id: 'LOT-2026-003',
  package_type: 'QFN',
  application: 'server',
  overall_decision: 'hold',
  total_cost_avoided: 420,
  checkpoints: [
    { step: 1, name: 'Dicing', status: 'pass', tools_run: ['Edge Chip Classifier', 'Griffith Crack Model'], reasons: ['Max crack: 0.4 mm — within spec'], cost_avoided: 0 },
    { step: 2, name: 'Die Attach', status: 'pass', tools_run: ['Void Ratio Calculator', 'Thermal Resistance Estimator'], reasons: ['Void ratio: 11.3% — within spec'], cost_avoided: 0 },
    {
      step: 3, name: 'Wire Bond', status: 'flag',
      tools_run: ['Pull/Shear SPC', 'Arrhenius IMC Model', 'Vision Agent', 'Debate Protocol'],
      reasons: ['Vision Agent: no visible defects detected — PASS', 'SPC Rule 2: process drift +3.2σ detected on bond force — OVERRIDE', 'Debate Rule 2 fired: Process beats specification', 'Decision: FLAG for additional inspection'],
      cost_avoided: 420,
      debate_triggered: true,
      debate_log: [{
        rule_number: 2, rule_name: 'Process beats specification',
        tool_a: 'Vision Agent', tool_a_says: 'No visible bond defects. Geometry within normal range. PASS.',
        tool_b: 'SPC Monitor', tool_b_says: 'Bond force drifting +3.2σ from mean over last 180 bonds. Western Electric Rule 1 violated.',
        winner: 'SPC Monitor',
        reason: 'A process drifting 3σ today will be out of spec tomorrow. Visual inspection cannot detect latent mechanical degradation. Rule 2 overrides Vision result.',
      }],
    },
    { step: 4, name: 'Molding', status: 'pass', tools_run: ['Wire Sweep Calculator', 'Cure Shrinkage Stress Model'], reasons: ['Wire deflection: 5.1% of pitch — within spec'], cost_avoided: 0 },
    { step: 5, name: 'Reflow', status: 'pass', tools_run: ["Coffin-Manson", "Black's Equation"], reasons: ['Predicted Nf: 2,100 cycles — above server spec'], cost_avoided: 0 },
    { step: 6, name: 'Test', status: 'pass', tools_run: ['Weibull Fit', 'Western Electric SPC'], reasons: ['Weibull β: 1.8 — healthy wear-out population'], cost_avoided: 0 },
    { step: 7, name: 'Final Gate', status: 'flag', tools_run: ['P(fail) Aggregator', 'Threshold Engine', 'Orchestrator LLM'], reasons: ['Wire bond process instability noted at Step 3', 'Recommend additional pull test sample at Step 3 before ship'], cost_avoided: 0 },
  ],
};

export const CLEAN_REPORT: FinalReport = {
  lot_id: 'LOT-2026-001',
  overall_decision: 'ship',
  overall_probability_of_failure: 0.0003,
  predicted_lifetime_years: 16.4,
  confidence_interval: [14.1, 18.9],
  failure_modes: [
    { name: 'Solder Joint Thermal Fatigue', probability: 0.00012, predicted_lifetime_years: 16.4, model_used: 'Coffin-Manson', threshold_dppm: 10 },
    { name: 'Electromigration', probability: 0.00008, predicted_lifetime_years: 14.2, model_used: "Black's Equation", threshold_dppm: 10 },
    { name: 'Humidity Corrosion', probability: 0.00006, predicted_lifetime_years: 18.1, model_used: "Peck's Model", threshold_dppm: 10 },
    { name: 'Wire Bond IMC Failure', probability: 0.00004, predicted_lifetime_years: 19.3, model_used: 'Arrhenius IMC Growth', threshold_dppm: 10 },
    { name: 'Delamination', probability: 0.00010, predicted_lifetime_years: 15.7, model_used: 'Interfacial Fracture Mechanics', threshold_dppm: 10 },
    { name: 'Die Crack Propagation', probability: 0.00003, predicted_lifetime_years: 22.1, model_used: "Griffith's Criterion", threshold_dppm: 10 },
  ],
  narrative: 'Lot LOT-2026-001 passed all seven inline checkpoints with no defects detected. All failure mode probabilities are well below the AEC-Q100 automotive threshold of 10 DPPM. Coffin-Manson analysis predicts 1,840 thermal cycles to first solder joint failure, exceeding the 1,000-cycle automotive specification by a margin of 84%. Electromigration MTTF of 14.2 years exceeds the 15-year target at the 90th percentile confidence level. This lot is cleared for shipment.',
  debate_log: [],
  pdf_url: '/api/report/LOT-2026-001/pdf',
};