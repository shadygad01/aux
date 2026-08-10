from __future__ import annotations

import tempfile
import unittest
from datetime import UTC, datetime, timedelta
from pathlib import Path

from backtest.ingest_supplied_mtf import ingest
from backtest.midpoint_bar_research import simulate
from backtest.mtf_feature_engine import FeatureSnapshot
from backtest.mtf_models import BidAskBar, Direction, ExitMode, ExitPlan
from backtest.mtf_storage import read_bars


def _bar(timestamp: datetime, *, high: float, low: float) -> BidAskBar:
    return BidAskBar(timestamp, 300, 100, high, low, 100, 100, high, low, 100, 1, 1, 1, 0)


class SuppliedMtfResearchTests(unittest.TestCase):
    def test_ingestion_censors_zero_volume_and_rebuilds_higher_timeframes(self) -> None:
        start = datetime(2025, 1, 6, tzinfo=UTC)
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "m5.csv"
            rows = ["timestamp_utc,open,high,low,close,volume_bid,volume_ask,source"]
            for index in range(24):
                volume = 0 if index == 0 else 1
                price = 200_000_000 + index * 100_000
                rows.append(
                    f"{(start + timedelta(minutes=5 * index)).isoformat()},"
                    f"{price},{price},{price},{price},{volume},{volume},test"
                )
            source.write_text("\n".join(rows), encoding="utf-8")
            manifest = ingest(source, root / "derived")
            h1 = read_bars(root / "derived" / "XAUUSD_H1.jsonl")
        self.assertEqual(manifest["zero_volume_m5_censored"], 1)
        self.assertEqual(len(h1), 1)
        self.assertEqual(h1[0].timestamp, start + timedelta(hours=1))

    def test_same_bar_stop_and_target_is_resolved_pessimistically(self) -> None:
        start = datetime(2025, 1, 6, tzinfo=UTC)
        bars = [_bar(start, high=103, low=97)]
        snapshot = FeatureSnapshot(start, Direction.BUY, {}, 1, 1)
        trade = simulate(
            snapshot,
            bars,
            [start],
            ExitPlan(ExitMode.FIXED_R, target_r=2),
            per_side_cost=0,
            delay_bars=0,
        )
        assert trade is not None
        self.assertEqual(trade.outcome, "STOP")
        self.assertEqual(trade.net_r, -1)


if __name__ == "__main__":
    unittest.main()
