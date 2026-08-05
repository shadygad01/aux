"""Complete research proposals that can never represent production policy."""

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

from .learning_models import EdgeStatistics, LearningConfidence


class ResearchOutputStatus(StrEnum):
    PROPOSAL = "PROPOSAL"


@dataclass(frozen=True, slots=True)
class ResearchProposal:
    proposal_id: str
    question: str
    hypothesis: str
    method: str
    evidence_references: tuple[str, ...]
    statistics: EdgeStatistics
    risk: str
    expected_gain: str
    confidence: LearningConfidence
    migration_impact: str
    proposed_at: datetime
    status: ResearchOutputStatus = ResearchOutputStatus.PROPOSAL
    contract_version: str = "1.0.0"

    def __post_init__(self) -> None:
        if self.proposed_at.tzinfo is None:
            raise ValueError("research proposal timestamp must be timezone-aware")
        required = (
            self.proposal_id,
            self.question,
            self.hypothesis,
            self.method,
            self.risk,
            self.expected_gain,
            self.migration_impact,
        )
        if any(not value.strip() for value in required) or not self.evidence_references:
            raise ValueError("research proposals require every governed field and evidence")
        if self.confidence != self.statistics.confidence:
            raise ValueError("research confidence must reproduce the supplied statistics")

    @property
    def production_eligible(self) -> bool:
        return False
