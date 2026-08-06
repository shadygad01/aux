"""Generate macro_evidence.json — publishes canonical macro evidence items."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from packages.infrastructure.macro_collectors import MacroCollector

from .envelope import build_envelope

GENERATOR = "publish.generators.macro_evidence"
SCHEMA_VERSION = "1.0.0"


def generate(output_path: Path) -> None:
    """Generate canonical macro_evidence.json artifact."""
    now = datetime.now(UTC)
    collector = MacroCollector(timeout_seconds=2)
    ctx = collector.acquire_macro_context(now)
    assessment = collector.evaluate_macro_assessment(ctx, now)

    evidence_items = [
        {
            "evidence_id": f"EVD-MACRO-{idx + 1:02d}",
            "source": "canonical-macro-collector",
            "category": "MACRO_INTELLIGENCE",
            "finding": item,
            "confidence": 0.90,
            "observed_at": now.isoformat(),
        }
        for idx, item in enumerate(assessment.evidence)
    ]

    statement = (
        "Canonical Macro Evidence documents individual macro intelligence findings "
        "(DXY, Yields, News, Liquidity Reference Levels)."
    )

    payload = {
        "statement": statement,
        "evidence": evidence_items,
    }

    artifact = build_envelope(GENERATOR, SCHEMA_VERSION, payload)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(artifact, indent=2), encoding="utf-8")
    print(f"  [OK] {output_path.name}")
