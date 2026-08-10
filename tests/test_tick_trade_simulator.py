from __future__ import annotations

import json
import unittest
from dataclasses import asdict
from datetime import UTC, datetime, timedelta

from backtest.mtf_models import Direction, ExitMode, ExitPlan, Tick, TradeIntent, TradeOutcome
from backtest.tick_trade_simulator import ExecutionAssumptions, simulate_intent, simulate_portfolio

START = datetime(2026, 1, 5, 10, tzinfo=UTC)


def ticks(prices: list[tuple[float, float]]) -> list[Tick]:
    return [
        Tick(START + timedelta(seconds=index), bid, ask, 1.0, 1.0)
        for index, (bid, ask) in enumerate(prices)
    ]


class TickTradeSimulatorTests(unittest.TestCase):
    def intent(self, mode: ExitMode = ExitMode.FIXED_R) -> TradeIntent:
        return TradeIntent("PAT-1", START, Direction.BUY, 1.0, 1.0, ExitPlan(mode))

    def test_buy_enters_at_ask_and_exits_target_on_bid(self) -> None:
        trade = simulate_intent(
            self.intent(),
            ticks([(100.0, 100.2), (104.3, 104.5)]),
            ExecutionAssumptions(),
        )
        assert trade is not None
        self.assertEqual(trade.entry_price, 100.2)
        self.assertEqual(trade.outcome, TradeOutcome.TARGET)
        self.assertEqual(trade.net_r, 4.0)

    def test_partial_moves_to_breakeven_then_trails_runner(self) -> None:
        trade = simulate_intent(
            self.intent(ExitMode.PARTIAL_TRAIL),
            ticks([(100.0, 100.2), (102.2, 102.4), (103.0, 103.2), (102.5, 102.7)]),
            ExecutionAssumptions(),
        )
        assert trade is not None
        self.assertTrue(trade.partial_taken)
        self.assertEqual(trade.outcome, TradeOutcome.TRAIL)
        self.assertGreater(trade.net_r, 1.0)

    def test_cost_and_slippage_are_deducted_in_r(self) -> None:
        trade = simulate_intent(
            self.intent(),
            ticks([(100.0, 100.2), (104.3, 104.5)]),
            ExecutionAssumptions(
                commission_per_side_points=0.1, slippage_per_side_points=0.1
            ),
        )
        assert trade is not None
        self.assertAlmostEqual(trade.net_r, 3.6)

    def test_one_open_trade_and_three_per_day_are_enforced(self) -> None:
        intents = [
            TradeIntent(
                f"PAT-{index}",
                START + timedelta(seconds=index * 2),
                Direction.BUY,
                1.0,
                1.0,
                ExitPlan(ExitMode.FIXED_R, target_r=1.0),
            )
            for index in range(5)
        ]
        market = ticks([(100.0, 100.2), (101.2, 101.4)] * 10)
        trades = simulate_portfolio(intents, market, ExecutionAssumptions(max_trades_per_day=3))
        self.assertLessEqual(len(trades), 3)

    def test_fixture_is_byte_deterministic(self) -> None:
        first = simulate_intent(
            self.intent(), ticks([(100.0, 100.2), (104.2, 104.4)]), ExecutionAssumptions()
        )
        second = simulate_intent(
            self.intent(), ticks([(100.0, 100.2), (104.2, 104.4)]), ExecutionAssumptions()
        )
        self.assertIsNotNone(first)
        self.assertIsNotNone(second)
        if first is None or second is None:
            self.fail("deterministic fixture did not produce a trade")
        self.assertEqual(
            json.dumps(asdict(first), sort_keys=True, default=str),
            json.dumps(asdict(second), sort_keys=True, default=str),
        )


if __name__ == "__main__":
    unittest.main()
