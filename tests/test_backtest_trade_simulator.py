"""Tests for outcome classification, using the same proven real-candle BUY
signal as test_real_candle_decision_reachability.py so risk guidance
(entry=98.0, stop=91.46, target=109.0) is real, not invented."""

from __future__ import annotations

import unittest
from datetime import timedelta

from test_real_candle_decision_reachability import (
    _bullish_break_then_discount_retracement_rows,
    _candles,
)

from backtest.trade_simulator import AMBIGUOUS_CANDLE_RULE, Outcome, simulate_trade
from backtest.walk_forward import SignalEvent, walk_forward
from packages.domain import DecisionPolicy
from packages.infrastructure.smc_detector import Candle


def _real_buy_signal() -> tuple[SignalEvent, list[Candle]]:
    candles = _candles(_bullish_break_then_discount_retracement_rows())
    signals = walk_forward(candles, DecisionPolicy())
    assert len(signals) == 1
    return signals[0], candles


def _flat(after: Candle, n: int, close: float, high: float, low: float) -> list[Candle]:
    return [
        Candle(
            timestamp=after.timestamp + timedelta(hours=i + 1),
            open=close,
            high=high,
            low=low,
            close=close,
        )
        for i in range(n)
    ]


class TradeSimulatorTests(unittest.TestCase):
    def test_target_hit_before_stop_is_a_win(self) -> None:
        signal, candles = _real_buy_signal()
        following = [
            Candle(
                timestamp=candles[-1].timestamp + timedelta(hours=1),
                open=100.0,
                high=109.5,  # clears the real target (109.0) without touching the stop
                low=99.0,
                close=109.0,
            )
        ]
        trade = simulate_trade(signal, candles + following)
        self.assertEqual(trade.outcome, Outcome.TARGET_HIT)
        self.assertEqual(trade.achieved_rr, trade.risk_guidance.risk_reward)
        self.assertIsNotNone(trade.exit_index)

    def test_stop_hit_before_target_is_a_loss(self) -> None:
        signal, candles = _real_buy_signal()
        following = [
            Candle(
                timestamp=candles[-1].timestamp + timedelta(hours=1),
                open=95.0,
                high=96.0,
                low=91.0,  # clears the real stop (91.46) without touching the target
                close=92.0,
            )
        ]
        trade = simulate_trade(signal, candles + following)
        self.assertEqual(trade.outcome, Outcome.STOP_HIT)
        self.assertEqual(trade.achieved_rr, -1.0)

    def test_same_candle_ambiguity_is_resolved_conservatively_as_a_stop(self) -> None:
        signal, candles = _real_buy_signal()
        following = [
            Candle(
                timestamp=candles[-1].timestamp + timedelta(hours=1),
                open=100.0,
                high=110.0,  # clears the target ...
                low=90.0,  # ... AND clears the stop, same candle
                close=100.0,
            )
        ]
        trade = simulate_trade(signal, candles + following)
        self.assertEqual(trade.outcome, Outcome.STOP_HIT)
        self.assertEqual(AMBIGUOUS_CANDLE_RULE, "CONSERVATIVE_STOP_FIRST")

    def test_neither_level_touched_stays_open_at_end_of_data(self) -> None:
        signal, candles = _real_buy_signal()
        following = _flat(candles[-1], n=5, close=98.0, high=99.0, low=97.0)
        trade = simulate_trade(signal, candles + following)
        self.assertEqual(trade.outcome, Outcome.OPEN_AT_END_OF_DATA)
        self.assertIsNone(trade.exit_index)
        self.assertIsNone(trade.achieved_rr)

    def test_the_signal_candles_own_high_low_are_never_inspected(self) -> None:
        """The signal candle's own close IS entry_price -- checking its own
        high/low for a stop/target touch would be self-referential
        lookahead, not a real trade. The real signal candle's own low
        (91.0) already sits below the real stop (91.46); if the loop
        incorrectly included index 42 itself, this would misclassify as an
        immediate STOP_HIT instead of correctly looking only forward."""
        signal, candles = _real_buy_signal()
        signal_candle = candles[signal.index]
        self.assertLess(signal_candle.low, 91.46)  # below the real stop-loss price
        following = _flat(candles[-1], n=5, close=98.0, high=99.0, low=97.0)
        trade = simulate_trade(signal, candles + following)
        self.assertEqual(trade.outcome, Outcome.OPEN_AT_END_OF_DATA)

    def test_insufficient_atr_history_yields_no_risk_guidance_and_excludes_from_rr(self) -> None:
        signal, candles = _real_buy_signal()
        short_window_signal = SignalEvent(
            index=signal.index,
            observation=signal.observation,
            decision=signal.decision,
            window_candles=tuple(candles[:10]),  # fewer than compute_atr's minimum
        )
        trade = simulate_trade(short_window_signal, candles)
        self.assertEqual(trade.outcome, Outcome.NO_RISK_GUIDANCE)
        self.assertEqual(trade.risk_guidance.risk_status, "INSUFFICIENT_DATA")
        self.assertIsNone(trade.achieved_rr)


if __name__ == "__main__":
    unittest.main()
