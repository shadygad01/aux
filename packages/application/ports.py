"""Ports implemented by outer infrastructure layers."""

from datetime import datetime
from typing import Protocol

from packages.domain import (
    Decision,
    DecisionSearch,
    DecisionVersion,
    Evidence,
    EvidenceDecision,
    HistoricalEvent,
    KnowledgeObject,
    LearningRecommendation,
    LearningRecord,
    MarketObservation,
    OpportunityTradeOutcome,
    PatternKnowledge,
    ReasoningDecision,
    ReasoningInput,
    ReasoningMistake,
    ResearchArtifact,
    SourceProfile,
    TradingDecision,
    TradingObservation,
)


class DecisionLogger(Protocol):
    def record(self, observation: MarketObservation, decision: Decision) -> None:
        """Persist or emit an important decision with its evidence context."""


class OpportunityRepository(Protocol):
    def append(self, observation: TradingObservation, decision: TradingDecision) -> None:
        """Durably append every evaluated opportunity and outcome state."""


class TradingDecisionLogger(Protocol):
    def record(self, observation: TradingObservation, decision: TradingDecision) -> None:
        """Emit a traceable trading decision with its evidence context."""


class OutcomeRepository(Protocol):
    def append_outcome(self, outcome: OpportunityTradeOutcome) -> None:
        """Append a later researched outcome without mutating the original evaluation."""


class EvidenceDecisionAudit(Protocol):
    def record(self, evidence: tuple[Evidence, ...], decision: EvidenceDecision) -> None:
        """Durably record each reproducible evidence decision."""


class LearningRepository(Protocol):
    def append_record(self, record: LearningRecord) -> None:
        """Append a complete evaluation and outcome record."""

    def append_artifact(self, artifact: ResearchArtifact) -> None:
        """Append a hypothesis or supporting-evidence artifact."""

    def append_recommendation(self, recommendation: LearningRecommendation) -> None:
        """Append an approval-required research recommendation."""


class KnowledgeRepository(Protocol):
    def append_source(self, source: SourceProfile) -> None: ...

    def append_knowledge(self, knowledge: KnowledgeObject) -> None: ...

    def append_event(self, event: HistoricalEvent) -> None: ...

    def append_pattern(self, pattern: PatternKnowledge) -> None: ...

    def sources(self) -> tuple[SourceProfile, ...]: ...

    def knowledge(self) -> tuple[KnowledgeObject, ...]: ...

    def events(self) -> tuple[HistoricalEvent, ...]: ...

    def patterns(self) -> tuple[PatternKnowledge, ...]: ...


class EvidenceEvaluator(Protocol):
    def evaluate(
        self, evidence: tuple[Evidence, ...], evaluated_at: datetime
    ) -> EvidenceDecision: ...


class ReasoningAudit(Protocol):
    def append_path(self, reasoning_input: ReasoningInput, decision: ReasoningDecision) -> None: ...

    def append_mistake(self, mistake: ReasoningMistake) -> None: ...


class DecisionIdPort(Protocol):
    def next_id(self, timestamp: datetime) -> str: ...


class DecisionArchive(Protocol):
    def append(self, decision: DecisionVersion) -> None: ...

    def latest(self, decision_id: str) -> DecisionVersion | None: ...

    def search(self, query: DecisionSearch) -> tuple[DecisionVersion, ...]: ...
