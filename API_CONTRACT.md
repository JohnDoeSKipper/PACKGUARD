# PackGuard v2.0 — API Contract
**Owner: Person 4. Update this file whenever any interface changes.**
Last updated: [YOUR NAME] — Day 1

---

## 1. Lot State JSON (Person 2 → Person 4 and Person 3)
Person 2: please paste your full lot state JSON schema here.
In the meantime, all team members use the TypeScript types in `lib/types.ts`.

Example lot_id format: "LOT-2026-001"

## 2. Physics Function Output (Person 1 → Person 2 and Person 3)
Every physics function must return exactly this shape:
{
  "probability_of_failure": float (0.0 to 1.0),
  "confidence_interval": [float, float],
  "predicted_lifetime": float,
  "units": string,
  "model_used": string,
  "assumptions": [string, ...]
}

## 3. Pipeline Service (Person 2 → Person 4)
Base URL: http://localhost:[PORT] ← Person 2: fill in your port number

POST /analyze
  Body: multipart/form-data { files, package_type, application }
  Returns: { lot_id: string }

GET /lot/{lot_id}
  Returns: Full LotState object (see lib/types.ts)

## 4. Orchestrator Service (Person 3 → Person 4)
Base URL: http://localhost:8001

POST /report
  Body: { lot_id: string }
  Returns: FinalReport object (see lib/types.ts)

GET /report/{lot_id}/pdf
  Returns: { pdf_url: string }

## 5. CORS
Person 2 and Person 3: add this to your FastAPI app on Day 5:
  from fastapi.middleware.cors import CORSMiddleware
  app.add_middleware(CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"])

## 6. Change Log
[DATE] — Person 4: Created initial contract