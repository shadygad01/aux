"""Derives TradeQuality and MarketThesis from a real Decision — no fabricated scores.

Previously several publish generators hardcoded DecisionVerdict.BUY and a
setup_quality_score of 94 straight into their engine calls, regardless of what
the live observation actually showed. This module replaces that with values
derived from the same DecisionEngine evaluation that decision.json itself
publishes, so every artifact describes the same real evidence consistently.
"""

from __future__ import annotations

from packages.domain import (
    Decision,
    DecisionPolicy,
    DecisionVerdict,
    ExecutionReadiness,
    LiquiditySide,
    MarketObservation,
    MarketThesis,
    RangeLocation,
    StructureBias,
    TradeQuality,
    TradeQualityGrade,
)

_GRADE_THRESHOLDS: tuple[tuple[int, TradeQualityGrade], ...] = (
    (90, TradeQualityGrade.EXCELLENT),
    (75, TradeQualityGrade.GOOD),
    (50, TradeQualityGrade.MODERATE),
    (25, TradeQualityGrade.WEAK),
)


def _grade_for_score(score: int) -> TradeQualityGrade:
    for threshold, grade in _GRADE_THRESHOLDS:
        if score >= threshold:
            return grade
    return TradeQualityGrade.INVALID


def _component_breakdown(observation: MarketObservation, policy: DecisionPolicy) -> dict[str, int]:
    """Mirrors DecisionEngine's own structure/location/liquidity checks so the
    breakdown reflects exactly what drove the score — not a separate guess.

    Keyed off the structural bias (the engine's "candidate" direction), not
    the final verdict: a conflict can still push the verdict to WAIT even
    when structure/location/liquidity partially aligned, and decision.score
    already reflects that partial alignment — this breakdown should match it.
    """
    structure = observation.structure
    dealing_range = observation.dealing_range
    if structure is None or dealing_range is None or structure.bias is StructureBias.NEUTRAL:
        return {}

    candidate = (
        DecisionVerdict.BUY if structure.bias is StructureBias.BULLISH else DecisionVerdict.SELL
    )
    required_location = (
        RangeLocation.DISCOUNT if candidate is DecisionVerdict.BUY else RangeLocation.PREMIUM
    )
    required_sweep = (
        LiquiditySide.SELL_SIDE if candidate is DecisionVerdict.BUY else LiquiditySide.BUY_SIDE
    )
    location = dealing_range.location(policy.equilibrium_band)
    liquidity_ok = any(
        event.side is required_sweep and event.swept and event.displacement_confirmed
        for event in observation.liquidity
    )

    return {
        "structure": round(policy.structure_weight * 100) if structure.break_of_structure else 0,
        "location": round(policy.location_weight * 100) if location is required_location else 0,
        "liquidity": round(policy.liquidity_weight * 100) if liquidity_ok else 0,
    }


def derive_trade_quality(
    observation: MarketObservation, decision: Decision, policy: DecisionPolicy
) -> TradeQuality:
    score = round(decision.score * 100)
    breakdown = _component_breakdown(observation, policy)

    if decision.reasons:
        explanation = " ".join(decision.reasons)
    elif decision.conflicts:
        explanation = " ".join(decision.conflicts)
    elif decision.missing_evidence:
        explanation = " ".join(decision.missing_evidence)
    else:
        explanation = f"{decision.verdict.value} evaluation."

    return TradeQuality(
        score=score, grade=_grade_for_score(score), breakdown=breakdown, explanation=explanation
    )


def build_market_thesis(
    *,
    thesis_id: str,
    observation: MarketObservation,
    decision: Decision,
    trade_quality: TradeQuality,
    execution_readiness: ExecutionReadiness | None,
) -> MarketThesis:
    meaning = (
        "Search for a high-quality setup"
        if decision.verdict is not DecisionVerdict.WAIT
        else "Do not search for a setup yet"
    )
    return MarketThesis(
        thesis_id=thesis_id,
        symbol=observation.symbol,
        timeframe=observation.timeframe,
        verdict=decision.verdict,
        meaning=meaning,
        confidence=decision.confidence.value,
        confidence_score=decision.score,
        uncertainty_score=round(1.0 - decision.score, 4),
        setup_quality_score=trade_quality.score,
        execution_readiness=execution_readiness,
        trade_quality=trade_quality,
        reasons=decision.reasons,
        conflicts=decision.conflicts,
        missing_evidence=decision.missing_evidence,
        evaluated_at=decision.evaluated_at,
        policy_version=decision.policy_version,
        contract_version=decision.contract_version,
    )
