"""Tests for MacroCollector's real DXY/yield fetching and real PDH/PDL/PWH/PWL/PMH/PML
liquidity reference computation from daily candle history (network mocked)."""

from __future__ import annotations

import json
import unittest
from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock, patch

from packages.domain import (
    DollarStrength,
    LiquidityReferenceEvidence,
    LiquidityReferenceLevel,
    MacroContext,
    NewsEnvironment,
    NewsImpact,
    NewsWindow,
    YieldEnvironment,
    YieldRegime,
)
from packages.infrastructure.macro_collectors import MacroCollector, _previous_complete_period
from packages.infrastructure.smc_detector import Candle

NOW = datetime(2026, 8, 6, 12, tzinfo=UTC)


def _macro_context(
    *,
    dollar_strength: DollarStrength = DollarStrength.NEUTRAL,
    yield_direction: str = "NEUTRAL",
    liquidity_references: tuple[LiquidityReferenceEvidence, ...] = (),
) -> MacroContext:
    return MacroContext(
        context_id="MACRO-TEST",
        dollar_strength=dollar_strength,
        yield_environment=YieldEnvironment(
            us10y=4.25,
            us02y=4.50,
            yield_direction=yield_direction,
            yield_momentum="MODERATE",
            regime=YieldRegime.NEUTRAL,
        ),
        news_environment=NewsEnvironment(
            impact=NewsImpact.IGNORE,
            window=NewsWindow.CLEAR,
            unresolved_high_impact=False,
            event_name="none",
        ),
        liquidity_references=liquidity_references,
        observed_at=NOW,
    )


def _mock_response(payload: object, status: int = 200) -> MagicMock:
    response = MagicMock()
    response.status = status
    response.read.return_value = json.dumps(payload).encode("utf-8")
    response.__enter__.return_value = response
    response.__exit__.return_value = False
    return response


def _chart_payload(timestamps: list[int], closes: list[float]) -> dict[str, object]:
    highs = [c + 0.5 for c in closes]
    lows = [c - 0.5 for c in closes]
    opens = closes
    return {
        "chart": {
            "result": [
                {
                    "timestamp": timestamps,
                    "indicators": {
                        "quote": [{"open": opens, "high": highs, "low": lows, "close": closes}]
                    },
                }
            ]
        }
    }


class PreviousCompletePeriodTests(unittest.TestCase):
    def _candles(self, n: int) -> list[Candle]:
        start = datetime(2026, 8, 1, tzinfo=UTC)
        return [
            Candle(
                timestamp=start + timedelta(days=i),
                open=95 + i,
                high=100 + i,
                low=90 + i,
                close=97 + i,
            )
            for i in range(n)
        ]

    def test_returns_the_second_to_last_bucket_not_the_still_forming_one(self) -> None:
        candles = self._candles(10)
        result = _previous_complete_period(candles, lambda ts: (ts.year, ts.month, ts.day))
        self.assertEqual(result, (108, 98, 8))

    def test_none_with_fewer_than_two_distinct_buckets(self) -> None:
        candles = self._candles(1)
        result = _previous_complete_period(candles, lambda ts: (ts.year, ts.month, ts.day))
        self.assertIsNone(result)

    def test_week_bucketing_spans_multiple_days(self) -> None:
        candles = self._candles(21)  # 3 weeks of daily candles
        result = _previous_complete_period(candles, lambda ts: ts.isocalendar()[:2])
        self.assertIsNotNone(result)
        high, low, _idx = result  # type: ignore[misc]
        self.assertGreater(high, 100)


class FetchDxyStrengthTests(unittest.TestCase):
    def test_bearish_dxy_move(self) -> None:
        start = int(datetime(2026, 8, 1, tzinfo=UTC).timestamp())
        payload = _chart_payload([start, start + 86400], [100.0, 99.7])
        with patch("urllib.request.urlopen", return_value=_mock_response(payload)):
            strength = MacroCollector()._fetch_dxy_strength()
        self.assertEqual(strength, DollarStrength.BEARISH)

    def test_strong_bearish_dxy_move(self) -> None:
        start = int(datetime(2026, 8, 1, tzinfo=UTC).timestamp())
        payload = _chart_payload([start, start + 86400], [100.0, 99.0])
        with patch("urllib.request.urlopen", return_value=_mock_response(payload)):
            strength = MacroCollector()._fetch_dxy_strength()
        self.assertEqual(strength, DollarStrength.STRONG_BEARISH)

    def test_bullish_dxy_move(self) -> None:
        start = int(datetime(2026, 8, 1, tzinfo=UTC).timestamp())
        payload = _chart_payload([start, start + 86400], [100.0, 100.3])
        with patch("urllib.request.urlopen", return_value=_mock_response(payload)):
            strength = MacroCollector()._fetch_dxy_strength()
        self.assertEqual(strength, DollarStrength.BULLISH)

    def test_strong_bullish_dxy_move(self) -> None:
        start = int(datetime(2026, 8, 1, tzinfo=UTC).timestamp())
        payload = _chart_payload([start, start + 86400], [100.0, 101.0])
        with patch("urllib.request.urlopen", return_value=_mock_response(payload)):
            strength = MacroCollector()._fetch_dxy_strength()
        self.assertEqual(strength, DollarStrength.STRONG_BULLISH)

    def test_flat_dxy_move_is_neutral(self) -> None:
        start = int(datetime(2026, 8, 1, tzinfo=UTC).timestamp())
        payload = _chart_payload([start, start + 86400], [100.0, 100.0])
        with patch("urllib.request.urlopen", return_value=_mock_response(payload)):
            strength = MacroCollector()._fetch_dxy_strength()
        self.assertEqual(strength, DollarStrength.NEUTRAL)

    def test_single_candle_is_insufficient_and_returns_neutral(self) -> None:
        start = int(datetime(2026, 8, 1, tzinfo=UTC).timestamp())
        payload = _chart_payload([start], [100.0])
        with patch("urllib.request.urlopen", return_value=_mock_response(payload)):
            strength = MacroCollector()._fetch_dxy_strength()
        self.assertEqual(strength, DollarStrength.NEUTRAL)

    def test_network_failure_returns_neutral(self) -> None:
        with patch("urllib.request.urlopen", side_effect=TimeoutError("no network")):
            strength = MacroCollector()._fetch_dxy_strength()
        self.assertEqual(strength, DollarStrength.NEUTRAL)


class FetchYieldEnvironmentTests(unittest.TestCase):
    def test_real_us10y_and_direction_from_candles(self) -> None:
        start = int(datetime(2026, 8, 1, tzinfo=UTC).timestamp())
        payload = _chart_payload([start, start + 86400], [4.30, 4.10])
        with patch("urllib.request.urlopen", return_value=_mock_response(payload)):
            env = MacroCollector()._fetch_yield_environment()
        self.assertEqual(env.us10y, 4.1)
        self.assertEqual(env.yield_direction, "DOWN")
        self.assertEqual(env.us02y, 4.50)  # documented static placeholder

    def test_yield_up_direction(self) -> None:
        start = int(datetime(2026, 8, 1, tzinfo=UTC).timestamp())
        payload = _chart_payload([start, start + 86400], [4.10, 4.30])
        with patch("urllib.request.urlopen", return_value=_mock_response(payload)):
            env = MacroCollector()._fetch_yield_environment()
        self.assertEqual(env.yield_direction, "UP")

    def test_empty_candle_list_falls_back_to_static_defaults(self) -> None:
        with patch(
            "urllib.request.urlopen", return_value=_mock_response({"chart": {"result": []}})
        ):
            env = MacroCollector()._fetch_yield_environment()
        self.assertEqual(env.us10y, 4.25)
        self.assertEqual(env.yield_direction, "NEUTRAL")

    def test_single_candle_sets_price_but_not_direction(self) -> None:
        start = int(datetime(2026, 8, 1, tzinfo=UTC).timestamp())
        payload = _chart_payload([start], [4.42])
        with patch("urllib.request.urlopen", return_value=_mock_response(payload)):
            env = MacroCollector()._fetch_yield_environment()
        self.assertEqual(env.us10y, 4.42)
        self.assertEqual(env.yield_direction, "NEUTRAL")

    def test_network_failure_falls_back_to_static_defaults(self) -> None:
        with patch("urllib.request.urlopen", side_effect=TimeoutError("no network")):
            env = MacroCollector()._fetch_yield_environment()
        self.assertEqual(env.us10y, 4.25)
        self.assertEqual(env.yield_direction, "NEUTRAL")


class FetchNewsEnvironmentTests(unittest.TestCase):
    def test_is_an_explicitly_labeled_placeholder_not_a_verified_clear_window(self) -> None:
        env = MacroCollector()._fetch_news_environment()
        self.assertFalse(env.unresolved_high_impact)
        self.assertIn("not a verified", env.event_name.lower())


class FetchLiquidityReferencesTests(unittest.TestCase):
    def _daily_payload(self) -> dict[str, object]:
        start = int(datetime(2026, 6, 1, tzinfo=UTC).timestamp())
        n = 40
        timestamps = [start + i * 86400 for i in range(n)]
        opens: list[float] = []
        highs: list[float] = []
        lows: list[float] = []
        closes: list[float] = []
        price = 3300.0
        for _ in range(n):
            o, c = price, price + 2
            highs.append(max(o, c) + 1)
            lows.append(min(o, c) - 1)
            opens.append(o)
            closes.append(c)
            price = c

        # Previous complete day gets a distinct, testable high/low.
        highs[-2] = 3450.0
        lows[-2] = 3200.0
        # Today's still-forming candle sweeps below that low and reclaims.
        opens[-1], highs[-1], lows[-1], closes[-1] = 3210.0, 3215.0, 3190.0, 3212.0

        return {
            "chart": {
                "result": [
                    {
                        "timestamp": timestamps,
                        "indicators": {
                            "quote": [{"open": opens, "high": highs, "low": lows, "close": closes}]
                        },
                    }
                ]
            }
        }

    def test_computes_real_pdh_pdl_from_daily_candles_with_sweep_detected(self) -> None:
        with patch("urllib.request.urlopen", return_value=_mock_response(self._daily_payload())):
            refs = MacroCollector()._fetch_liquidity_references()

        by_level = {r.level: r for r in refs}
        self.assertEqual(len(refs), 6)
        self.assertEqual(by_level[LiquidityReferenceLevel.PDH].price, 3450.0)
        self.assertFalse(by_level[LiquidityReferenceLevel.PDH].swept)
        self.assertEqual(by_level[LiquidityReferenceLevel.PDL].price, 3200.0)
        self.assertTrue(by_level[LiquidityReferenceLevel.PDL].swept)

    def test_network_failure_returns_empty_tuple_not_fake_levels(self) -> None:
        with patch("urllib.request.urlopen", side_effect=TimeoutError("no network")):
            refs = MacroCollector()._fetch_liquidity_references()
        self.assertEqual(refs, ())

    def test_insufficient_history_returns_empty_tuple(self) -> None:
        start = int(datetime(2026, 8, 1, tzinfo=UTC).timestamp())
        payload = _chart_payload([start, start + 86400], [3300.0, 3302.0])
        with patch("urllib.request.urlopen", return_value=_mock_response(payload)):
            refs = MacroCollector()._fetch_liquidity_references()
        self.assertEqual(refs, ())

    def test_week_and_month_levels_skipped_when_span_too_short_to_bucket(self) -> None:
        # 2026-08-03 is a Monday; 5 consecutive days all land in the same ISO
        # week and the same month, so only day-level buckets have >=2 entries.
        start = int(datetime(2026, 8, 3, tzinfo=UTC).timestamp())
        timestamps = [start + i * 86400 for i in range(5)]
        closes = [3300.0, 3302.0, 3304.0, 3306.0, 3308.0]
        payload = _chart_payload(timestamps, closes)
        with patch("urllib.request.urlopen", return_value=_mock_response(payload)):
            refs = MacroCollector()._fetch_liquidity_references()
        levels = {r.level for r in refs}
        self.assertEqual(levels, {LiquidityReferenceLevel.PDH, LiquidityReferenceLevel.PDL})


class EvaluateMacroAssessmentTests(unittest.TestCase):
    def test_bearish_dollar_strength_boosts_gold_score(self) -> None:
        ctx = _macro_context(dollar_strength=DollarStrength.BEARISH)
        assessment = MacroCollector().evaluate_macro_assessment(ctx, NOW)
        self.assertIn("Bullish for Gold", " ".join(assessment.evidence))
        self.assertGreater(assessment.macro_score, 0.50)

    def test_bullish_dollar_strength_reduces_gold_score(self) -> None:
        ctx = _macro_context(dollar_strength=DollarStrength.BULLISH)
        assessment = MacroCollector().evaluate_macro_assessment(ctx, NOW)
        self.assertIn("Bearish for Gold", " ".join(assessment.evidence))
        self.assertLess(assessment.macro_score, 0.50)

    def test_yield_up_reduces_gold_score(self) -> None:
        ctx = _macro_context(yield_direction="UP")
        assessment = MacroCollector().evaluate_macro_assessment(ctx, NOW)
        self.assertIn("US10Y Yield direction is UP", " ".join(assessment.evidence))
        self.assertLess(assessment.macro_score, 0.50)

    def test_swept_liquidity_levels_are_listed_in_evidence(self) -> None:
        swept = LiquidityReferenceEvidence(
            level=LiquidityReferenceLevel.PDL, price=3300.0, swept=True, displacement_confirmed=True
        )
        ctx = _macro_context(liquidity_references=(swept,))
        assessment = MacroCollector().evaluate_macro_assessment(ctx, NOW)
        self.assertTrue(any("Swept Liquidity Reference Levels" in e for e in assessment.evidence))
        self.assertIn("PDL", " ".join(assessment.evidence))


if __name__ == "__main__":
    unittest.main()
