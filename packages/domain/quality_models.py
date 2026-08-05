"""Sprint review evidence and completion records."""

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum


class ReviewArea(StrEnum):
    ARCHITECTURE = "ARCHITECTURE"
    TRADING = "TRADING"
    RESEARCH = "RESEARCH"
    LEARNING = "LEARNING"
    DOCUMENTATION = "DOCUMENTATION"
    TESTING = "TESTING"
    PERFORMANCE = "PERFORMANCE"
    SECURITY = "SECURITY"
    EXPLAINABILITY = "EXPLAINABILITY"
    MAINTAINABILITY = "MAINTAINABILITY"


class ReviewVerdict(StrEnum):
    APPROVED = "APPROVED"
    CHANGES_REQUIRED = "CHANGES_REQUIRED"


@dataclass(frozen=True, slots=True)
class SprintReview:
    area: ReviewArea
    verdict: ReviewVerdict
    reviewer: str
    findings: tuple[str, ...]
    evidence_references: tuple[str, ...]
    reviewed_at: datetime

    def __post_init__(self) -> None:
        if self.reviewed_at.tzinfo is None:
            raise ValueError("sprint review timestamp must be timezone-aware")
        if not self.reviewer.strip() or not self.findings or not self.evidence_references:
            raise ValueError("sprint reviews require reviewer, findings, and evidence")


@dataclass(frozen=True, slots=True)
class SynchronizationEvidence:
    documentation_synchronized: bool
    tests_synchronized: bool
    architecture_synchronized: bool
    documentation_references: tuple[str, ...]
    test_references: tuple[str, ...]
    architecture_references: tuple[str, ...]

    def __post_init__(self) -> None:
        if self.documentation_synchronized and not self.documentation_references:
            raise ValueError("documentation synchronization requires evidence")
        if self.tests_synchronized and not self.test_references:
            raise ValueError("test synchronization requires evidence")
        if self.architecture_synchronized and not self.architecture_references:
            raise ValueError("architecture synchronization requires evidence")


@dataclass(frozen=True, slots=True)
class InstitutionalQualityCompletion:
    completion_id: str
    sprint_id: str
    reviews: tuple[SprintReview, ...]
    synchronization: SynchronizationEvidence
    completed_at: datetime
    policy_version: str

    def __post_init__(self) -> None:
        if self.completed_at.tzinfo is None:
            raise ValueError("institutional quality completion timestamp must be timezone-aware")
        if not self.completion_id.strip() or not self.sprint_id.strip():
            raise ValueError("institutional quality completion identity is required")
