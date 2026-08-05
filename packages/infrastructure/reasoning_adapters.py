"""Append-only Version 4 reasoning-path and mistake audit."""

import json
from pathlib import Path

from packages.domain import ReasoningDecision, ReasoningInput, ReasoningMistake

from .json_contracts import JsonObject


def reasoning_decision_to_json(decision: ReasoningDecision) -> JsonObject:
    return {
        "contract_version": decision.contract_version,
        "reasoning_id": decision.reasoning_id,
        "recommendation": decision.recommendation.value,
        "trade_quality": decision.trade_quality,
        "reliability": decision.reliability,
        "what_is_happening": decision.what_is_happening,
        "why": list(decision.why),
        "supporting_evidence": list(decision.supporting_evidence),
        "contradicting_evidence": list(decision.contradicting_evidence),
        "missing_evidence": list(decision.missing_evidence),
        "alternative_explanations": list(decision.alternative_explanations),
        "historical_similarities": list(decision.historical_similarities),
        "what_would_invalidate": list(decision.what_would_invalidate),
        "what_would_improve": list(decision.what_would_improve),
        "stages": [
            {
                "stage": item.stage.value,
                "status": item.status.value,
                "explanation": item.explanation,
                "evidence_ids": list(item.evidence_ids),
            }
            for item in decision.stages
        ],
        "evaluated_at": decision.evaluated_at.isoformat(),
        "policy_version": decision.policy_version,
    }


def _reasoning_input_to_json(value: ReasoningInput) -> JsonObject:
    state = value.market_state
    return {
        "reasoning_id": value.reasoning_id,
        "market_state": {
            "state_id": state.state_id,
            "symbol": state.symbol,
            "captured_at": state.captured_at.isoformat(),
            "time_to_live_seconds": state.time_to_live.total_seconds(),
            "price": state.price,
            "location": state.location.value,
            "session": state.session,
            "volatility_regime": state.volatility_regime,
            "summary": state.summary,
            "alternative_explanations": list(state.alternative_explanations),
            "source": state.source,
        },
        "evidence": [
            {
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
            for item in value.evidence
        ],
        "knowledge": [
            {"knowledge_id": item.knowledge_id, "revision": item.revision}
            for item in value.knowledge
        ],
        "historical_context": [
            {
                "event_id": item.event.event_id,
                "similarity": item.similarity,
                "reasoning": item.reasoning,
                "evidence_references": list(item.evidence_references),
            }
            for item in value.historical_context
        ],
        "research_ids": [item.artifact_id for item in value.research],
        "learning_recommendation_ids": [
            item.recommendation_id for item in value.learning_suggestions
        ],
    }


class JsonLinesReasoningAudit:
    def __init__(self, path: Path) -> None:
        self._path = path

    def append_path(self, reasoning_input: ReasoningInput, decision: ReasoningDecision) -> None:
        payload: JsonObject = {
            "reasoning_input": _reasoning_input_to_json(reasoning_input),
            "decision": reasoning_decision_to_json(decision),
        }
        self._append("reasoning_path", payload)

    def append_mistake(self, mistake: ReasoningMistake) -> None:
        payload: JsonObject = {
            "mistake_id": mistake.mistake_id,
            "reasoning_id": mistake.reasoning_id,
            "recorded_at": mistake.recorded_at.isoformat(),
            "kind": mistake.kind.value,
            "description": mistake.description,
            "evidence_references": list(mistake.evidence_references),
            "corrective_hypothesis": mistake.corrective_hypothesis,
        }
        self._append("reasoning_mistake", payload)

    def _append(self, event: str, payload: JsonObject) -> None:
        record: JsonObject = {"event": event, "payload": payload}
        self._path.parent.mkdir(parents=True, exist_ok=True)
        with self._path.open("a", encoding="utf-8", newline="\n") as stream:
            stream.write(json.dumps(record, separators=(",", ":")))
            stream.write("\n")
