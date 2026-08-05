"""Professional-trader comprehension reviews for institutional reasoning."""

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum


class ComprehensionVerdict(StrEnum):
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


@dataclass(frozen=True, slots=True)
class ExplainedConcept:
    concept: str
    plain_language_meaning: str

    def __post_init__(self) -> None:
        if not self.concept.strip() or not self.plain_language_meaning.strip():
            raise ValueError("abstract concepts require a plain-language explanation")


@dataclass(frozen=True, slots=True)
class ExplainedStatistic:
    claim: str
    plain_language_meaning: str
    calculation_reference: str

    def __post_init__(self) -> None:
        values = (self.claim, self.plain_language_meaning, self.calculation_reference)
        if any(not value.strip() for value in values):
            raise ValueError("statistics require meaning and reproducible calculation")


@dataclass(frozen=True, slots=True)
class ReasoningComprehensionReview:
    review_id: str
    reasoning_id: str
    verdict: ComprehensionVerdict
    plain_language_summary: str
    explained_concepts: tuple[ExplainedConcept, ...]
    explained_statistics: tuple[ExplainedStatistic, ...]
    opaque_elements: tuple[str, ...]
    trader_judgment_required: str
    automation_limit: str
    reviewer: str
    evidence_references: tuple[str, ...]
    reviewed_at: datetime
    policy_version: str

    def __post_init__(self) -> None:
        if self.reviewed_at.tzinfo is None:
            raise ValueError("comprehension review timestamp must be timezone-aware")
        values = (
            self.review_id,
            self.reasoning_id,
            self.plain_language_summary,
            self.trader_judgment_required,
            self.automation_limit,
            self.reviewer,
            self.policy_version,
        )
        if any(not value.strip() for value in values) or not self.evidence_references:
            raise ValueError("comprehension review requires complete professional context")
        if self.verdict is ComprehensionVerdict.APPROVED and self.opaque_elements:
            raise ValueError("approved reasoning cannot contain opaque elements")
        if self.verdict is ComprehensionVerdict.APPROVED and (
            not self.explained_concepts or not self.explained_statistics
        ):
            raise ValueError("approved reasoning must explain abstractions and statistics")
