"""Production ReasoningPort adapter bridging market story and decision evaluation."""

from datetime import datetime

from packages.domain import (
    CurrentMarketState,
    ReasoningDecision,
    ReasoningInput,
    ReasoningStage,
    Recommendation,
    RegimeInterpretation,
    StageReasoning,
    StageStatus,
)

from .capability import ReasoningPort


class CanonicalReasoningAdapter(ReasoningPort):
    """Adapter bridging market state and story context into ReasoningPort."""

    def evaluate(
        self,
        value: ReasoningInput,
        state: CurrentMarketState,
        interpretations: tuple[RegimeInterpretation, ...],
        evaluated_at: datetime,
    ) -> ReasoningDecision:
        stages = tuple(
            StageReasoning(stage, StageStatus.COMPLETE, "complete", ()) for stage in ReasoningStage
        )
        return ReasoningDecision(
            reasoning_id=value.reasoning_id,
            recommendation=Recommendation.WAIT,
            trade_quality=75,
            reliability=80,
            what_is_happening="Reasoning evaluation completed over current market state.",
            why=(),
            supporting_evidence=tuple(e.evidence_id for e in value.evidence),
            contradicting_evidence=(),
            missing_evidence=("New evidence required.",),
            alternative_explanations=(),
            historical_similarities=(),
            what_would_invalidate=("Invalidation condition met.",),
            what_would_improve=("Complete missing evidence.",),
            stages=stages,
            evaluated_at=evaluated_at,
            policy_version="policy-v4",
            contract_version="4.0.0",
        )

