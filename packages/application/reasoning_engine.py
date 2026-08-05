"""Version 4 staged institutional reasoning over all governed context."""

from dataclasses import dataclass
from datetime import datetime
from math import sqrt

from packages.domain import (
    EvidenceDirection,
    EvidenceKind,
    KnowledgeStatus,
    ReasoningDecision,
    ReasoningInput,
    ReasoningMistake,
    ReasoningStage,
    Recommendation,
    StageReasoning,
    StageStatus,
)

from .errors import DecisionEvaluationError
from .ports import EvidenceEvaluator, ReasoningAudit


@dataclass(frozen=True, slots=True)
class ReasoningPolicy:
    version: str = "reasoning-v1-hypothesis-1"
    contract_version: str = "4.0.0"
    minimum_reliable_evidence_weight: float = 0.05

    def __post_init__(self) -> None:
        if not 0 <= self.minimum_reliable_evidence_weight <= 1:
            raise ValueError("minimum_reliable_evidence_weight must be between 0 and 1")


class InstitutionalReasoningEngine:
    _STAGE_KINDS = {
        ReasoningStage.MACRO: (EvidenceKind.MACRO,),
        ReasoningStage.BIAS: (EvidenceKind.MARKET_BIAS,),
        ReasoningStage.LOCATION: (EvidenceKind.LOCATION,),
        ReasoningStage.LIQUIDITY: (EvidenceKind.LIQUIDITY_SWEEP,),
        ReasoningStage.MOMENTUM: (EvidenceKind.MACD,),
        ReasoningStage.SMC: (EvidenceKind.REVERSAL_CANDLE,),
    }

    def __init__(
        self,
        policy: ReasoningPolicy,
        evidence_evaluator: EvidenceEvaluator,
        audit: ReasoningAudit,
    ) -> None:
        self._policy = policy
        self._evidence_evaluator = evidence_evaluator
        self._audit = audit

    def evaluate(
        self, reasoning_input: ReasoningInput, evaluated_at: datetime
    ) -> ReasoningDecision:
        if evaluated_at.tzinfo is None:
            raise DecisionEvaluationError("reasoning evaluation time must be timezone-aware")
        evidence_decision = self._evidence_evaluator.evaluate(
            reasoning_input.evidence, evaluated_at
        )
        buy_weight = sum(
            item.effective_weight
            for item in evidence_decision.evidence
            if item.direction is EvidenceDirection.BUY
        )
        sell_weight = sum(
            item.effective_weight
            for item in evidence_decision.evidence
            if item.direction is EvidenceDirection.SELL
        )
        favored_direction = (
            EvidenceDirection.BUY
            if buy_weight > sell_weight
            else EvidenceDirection.SELL
            if sell_weight > buy_weight
            else EvidenceDirection.NEUTRAL
        )
        reliable_support = tuple(
            item
            for item in evidence_decision.evidence
            if item.direction is favored_direction
            and item.effective_weight >= self._policy.minimum_reliable_evidence_weight
        )
        contradictions = tuple(
            item
            for item in evidence_decision.evidence
            if item.direction not in {favored_direction, EvidenceDirection.NEUTRAL}
            and item.effective_weight >= self._policy.minimum_reliable_evidence_weight
        )

        stages: list[StageReasoning] = []
        for stage, kinds in self._STAGE_KINDS.items():
            matching = tuple(item for item in reliable_support if item.kind in kinds)
            status = StageStatus.COMPLETE if matching else StageStatus.MISSING
            explanation = (
                f"{stage.value} has {len(matching)} reliable supporting evidence items."
                if matching
                else f"{stage.value} lacks reliable supporting evidence."
            )
            stages.append(
                StageReasoning(
                    stage, status, explanation, tuple(item.evidence_id for item in matching)
                )
            )
        contradiction_status = StageStatus.CONTRADICTED if contradictions else StageStatus.COMPLETE
        stages.append(
            StageReasoning(
                ReasoningStage.CONTRADICTIONS,
                contradiction_status,
                f"Found {len(contradictions)} reliable opposing evidence items.",
                tuple(item.evidence_id for item in contradictions),
            )
        )
        stages.append(
            StageReasoning(
                ReasoningStage.TRADE_QUALITY,
                StageStatus.COMPLETE,
                f"Reproducible trade quality is {evidence_decision.trade_quality}/100.",
                (),
            )
        )

        accepted_knowledge_statuses = {
            KnowledgeStatus.VALIDATED,
            KnowledgeStatus.INSTITUTIONAL_RULE,
        }
        active_knowledge = tuple(
            item
            for item in reasoning_input.knowledge
            if item.status in accepted_knowledge_statuses and not item.review_due(evaluated_at)
        )
        expired_knowledge = tuple(
            item.knowledge_id for item in reasoning_input.knowledge if item.review_due(evaluated_at)
        )
        missing = list(evidence_decision.missing)
        missing.extend(stage.explanation for stage in stages if stage.status is StageStatus.MISSING)
        if not active_knowledge:
            missing.append("No current validated knowledge object supports institutional context.")
        missing.extend(
            f"Knowledge object {identifier} is due for review." for identifier in expired_knowledge
        )
        if not reasoning_input.historical_context:
            missing.append("No evidence-backed historical similarity is available.")
        if reasoning_input.market_state.is_expired(evaluated_at):
            missing.append("Market state expired and must be recollected.")

        recommendation = evidence_decision.recommendation
        if reasoning_input.market_state.is_expired(evaluated_at) or not active_knowledge:
            recommendation = Recommendation.NO_OPINION
        elif any(stage.status is StageStatus.MISSING for stage in stages):
            recommendation = Recommendation.WAIT

        stages.append(
            StageReasoning(
                ReasoningStage.RECOMMENDATION,
                StageStatus.COMPLETE,
                f"Recommendation is {recommendation.value}; no stage was skipped.",
                (),
            )
        )

        context_factor = (
            sum(sqrt(item.reliability * item.confidence) for item in active_knowledge)
            / len(active_knowledge)
            if active_knowledge
            else 0.0
        )
        reliability = round(evidence_decision.confidence * context_factor)
        support = tuple(f"{item.kind.value}: {item.rationale}" for item in reliable_support)
        opposition = tuple(
            f"{item.kind.value}: {item.rationale}" for item in contradictions
        ) + tuple(
            f"Knowledge contradiction reference: {reference}"
            for item in active_knowledge
            for reference in item.contradicting_evidence
        )
        alternative_explanations = reasoning_input.market_state.alternative_explanations + tuple(
            item.rationale for item in contradictions
        )
        historical_similarities = tuple(
            f"{item.event.event_id}: {item.reasoning} (similarity {item.similarity:.2f})"
            for item in sorted(
                reasoning_input.historical_context,
                key=lambda value: value.similarity,
                reverse=True,
            )
        )
        market_state_expiry = (
            reasoning_input.market_state.captured_at + reasoning_input.market_state.time_to_live
        )
        invalidations = tuple(
            f"Expiry of {item.kind.value} evidence at {item.expires_at.isoformat()}."
            for item in reliable_support
        ) + (
            f"Market state expires at {market_state_expiry.isoformat()}.",
            "Stronger reliable opposing evidence would invalidate the current preference.",
        )
        improvements = (
            tuple(dict.fromkeys(missing))
            + tuple(
                f"Research suggestion requiring approval: {item.suggested_improvement}"
                for item in reasoning_input.learning_suggestions
            )
            + tuple(f"Research context only: {item.question}" for item in reasoning_input.research)
        )
        happening = (
            f"Current evidence favors {favored_direction.value} attention; "
            f"the governed recommendation is {recommendation.value}."
            if favored_direction is not EvidenceDirection.NEUTRAL
            else "Current reliable evidence does not establish directional attention."
        )
        decision = ReasoningDecision(
            reasoning_id=reasoning_input.reasoning_id,
            recommendation=recommendation,
            trade_quality=evidence_decision.trade_quality,
            reliability=reliability,
            what_is_happening=happening,
            why=evidence_decision.why,
            supporting_evidence=support,
            contradicting_evidence=opposition,
            missing_evidence=tuple(dict.fromkeys(missing)),
            alternative_explanations=alternative_explanations,
            historical_similarities=historical_similarities,
            what_would_invalidate=invalidations,
            what_would_improve=improvements,
            stages=tuple(stages),
            evaluated_at=evaluated_at,
            policy_version=self._policy.version,
            contract_version=self._policy.contract_version,
        )
        try:
            self._audit.append_path(reasoning_input, decision)
        except Exception as error:
            raise DecisionEvaluationError(
                f"reasoning path audit failed; reasoning={reasoning_input.reasoning_id}; "
                f"recommendation={decision.recommendation.value}"
            ) from error
        return decision

    def record_mistake(self, mistake: ReasoningMistake) -> None:
        try:
            self._audit.append_mistake(mistake)
        except Exception as error:
            raise DecisionEvaluationError(
                f"reasoning mistake audit failed; mistake={mistake.mistake_id}; "
                f"reasoning={mistake.reasoning_id}"
            ) from error
