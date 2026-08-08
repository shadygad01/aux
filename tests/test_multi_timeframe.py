"""Unit and integration tests for Multi-Timeframe Scalping Engine and Generator."""

from __future__ import annotations

import json
import tempfile
import unittest
from datetime import UTC, datetime
from pathlib import Path

from packages.application.execution_readiness_engine import ExecutionReadinessEngine
from packages.application.multi_timeframe_engine import (
    ATR_BUFFER_MULTIPLIER,
    MultiTimeframeEngine,
)
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

NOW = datetime(2026, 8, 5, 12, 0, 0, tzinfo=UTC)
DEFAULT_DEALING_RANGE = DealingRange(low=3302.0, high=3312.0, current_price=3304.5)


class MultiTimeframeEngineTests(unittest.TestCase):
    def setUp(self) -> None:
        self.now = NOW
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

    def _ltf_observation(
        self,
        *,
        bias: StructureBias = StructureBias.BULLISH,
        dealing_range: DealingRange = DEFAULT_DEALING_RANGE,
        liquidity: tuple[LiquidityEvent, ...] = (),
        break_of_structure: bool = True,
    ) -> MarketObservation:
        return MarketObservation(
            symbol="XAUUSD",
            timeframe="M5",
            observed_at=self.now,
            structure=MarketStructure(
                bias=bias, break_of_structure=break_of_structure, change_of_character=True
            ),
            dealing_range=dealing_range,
            liquidity=liquidity,
            source="test",
            higher_timeframe="H1",
            execution_timeframe="M5",
        )

    # -- Direction / cascade: unchanged behavior -----------------------------

    def test_m5_aligned_with_h1_buy_bias(self) -> None:
        htf_thesis = self._make_htf_thesis(DecisionVerdict.BUY)
        ltf_obs = self._ltf_observation(
            liquidity=(
                LiquidityEvent(
                    side=LiquiditySide.SELL_SIDE,
                    swept=True,
                    displacement_confirmed=True,
                    level=3301.0,
                ),
            )
        )
        readiness = self.engine_er.evaluate(ltf_obs, DecisionVerdict.BUY, 94, None, self.now)

        mtf_thesis = self.mtf_engine.evaluate_multi_timeframe(
            htf_thesis, ltf_obs, readiness, self.now, atr=2.0
        )
        self.assertEqual(mtf_thesis.cascade_status, "ALIGNED")
        self.assertEqual(mtf_thesis.execution_timeframe, "M5")

    def test_m5_counter_trend_blocked_by_h1_bias(self) -> None:
        htf_thesis = self._make_htf_thesis(DecisionVerdict.BUY)
        ltf_obs = self._ltf_observation(
            bias=StructureBias.BEARISH,
            dealing_range=DealingRange(low=3302.0, high=3312.0, current_price=3310.0),
        )
        readiness = self.engine_er.evaluate(ltf_obs, DecisionVerdict.BUY, 94, None, self.now)

        mtf_thesis = self.mtf_engine.evaluate_multi_timeframe(
            htf_thesis, ltf_obs, readiness, self.now, atr=2.0
        )
        self.assertEqual(mtf_thesis.cascade_status, "CONFLICT")
        self.assertIn("opposes H1 BUY bias", "".join(mtf_thesis.reasons))

    def test_m5_counter_trend_blocked_by_h1_sell_bias(self) -> None:
        htf_thesis = self._make_htf_thesis(DecisionVerdict.SELL)
        ltf_obs = self._ltf_observation(
            dealing_range=DealingRange(low=3302.0, high=3312.0, current_price=3304.0)
        )
        readiness = self.engine_er.evaluate(ltf_obs, DecisionVerdict.SELL, 94, None, self.now)

        mtf_thesis = self.mtf_engine.evaluate_multi_timeframe(
            htf_thesis, ltf_obs, readiness, self.now, atr=2.0
        )
        self.assertEqual(mtf_thesis.cascade_status, "CONFLICT")
        self.assertIn("opposes H1 SELL bias", "".join(mtf_thesis.reasons))

    def test_m5_aligned_without_confirmed_break_of_structure(self) -> None:
        htf_thesis = self._make_htf_thesis(DecisionVerdict.BUY)
        ltf_obs = self._ltf_observation(break_of_structure=False)
        readiness = self.engine_er.evaluate(ltf_obs, DecisionVerdict.BUY, 94, None, self.now)

        mtf_thesis = self.mtf_engine.evaluate_multi_timeframe(
            htf_thesis, ltf_obs, readiness, self.now, atr=2.0
        )
        self.assertEqual(mtf_thesis.cascade_status, "ALIGNED")
        self.assertIn("no M5 BOS yet", mtf_thesis.ltf_trigger)

    def test_direction_is_never_reversed_by_the_risk_model(self) -> None:
        """The risk model must not influence htf_bias/cascade_status -- it is
        strictly downstream of the (unchanged) directional cascade."""
        for verdict in (DecisionVerdict.BUY, DecisionVerdict.SELL):
            htf_thesis = self._make_htf_thesis(verdict)
            bias = (
                StructureBias.BULLISH if verdict is DecisionVerdict.BUY else StructureBias.BEARISH
            )
            ltf_obs = self._ltf_observation(bias=bias)
            readiness = self.engine_er.evaluate(ltf_obs, verdict, 94, None, self.now)
            for atr in (None, 0.0, 2.0):
                mtf_thesis = self.mtf_engine.evaluate_multi_timeframe(
                    htf_thesis, ltf_obs, readiness, self.now, atr
                )
                self.assertEqual(mtf_thesis.htf_bias, verdict)
                self.assertEqual(mtf_thesis.cascade_status, "ALIGNED")

    # -- SL: structural/liquidity invalidation -------------------------------

    def test_buy_stop_anchors_to_swept_sell_side_liquidity_level(self) -> None:
        htf_thesis = self._make_htf_thesis(DecisionVerdict.BUY)
        ltf_obs = self._ltf_observation(
            liquidity=(
                LiquidityEvent(
                    side=LiquiditySide.SELL_SIDE,
                    swept=True,
                    displacement_confirmed=True,
                    level=3301.0,
                ),
            )
        )
        readiness = self.engine_er.evaluate(ltf_obs, DecisionVerdict.BUY, 94, None, self.now)

        mtf_thesis = self.mtf_engine.evaluate_multi_timeframe(
            htf_thesis, ltf_obs, readiness, self.now, atr=2.0
        )
        risk = mtf_thesis.risk_guidance
        self.assertEqual(risk.invalidation_source, "LIQUIDITY_SWEEP")
        self.assertEqual(risk.invalidation_level, 3301.0)
        self.assertEqual(risk.stop_loss_price, 3301.0 - 2.0 * ATR_BUFFER_MULTIPLIER)

    def test_sell_stop_anchors_to_swept_buy_side_liquidity_level(self) -> None:
        htf_thesis = self._make_htf_thesis(DecisionVerdict.SELL)
        ltf_obs = self._ltf_observation(
            bias=StructureBias.BEARISH,
            liquidity=(
                LiquidityEvent(
                    side=LiquiditySide.BUY_SIDE,
                    swept=True,
                    displacement_confirmed=True,
                    level=3315.0,
                ),
            ),
        )
        readiness = self.engine_er.evaluate(ltf_obs, DecisionVerdict.SELL, 94, None, self.now)

        mtf_thesis = self.mtf_engine.evaluate_multi_timeframe(
            htf_thesis, ltf_obs, readiness, self.now, atr=2.0
        )
        risk = mtf_thesis.risk_guidance
        self.assertEqual(risk.invalidation_source, "LIQUIDITY_SWEEP")
        self.assertEqual(risk.invalidation_level, 3315.0)
        self.assertEqual(risk.stop_loss_price, 3315.0 + 2.0 * ATR_BUFFER_MULTIPLIER)

    def test_stop_falls_back_to_dealing_range_boundary_without_a_liquidity_level(self) -> None:
        htf_thesis = self._make_htf_thesis(DecisionVerdict.BUY)
        ltf_obs = self._ltf_observation(liquidity=())
        readiness = self.engine_er.evaluate(ltf_obs, DecisionVerdict.BUY, 94, None, self.now)

        mtf_thesis = self.mtf_engine.evaluate_multi_timeframe(
            htf_thesis, ltf_obs, readiness, self.now, atr=2.0
        )
        risk = mtf_thesis.risk_guidance
        self.assertEqual(risk.invalidation_source, "DEALING_RANGE")
        self.assertEqual(risk.invalidation_level, 3302.0)  # dealing_range.low

    # -- TP: target selection -------------------------------------------------

    def test_target_uses_opposing_execution_liquidity_when_available(self) -> None:
        htf_thesis = self._make_htf_thesis(DecisionVerdict.BUY)
        ltf_obs = self._ltf_observation(
            liquidity=(
                LiquidityEvent(
                    side=LiquiditySide.BUY_SIDE,
                    swept=False,
                    displacement_confirmed=False,
                    level=3315.0,
                ),
            )
        )
        readiness = self.engine_er.evaluate(ltf_obs, DecisionVerdict.BUY, 94, None, self.now)

        mtf_thesis = self.mtf_engine.evaluate_multi_timeframe(
            htf_thesis, ltf_obs, readiness, self.now, atr=2.0
        )
        risk = mtf_thesis.risk_guidance
        self.assertEqual(risk.target_source, "EXECUTION_LIQUIDITY")
        self.assertEqual(risk.target_price, 3315.0)

    def test_target_falls_back_to_dealing_range_boundary(self) -> None:
        htf_thesis = self._make_htf_thesis(DecisionVerdict.BUY)
        ltf_obs = self._ltf_observation(liquidity=())
        readiness = self.engine_er.evaluate(ltf_obs, DecisionVerdict.BUY, 94, None, self.now)

        mtf_thesis = self.mtf_engine.evaluate_multi_timeframe(
            htf_thesis, ltf_obs, readiness, self.now, atr=2.0
        )
        risk = mtf_thesis.risk_guidance
        self.assertEqual(risk.target_source, "DEALING_RANGE")
        self.assertEqual(risk.target_price, 3312.0)  # dealing_range.high

    def test_target_on_the_wrong_side_of_entry_is_rejected_in_favor_of_the_fallback(self) -> None:
        """An opposing liquidity level that isn't actually beyond entry (e.g.
        stale/malformed data) must not be published as a target."""
        htf_thesis = self._make_htf_thesis(DecisionVerdict.BUY)
        ltf_obs = self._ltf_observation(
            liquidity=(
                LiquidityEvent(
                    side=LiquiditySide.BUY_SIDE,
                    swept=False,
                    displacement_confirmed=False,
                    level=3303.0,  # below entry_price (3304.5) -- invalid for a BUY target
                ),
            )
        )
        readiness = self.engine_er.evaluate(ltf_obs, DecisionVerdict.BUY, 94, None, self.now)

        mtf_thesis = self.mtf_engine.evaluate_multi_timeframe(
            htf_thesis, ltf_obs, readiness, self.now, atr=2.0
        )
        risk = mtf_thesis.risk_guidance
        self.assertEqual(risk.target_source, "DEALING_RANGE")
        self.assertEqual(risk.target_price, 3312.0)

    # -- RR: calculated, never fixed ------------------------------------------

    def test_risk_reward_is_calculated_from_actual_prices(self) -> None:
        htf_thesis = self._make_htf_thesis(DecisionVerdict.BUY)
        ltf_obs = self._ltf_observation(
            liquidity=(
                LiquidityEvent(
                    side=LiquiditySide.SELL_SIDE,
                    swept=True,
                    displacement_confirmed=True,
                    level=3301.0,
                ),
                LiquidityEvent(
                    side=LiquiditySide.BUY_SIDE,
                    swept=False,
                    displacement_confirmed=False,
                    level=3315.0,
                ),
            )
        )
        readiness = self.engine_er.evaluate(ltf_obs, DecisionVerdict.BUY, 94, None, self.now)

        mtf_thesis = self.mtf_engine.evaluate_multi_timeframe(
            htf_thesis, ltf_obs, readiness, self.now, atr=2.0
        )
        risk = mtf_thesis.risk_guidance
        # entry=3304.5, stop=3301.0-1.0=3300.0 (risk=4.5), target=3315.0 (reward=10.5)
        self.assertEqual(risk.risk_status, "OK")
        self.assertEqual(risk.stop_distance, 4.5)
        self.assertEqual(risk.target_distance, 10.5)
        self.assertEqual(risk.risk_reward, round(10.5 / 4.5, 2))
        self.assertEqual(risk.calculation_method, "structure_atr_liquidity_v1")

    # -- Fail-closed behavior --------------------------------------------------

    def test_insufficient_atr_data_yields_insufficient_data_status_not_a_fabricated_stop(
        self,
    ) -> None:
        htf_thesis = self._make_htf_thesis(DecisionVerdict.BUY)
        ltf_obs = self._ltf_observation(liquidity=())
        readiness = self.engine_er.evaluate(ltf_obs, DecisionVerdict.BUY, 94, None, self.now)

        mtf_thesis = self.mtf_engine.evaluate_multi_timeframe(
            htf_thesis, ltf_obs, readiness, self.now, atr=None
        )
        risk = mtf_thesis.risk_guidance
        self.assertEqual(risk.risk_status, "INSUFFICIENT_DATA")
        self.assertIsNone(risk.stop_loss_price)
        self.assertIsNone(risk.risk_reward)
        self.assertIsNone(risk.atr)
        # Target/invalidation don't depend on ATR and can still be reported.
        self.assertIsNotNone(risk.target_price)
        self.assertIsNotNone(risk.invalidation_level)

    def test_missing_dealing_range_yields_insufficient_data_status(self) -> None:
        htf_thesis = self._make_htf_thesis(DecisionVerdict.BUY)
        ltf_obs = MarketObservation(
            symbol="XAUUSD",
            timeframe="M5",
            observed_at=self.now,
            structure=None,
            dealing_range=None,
            liquidity=(),
            source="test",
            higher_timeframe="H1",
            execution_timeframe="M5",
        )
        readiness = self.engine_er.evaluate(ltf_obs, DecisionVerdict.BUY, 94, None, self.now)

        mtf_thesis = self.mtf_engine.evaluate_multi_timeframe(
            htf_thesis, ltf_obs, readiness, self.now, atr=2.0
        )
        risk = mtf_thesis.risk_guidance
        self.assertEqual(risk.risk_status, "INSUFFICIENT_DATA")
        self.assertIsNone(risk.entry_price)
        self.assertIsNone(risk.stop_loss_price)
        self.assertIsNone(risk.target_price)

    def test_zero_risk_yields_unavailable_status_not_a_fabricated_ratio(self) -> None:
        """Price sitting exactly at the invalidation boundary with zero
        volatility (atr=0) collapses risk to zero -- must reject, not divide
        by zero or publish a fake ratio."""
        htf_thesis = self._make_htf_thesis(DecisionVerdict.BUY)
        ltf_obs = self._ltf_observation(
            dealing_range=DealingRange(low=3302.0, high=3312.0, current_price=3302.0),
            liquidity=(),
        )
        readiness = self.engine_er.evaluate(ltf_obs, DecisionVerdict.BUY, 94, None, self.now)

        mtf_thesis = self.mtf_engine.evaluate_multi_timeframe(
            htf_thesis, ltf_obs, readiness, self.now, atr=0.0
        )
        risk = mtf_thesis.risk_guidance
        self.assertEqual(risk.risk_status, "UNAVAILABLE")
        self.assertIsNone(risk.risk_reward)

    def test_zero_reward_yields_unavailable_status_not_a_fabricated_ratio(self) -> None:
        """Price sitting exactly at the dealing-range boundary with no
        opposing liquidity leaves zero reward -- must reject."""
        htf_thesis = self._make_htf_thesis(DecisionVerdict.BUY)
        ltf_obs = self._ltf_observation(
            dealing_range=DealingRange(low=3302.0, high=3312.0, current_price=3312.0),
            liquidity=(),
        )
        readiness = self.engine_er.evaluate(ltf_obs, DecisionVerdict.BUY, 94, None, self.now)

        mtf_thesis = self.mtf_engine.evaluate_multi_timeframe(
            htf_thesis, ltf_obs, readiness, self.now, atr=2.0
        )
        risk = mtf_thesis.risk_guidance
        self.assertEqual(risk.risk_status, "UNAVAILABLE")
        self.assertIsNone(risk.risk_reward)

    def test_wait_verdict_yields_unavailable_risk_guidance(self) -> None:
        htf_thesis = self._make_htf_thesis(DecisionVerdict.WAIT)
        ltf_obs = self._ltf_observation(bias=StructureBias.NEUTRAL)
        readiness = self.engine_er.evaluate(ltf_obs, DecisionVerdict.WAIT, 0, None, self.now)

        mtf_thesis = self.mtf_engine.evaluate_multi_timeframe(
            htf_thesis, ltf_obs, readiness, self.now, atr=2.0
        )
        risk = mtf_thesis.risk_guidance
        self.assertEqual(risk.risk_status, "UNAVAILABLE")
        self.assertIsNone(risk.stop_loss_price)
        self.assertIsNone(risk.target_price)

    def test_no_fabricated_legacy_constants_appear_anywhere(self) -> None:
        """The fabricated constants this change replaces must never reappear
        as computed output, and the fields that carried them must be gone
        from the schema entirely."""
        htf_thesis = self._make_htf_thesis(DecisionVerdict.BUY)
        ltf_obs = self._ltf_observation(
            liquidity=(
                LiquidityEvent(
                    side=LiquiditySide.SELL_SIDE,
                    swept=True,
                    displacement_confirmed=True,
                    level=3301.0,
                ),
            )
        )
        readiness = self.engine_er.evaluate(ltf_obs, DecisionVerdict.BUY, 94, None, self.now)

        mtf_thesis = self.mtf_engine.evaluate_multi_timeframe(
            htf_thesis, ltf_obs, readiness, self.now, atr=2.0
        )
        as_dict = mtf_thesis.to_dict()
        self.assertNotIn("tight_stop_loss_pips", as_dict)
        self.assertNotIn("target_rr", as_dict)
        risk_dict = as_dict["risk_guidance"]
        assert isinstance(risk_dict, dict)
        self.assertNotIn(risk_dict.get("stop_distance"), (12.5, 18.0))
        self.assertNotIn(risk_dict.get("risk_reward"), (3.2, 2.8))

    # -- Production path --------------------------------------------------------

    def test_generator_execution(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            out_file = Path(tmpdir) / "multi_timeframe.json"
            mtf_generator.generate(out_file)
            self.assertTrue(out_file.exists())

            artifact = json.loads(out_file.read_text(encoding="utf-8"))
            thesis = artifact["payload"]["multi_timeframe_thesis"]
            self.assertNotIn("tight_stop_loss_pips", thesis)
            self.assertNotIn("target_rr", thesis)
            risk = thesis["risk_guidance"]
            self.assertIn(risk["risk_status"], ("OK", "INSUFFICIENT_DATA", "UNAVAILABLE"))
            self.assertEqual(risk["calculation_method"], "structure_atr_liquidity_v1")


if __name__ == "__main__":
    unittest.main()
