"""Generate macro_assessment.json — publishes canonical MacroAssessment artifact."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from packages.infrastructure.macro_collectors import MacroCollector

from .envelope import build_envelope

GENERATOR = "publish.generators.macro_assessment"
SCHEMA_VERSION = "1.0.0"


def generate(output_path: Path) -> None:
    """Generate canonical macro_assessment.json artifact."""
    now = datetime.now(UTC)
    collector = MacroCollector(timeout_seconds=2)
    ctx = collector.acquire_macro_context(now)
    assessment = collector.evaluate_macro_assessment(ctx, now)

    statement = (
        "Canonical Macro Assessment evaluates macro context to produce macro score, "
        "confidence modifier, and fail-closed WAIT signals."
    )

    payload = {
        "statement": statement,
        "macro_assessment": assessment.to_dict(),
    }

    artifact = build_envelope(GENERATOR, SCHEMA_VERSION, payload)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(artifact, indent=2), encoding="utf-8")
    print(f"  [OK] {output_path.name}")
