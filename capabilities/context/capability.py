"""Context capability: acquire and validate canonical environmental context.

Context is NOT Evidence. Context is NOT Knowledge.
Context describes the environment in which evidence must be interpreted.
"""

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
from packages.domain import MarketContext


class ContextProvider(Protocol):
    def acquire_context(self, symbol: str, at: datetime) -> MarketContext: ...


class ContextCapability:
    name = "context"

    def __init__(self, provider: ContextProvider, telemetry: CapabilityTelemetry) -> None:
        self._provider = provider
        self._telemetry = telemetry

    def get_context(self, symbol: str, at: datetime) -> MarketContext:
        context = self._provider.acquire_context(symbol, at)
        if not context.is_valid(at):
            raise ValueError(f"acquired context '{context.context_id}' is stale or invalid at {at.isoformat()}")
        
        self._telemetry.metric(CapabilityMetric(self.name, "context_acquisitions", 1, "count"))
        self._telemetry.log(
            CapabilityLog(
                self.name,
                LogLevel.INFO,
                "context_acquired",
                (
                    ("context_id", context.context_id),
                    ("symbol", context.symbol),
                    ("session", str(context.session)),
                ),
            )
        )
        return context

    def validate_context(self, context: MarketContext, at: datetime) -> bool:
        valid = context.is_valid(at)
        self._telemetry.metric(CapabilityMetric(self.name, "context_validations", 1, "count"))
        return valid

    def health(self, checked_at: datetime) -> CapabilityHealth:
        return CapabilityHealth(self.name, HealthState.HEALTHY, checked_at, "context provider active")
