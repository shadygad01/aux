"""Deterministic, network-free tests for real SMC structure detection from candles."""

from __future__ import annotations

import unittest
from collections.abc import Sequence
from datetime import UTC, datetime, timedelta

from packages.domain import LiquiditySide, StructureBias
from packages.infrastructure.smc_detector import (
    Candle,
    SwingKind,
    SwingPoint,
    _alternating_swings,
    build_dealing_range,
    build_observation_from_candles,
    classify_structure,
    detect_liquidity_events,
    find_swings,
)

_START = datetime(2026, 8, 1, tzinfo=UTC)


def _leg(start: float, end: float, n: int) -> list[list[float]]:
    """n candles stepping linearly from `start` to `end`, body-only (no wicks)."""
    step = (end - start) / n
    out: list[list[float]] = []
    for i in range(n):
        o = start + step * i
        c = start + step * (i + 1)
        out.append([o, max(o, c), min(o, c), c])
    return out


def _candles(rows: Sequence[Sequence[float]]) -> list[Candle]:
    return [
        Candle(
            timestamp=_START + timedelta(hours=i),
            open=row[0],
            high=row[1],
            low=row[2],
            close=row[3],
        )
        for i, row in enumerate(rows)
    ]


def _bullish_structure_candles() -> list[Candle]:
    """Down to a swing low, up to a swing high, higher pullback low, then a
    confirmed higher swing high, with the final close breaking above it."""
    rows: list[list[float]] = []
    rows += _leg(100, 90, 6)  # -> swing low ~89 (idx 5)
    rows += _leg(90, 98, 6)  # -> swing high ~99 (idx 11)
    rows += _leg(98, 94, 6)  # -> swing low ~93 (idx 17), higher low than 89
    rows += _leg(94, 108, 6)  # -> rally to ~108
    rows += _leg(108, 103, 4)  # pullback confirms 108 as swing high (idx 23)
    rows += _leg(103, 113, 5)  # final rally, last close breaks above the swing high
    rows[5][2] -= 1.0  # exaggerate swing low uniqueness
    rows[17][2] -= 1.0
    rows[11][1] += 1.0  # exaggerate swing high uniqueness
    rows[23][1] += 1.0
    return _candles(rows)


class SwingDetectionTests(unittest.TestCase):
    def test_finds_alternating_highs_and_lows_at_true_extremes(self) -> None:
        candles = _bullish_structure_candles()
        swings = find_swings(candles, window=3)
        prices_by_index = {s.index: round(s.price, 1) for s in swings}
        self.assertEqual(prices_by_index[5], 89.0)
        self.assertEqual(prices_by_index[11], 99.0)
        self.assertEqual(prices_by_index[17], 93.0)
        self.assertEqual(prices_by_index[23], 109.0)


class AlternatingSwingsTests(unittest.TestCase):
    def test_consecutive_same_kind_swings_keep_the_more_extreme_one(self) -> None:
        raw = [
            SwingPoint(index=0, timestamp=_START, price=95.0, kind=SwingKind.LOW),
            SwingPoint(index=1, timestamp=_START, price=90.0, kind=SwingKind.LOW),
            SwingPoint(index=2, timestamp=_START, price=100.0, kind=SwingKind.HIGH),
            SwingPoint(index=3, timestamp=_START, price=98.0, kind=SwingKind.HIGH),
        ]
        cleaned = _alternating_swings(raw)
        self.assertEqual([(s.index, s.price) for s in cleaned], [(1, 90.0), (2, 100.0)])


class StructureClassificationTests(unittest.TestCase):
    def test_higher_high_and_higher_low_is_bullish_with_break_of_structure(self) -> None:
        candles = _bullish_structure_candles()
        swings = find_swings(candles, window=3)
        structure = classify_structure(swings, candles[-1].close)
        self.assertIsNotNone(structure)
        assert structure is not None
        self.assertEqual(structure.bias, StructureBias.BULLISH)
        self.assertTrue(structure.break_of_structure)
        self.assertFalse(structure.change_of_character)

    def test_insufficient_swing_history_returns_none(self) -> None:
        rows = _leg(100, 90, 6) + _leg(90, 95, 6)
        candles = _candles(rows)
        swings = find_swings(candles, window=3)
        self.assertIsNone(classify_structure(swings, candles[-1].close))

    def test_mixed_higher_high_and_lower_low_is_neutral(self) -> None:
        rows: list[list[float]] = []
        rows += _leg(100, 90, 6)  # swing low ~89
        rows += _leg(90, 98, 6)  # swing high ~99
        rows += _leg(98, 85, 6)  # swing low ~84, a *lower* low than 89
        rows += _leg(85, 105, 6)  # swing high ~106, a *higher* high than 99
        rows += _leg(105, 101, 4)  # pullback confirms 106 as swing high
        rows += _leg(101, 104, 5)
        rows[5][2] -= 1.0
        rows[17][2] -= 1.0
        rows[11][1] += 1.0
        rows[23][1] += 1.0
        candles = _candles(rows)
        structure = classify_structure(find_swings(candles, window=3), candles[-1].close)
        self.assertIsNotNone(structure)
        assert structure is not None
        self.assertEqual(structure.bias, StructureBias.NEUTRAL)
        self.assertFalse(structure.break_of_structure)

    def test_lower_high_and_lower_low_is_bearish(self) -> None:
        rows: list[list[float]] = []
        rows += _leg(100, 110, 6)  # swing high ~109
        rows += _leg(110, 102, 6)  # swing low ~103
        rows += _leg(102, 106, 6)  # swing high ~105, lower high than 109
        rows += _leg(106, 90, 6)  # rally down
        rows += _leg(90, 95, 4)  # pullback confirms swing low ~89, lower low than 103
        rows += _leg(95, 85, 5)  # final leg breaks below the swing low
        rows[5][1] += 1.0
        rows[17][1] += 1.0
        rows[11][2] -= 1.0
        rows[23][2] -= 1.0
        candles = _candles(rows)
        swings = find_swings(candles, window=3)
        structure = classify_structure(swings, candles[-1].close)
        self.assertIsNotNone(structure)
        assert structure is not None
        self.assertEqual(structure.bias, StructureBias.BEARISH)
        self.assertTrue(structure.break_of_structure)


class DealingRangeTests(unittest.TestCase):
    def test_range_bounded_by_last_two_alternating_swings(self) -> None:
        candles = _bullish_structure_candles()
        swings = find_swings(candles, window=3)
        dealing_range = build_dealing_range(swings, candles[-1].close)
        self.assertIsNotNone(dealing_range)
        assert dealing_range is not None
        self.assertAlmostEqual(dealing_range.low, 93.0, places=1)
        self.assertAlmostEqual(dealing_range.high, candles[-1].close, places=1)

    def test_none_with_fewer_than_two_alternating_swings(self) -> None:
        rows = _leg(100, 90, 6) + _leg(90, 95, 6)
        candles = _candles(rows)
        swings = find_swings(candles, window=3)
        self.assertIsNone(build_dealing_range(swings, candles[-1].close))

    def test_none_when_recent_low_swing_prices_above_recent_high_swing(self) -> None:
        t = _START
        swings = [
            SwingPoint(index=0, timestamp=t, price=100.0, kind=SwingKind.HIGH),
            SwingPoint(index=1, timestamp=t, price=105.0, kind=SwingKind.LOW),
        ]
        self.assertIsNone(build_dealing_range(swings, current_price=102.0))


def _sweep_setup_rows() -> list[list[float]]:
    rows: list[list[float]] = []
    rows += _leg(100, 90, 5)  # -> structural swing low ~89 (idx 4)
    rows += _leg(90, 96, 5)  # confirms idx 4 as the swing low
    rows += _leg(96, 94, 3)  # minor chop, stays above the swing low
    rows[4][2] -= 1.0
    return rows


class LiquiditySweepTests(unittest.TestCase):
    def test_sweep_with_strong_follow_through_confirms_displacement(self) -> None:
        rows = _sweep_setup_rows()
        rows.append([94.0, 94.5, 88.0, 94.3])  # wicks below 89, closes back above
        rows.append([94.3, 98.0, 94.0, 97.8])  # strong bullish follow-through
        candles = _candles(rows)
        events = detect_liquidity_events(candles, find_swings(candles, window=3))
        sell_side = next(e for e in events if e.side == LiquiditySide.SELL_SIDE)
        self.assertTrue(sell_side.swept)
        self.assertTrue(sell_side.displacement_confirmed)

    def test_sweep_without_follow_through_has_no_displacement(self) -> None:
        rows = _sweep_setup_rows()
        rows.append([94.0, 94.5, 88.0, 94.3])  # wicks below 89, closes back above
        rows.append([94.3, 94.6, 94.1, 94.4])  # weak, indecisive next candle
        candles = _candles(rows)
        events = detect_liquidity_events(candles, find_swings(candles, window=3))
        sell_side = next(e for e in events if e.side == LiquiditySide.SELL_SIDE)
        self.assertTrue(sell_side.swept)
        self.assertFalse(sell_side.displacement_confirmed)

    def test_no_wick_beyond_swing_means_not_swept(self) -> None:
        rows = _sweep_setup_rows()
        rows.append([94.0, 94.5, 91.0, 94.3])  # stays above the swing low, no sweep
        candles = _candles(rows)
        events = detect_liquidity_events(candles, find_swings(candles, window=3))
        sell_side = next(e for e in events if e.side == LiquiditySide.SELL_SIDE)
        self.assertFalse(sell_side.swept)
        self.assertFalse(sell_side.displacement_confirmed)

    def test_sweep_candle_with_strong_body_confirms_displacement_alone(self) -> None:
        rows = _sweep_setup_rows()
        # the sweep candle itself has a strong bullish body, not just a wick
        rows.append([90.0, 96.0, 88.0, 95.8])
        candles = _candles(rows)
        events = detect_liquidity_events(candles, find_swings(candles, window=3))
        sell_side = next(e for e in events if e.side == LiquiditySide.SELL_SIDE)
        self.assertTrue(sell_side.swept)
        self.assertTrue(sell_side.displacement_confirmed)

    def test_only_swing_high_present_yields_only_buy_side_event(self) -> None:
        rows = _leg(90, 100, 6) + _leg(100, 95, 4)
        rows[5][1] += 1.0  # exaggerate the swing high, no swing low ever confirms
        candles = _candles(rows)
        events = detect_liquidity_events(candles, find_swings(candles, window=3))
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].side, LiquiditySide.BUY_SIDE)


class BuildObservationTests(unittest.TestCase):
    def test_builds_full_observation_from_sufficient_candles(self) -> None:
        candles = _bullish_structure_candles()
        observation = build_observation_from_candles(
            candles, symbol="XAUUSD", timeframe="H1", source="unit-test"
        )
        self.assertEqual(observation.symbol, "XAUUSD")
        self.assertIsNotNone(observation.structure)
        assert observation.structure is not None
        self.assertEqual(observation.structure.bias, StructureBias.BULLISH)
        self.assertIsNotNone(observation.dealing_range)
        self.assertEqual(observation.observed_at, candles[-1].timestamp)

    def test_raises_on_too_few_candles(self) -> None:
        candles = _candles(_leg(100, 95, 5))
        with self.assertRaises(ValueError):
            build_observation_from_candles(
                candles, symbol="XAUUSD", timeframe="H1", source="unit-test"
            )


if __name__ == "__main__":
    unittest.main()
