"""Multi-Timeframe Scalping Engine implementation.

Cascades M5/M15 lower timeframe execution triggers from H1 higher timeframe structural bias.
Strictly blocks execution if lower timeframe signals contradict higher timeframe bias.

Also computes market-derived risk guidance (stop/target/risk-reward) for the
execution timeframe -- see `_compute_risk_guidance`. This replaces fixed
`tight_stop_loss_pips`/`target_rr` constants (12.5/18.0 pips, 3.2/2.8 RR)
that were never derived from any market data; see
docs/adr/0007-engine-consolidation.md and the Multi-Timeframe risk model
design report for the full investigation and rationale.
"""

from __future__ import annotations

from datetime import datetime

from packages.domain import (
    DealingRange,
    DecisionVerdict,
    ExecutionReadiness,
    LiquiditySide,
    MarketObservation,
    MarketThesis,
    MultiTimeframeThesis,
    RiskGuidance,
    StructureBias,
)

CALCULATION_METHOD = "structure_atr_liquidity_v1"

# Implementation default only -- NOT empirically validated. No historical or
# walk-forward evidence exists in this repository to calibrate this value
# (see docs/hypothesis-register.md and TD-014); it must be treated as a
# placeholder pending future research, not as trading truth. It never
# influences direction -- only how far beyond the structural invalidation
# level the stop is buffered.
ATR_BUFFER_MULTIPLIER = 0.5


class MultiTimeframeEngine:
    """Evaluates M5/M15 lower timeframe triggers cascaded from H1 structural bias."""

    def evaluate_multi_timeframe(
        self,
        htf_thesis: MarketThesis,
        ltf_observation: MarketObservation,
        execution_readiness: ExecutionReadiness,
        evaluated_at: datetime,
        atr: float | None,
    ) -> MultiTimeframeThesis:
        symbol = ltf_observation.symbol
        htf_bias = htf_thesis.verdict
        ltf_tf = ltf_observation.execution_timeframe

        # Check alignment -- unchanged from before this risk-model addition.
        reasons: list[str] = []
        ltf_bias = ltf_observation.structure.bias if ltf_observation.structure else None

        if htf_bias is DecisionVerdict.WAIT:
            cascade_status = "WAIT_HTF"
            reasons.append("Higher timeframe (H1) bias is WAIT. Execution blocked.")
            trigger = f"{ltf_tf} setup blocked by H1 WAIT status."
        elif ltf_bias == StructureBias.BEARISH and htf_bias is DecisionVerdict.BUY:
            cascade_status = "CONFLICT"
            reasons.append(f"{ltf_tf} structure opposes H1 BUY bias. Execution strictly blocked.")
            trigger = f"{ltf_tf} bearish structure contradicts H1 BUY bias."
        elif ltf_bias == StructureBias.BULLISH and htf_bias is DecisionVerdict.SELL:
            cascade_status = "CONFLICT"
            reasons.append(f"{ltf_tf} structure opposes H1 SELL bias. Execution strictly blocked.")
            trigger = f"{ltf_tf} bullish structure contradicts H1 SELL bias."
        else:
            cascade_status = "ALIGNED"
            reasons.append(f"H1 bias ({htf_bias}) is aligned with {ltf_tf} entry trigger.")
            if ltf_observation.structure and ltf_observation.structure.break_of_structure:
                reasons.append(f"{ltf_tf} structure confirms a break of structure with H1.")
                trigger = f"{ltf_tf} break of structure aligned with H1 {htf_bias}."
            else:
                trigger = f"{ltf_tf} structure aligned with H1 {htf_bias}; no {ltf_tf} BOS yet."

        risk_guidance = _compute_risk_guidance(ltf_observation, htf_bias, atr)

        return MultiTimeframeThesis(
            thesis_id=f"MTF-{evaluated_at.strftime('%Y%m%d')}-01",
            symbol=symbol,
            higher_timeframe="H1",
            execution_timeframe=ltf_tf,
            htf_bias=htf_bias,
            ltf_trigger=trigger,
            cascade_status=cascade_status,
            setup_quality_score=htf_thesis.setup_quality_score,
            execution_readiness=execution_readiness,
            risk_guidance=risk_guidance,
            reasons=tuple(reasons),
            evaluated_at=evaluated_at,
        )


def _compute_risk_guidance(
    observation: MarketObservation, verdict: DecisionVerdict, atr: float | None
) -> RiskGuidance:
    """Structure/liquidity defines invalidation; ATR only buffers it. Target
    comes from opposing execution-timeframe liquidity, falling back to the
    dealing-range boundary. R:R is always computed from the resulting
    prices, never assigned. Never fabricates a value it cannot derive --
    every unavailable input degrades `risk_status` instead."""
    dealing_range = observation.dealing_range

    if verdict is DecisionVerdict.WAIT or dealing_range is None:
        return RiskGuidance(
            entry_price=dealing_range.current_price if dealing_range else None,
            stop_loss_price=None,
            target_price=None,
            stop_distance=None,
            target_distance=None,
            risk_reward=None,
            invalidation_level=None,
            invalidation_source=None,
            atr=atr,
            target_source=None,
            risk_status="UNAVAILABLE" if dealing_range is not None else "INSUFFICIENT_DATA",
            calculation_method=CALCULATION_METHOD,
        )

    entry_price = dealing_range.current_price
    is_buy = verdict is DecisionVerdict.BUY

    invalidation_level, invalidation_source = _select_invalidation(
        observation, dealing_range, is_buy
    )
    target_price, target_source = _select_target(observation, dealing_range, entry_price, is_buy)

    if atr is None:
        return RiskGuidance(
            entry_price=entry_price,
            stop_loss_price=None,
            target_price=target_price,
            stop_distance=None,
            target_distance=round(abs(target_price - entry_price), 2),
            risk_reward=None,
            invalidation_level=round(invalidation_level, 2),
            invalidation_source=invalidation_source,
            atr=None,
            target_source=target_source,
            risk_status="INSUFFICIENT_DATA",
            calculation_method=CALCULATION_METHOD,
        )

    buffer = atr * ATR_BUFFER_MULTIPLIER
    stop_loss_price = invalidation_level - buffer if is_buy else invalidation_level + buffer

    risk = (entry_price - stop_loss_price) if is_buy else (stop_loss_price - entry_price)
    reward = (target_price - entry_price) if is_buy else (entry_price - target_price)

    if risk <= 0 or reward <= 0:
        return RiskGuidance(
            entry_price=entry_price,
            stop_loss_price=round(stop_loss_price, 2),
            target_price=round(target_price, 2),
            stop_distance=round(abs(entry_price - stop_loss_price), 2),
            target_distance=round(abs(target_price - entry_price), 2),
            risk_reward=None,
            invalidation_level=round(invalidation_level, 2),
            invalidation_source=invalidation_source,
            atr=round(atr, 4),
            target_source=target_source,
            risk_status="UNAVAILABLE",
            calculation_method=CALCULATION_METHOD,
        )

    return RiskGuidance(
        entry_price=entry_price,
        stop_loss_price=round(stop_loss_price, 2),
        target_price=round(target_price, 2),
        stop_distance=round(abs(entry_price - stop_loss_price), 2),
        target_distance=round(abs(target_price - entry_price), 2),
        risk_reward=round(reward / risk, 2),
        invalidation_level=round(invalidation_level, 2),
        invalidation_source=invalidation_source,
        atr=round(atr, 4),
        target_source=target_source,
        risk_status="OK",
        calculation_method=CALCULATION_METHOD,
    )


def _select_invalidation(
    observation: MarketObservation, dealing_range: DealingRange, is_buy: bool
) -> tuple[float, str]:
    """Primary: the swept liquidity level on the side that justified this
    direction (SELL_SIDE swept below price for a BUY; BUY_SIDE swept above
    price for a SELL) -- the same level the mandatory SMC sweep gate already
    requires. Fallback: the dealing-range boundary, when no precise level is
    available (e.g. an observation built before LiquidityEvent.level
    existed)."""
    side = LiquiditySide.SELL_SIDE if is_buy else LiquiditySide.BUY_SIDE
    swept_level = next(
        (
            event.level
            for event in observation.liquidity
            if event.side is side and event.swept and event.level is not None
        ),
        None,
    )
    if swept_level is not None:
        return swept_level, "LIQUIDITY_SWEEP"
    return (dealing_range.low if is_buy else dealing_range.high), "DEALING_RANGE"


def _select_target(
    observation: MarketObservation, dealing_range: DealingRange, entry_price: float, is_buy: bool
) -> tuple[float, str]:
    """Tier 1: the opposing execution-timeframe liquidity level (resting
    liquidity on the far side -- the natural draw for price), if it exists
    and is directionally valid. Tier 2: the dealing-range boundary, always
    available and always directionally valid by DealingRange's own
    invariant (current_price is strictly inside [low, high])."""
    side = LiquiditySide.BUY_SIDE if is_buy else LiquiditySide.SELL_SIDE
    opposing_level = next(
        (
            event.level
            for event in observation.liquidity
            if event.side is side and event.level is not None
        ),
        None,
    )
    if opposing_level is not None and (
        (is_buy and opposing_level > entry_price) or (not is_buy and opposing_level < entry_price)
    ):
        return opposing_level, "EXECUTION_LIQUIDITY"
    return (dealing_range.high if is_buy else dealing_range.low), "DEALING_RANGE"
