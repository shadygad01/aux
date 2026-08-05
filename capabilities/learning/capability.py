"""Learning capability: store one outcome and produce its research artifact."""

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
    CritiqueAssessment,
    CritiqueStage,
    DecisionCritique,
    DecisionVersion,
    LearningRecord,
    ResearchArtifact,
    ResearchTask,
)


class LearningPort(Protocol):
    def record(self, record: LearningRecord) -> ResearchArtifact | None: ...


class SelfCriticPort(Protocol):
    def challenge(
        self,
        decision: DecisionVersion,
        stage: CritiqueStage,
        assessment: CritiqueAssessment,
        challenged_at: datetime,
    ) -> tuple[DecisionCritique, tuple[ResearchTask, ...]]: ...


class LearningCapability:
    name = "learning"

    def __init__(
        self,
        learning_service: LearningPort,
        telemetry: CapabilityTelemetry,
        self_critic: SelfCriticPort | None = None,
    ) -> None:
        self._learning_service = learning_service
        self._telemetry = telemetry
        self._self_critic = self_critic

    def challenge(
        self,
        decision: DecisionVersion,
        stage: CritiqueStage,
        assessment: CritiqueAssessment,
        challenged_at: datetime,
    ) -> tuple[DecisionCritique, tuple[ResearchTask, ...]]:
        if self._self_critic is None:
            raise RuntimeError("self-critic is not configured")
        critique, tasks = self._self_critic.challenge(decision, stage, assessment, challenged_at)
        self._telemetry.metric(CapabilityMetric(self.name, "decisions_challenged", 1, "decisions"))
        self._telemetry.metric(
            CapabilityMetric(self.name, "research_tasks_opened", len(tasks), "tasks")
        )
        return critique, tasks

    def learn(self, record: LearningRecord) -> ResearchArtifact | None:
        artifact = self._learning_service.record(record)
        self._telemetry.metric(CapabilityMetric(self.name, "records_learned", 1, "records"))
        self._telemetry.log(
            CapabilityLog(
                self.name, LogLevel.INFO, "learning_recorded", (("record_id", record.record_id),)
            )
        )
        return artifact

    def health(self, checked_at: datetime) -> CapabilityHealth:
        return CapabilityHealth(
            self.name, HealthState.HEALTHY, checked_at, "learning store configured"
        )
