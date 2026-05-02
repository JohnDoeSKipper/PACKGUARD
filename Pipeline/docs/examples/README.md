# Example payloads — for Person 3 (Orchestrator) & Person 4 (Frontend)

These are real, live JSON outputs captured from `Pipeline/`'s running service.
They are not handwritten mocks — they were produced by `GET /demo/{scenario}`
on the actual FastAPI app, which calls Person 1's real `packguard_physics`.

## Files

| File | What it is | Verdict |
|---|---|---|
| [`lot_state_clean_SHIP.json`](lot_state_clean_SHIP.json) | All 7 checkpoints PASS (consumer app) | **SHIP** |
| [`lot_state_early_kill_REJECT.json`](lot_state_early_kill_REJECT.json) | KILL at C1 dicing (1.8mm crack, automotive) | **KILL** |
| [`lot_state_debate_HOLD.json`](lot_state_debate_HOLD.json) | Vision OK + 2.4σ SPC drift @ wire bond → Rule 2 fires (server) | **HOLD** |
| [`physics_output_examples.json`](physics_output_examples.json) | Two raw `ReliabilityResult` dicts from Person 1's package | n/a |

## Person 3 — Orchestrator

Your orchestrator consumes `LotState` and writes back into `final_decision`.
Specifically you should:

1. Read `lot.checkpoints[*].tools_called[*].output` — these are the
   per-mode physics outputs (Person 1's `ReliabilityResult` dict shape:
   `probability_of_failure`, `confidence_interval`, `predicted_lifetime`,
   `units`, `model_used`, `assumptions`, `inputs`, `citations`).
2. Read any `forward_sim_prediction` (currently only on Checkpoint 1) — it
   contains the killer-demo narrative + step-by-step crack growth trace.
3. Read any `reasons[]` and `rule_fired` strings — these are the
   deterministic decision-rule outputs (e.g., `"Cpk < 1.33 + Rule 2
   (Process beats specification)"` for the debate scenario).
4. Mutate `lot.final_decision`:
   - `verdict`: `SHIP` | `HOLD` | `REJECT` (already set by Pipeline; you may override)
   - `narrative`: human-readable engineer report (THIS IS YOUR LLM OUTPUT)
   - `debate_log`: list of `DebateLogEntry` for any Rule-1..5 firings
   - `recommended_actions`: list[str] suggested next steps
5. The `failure_modes[]` list is already aggregated by Pipeline (1 - ∏(1-Pᵢ)
   over the 5 lifetime modes: coffin_manson, blacks_equation, pecks_model,
   arrhenius_imc, void_thermal_resistance).

## Person 4 — Frontend

Your `lib/types.ts` is generated from `Pipeline/docs/lot_state_schema.json`:

```bash
npx json-schema-to-typescript Pipeline/docs/lot_state_schema.json -o lib/types.ts
```

The example files here let you build static fixtures for offline UI dev
without the backend running. Once the backend is up, hit:

* `GET http://localhost:8001/demo/clean` → equivalent to clean fixture
* `GET http://localhost:8001/demo/early_kill` → equivalent to early-kill
* `GET http://localhost:8001/demo/debate` → equivalent to debate

## Regenerate

```bash
cd Pipeline
uvicorn packguard_pipeline.main:app --port 8001 &
sleep 2
curl http://127.0.0.1:8001/demo/clean      | python -m json.tool > docs/examples/lot_state_clean_SHIP.json
curl http://127.0.0.1:8001/demo/early_kill | python -m json.tool > docs/examples/lot_state_early_kill_REJECT.json
curl http://127.0.0.1:8001/demo/debate     | python -m json.tool > docs/examples/lot_state_debate_HOLD.json
```
