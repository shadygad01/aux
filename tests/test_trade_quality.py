"""Tests for deriving TradeQuality/MarketThesis from a real Decision (no fabricated scores)."""

from __future__ import annotations

import unittest
from datetime import UTC, datetime

from packages.application import DecisionEngine, build_market_thesis, derive_trade_quality
from packages.application.trade_quality import _grade_for_score
from packages.domain import (
    Confidence,
    DealingRange,
    Decision,
    DecisionPolicy,
    DecisionVerdict,
    LiquidityEvent,
    LiquiditySide,
    MarketObservation,
    MarketStructure,
    StructureBias,
    TradeQualityGrade,
)

NOW = datetime(2026, 8, 6, 12, tzinfo=UTC)


class _RecordingLogger:
    def record(self, observation: MarketObservation, decision: Decision) -> None:
        pass


def _observation(
    *,
    bias: StructureBias = StructureBias.BULLISH,
    price: float = 20,
    liquidity_side: LiquiditySide = LiquiditySide.SELL_SIDE,
    swept: bool = True,
    displacement: bool = True,
    structure: bool = True,
    dealing_range: bool = True,
    liquidity: bool = True,
    break_of_structure: bool = True,
) -> MarketObservation:
    return MarketObservation(
        symbol="XAUUSD",
        timeframe="H1",
        observed_at=NOW,
        structure=(
            MarketStructure(bias=bias, break_of_structure=break_of_structure) if structure else None
        ),
        dealing_range=DealingRange(low=0, high=100, current_price=price) if dealing_range else None,
        liquidity=(LiquidityEvent(liquidity_side, swept, displacement),) if liquidity else (),
        source="unit-test",
    )


def _decision(observation: MarketObservation, policy: DecisionPolicy | None = None) -> Decision:
    return DecisionEngine(policy or DecisionPolicy(), _RecordingLogger()).evaluate(observation, NOW)


class DeriveTradeQualityTests(unittest.TestCase):
    def test_full_alignment_yields_max_score_and_full_breakdown(self) -> None:
        policy = DecisionPolicy()
        obs = _observation()
        decision = _decision(obs, policy)
        tq = derive_trade_quality(obs, decision, policy)
        self.assertEqual(tq.score, 100)
        self.assertEqual(tq.grade, TradeQualityGrade.EXCELLENT)
        self.assertEqual(tq.breakdown, {"structure": 40, "location": 30, "liquidity": 30})
        self.assertIn("break of structure", tq.explanation)

    def test_missing_evidence_yields_zero_score_and_empty_breakdown(self) -> None:
        policy = DecisionPolicy()
        obs = _observation(structure=False, dealing_range=False, liquidity=False)
        decision = _decision(obs, policy)
        self.assertEqual(decision.verdict, DecisionVerdict.WAIT)
        tq = derive_trade_quality(obs, decision, policy)
        self.assertEqual(tq.score, 0)
        self.assertEqual(tq.grade, TradeQualityGrade.INVALID)
        self.assertEqual(tq.breakdown, {})
        self.assertIn("missing", tq.explanation)

    def test_conflicting_location_still_reflects_partial_breakdown_under_wait(self) -> None:
        """A WAIT verdict from a conflict should still show the partial evidence
        that drove decision.score, matching the engine's own scoring — not zero
        out the breakdown just because the final verdict wasn't actionable."""
        policy = DecisionPolicy()
        obs = _observation(price=60)  # price in premium, BUY thesis needs discount
        decision = _decision(obs, policy)
        self.assertEqual(decision.verdict, DecisionVerdict.WAIT)
        self.assertEqual(decision.score, 0.7)
        tq = derive_trade_quality(obs, decision, policy)
        self.assertEqual(tq.score, 70)
        self.assertEqual(tq.grade, TradeQualityGrade.MODERATE)
        self.assertEqual(tq.breakdown, {"structure": 40, "location": 0, "liquidity": 30})

    def test_neutral_bias_yields_empty_breakdown(self) -> None:
        policy = DecisionPolicy()
        obs = _observation(bias=StructureBias.NEUTRAL)
        decision = _decision(obs, policy)
        self.assertEqual(decision.verdict, DecisionVerdict.WAIT)
        tq = derive_trade_quality(obs, decision, policy)
        self.assertEqual(tq.breakdown, {})

    def test_explanation_prefers_reasons_when_both_reasons_and_conflicts_exist(self) -> None:
        policy = DecisionPolicy()
        obs = _observation(price=60)  # structure/liquidity pass, location conflicts
        decision = _decision(obs, policy)
        self.assertTrue(decision.reasons)
        self.assertTrue(decision.conflicts)
        tq = derive_trade_quality(obs, decision, policy)
        self.assertEqual(tq.explanation, " ".join(decision.reasons))

    def test_explanation_falls_back_to_conflicts_when_no_reasons(self) -> None:
        policy = DecisionPolicy()
        obs = _observation(bias=StructureBias.NEUTRAL)  # WAIT before any reasons accumulate
        decision = _decision(obs, policy)
        self.assertFalse(decision.reasons)
        self.assertTrue(decision.conflicts)
        tq = derive_trade_quality(obs, decision, policy)
        self.assertEqual(tq.explanation, " ".join(decision.conflicts))

    def test_explanation_generic_fallback_when_decision_has_no_text_at_all(self) -> None:
        """A hand-built Decision without reasons/conflicts/missing_evidence isn't
        producible by DecisionEngine itself, but derive_trade_quality is a general
        function — it should still degrade to a generic explanation, not crash."""
        policy = DecisionPolicy()
        obs = _observation()
        decision = Decision(
            verdict=DecisionVerdict.WAIT,
            confidence=Confidence.NONE,
            score=0.0,
            evaluated_at=NOW,
            observation_time=NOW,
            reasons=(),
            conflicts=(),
            missing_evidence=(),
            policy_version="v1-hypothesis-1",
            contract_version="1.0.0",
            disclaimer="test",
        )
        tq = derive_trade_quality(obs, decision, policy)
        self.assertEqual(tq.explanation, "WAIT evaluation.")

    def test_grade_thresholds(self) -> None:
        cases = [
            (0, TradeQualityGrade.INVALID),
            (24, TradeQualityGrade.INVALID),
            (25, TradeQualityGrade.WEAK),
            (49, TradeQualityGrade.WEAK),
            (50, TradeQualityGrade.MODERATE),
            (74, TradeQualityGrade.MODERATE),
            (75, TradeQualityGrade.GOOD),
            (89, TradeQualityGrade.GOOD),
            (90, TradeQualityGrade.EXCELLENT),
            (100, TradeQualityGrade.EXCELLENT),
        ]
        for score, expected_grade in cases:
            with self.subTest(score=score):
                self.assertEqual(_grade_for_score(score), expected_grade)


class BuildMarketThesisTests(unittest.TestCase):
    def test_buy_thesis_carries_real_decision_fields(self) -> None:
        policy = DecisionPolicy()
        obs = _observation()
        decision = _decision(obs, policy)
        tq = derive_trade_quality(obs, decision, policy)
        thesis = build_market_thesis(
            thesis_id="THESIS-TEST-01",
            observation=obs,
            decision=decision,
            trade_quality=tq,
            execution_readiness=None,
        )
        self.assertEqual(thesis.verdict, DecisionVerdict.BUY)
        self.assertEqual(thesis.meaning, "Search for a high-quality setup")
        self.assertEqual(thesis.confidence, "HIGH")
        self.assertEqual(thesis.confidence_score, decision.score)
        self.assertEqual(thesis.uncertainty_score, 0.0)
        self.assertEqual(thesis.reasons, decision.reasons)
        self.assertEqual(thesis.setup_quality_score, tq.score)

    def test_wait_thesis_carries_missing_evidence_meaning(self) -> None:
        policy = DecisionPolicy()
        obs = _observation(structure=False, dealing_range=False, liquidity=False)
        decision = _decision(obs, policy)
        tq = derive_trade_quality(obs, decision, policy)
        thesis = build_market_thesis(
            thesis_id="THESIS-TEST-02",
            observation=obs,
            decision=decision,
            trade_quality=tq,
            execution_readiness=None,
        )
        self.assertEqual(thesis.verdict, DecisionVerdict.WAIT)
        self.assertEqual(thesis.meaning, "Do not search for a setup yet")
        self.assertEqual(thesis.confidence, "NONE")
        self.assertEqual(thesis.missing_evidence, decision.missing_evidence)


if __name__ == "__main__":
    unittest.main()
