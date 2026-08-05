"""Shared operational contracts; contains no trading business behavior."""

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import Protocol


class HealthState(StrEnum):
    HEALTHY = "HEALTHY"
    DEGRADED = "DEGRADED"
    NOT_READY = "NOT_READY"


class LogLevel(StrEnum):
    INFO = "INFO"
    ERROR = "ERROR"


@dataclass(frozen=True, slots=True)
class CapabilityHealth:
    capability: str
    state: HealthState
    checked_at: datetime
    details: str


@dataclass(frozen=True, slots=True)
class CapabilityMetric:
    capability: str
    name: str
    value: float
    unit: str


@dataclass(frozen=True, slots=True)
class CapabilityLog:
    capability: str
    level: LogLevel
    event: str
    context: tuple[tuple[str, str], ...]


class CapabilityTelemetry(Protocol):
    def metric(self, value: CapabilityMetric) -> None: ...

    def log(self, value: CapabilityLog) -> None: ...


class HealthProvider(Protocol):
    def health(self, checked_at: datetime) -> CapabilityHealth: ...
