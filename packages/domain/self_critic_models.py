"""Independent decision challenges and research tasks."""

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

from .decision_memory_models import DecisionOutcome


class CritiqueStage(StrEnum):
    PRE_PUBLICATION = "PRE_PUBLICATION"
    OUTCOME_REVIEW = "OUTCOME_REVIEW"


class ResearchTaskStatus(StrEnum):
    OPEN = "OPEN"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    REJECTED = "REJECTED"


@dataclass(frozen=True, slots=True)
class CritiqueAssessment:
    ignored_evidence: str
    overweighted_evidence: str
    underweighted_evidence: str
    uncertainty_assessment: str
    conflicting_evidence: str
    alternative_reasoning_path: str
    evidence_references: tuple[str, ...]

    def __post_init__(self) -> None:
        answers = (
            self.ignored_evidence,
            self.overweighted_evidence,
            self.underweighted_evidence,
            self.uncertainty_assessment,
            self.conflicting_evidence,
            self.alternative_reasoning_path,
        )
        if any(not answer.strip() for answer in answers) or not self.evidence_references:
            raise ValueError("every self-critic question requires an evidence-linked answer")


@dataclass(frozen=True, slots=True)
class DecisionCritique:
    critique_id: str
    decision_id: str
    decision_version: int
    stage: CritiqueStage
    outcome: DecisionOutcome
    assessment: CritiqueAssessment
    challenged_at: datetime
    critic_policy_version: str

    def __post_init__(self) -> None:
        if self.challenged_at.tzinfo is None:
            raise ValueError("critique timestamp must be timezone-aware")
        if self.decision_version <= 0:
            raise ValueError("critique decision version must be positive")
        values = (self.critique_id, self.decision_id, self.critic_policy_version)
        if any(not value.strip() for value in values):
            raise ValueError("critique identity and policy version are required")


@dataclass(frozen=True, slots=True)
class ResearchTask:
    task_id: str
    decision_id: str
    critique_id: str
    question: str
    evidence_references: tuple[str, ...]
    created_at: datetime
    status: ResearchTaskStatus = ResearchTaskStatus.OPEN

    def __post_init__(self) -> None:
        if self.created_at.tzinfo is None:
            raise ValueError("research task timestamp must be timezone-aware")
        values = (self.task_id, self.decision_id, self.critique_id, self.question)
        if any(not value.strip() for value in values) or not self.evidence_references:
            raise ValueError("research tasks require identity, question, and evidence")
