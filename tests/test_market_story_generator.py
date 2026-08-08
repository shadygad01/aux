"""Tests for market_story.py's per-stage narrative builders — pure functions
over real domain objects, no network needed."""

from __future__ import annotations

import unittest
from datetime import UTC, datetime, timedelta
from unittest.mock import patch

from packages.domain import (
    DealingRange,
    Decision,
    DecisionPolicy,
    DecisionVerdict,
    LiquidityEvent,
    LiquiditySide,
    MacroAssessment,
    MarketObservation,
    MarketStructure,
    StructureBias,
)
from packages.infrastructure.momentum import MacdResult, compute_macd
from packages.infrastructure.smc_detector import Candle
from publish.generators.market_story import (
    _bias_stage,
    _discount_stage,
    _evolution_summary,
    _fetch_observation_and_macd,
    _liquidity_stage,
    _macro_stage,
    _momentum_stage,
    _smc_stage,
    _thesis_stage,
)

NOW = datetime(2026, 8, 6, 12, tzinfo=UTC)
STAMP = "202608061200"


def _observation(
    *,
    structure: MarketStructure | None = None,
    dealing_range: DealingRange | None = None,
    liquidity: tuple[LiquidityEvent, ...] = (),
) -> MarketObservation:
    return MarketObservation(
        symbol="XAUUSD",
        timeframe="H1",
        observed_at=NOW,
        structure=structure,
        dealing_range=dealing_range,
        liquidity=liquidity,
        source="unit-test",
    )


class MacroStageTests(unittest.TestCase):
    def _assessment(self, score: float, evidence: tuple[str, ...] = ()) -> MacroAssessment:
        return MacroAssessment(
            assessment_id="A-1",
            macro_score=score,
            confidence_modifier=0.0,
            force_wait=False,
            wait_reason="",
            evidence=evidence,
            evaluated_at=NOW,
        )

    def test_bullish_for_gold_above_half(self) -> None:
        stage = _macro_stage(self._assessment(0.75, ("DXY BEARISH",)), STAMP)
        self.assertEqual(stage.status, "BULLISH_FOR_GOLD")
        self.assertIn("DXY BEARISH", stage.narrative)

    def test_bearish_for_gold_below_half(self) -> None:
        stage = _macro_stage(self._assessment(0.25), STAMP)
        self.assertEqual(stage.status, "BEARISH_FOR_GOLD")
        self.assertEqual(stage.narrative, "No macro evidence collected.")

    def test_neutral_at_half(self) -> None:
        stage = _macro_stage(self._assessment(0.50), STAMP)
        self.assertEqual(stage.status, "NEUTRAL")


class BiasStageTests(unittest.TestCase):
    def test_no_structure_is_unknown(self) -> None:
        stage = _bias_stage(_observation(), STAMP)
        self.assertEqual(stage.status, "UNKNOWN")

    def test_bullish_with_bos(self) -> None:
        obs = _observation(
            structure=MarketStructure(bias=StructureBias.BULLISH, break_of_structure=True)
        )
        stage = _bias_stage(obs, STAMP)
        self.assertEqual(stage.status, "BULLISH")
        self.assertIn("confirmed break of structure", stage.narrative)

    def test_bearish_without_bos(self) -> None:
        obs = _observation(
            structure=MarketStructure(bias=StructureBias.BEARISH, break_of_structure=False)
        )
        stage = _bias_stage(obs, STAMP)
        self.assertIn("without a confirmed break", stage.narrative)


class DiscountStageTests(unittest.TestCase):
    def test_no_dealing_range_is_unknown(self) -> None:
        stage = _discount_stage(_observation(), DecisionPolicy(), STAMP)
        self.assertEqual(stage.status, "UNKNOWN")

    def test_discount_location(self) -> None:
        obs = _observation(dealing_range=DealingRange(low=0, high=100, current_price=10))
        stage = _discount_stage(obs, DecisionPolicy(), STAMP)
        self.assertEqual(stage.status, "DISCOUNT")
        self.assertIn("10.00", stage.narrative)

    def test_premium_location(self) -> None:
        obs = _observation(dealing_range=DealingRange(low=0, high=100, current_price=90))
        stage = _discount_stage(obs, DecisionPolicy(), STAMP)
        self.assertEqual(stage.status, "PREMIUM")


class LiquidityStageTests(unittest.TestCase):
    def test_no_sweeps_not_swept(self) -> None:
        stage = _liquidity_stage(_observation(), STAMP)
        self.assertEqual(stage.status, "NOT_SWEPT")

    def test_swept_with_displacement(self) -> None:
        obs = _observation(
            liquidity=(
                LiquidityEvent(
                    side=LiquiditySide.SELL_SIDE, swept=True, displacement_confirmed=True
                ),
            )
        )
        stage = _liquidity_stage(obs, STAMP)
        self.assertEqual(stage.status, "SELL_SIDE_SWEPT")
        self.assertIn("displacement confirmation", stage.narrative)

    def test_swept_without_displacement(self) -> None:
        obs = _observation(
            liquidity=(
                LiquidityEvent(
                    side=LiquiditySide.BUY_SIDE, swept=True, displacement_confirmed=False
                ),
            )
        )
        stage = _liquidity_stage(obs, STAMP)
        self.assertIn("without confirmed displacement", stage.narrative)


class MomentumStageTests(unittest.TestCase):
    def test_none_is_unknown(self) -> None:
        stage = _momentum_stage(None, STAMP)
        self.assertEqual(stage.status, "UNKNOWN")

    def test_bullish_histogram(self) -> None:
        stage = _momentum_stage(MacdResult(macd_line=1.0, signal_line=0.5, histogram=0.5), STAMP)
        self.assertEqual(stage.status, "BULLISH")

    def test_bearish_histogram(self) -> None:
        stage = _momentum_stage(MacdResult(macd_line=-1.0, signal_line=-0.5, histogram=-0.5), STAMP)
        self.assertEqual(stage.status, "BEARISH")


class SmcStageTests(unittest.TestCase):
    def test_full_alignment_is_validated(self) -> None:
        obs = _observation(
            structure=MarketStructure(bias=StructureBias.BULLISH, break_of_structure=True),
            liquidity=(
                LiquidityEvent(
                    side=LiquiditySide.SELL_SIDE, swept=True, displacement_confirmed=True
                ),
            ),
        )
        stage = _smc_stage(obs, STAMP)
        self.assertEqual(stage.status, "VALIDATED")

    def test_missing_bos_is_not_validated(self) -> None:
        obs = _observation(
            structure=MarketStructure(bias=StructureBias.BULLISH, break_of_structure=False),
            liquidity=(
                LiquidityEvent(
                    side=LiquiditySide.SELL_SIDE, swept=True, displacement_confirmed=True
                ),
            ),
        )
        stage = _smc_stage(obs, STAMP)
        self.assertEqual(stage.status, "NOT_VALIDATED")
        self.assertIn("no confirmed break of structure", stage.narrative)

    def test_no_structure_lists_all_gaps(self) -> None:
        stage = _smc_stage(_observation(), STAMP)
        self.assertEqual(stage.status, "NOT_VALIDATED")
        self.assertIn("no directional structure bias", stage.narrative)
        self.assertIn("no displaced liquidity sweep", stage.narrative)


def _decision(
    verdict: DecisionVerdict,
    reasons: tuple[str, ...] = (),
    conflicts: tuple[str, ...] = (),
    missing: tuple[str, ...] = (),
) -> Decision:
    from packages.domain import Confidence

    return Decision(
        verdict=verdict,
        confidence=Confidence.HIGH if verdict != DecisionVerdict.WAIT else Confidence.NONE,
        score=1.0 if verdict != DecisionVerdict.WAIT else 0.0,
        evaluated_at=NOW,
        observation_time=NOW,
        reasons=reasons,
        conflicts=conflicts,
        missing_evidence=missing,
        policy_version="v1",
        contract_version="1.0.0",
        disclaimer="test",
    )


class ThesisStageAndEvolutionSummaryTests(unittest.TestCase):
    def test_buy_thesis_uses_reasons(self) -> None:
        decision = _decision(DecisionVerdict.BUY, reasons=("Bullish BOS confirmed.",))
        stage = _thesis_stage(decision, STAMP)
        self.assertEqual(stage.status, "BUY")
        self.assertIn("Bullish BOS confirmed.", stage.narrative)

    def test_wait_thesis_uses_missing_evidence(self) -> None:
        decision = _decision(DecisionVerdict.WAIT, missing=("Liquidity evidence is missing.",))
        stage = _thesis_stage(decision, STAMP)
        self.assertEqual(stage.status, "WAIT")
        self.assertIn("Liquidity evidence is missing.", stage.narrative)

    def test_evolution_summary_for_actionable_verdict(self) -> None:
        decision = _decision(DecisionVerdict.SELL, reasons=("Bearish BOS confirmed.",))
        summary = _evolution_summary(decision)
        self.assertIn("SELL setup", summary)
        self.assertIn("Bearish BOS confirmed.", summary)

    def test_evolution_summary_for_wait_uses_conflicts(self) -> None:
        decision = _decision(DecisionVerdict.WAIT, conflicts=("Price is in premium.",))
        summary = _evolution_summary(decision)
        self.assertIn("does not justify", summary)
        self.assertIn("Price is in premium.", summary)


def _trending_h1_candles(n: int = 40) -> list[Candle]:
    """A simple, monotonic price path with enough bars to clear
    compute_macd's own minimum (35) -- shape doesn't matter here, only that
    a real, non-None MACD line results."""
    start = datetime(2026, 8, 1, tzinfo=UTC)
    candles = []
    price = 100.0
    for i in range(n):
        o, c = price, price + 1.0
        candles.append(Candle(timestamp=start + timedelta(hours=i), open=o, high=c, low=o, close=c))
        price = c
    return candles


class FetchObservationAndMacdTests(unittest.TestCase):
    """The narrative's own momentum stage and the observation DecisionEngine
    gates on must read the exact same MACD reading -- never two independent
    computations that could silently diverge."""

    def test_observation_macd_value_matches_the_narrative_macd_result(self) -> None:
        candles = _trending_h1_candles()
        with patch("publish.generators.market_story.fetch_yahoo_candles", return_value=candles):
            obs, macd = _fetch_observation_and_macd()
        self.assertIsNotNone(macd)
        assert macd is not None
        self.assertEqual(obs.macd_value, macd.macd_line)

    def test_macd_result_matches_compute_macd_on_the_same_closes(self) -> None:
        candles = _trending_h1_candles()
        with patch("publish.generators.market_story.fetch_yahoo_candles", return_value=candles):
            _obs, macd = _fetch_observation_and_macd()
        expected = compute_macd([c.close for c in candles])
        self.assertEqual(macd, expected)

    def test_none_macd_when_candle_fetch_raises(self) -> None:
        fallback_obs = MarketObservation(
            symbol="XAUUSD",
            timeframe="H1",
            observed_at=datetime.now(UTC),
            structure=None,
            dealing_range=None,
            liquidity=(),
            source="no-data-source-reachable",
        )
        with (
            patch(
                "publish.generators.market_story.fetch_yahoo_candles",
                side_effect=Exception("network down"),
            ),
            patch(
                "publish.generators.market_story.build_live_market_collector"
            ) as mock_build_collector,
        ):
            mock_build_collector.return_value.fetch_live_observation.return_value = (
                fallback_obs,
                "FALLBACK:no-data-source-reachable",
            )
            obs, macd = _fetch_observation_and_macd()
        self.assertIsNone(macd)
        self.assertIsNone(obs.macd_value)


if __name__ == "__main__":
    unittest.main()
