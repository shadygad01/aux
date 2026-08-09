"""Multi-Timeframe Scalping Engine implementation.

Cascades M15 lower timeframe execution triggers from H1 higher timeframe structural bias.
Strictly blocks execution if lower timeframe signals contradict higher timeframe bias.

Also computes market-derived risk guidance (stop/target/risk-reward, plus a
partial-exit and trailing-stop exit plan) for the execution timeframe -- see
`_compute_risk_guidance`. This replaces fixed `tight_stop_loss_pips`/
`target_rr` constants (12.5/18.0 pips, 3.2/2.8 RR) that were never derived
from any market data; see docs/adr/0007-engine-consolidation.md and the
Multi-Timeframe risk model design report for the original investigation,
and docs/hypothesis-register.md H-026 for the rr_multiple-target and
partial-exit methodology this module now uses.
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

CALCULATION_METHOD = "structure_atr_rr_multiple_v2"

# Implementation default only -- NOT empirically validated. No historical or
# walk-forward evidence exists in this repository to calibrate this value
# (see docs/hypothesis-register.md and TD-014); it must be treated as a
# placeholder pending future research, not as trading truth. It never
# influences direction -- only how far beyond the structural invalidation
# level the stop is buffered.
ATR_BUFFER_MULTIPLIER = 0.5

# The following four constants ARE empirically validated -- unlike
# ATR_BUFFER_MULTIPLIER above. The owner ran exhaustive walk-forward
# backtesting on 5 years of real XAUUSD M15 data (single train(2021-2023)/
# test(2024-2026) split, plus an independent 4-way expanding-window
# per-year check spanning all of 2021-2026) to search rr_multiple targets,
# partial-exit fractions, and trailing-stop distances. See
# docs/hypothesis-register.md H-026 for the full methodology, results, and
# -- just as important -- its disclosed limits: spread/commission/slippage
# and manual (non-instant) trade entry are NOT modeled in any of it, and
# the underlying sample is a few hundred trades, not thousands. Treat these
# as the best evidence-backed defaults available today, not as guarantees.
#
# RR_TARGET_MULTIPLE also directly satisfies the owner's explicit minimum
# reward:risk requirement (at least 1:3) -- 4 clears it with margin.
RR_TARGET_MULTIPLE = 4.0
RR_PARTIAL_MULTIPLE = 2.0
PARTIAL_FRACTION = 0.5
TRAIL_ATR_MULTIPLE = 0.5


class MultiTimeframeEngine:
    """Evaluates M5/M15 lower timeframe triggers cascaded from H1 structural
    bias. Timeframe-agnostic: which one is "the" execution timeframe is a
    wiring decision made by the caller (publish/generators/multi_timeframe.py
    uses M15 in production -- see docs/hypothesis-register.md H-026 for why)."""

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
    """Structure/liquidity defines the stop's invalidation level; ATR
    buffers it -- unchanged. The target is NOT structure/liquidity-derived
    anymore: target = entry +/- RR_TARGET_MULTIPLE * stop_distance, which
    guarantees a minimum RR_TARGET_MULTIPLE:1 reward-to-risk by
    construction rather than whatever a resting liquidity level happens to
    offer (see docs/hypothesis-register.md H-026). Because the target is
    now derived FROM stop_distance, it -- like the stop itself -- requires
    ATR and is unavailable whenever ATR or the stop can't be computed
    (this is new: the previous structure-derived target didn't need ATR).
    A validated partial-exit/trailing-stop exit plan (RR_PARTIAL_MULTIPLE,
    PARTIAL_FRACTION, TRAIL_ATR_MULTIPLE) rides alongside the target as
    additional guidance. Never fabricates a value it cannot derive -- every
    unavailable input degrades `risk_status` instead."""
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

    if atr is None:
        return RiskGuidance(
            entry_price=entry_price,
            stop_loss_price=None,
            target_price=None,
            stop_distance=None,
            target_distance=None,
            risk_reward=None,
            invalidation_level=round(invalidation_level, 2),
            invalidation_source=invalidation_source,
            atr=None,
            target_source=None,
            risk_status="INSUFFICIENT_DATA",
            calculation_method=CALCULATION_METHOD,
        )

    buffer = atr * ATR_BUFFER_MULTIPLIER
    stop_loss_price = invalidation_level - buffer if is_buy else invalidation_level + buffer
    stop_distance = (entry_price - stop_loss_price) if is_buy else (stop_loss_price - entry_price)

    if stop_distance <= 0:
        return RiskGuidance(
            entry_price=entry_price,
            stop_loss_price=round(stop_loss_price, 2),
            target_price=None,
            stop_distance=round(abs(entry_price - stop_loss_price), 2),
            target_distance=None,
            risk_reward=None,
            invalidation_level=round(invalidation_level, 2),
            invalidation_source=invalidation_source,
            atr=round(atr, 4),
            target_source=None,
            risk_status="UNAVAILABLE",
            calculation_method=CALCULATION_METHOD,
        )

    target_price = (
        entry_price + RR_TARGET_MULTIPLE * stop_distance
        if is_buy
        else entry_price - RR_TARGET_MULTIPLE * stop_distance
    )
    partial_target_price = (
        entry_price + RR_PARTIAL_MULTIPLE * stop_distance
        if is_buy
        else entry_price - RR_PARTIAL_MULTIPLE * stop_distance
    )

    return RiskGuidance(
        entry_price=entry_price,
        stop_loss_price=round(stop_loss_price, 2),
        target_price=round(target_price, 2),
        stop_distance=round(stop_distance, 2),
        target_distance=round(RR_TARGET_MULTIPLE * stop_distance, 2),
        risk_reward=RR_TARGET_MULTIPLE,
        invalidation_level=round(invalidation_level, 2),
        invalidation_source=invalidation_source,
        atr=round(atr, 4),
        target_source="RR_MULTIPLE",
        risk_status="OK",
        calculation_method=CALCULATION_METHOD,
        partial_target_price=round(partial_target_price, 2),
        partial_fraction=PARTIAL_FRACTION,
        breakeven_price=round(entry_price, 2),
        trailing_stop_distance=round(TRAIL_ATR_MULTIPLE * atr, 2),
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
