"""Constitutional authority, change requests, and immutable decisions."""

from dataclasses import dataclass
from datetime import datetime
from enum import IntEnum, StrEnum


class AuthorityLevel(IntEnum):
    IMMUTABLE_PRINCIPLE = 1
    VALIDATED_TRADING_RULE = 2
    IMPLEMENTATION = 3
    PERFORMANCE_IMPROVEMENT = 4
    DOCUMENTATION = 5


class GovernanceActor(StrEnum):
    PROJECT_OWNER = "PROJECT_OWNER"
    LEARNING = "LEARNING"
    RESEARCH = "RESEARCH"
    IMPLEMENTATION = "IMPLEMENTATION"
    AUTOMATION = "AUTOMATION"
    DOCUMENTATION = "DOCUMENTATION"


class GovernedDomain(StrEnum):
    IMMUTABLE_PRINCIPLES = "IMMUTABLE_PRINCIPLES"
    TRADING_CONSTITUTION = "TRADING_CONSTITUTION"
    DECISION_CONSTITUTION = "DECISION_CONSTITUTION"
    IMPLEMENTATION = "IMPLEMENTATION"
    PERFORMANCE = "PERFORMANCE"
    DOCUMENTATION = "DOCUMENTATION"


class GovernanceVerdict(StrEnum):
    AUTHORIZED = "AUTHORIZED"
    REJECTED = "REJECTED"


@dataclass(frozen=True, slots=True)
class GovernanceEvidence:
    research_references: tuple[str, ...] = ()
    backtest_references: tuple[str, ...] = ()
    documentation_references: tuple[str, ...] = ()
    test_references: tuple[str, ...] = ()
    owner_approval_reference: str | None = None
    logic_identical: bool = False


@dataclass(frozen=True, slots=True)
class GovernanceChangeRequest:
    request_id: str
    artifact_id: str
    authority: AuthorityLevel
    domain: GovernedDomain
    requested_by: GovernanceActor
    applied_by: GovernanceActor
    description: str
    evidence: GovernanceEvidence
    requested_at: datetime

    def __post_init__(self) -> None:
        if self.requested_at.tzinfo is None:
            raise ValueError("governance request timestamp must be timezone-aware")
        values = (self.request_id, self.artifact_id, self.description)
        if any(not value.strip() for value in values):
            raise ValueError("governance request identity and description are required")


@dataclass(frozen=True, slots=True)
class GovernanceDecision:
    decision_id: str
    request_id: str
    verdict: GovernanceVerdict
    reasons: tuple[str, ...]
    decided_at: datetime
    policy_version: str

    def __post_init__(self) -> None:
        if self.decided_at.tzinfo is None:
            raise ValueError("governance decision timestamp must be timezone-aware")
        if not self.decision_id.strip() or not self.request_id.strip() or not self.reasons:
            raise ValueError("governance decisions require identity and reasons")
