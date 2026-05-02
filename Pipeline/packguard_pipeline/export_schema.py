"""
Export the LotState JSON Schema to docs/lot_state_schema.json so Person 4 can
generate TypeScript types from it (e.g., via `json-schema-to-typescript`).

Run:
    python -m packguard_pipeline.export_schema
"""

import json
from pathlib import Path

from .models import LotState

OUT = Path(__file__).resolve().parents[1] / "docs" / "lot_state_schema.json"


def main() -> None:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    # mode="serialization" includes @computed_field aliases (step, name,
    # status, tools_run, cost_avoided, total_cost_avoided, overall_decision,
    # forward_sim, target_application, debate_triggered, debate_log,
    # final_verdict). These are what Person 3 + Person 4 read.
    schema = LotState.model_json_schema(mode="serialization")
    OUT.write_text(json.dumps(schema, indent=2), encoding="utf-8")
    print(f"Wrote {OUT}  ({len(schema.get('$defs', {}))} sub-schemas, "
          f"{OUT.stat().st_size:,} bytes)")


if __name__ == "__main__":
    main()
