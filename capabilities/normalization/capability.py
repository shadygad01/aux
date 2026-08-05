"""Normalization capability: convert raw numeric records into canonical units."""

from dataclasses import dataclass
from datetime import datetime

from capabilities.collection import CollectionBatch
from capabilities.contracts import (
    CapabilityHealth,
    CapabilityLog,
    CapabilityMetric,
    CapabilityTelemetry,
    HealthState,
    LogLevel,
)


@dataclass(frozen=True, slots=True)
class NormalizedDatum:
    field: str
    value: float
    unit: str
    observed_at: datetime
    source: str


class NormalizationCapability:
    name = "normalization"

    def __init__(self, field_units: dict[str, str], telemetry: CapabilityTelemetry) -> None:
        self._field_units = dict(field_units)
        self._telemetry = telemetry

    def normalize(self, batch: CollectionBatch) -> tuple[NormalizedDatum, ...]:
        normalized: list[NormalizedDatum] = []
        for record in batch.records:
            if record.field not in self._field_units:
                raise ValueError(f"normalization unit missing; field={record.field}")
            try:
                numeric_value = float(record.value)
            except ValueError as error:
                self._telemetry.log(
                    CapabilityLog(
                        self.name,
                        LogLevel.ERROR,
                        "normalization_failed",
                        (("field", record.field),),
                    )
                )
                raise ValueError(
                    f"non-numeric raw datum; field={record.field}; value={record.value}"
                ) from error
            normalized.append(
                NormalizedDatum(
                    record.field,
                    numeric_value,
                    self._field_units[record.field],
                    record.observed_at,
                    record.source,
                )
            )
        self._telemetry.metric(
            CapabilityMetric(self.name, "records_normalized", len(normalized), "records")
        )
        self._telemetry.log(
            CapabilityLog(
                self.name,
                LogLevel.INFO,
                "normalization_completed",
                (("records", str(len(normalized))),),
            )
        )
        return tuple(normalized)

    def health(self, checked_at: datetime) -> CapabilityHealth:
        state = HealthState.HEALTHY if self._field_units else HealthState.NOT_READY
        return CapabilityHealth(
            self.name, state, checked_at, f"configured fields={len(self._field_units)}"
        )
