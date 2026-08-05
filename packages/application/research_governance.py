"""Create complete research proposals with no production mutation path."""

from datetime import datetime
from typing import Protocol

from packages.domain import EdgeStatistics, ResearchProposal


class ResearchProposalArchive(Protocol):
    def append(self, proposal: ResearchProposal) -> None: ...


class ResearchGovernance:
    def __init__(self, archive: ResearchProposalArchive) -> None:
        self._archive = archive

    def propose(
        self,
        proposal_id: str,
        question: str,
        hypothesis: str,
        method: str,
        evidence_references: tuple[str, ...],
        statistics: EdgeStatistics,
        risk: str,
        expected_gain: str,
        migration_impact: str,
        proposed_at: datetime,
    ) -> ResearchProposal:
        proposal = ResearchProposal(
            proposal_id,
            question,
            hypothesis,
            method,
            evidence_references,
            statistics,
            risk,
            expected_gain,
            statistics.confidence,
            migration_impact,
            proposed_at,
        )
        self._archive.append(proposal)
        return proposal
