"""Tests for the live collector's network fallback tiers.

Network calls are mocked — the existing `test_live_collector_fallback`
integration test in test_production_completion.py already covers real
reachability; these tests exercise the branch logic deterministically
instead. Chart-parsing itself is tested in test_yahoo_chart.py.
"""

from __future__ import annotations

import json
import unittest
from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock, patch

from packages.infrastructure.live_collector import LiveMarketCollector


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


class FetchLiveObservationTests(unittest.TestCase):
    def test_returns_live_smc_observation_when_candles_available(self) -> None:
        payload = _yahoo_chart_payload(_bullish_rows())
        with patch("urllib.request.urlopen", return_value=_mock_response(payload)):
            obs, source = LiveMarketCollector().fetch_live_observation()
        self.assertEqual(source, "LIVE:yahoo-finance-gold-futures-smc-1h")
        self.assertEqual(obs.timeframe, "H1")
        self.assertIsNotNone(obs.structure)

    def test_custom_interval_and_timeframe_are_used_for_the_request_and_observation(self) -> None:
        payload = _yahoo_chart_payload(_bullish_rows())
        captured_urls: list[str] = []

        def _capturing_urlopen(req: object, timeout: float) -> MagicMock:
            captured_urls.append(req.full_url)  # type: ignore[attr-defined]
            return _mock_response(payload)

        with patch("urllib.request.urlopen", side_effect=_capturing_urlopen):
            obs, source = LiveMarketCollector().fetch_live_observation(
                interval="5m", chart_range="5d", timeframe="M5"
            )
        self.assertEqual(source, "LIVE:yahoo-finance-gold-futures-smc-5m")
        self.assertEqual(obs.timeframe, "M5")
        self.assertIn("interval=5m", captured_urls[0])
        self.assertIn("range=5d", captured_urls[0])

    def test_falls_back_to_price_only_when_candles_unavailable(self) -> None:
        candle_failure = _mock_response({"chart": {"result": []}})
        price_success = _mock_response({"price": 3345.5})
        with patch("urllib.request.urlopen", side_effect=[candle_failure, price_success]):
            obs, source = LiveMarketCollector().fetch_live_observation()
        self.assertEqual(source, "LIVE:spot-gold-api-price-only")
        self.assertIsNone(obs.structure)
        self.assertIsNone(obs.dealing_range)

    def test_falls_back_to_honest_empty_observation_when_nothing_reachable(self) -> None:
        with patch("urllib.request.urlopen", side_effect=TimeoutError("no network")):
            obs, source = LiveMarketCollector().fetch_live_observation()
        self.assertEqual(source, "FALLBACK:no-data-source-reachable")
        self.assertIsNone(obs.structure)
        self.assertIsNone(obs.dealing_range)
        self.assertEqual(obs.liquidity, ())
        self.assertLess(datetime.now(UTC) - obs.observed_at, timedelta(seconds=5))

    def test_falls_back_to_price_only_when_candle_response_is_non_200(self) -> None:
        candle_failure = _mock_response({}, status=500)
        price_success = _mock_response({"price": 3345.5})
        with patch("urllib.request.urlopen", side_effect=[candle_failure, price_success]):
            obs, source = LiveMarketCollector().fetch_live_observation()
        self.assertEqual(source, "LIVE:spot-gold-api-price-only")

    def test_falls_back_when_spot_price_field_missing(self) -> None:
        candle_failure = _mock_response({"chart": {"result": []}})
        price_missing = _mock_response({"not_price": 1})
        with patch("urllib.request.urlopen", side_effect=[candle_failure, price_missing]):
            obs, source = LiveMarketCollector().fetch_live_observation()
        self.assertEqual(source, "FALLBACK:no-data-source-reachable")

    def test_falls_back_when_spot_price_response_is_non_200(self) -> None:
        candle_failure = _mock_response({"chart": {"result": []}})
        price_failure = _mock_response({"price": 3345.5}, status=503)
        with patch("urllib.request.urlopen", side_effect=[candle_failure, price_failure]):
            obs, source = LiveMarketCollector().fetch_live_observation()
        self.assertEqual(source, "FALLBACK:no-data-source-reachable")

    def test_falls_back_to_price_only_when_candle_response_body_is_not_a_dict(self) -> None:
        candle_failure = _mock_response(["not", "a", "dict"])
        price_success = _mock_response({"price": 3345.5})
        with patch("urllib.request.urlopen", side_effect=[candle_failure, price_success]):
            obs, source = LiveMarketCollector().fetch_live_observation()
        self.assertEqual(source, "LIVE:spot-gold-api-price-only")


if __name__ == "__main__":
    unittest.main()
