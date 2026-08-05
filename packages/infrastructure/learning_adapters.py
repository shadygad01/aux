"""Append-only JSON Lines research repository."""

import json
from pathlib import Path

from packages.domain import LearningRecommendation, LearningRecord, ResearchArtifact

from .json_contracts import JsonObject


def learning_record_to_json(record: LearningRecord) -> JsonObject:
    return {
        "record_id": record.record_id,
        "decision_audit_id": record.decision_audit_id,
        "timestamp": record.timestamp.isoformat(),
        "market_snapshot": {
            "xauusd_price": record.market_snapshot.xauusd_price,
            "captured_at": record.market_snapshot.captured_at.isoformat(),
            "source": record.market_snapshot.source,
            "reference": record.market_snapshot.reference,
        },
        "bias": [
            {
                "horizon": item.horizon.value,
                "bias": item.bias.value,
                "reasoning": item.reasoning,
            }
            for item in record.biases
        ],
        "trade_quality": record.trade_quality,
        "location": record.location.value,
        "premium_discount": record.location.value,
        "liquidity": list(record.liquidity),
        "macd": record.macd,
        "news": list(record.news),
        "macro": record.macro,
        "dxy": record.dxy,
        "real_yields": record.real_yields,
        "session": record.session,
        "smc_evidence": list(record.smc_evidence),
        "supporting_evidence": list(record.supporting_evidence),
        "contradicting_evidence": list(record.contradicting_evidence),
        "decision": record.decision.value,
        "outcome": record.outcome.value,
        "maximum_favorable_excursion": record.maximum_favorable_excursion,
        "maximum_adverse_excursion": record.maximum_adverse_excursion,
        "learning_notes": list(record.learning_notes),
        "what_changed_after": record.what_changed_after,
    }


def _artifact_to_json(artifact: ResearchArtifact) -> JsonObject:
    return {
        "artifact_id": artifact.artifact_id,
        "source_record_id": artifact.source_record_id,
        "kind": artifact.kind.value,
        "question": artifact.question,
        "explanation": artifact.explanation,
        "knowledge_level": artifact.knowledge_level.value,
    }


def _recommendation_to_json(recommendation: LearningRecommendation) -> JsonObject:
    statistics = recommendation.historical_statistics
    return {
        "recommendation_id": recommendation.recommendation_id,
        "current_rule": recommendation.current_rule,
        "suggested_improvement": recommendation.suggested_improvement,
        "supporting_evidence": list(recommendation.supporting_evidence),
        "historical_statistics": {
            "evidence_combination": list(statistics.evidence_combination),
            "sample_size": statistics.sample_size,
            "winning": statistics.winning,
            "losing": statistics.losing,
            "win_rate": statistics.win_rate,
        },
        "expected_impact": recommendation.expected_impact,
        "migration_risk": recommendation.migration_risk,
        "confidence_level": recommendation.confidence.score,
        "confidence_inputs": {
            "historical_performance": recommendation.confidence.historical_performance,
            "repeatability": recommendation.confidence.repeatability,
            "evidence_quality": recommendation.confidence.evidence_quality,
            "data_quality": recommendation.confidence.data_quality,
            "sample_size_adequacy": recommendation.confidence.sample_size_adequacy,
        },
        "status": recommendation.status.value,
        "requires_approval": recommendation.requires_approval,
    }


class JsonLinesLearningRepository:
    def __init__(self, path: Path) -> None:
        self._path = path

    def append_record(self, record: LearningRecord) -> None:
        self._append("learning_record", learning_record_to_json(record))

    def append_artifact(self, artifact: ResearchArtifact) -> None:
        self._append("research_artifact", _artifact_to_json(artifact))

    def append_recommendation(self, recommendation: LearningRecommendation) -> None:
        self._append("learning_recommendation", _recommendation_to_json(recommendation))

    def _append(self, event: str, payload: JsonObject) -> None:
        record: JsonObject = {"event": event, "payload": payload}
        self._path.parent.mkdir(parents=True, exist_ok=True)
        with self._path.open("a", encoding="utf-8", newline="\n") as stream:
            stream.write(json.dumps(record, separators=(",", ":")))
            stream.write("\n")
