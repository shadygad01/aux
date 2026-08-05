"""Reasoning capability: create one complete governed reasoning path."""

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
from packages.domain import (
    CurrentMarketState,
    ReasoningDecision,
    ReasoningInput,
    RegimeInterpretation,
)


class ReasoningPort(Protocol):
    def evaluate(
        self,
        value: ReasoningInput,
        state: CurrentMarketState,
        interpretations: tuple[RegimeInterpretation, ...],
        evaluated_at: datetime,
    ) -> ReasoningDecision: ...


class ReasoningCapability:
    name = "reasoning"

    def __init__(self, reasoner: ReasoningPort, telemetry: CapabilityTelemetry) -> None:
        self._reasoner = reasoner
        self._telemetry = telemetry

    def reason(
        self,
        value: ReasoningInput,
        state: CurrentMarketState,
        interpretations: tuple[RegimeInterpretation, ...],
        evaluated_at: datetime,
    ) -> ReasoningDecision:
        if not state.is_current(evaluated_at):
            raise ValueError("reasoning requires a current market state")
        expected = {item.evidence_id for item in value.evidence}
        interpreted = {item.evidence_id for item in interpretations}
        if expected != interpreted or any(
            item.regime_id != state.regime.regime_id for item in interpretations
        ):
            raise ValueError("reasoning requires current-regime interpretation for every evidence")
        decision = self._reasoner.evaluate(value, state, interpretations, evaluated_at)
        self._telemetry.metric(CapabilityMetric(self.name, "reasoning_paths", 1, "paths"))
        self._telemetry.log(
            CapabilityLog(
                self.name,
                LogLevel.INFO,
                "reasoning_completed",
                (("reasoning_id", value.reasoning_id),),
            )
        )
        return decision

    def health(self, checked_at: datetime) -> CapabilityHealth:
        return CapabilityHealth(self.name, HealthState.HEALTHY, checked_at, "reasoner configured")
