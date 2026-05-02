#!/usr/bin/env bash
# PackGuard v2.0 — start all 3 services for the demo
#
# Spawns:
#   :8001  Pipeline       (FastAPI + Person 1 physics + CV)
#   :8002  Orchestrator   (FastAPI + Anthropic Claude + PDF)
#   :3000  UI             (Next.js 16 + Recharts + D3)
#
# Each service runs in the foreground in its own terminal-friendly tee log.
# Press Ctrl+C to stop them all.

set -euo pipefail
cd "$(dirname "$0")"

# Load .env if present (ANTHROPIC_API_KEY, PACKGUARD_MODEL, etc.)
if [[ -f .env ]]; then
  set -a
  # shellcheck disable=SC1091
  source .env
  set +a
fi

LOG_DIR=".logs"
mkdir -p "${LOG_DIR}"

PYTHON="${PYTHON:-python}"
PIPELINE_PORT="${PIPELINE_PORT:-8001}"
ORCHESTRATOR_PORT="${ORCHESTRATOR_PORT:-8002}"
UI_PORT="${UI_PORT:-3000}"

# Make Pipeline + Physics_Model importable everywhere
export PYTHONUNBUFFERED=1

echo ""
echo "╔══════════════════════════════════════════╗"
echo "║   PackGuard v2.0 — start_all.sh          ║"
echo "╚══════════════════════════════════════════╝"
echo "  Pipeline      :${PIPELINE_PORT}"
echo "  Orchestrator  :${ORCHESTRATOR_PORT}  (PIPELINE_URL=http://localhost:${PIPELINE_PORT})"
echo "  UI            :${UI_PORT}"
[[ -z "${ANTHROPIC_API_KEY:-}" ]] && \
  echo "  ⚠  ANTHROPIC_API_KEY not set — /orchestrate endpoints will 500"
echo ""

# Start the three processes
(
  cd Pipeline
  echo "→ Pipeline: uvicorn packguard_pipeline.main:app --port ${PIPELINE_PORT}"
  exec ${PYTHON} -m uvicorn packguard_pipeline.main:app \
    --reload --port "${PIPELINE_PORT}" --host 0.0.0.0
) > "${LOG_DIR}/pipeline.log" 2>&1 &
PIPE_PID=$!

(
  cd Orchestrator
  PORT="${ORCHESTRATOR_PORT}" \
  PIPELINE_URL="http://localhost:${PIPELINE_PORT}" \
  echo "→ Orchestrator: uvicorn main:app --port ${ORCHESTRATOR_PORT}"
  exec ${PYTHON} -m uvicorn main:app \
    --reload --port "${ORCHESTRATOR_PORT}" --host 0.0.0.0
) > "${LOG_DIR}/orchestrator.log" 2>&1 &
ORCH_PID=$!

(
  cd UI
  echo "→ UI: npm run dev"
  exec npm run dev -- --port "${UI_PORT}"
) > "${LOG_DIR}/ui.log" 2>&1 &
UI_PID=$!

cleanup() {
  echo ""
  echo "→ Stopping services..."
  kill "${PIPE_PID}" "${ORCH_PID}" "${UI_PID}" 2>/dev/null || true
  wait
  echo "  done."
}
trap cleanup EXIT INT TERM

echo "  PIDs: pipeline=${PIPE_PID}  orchestrator=${ORCH_PID}  ui=${UI_PID}"
echo "  Logs: ${LOG_DIR}/{pipeline,orchestrator,ui}.log"
echo "  Open: http://localhost:${UI_PORT}"
echo ""
echo "  Press Ctrl+C to stop all three."
echo ""

wait
