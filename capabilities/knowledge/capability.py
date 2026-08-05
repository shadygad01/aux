"""Knowledge capability: govern and query institutional knowledge."""

from datetime import datetime
from typing import Protocol

from capabilities.contracts import (
    CapabilityHealth,
    CapabilityLog,
    CapabilityMetric,
    CapabilityTelemetry,
    HealthState,
    LogLevel,
)
from packages.domain import InstitutionalQuestion, KnowledgeAnswer, KnowledgeObject, RankedSource


class KnowledgeServicePort(Protocol):
    def answer(self, question: InstitutionalQuestion) -> KnowledgeAnswer: ...

    def due_for_review(self, evaluated_at: datetime) -> tuple[KnowledgeObject, ...]: ...

    def rank_sources(self, evaluated_at: datetime) -> tuple[RankedSource, ...]: ...


class KnowledgeCapability:
    name = "knowledge"

    def __init__(
        self, knowledge_base: KnowledgeServicePort, telemetry: CapabilityTelemetry
    ) -> None:
        self._knowledge_base = knowledge_base
        self._telemetry = telemetry

    def answer(self, question: InstitutionalQuestion) -> KnowledgeAnswer:
        answer = self._knowledge_base.answer(question)
        self._telemetry.metric(
            CapabilityMetric(self.name, "answer_results", len(answer.result_ids), "objects")
        )
        self._telemetry.log(
            CapabilityLog(
                self.name, LogLevel.INFO, "question_answered", (("question", question.value),)
            )
        )
        return answer

    def due_for_review(self, evaluated_at: datetime) -> tuple[KnowledgeObject, ...]:
        return self._knowledge_base.due_for_review(evaluated_at)

    def rank_sources(self, evaluated_at: datetime) -> tuple[RankedSource, ...]:
        return self._knowledge_base.rank_sources(evaluated_at)

    def health(self, checked_at: datetime) -> CapabilityHealth:
        return CapabilityHealth(
            self.name, HealthState.HEALTHY, checked_at, "knowledge service configured"
        )
