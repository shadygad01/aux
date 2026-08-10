"""Research-only risk simulation retained for reproducibility.

This module is deliberately outside the production graph. Its constants are
experimental assumptions and can never appear in the published market data.
"""

from __future__ import annotations

from dataclasses import dataclass

from packages.domain import DealingRange, DecisionVerdict, LiquiditySide, MarketObservation

ATR_BUFFER_MULTIPLIER = 0.5
RR_TARGET_MULTIPLE = 4.0
RR_PARTIAL_MULTIPLE = 2.0
PARTIAL_FRACTION = 0.5
TRAIL_ATR_MULTIPLE = 0.5


@dataclass(frozen=True, slots=True)
class RiskGuidance:
    entry_price: float | None
    stop_loss_price: float | None
    target_price: float | None
    stop_distance: float | None
    target_distance: float | None
    risk_reward: float | None
    invalidation_level: float | None
    invalidation_source: str | None
    atr: float | None
    target_source: str | None
    risk_status: str
    calculation_method: str = "research_structure_atr_rr_v1"
    partial_target_price: float | None = None
    partial_fraction: float | None = None
    breakeven_price: float | None = None
    trailing_stop_distance: float | None = None


def compute_risk_guidance(
    observation: MarketObservation, verdict: DecisionVerdict, atr: float | None
) -> RiskGuidance:
    dealing_range = observation.dealing_range
    if verdict is DecisionVerdict.WAIT or dealing_range is None:
        return RiskGuidance(
            dealing_range.current_price if dealing_range else None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            atr,
            None,
            "UNAVAILABLE" if dealing_range else "INSUFFICIENT_DATA",
        )
    entry = dealing_range.current_price
    is_buy = verdict is DecisionVerdict.BUY
    invalidation, source = _select_invalidation(observation, dealing_range, is_buy)
    if atr is None:
        return RiskGuidance(
            entry,
            None,
            None,
            None,
            None,
            None,
            invalidation,
            source,
            None,
            None,
            "INSUFFICIENT_DATA",
        )
    stop = (
        invalidation - atr * ATR_BUFFER_MULTIPLIER
        if is_buy
        else invalidation + atr * ATR_BUFFER_MULTIPLIER
    )
    distance = entry - stop if is_buy else stop - entry
    if distance <= 0:
        return RiskGuidance(
            entry,
            round(stop, 2),
            None,
            abs(round(distance, 2)),
            None,
            None,
            round(invalidation, 2),
            source,
            round(atr, 4),
            None,
            "UNAVAILABLE",
        )
    sign = 1 if is_buy else -1
    return RiskGuidance(
        entry_price=entry,
        stop_loss_price=round(stop, 2),
        target_price=round(entry + sign * RR_TARGET_MULTIPLE * distance, 2),
        stop_distance=round(distance, 2),
        target_distance=round(RR_TARGET_MULTIPLE * distance, 2),
        risk_reward=RR_TARGET_MULTIPLE,
        invalidation_level=round(invalidation, 2),
        invalidation_source=source,
        atr=round(atr, 4),
        target_source="RR_MULTIPLE",
        risk_status="OK",
        partial_target_price=round(entry + sign * RR_PARTIAL_MULTIPLE * distance, 2),
        partial_fraction=PARTIAL_FRACTION,
        breakeven_price=round(entry, 2),
        trailing_stop_distance=round(TRAIL_ATR_MULTIPLE * atr, 2),
    )


def _select_invalidation(
    observation: MarketObservation, dealing_range: DealingRange, is_buy: bool
) -> tuple[float, str]:
    side = LiquiditySide.SELL_SIDE if is_buy else LiquiditySide.BUY_SIDE
    level = next(
        (
            event.level
            for event in observation.liquidity
            if event.side is side and event.swept and event.level is not None
        ),
        None,
    )
    if level is not None:
        return level, "LIQUIDITY_SWEEP"
    return (dealing_range.low if is_buy else dealing_range.high), "DEALING_RANGE"
