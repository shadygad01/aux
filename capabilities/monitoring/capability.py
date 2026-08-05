"""Monitoring capability: aggregate capability-owned health contracts."""

from dataclasses import dataclass
from datetime import datetime

from capabilities.contracts import (
    CapabilityHealth,
    CapabilityLog,
    CapabilityMetric,
    CapabilityTelemetry,
    HealthProvider,
    HealthState,
    LogLevel,
)


@dataclass(frozen=True, slots=True)
class SystemHealth:
    state: HealthState
    capabilities: tuple[CapabilityHealth, ...]
    checked_at: datetime


class MonitoringCapability:
    name = "monitoring"

    def __init__(
        self, providers: tuple[HealthProvider, ...], telemetry: CapabilityTelemetry
    ) -> None:
        self._providers = providers
        self._telemetry = telemetry

    def check(self, checked_at: datetime) -> SystemHealth:
        results = tuple(provider.health(checked_at) for provider in self._providers)
        if any(item.state is HealthState.NOT_READY for item in results):
            state = HealthState.NOT_READY
        elif any(item.state is HealthState.DEGRADED for item in results):
            state = HealthState.DEGRADED
        else:
            state = HealthState.HEALTHY
        self._telemetry.metric(
            CapabilityMetric(self.name, "capabilities_checked", len(results), "capabilities")
        )
        self._telemetry.log(
            CapabilityLog(self.name, LogLevel.INFO, "health_checked", (("state", state.value),))
        )
        return SystemHealth(state, results, checked_at)

    def health(self, checked_at: datetime) -> CapabilityHealth:
        state = HealthState.HEALTHY if self._providers else HealthState.NOT_READY
        return CapabilityHealth(self.name, state, checked_at, f"providers={len(self._providers)}")
