"""Production ReasoningPort adapter bridging market state, evidence, and regime evaluation."""

from collections import Counter
from datetime import datetime

from packages.domain import (
    AttentionBias,
    CurrentMarketState,
    Evidence,
    EvidenceDirection,
    EvidenceKind,
    HorizonBias,
    ReasoningDecision,
    ReasoningInput,
    ReasoningStage,
    Recommendation,
    RegimeInterpretation,
    StageReasoning,
    StageStatus,
)

from .capability import ReasoningPort

_STAGE_KINDS: dict[ReasoningStage, tuple[EvidenceKind, ...]] = {
    ReasoningStage.MACRO: (EvidenceKind.MACRO,),
    ReasoningStage.LOCATION: (EvidenceKind.LOCATION,),
    ReasoningStage.LIQUIDITY: (EvidenceKind.LIQUIDITY_SWEEP,),
    ReasoningStage.MOMENTUM: (EvidenceKind.MACD,),
    ReasoningStage.SMC: (
        EvidenceKind.ORDER_BLOCK,
        EvidenceKind.FAIR_VALUE_GAP,
        EvidenceKind.CHANGE_OF_CHARACTER,
    ),
}
_CORE_KINDS = (
    EvidenceKind.MACRO,
    EvidenceKind.MARKET_BIAS,
    EvidenceKind.LOCATION,
    EvidenceKind.LIQUIDITY_SWEEP,
    EvidenceKind.MACD,
)


class CanonicalReasoningAdapter(ReasoningPort):
    """Weighs regime-interpreted, unexpired evidence against horizon bias into a decision.

    Every field is derived from the actual `value`/`state`/`interpretations` inputs -- there
    are no fixed placeholder scores or boilerplate strings independent of the evidence given.
    """

    def evaluate(
        self,
        value: ReasoningInput,
        state: CurrentMarketState,
        interpretations: tuple[RegimeInterpretation, ...],
        evaluated_at: datetime,
    ) -> ReasoningDecision:
        interpretation_by_evidence = {item.evidence_id: item for item in interpretations}
        fresh = tuple(item for item in value.evidence if item.freshness(evaluated_at) > 0)
        forced = tuple(item for item in fresh if item.forces_wait)
        reliability = self._reliability(fresh, state)

        if forced:
            recommendation = Recommendation.WAIT
            trade_quality = 0
            what_is_happening = "Mandatory evidence forces a wait regardless of directional signal."
            supporting: tuple[str, ...] = ()
            contradicting = tuple(item.evidence_id for item in forced)
            missing: tuple[str, ...] = ()
            alternatives: tuple[str, ...] = ()
            invalidate = tuple(item.rationale for item in forced)
        elif not fresh:
            recommendation = Recommendation.NO_OPINION
            trade_quality = 0
            what_is_happening = "No unexpired evidence is available to reason over."
            supporting, contradicting = (), ()
            missing = ("At least one unexpired evidence item is required.",)
            alternatives = ()
            invalidate = ("Fresh evidence becoming available.",)
        else:
            (
                recommendation,
                trade_quality,
                what_is_happening,
                supporting,
                contradicting,
            ) = self._weigh_direction(fresh, state.biases, interpretation_by_evidence, evaluated_at)
            missing = self._missing_evidence(fresh, value)
            alternatives = tuple(
                item.rationale for item in fresh if item.direction is EvidenceDirection.NEUTRAL
            )
            opposing = tuple(item for item in fresh if item.evidence_id in contradicting)
            invalidate = tuple(item.rationale for item in opposing) or (
                f"The dominant {state.biases[0].horizon.value.lower()} horizon bias reverses.",
            )

        return ReasoningDecision(
            reasoning_id=value.reasoning_id,
            recommendation=recommendation,
            trade_quality=trade_quality,
            reliability=reliability,
            what_is_happening=what_is_happening,
            why=tuple(item.rationale for item in fresh if item.evidence_id in supporting),
            supporting_evidence=supporting,
            contradicting_evidence=contradicting,
            missing_evidence=missing,
            alternative_explanations=alternatives,
            historical_similarities=tuple(
                f"{item.event.title}: {item.reasoning} (similarity={item.similarity:.2f})"
                for item in value.historical_context
                if item.similarity >= 0.5
            ),
            what_would_invalidate=invalidate,
            what_would_improve=tuple(
                f"Add {kind.value} evidence." for kind in self._absent_kinds(fresh)
            ),
            stages=self._stages(fresh, supporting, contradicting),
            evaluated_at=evaluated_at,
            policy_version="policy-v4",
            contract_version="4.0.0",
        )

    @staticmethod
    def _dominant_bias(biases: tuple[HorizonBias, ...]) -> AttentionBias:
        counts = Counter(bias.bias for bias in biases)
        return counts.most_common(1)[0][0]

    def _weigh_direction(
        self,
        fresh: tuple[Evidence, ...],
        biases: tuple[HorizonBias, ...],
        interpretation_by_evidence: dict[str, RegimeInterpretation],
        evaluated_at: datetime,
    ) -> tuple[Recommendation, int, str, tuple[str, ...], tuple[str, ...]]:
        buy_weight, sell_weight = 0.0, 0.0
        buy_ids: list[str] = []
        sell_ids: list[str] = []
        for item in fresh:
            interpretation = interpretation_by_evidence.get(item.evidence_id)
            importance = interpretation.adjusted_importance if interpretation else item.importance
            weight = (
                item.strength
                * item.confidence
                * item.reliability
                * importance
                * item.freshness(evaluated_at)
            )
            if item.direction is EvidenceDirection.BUY:
                buy_weight += weight
                buy_ids.append(item.evidence_id)
            elif item.direction is EvidenceDirection.SELL:
                sell_weight += weight
                sell_ids.append(item.evidence_id)

        bias_leader = self._dominant_bias(biases)
        favors_buy = (
            buy_weight > sell_weight
            and bias_leader is not AttentionBias.SELL_ONLY
            and bias_leader is not AttentionBias.WAIT
        )
        favors_sell = (
            sell_weight > buy_weight
            and bias_leader is not AttentionBias.BUY_ONLY
            and bias_leader is not AttentionBias.WAIT
        )

        if favors_buy:
            winning_ids, opposing_ids = buy_ids, sell_ids
            recommendation = Recommendation.BUY_SETUPS_ONLY
            what_is_happening = "Weighted evidence and horizon bias favor a BUY setup search."
            winning_weight = buy_weight
        elif favors_sell:
            winning_ids, opposing_ids = sell_ids, buy_ids
            recommendation = Recommendation.SELL_SETUPS_ONLY
            what_is_happening = "Weighted evidence and horizon bias favor a SELL setup search."
            winning_weight = sell_weight
        else:
            winning_ids, opposing_ids = [], buy_ids + sell_ids
            recommendation = Recommendation.WAIT
            what_is_happening = (
                "Directional evidence is balanced, absent, or conflicts with the "
                "dominant horizon bias."
            )
            winning_weight = 0.0

        trade_quality = round(100 * winning_weight / len(winning_ids)) if winning_ids else 0
        return (
            recommendation,
            trade_quality,
            what_is_happening,
            tuple(winning_ids),
            tuple(opposing_ids),
        )

    @staticmethod
    def _reliability(fresh: tuple[Evidence, ...], state: CurrentMarketState) -> int:
        state_reliability = state.confidence * (1 - state.uncertainty / 100)
        if not fresh:
            return round(min(100.0, max(0.0, state_reliability)))
        evidence_reliability = 100 * sum(item.reliability for item in fresh) / len(fresh)
        return round(min(100.0, max(0.0, (evidence_reliability + state_reliability) / 2)))

    @staticmethod
    def _absent_kinds(fresh: tuple[Evidence, ...]) -> tuple[EvidenceKind, ...]:
        present = {item.kind for item in fresh}
        return tuple(kind for kind in _CORE_KINDS if kind not in present)

    def _missing_evidence(
        self, fresh: tuple[Evidence, ...], value: ReasoningInput
    ) -> tuple[str, ...]:
        missing = [f"{kind.value} evidence is absent." for kind in self._absent_kinds(fresh)]
        if value.macro_context is None and value.macro_assessment is None:
            missing.append("Macro context and assessment are both absent.")
        return tuple(missing)

    def _stages(
        self,
        fresh: tuple[Evidence, ...],
        supporting: tuple[str, ...],
        contradicting: tuple[str, ...],
    ) -> tuple[StageReasoning, ...]:
        stages: list[StageReasoning] = []
        for stage in ReasoningStage:
            if stage is ReasoningStage.CONTRADICTIONS:
                status = StageStatus.CONTRADICTED if contradicting else StageStatus.COMPLETE
                evidence_ids = contradicting
            elif stage in (
                ReasoningStage.BIAS,
                ReasoningStage.TRADE_QUALITY,
                ReasoningStage.RECOMMENDATION,
            ):
                status = StageStatus.COMPLETE
                evidence_ids = supporting
            else:
                kinds = _STAGE_KINDS.get(stage, ())
                evidence_ids = tuple(item.evidence_id for item in fresh if item.kind in kinds)
                status = StageStatus.COMPLETE if evidence_ids else StageStatus.MISSING
            outcome = {
                StageStatus.COMPLETE: "evidence present",
                StageStatus.MISSING: "evidence missing",
                StageStatus.CONTRADICTED: "evidence contradicted",
            }[status]
            stages.append(StageReasoning(stage, status, f"{stage.value}: {outcome}.", evidence_ids))
        return tuple(stages)
