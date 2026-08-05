"""Institutional knowledge governance, ranking, review, and structured questions."""

from collections.abc import Callable
from dataclasses import dataclass, replace
from datetime import datetime

from packages.domain import (
    HistoricalEvent,
    InstitutionalQuestion,
    KnowledgeAnswer,
    KnowledgeCategory,
    KnowledgeObject,
    KnowledgeStatus,
    PatternKnowledge,
    RankedSource,
    SourceProfile,
)

from .errors import DecisionEvaluationError
from .ports import KnowledgeRepository


@dataclass(frozen=True, slots=True)
class KnowledgePolicy:
    version: str = "knowledge-v1-hypothesis-1"
    reliability_weight: float = 0.25
    freshness_weight: float = 0.15
    authority_weight: float = 0.20
    historical_accuracy_weight: float = 0.20
    transparency_weight: float = 0.15
    inverse_bias_weight: float = 0.05
    strongest_event_limit: int = 10

    def __post_init__(self) -> None:
        weights = (
            self.reliability_weight,
            self.freshness_weight,
            self.authority_weight,
            self.historical_accuracy_weight,
            self.transparency_weight,
            self.inverse_bias_weight,
        )
        if any(weight < 0 for weight in weights) or abs(sum(weights) - 1) > 1e-9:
            raise ValueError("source-ranking weights must be non-negative and total one")
        if self.strongest_event_limit <= 0:
            raise ValueError("strongest_event_limit must be positive")


class InstitutionalKnowledgeBase:
    _TRANSITIONS = {
        KnowledgeStatus.OBSERVATION: KnowledgeStatus.HYPOTHESIS,
        KnowledgeStatus.HYPOTHESIS: KnowledgeStatus.VALIDATED,
        KnowledgeStatus.VALIDATED: KnowledgeStatus.INSTITUTIONAL_RULE,
        KnowledgeStatus.INSTITUTIONAL_RULE: KnowledgeStatus.DEPRECATED,
    }

    def __init__(self, policy: KnowledgePolicy, repository: KnowledgeRepository) -> None:
        self._policy = policy
        self._repository = repository

    def register_source(self, source: SourceProfile) -> None:
        self._persist("source", source.source_id, lambda: self._repository.append_source(source))

    def register_knowledge(self, knowledge: KnowledgeObject) -> None:
        source_ids = {source.source_id for source in self._repository.sources()}
        unknown = set(knowledge.source_ids) - source_ids
        if unknown:
            raise ValueError(f"knowledge references unknown sources: {sorted(unknown)}")
        self._persist(
            "knowledge",
            knowledge.knowledge_id,
            lambda: self._repository.append_knowledge(knowledge),
        )

    def register_event(self, event: HistoricalEvent) -> None:
        self._persist("event", event.event_id, lambda: self._repository.append_event(event))

    def register_pattern(self, pattern: PatternKnowledge) -> None:
        self._persist(
            "pattern", pattern.pattern_id, lambda: self._repository.append_pattern(pattern)
        )

    def transition(
        self,
        knowledge: KnowledgeObject,
        target: KnowledgeStatus,
        reviewed_at: datetime,
        historical_validation: str,
        supporting_evidence: tuple[str, ...],
    ) -> KnowledgeObject:
        expected = self._TRANSITIONS.get(knowledge.status)
        if target is not expected:
            raise ValueError(
                f"invalid knowledge transition {knowledge.status.value} -> {target.value}"
            )
        revision = replace(
            knowledge,
            revision=knowledge.revision + 1,
            status=target,
            last_review=reviewed_at,
            historical_validation=historical_validation,
            supporting_evidence=supporting_evidence,
        )
        self.register_knowledge(revision)
        return revision

    def rank_sources(self, evaluated_at: datetime) -> tuple[RankedSource, ...]:
        scored: list[tuple[SourceProfile, float, float]] = []
        for source in self._repository.sources():
            freshness = source.freshness(evaluated_at)
            score = (
                source.reliability * self._policy.reliability_weight
                + freshness * self._policy.freshness_weight
                + source.authority * self._policy.authority_weight
                + source.historical_accuracy * self._policy.historical_accuracy_weight
                + source.transparency * self._policy.transparency_weight
                + (1 - source.bias_risk) * self._policy.inverse_bias_weight
            )
            scored.append((source, score, freshness))
        ordered = sorted(scored, key=lambda item: (-item[1], item[0].source_id))
        return tuple(
            RankedSource(source.source_id, round(score, 6), round(freshness, 6), rank)
            for rank, (source, score, freshness) in enumerate(ordered, start=1)
        )

    def due_for_review(self, evaluated_at: datetime) -> tuple[KnowledgeObject, ...]:
        latest: dict[str, KnowledgeObject] = {}
        for item in self._repository.knowledge():
            current = latest.get(item.knowledge_id)
            if current is None or item.revision > current.revision:
                latest[item.knowledge_id] = item
        return tuple(
            sorted(
                (item for item in latest.values() if item.review_due(evaluated_at)),
                key=lambda item: item.knowledge_id,
            )
        )

    def answer(self, question: InstitutionalQuestion) -> KnowledgeAnswer:
        if question is InstitutionalQuestion.GOLD_IGNORED_DXY:
            return self._event_answer(question, lambda event: event.gold_ignored_dxy)
        if question is InstitutionalQuestion.YIELDS_DOMINATED_GOLD:
            return self._event_answer(question, lambda event: event.yields_dominated_gold)
        if question is InstitutionalQuestion.STRONGEST_MACRO_REVERSALS:
            macro_categories = {
                KnowledgeCategory.MACRO_ECONOMICS,
                KnowledgeCategory.FEDERAL_RESERVE,
                KnowledgeCategory.INFLATION,
                KnowledgeCategory.EMPLOYMENT,
                KnowledgeCategory.INTEREST_RATES,
            }
            events = sorted(
                (
                    event
                    for event in self._repository.events()
                    if set(event.categories).intersection(macro_categories)
                ),
                key=lambda event: abs(event.gold_reaction_percent),
                reverse=True,
            )[: self._policy.strongest_event_limit]
            return self._events_to_answer(question, tuple(events))
        tag = "premium" if question is InstitutionalQuestion.PREMIUM_FAILURE_RATE else "sweep"
        return self._pattern_failure_answer(question, tag)

    def _event_answer(
        self, question: InstitutionalQuestion, predicate: Callable[[HistoricalEvent], bool]
    ) -> KnowledgeAnswer:
        events = tuple(event for event in self._repository.events() if predicate(event))
        return self._events_to_answer(question, events)

    @staticmethod
    def _events_to_answer(
        question: InstitutionalQuestion, events: tuple[HistoricalEvent, ...]
    ) -> KnowledgeAnswer:
        references = tuple(
            dict.fromkeys(ref for event in events for ref in event.evidence_references)
        )
        summary = (
            f"Found {len(events)} evidence-backed historical events."
            if events
            else "No evidence-backed historical events answer this question."
        )
        statistics = tuple(
            f"{event.event_id}: gold reaction {event.gold_reaction_percent:.4f}%"
            for event in events
        )
        return KnowledgeAnswer(
            question, summary, tuple(event.event_id for event in events), statistics, references
        )

    def _pattern_failure_answer(self, question: InstitutionalQuestion, tag: str) -> KnowledgeAnswer:
        accepted_statuses = {KnowledgeStatus.VALIDATED, KnowledgeStatus.INSTITUTIONAL_RULE}
        patterns = tuple(
            pattern
            for pattern in self._repository.patterns()
            if pattern.status in accepted_statuses
            and tag in {condition.casefold() for condition in pattern.conditions}
        )
        sample_size = sum(pattern.sample_size for pattern in patterns)
        failures = sum(pattern.failure_rate * pattern.sample_size for pattern in patterns)
        failure_rate = failures / sample_size if sample_size else 0.0
        references = tuple(
            dict.fromkeys(ref for pattern in patterns for ref in pattern.evidence_references)
        )
        summary = (
            f"Observed failure rate {failure_rate:.4%} across {sample_size} samples."
            if sample_size
            else "No validated evidence-backed pattern samples answer this question."
        )
        return KnowledgeAnswer(
            question,
            summary,
            tuple(pattern.pattern_id for pattern in patterns),
            (f"sample_size={sample_size}", f"failure_rate={failure_rate:.6f}"),
            references,
        )

    @staticmethod
    def _persist(kind: str, identifier: str, operation: Callable[[], None]) -> None:
        try:
            operation()
        except Exception as error:
            raise DecisionEvaluationError(
                f"knowledge persistence failed; kind={kind}; id={identifier}"
            ) from error
