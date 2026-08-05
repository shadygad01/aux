"""Generate technical_debt.json — parses docs/technical-debt-register.md markdown table."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from .envelope import build_envelope

GENERATOR = "publish.generators.technical_debt"
SCHEMA_VERSION = "1.0.0"
SOURCE_PATH = Path(__file__).parent.parent.parent / "docs" / "technical-debt-register.md"

_PRIORITY_ORDER = {"P0": 0, "P1": 1, "P2": 2}


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
        # Skip separator row (contains dashes)
        if all(re.match(r"^-+$", c) for c in cells if c):
            continue
        if len(cells) == len(headers):
            rows.append(dict(zip(headers, cells, strict=False)))

    return rows


def generate(output_path: Path) -> None:
    """Parse technical-debt-register.md and write technical_debt.json."""
    text = SOURCE_PATH.read_text(encoding="utf-8")
    raw_rows = _parse_table(text)

    items = []
    for row in raw_rows:
        debt_id = row.get("id", "").strip()
        if not debt_id:
            continue
        priority = row.get("priority", "").strip()
        items.append(
            {
                "id": debt_id,
                "reason": row.get("reason", "").strip(),
                "impact": row.get("impact", "").strip(),
                "owner": row.get("owner", "").strip(),
                "priority": priority,
                "estimated_cost": row.get("estimated_cost", "").strip(),
                "target_sprint": row.get("target_sprint", "").strip(),
                "removal_strategy": row.get("removal_strategy", "").strip(),
            }
        )

    items.sort(key=lambda i: (_PRIORITY_ORDER.get(i["priority"], 99), i["id"]))

    p0_count = sum(1 for i in items if i["priority"] == "P0")
    p1_count = sum(1 for i in items if i["priority"] == "P1")

    payload = {
        "total_items": len(items),
        "p0_blocking_count": p0_count,
        "p1_scale_count": p1_count,
        "items": items,
    }

    artifact = build_envelope(GENERATOR, SCHEMA_VERSION, payload)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(artifact, indent=2), encoding="utf-8")
    print(f"  [OK] {output_path.name}")
