"""Thread-local-process telemetry recorder for capability metrics and logs."""

from capabilities.contracts import CapabilityLog, CapabilityMetric


class InMemoryCapabilityTelemetry:
    def __init__(self) -> None:
        self.metrics: list[CapabilityMetric] = []
        self.logs: list[CapabilityLog] = []

    def metric(self, value: CapabilityMetric) -> None:
        self.metrics.append(value)

    def log(self, value: CapabilityLog) -> None:
        self.logs.append(value)
