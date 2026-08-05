"""Generate institutional_health.json — derived from readiness and technical debt artifacts."""

from __future__ import annotations

import json
from pathlib import Path

from .envelope import build_envelope

GENERATOR = "publish.generators.health"
SCHEMA_VERSION = "1.0.0"


def generate(
    output_path: Path,
    artifacts_dir: Path,
) -> None:
    """Compute institutional health from already-generated sibling artifacts."""
    readiness_path = artifacts_dir / "capability_readiness.json"
    debt_path = artifacts_dir / "technical_debt.json"

    readiness_artifact: dict = json.loads(readiness_path.read_text(encoding="utf-8"))
    debt_artifact: dict = json.loads(debt_path.read_text(encoding="utf-8"))

    readiness_payload = readiness_artifact["payload"]
    debt_payload = debt_artifact["payload"]

    capabilities = readiness_payload.get("capabilities", [])
    scores = [c["score"] for c in capabilities]
    project_score = readiness_payload.get("project_score", 0)
    average_capability_score = round(sum(scores) / len(scores), 1) if scores else 0.0

    p0_items = [i for i in debt_payload.get("items", []) if i["priority"] == "P0"]
    critical_blockers = [i["reason"] for i in p0_items]

    # Institutional readiness band
    if project_score >= 80:
        readiness_band = "VALIDATION_READY"
    elif project_score >= 60:
        readiness_band = "IMPLEMENTATION_READY"
    elif project_score >= 40:
        readiness_band = "ARCHITECTURE_READY"
    elif project_score >= 20:
        readiness_band = "PROTOTYPE"
    else:
        readiness_band = "NO_PROTOTYPE"

    capabilities_by_milestone: dict[str, list[str]] = {}
    for cap in capabilities:
        milestone = cap["milestone"]
        capabilities_by_milestone.setdefault(milestone, []).append(cap["capability"])

    payload = {
        "project_score": project_score,
        "readiness_band": readiness_band,
        "average_capability_score": average_capability_score,
        "capability_count": len(capabilities),
        "p0_debt_count": debt_payload.get("p0_blocking_count", 0),
        "p1_debt_count": debt_payload.get("p1_scale_count", 0),
        "total_debt_items": debt_payload.get("total_items", 0),
        "critical_blockers": critical_blockers,
        "capabilities_by_milestone": capabilities_by_milestone,
        "snapshot_id": readiness_payload.get("snapshot_id", ""),
        "assessed_at": readiness_payload.get("assessed_at", ""),
    }

    artifact = build_envelope(GENERATOR, SCHEMA_VERSION, payload)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(artifact, indent=2), encoding="utf-8")
    print(f"  [OK] {output_path.name}")
