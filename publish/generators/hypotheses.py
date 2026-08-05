"""Generate hypothesis_register.json — parses docs/hypothesis-register.md markdown table."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from .envelope import build_envelope

GENERATOR = "publish.generators.hypotheses"
SCHEMA_VERSION = "1.0.0"
SOURCE_PATH = Path(__file__).parent.parent.parent / "docs" / "hypothesis-register.md"

_STATUS_ORDER = {"UNVALIDATED": 0, "TESTING": 1, "SUPPORTED": 2, "REJECTED": 3}


def _parse_table(text: str) -> list[dict[str, Any]]:
    """Parse the markdown pipe table into a list of dicts."""
    rows = []
    in_table = False
    headers: list[str] = []

    for line in text.splitlines():
        stripped = line.strip()
        if not stripped.startswith("|"):
            if in_table:
                break
            continue
        cells = [c.strip() for c in stripped.strip("|").split("|")]
        if not headers:
            headers = [h.lower().replace(" ", "_") for h in cells]
            in_table = True
            continue
        if all(re.match(r"^-+$", c) for c in cells if c):
            continue
        if len(cells) == len(headers):
            rows.append(dict(zip(headers, cells, strict=False)))

    return rows


def generate(output_path: Path) -> None:
    """Parse hypothesis-register.md and write hypothesis_register.json."""
    text = SOURCE_PATH.read_text(encoding="utf-8")
    raw_rows = _parse_table(text)

    items = []
    for row in raw_rows:
        hyp_id = row.get("id", "").strip()
        if not hyp_id:
            continue
        status = row.get("status", "UNVALIDATED").strip()
        items.append(
            {
                "id": hyp_id,
                "hypothesis": row.get("hypothesis", "").strip(),
                "initial_implementation": row.get("initial_implementation", "").strip(),
                "status": status,
                "required_evidence": row.get("required_evidence", "").strip(),
            }
        )

    status_counts: dict[str, int] = {}
    for item in items:
        s = item["status"]
        status_counts[s] = status_counts.get(s, 0) + 1

    payload = {
        "total_hypotheses": len(items),
        "status_summary": status_counts,
        "hypotheses": items,
    }

    artifact = build_envelope(GENERATOR, SCHEMA_VERSION, payload)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(artifact, indent=2), encoding="utf-8")
    print(f"  [OK] {output_path.name}")
