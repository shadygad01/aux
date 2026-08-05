"""Publishing capability: deliver an official decision through a replaceable sink."""

from dataclasses import dataclass
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
from capabilities.decision import OfficialDecision


@dataclass(frozen=True, slots=True)
class PublicationReceipt:
    publication_id: str
    decision_id: str
    published_at: datetime
    destination: str


class PublicationSink(Protocol):
    def publish(self, decision: OfficialDecision) -> PublicationReceipt: ...


class PublishingCapability:
    name = "publishing"

    def __init__(self, sink: PublicationSink | None, telemetry: CapabilityTelemetry) -> None:
        self._sink = sink
        self._telemetry = telemetry

    def publish(self, decision: OfficialDecision) -> PublicationReceipt:
        if self._sink is None:
            raise RuntimeError("publishing capability is not ready; no sink configured")
        receipt = self._sink.publish(decision)
        self._telemetry.metric(CapabilityMetric(self.name, "decisions_published", 1, "decisions"))
        self._telemetry.log(
            CapabilityLog(
                self.name,
                LogLevel.INFO,
                "decision_published",
                (("decision_id", decision.decision_id),),
            )
        )
        return receipt

    def health(self, checked_at: datetime) -> CapabilityHealth:
        state = HealthState.HEALTHY if self._sink is not None else HealthState.NOT_READY
        details = "sink configured" if self._sink is not None else "no publication sink configured"
        return CapabilityHealth(self.name, state, checked_at, details)
