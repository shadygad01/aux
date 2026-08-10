from __future__ import annotations

import unittest
from datetime import UTC, datetime, timedelta

from backtest.bottom_up_reversal import _closed_window
from backtest.mtf_models import BidAskBar


def _bar(timestamp: datetime, seconds: int) -> BidAskBar:
    return BidAskBar(
        timestamp, seconds, 2000, 2001, 1999, 2000.5, 2000.2, 2001.2, 1999.2, 2000.7, 10, 5, 5, 0.2
    )


class BottomUpReversalTests(unittest.TestCase):
    def test_each_timeframe_window_excludes_open_bar(self) -> None:
        start = datetime(2025, 1, 1, tzinfo=UTC)
        bars = [_bar(start + timedelta(minutes=15 * i), 900) for i in range(8)]
        decision = start + timedelta(hours=1)
        selected = _closed_window(bars, decision, maximum=20)
        self.assertEqual(
            [bar.closed_at for bar in selected],
            [
                start + timedelta(minutes=15),
                start + timedelta(minutes=30),
                start + timedelta(minutes=45),
                start + timedelta(hours=1),
            ],
        )
        self.assertTrue(all(bar.closed_at <= decision for bar in selected))


if __name__ == "__main__":
    unittest.main()
