"""Tests for backtest_report.json/.md generation."""

from __future__ import annotations

import json
import tempfile
import unittest
from datetime import UTC, datetime
from pathlib import Path

from backtest.report import write_report
from backtest.statistics import BacktestSummary
from backtest.trade_simulator import Outcome, SimulatedTrade
from backtest.walk_forward import SignalEvent
from packages.domain import (
    Confidence,
    DealingRange,
    Decision,
    DecisionPolicy,
    DecisionVerdict,
    MarketObservation,
    RiskGuidance,
)
from packages.infrastructure.smc_detector import Candle

_NOW = datetime(2026, 1, 1, tzinfo=UTC)


def _summary() -> BacktestSummary:
    return BacktestSummary(
        total_signals=2,
        total_buy=1,
        total_sell=1,
        win_rate_overall=0.5,
        win_rate_buy=1.0,
        win_rate_sell=0.0,
        average_rr_overall=0.5,
        average_rr_buy=2.0,
        average_rr_sell=-1.0,
        target_hit_count=1,
        stop_hit_count=1,
        open_at_end_count=0,
        no_risk_guidance_count=0,
    )


def _trade() -> SimulatedTrade:
    candle = Candle(timestamp=_NOW, open=100, high=101, low=99, close=100)
    observation = MarketObservation(
        symbol="XAUUSD",
        timeframe="H1",
        observed_at=_NOW,
        structure=None,
        dealing_range=DealingRange(low=90, high=110, current_price=100),
        liquidity=(),
        source="test",
    )
    decision = Decision(
        verdict=DecisionVerdict.BUY,
        confidence=Confidence.HIGH,
        score=1.0,
        evaluated_at=_NOW,
        observation_time=_NOW,
        reasons=(),
        conflicts=(),
        missing_evidence=(),
        policy_version="v1-hypothesis-1",
        contract_version="1.0.0",
        disclaimer="test",
    )
    signal = SignalEvent(
        index=0, observation=observation, decision=decision, window_candles=(candle,)
    )
    risk_guidance = RiskGuidance(
        entry_price=100.0,
        stop_loss_price=95.0,
        target_price=110.0,
        stop_distance=5.0,
        target_distance=10.0,
        risk_reward=2.0,
        invalidation_level=95.0,
        invalidation_source="DEALING_RANGE",
        atr=1.0,
        target_source="DEALING_RANGE",
        risk_status="OK",
        calculation_method="test",
    )
    return SimulatedTrade(
        signal=signal,
        risk_guidance=risk_guidance,
        outcome=Outcome.TARGET_HIT,
        exit_index=1,
        achieved_rr=2.0,
    )


class WriteReportTests(unittest.TestCase):
    def test_writes_both_json_and_markdown(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp)
            write_report(
                output_dir,
                ticker="GC=F",
                policy=DecisionPolicy(),
                candle_count=100,
                data_start=_NOW,
                data_end=_NOW,
                summary=_summary(),
                trades=[_trade()],
            )
            self.assertTrue((output_dir / "backtest_report.json").exists())
            self.assertTrue((output_dir / "backtest_report.md").exists())

    def test_json_report_round_trips_summary_and_trades(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp)
            write_report(
                output_dir,
                ticker="GC=F",
                policy=DecisionPolicy(),
                candle_count=100,
                data_start=_NOW,
                data_end=_NOW,
                summary=_summary(),
                trades=[_trade()],
            )
            payload = json.loads((output_dir / "backtest_report.json").read_text())
            self.assertEqual(payload["summary"]["total_signals"], 2)
            self.assertEqual(len(payload["trades"]), 1)
            self.assertEqual(payload["trades"][0]["verdict"], "BUY")
            self.assertIsNone(payload["sensitivity_sweep"])

    def test_markdown_report_includes_caveats_and_sensitivity_when_present(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp)
            write_report(
                output_dir,
                ticker="GC=F",
                policy=DecisionPolicy(),
                candle_count=100,
                data_start=_NOW,
                data_end=_NOW,
                summary=_summary(),
                trades=[_trade()],
                sensitivity={0.75: _summary()},
            )
            markdown = (output_dir / "backtest_report.md").read_text()
            self.assertIn("## Caveats", markdown)
            self.assertIn("## Sensitivity sweep", markdown)
            self.assertIn("Data coverage actually obtained", markdown)

    def test_missing_data_bounds_render_as_none_not_a_crash(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp)
            write_report(
                output_dir,
                ticker="GC=F",
                policy=DecisionPolicy(),
                candle_count=0,
                data_start=None,
                data_end=None,
                summary=BacktestSummary(
                    total_signals=0,
                    total_buy=0,
                    total_sell=0,
                    win_rate_overall=None,
                    win_rate_buy=None,
                    win_rate_sell=None,
                    average_rr_overall=None,
                    average_rr_buy=None,
                    average_rr_sell=None,
                    target_hit_count=0,
                    stop_hit_count=0,
                    open_at_end_count=0,
                    no_risk_guidance_count=0,
                ),
                trades=[],
            )
            payload = json.loads((output_dir / "backtest_report.json").read_text())
            self.assertIsNone(payload["run"]["data_start"])
            self.assertEqual(payload["trades"], [])


if __name__ == "__main__":
    unittest.main()
