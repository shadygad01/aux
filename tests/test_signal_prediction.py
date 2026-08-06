"""Unit and integration tests for Signal Prediction Engine and Generator."""

from __future__ import annotations

import tempfile
import unittest
from datetime import UTC, datetime
from pathlib import Path

from packages.application.signal_prediction_engine import SignalPredictionEngine
from packages.domain import (
    DealingRange,
    LiquidityEvent,
    LiquiditySide,
    MarketObservation,
    MarketStructure,
    StructureBias,
)
from publish.generators import signal_prediction as sp_generator


class SignalPredictionEngineTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = SignalPredictionEngine()

    def test_predict_next_signal_london_window(self) -> None:
        eval_time = datetime(2026, 8, 6, 7, 15, 0, tzinfo=UTC)
        obs = MarketObservation(
            symbol="XAUUSD",
            timeframe="H1",
            observed_at=eval_time,
            structure=MarketStructure(
                bias=StructureBias.BULLISH, break_of_structure=True, change_of_character=True
            ),
            dealing_range=DealingRange(low=3300.0, high=3400.0, current_price=3345.50),
            liquidity=(
                LiquidityEvent(
                    side=LiquiditySide.SELL_SIDE, swept=True, displacement_confirmed=True
                ),
            ),
            source="test",
        )
        prediction = self.engine.predict_next_signal(obs, eval_time)

        self.assertEqual(prediction.symbol, "XAUUSD")
        self.assertEqual(prediction.current_price, 3345.50)
        self.assertEqual(prediction.next_window_start.hour, 8)
        self.assertEqual(prediction.estimated_minutes_remaining, 45)
        self.assertGreater(prediction.probability_next_2h_pct, 70.0)

    def test_generator_execution(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            out_file = Path(tmpdir) / "signal_prediction.json"
            sp_generator.generate(out_file)
            self.assertTrue(out_file.exists())
