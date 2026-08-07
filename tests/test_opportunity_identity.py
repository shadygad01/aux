"""Unit and integration tests for Opportunity Identity Engine, Capability, and Backtest."""

from __future__ import annotations

import json
import tempfile
import unittest
from datetime import UTC, datetime
from pathlib import Path

from capabilities.contracts import HealthState
from capabilities.opportunity_identity import OpportunityIdentityCapability
from packages.application.execution_readiness_engine import ExecutionReadinessEngine
from packages.application.opportunity_identity_engine import OpportunityIdentityEngine
from packages.domain import (
    DealingRange,
    DecisionVerdict,
    ExecutionReadiness,
    LiquidityEvent,
    LiquiditySide,
    MarketObservation,
    MarketStructure,
    MarketThesis,
    OpportunityLifecycleState,
    StructureBias,
    TradeQuality,
    TradeQualityGrade,
)
from packages.domain._json_coerce import to_int
from publish.generators import opportunity_identity as opp_generator


class MockTelemetry:
    def __init__(self) -> None:
        self.metrics: list[object] = []
        self.logs: list[object] = []

    def metric(self, value: object) -> None:
        self.metrics.append(value)

    def log(self, value: object) -> None:
        self.logs.append(value)


class OpportunityIdentityTests(unittest.TestCase):
    def setUp(self) -> None:
        self.now = datetime(2026, 8, 5, 12, 0, 0, tzinfo=UTC)
        self.engine_er = ExecutionReadinessEngine()
        self.engine_opp = OpportunityIdentityEngine()

    def _make_thesis(self, obs: MarketObservation, readiness: ExecutionReadiness) -> MarketThesis:
        tq = TradeQuality(
            score=94,
            grade=TradeQualityGrade.EXCELLENT,
            breakdown={"structure": 30},
            explanation="Test quality",
        )
        return MarketThesis(
            thesis_id="THESIS-01",
            symbol=obs.symbol,
            timeframe=obs.timeframe,
            verdict=DecisionVerdict.BUY,
            meaning="BUY",
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

    def test_new_opportunity_id_generated_on_initial_observation(self) -> None:
        obs = MarketObservation(
            symbol="XAUUSD",
            timeframe="H1",
            observed_at=self.now,
            structure=MarketStructure(
                bias=StructureBias.BULLISH, break_of_structure=True, change_of_character=True
            ),
            dealing_range=DealingRange(low=3300.0, high=3400.0, current_price=3305.0),
            liquidity=(
                LiquidityEvent(
                    side=LiquiditySide.SELL_SIDE, swept=True, displacement_confirmed=True
                ),
            ),
            source="test",
        )
        readiness = self.engine_er.evaluate(obs, DecisionVerdict.BUY, 94, None, self.now)
        thesis = self._make_thesis(obs, readiness)

        curr_opp, prev_opp = self.engine_opp.evaluate_opportunity(obs, thesis, readiness, self.now)
        self.assertTrue(curr_opp.opportunity_id.startswith("OPP-20260805-"))
        self.assertTrue(curr_opp.is_fresh)
        self.assertEqual(curr_opp.current_state, OpportunityLifecycleState.ACTIVE)
        self.assertIsNone(prev_opp)

    def test_opportunity_id_remains_constant_during_continuation(self) -> None:
        obs1 = MarketObservation(
            symbol="XAUUSD",
            timeframe="H1",
            observed_at=self.now,
            structure=MarketStructure(
                bias=StructureBias.BULLISH, break_of_structure=True, change_of_character=True
            ),
            dealing_range=DealingRange(low=3300.0, high=3400.0, current_price=3305.0),
            liquidity=(
                LiquidityEvent(
                    side=LiquiditySide.SELL_SIDE, swept=True, displacement_confirmed=True
                ),
            ),
            source="test",
        )
        readiness1 = self.engine_er.evaluate(obs1, DecisionVerdict.BUY, 94, None, self.now)
        thesis1 = self._make_thesis(obs1, readiness1)

        opp1, _ = self.engine_opp.evaluate_opportunity(obs1, thesis1, readiness1, self.now)

        # Advanced observation of the SAME opportunity (price advanced to 3345.0)
        obs2 = MarketObservation(
            symbol="XAUUSD",
            timeframe="H1",
            observed_at=self.now,
            structure=MarketStructure(
                bias=StructureBias.BULLISH, break_of_structure=True, change_of_character=True
            ),
            dealing_range=DealingRange(low=3300.0, high=3400.0, current_price=3345.0),
            liquidity=(
                LiquidityEvent(
                    side=LiquiditySide.SELL_SIDE, swept=True, displacement_confirmed=True
                ),
            ),
            source="test",
        )
        readiness2 = self.engine_er.evaluate(obs2, DecisionVerdict.BUY, 94, None, self.now)
        thesis2 = self._make_thesis(obs2, readiness2)

        opp2, _ = self.engine_opp.evaluate_opportunity(obs2, thesis2, readiness2, self.now)

        # ID MUST remain constant!
        self.assertEqual(opp2.opportunity_id, opp1.opportunity_id)
        self.assertFalse(opp2.is_fresh)
        self.assertEqual(opp2.current_state, OpportunityLifecycleState.AGING)

    def test_new_sweep_generates_new_opportunity_id(self) -> None:
        obs1 = MarketObservation(
            symbol="XAUUSD",
            timeframe="H1",
            observed_at=self.now,
            structure=MarketStructure(
                bias=StructureBias.BULLISH, break_of_structure=True, change_of_character=True
            ),
            dealing_range=DealingRange(low=3300.0, high=3400.0, current_price=3305.0),
            liquidity=(
                LiquidityEvent(
                    side=LiquiditySide.SELL_SIDE, swept=True, displacement_confirmed=True
                ),
            ),
            source="test",
        )
        readiness1 = self.engine_er.evaluate(obs1, DecisionVerdict.BUY, 94, None, self.now)
        thesis1 = self._make_thesis(obs1, readiness1)

        opp1, _ = self.engine_opp.evaluate_opportunity(obs1, thesis1, readiness1, self.now)

        # NEW liquidity sweep event at a NEW dealing range (3400 - 3500)
        obs2 = MarketObservation(
            symbol="XAUUSD",
            timeframe="H1",
            observed_at=self.now,
            structure=MarketStructure(
                bias=StructureBias.BULLISH, break_of_structure=True, change_of_character=True
            ),
            dealing_range=DealingRange(low=3400.0, high=3500.0, current_price=3405.0),
            liquidity=(
                LiquidityEvent(
                    side=LiquiditySide.SELL_SIDE, swept=True, displacement_confirmed=True
                ),
            ),
            source="test",
        )
        readiness2 = self.engine_er.evaluate(obs2, DecisionVerdict.BUY, 94, None, self.now)
        thesis2 = self._make_thesis(obs2, readiness2)

        opp2, prev_opp = self.engine_opp.evaluate_opportunity(obs2, thesis2, readiness2, self.now)

        # NEW ID generated!
        self.assertNotEqual(opp2.opportunity_id, opp1.opportunity_id)
        self.assertTrue(opp2.is_fresh)
        assert prev_opp is not None
        self.assertEqual(prev_opp.opportunity_id, opp1.opportunity_id)

    def test_engine_state_survives_restore_for_continuation(self) -> None:
        """A fresh engine (as created by every separate publish run) must pick
        up where the last run left off, or continuation is misread as a brand
        new opportunity and `previous_opportunity` never gets populated."""
        obs1 = MarketObservation(
            symbol="XAUUSD",
            timeframe="H1",
            observed_at=self.now,
            structure=MarketStructure(
                bias=StructureBias.BULLISH, break_of_structure=True, change_of_character=True
            ),
            dealing_range=DealingRange(low=3300.0, high=3400.0, current_price=3305.0),
            liquidity=(
                LiquidityEvent(
                    side=LiquiditySide.SELL_SIDE, swept=True, displacement_confirmed=True
                ),
            ),
            source="test",
        )
        readiness1 = self.engine_er.evaluate(obs1, DecisionVerdict.BUY, 94, None, self.now)
        thesis1 = self._make_thesis(obs1, readiness1)
        opp1, prev1 = self.engine_opp.evaluate_opportunity(obs1, thesis1, readiness1, self.now)
        self.assertIsNone(prev1)
        snapshot = self.engine_opp.snapshot_state()

        # Simulate a brand new process (new engine instance) restoring the
        # previous run's persisted state before evaluating the next observation.
        last_sig = snapshot["last_sweep_signature"]
        assert last_sig is None or isinstance(last_sig, str)
        fresh_engine = OpportunityIdentityEngine()
        fresh_engine.restore_state(opp1, prev1, to_int(snapshot["counter"]), last_sig)

        # Same dealing range / sweep signature -> continuation, not a new opportunity.
        obs2 = MarketObservation(
            symbol="XAUUSD",
            timeframe="H1",
            observed_at=self.now,
            structure=MarketStructure(
                bias=StructureBias.BULLISH, break_of_structure=True, change_of_character=True
            ),
            dealing_range=DealingRange(low=3300.0, high=3400.0, current_price=3345.0),
            liquidity=(
                LiquidityEvent(
                    side=LiquiditySide.SELL_SIDE, swept=True, displacement_confirmed=True
                ),
            ),
            source="test",
        )
        readiness2 = self.engine_er.evaluate(obs2, DecisionVerdict.BUY, 94, None, self.now)
        thesis2 = self._make_thesis(obs2, readiness2)
        opp2, prev2 = fresh_engine.evaluate_opportunity(obs2, thesis2, readiness2, self.now)

        self.assertEqual(opp2.opportunity_id, opp1.opportunity_id)
        self.assertFalse(opp2.is_fresh)
        self.assertIsNone(prev2)

        # A genuinely new sweep at a new dealing range on yet another fresh
        # process must now correctly archive the restored opportunity as previous.
        snapshot2 = fresh_engine.snapshot_state()
        last_sig2 = snapshot2["last_sweep_signature"]
        assert last_sig2 is None or isinstance(last_sig2, str)
        another_fresh_engine = OpportunityIdentityEngine()
        another_fresh_engine.restore_state(opp2, prev2, to_int(snapshot2["counter"]), last_sig2)
        obs3 = MarketObservation(
            symbol="XAUUSD",
            timeframe="H1",
            observed_at=self.now,
            structure=MarketStructure(
                bias=StructureBias.BULLISH, break_of_structure=True, change_of_character=True
            ),
            dealing_range=DealingRange(low=3400.0, high=3500.0, current_price=3405.0),
            liquidity=(
                LiquidityEvent(
                    side=LiquiditySide.SELL_SIDE, swept=True, displacement_confirmed=True
                ),
            ),
            source="test",
        )
        readiness3 = self.engine_er.evaluate(obs3, DecisionVerdict.BUY, 94, None, self.now)
        thesis3 = self._make_thesis(obs3, readiness3)
        opp3, prev3 = another_fresh_engine.evaluate_opportunity(obs3, thesis3, readiness3, self.now)

        self.assertNotEqual(opp3.opportunity_id, opp2.opportunity_id)
        self.assertTrue(opp3.is_fresh)
        assert prev3 is not None
        self.assertEqual(prev3.opportunity_id, opp2.opportunity_id)

    def test_generator_persists_previous_opportunity_across_process_runs(self) -> None:
        """Regression test: calling generate() twice against the same output
        file (simulating two separate CI publish runs) must not silently drop
        opportunity continuity — the persisted `engine_state` must round-trip."""
        with tempfile.TemporaryDirectory() as tmpdir:
            out_file = Path(tmpdir) / "opportunity_identity.json"

            opp_generator.generate(out_file)
            first_raw = json.loads(out_file.read_text(encoding="utf-8"))
            first_payload = first_raw["payload"]
            self.assertIn("engine_state", first_payload)
            self.assertIn("counter", first_payload["engine_state"])

            restored_current, restored_previous, counter, sig = opp_generator._load_engine_state(
                out_file
            )
            assert restored_current is not None
            self.assertEqual(
                restored_current.opportunity_id,
                first_payload["current_opportunity"]["opportunity_id"],
            )
            self.assertEqual(counter, first_payload["engine_state"]["counter"])
            self.assertEqual(sig, first_payload["engine_state"]["last_sweep_signature"])

            opp_generator.generate(out_file)
            second_raw = json.loads(out_file.read_text(encoding="utf-8"))
            second_payload = second_raw["payload"]
            # The counter must never reset backwards across runs.
            self.assertGreaterEqual(
                second_payload["engine_state"]["counter"], first_payload["engine_state"]["counter"]
            )

    def test_capability_and_generator(self) -> None:
        telemetry = MockTelemetry()
        capability = OpportunityIdentityCapability(self.engine_opp, telemetry)
        self.assertEqual(capability.health(self.now).state, HealthState.HEALTHY)

        with tempfile.TemporaryDirectory() as tmpdir:
            out_file = Path(tmpdir) / "opportunity_identity.json"
            opp_generator.generate(out_file)
            self.assertTrue(out_file.exists())
