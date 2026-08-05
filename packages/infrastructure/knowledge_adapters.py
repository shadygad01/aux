"""Append-only institutional knowledge journal with an in-process query index."""

import json
from pathlib import Path

from packages.domain import HistoricalEvent, KnowledgeObject, PatternKnowledge, SourceProfile

from .json_contracts import JsonObject


def source_to_json(source: SourceProfile) -> JsonObject:
    return {
        "source_id": source.source_id,
        "name": source.name,
        "source_type": source.source_type.value,
        "reliability": source.reliability,
        "authority": source.authority,
        "historical_accuracy": source.historical_accuracy,
        "bias_risk": source.bias_risk,
        "transparency": source.transparency,
        "last_review": source.last_review.isoformat(),
        "review_interval_seconds": source.review_interval.total_seconds(),
        "evidence_references": list(source.evidence_references),
    }


def knowledge_to_json(knowledge: KnowledgeObject) -> JsonObject:
    return {
        "knowledge_id": knowledge.knowledge_id,
        "revision": knowledge.revision,
        "title": knowledge.title,
        "category": knowledge.category.value,
        "description": knowledge.description,
        "source_ids": list(knowledge.source_ids),
        "reliability": knowledge.reliability,
        "confidence": knowledge.confidence,
        "historical_validation": knowledge.historical_validation,
        "last_review": knowledge.last_review.isoformat(),
        "review_interval_seconds": knowledge.review_interval.total_seconds(),
        "status": knowledge.status.value,
        "supporting_evidence": list(knowledge.supporting_evidence),
        "contradicting_evidence": list(knowledge.contradicting_evidence),
    }


def event_to_json(event: HistoricalEvent) -> JsonObject:
    return {
        "event_id": event.event_id,
        "title": event.title,
        "categories": [category.value for category in event.categories],
        "timeline": [
            {"timestamp": moment.timestamp.isoformat(), "description": moment.description}
            for moment in event.timeline
        ],
        "market_reaction": event.market_reaction,
        "gold_behaviour": event.gold_behaviour,
        "dollar_behaviour": event.dollar_behaviour,
        "yield_behaviour": event.yield_behaviour,
        "lessons_learned": list(event.lessons_learned),
        "gold_reaction_percent": event.gold_reaction_percent,
        "gold_ignored_dxy": event.gold_ignored_dxy,
        "yields_dominated_gold": event.yields_dominated_gold,
        "evidence_references": list(event.evidence_references),
    }


def pattern_to_json(pattern: PatternKnowledge) -> JsonObject:
    return {
        "pattern_id": pattern.pattern_id,
        "title": pattern.title,
        "status": pattern.status.value,
        "conditions": list(pattern.conditions),
        "sample_size": pattern.sample_size,
        "win_rate": pattern.win_rate,
        "failure_rate": pattern.failure_rate,
        "known_weaknesses": list(pattern.known_weaknesses),
        "best_sessions": list(pattern.best_sessions),
        "worst_sessions": list(pattern.worst_sessions),
        "evidence_references": list(pattern.evidence_references),
        "last_review": pattern.last_review.isoformat(),
        "review_interval_seconds": pattern.review_interval.total_seconds(),
    }


class InMemoryKnowledgeRepository:
    def __init__(self) -> None:
        self._sources: list[SourceProfile] = []
        self._knowledge: list[KnowledgeObject] = []
        self._events: list[HistoricalEvent] = []
        self._patterns: list[PatternKnowledge] = []

    def append_source(self, source: SourceProfile) -> None:
        self._sources.append(source)

    def append_knowledge(self, knowledge: KnowledgeObject) -> None:
        self._knowledge.append(knowledge)

    def append_event(self, event: HistoricalEvent) -> None:
        self._events.append(event)

    def append_pattern(self, pattern: PatternKnowledge) -> None:
        self._patterns.append(pattern)

    def sources(self) -> tuple[SourceProfile, ...]:
        return tuple(self._sources)

    def knowledge(self) -> tuple[KnowledgeObject, ...]:
        return tuple(self._knowledge)

    def events(self) -> tuple[HistoricalEvent, ...]:
        return tuple(self._events)

    def patterns(self) -> tuple[PatternKnowledge, ...]:
        return tuple(self._patterns)


class JsonLinesKnowledgeRepository(InMemoryKnowledgeRepository):
    """Durable append journal plus a typed index for the current process."""

    def __init__(self, path: Path) -> None:
        super().__init__()
        self._path = path

    def append_source(self, source: SourceProfile) -> None:
        self._append("source", source_to_json(source))
        super().append_source(source)

    def append_knowledge(self, knowledge: KnowledgeObject) -> None:
        self._append("knowledge", knowledge_to_json(knowledge))
        super().append_knowledge(knowledge)

    def append_event(self, event: HistoricalEvent) -> None:
        self._append("event", event_to_json(event))
        super().append_event(event)

    def append_pattern(self, pattern: PatternKnowledge) -> None:
        self._append("pattern", pattern_to_json(pattern))
        super().append_pattern(pattern)

    def _append(self, record_type: str, payload: JsonObject) -> None:
        record: JsonObject = {"record_type": record_type, "payload": payload}
        self._path.parent.mkdir(parents=True, exist_ok=True)
        with self._path.open("a", encoding="utf-8", newline="\n") as stream:
            stream.write(json.dumps(record, separators=(",", ":")))
            stream.write("\n")
