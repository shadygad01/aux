"""Pattern discovery candidates, validation evidence, and governed lifecycle."""

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum


class PatternSource(StrEnum):
    HISTORICAL_MARKET_DATA = "HISTORICAL_MARKET_DATA"
    DECISION_MEMORY = "DECISION_MEMORY"
    EVIDENCE_GRAPH = "EVIDENCE_GRAPH"
    KNOWLEDGE_BASE = "KNOWLEDGE_BASE"
    LEARNING_RECORDS = "LEARNING_RECORDS"
    MACRO_EVENTS = "MACRO_EVENTS"


class PatternStatus(StrEnum):
    EXPERIMENTAL = "EXPERIMENTAL"
    OBSERVED = "OBSERVED"
    VALIDATED = "VALIDATED"
    INSTITUTIONAL_PATTERN = "INSTITUTIONAL_PATTERN"
    DEPRECATED = "DEPRECATED"


@dataclass(frozen=True, slots=True)
class PatternValidation:
    statistically_significant: bool = False
    repeatability_runs: int = 0
    backtested: bool = False
    forward_tested: bool = False
    documented: bool = False
    validation_references: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.repeatability_runs < 0:
            raise ValueError("pattern repeatability runs cannot be negative")
        if any((self.backtested, self.forward_tested, self.documented)) and not (
            self.statistically_significant and self.repeatability_runs >= 2
        ):
            raise ValueError("pattern testing requires significance and repeatability")
        if any((self.statistically_significant, self.backtested, self.forward_tested)) and not (
            self.validation_references
        ):
            raise ValueError("pattern validation claims require evidence references")


@dataclass(frozen=True, slots=True)
class DiscoveredPattern:
    pattern_id: str
    revision: int
    description: str
    supporting_evidence: tuple[str, ...]
    source_types: tuple[PatternSource, ...]
    sample_size: int
    win_rate: float
    failure_rate: float
    sessions: tuple[str, ...]
    macro_context: tuple[str, ...]
    confidence: float
    status: PatternStatus
    validation: PatternValidation
    reviewed_at: datetime
    change_reason: str

    def __post_init__(self) -> None:
        if self.reviewed_at.tzinfo is None:
            raise ValueError("pattern review timestamp must be timezone-aware")
        if self.revision <= 0 or self.sample_size < 2:
            raise ValueError("patterns require a positive revision and multiple observations")
        if not 0 <= self.win_rate <= 1 or not 0 <= self.failure_rate <= 1:
            raise ValueError("pattern rates must be between zero and one")
        if abs((self.win_rate + self.failure_rate) - 1) > 0.000001:
            raise ValueError("pattern win and failure rates must be reproducible complements")
        if not 0 <= self.confidence <= 1:
            raise ValueError("pattern confidence must be between zero and one")
        required = (self.pattern_id, self.description, self.change_reason)
        if any(not value.strip() for value in required):
            raise ValueError("pattern identity, description, and change reason are required")
        if not self.supporting_evidence or not self.source_types or not self.sessions:
            raise ValueError("patterns require evidence, sources, and sessions")

    @property
    def production_eligible(self) -> bool:
        return self.status is PatternStatus.INSTITUTIONAL_PATTERN
