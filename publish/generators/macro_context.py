"""Generate macro_context.json — publishes canonical MacroContext artifact."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from packages.infrastructure.macro_collectors import MacroCollector

from .envelope import build_envelope

GENERATOR = "publish.generators.macro_context"
SCHEMA_VERSION = "1.0.0"


def generate(output_path: Path) -> None:
    """Generate canonical macro_context.json artifact."""
    now = datetime(2026, 8, 5, 12, 0, 0, tzinfo=UTC)
    collector = MacroCollector(timeout_seconds=2)
    ctx = collector.acquire_macro_context(now)

    statement = (
        "Canonical Macro Context describes the institutional macro environment "
        "(DXY, US10Y/US02Y yields, news, liquidity reference levels)."
    )

    payload = {
        "statement": statement,
        "macro_context": ctx.to_dict(),
    }

    artifact = build_envelope(GENERATOR, SCHEMA_VERSION, payload)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(artifact, indent=2), encoding="utf-8")
    print(f"  [OK] {output_path.name}")
