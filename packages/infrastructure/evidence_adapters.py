"""Version 3 JSON output and append-only evidence-decision audit."""

import json
from pathlib import Path

from packages.domain import Evidence, EvidenceDecision

from .json_contracts import JsonObject


def evidence_decision_to_json(decision: EvidenceDecision) -> JsonObject:
    return {
        "contract_version": decision.contract_version,
        "recommendation": decision.recommendation.value,
        "trade_quality": decision.trade_quality,
        "confidence": decision.confidence,
        "why": list(decision.why),
        "why_not": list(decision.why_not),
        "missing": list(decision.missing),
        "what_would_change": list(decision.what_would_change),
        "evidence": [
            {
                "evidence_id": item.evidence_id,
                "kind": item.kind.value,
                "direction": item.direction.value,
                "freshness": item.freshness,
                "effective_weight": item.effective_weight,
                "expires_at": item.expires_at.isoformat(),
                "rationale": item.rationale,
            }
            for item in decision.evidence
        ],
        "evaluated_at": decision.evaluated_at.isoformat(),
        "policy_version": decision.policy_version,
    }


def _evidence_to_json(item: Evidence) -> JsonObject:
    return {
        "evidence_id": item.evidence_id,
        "kind": item.kind.value,
        "direction": item.direction.value,
        "observed_at": item.observed_at.isoformat(),
        "time_to_live_seconds": item.time_to_live.total_seconds(),
        "strength": item.strength,
        "reliability": item.reliability,
        "importance": item.importance,
        "historical_performance": item.historical_performance,
        "confidence": item.confidence,
        "rationale": item.rationale,
        "source": item.source,
        "forces_wait": item.forces_wait,
    }


class JsonLinesEvidenceDecisionAudit:
    def __init__(self, path: Path) -> None:
        self._path = path

    def record(self, evidence: tuple[Evidence, ...], decision: EvidenceDecision) -> None:
        record: JsonObject = {
            "event": "evidence_decision_evaluated",
            "evidence": [_evidence_to_json(item) for item in evidence],
            "decision": evidence_decision_to_json(decision),
        }
        self._path.parent.mkdir(parents=True, exist_ok=True)
        with self._path.open("a", encoding="utf-8", newline="\n") as stream:
            stream.write(json.dumps(record, separators=(",", ":")))
            stream.write("\n")
