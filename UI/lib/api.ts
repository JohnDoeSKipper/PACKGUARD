// lib/api.ts
// All backend calls go here. During development, functions return mock data.
// On Day 5, change USE_MOCK to false and set the real URLs.

import axios from 'axios';
import { LotState, FinalReport, PackageType, Application } from './types';
import { CLEAN_LOT, EARLY_KILL, DEBATE_TRIGGER, CLEAN_REPORT } from './mockData';

const USE_MOCK = false; // ← Set to true to use mock data without backends running
const PIPELINE_URL = 'http://localhost:8002';
const ORCHESTRATOR_URL = 'http://localhost:8001';

// Simulate a realistic delay so the pipeline animation plays correctly
const delay = (ms: number) => new Promise(res => setTimeout(res, ms));

export async function analyzeLot(
  files: File[],
  packageType: PackageType,
  application: Application
): Promise<{ lot_id: string }> {
  if (USE_MOCK) {
    await delay(800);
    return { lot_id: 'LOT-2026-001' };
  }
  const formData = new FormData();
  files.forEach(f => formData.append('files', f));
  formData.append('package_type', packageType);
  formData.append('application', application);
  const res = await axios.post(`${PIPELINE_URL}/analyze`, formData);
  return res.data;
}

export async function loadDemoScenario(
  scenario: 'clean' | 'early_kill' | 'debate'
): Promise<{ lot_id: string }> {
  // Returns the lot_id for the chosen demo scenario
  const ids = { clean: 'LOT-2026-001', early_kill: 'LOT-2026-002', debate: 'LOT-2026-003' };
  return { lot_id: ids[scenario] };
}

export async function getLotState(lot_id: string): Promise<LotState> {
  if (USE_MOCK) {
    await delay(200);
    if (lot_id === 'LOT-2026-002') return EARLY_KILL;
    if (lot_id === 'LOT-2026-003') return DEBATE_TRIGGER;
    return CLEAN_LOT;
  }
  const res = await axios.get(`${PIPELINE_URL}/lot/${lot_id}`);
  return res.data;
}

export async function getFinalReport(lot_id: string): Promise<FinalReport> {
  if (USE_MOCK) {
    await delay(600);
    return CLEAN_REPORT;
  }
  const res = await axios.post(`${ORCHESTRATOR_URL}/report`, { lot_id });
  return res.data;
}