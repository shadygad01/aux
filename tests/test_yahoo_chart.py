"""Tests for the shared Yahoo Finance chart-endpoint fetching and parsing."""

from __future__ import annotations

import json
import unittest
from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

from packages.infrastructure.yahoo_chart import fetch_yahoo_candles, parse_yahoo_chart_candles


def _mock_response(payload: object, status: int = 200) -> MagicMock:
    response = MagicMock()
    response.status = status
    response.read.return_value = json.dumps(payload).encode("utf-8")
    response.__enter__.return_value = response
    response.__exit__.return_value = False
    return response


def _yahoo_chart_payload(rows: list[list[float]]) -> dict[str, object]:
    """Build a Yahoo-chart-shaped payload from a bullish HH/HL price path
    (same construction as test_smc_detector's fixture) with real timestamps."""
    start = int(datetime(2026, 8, 1, tzinfo=UTC).timestamp())
    timestamps = [start + i * 3600 for i in range(len(rows))]
    return {
        "chart": {
            "result": [
                {
                    "timestamp": timestamps,
                    "indicators": {
                        "quote": [
                            {
                                "open": [r[0] for r in rows],
                                "high": [r[1] for r in rows],
                                "low": [r[2] for r in rows],
                                "close": [r[3] for r in rows],
                            }
                        ]
                    },
                }
            ]
        }
    }


def _leg(start: float, end: float, n: int) -> list[list[float]]:
    step = (end - start) / n
    out: list[list[float]] = []
    for i in range(n):
        o = start + step * i
        c = start + step * (i + 1)
        out.append([o, max(o, c), min(o, c), c])
    return out


def _bullish_rows() -> list[list[float]]:
    rows: list[list[float]] = []
    rows += _leg(100, 90, 6)
    rows += _leg(90, 98, 6)
    rows += _leg(98, 94, 6)
    rows += _leg(94, 108, 6)
    rows += _leg(108, 103, 4)
    rows += _leg(103, 113, 5)
    rows[5][2] -= 1.0
    rows[17][2] -= 1.0
    rows[11][1] += 1.0
    rows[23][1] += 1.0
    return rows


class ParseChartCandlesTests(unittest.TestCase):
    def test_parses_valid_payload_into_candles(self) -> None:
        rows = _bullish_rows()
        payload = _yahoo_chart_payload(rows)
        candles = parse_yahoo_chart_candles(payload)
        self.assertEqual(len(candles), len(rows))
        self.assertAlmostEqual(candles[0].open, rows[0][0])
        self.assertAlmostEqual(candles[-1].close, rows[-1][3])

    def test_skips_rows_with_non_numeric_values(self) -> None:
        payload = _yahoo_chart_payload(_bullish_rows())
        quote = payload["chart"]["result"][0]["indicators"]["quote"][0]  # type: ignore[index]
        quote["close"][3] = None
        candles = parse_yahoo_chart_candles(payload)
        self.assertEqual(len(candles), len(_bullish_rows()) - 1)

    def test_missing_chart_key_returns_empty(self) -> None:
        self.assertEqual(parse_yahoo_chart_candles({}), [])

    def test_non_dict_chart_returns_empty(self) -> None:
        self.assertEqual(parse_yahoo_chart_candles({"chart": "not-a-dict"}), [])

    def test_empty_result_list_returns_empty(self) -> None:
        self.assertEqual(parse_yahoo_chart_candles({"chart": {"result": []}}), [])

    def test_missing_quote_list_returns_empty(self) -> None:
        payload: dict[str, object] = {
            "chart": {"result": [{"timestamp": [1, 2, 3], "indicators": {"quote": []}}]}
        }
        self.assertEqual(parse_yahoo_chart_candles(payload), [])

    def test_non_list_ohlc_field_returns_empty(self) -> None:
        payload: dict[str, object] = {
            "chart": {
                "result": [
                    {
                        "timestamp": [1, 2, 3],
                        "indicators": {
                            "quote": [{"open": "bad", "high": [], "low": [], "close": []}]
                        },
                    }
                ]
            }
        }
        self.assertEqual(parse_yahoo_chart_candles(payload), [])

    def test_non_dict_result_entry_returns_empty(self) -> None:
        payload: dict[str, object] = {"chart": {"result": ["not-a-dict"]}}
        self.assertEqual(parse_yahoo_chart_candles(payload), [])

    def test_non_list_timestamp_returns_empty(self) -> None:
        payload: dict[str, object] = {
            "chart": {"result": [{"timestamp": "bad", "indicators": {"quote": [{}]}}]}
        }
        self.assertEqual(parse_yahoo_chart_candles(payload), [])

    def test_non_dict_quote_entry_returns_empty(self) -> None:
        payload: dict[str, object] = {
            "chart": {"result": [{"timestamp": [1], "indicators": {"quote": ["not-a-dict"]}}]}
        }
        self.assertEqual(parse_yahoo_chart_candles(payload), [])


class FetchYahooCandlesTests(unittest.TestCase):
    def test_builds_url_from_ticker_interval_and_range(self) -> None:
        payload = _yahoo_chart_payload(_bullish_rows())
        captured_urls: list[str] = []

        def _capturing_urlopen(req: object, timeout: float) -> MagicMock:
            captured_urls.append(req.full_url)  # type: ignore[attr-defined]
            return _mock_response(payload)

        with patch("urllib.request.urlopen", side_effect=_capturing_urlopen):
            candles = fetch_yahoo_candles("DX-Y.NYB", "1d", "5d", timeout_seconds=5)
        self.assertEqual(len(candles), len(_bullish_rows()))
        self.assertIn("DX-Y.NYB", captured_urls[0])
        self.assertIn("interval=1d", captured_urls[0])
        self.assertIn("range=5d", captured_urls[0])

    def test_non_200_response_returns_empty(self) -> None:
        with patch("urllib.request.urlopen", return_value=_mock_response({}, status=500)):
            candles = fetch_yahoo_candles("GC=F", "1h", "1mo", timeout_seconds=5)
        self.assertEqual(candles, [])

    def test_non_dict_response_body_returns_empty(self) -> None:
        with patch("urllib.request.urlopen", return_value=_mock_response(["not", "a", "dict"])):
            candles = fetch_yahoo_candles("GC=F", "1h", "1mo", timeout_seconds=5)
        self.assertEqual(candles, [])


if __name__ == "__main__":
    unittest.main()
