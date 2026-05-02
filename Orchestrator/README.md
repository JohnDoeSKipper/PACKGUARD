# PackGuard v2.0 — Person 3: Orchestrator, Debate & Knowledge Base

## What this subsystem does

Person 3 owns the **brain of the Final Gate** (Checkpoint 7). Every other
person's work flows through here to become the final engineering report.

```
Person 2 pipeline output (LotState JSON)
  ↓
POST /orchestrate
  ↓
[1] debate.py       → 5 deterministic rules, <5ms, NO LLM
  ↓
[2] aggregator.py   → 1−∏(1−Pᵢ) with interaction terms, deterministic
  ↓
[3] kb/retriever.py → top-3 similar historical cases (TF-IDF + FAISS, ~10ms)
  ↓
[4] orchestrator/service.py → Anthropic API, temperature=0, ~2s
  ↓
Structured JSON report + downloadable PDF
```

---

## Quick start (one command)

```bash
export ANTHROPIC_API_KEY="sk-ant-..."   # Required for LLM narrative
bash start.sh
```

Then open `frontend/index.html` in your browser.

---

## File structure

```
packguard/
├── main.py                   ← FastAPI app
├── lot_schema.py             ← Pydantic LotState (API contract with Person 2)
├── debate.py                 ← 5 deterministic debate rules
├── aggregator.py             ← Probability aggregation + DPPM thresholds
├── start.sh                  ← One-command launcher
│
├── orchestrator/
│   ├── service.py            ← run_orchestrator() main function
│   └── prompt.py             ← Orchestrator system prompt
│
├── kb/
│   ├── cases.json            ← 35 curated failure cases
│   ├── embed.py              ← Build FAISS index (run after adding cases)
│   ├── retriever.py          ← retrieve(query, k) → similar cases
│   ├── index.faiss           ← Auto-generated
│   └── tfidf_vectorizer.pkl  ← Auto-generated
│
├── pdf_gen/
│   └── generator.py          ← ReportLab PDF report
│
├── frontend/
│   └── index.html            ← Full dashboard UI
│
└── tests/
    ├── test_all.py           ← 24 unit tests (all passing)
    └── test_consistency.py   ← 10-run deterministic consistency check
```

---

## API endpoints

| Method | Path | Description | Needs API key? |
|--------|------|-------------|----------------|
| GET  | `/health` | Liveness check | No |
| GET  | `/scenarios/{name}` | Pre-built demo lots | No |
| POST | `/debate` | Debate protocol only (<5ms) | No |
| POST | `/aggregate` | Aggregator only (<5ms) | No |
| POST | `/orchestrate` | Full pipeline + LLM report | Yes |
| POST | `/orchestrate/pdf` | Full pipeline + PDF download | Yes |

**Swagger UI:** http://localhost:8001/docs

---

## The 5 debate rules (pure Python, no LLM)

| Rule | Trigger | Decision |
|------|---------|----------|
| 1 | Physics P(fail) >15% AND CV said "no defect" at <80% confidence | KILL |
| 2 | SPC drift >3σ from centre | KILL |
| 3 | Safety-critical app (automotive/medical) AND any P(fail) >10 DPPM | KILL |
| 4 | Consumer/industrial AND blended P(fail) exceeds threshold | FLAG |
| 5 | No conflict detected | PASS |

---

## Application thresholds

| Application | DPPM limit | P(fail) max | Lifetime target |
|-------------|-----------|-------------|-----------------|
| Automotive (AEC-Q100) | 10 | 0.001% | 15 years |
| Server / Datacenter | 100 | 0.01% | 7 years |
| Consumer | 1000 | 0.1% | 3 years |
| Industrial | 50 | 0.005% | 10 years |

---

## Probability aggregation formula

```
P(any failure) = 1 − ∏(1 − Pᵢ)
```

With explicit interaction terms for known coupled modes:
- Delamination + Corrosion: ×1.40 (delamination opens moisture path)
- Thermal cycling + CTE mismatch: ×1.30
- Void/thermal + Solder fatigue: ×1.20
- IMC wire bond + Thermal cycling: ×1.25
- Die crack + Solder fatigue: ×1.50

---

## Knowledge base

35 hand-curated failure cases covering:
- 8 solder fatigue (Coffin-Manson)
- 7 die crack / edge chip (Griffith)
- 6 void/thermal (Thermal resistance + Ideal Gas Law)
- 6 wire bond IMC (Arrhenius)
- 5 popcorn / moisture (Peck)
- 5 delamination (Cure shrinkage)
- 5 electromigration (Black's equation)
- 4 humidity corrosion (Peck)
- True negatives (clean lots, false positives) for CV training

Every case cites its source (JEDEC standard or IEEE paper).

To add cases: edit `kb/cases.json`, then run `python kb/embed.py`.

---

## Running the tests

```bash
# All 24 unit tests
python -m pytest tests/test_all.py -v

# 30-run deterministic consistency check (no API key needed)
python tests/test_consistency.py

# LLM consistency check (needs API key)
ANTHROPIC_API_KEY=sk-ant-... python tests/test_consistency.py
```

---

## Demo scenarios

Three pre-built lots available at `/scenarios/{name}` and in the frontend:

| Scenario | What it shows |
|----------|---------------|
| `clean` | All 7 checkpoints pass — system ships with confidence |
| `early_kill` | 2.1mm crack at CP1 → kill, saves $1,847/lot |
| `debate_trigger` | SPC 3.2σ drift at CP3, CV says OK → Rule 2 fires, KILL |

---

## Q&A prep (judges will ask these)

**"Why not let Claude make the final decision?"**
The decisions are made by deterministic physics rules and debate logic in
`debate.py` — pure Python, no randomness. Claude writes the explanation.
The final_decision field is hard-enforced after the LLM call in service.py.

**"What if the same lot gives different scores twice?"**
It can't. We use temperature=0 and the deterministic parts produce
bit-identical output every run. Verified by test_consistency.py across 10 runs.

**"How is the KB validated?"**
Every case cites a JEDEC standard or IEEE paper. We don't invent numbers.

**"What's the API latency?"**
Debate + aggregator: <5ms. KB retrieval: ~10ms. LLM call: ~1–2s.
Total: ~2s per lot — acceptable for end-of-line gate, not inline per-step.

**"What if the KB has no matching case?"**
The physics models still produce P(fail). The KB match is enrichment only
— the aggregator and gate decision work without it.

**"How does this integrate with Micron's MES?"**
The `/orchestrate` endpoint accepts standard JSON and returns structured JSON.
The MES write-back is a one-line POST call. We designed for interoperability.
