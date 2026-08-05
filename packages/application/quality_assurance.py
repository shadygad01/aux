"""Fail-closed sprint completion based on review and synchronization evidence."""

from datetime import datetime
from typing import Protocol

from packages.domain import (
    InstitutionalQualityCompletion,
    ReviewArea,
    ReviewVerdict,
    SprintReview,
    SynchronizationEvidence,
)


class QualityAudit(Protocol):
    def append(self, completion: InstitutionalQualityCompletion) -> None: ...


class InstitutionalQualityGate:
    def __init__(self, audit: QualityAudit, policy_version: str) -> None:
        if not policy_version.strip():
            raise ValueError("quality policy version is required")
        self._audit = audit
        self._policy_version = policy_version

    def complete(
        self,
        sprint_id: str,
        reviews: tuple[SprintReview, ...],
        synchronization: SynchronizationEvidence,
        completed_at: datetime,
    ) -> InstitutionalQualityCompletion:
        areas = {review.area for review in reviews}
        required = set(ReviewArea)
        if len(reviews) != len(required) or areas != required:
            missing = sorted(area.value for area in required - areas)
            raise ValueError(
                f"institutional gate requires exactly ten unique reviews; missing={missing}"
            )
        rejected = sorted(
            review.area.value for review in reviews if review.verdict is not ReviewVerdict.APPROVED
        )
        if rejected:
            raise ValueError(f"sprint reviews require changes; areas={rejected}")
        synchronized = (
            synchronization.documentation_synchronized
            and synchronization.tests_synchronized
            and synchronization.architecture_synchronized
        )
        if not synchronized:
            raise ValueError("documentation, tests, and architecture must remain synchronized")
        completion = InstitutionalQualityCompletion(
            f"SPRINT-COMPLETE-{sprint_id}",
            sprint_id,
            reviews,
            synchronization,
            completed_at,
            self._policy_version,
        )
        self._audit.append(completion)
        return completion
