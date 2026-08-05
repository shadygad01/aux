"""Macro capability implementation."""

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
from packages.domain import MacroAssessment, MacroContext


class MacroProvider(Protocol):
    def acquire_macro_context(self, now: datetime) -> MacroContext: ...
    def evaluate_macro_assessment(
        self, macro_context: MacroContext, evaluated_at: datetime
    ) -> MacroAssessment: ...


class MacroCapability:
    name = "macro"

    def __init__(self, provider: MacroProvider, telemetry: CapabilityTelemetry) -> None:
        self._provider = provider
        self._telemetry = telemetry

    def get_macro_context(self, at: datetime) -> MacroContext:
        ctx = self._provider.acquire_macro_context(at)
        if not ctx.is_valid(at):
            raise ValueError(f"macro context '{ctx.context_id}' is invalid or expired at {at.isoformat()}")

        self._telemetry.metric(CapabilityMetric(self.name, "context_acquired", 1, "count"))
        self._telemetry.log(
            CapabilityLog(
                self.name,
                LogLevel.INFO,
                "macro_context_acquired",
                (
                    ("context_id", ctx.context_id),
                    ("dollar_strength", str(ctx.dollar_strength)),
                ),
            )
        )
        return ctx

    def get_macro_assessment(self, ctx: MacroContext, at: datetime) -> MacroAssessment:
        assessment = self._provider.evaluate_macro_assessment(ctx, at)
        self._telemetry.metric(CapabilityMetric(self.name, "assessments_evaluated", 1, "count"))
        return assessment

    def health(self, checked_at: datetime) -> CapabilityHealth:
        return CapabilityHealth(self.name, HealthState.HEALTHY, checked_at, "macro intelligence active")
