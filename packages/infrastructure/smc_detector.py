"""Smart Money Concepts structure detection from a real OHLC candle series.

Pure, deterministic functions: fractal swing detection, structure bias
(higher-high/higher-low vs lower-high/lower-low), the current dealing range,
and liquidity-sweep-with-displacement detection. No network calls here —
see `live_collector.py` for fetching the candle series itself.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

from packages.domain import (
    DealingRange,
    LiquidityEvent,
    LiquiditySide,
    MarketObservation,
    MarketStructure,
    SmcAssessment,
    StructureBias,
)

MIN_CANDLES_FOR_STRUCTURE = 20
DEFAULT_SWING_WINDOW = 3
DISPLACEMENT_BODY_RATIO = 0.5
REVERSAL_WICK_TO_BODY_RATIO = 2.0
REVERSAL_MAX_BODY_RANGE_RATIO = 0.35


@dataclass(frozen=True, slots=True)
class Candle:
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float


class SwingKind(StrEnum):
    HIGH = "HIGH"
    LOW = "LOW"


@dataclass(frozen=True, slots=True)
class SwingPoint:
    index: int
    timestamp: datetime
    price: float
    kind: SwingKind


def find_swings(candles: Sequence[Candle], window: int = DEFAULT_SWING_WINDOW) -> list[SwingPoint]:
    """Fractal swing detection: a candle is a swing high/low if it is the unique
    extreme within `window` candles on both sides."""
    swings: list[SwingPoint] = []
    total = len(candles)
    for i in range(window, total - window):
        segment = candles[i - window : i + window + 1]
        candle = candles[i]

        highs = [c.high for c in segment]
        if candle.high == max(highs) and highs.count(candle.high) == 1:
            swings.append(SwingPoint(i, candle.timestamp, candle.high, SwingKind.HIGH))

        lows = [c.low for c in segment]
        if candle.low == min(lows) and lows.count(candle.low) == 1:
            swings.append(SwingPoint(i, candle.timestamp, candle.low, SwingKind.LOW))
    return swings


def _alternating_swings(swings: Sequence[SwingPoint]) -> list[SwingPoint]:
    """Collapse raw fractal swings into a clean alternating H/L/H/L sequence,
    keeping the more extreme point whenever two consecutive swings share a kind."""
    ordered = sorted(swings, key=lambda s: s.index)
    cleaned: list[SwingPoint] = []
    for swing in ordered:
        if cleaned and cleaned[-1].kind == swing.kind:
            more_extreme = (
                swing.price > cleaned[-1].price
                if swing.kind == SwingKind.HIGH
                else swing.price < cleaned[-1].price
            )
            if more_extreme:
                cleaned[-1] = swing
            continue
        cleaned.append(swing)
    return cleaned


def classify_structure(swings: Sequence[SwingPoint], last_close: float) -> MarketStructure | None:
    """Bias from the last two swing highs and last two swing lows (HH+HL vs LH+LL).
    Returns None when there isn't enough swing history to classify at all."""
    alt = _alternating_swings(swings)
    highs = [s for s in alt if s.kind == SwingKind.HIGH]
    lows = [s for s in alt if s.kind == SwingKind.LOW]
    if len(highs) < 2 or len(lows) < 2:
        return None

    higher_high = highs[-1].price > highs[-2].price
    higher_low = lows[-1].price > lows[-2].price
    lower_high = highs[-1].price < highs[-2].price
    lower_low = lows[-1].price < lows[-2].price

    if higher_high and higher_low:
        return MarketStructure(
            bias=StructureBias.BULLISH,
            break_of_structure=last_close > highs[-1].price,
            change_of_character=last_close < lows[-1].price,
        )
    if lower_high and lower_low:
        return MarketStructure(
            bias=StructureBias.BEARISH,
            break_of_structure=last_close < lows[-1].price,
            change_of_character=last_close > highs[-1].price,
        )
    return MarketStructure(
        bias=StructureBias.NEUTRAL, break_of_structure=False, change_of_character=False
    )


def build_dealing_range(swings: Sequence[SwingPoint], current_price: float) -> DealingRange | None:
    """The dealing range is bounded by the two most recent alternating swings
    (one high, one low), extended to include the current price if price has
    already moved past the last confirmed extreme."""
    alt = _alternating_swings(swings)
    if len(alt) < 2:
        return None
    # _alternating_swings guarantees no two consecutive entries share a kind,
    # so exactly one of the last two is a high and the other a low.
    second_last, last = alt[-2], alt[-1]

    high_swing = last if last.kind == SwingKind.HIGH else second_last
    low_swing = second_last if last.kind == SwingKind.HIGH else last

    high = max(high_swing.price, current_price)
    low = min(low_swing.price, current_price)
    if high <= low:
        return None
    return DealingRange(low=low, high=high, current_price=current_price)


def detect_sweep_from_swing(candles: Sequence[Candle], swing: SwingPoint) -> LiquidityEvent:
    """Scan forward from a swing point for a wick-through-and-reclaim (sweep),
    confirmed by a strong-bodied candle in the reversal direction (displacement)."""
    side = LiquiditySide.BUY_SIDE if swing.kind == SwingKind.HIGH else LiquiditySide.SELL_SIDE

    for i in range(swing.index + 1, len(candles)):
        candle = candles[i]
        if swing.kind == SwingKind.HIGH:
            swept = candle.high > swing.price and candle.close < swing.price
        else:
            swept = candle.low < swing.price and candle.close > swing.price

        if not swept:
            continue

        # A sweep candle is often a thin-bodied wick by itself; the confirming
        # momentum ("displacement") commonly shows up on the very next candle
        # instead, so either counts as confirmation.
        displacement = _is_displacement(candle, swing.kind)
        if not displacement and i + 1 < len(candles):
            displacement = _is_displacement(candles[i + 1], swing.kind)
        return LiquidityEvent(
            side=side, swept=True, displacement_confirmed=displacement, level=swing.price
        )

    return LiquidityEvent(side=side, swept=False, displacement_confirmed=False, level=swing.price)


def _is_displacement(candle: Candle, swept_kind: SwingKind) -> bool:
    candle_range = candle.high - candle.low
    body = abs(candle.close - candle.open)
    strong_body = candle_range > 0 and (body / candle_range) >= DISPLACEMENT_BODY_RATIO
    reversal_direction = (
        candle.close < candle.open if swept_kind == SwingKind.HIGH else candle.close > candle.open
    )
    return strong_body and reversal_direction


def detect_reversal_candle(candles: Sequence[Candle], swing: SwingPoint) -> bool:
    """A pin-bar-style rejection at the swing extreme: a small body dominated
    by a long wick on the swept side. Checked on the swing candle itself and
    the one immediately after it — the same window `detect_sweep_from_swing`
    uses for displacement, since the rejection wick commonly prints on the
    follow-through candle rather than the extreme candle itself."""
    for index in (swing.index, swing.index + 1):
        if index < len(candles) and _is_reversal_candle(candles[index], swing.kind):
            return True
    return False


def _is_reversal_candle(candle: Candle, swing_kind: SwingKind) -> bool:
    candle_range = candle.high - candle.low
    if candle_range <= 0:
        return False
    body = abs(candle.close - candle.open)
    if body / candle_range > REVERSAL_MAX_BODY_RANGE_RATIO:
        return False
    rejection_wick = (
        min(candle.open, candle.close) - candle.low
        if swing_kind == SwingKind.LOW
        else candle.high - max(candle.open, candle.close)
    )
    if rejection_wick <= 0:
        return False
    return body == 0 or rejection_wick / body >= REVERSAL_WICK_TO_BODY_RATIO


def detect_liquidity_events(
    candles: Sequence[Candle], swings: Sequence[SwingPoint]
) -> tuple[LiquidityEvent, ...]:
    """Liquidity resting beyond the most recent swing high (BUY_SIDE) and the
    most recent swing low (SELL_SIDE), checked for a sweep-and-reclaim."""
    alt = _alternating_swings(swings)
    highs = [s for s in alt if s.kind == SwingKind.HIGH]
    lows = [s for s in alt if s.kind == SwingKind.LOW]

    events: list[LiquidityEvent] = []
    if highs:
        events.append(detect_sweep_from_swing(candles, highs[-1]))
    if lows:
        events.append(detect_sweep_from_swing(candles, lows[-1]))
    return tuple(events)


def build_observation_from_candles(
    candles: Sequence[Candle],
    *,
    symbol: str,
    timeframe: str,
    source: str,
    swing_window: int = DEFAULT_SWING_WINDOW,
    macd_value: float | None = None,
) -> MarketObservation:
    """Build a MarketObservation from real candles. Structure and dealing range
    are None when there isn't enough swing history to classify — the decision
    engine already treats missing evidence as a hard WAIT gate, so an honest
    None here is correct, not a bug to work around.

    `macd_value` is a pass-through, not computed here: this module must not
    import packages.infrastructure.momentum (that module already imports
    Candle from here, so the reverse import would be circular). Callers that
    already have the same candles in scope (LiveMarketCollector,
    market_story.py) compute it once via compute_macd() and pass the result
    through."""
    if len(candles) < MIN_CANDLES_FOR_STRUCTURE:
        raise ValueError(
            f"insufficient candles for structure detection: got {len(candles)}, "
            f"need at least {MIN_CANDLES_FOR_STRUCTURE}"
        )

    last = candles[-1]
    swings = find_swings(candles, window=swing_window)
    structure = classify_structure(swings, last.close)
    dealing_range = build_dealing_range(swings, last.close)
    liquidity = detect_liquidity_events(candles, swings)

    return MarketObservation(
        symbol=symbol,
        timeframe=timeframe,
        observed_at=last.timestamp,
        structure=structure,
        dealing_range=dealing_range,
        liquidity=liquidity,
        source=source,
        macd_value=macd_value,
    )


def build_smc_assessment_from_candles(
    candles: Sequence[Candle], swing_window: int = DEFAULT_SWING_WINDOW
) -> SmcAssessment | None:
    """SMC evidence for the trading-opportunity engine: the liquidity sweep and
    reversal candle at the swing relevant to the current structural bias (the
    swept low under a bullish thesis, the swept high under a bearish one).
    None when there isn't enough swing history to classify a bias, matching
    `build_observation_from_candles`'s honest-gap convention. order_block and
    fair_value_gap are not detected here and stay False — an honest gap, not
    a fabricated confirmation."""
    swings = find_swings(candles, window=swing_window)
    structure = classify_structure(swings, candles[-1].close)
    if structure is None or structure.bias is StructureBias.NEUTRAL:
        return None

    relevant_kind = SwingKind.LOW if structure.bias is StructureBias.BULLISH else SwingKind.HIGH
    relevant_swings = [s for s in _alternating_swings(swings) if s.kind == relevant_kind]
    if not relevant_swings:
        return None
    swing = relevant_swings[-1]

    return SmcAssessment(
        liquidity_event=detect_sweep_from_swing(candles, swing),
        reversal_candle_confirmed=detect_reversal_candle(candles, swing),
        change_of_character=structure.change_of_character,
    )
