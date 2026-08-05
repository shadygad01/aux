"""Collection capability: acquire raw observations through a replaceable port."""

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


@dataclass(frozen=True, slots=True)
class CollectionRequest:
    symbol: str
    requested_at: datetime


@dataclass(frozen=True, slots=True)
class RawDatum:
    field: str
    value: str
    observed_at: datetime
    source: str


@dataclass(frozen=True, slots=True)
class CollectionBatch:
    request: CollectionRequest
    records: tuple[RawDatum, ...]
    collected_at: datetime


class CollectionPort(Protocol):
    def collect(self, request: CollectionRequest) -> CollectionBatch: ...


class CollectionCapability:
    name = "collection"

    def __init__(self, adapter: CollectionPort | None, telemetry: CapabilityTelemetry) -> None:
        self._adapter = adapter
        self._telemetry = telemetry

    def collect(self, request: CollectionRequest) -> CollectionBatch:
        if self._adapter is None:
            raise RuntimeError("collection capability is not ready; no adapter configured")
        try:
            batch = self._adapter.collect(request)
            self._telemetry.metric(
                CapabilityMetric(self.name, "records_collected", len(batch.records), "records")
            )
            self._telemetry.log(
                CapabilityLog(
                    self.name, LogLevel.INFO, "collection_completed", (("symbol", request.symbol),)
                )
            )
            return batch
        except Exception as error:
            self._telemetry.log(
                CapabilityLog(
                    self.name, LogLevel.ERROR, "collection_failed", (("symbol", request.symbol),)
                )
            )
            raise RuntimeError(f"collection failed; symbol={request.symbol}") from error

    def health(self, checked_at: datetime) -> CapabilityHealth:
        state = HealthState.HEALTHY if self._adapter is not None else HealthState.NOT_READY
        details = (
            "adapter configured"
            if self._adapter is not None
            else "no collection adapter configured"
        )
        return CapabilityHealth(self.name, state, checked_at, details)
