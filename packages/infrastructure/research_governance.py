"""Append-only research proposal archive for composition and tests."""

from packages.domain import ResearchProposal


class InMemoryResearchProposalArchive:
    def __init__(self) -> None:
        self.proposals: list[ResearchProposal] = []

    def append(self, proposal: ResearchProposal) -> None:
        if any(item.proposal_id == proposal.proposal_id for item in self.proposals):
            raise ValueError(
                f"research proposal already exists; proposal_id={proposal.proposal_id}"
            )
        self.proposals.append(proposal)
