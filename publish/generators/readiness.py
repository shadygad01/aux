"""Generate capability_readiness.json — re-wraps existing readiness-history.json artifact."""

from __future__ import annotations

import json
from pathlib import Path

from .envelope import build_envelope

GENERATOR = "publish.generators.readiness"
SCHEMA_VERSION = "1.0.0"
SOURCE_PATH = Path(__file__).parent.parent.parent / "docs" / "readiness-history.json"

# Milestone labels for the governed milestone scale
_MILESTONE_LABELS: dict[int, str] = {
    0: "No Prototype",
    20: "Prototype",
    40: "Architecture Ready",
    60: "Implementation Ready",
    80: "Validation Ready",
    100: "Production Ready",
}


def _milestone_label(score: int) -> str:
    for threshold in sorted(_MILESTONE_LABELS, reverse=True):
        if score >= threshold:
            return _MILESTONE_LABELS[threshold]
    return "No Prototype"


def generate(output_path: Path) -> None:
    """Read docs/readiness-history.json and produce capability_readiness.json."""
    source: dict = json.loads(SOURCE_PATH.read_text(encoding="utf-8"))
    snapshots = source.get("snapshots", [])

    # Take the latest snapshot
    latest = snapshots[-1] if snapshots else {}
    records = latest.get("records", [])

    enriched_records = [
        {
            "capability": r["capability"],
            "score": r["score"],
            "milestone": _milestone_label(r["score"]),
            "reason": r["reason"],
            "evidence": r["evidence"],
        }
        for r in records
    ]

    project_score = latest.get("project_score", 0)
    payload = {
        "snapshot_id": latest.get("snapshot_id", ""),
        "sprint": latest.get("sprint", ""),
        "assessed_at": latest.get("assessed_at", ""),
        "assessor": latest.get("assessor", ""),
        "formula": latest.get("formula", ""),
        "project_score": project_score,
        "project_milestone": _milestone_label(project_score),
        "capabilities": enriched_records,
    }

    artifact = build_envelope(GENERATOR, SCHEMA_VERSION, payload)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(artifact, indent=2), encoding="utf-8")
    print(f"  [OK] {output_path.name}")
