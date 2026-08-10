from __future__ import annotations

import unittest
from datetime import UTC, datetime, timedelta

from backtest.mtf_data import (
    H1_SECONDS,
    M15_SECONDS,
    aggregate_bars,
    ticks_to_bars,
    validate_bar_lineage,
)
from backtest.mtf_models import Tick


def tick(minute: int, bid: float, ask: float) -> Tick:
    return Tick(datetime(2026, 1, 5, 10, minute, tzinfo=UTC), bid, ask, 1.0, 2.0)


class TickAggregationTests(unittest.TestCase):
    def test_ticks_build_bid_ask_m5_and_exclude_open_candle(self) -> None:
        ticks = [tick(0, 100.0, 100.2), tick(2, 101.0, 101.3), tick(5, 102.0, 102.2)]
        bars = ticks_to_bars(ticks, closed_before=datetime(2026, 1, 5, 10, 7, tzinfo=UTC))
        self.assertEqual(len(bars), 1)
        self.assertEqual(bars[0].bid_open, 100.0)
        self.assertEqual(bars[0].bid_high, 101.0)
        self.assertEqual(bars[0].ask_close, 101.3)
        self.assertAlmostEqual(bars[0].mean_spread, 0.25)

    def test_duplicate_tick_timestamp_is_rejected(self) -> None:
        duplicate = tick(0, 100.0, 100.2)
        with self.assertRaisesRegex(ValueError, "duplicate"):
            ticks_to_bars([duplicate, duplicate])

    def test_m5_is_the_only_lineage_source_for_m15_and_h1(self) -> None:
        ticks = [
            Tick(
                datetime(2026, 1, 5, 10, 0, tzinfo=UTC) + timedelta(minutes=minute),
                100 + minute / 100,
                100.2 + minute / 100,
                1.0,
                1.0,
            )
            for minute in range(60)
        ]
        m5 = ticks_to_bars(ticks)
        m15 = aggregate_bars(m5, M15_SECONDS)
        h1 = aggregate_bars(m5, H1_SECONDS)
        validate_bar_lineage(m5, m15, h1)
        self.assertEqual((len(m5), len(m15), len(h1)), (12, 4, 1))

    def test_incomplete_parent_bar_is_not_fabricated(self) -> None:
        ticks = [tick(minute, 100.0, 100.2) for minute in (0, 5, 20)]
        m5 = ticks_to_bars(ticks)
        self.assertEqual(aggregate_bars(m5, M15_SECONDS), [])


if __name__ == "__main__":
    unittest.main()
