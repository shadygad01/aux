"""Unit and integration tests for Execution Readiness Engine, Capability, and Backtest."""

from __future__ import annotations

import tempfile
import unittest
from datetime import UTC, datetime
from pathlib import Path

from capabilities.contracts import HealthState
from capabilities.execution_readiness import ExecutionReadinessCapability
from packages.application.execution_readiness_engine import ExecutionReadinessEngine
from packages.domain import (
    DealingRange,
    DecisionVerdict,
    ExecutionStatus,
    LiquidityEvent,
    LiquiditySide,
    MacroAssessment,
    MarketObservation,
    MarketStructure,
    StructureBias,
)
from publish.generators import execution_readiness as execution_generator


class MockTelemetry:
    def __init__(self) -> None:
        self.metrics: list[object] = []
        self.logs: list[object] = []

    def metric(self, value: object) -> None:
        self.metrics.append(value)

    def log(self, value: object) -> None:
        self.logs.append(value)


class ExecutionReadinessTests(unittest.TestCase):
    def setUp(self) -> None:
        self.now = datetime(2026, 8, 5, 12, 0, 0, tzinfo=UTC)
        self.engine = ExecutionReadinessEngine()

    def test_fresh_execution_status(self) -> None:
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
        readiness = self.engine.evaluate(obs, DecisionVerdict.BUY, 94, None, self.now)
        self.assertEqual(readiness.status, ExecutionStatus.FRESH)
        self.assertGreaterEqual(readiness.readiness_score, 80)

    def test_late_execution_status(self) -> None:
        obs = MarketObservation(
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
        readiness = self.engine.evaluate(obs, DecisionVerdict.BUY, 94, None, self.now)
        self.assertEqual(readiness.status, ExecutionStatus.LATE)
        self.assertLess(readiness.readiness_score, 50)
        self.assertIn("Price traveled", "".join(readiness.reasons_for_reduction))

    def test_macro_force_wait_overrides_readiness(self) -> None:
        obs = MarketObservation(
            symbol="XAUUSD",
            timeframe="H1",
            observed_at=self.now,
            structure=MarketStructure(
                bias=StructureBias.BULLISH, break_of_structure=True, change_of_character=True
            ),
            dealing_range=DealingRange(low=3300.0, high=3400.0, current_price=3305.0),
            liquidity=(),
            source="test",
        )
        macro = MacroAssessment(
            assessment_id="ASM-01",
            macro_score=0.2,
            confidence_modifier=-0.2,
            force_wait=True,
            wait_reason="Active NFP High Impact News",
            evidence=("NFP active",),
            evaluated_at=self.now,
        )
        readiness = self.engine.evaluate(obs, DecisionVerdict.BUY, 94, macro, self.now)
        self.assertEqual(readiness.status, ExecutionStatus.WAIT)
        self.assertEqual(readiness.readiness_score, 0)

    def test_capability_and_generator(self) -> None:
        telemetry = MockTelemetry()
        capability = ExecutionReadinessCapability(self.engine, telemetry)
        self.assertEqual(capability.health(self.now).state, HealthState.HEALTHY)

        with tempfile.TemporaryDirectory() as tmpdir:
            out_file = Path(tmpdir) / "execution_readiness.json"
            execution_generator.generate(out_file)
            self.assertTrue(out_file.exists())
