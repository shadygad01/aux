"""Permanent research subsystem that can propose but never deploy changes."""

from dataclasses import dataclass

from packages.domain import (
    EdgeStatistics,
    KnowledgeLevel,
    LearningConfidence,
    LearningRecommendation,
    LearningRecord,
    OutcomeClassification,
    ResearchArtifact,
    ResearchArtifactKind,
)

from .errors import DecisionEvaluationError
from .ports import LearningRepository


@dataclass(frozen=True, slots=True)
class LearningPolicy:
    version: str = "learning-v1-hypothesis-1"
    minimum_edge_sample: int = 100

    def __post_init__(self) -> None:
        if self.minimum_edge_sample <= 0:
            raise ValueError("minimum_edge_sample must be positive")


class LearningEngine:
    """Store, analyze, and propose research; owns no production-policy mutation path."""

    def __init__(self, policy: LearningPolicy, repository: LearningRepository) -> None:
        self._policy = policy
        self._repository = repository

    def record(self, record: LearningRecord) -> ResearchArtifact | None:
        artifact = self._artifact_for(record)
        try:
            self._repository.append_record(record)
            if artifact is not None:
                self._repository.append_artifact(artifact)
        except Exception as error:
            raise DecisionEvaluationError(
                f"learning audit failed; record={record.record_id}; outcome={record.outcome.value}"
            ) from error
        return artifact

    def evaluate_edge(
        self,
        records: tuple[LearningRecord, ...],
        evidence_combination: tuple[str, ...],
        evidence_quality: float,
        data_quality: float,
    ) -> EdgeStatistics:
        if not evidence_combination:
            raise ValueError("edge evidence combination is required")
        normalized_combination = {value.casefold() for value in evidence_combination}
        cohort = tuple(
            record
            for record in records
            if normalized_combination.issubset(self._evidence_tags(record))
            and record.outcome in {OutcomeClassification.WINNING, OutcomeClassification.LOSING}
        )
        winning = sum(record.outcome is OutcomeClassification.WINNING for record in cohort)
        losing = sum(record.outcome is OutcomeClassification.LOSING for record in cohort)
        sample_size = winning + losing
        win_rate = winning / sample_size if sample_size else 0.0
        repeatability = abs((2 * win_rate) - 1) if sample_size else 0.0
        sample_adequacy = min(1.0, sample_size / self._policy.minimum_edge_sample)
        confidence = LearningConfidence(
            historical_performance=win_rate,
            repeatability=repeatability,
            evidence_quality=evidence_quality,
            data_quality=data_quality,
            sample_size_adequacy=sample_adequacy,
        )
        return EdgeStatistics(
            evidence_combination=evidence_combination,
            sample_size=sample_size,
            winning=winning,
            losing=losing,
            win_rate=round(win_rate, 6),
            confidence=confidence,
        )

    def evaluate_opportunity_edge(
        self,
        records: tuple[LearningRecord, ...],
        evidence_combination: tuple[str, ...],
        evidence_quality: float,
        data_quality: float,
    ) -> EdgeStatistics:
        """Evaluates edge per unique Opportunity ID lifetime rather than isolated decisions."""
        # Deduplicate records by opportunity_id keeping the final outcome
        unique_opps: dict[str, LearningRecord] = {}
        for record in records:
            if record.opportunity_id:
                unique_opps[record.opportunity_id] = record
            else:
                unique_opps[record.record_id] = record

        return self.evaluate_edge(
            tuple(unique_opps.values()),
            evidence_combination,
            evidence_quality,
            data_quality,
        )

    def propose(
        self,
        recommendation_id: str,
        current_rule: str,
        suggested_improvement: str,
        statistics: EdgeStatistics,
        supporting_evidence: tuple[str, ...],
        expected_impact: str,
        migration_risk: str,
    ) -> LearningRecommendation:
        recommendation = LearningRecommendation(
            recommendation_id=recommendation_id,
            current_rule=current_rule,
            suggested_improvement=suggested_improvement,
            supporting_evidence=supporting_evidence,
            historical_statistics=statistics,
            expected_impact=expected_impact,
            migration_risk=migration_risk,
            confidence=statistics.confidence,
        )
        try:
            self._repository.append_recommendation(recommendation)
        except Exception as error:
            raise DecisionEvaluationError(
                f"learning recommendation audit failed; recommendation={recommendation_id}"
            ) from error
        return recommendation

    @staticmethod
    def _evidence_tags(record: LearningRecord) -> set[str]:
        values = (
            record.liquidity
            + record.smc_evidence
            + record.supporting_evidence
            + (record.location.value,)
        )
        return {value.casefold() for value in values}

    @staticmethod
    def _artifact_for(record: LearningRecord) -> ResearchArtifact | None:
        failure_outcomes = {
            OutcomeClassification.LOSING,
            OutcomeClassification.FALSE_POSITIVE,
            OutcomeClassification.FALSE_NEGATIVE,
            OutcomeClassification.MISSED,
            OutcomeClassification.REJECTED,
            OutcomeClassification.IGNORED,
        }
        if record.outcome in failure_outcomes:
            return ResearchArtifact(
                artifact_id=f"{record.record_id}:hypothesis",
                source_record_id=record.record_id,
                kind=ResearchArtifactKind.HYPOTHESIS,
                question=(
                    "Why did this decision or detection fail, and was the failure predictable?"
                ),
                explanation="; ".join(record.learning_notes),
                knowledge_level=KnowledgeLevel.WORKING_HYPOTHESIS,
            )
        if record.outcome is OutcomeClassification.WINNING:
            return ResearchArtifact(
                artifact_id=f"{record.record_id}:evidence",
                source_record_id=record.record_id,
                kind=ResearchArtifactKind.SUPPORTING_EVIDENCE,
                question="Why did the supporting evidence align with the observed outcome?",
                explanation="; ".join(record.learning_notes),
                knowledge_level=KnowledgeLevel.EXPERIMENTAL,
            )
        return None
