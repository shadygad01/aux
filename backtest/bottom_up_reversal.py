"""Frozen H-028 bottom-up reversal signal built only from closed bars.

H1 contributes location, M15 contributes the reversal event, and M5 must
confirm the new direction with established structure plus BOS.  Macro is not
included here because the repository has no point-in-time historical macro
series suitable for a leakage-safe backtest.
"""

from __future__ import annotations

from bisect import bisect_left, bisect_right
from collections.abc import Sequence
from datetime import datetime

from packages.domain import (
    DecisionVerdict,
    MarketObservation,
    MarketStructure,
    RangeLocation,
    StructureBias,
)
from packages.infrastructure.momentum import compute_atr
from packages.infrastructure.smc_detector import (
    DEFAULT_SWING_WINDOW,
    Candle,
    SwingPoint,
    build_dealing_range,
    build_observation_from_candles,
    classify_structure,
    find_swings,
)

from .mtf_feature_engine import FeatureSnapshot, _candles
from .mtf_models import BidAskBar, Direction
from .risk_guidance import compute_risk_guidance

HYPOTHESIS_ID = "H-028-bottom-up-reversal"
M15_REVERSAL_LOOKBACK = 4


def _closed_window(
    bars: Sequence[BidAskBar], closed_at: datetime, *, maximum: int
) -> list[BidAskBar]:
    end = bisect_right([bar.closed_at for bar in bars], closed_at)
    selected = list(bars[max(0, end - maximum) : end])
    if selected and selected[-1].closed_at > closed_at:
        raise AssertionError("future candle leaked into hypothesis window")
    return selected


def _choch_direction(observation: MarketObservation) -> Direction | None:
    structure = observation.structure
    if structure is None or not structure.change_of_character:
        return None
    if structure.bias is StructureBias.BULLISH:
        return Direction.SELL
    if structure.bias is StructureBias.BEARISH:
        return Direction.BUY
    return None


def _confirmed_direction(observation: MarketObservation) -> Direction | None:
    structure = observation.structure
    if structure is None or not structure.break_of_structure:
        return None
    if structure.bias is StructureBias.BULLISH:
        return Direction.BUY
    if structure.bias is StructureBias.BEARISH:
        return Direction.SELL
    return None


def _structure(bars: Sequence[BidAskBar]) -> MarketStructure | None:
    candles = _candles(bars)
    return classify_structure(find_swings(candles), candles)


def _rolling_structure(
    candles: Sequence[Candle],
    swings: Sequence[SwingPoint],
    swing_indices: Sequence[int],
    index: int,
    window: int,
) -> MarketStructure | None:
    start = max(0, index - window + 1)
    left = bisect_left(swing_indices, start + DEFAULT_SWING_WINDOW)
    right = bisect_right(swing_indices, index - DEFAULT_SWING_WINDOW)
    return classify_structure(swings[left:right], candles[start : index + 1])


def _choch_from_structure(structure: MarketStructure | None) -> Direction | None:
    if structure is None or not structure.change_of_character:
        return None
    if structure.bias is StructureBias.BULLISH:
        return Direction.SELL
    if structure.bias is StructureBias.BEARISH:
        return Direction.BUY
    return None


def _confirmed_from_structure(structure: MarketStructure | None) -> Direction | None:
    if structure is None or not structure.break_of_structure:
        return None
    if structure.bias is StructureBias.BULLISH:
        return Direction.BUY
    if structure.bias is StructureBias.BEARISH:
        return Direction.SELL
    return None


def build_bottom_up_snapshots(
    h1: Sequence[BidAskBar],
    m15: Sequence[BidAskBar],
    m5: Sequence[BidAskBar],
    *,
    window: int = 720,
) -> list[FeatureSnapshot]:
    """Return edge-triggered H-028 signals evaluated at each closed M5 bar."""
    snapshots: list[FeatureSnapshot] = []
    m5_closed = [bar.closed_at for bar in m5]
    h1_closed = [bar.closed_at for bar in h1]
    m15_candles = _candles(m15)
    m15_swings = find_swings(m15_candles)
    m15_swing_indices = [swing.index for swing in m15_swings]
    m5_candles = _candles(m5)
    m5_swings = find_swings(m5_candles)
    m5_swing_indices = [swing.index for swing in m5_swings]
    h1_candles = _candles(h1)
    h1_swings = find_swings(h1_candles)
    h1_swing_indices = [swing.index for swing in h1_swings]

    # Detect M15 reversal events once. The original definition keeps each
    # event eligible while it remains inside the latest four closed M15 bars.
    candidates: dict[int, tuple[Direction, datetime]] = {}
    for index in range(34, len(m15)):
        direction = _choch_from_structure(
            _rolling_structure(
                m15_candles, m15_swings, m15_swing_indices, index, window
            )
        )
        if direction is None:
            continue
        start = bisect_left(m5_closed, m15[index].closed_at)
        cutoff = (
            m15[index + M15_REVERSAL_LOOKBACK].closed_at
            if (index + M15_REVERSAL_LOOKBACK < len(m15))
            else m5_closed[-1]
        )
        end = bisect_left(m5_closed, cutoff)
        for m5_index in range(start, end):
            candidates[m5_index] = (direction, m15[index].closed_at)

    previous_active: Direction | None = None
    previous_index: int | None = None
    h1_location_cache: dict[int, RangeLocation | None] = {}
    for m5_index, reversal in sorted(candidates.items()):
        if m5_index < 59:
            continue
        if previous_index is None or m5_index != previous_index + 1:
            previous_active = None
        previous_index = m5_index
        decision_time = m5[m5_index].closed_at
        h1_end = bisect_right(h1_closed, decision_time)
        h1_window = list(h1[max(0, h1_end - window) : h1_end])
        m5_window = list(m5[max(0, m5_index - window + 1) : m5_index + 1])
        if len(h1_window) < 35:
            continue
        direction, reversal_time = reversal
        if h1_end not in h1_location_cache:
            h1_index = h1_end - 1
            h1_start = max(0, h1_end - window)
            left = bisect_left(h1_swing_indices, h1_start + DEFAULT_SWING_WINDOW)
            right = bisect_right(h1_swing_indices, h1_index - DEFAULT_SWING_WINDOW)
            dealing_range = build_dealing_range(
                h1_swings[left:right], h1_candles[h1_index].close
            )
            h1_location_cache[h1_end] = (
                dealing_range.location(0.02) if dealing_range is not None else None
            )
        location = h1_location_cache[h1_end]
        required_location = (
            RangeLocation.DISCOUNT if direction is Direction.BUY else RangeLocation.PREMIUM
        )
        if location is not required_location:
            previous_active = None
            continue

        if (
            _confirmed_from_structure(
                _rolling_structure(
                    m5_candles, m5_swings, m5_swing_indices, m5_index, window
                )
            )
            is not direction
        ):
            previous_active = None
            continue
        m5_observation = build_observation_from_candles(
            _candles(m5_window),
            symbol="XAUUSD",
            timeframe="M5",
            source="dukascopy-ticks-derived",
        )
        if direction is previous_active:
            continue
        previous_active = direction

        atr = compute_atr(_candles(m5_window))
        verdict = DecisionVerdict.BUY if direction is Direction.BUY else DecisionVerdict.SELL
        risk = compute_risk_guidance(m5_observation, verdict, atr)
        if atr is None or risk.risk_status != "OK" or risk.stop_distance is None:
            continue
        snapshots.append(
            FeatureSnapshot(
                timestamp=decision_time,
                direction=direction,
                features={
                    "hypothesis_id": HYPOTHESIS_ID,
                    "h1_location": location.value,
                    "m15_choch_direction": direction.value,
                    "m15_reversal_time": reversal_time.isoformat(),
                    "m5_bos": True,
                    "macro_filter": "UNTESTED_NO_POINT_IN_TIME_SERIES",
                },
                stop_distance=risk.stop_distance,
                atr=atr,
            )
        )
    return snapshots
