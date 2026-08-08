"""Tests for the walk-forward replay loop: windowing and edge-triggered
signal emission, using the same proven real-candle fixture as
test_real_candle_decision_reachability.py (extended so the verdict
persists across several consecutive candles, to prove edge-triggering
actually collapses that into one signal)."""

from __future__ import annotations

import unittest
from datetime import UTC, datetime, timedelta

from test_real_candle_decision_reachability import (
    _bullish_break_then_discount_retracement_rows,
    _candles,
)

from backtest.walk_forward import walk_forward
from packages.domain import DecisionPolicy, DecisionVerdict
from packages.infrastructure.smc_detector import Candle

_START = datetime(2026, 1, 1, tzinfo=UTC)


def _flat_continuation(after: Candle, count: int, level: float) -> list[Candle]:
    return [
        Candle(
            timestamp=after.timestamp + timedelta(hours=i + 1),
            open=level,
            high=level + 1.0,
            low=level - 1.0,
            close=level,
        )
        for i in range(count)
    ]


class WalkForwardTests(unittest.TestCase):
    def test_a_persistent_buy_setup_is_recorded_as_one_signal_not_one_per_candle(self) -> None:
        """The real fixture's verdict is BUY at candle indices 42, 43, and
        44 in a row (verified independently before writing this test) --
        edge-triggering must collapse that run into exactly one signal, at
        the first index the transition happens."""
        candles = _candles(_bullish_break_then_discount_retracement_rows())
        candles += _flat_continuation(candles[-1], count=15, level=98.0)

        signals = walk_forward(candles, DecisionPolicy())

        self.assertEqual(len(signals), 1)
        self.assertEqual(signals[0].decision.verdict, DecisionVerdict.BUY)
        self.assertEqual(signals[0].index, 42)

    def test_a_pure_wait_series_produces_no_signals(self) -> None:
        flat = [
            Candle(
                timestamp=_START + timedelta(hours=i),
                open=100.0,
                high=100.5,
                low=99.5,
                close=100.0,
            )
            for i in range(30)
        ]
        signals = walk_forward(flat, DecisionPolicy())
        self.assertEqual(signals, [])

    def test_window_is_bounded_and_matches_the_candles_available_at_that_index(self) -> None:
        """Before the window fills up, the observation sees only the
        candles available so far (index+1 candles); once past the window
        size it must never grow beyond it."""
        candles = _candles(_bullish_break_then_discount_retracement_rows())
        candles += _flat_continuation(candles[-1], count=15, level=98.0)

        signals = walk_forward(candles, DecisionPolicy(), window=720)
        self.assertEqual(len(signals), 1)
        # Fewer than 720 candles exist by index 42 -- window shouldn't pad or truncate that.
        self.assertEqual(len(signals[0].window_candles), signals[0].index + 1)

        small_window_signals = walk_forward(candles, DecisionPolicy(), window=30)
        for signal in small_window_signals:
            self.assertLessEqual(len(signal.window_candles), 30)


if __name__ == "__main__":
    unittest.main()
