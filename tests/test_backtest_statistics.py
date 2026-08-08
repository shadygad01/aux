"""Tests for aggregation math (win rate, average R:R, decided-outcome
denominator) and the attention_threshold sensitivity sweep."""

from __future__ import annotations

import unittest
from datetime import timedelta

from test_real_candle_decision_reachability import (
    _bullish_break_then_discount_retracement_rows,
    _candles,
)
from test_real_candle_decision_reachability import _evaluate as _real_decision

from backtest.statistics import run_and_summarize, sensitivity_sweep, summarize
from backtest.trade_simulator import Outcome, SimulatedTrade
from backtest.walk_forward import SignalEvent
from packages.domain import (
    Confidence,
    Decision,
    DecisionPolicy,
    DecisionVerdict,
    RiskGuidance,
)


def _decision(verdict: DecisionVerdict) -> Decision:
    from datetime import UTC, datetime

    return Decision(
        verdict=verdict,
        confidence=Confidence.HIGH,
        score=1.0,
        evaluated_at=datetime(2026, 1, 1, tzinfo=UTC),
        observation_time=datetime(2026, 1, 1, tzinfo=UTC),
        reasons=(),
        conflicts=(),
        missing_evidence=(),
        policy_version="v1-hypothesis-1",
        contract_version="1.0.0",
        disclaimer="test",
    )


def _fake_signal(verdict: DecisionVerdict) -> SignalEvent:
    from datetime import UTC, datetime

    from packages.domain import DealingRange, MarketObservation
    from packages.infrastructure.smc_detector import Candle

    candle = Candle(
        timestamp=datetime(2026, 1, 1, tzinfo=UTC), open=100, high=101, low=99, close=100
    )
    observation = MarketObservation(
        symbol="XAUUSD",
        timeframe="H1",
        observed_at=candle.timestamp,
        structure=None,
        dealing_range=DealingRange(low=90, high=110, current_price=100),
        liquidity=(),
        source="test",
    )
    return SignalEvent(
        index=0, observation=observation, decision=_decision(verdict), window_candles=(candle,)
    )


def _trade(verdict: DecisionVerdict, outcome: Outcome, achieved_rr: float | None) -> SimulatedTrade:
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
        risk_status="OK" if outcome != Outcome.NO_RISK_GUIDANCE else "UNAVAILABLE",
        calculation_method="test",
    )
    return SimulatedTrade(
        signal=_fake_signal(verdict),
        risk_guidance=risk_guidance,
        outcome=outcome,
        exit_index=1 if outcome in (Outcome.TARGET_HIT, Outcome.STOP_HIT) else None,
        achieved_rr=achieved_rr,
    )


class SummarizeTests(unittest.TestCase):
    def test_win_rate_and_average_rr_only_count_decided_outcomes(self) -> None:
        trades = [
            _trade(DecisionVerdict.BUY, Outcome.TARGET_HIT, 2.0),
            _trade(DecisionVerdict.BUY, Outcome.STOP_HIT, -1.0),
            _trade(DecisionVerdict.BUY, Outcome.OPEN_AT_END_OF_DATA, None),
            _trade(DecisionVerdict.BUY, Outcome.NO_RISK_GUIDANCE, None),
        ]
        summary = summarize(trades)

        self.assertEqual(summary.total_signals, 4)
        self.assertEqual(summary.win_rate_overall, 0.5)  # 1 win / 2 decided, not / 4 total
        self.assertEqual(summary.average_rr_overall, 0.5)  # (2.0 + -1.0) / 2
        self.assertEqual(summary.open_at_end_count, 1)
        self.assertEqual(summary.no_risk_guidance_count, 1)

    def test_buy_and_sell_are_broken_out_separately(self) -> None:
        trades = [
            _trade(DecisionVerdict.BUY, Outcome.TARGET_HIT, 2.0),
            _trade(DecisionVerdict.SELL, Outcome.STOP_HIT, -1.0),
        ]
        summary = summarize(trades)

        self.assertEqual(summary.total_buy, 1)
        self.assertEqual(summary.total_sell, 1)
        self.assertEqual(summary.win_rate_buy, 1.0)
        self.assertEqual(summary.win_rate_sell, 0.0)

    def test_no_trades_yields_none_rates_not_a_crash(self) -> None:
        summary = summarize([])
        self.assertEqual(summary.total_signals, 0)
        self.assertIsNone(summary.win_rate_overall)
        self.assertIsNone(summary.average_rr_overall)


class SensitivitySweepTests(unittest.TestCase):
    def test_sweep_runs_the_real_pipeline_once_per_threshold(self) -> None:
        """Uses the real BUY-producing fixture and proves the sweep plumbs
        a distinct DecisionPolicy through each independent run (one entry
        per requested threshold, each a full walk-forward). It does NOT
        prove attention_threshold changes the result here: DecisionEngine
        only reaches `not conflicts` (required for any BUY/SELL) when
        structure+location+liquidity all pass, which sums to exactly 1.0
        -- so score is 1.0 whenever conflicts is empty, and any valid
        threshold (<=1.0 by DecisionPolicy's own validation) is trivially
        satisfied. This fixture can't demonstrate threshold-driven
        exclusion because none exists for a conflict-free candidate in the
        current DecisionEngine -- documented here rather than silently
        assumed away."""
        candles = _candles(_bullish_break_then_discount_retracement_rows())
        candles += [
            candles[-1].__class__(
                timestamp=candles[-1].timestamp + timedelta(hours=i + 1),
                open=98.0,
                high=99.0,
                low=97.0,
                close=98.0,
            )
            for i in range(5)
        ]
        base_policy = DecisionPolicy()

        results = sensitivity_sweep(candles, base_policy, attention_thresholds=(0.01, 1.0))

        self.assertEqual(set(results.keys()), {0.01, 1.0})
        self.assertEqual(results[0.01].total_signals, 1)
        self.assertEqual(results[1.0].total_signals, 1)

    def test_run_and_summarize_matches_the_real_reachability_fixture(self) -> None:
        """Sanity check tying this module to the same ground truth as
        test_real_candle_decision_reachability.py: the full
        walk-forward -> simulate -> summarize pipeline must find the one
        real signal this fixture is known to produce."""
        candles = _candles(_bullish_break_then_discount_retracement_rows())
        decision = _real_decision(candles)
        self.assertEqual(decision.verdict, DecisionVerdict.BUY)

        summary, trades = run_and_summarize(candles, DecisionPolicy())
        self.assertEqual(summary.total_signals, 1)
        self.assertEqual(len(trades), 1)


if __name__ == "__main__":
    unittest.main()
