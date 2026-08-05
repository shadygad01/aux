"""Evidence capability: evaluate one expiring evidence snapshot."""

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
from packages.domain import CurrentMarketState, Evidence, EvidenceDecision, RegimeInterpretation


class EvidenceEvaluatorPort(Protocol):
    def evaluate(
        self,
        evidence: tuple[Evidence, ...],
        evaluated_at: datetime,
        state: CurrentMarketState,
        interpretations: tuple[RegimeInterpretation, ...],
    ) -> EvidenceDecision: ...


class EvidenceCapability:
    name = "evidence"

    def __init__(self, evaluator: EvidenceEvaluatorPort, telemetry: CapabilityTelemetry) -> None:
        self._evaluator = evaluator
        self._telemetry = telemetry

    def evaluate(
        self,
        evidence: tuple[Evidence, ...],
        state: CurrentMarketState,
        interpretations: tuple[RegimeInterpretation, ...],
        evaluated_at: datetime,
    ) -> EvidenceDecision:
        self._validate_state(evidence, state, interpretations, evaluated_at)
        decision = self._evaluator.evaluate(evidence, evaluated_at, state, interpretations)
        self._telemetry.metric(
            CapabilityMetric(self.name, "evidence_items", len(evidence), "items")
        )
        self._telemetry.log(
            CapabilityLog(
                self.name,
                LogLevel.INFO,
                "evidence_evaluated",
                (("recommendation", decision.recommendation.value),),
            )
        )
        return decision

    @staticmethod
    def _validate_state(
        evidence: tuple[Evidence, ...],
        state: CurrentMarketState,
        interpretations: tuple[RegimeInterpretation, ...],
        evaluated_at: datetime,
    ) -> None:
        if not state.is_current(evaluated_at):
            raise ValueError("analysis requires a current market state")
        expected = {item.evidence_id for item in evidence}
        interpreted = {item.evidence_id for item in interpretations}
        if expected != interpreted or len(interpretations) != len(expected):
            raise ValueError("every evidence item requires exactly one regime interpretation")
        if any(item.regime_id != state.regime.regime_id for item in interpretations):
            raise ValueError("evidence interpretations must reference the current regime")

    def health(self, checked_at: datetime) -> CapabilityHealth:
        return CapabilityHealth(self.name, HealthState.HEALTHY, checked_at, "evaluator configured")
