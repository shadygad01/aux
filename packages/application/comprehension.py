"""Reject reasoning that a professional trader cannot inspect and understand."""

from datetime import datetime
from typing import Protocol

from packages.domain import (
    ComprehensionVerdict,
    ExplainedConcept,
    ExplainedStatistic,
    ReasoningComprehensionReview,
    ReasoningDecision,
)


class ComprehensionAudit(Protocol):
    def append(self, review: ReasoningComprehensionReview) -> None: ...


class InstitutionalComprehensionGate:
    def __init__(self, audit: ComprehensionAudit, policy_version: str) -> None:
        if not policy_version.strip():
            raise ValueError("comprehension policy version is required")
        self._audit = audit
        self._policy_version = policy_version

    def review(
        self,
        reasoning: ReasoningDecision,
        plain_language_summary: str,
        explained_concepts: tuple[ExplainedConcept, ...],
        explained_statistics: tuple[ExplainedStatistic, ...],
        opaque_elements: tuple[str, ...],
        trader_judgment_required: str,
        automation_limit: str,
        reviewer: str,
        evidence_references: tuple[str, ...],
        reviewed_at: datetime,
    ) -> ReasoningComprehensionReview:
        unresolved = tuple(item for item in opaque_elements if item.strip())
        verdict = ComprehensionVerdict.REJECTED if unresolved else ComprehensionVerdict.APPROVED
        review = ReasoningComprehensionReview(
            f"COMPREHENSION-{reasoning.reasoning_id}",
            reasoning.reasoning_id,
            verdict,
            plain_language_summary,
            explained_concepts,
            explained_statistics,
            unresolved,
            trader_judgment_required,
            automation_limit,
            reviewer,
            evidence_references,
            reviewed_at,
            self._policy_version,
        )
        self._audit.append(review)
        return review
