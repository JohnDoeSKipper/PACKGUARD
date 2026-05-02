"""
PackGuard — Orchestrator FastAPI Application
Person 3 owns this service. It consumes Person 2's Pipeline output and writes
the human-readable risk report.

Endpoints (canonical post-integration):
  GET  /health                          health check
  GET  /scenarios/{name}                pre-built demo lots (calls Pipeline pkg)
  POST /orchestrate                     accept LotState body, return JSON report
  POST /orchestrate/pdf                 accept LotState body, return PDF
  POST /orchestrate/{lot_id}            ★ bridge: fetch lot from Pipeline by id, return JSON
  POST /orchestrate/{lot_id}/pdf        ★ bridge: fetch lot from Pipeline by id, return PDF
  POST /debate                          deterministic debate only (no LLM)
  POST /aggregate                       probability aggregator only (no LLM)

Run:
  uvicorn main:app --reload --port 8002

Environment:
  ANTHROPIC_API_KEY   required for /orchestrate (LLM narrative)
  PACKGUARD_MODEL     optional override for the Claude model name
  PIPELINE_URL        optional override for Pipeline service URL (default http://localhost:8001)
"""

from __future__ import annotations

import os
import sys
import json

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import httpx
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import JSONResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware

from lot_schema import LotState, make_synthetic_lot
from orchestrator.service import run_orchestrator
from pdf_gen.generator import generate_pdf

# ── Config ────────────────────────────────────────────────────────────────────

PIPELINE_URL = os.environ.get("PIPELINE_URL", "http://localhost:8001")
PORT = int(os.environ.get("PORT", "8002"))


# ── App setup ─────────────────────────────────────────────────────────────────

app = FastAPI(
    title="PackGuard Orchestrator API",
    description=(
        "Person 3's orchestration service. "
        "Accepts a Pipeline-produced LotState (or a lot_id to fetch it), runs "
        "debate protocol + KB retrieval, calls the Orchestrator LLM, and returns "
        "a structured risk report."
    ),
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Health ────────────────────────────────────────────────────────────────────

@app.get("/health")
def health():
    """Quick liveness check for the frontend to poll."""
    return {
        "status": "ok",
        "service": "PackGuard Orchestrator",
        "version": "2.0.0",
        "port": PORT,
        "pipeline_url": PIPELINE_URL,
    }


# ── Demo scenarios (no ANTHROPIC_API_KEY needed) ──────────────────────────────

@app.get("/scenarios/{scenario_name}")
def get_scenario(scenario_name: str):
    """
    Return a pre-built synthetic lot for testing. Uses Pipeline's real
    CheckpointPipeline + Person 1's physics under the hood.

    scenario_name: clean | early_kill | debate_trigger
    """
    valid = {"clean", "early_kill", "debate_trigger"}
    if scenario_name not in valid:
        raise HTTPException(
            status_code=404,
            detail=f"Unknown scenario '{scenario_name}'. Valid: {sorted(valid)}",
        )
    lot = make_synthetic_lot(scenario_name)
    return JSONResponse(content=lot)


# ── Main orchestration endpoint (body) ────────────────────────────────────────

@app.post("/orchestrate")
def orchestrate(lot: LotState):
    """
    Run the full orchestration pipeline on a LotState body.

    1. Debate protocol (deterministic)
    2. Probability aggregation (deterministic)
    3. KB retrieval (vector search)
    4. LLM narrative generation (Anthropic Claude)
    5. Return structured report JSON

    Requires ANTHROPIC_API_KEY environment variable.
    """
    try:
        report = run_orchestrator(lot.model_dump(mode="json"))
        return JSONResponse(content=report)
    except EnvironmentError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"Orchestration failed: {str(e)}")


@app.post("/orchestrate/pdf")
def orchestrate_pdf(lot: LotState):
    """Same as /orchestrate but returns a downloadable PDF."""
    try:
        report = run_orchestrator(lot.model_dump(mode="json"))
        pdf_path = generate_pdf(report, lot.lot_id)
        return FileResponse(
            pdf_path,
            media_type="application/pdf",
            filename=f"packguard_{lot.lot_id}.pdf",
        )
    except EnvironmentError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"PDF generation failed: {str(e)}")


# ── Bridge endpoints: by lot_id (Person 4 frontend uses these) ───────────────

def _fetch_lot_from_pipeline(lot_id: str) -> dict:
    """GET LotState JSON from Pipeline service. Raises HTTPException on failure."""
    url = f"{PIPELINE_URL}/lot/{lot_id}"
    try:
        with httpx.Client(timeout=10.0) as client:
            resp = client.get(url)
        resp.raise_for_status()
    except httpx.HTTPStatusError as e:
        raise HTTPException(
            status_code=e.response.status_code,
            detail=f"Pipeline returned {e.response.status_code} for {lot_id}",
        )
    except httpx.RequestError as e:
        raise HTTPException(
            status_code=503,
            detail=f"Cannot reach Pipeline at {PIPELINE_URL}: {e}",
        )
    return resp.json()


@app.post("/orchestrate/{lot_id}")
def orchestrate_by_lot_id(lot_id: str):
    """
    Bridge endpoint — fetch the lot from Pipeline by lot_id, then orchestrate.

    The frontend hits POST /orchestrate/<lot_id> (no body) once Pipeline has
    finished an /analyze call and returned the lot_id.
    """
    lot_dict = _fetch_lot_from_pipeline(lot_id)
    try:
        report = run_orchestrator(lot_dict)
        return JSONResponse(content=report)
    except EnvironmentError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"Orchestration failed: {str(e)}")


@app.post("/orchestrate/{lot_id}/pdf")
def orchestrate_by_lot_id_pdf(lot_id: str):
    """Bridge endpoint, PDF variant."""
    lot_dict = _fetch_lot_from_pipeline(lot_id)
    try:
        report = run_orchestrator(lot_dict)
        pdf_path = generate_pdf(report, lot_id)
        return FileResponse(
            pdf_path,
            media_type="application/pdf",
            filename=f"packguard_{lot_id}.pdf",
        )
    except EnvironmentError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"PDF generation failed: {str(e)}")


# ── Debate-only endpoint (useful for debugging) ───────────────────────────────

@app.post("/debate")
def debate_only(lot: LotState):
    """Run only the deterministic debate protocol without calling the LLM."""
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
    """Run only the probability aggregator + gate decision without LLM."""
    from aggregator import (aggregate_failure_probability, compute_gate_decision,
                            dppm_from_probability, get_threshold)
    per_mode: dict[str, float] = {}
    for chk in lot.checkpoints:
        if not chk.skipped:
            mode = chk.physics_outputs.failure_mode or f"step_{chk.step}"
            per_mode[mode] = chk.physics_outputs.probability_of_failure

    overall = aggregate_failure_probability(per_mode)
    decision = compute_gate_decision(overall, lot.target_application)
    threshold = get_threshold(lot.target_application)

    return JSONResponse(content={
        "per_mode_probabilities": per_mode,
        "overall_p_fail":         overall,
        "dppm_equivalent":        dppm_from_probability(overall),
        "gate_decision":          decision,
        "threshold":              threshold,
    })
