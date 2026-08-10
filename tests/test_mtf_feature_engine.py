from __future__ import annotations

import unittest
from datetime import UTC, datetime, timedelta

from backtest.mtf_feature_engine import _m15_window
from backtest.mtf_models import BidAskBar


def _bar(timestamp: datetime) -> BidAskBar:
    return BidAskBar(
        timestamp=timestamp,
        seconds=900,
        bid_open=2000.0,
        bid_high=2001.0,
        bid_low=1999.0,
        bid_close=2000.5,
        ask_open=2000.2,
        ask_high=2001.2,
        ask_low=1999.2,
        ask_close=2000.7,
        tick_count=10,
        bid_volume=5.0,
        ask_volume=5.0,
        mean_spread=0.2,
    )


class MtfFeatureLeakageTests(unittest.TestCase):
    def test_m15_window_uses_only_candles_closed_at_decision_time(self) -> None:
        start = datetime(2025, 1, 1, tzinfo=UTC)
        bars = [_bar(start + timedelta(minutes=15 * index)) for index in range(6)]
        decision_time = start + timedelta(hours=1)

        selected = _m15_window(bars, decision_time)

        self.assertEqual(len(selected), 4)
        self.assertTrue(all(bar.closed_at <= decision_time for bar in selected))
        self.assertNotIn(bars[4], selected)


if __name__ == "__main__":
    unittest.main()
