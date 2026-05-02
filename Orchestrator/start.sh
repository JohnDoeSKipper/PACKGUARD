#!/usr/bin/env bash
# PackGuard Person 3 — Quick Start Script
# Usage:  bash start.sh
#
# Port:        8002 (Pipeline owns 8001; UI runs on 3000)
# Depends on:  packguard_physics + packguard_pipeline (siblings in the monorepo)

set -e
cd "$(dirname "$0")"

echo ""
echo "╔══════════════════════════════════════════╗"
echo "║  PackGuard v2.0 — Orchestrator Service   ║"
echo "╚══════════════════════════════════════════╝"
echo ""

# ── 1. Check Python ──────────────────────────────────────────────────────────
python3 --version || { echo "ERROR: python3 not found"; exit 1; }

# ── 2. Install dependencies ──────────────────────────────────────────────────
echo "→ Installing dependencies..."
pip install -r requirements.txt --quiet
pip install -e ../Pipeline --quiet
pip install -e ../Physics_Model --quiet 2>/dev/null || true

# ── 3. Build KB index if missing ─────────────────────────────────────────────
if [ ! -f kb/index.faiss ]; then
  echo "→ Building knowledge base index..."
  python3 kb/embed.py
else
  echo "→ KB index already exists (skip rebuild)"
fi

# ── 4. Run tests ─────────────────────────────────────────────────────────────
echo "→ Running unit tests..."
python3 -m pytest tests/ -q --tb=short

# ── 5. Check API key ─────────────────────────────────────────────────────────
if [ -z "$ANTHROPIC_API_KEY" ]; then
  echo ""
  echo "⚠  ANTHROPIC_API_KEY is not set."
  echo "   The /orchestrate endpoints will return 500 until you export it:"
  echo "     export ANTHROPIC_API_KEY='sk-ant-...'"
  echo "   /debate, /aggregate, and /scenarios still work without it."
  echo ""
fi

# ── 6. Start FastAPI ─────────────────────────────────────────────────────────
PORT="${PORT:-8002}"
echo ""
echo "→ Starting Orchestrator on http://localhost:${PORT}"
echo "   Swagger docs:   http://localhost:${PORT}/docs"
echo "   Pipeline (sib): ${PIPELINE_URL:-http://localhost:8001}"
echo "   Press Ctrl+C to stop"
echo ""
uvicorn main:app --reload --port "${PORT}" --host 0.0.0.0
