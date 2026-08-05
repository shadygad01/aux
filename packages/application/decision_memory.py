"""Decision identity, immutable evolution, and institutional search use cases."""

from datetime import datetime

from packages.domain import (
    DecisionChange,
    DecisionOutcome,
    DecisionSearch,
    DecisionSearchResult,
    DecisionSnapshot,
    DecisionVersion,
)

from .errors import DecisionEvaluationError
from .ports import DecisionArchive, DecisionIdPort


class DecisionMemory:
    def __init__(self, identifier: DecisionIdPort, archive: DecisionArchive) -> None:
        self._identifier = identifier
        self._archive = archive

    def create(
        self,
        snapshot: DecisionSnapshot,
        timestamp: datetime,
        reason: str,
    ) -> DecisionVersion:
        decision_id = self._identifier.next_id(timestamp)
        decision = DecisionVersion(
            decision_id=decision_id,
            version=1,
            timestamp=timestamp,
            snapshot=snapshot,
            outcome=DecisionOutcome.PENDING,
            changes=(DecisionChange("decision", "NONE", "CREATED"),),
            change_reason=reason,
            previous_version=None,
        )
        self._append(decision)
        return decision

    def evolve(
        self,
        decision_id: str,
        snapshot: DecisionSnapshot,
        timestamp: datetime,
        reason: str,
        outcome: DecisionOutcome | None = None,
    ) -> DecisionVersion:
        previous = self._archive.latest(decision_id)
        if previous is None:
            raise ValueError(f"cannot evolve unknown decision; decision_id={decision_id}")
        current_outcome = outcome or previous.outcome
        changes = self._changes(previous.snapshot, snapshot)
        if current_outcome is not previous.outcome:
            changes.append(DecisionChange("outcome", previous.outcome.value, current_outcome.value))
        if not changes:
            raise ValueError(f"decision evolution has no changes; decision_id={decision_id}")
        decision = DecisionVersion(
            decision_id=decision_id,
            version=previous.version + 1,
            timestamp=timestamp,
            snapshot=snapshot,
            outcome=current_outcome,
            changes=tuple(changes),
            change_reason=reason,
            previous_version=previous.version,
        )
        self._append(decision)
        return decision

    def search(self, query: DecisionSearch) -> DecisionSearchResult:
        decisions = self._archive.search(query)
        return DecisionSearchResult(query, decisions, len(decisions))

    def _append(self, decision: DecisionVersion) -> None:
        try:
            self._archive.append(decision)
        except Exception as error:
            raise DecisionEvaluationError(
                f"decision archive failed; decision={decision.decision_id}; "
                f"version={decision.version}"
            ) from error

    @staticmethod
    def _changes(previous: DecisionSnapshot, current: DecisionSnapshot) -> list[DecisionChange]:
        fields = (
            ("market_state", previous.market_state.state_id, current.market_state.state_id),
            ("macro_snapshot", previous.macro_snapshot, current.macro_snapshot),
            ("bias", repr(previous.biases), repr(current.biases)),
            ("trade_quality", str(previous.trade_quality), str(current.trade_quality)),
            ("execution_state", previous.execution_state.value, current.execution_state.value),
            ("evidence_graph", repr(previous.evidence_graph), repr(current.evidence_graph)),
            (
                "knowledge_objects",
                repr(previous.knowledge_object_ids),
                repr(current.knowledge_object_ids),
            ),
            ("reasoning_graph", repr(previous.reasoning_graph), repr(current.reasoning_graph)),
            (
                "contradiction_graph",
                repr(previous.contradiction_graph),
                repr(current.contradiction_graph),
            ),
            ("confidence", str(previous.confidence), str(current.confidence)),
            ("uncertainty", str(previous.uncertainty), str(current.uncertainty)),
            (
                "supporting_evidence",
                repr(previous.supporting_evidence),
                repr(current.supporting_evidence),
            ),
            (
                "contradicting_evidence",
                repr(previous.contradicting_evidence),
                repr(current.contradicting_evidence),
            ),
            (
                "rejected_alternatives",
                repr(previous.rejected_alternatives),
                repr(current.rejected_alternatives),
            ),
        )
        return [
            DecisionChange(field, before, after)
            for field, before, after in fields
            if before != after
        ]
