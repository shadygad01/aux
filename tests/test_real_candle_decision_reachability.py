"""Regression test for a structural bug that made BUY/SELL mathematically
unreachable from any real, candle-derived MarketObservation.

`build_dealing_range` extends the range boundary to exactly match
`current_price` whenever price has moved past the last confirmed swing
(see its docstring) -- so whenever `break_of_structure` was checked against
the *same instantaneous* last close (the pre-fix behavior), a confirmed
break necessarily put current_price exactly at the range boundary,
which is always premium for a bullish break and always discount for a
bearish one. Since DecisionEngine requires break_of_structure AND the
*opposite* location (discount for BUY, premium for SELL), those two
conditions could never both be true on the same observation -- BUY/SELL
were provably unreachable regardless of market conditions, and every
existing DecisionEngine unit test used a hand-built DealingRange that
bypassed build_dealing_range entirely, so nothing caught it.

H-025 (BOS_LOOKBACK, see docs/hypothesis-register.md) fixes this by
checking break_of_structure over a recent window instead of only the
last candle: a break can remain valid while price retraces into a
genuine discount/premium zone on a later candle, matching standard
Smart Money Concepts practice (break, then retrace, then entry). These
tests run real candles through the complete, unmodified production
pipeline (smc_detector -> compute_macd -> DecisionEngine) end to end --
the exact path that was previously never exercised -- and must keep
producing a real BUY/SELL, not just a non-crashing WAIT.
"""

from __future__ import annotations

import unittest
from collections.abc import Sequence
from datetime import UTC, datetime, timedelta

from packages.application.decision_engine import DecisionEngine
from packages.domain import Decision, DecisionPolicy, DecisionVerdict, MarketObservation
from packages.infrastructure.momentum import compute_macd
from packages.infrastructure.smc_detector import Candle, build_observation_from_candles

_START = datetime(2026, 1, 1, tzinfo=UTC)


class _NullLogger:
    def record(self, observation: MarketObservation, decision: Decision) -> None:
        pass


def _leg(start: float, end: float, n: int) -> list[list[float]]:
    step = (end - start) / n
    out: list[list[float]] = []
    for i in range(n):
        o = start + step * i
        c = start + step * (i + 1)
        out.append([o, max(o, c), min(o, c), c])
    return out


def _candles(rows: Sequence[Sequence[float]]) -> list[Candle]:
    return [
        Candle(
            timestamp=_START + timedelta(hours=i),
            open=row[0],
            high=row[1],
            low=row[2],
            close=row[3],
        )
        for i, row in enumerate(rows)
    ]


def _evaluate(candles: list[Candle]) -> Decision:
    macd = compute_macd([c.close for c in candles])
    observation = build_observation_from_candles(
        candles,
        symbol="XAUUSD",
        timeframe="H1",
        source="test",
        macd_value=macd.macd_line if macd is not None else None,
    )
    engine = DecisionEngine(DecisionPolicy(), _NullLogger())
    return engine.evaluate(observation, candles[-1].timestamp + timedelta(hours=1))


def _bullish_break_then_discount_retracement_rows() -> list[list[float]]:
    """Bullish structure (same shape as test_smc_detector's proven fixture),
    a strong break above the confirmed swing high, then a pullback that
    sweeps the confirmed swing low with displacement and closes in a
    genuine discount zone -- the real-world pattern the BOS lookback exists
    to recognize."""
    rows: list[list[float]] = []
    rows += _leg(100, 90, 6)  # swing low ~89
    rows += _leg(90, 98, 6)  # swing high ~99
    rows += _leg(98, 94, 6)  # swing low ~93, higher low than 89
    rows += _leg(94, 108, 6)  # rally to ~108
    rows += _leg(108, 103, 4)  # pullback confirms 108 as swing high (~109)
    rows += _leg(103, 118, 6)  # strong rally, breaks above the swing high
    rows[5][2] -= 1.0
    rows[17][2] -= 1.0
    rows[11][1] += 1.0
    rows[23][1] += 1.0
    rows += _leg(118, 95, 8)  # pullback deep enough to also turn MACD negative
    # Sweep the confirmed swing low (~93) with a strong bullish reclaim.
    rows.append([93.5, 98.5, 91.0, 98.0])
    return rows


def _bearish_break_then_premium_retracement_rows() -> list[list[float]]:
    """Mirror of the bullish fixture: bearish structure, a break below the
    confirmed swing low, then a rally that sweeps the confirmed swing high
    with displacement and closes in a genuine premium zone."""
    rows: list[list[float]] = []
    rows += _leg(100, 110, 6)  # swing high ~109
    rows += _leg(110, 102, 6)  # swing low ~103
    rows += _leg(102, 106, 6)  # swing high ~105, lower high than 109
    rows += _leg(106, 90, 6)  # rally down
    rows += _leg(90, 95, 4)  # pullback confirms swing low ~89, lower low than 103
    rows += _leg(95, 80, 6)  # breaks below the swing low
    rows[5][1] += 1.0
    rows[17][1] += 1.0
    rows[11][2] -= 1.0
    rows[23][2] -= 1.0
    rows += _leg(80, 103, 9)  # rally deep enough to also turn MACD positive
    # Sweep the confirmed swing high (~107) with a strong bearish reclaim.
    rows.append([104.0, 107.5, 99.0, 99.5])
    return rows


class RealCandleDecisionReachabilityTests(unittest.TestCase):
    def test_a_real_bullish_break_and_discount_retracement_produces_buy(self) -> None:
        decision = _evaluate(_candles(_bullish_break_then_discount_retracement_rows()))
        self.assertEqual(decision.verdict, DecisionVerdict.BUY)
        self.assertEqual(decision.score, 1.0)
        self.assertFalse(decision.conflicts)

    def test_a_real_bearish_break_and_premium_retracement_produces_sell(self) -> None:
        decision = _evaluate(_candles(_bearish_break_then_premium_retracement_rows()))
        self.assertEqual(decision.verdict, DecisionVerdict.SELL)
        self.assertEqual(decision.score, 1.0)
        self.assertFalse(decision.conflicts)

    def test_break_is_recognized_only_within_the_lookback_window(self) -> None:
        """A break far outside BOS_LOOKBACK candles in the past must not
        count -- this isn't unconditional memory, it's a bounded window.
        Uses hand-built swings directly (bypassing find_swings) for exact
        control over exactly where the break sits relative to the window,
        rather than fighting fractal-detection side effects in a full
        candle series."""
        from packages.infrastructure.smc_detector import (
            BOS_LOOKBACK,
            SwingKind,
            SwingPoint,
            classify_structure,
        )

        swings = [
            SwingPoint(index=0, timestamp=_START, price=85.0, kind=SwingKind.LOW),
            SwingPoint(index=1, timestamp=_START, price=95.0, kind=SwingKind.HIGH),
            SwingPoint(index=2, timestamp=_START, price=90.0, kind=SwingKind.LOW),
            SwingPoint(index=3, timestamp=_START, price=100.0, kind=SwingKind.HIGH),
        ]

        def _flat_candles(count: int, close: float, offset: int) -> list[Candle]:
            return [
                Candle(
                    timestamp=_START + timedelta(hours=offset + i),
                    open=close,
                    high=close,
                    low=close,
                    close=close,
                )
                for i in range(count)
            ]

        below_level = _flat_candles(5, 92.0, offset=0)
        break_candle = _flat_candles(1, 105.0, offset=len(below_level))
        candles_break_recent = (
            below_level + break_candle + _flat_candles(2, 92.0, offset=len(below_level) + 1)
        )
        structure_recent = classify_structure(swings, candles_break_recent)
        assert structure_recent is not None
        self.assertTrue(structure_recent.break_of_structure)

        candles_break_stale = (
            below_level
            + break_candle
            + _flat_candles(BOS_LOOKBACK + 2, 92.0, offset=len(below_level) + 1)
        )
        structure_stale = classify_structure(swings, candles_break_stale)
        assert structure_stale is not None
        self.assertFalse(structure_stale.break_of_structure)


if __name__ == "__main__":
    unittest.main()
