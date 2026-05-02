// lib/api.ts
// Centralised backend calls.
//
// Ports (canonical, agreed Day 2 sync):
//   Pipeline (Person 2):     http://localhost:8001
//   Orchestrator (Person 3): http://localhost:8002
//   UI (this app):           http://localhost:3000
//
// Set USE_MOCK = true to develop UI without backends running.

import axios from 'axios';
import { LotState, FinalReport, PackageType, Application } from './types';
import { CLEAN_LOT, EARLY_KILL, DEBATE_TRIGGER, CLEAN_REPORT } from './mockData';

export const USE_MOCK = false;
export const PIPELINE_URL = 'http://localhost:8001';
export const ORCHESTRATOR_URL = 'http://localhost:8002';

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
  if (USE_MOCK) {
    await delay(200);
    const ids = { clean: 'LOT-2026-001', early_kill: 'LOT-2026-002', debate: 'LOT-2026-003' };
    return { lot_id: ids[scenario] };
  }
  // Hit Pipeline /demo/{scenario} which fires the in-memory pipeline and stores the lot
  const res = await axios.get(`${PIPELINE_URL}/demo/${scenario}`);
  return { lot_id: res.data.lot_id };
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
  // Bridge endpoint: Orchestrator fetches from Pipeline by lot_id and returns the report
  const res = await axios.post(`${ORCHESTRATOR_URL}/orchestrate/${lot_id}`);
  return res.data;
}

/**
 * URL of the downloadable PDF report for a given lot. Returned as a string
 * so the UI can drop it into an <a download> or window.open() call directly
 * (the Orchestrator streams the file with the right Content-Type).
 */
export function getReportPdfUrl(lot_id: string): string {
  return `${ORCHESTRATOR_URL}/orchestrate/${encodeURIComponent(lot_id)}/pdf`;
}
