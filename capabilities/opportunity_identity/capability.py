"""Opportunity Identity capability implementation."""

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
    ExecutionReadiness,
    MarketObservation,
    MarketThesis,
    OpportunityIdentity,
)


class OpportunityIdentityProvider(Protocol):
    def evaluate_opportunity(
        self,
        observation: MarketObservation,
        thesis: MarketThesis,
        readiness: ExecutionReadiness,
        evaluated_at: datetime,
    ) -> tuple[OpportunityIdentity, OpportunityIdentity | None]: ...


class OpportunityIdentityCapability:
    name = "opportunity_identity"

    def __init__(
        self, provider: OpportunityIdentityProvider, telemetry: CapabilityTelemetry
    ) -> None:
        self._provider = provider
        self._telemetry = telemetry

    def track_opportunity(
        self,
        observation: MarketObservation,
        thesis: MarketThesis,
        readiness: ExecutionReadiness,
        at: datetime,
    ) -> tuple[OpportunityIdentity, OpportunityIdentity | None]:
        current_opp, prev_opp = self._provider.evaluate_opportunity(
            observation, thesis, readiness, at
        )
        self._telemetry.metric(
            CapabilityMetric(self.name, "opportunities_tracked", 1, "count")
        )
        self._telemetry.log(
            CapabilityLog(
                self.name,
                LogLevel.INFO,
                "opportunity_tracked",
                (
                    ("opportunity_id", current_opp.opportunity_id),
                    ("state", str(current_opp.current_state)),
                    ("is_fresh", str(current_opp.is_fresh)),
                ),
            )
        )
        return current_opp, prev_opp

    def health(self, checked_at: datetime) -> CapabilityHealth:
        msg = "opportunity identity engine active"
        return CapabilityHealth(self.name, HealthState.HEALTHY, checked_at, msg)
