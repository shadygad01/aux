"""Tests for market_story.py's per-stage narrative builders — pure functions
over real domain objects, no network needed."""

from __future__ import annotations

import unittest
from datetime import UTC, datetime

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
from packages.infrastructure.momentum import MacdResult
from publish.generators.market_story import (
    _bias_stage,
    _discount_stage,
    _evolution_summary,
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


if __name__ == "__main__":
    unittest.main()
