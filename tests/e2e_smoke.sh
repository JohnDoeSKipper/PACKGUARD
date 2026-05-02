#!/usr/bin/env bash
# PackGuard v2.0 — end-to-end smoke test (no LLM key required).
#
# Boots Pipeline + Orchestrator in the background, fires the 3 demo scenarios
# through both services, and tears down. Last line ends with "decision: …"
# matching what the demo will show on stage.
#
# Usage:  bash tests/e2e_smoke.sh
# Prereqs: pip install -e Pipeline + Orchestrator/requirements.txt + venv active.

set -euo pipefail
cd "$(dirname "$0")/.."
ROOT="$PWD"
LOG="${ROOT}/.logs"
mkdir -p "${LOG}"

PYTHON="${PYTHON:-python}"
PIPELINE_PORT="${PIPELINE_PORT:-8001}"
ORCH_PORT="${ORCHESTRATOR_PORT:-8002}"

cleanup() {
  echo ""
  echo "→ tearing down…"
  for p in "${PIPE_PID:-}" "${ORCH_PID:-}"; do
    [[ -n "$p" ]] && kill "$p" 2>/dev/null || true
  done
  wait 2>/dev/null || true
}
trap cleanup EXIT INT TERM

start_service() {
  local name="$1" cwd="$2" cmd="$3"
  ( cd "${cwd}" && eval "${cmd}" ) > "${LOG}/${name}.log" 2>&1 &
  echo "$!"
}

wait_for() {
  local url="$1" tries="${2:-60}"
  for ((i = 0; i < tries; i++)); do
    if curl -sSf "${url}" > /dev/null 2>&1; then return 0; fi
    sleep 0.5
  done
  echo "TIMEOUT waiting for ${url}" >&2
  return 1
}

echo "→ Starting Pipeline on :${PIPELINE_PORT}…"
PIPE_PID=$(start_service pipeline Pipeline \
  "${PYTHON} -m uvicorn packguard_pipeline.main:app --port ${PIPELINE_PORT} --host 127.0.0.1 --log-level warning")
wait_for "http://127.0.0.1:${PIPELINE_PORT}/healthz"
echo "  ↳ pipeline up (PID ${PIPE_PID})"

echo "→ Starting Orchestrator on :${ORCH_PORT}…"
PIPELINE_URL="http://127.0.0.1:${PIPELINE_PORT}" PORT="${ORCH_PORT}" \
  ORCH_PID=$(start_service orchestrator Orchestrator \
    "PORT=${ORCH_PORT} PIPELINE_URL=http://127.0.0.1:${PIPELINE_PORT} ${PYTHON} -m uvicorn main:app --port ${ORCH_PORT} --host 127.0.0.1 --log-level warning")
wait_for "http://127.0.0.1:${ORCH_PORT}/health"
echo "  ↳ orchestrator up (PID ${ORCH_PID})"

# 1) Pipeline demo scenarios
for scenario in clean early_kill debate; do
  body=$(curl -sS "http://127.0.0.1:${PIPELINE_PORT}/demo/${scenario}")
  state=$(echo "${body}" | "${PYTHON}" -c "import sys,json; d=json.load(sys.stdin); print(d['decision_state'])")
  total=$(echo "${body}" | "${PYTHON}" -c "import sys,json; d=json.load(sys.stdin); print(d.get('total_cost_avoided', 0))")
  echo "  pipeline /demo/${scenario}: state=${state}  cost_avoided=\$${total}"
done

# 2) Bridge endpoint — orchestrator fetches a lot from Pipeline by id (no LLM call to keep it offline)
for lot_id in LOT-2026-001 LOT-2026-002 LOT-2026-003; do
  resp=$(curl -sS "http://127.0.0.1:${ORCH_PORT}/scenarios/$( [[ "$lot_id" == *002 ]] && echo early_kill || ([[ "$lot_id" == *003 ]] && echo debate_trigger || echo clean))")
  has_checks=$(echo "${resp}" | "${PYTHON}" -c "import sys,json; d=json.load(sys.stdin); print(len(d.get('checkpoints', [])))")
  echo "  orchestrator scenario for ${lot_id}: ${has_checks} checkpoints"
done

# 3) Aggregator (no LLM)
agg_payload=$(curl -sS "http://127.0.0.1:${PIPELINE_PORT}/demo/clean")
agg_resp=$(curl -sS -X POST "http://127.0.0.1:${ORCH_PORT}/aggregate" \
  -H "Content-Type: application/json" -d "${agg_payload}")
gate=$(echo "${agg_resp}" | "${PYTHON}" -c "import sys,json; d=json.load(sys.stdin); print(d.get('gate_decision', '?'))")
echo "  orchestrator /aggregate (clean): gate=${gate}"

# 4) Debate (no LLM)
deb_payload=$(curl -sS "http://127.0.0.1:${PIPELINE_PORT}/demo/debate")
deb_resp=$(curl -sS -X POST "http://127.0.0.1:${ORCH_PORT}/debate" \
  -H "Content-Type: application/json" -d "${deb_payload}")
fired=$(echo "${deb_resp}" | "${PYTHON}" -c "import sys,json; d=json.load(sys.stdin); print(d.get('rule_fired', '?'))")
echo "  orchestrator /debate (debate): rule_fired=${fired}"

echo ""
echo "decision: ship  (smoke green — Pipeline + Orchestrator integrated)"
