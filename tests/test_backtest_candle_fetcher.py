"""Tests for the chunked historical H1 candle fetch (no real network)."""

from __future__ import annotations

import json
import unittest
from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

from backtest.candle_fetcher import fetch_h1_history


def _mock_response(payload: object, status: int = 200) -> MagicMock:
    response = MagicMock()
    response.status = status
    response.read.return_value = json.dumps(payload).encode("utf-8")
    response.__enter__.return_value = response
    response.__exit__.return_value = False
    return response


def _chart_payload(start_ts: int, closes: list[float]) -> dict[str, object]:
    timestamps = [start_ts + i * 3600 for i in range(len(closes))]
    return {
        "chart": {
            "result": [
                {
                    "timestamp": timestamps,
                    "indicators": {
                        "quote": [
                            {
                                "open": closes,
                                "high": closes,
                                "low": closes,
                                "close": closes,
                            }
                        ]
                    },
                }
            ]
        }
    }


class FetchH1HistoryTests(unittest.TestCase):
    def test_rejects_non_positive_total_days(self) -> None:
        with self.assertRaises(ValueError):
            fetch_h1_history("GC=F", 0)

    def test_rejects_naive_now(self) -> None:
        with self.assertRaises(ValueError):
            fetch_h1_history("GC=F", 30, now=datetime(2026, 1, 1))

    def test_single_chunk_returns_sorted_candles(self) -> None:
        now = datetime(2026, 1, 10, tzinfo=UTC)
        start_ts = int(datetime(2026, 1, 9, tzinfo=UTC).timestamp())
        payload = _chart_payload(start_ts, [100.0, 101.0, 102.0])

        with patch("urllib.request.urlopen", return_value=_mock_response(payload)):
            candles = fetch_h1_history("GC=F", total_days=1, chunk_days=60, now=now)

        self.assertEqual(len(candles), 3)
        self.assertEqual([c.close for c in candles], [100.0, 101.0, 102.0])
        self.assertEqual(candles, sorted(candles, key=lambda c: c.timestamp))

    def test_multiple_chunks_are_merged_and_deduplicated(self) -> None:
        now = datetime(2026, 3, 1, tzinfo=UTC)
        older_ts = int(datetime(2026, 1, 1, tzinfo=UTC).timestamp())
        newer_ts = int(datetime(2026, 2, 1, tzinfo=UTC).timestamp())

        responses = [
            _mock_response(_chart_payload(newer_ts, [200.0, 201.0])),
            _mock_response(_chart_payload(older_ts, [100.0, 101.0])),
        ]

        with patch("urllib.request.urlopen", side_effect=responses):
            candles = fetch_h1_history("GC=F", total_days=60, chunk_days=30, now=now)

        self.assertEqual(len(candles), 4)
        closes = [c.close for c in candles]
        self.assertEqual(closes, sorted(closes))  # ascending by timestamp too

    def test_stops_early_when_a_chunk_returns_nothing(self) -> None:
        now = datetime(2026, 3, 1, tzinfo=UTC)
        newer_ts = int(datetime(2026, 2, 1, tzinfo=UTC).timestamp())

        responses = [
            _mock_response(_chart_payload(newer_ts, [200.0, 201.0])),
            _mock_response({"chart": {"result": []}}),
        ]

        with patch("urllib.request.urlopen", side_effect=responses) as mock_urlopen:
            candles = fetch_h1_history("GC=F", total_days=200, chunk_days=30, now=now)

        self.assertEqual(len(candles), 2)
        # Stopped after the empty chunk instead of continuing to fetch further back.
        self.assertEqual(mock_urlopen.call_count, 2)

    def test_no_candles_reachable_returns_empty_list(self) -> None:
        now = datetime(2026, 1, 10, tzinfo=UTC)
        empty_response = _mock_response({"chart": {"result": []}})
        with patch("urllib.request.urlopen", return_value=empty_response):
            candles = fetch_h1_history("GC=F", total_days=5, chunk_days=60, now=now)
        self.assertEqual(candles, [])


if __name__ == "__main__":
    unittest.main()
