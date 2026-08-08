"""Production ResearchPort and ResearchProposalPort adapters bridging backtest & hypothesis evaluation."""

from datetime import datetime

from packages.domain import (
    EdgeStatistics,
    LearningConfidence,
    LearningRecord,
    ResearchProposal,
)

from .capability import ResearchPort, ResearchProposalPort


class CanonicalResearchAdapter(ResearchPort, ResearchProposalPort):
    """Adapter bridging backtest evaluation reports into ResearchPort."""

    def evaluate_edge(
        self,
        records: tuple[LearningRecord, ...],
        evidence_combination: tuple[str, ...],
        evidence_quality: float,
        data_quality: float,
    ) -> EdgeStatistics:
        sample_size = len(records)
        wins = sum(1 for r in records if r.outcome == "TARGET_HIT")
        losses = sum(1 for r in records if r.outcome == "STOP_HIT")
        win_rate = (wins / sample_size * 100.0) if sample_size > 0 else 0.0
        confidence = LearningConfidence(
            historical_performance=min(1.0, max(0.0, win_rate / 100.0)),
            repeatability=0.8,
            evidence_quality=min(1.0, max(0.0, evidence_quality)),
            data_quality=min(1.0, max(0.0, data_quality)),
            sample_size_adequacy=min(1.0, max(0.0, sample_size / 100.0)),
        )

        return EdgeStatistics(
            evidence_combination=evidence_combination,
            sample_size=sample_size,
            winning=wins,
            losing=losses,
            win_rate=win_rate,
            confidence=confidence,
        )


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
        return ResearchProposal(
            proposal_id=proposal_id,
            question=question,
            hypothesis=hypothesis,
            method=method,
            evidence_references=evidence_references,
            statistics=statistics,
            risk=risk,
            expected_gain=expected_gain,
            confidence=statistics.confidence,
            migration_impact=migration_impact,
            proposed_at=proposed_at,
        )

