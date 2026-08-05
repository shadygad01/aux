"""Append-only governance audit for composition and tests."""

from packages.domain import GovernanceChangeRequest, GovernanceDecision


class InMemoryGovernanceAudit:
    def __init__(self) -> None:
        self.records: list[tuple[GovernanceChangeRequest, GovernanceDecision]] = []

    def append(self, request: GovernanceChangeRequest, decision: GovernanceDecision) -> None:
        if any(item[0].request_id == request.request_id for item in self.records):
            raise ValueError(f"governance request already decided; request_id={request.request_id}")
        self.records.append((request, decision))
