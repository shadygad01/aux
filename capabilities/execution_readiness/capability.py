"""Execution Readiness capability implementation."""

from __future__ import annotations

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
    DecisionVerdict,
    ExecutionReadiness,
    MacroAssessment,
    MarketObservation,
)


class ExecutionReadinessProvider(Protocol):
    def evaluate(
        self,
        observation: MarketObservation,
        verdict: DecisionVerdict,
        setup_quality_score: int,
        macro_assessment: MacroAssessment | None,
        evaluated_at: datetime,
    ) -> ExecutionReadiness: ...


class ExecutionReadinessCapability:
    name = "execution_readiness"

    def __init__(
        self, provider: ExecutionReadinessProvider, telemetry: CapabilityTelemetry
    ) -> None:
        self._provider = provider
        self._telemetry = telemetry

    def evaluate_readiness(
        self,
        observation: MarketObservation,
        verdict: DecisionVerdict,
        setup_quality_score: int,
        macro_assessment: MacroAssessment | None,
        at: datetime,
    ) -> ExecutionReadiness:
        readiness = self._provider.evaluate(
            observation, verdict, setup_quality_score, macro_assessment, at
        )
        self._telemetry.metric(CapabilityMetric(self.name, "readiness_evaluations", 1, "count"))
        self._telemetry.log(
            CapabilityLog(
                self.name,
                LogLevel.INFO,
                "readiness_evaluated",
                (
                    ("status", str(readiness.status)),
                    ("score", str(readiness.readiness_score)),
                ),
            )
        )
        return readiness

    def health(self, checked_at: datetime) -> CapabilityHealth:
        msg = "execution readiness engine active"
        return CapabilityHealth(self.name, HealthState.HEALTHY, checked_at, msg)
