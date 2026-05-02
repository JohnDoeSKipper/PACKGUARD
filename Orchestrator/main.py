"""
PackGuard — FastAPI Application
Person 3's deliverable to Person 4.

Endpoints:
  POST /orchestrate        → JSON report
  POST /orchestrate/pdf    → downloadable PDF report
  GET  /health             → health check
  GET  /scenarios/{name}   → pre-built demo lots for testing

Run:
  uvicorn main:app --reload --port 8001

API docs (auto-generated):
  http://localhost:8001/docs
"""

import os
import sys
import json

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import JSONResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware

from lot_schema import LotState, make_synthetic_lot
from orchestrator.service import run_orchestrator
from pdf_gen.generator import generate_pdf

# ── App setup ─────────────────────────────────────────────────────────────────
app = FastAPI(
    title="PackGuard Orchestrator API",
    description=(
        "Person 3's orchestration service. "
        "Accepts a lot_state JSON, runs debate protocol + KB retrieval, "
        "calls the Orchestrator LLM, and returns a structured risk report."
    ),
    version="2.0.0",
)

# Allow Person 4's frontend to call this API from the browser
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],      # In production: restrict to Person 4's domain
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Health check ──────────────────────────────────────────────────────────────
@app.get("/health")
def health():
    """Quick liveness check for Person 4's frontend to poll."""
    return {"status": "ok", "service": "PackGuard Orchestrator", "version": "2.0.0"}


# ── Demo scenarios (no ANTHROPIC_API_KEY needed) ──────────────────────────────
@app.get("/scenarios/{scenario_name}")
def get_scenario(scenario_name: str):
    """
    Return a pre-built synthetic lot for testing.
    Use this to show Person 4 what inputs the /orchestrate endpoint expects.
    scenario_name: clean | early_kill | debate_trigger
    """
    valid = {"clean", "early_kill", "debate_trigger"}
    if scenario_name not in valid:
        raise HTTPException(
            status_code=404,
            detail=f"Unknown scenario '{scenario_name}'. Valid: {sorted(valid)}"
        )
    lot = make_synthetic_lot(scenario_name)
    return JSONResponse(content=lot)


# ── Main orchestration endpoint ───────────────────────────────────────────────
@app.post("/orchestrate")
def orchestrate(lot: LotState):
    """
    Full orchestration pipeline:
    1. Debate protocol (deterministic)
    2. Probability aggregation (deterministic)
    3. KB retrieval (vector search)
    4. LLM narrative generation (Anthropic Claude)
    5. Return structured report JSON

    Requires ANTHROPIC_API_KEY environment variable.
    """
    try:
        report = run_orchestrator(lot.dict())
        return JSONResponse(content=report)
    except EnvironmentError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Orchestration failed: {str(e)}")


# ── PDF download endpoint ─────────────────────────────────────────────────────
@app.post("/orchestrate/pdf")
def orchestrate_pdf(lot: LotState):
    """
    Same as /orchestrate but returns a downloadable PDF instead of JSON.
    The PDF contains the full report including narrative, tables, and citations.

    Requires ANTHROPIC_API_KEY environment variable.
    """
    try:
        report = run_orchestrator(lot.dict())
        pdf_path = generate_pdf(report, lot.lot_id)
        return FileResponse(
            pdf_path,
            media_type="application/pdf",
            filename=f"packguard_{lot.lot_id}.pdf",
        )
    except EnvironmentError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"PDF generation failed: {str(e)}")


# ── Debate-only endpoint (useful for debugging) ───────────────────────────────
@app.post("/debate")
def debate_only(lot: LotState):
    """
    Run only the deterministic debate protocol without calling the LLM.
    Fast (<5ms). Useful for Person 4 to test debate logic without API key.
    """
    from debate import run_debate
    result = run_debate(lot)
    return JSONResponse(content={
        "triggered":        result.triggered,
        "rule_fired":       result.rule_fired,
        "rule_description": result.rule_description,
        "final_decision":   result.final_decision,
        "override_applied": result.override_applied,
        "reasoning":        result.reasoning,
        "evidence":         result.evidence,
    })


# ── Aggregator-only endpoint ──────────────────────────────────────────────────
@app.post("/aggregate")
def aggregate_only(lot: LotState):
    """
    Run only the probability aggregator + gate decision without LLM.
    Fast (<5ms). Useful for verifying physics model outputs.
    """
    from aggregator import (aggregate_failure_probability, compute_gate_decision,
                            dppm_from_probability, get_threshold)
    per_mode = {}
    for chk in lot.checkpoints:
        if not chk.skipped:
            mode = chk.physics_outputs.failure_mode or f"step_{chk.step}"
            per_mode[mode] = chk.physics_outputs.probability_of_failure

    overall = aggregate_failure_probability(per_mode)
    decision = compute_gate_decision(overall, lot.target_application)
    threshold = get_threshold(lot.target_application)

    return JSONResponse(content={
        "per_mode_probabilities": per_mode,
        "overall_p_fail": overall,
        "dppm_equivalent": dppm_from_probability(overall),
        "gate_decision": decision,
        "threshold": threshold,
    })
