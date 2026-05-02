#!/usr/bin/env bash
# PackGuard Person 3 — Quick Start Script
# Usage:  bash start.sh

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
pip install fastapi uvicorn pydantic python-multipart reportlab \
            faiss-cpu scikit-learn pytest anthropic \
            --quiet --break-system-packages 2>/dev/null \
  || pip install fastapi uvicorn pydantic python-multipart reportlab \
                 faiss-cpu scikit-learn pytest anthropic --quiet

# ── 3. Build KB index if missing ─────────────────────────────────────────────
if [ ! -f kb/index.faiss ]; then
  echo "→ Building knowledge base index..."
  python3 kb/embed.py
else
  echo "→ KB index already exists (skip rebuild)"
fi

# ── 4. Run tests ─────────────────────────────────────────────────────────────
echo "→ Running unit tests..."
python3 -m pytest tests/test_all.py -q --tb=short

# ── 5. Check API key ─────────────────────────────────────────────────────────
if [ -z "$ANTHROPIC_API_KEY" ]; then
  echo ""
  echo "⚠  ANTHROPIC_API_KEY is not set."
  echo "   The /orchestrate endpoint will run in deterministic-only mode."
  echo "   To enable the full LLM narrative, run:"
  echo "     export ANTHROPIC_API_KEY='sk-ant-...'"
  echo ""
fi

# ── 6. Start FastAPI ─────────────────────────────────────────────────────────
echo ""
echo "→ Starting API server on http://localhost:8001"
echo "   Swagger docs: http://localhost:8001/docs"
echo "   Frontend:     open frontend/index.html in your browser"
echo "   Press Ctrl+C to stop"
echo ""
uvicorn main:app --reload --port 8001 --host 0.0.0.0
