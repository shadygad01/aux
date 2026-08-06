"""Unit and integration tests for Multi-Timeframe Scalping Engine and Generator."""

from __future__ import annotations

import tempfile
import unittest
from datetime import UTC, datetime
from pathlib import Path

from packages.application.execution_readiness_engine import ExecutionReadinessEngine
from packages.application.multi_timeframe_engine import MultiTimeframeEngine
from packages.domain import (
    DealingRange,
    DecisionVerdict,
    LiquidityEvent,
    LiquiditySide,
    MarketObservation,
    MarketStructure,
    MarketThesis,
    StructureBias,
    TradeQuality,
    TradeQualityGrade,
)
from publish.generators import multi_timeframe as mtf_generator


class MultiTimeframeEngineTests(unittest.TestCase):
    def setUp(self) -> None:
        self.now = datetime(2026, 8, 5, 12, 0, 0, tzinfo=UTC)
        self.engine_er = ExecutionReadinessEngine()
        self.mtf_engine = MultiTimeframeEngine()

    def _make_htf_thesis(self, verdict: DecisionVerdict) -> MarketThesis:
        is_bull = verdict == DecisionVerdict.BUY
        bias = StructureBias.BULLISH if is_bull else StructureBias.BEARISH
        obs = MarketObservation(
            symbol="XAUUSD",
            timeframe="H1",
            observed_at=self.now,
            structure=MarketStructure(
                bias=bias,
                break_of_structure=True,
                change_of_character=True,
            ),
            dealing_range=DealingRange(low=3300.0, high=3400.0, current_price=3305.0),
            liquidity=(
                LiquidityEvent(
                    side=LiquiditySide.SELL_SIDE, swept=True, displacement_confirmed=True
                ),
            ),
            source="test",
        )
        readiness = self.engine_er.evaluate(obs, verdict, 94, None, self.now)
        tq = TradeQuality(
            score=94,
            grade=TradeQualityGrade.EXCELLENT,
            breakdown={"structure": 30},
            explanation="Test quality",
        )
        return MarketThesis(
            thesis_id="THESIS-01",
            symbol="XAUUSD",
            timeframe="H1",
            verdict=verdict,
            meaning="BUY" if verdict == DecisionVerdict.BUY else "SELL",
            confidence="HIGH",
            confidence_score=1.0,
            uncertainty_score=0.0,
            setup_quality_score=94,
            execution_readiness=readiness,
            trade_quality=tq,
            reasons=("BOS",),
            conflicts=(),
            missing_evidence=(),
            evaluated_at=self.now,
            policy_version="v1",
            contract_version="1.0.0",
        )

    def test_m5_aligned_with_h1_buy_bias(self) -> None:
        htf_thesis = self._make_htf_thesis(DecisionVerdict.BUY)
        ltf_obs = MarketObservation(
            symbol="XAUUSD",
            timeframe="M5",
            observed_at=self.now,
            structure=MarketStructure(
                bias=StructureBias.BULLISH, break_of_structure=True, change_of_character=True
            ),
            dealing_range=DealingRange(low=3302.0, high=3312.0, current_price=3304.5),
            liquidity=(
                LiquidityEvent(
                    side=LiquiditySide.SELL_SIDE, swept=True, displacement_confirmed=True
                ),
            ),
            source="test",
            higher_timeframe="H1",
            execution_timeframe="M5",
        )
        readiness = self.engine_er.evaluate(ltf_obs, DecisionVerdict.BUY, 94, None, self.now)

        mtf_thesis = self.mtf_engine.evaluate_multi_timeframe(
            htf_thesis, ltf_obs, readiness, self.now
        )
        self.assertEqual(mtf_thesis.cascade_status, "ALIGNED")
        self.assertEqual(mtf_thesis.execution_timeframe, "M5")
        self.assertLessEqual(mtf_thesis.tight_stop_loss_pips, 15.0)

    def test_m5_counter_trend_blocked_by_h1_bias(self) -> None:
        htf_thesis = self._make_htf_thesis(DecisionVerdict.BUY)
        ltf_obs = MarketObservation(
            symbol="XAUUSD",
            timeframe="M5",
            observed_at=self.now,
            structure=MarketStructure(
                bias=StructureBias.BEARISH, break_of_structure=True, change_of_character=True
            ),
            dealing_range=DealingRange(low=3302.0, high=3312.0, current_price=3310.0),
            liquidity=(),
            source="test",
            higher_timeframe="H1",
            execution_timeframe="M5",
        )
        readiness = self.engine_er.evaluate(ltf_obs, DecisionVerdict.BUY, 94, None, self.now)

        mtf_thesis = self.mtf_engine.evaluate_multi_timeframe(
            htf_thesis, ltf_obs, readiness, self.now
        )
        self.assertEqual(mtf_thesis.cascade_status, "CONFLICT")
        self.assertIn("opposes H1 BUY bias", "".join(mtf_thesis.reasons))

    def test_generator_execution(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            out_file = Path(tmpdir) / "multi_timeframe.json"
            mtf_generator.generate(out_file)
            self.assertTrue(out_file.exists())
