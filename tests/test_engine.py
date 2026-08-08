import unittest
from datetime import UTC, datetime, timedelta

from packages.application import DecisionEngine
from packages.application.errors import DecisionEvaluationError
from packages.domain import (
    Confidence,
    DealingRange,
    Decision,
    DecisionPolicy,
    DecisionVerdict,
    LiquidityEvent,
    LiquiditySide,
    MarketObservation,
    MarketStructure,
    StructureBias,
)

NOW = datetime(2026, 8, 5, 12, tzinfo=UTC)


class RecordingLogger:
    def __init__(self) -> None:
        self.decisions: list[Decision] = []

    def record(self, observation: MarketObservation, decision: Decision) -> None:
        self.decisions.append(decision)


class FailingLogger:
    def record(self, observation: MarketObservation, decision: Decision) -> None:
        raise OSError("audit sink unavailable")


def observation(
    *,
    bias: StructureBias = StructureBias.BULLISH,
    price: float = 40,
    liquidity_side: LiquiditySide = LiquiditySide.SELL_SIDE,
    swept: bool = True,
    displacement: bool = True,
    observed_at: datetime = NOW - timedelta(minutes=10),
    structure: bool = True,
    liquidity: bool = True,
    symbol: str = "XAUUSD",
    dealing_range: bool = True,
    break_of_structure: bool = True,
    change_of_character: bool = False,
    macd: float | None = -1.0,
) -> MarketObservation:
    return MarketObservation(
        symbol=symbol,
        timeframe="H1",
        observed_at=observed_at,
        structure=MarketStructure(
            bias, break_of_structure=break_of_structure, change_of_character=change_of_character
        )
        if structure
        else None,
        dealing_range=DealingRange(0, 100, price) if dealing_range else None,
        liquidity=(LiquidityEvent(liquidity_side, swept, displacement),) if liquidity else (),
        source="unit-test",
        macd_value=macd,
    )


class DecisionEngineTests(unittest.TestCase):
    def setUp(self) -> None:
        self.logger = RecordingLogger()
        self.engine = DecisionEngine(DecisionPolicy(), self.logger)

    def test_bullish_confluence_justifies_searching_for_buy_setup(self) -> None:
        decision = self.engine.evaluate(observation(), NOW)
        self.assertEqual(decision.verdict, DecisionVerdict.BUY)
        self.assertEqual(decision.confidence, Confidence.HIGH)
        self.assertEqual(decision.score, 1.0)
        self.assertEqual(len(decision.reasons), 3)
        self.assertFalse(decision.conflicts)
        self.assertEqual(self.logger.decisions, [decision])

    def test_bearish_confluence_justifies_searching_for_sell_setup(self) -> None:
        decision = self.engine.evaluate(
            observation(
                bias=StructureBias.BEARISH,
                price=60,
                liquidity_side=LiquiditySide.BUY_SIDE,
                macd=1.0,
            ),
            NOW,
        )
        self.assertEqual(decision.verdict, DecisionVerdict.SELL)
        self.assertEqual(decision.score, 1.0)

    def test_wrong_range_location_fails_closed(self) -> None:
        decision = self.engine.evaluate(observation(price=60), NOW)
        self.assertEqual(decision.verdict, DecisionVerdict.WAIT)
        self.assertEqual(decision.score, 0.7)
        self.assertTrue(any("requires discount" in item for item in decision.conflicts))

    def test_liquidity_without_displacement_fails_closed(self) -> None:
        decision = self.engine.evaluate(observation(displacement=False), NOW)
        self.assertEqual(decision.verdict, DecisionVerdict.WAIT)
        self.assertTrue(any("No confirmed" in item for item in decision.conflicts))

    def test_missing_mandatory_evidence_fails_closed(self) -> None:
        decision = self.engine.evaluate(observation(structure=False), NOW)
        self.assertEqual(decision.verdict, DecisionVerdict.WAIT)
        self.assertEqual(decision.score, 0.0)
        self.assertTrue(any("market-structure" in item for item in decision.missing_evidence))

    def test_stale_evidence_fails_closed(self) -> None:
        stale = observation(observed_at=NOW - timedelta(hours=5))
        decision = self.engine.evaluate(stale, NOW)
        self.assertEqual(decision.verdict, DecisionVerdict.WAIT)
        self.assertTrue(any("Fresh evidence" in item for item in decision.missing_evidence))

    def test_future_evidence_fails_closed(self) -> None:
        future = observation(observed_at=NOW + timedelta(seconds=1))
        decision = self.engine.evaluate(future, NOW)
        self.assertEqual(decision.verdict, DecisionVerdict.WAIT)
        self.assertTrue(any("future" in item for item in decision.conflicts))

    def test_unsupported_symbol_fails_closed(self) -> None:
        decision = self.engine.evaluate(observation(symbol="EURUSD"), NOW)
        self.assertEqual(decision.verdict, DecisionVerdict.WAIT)
        self.assertIn("Unsupported symbol", decision.conflicts[0])

    def test_missing_range_and_liquidity_are_both_reported(self) -> None:
        decision = self.engine.evaluate(observation(dealing_range=False, liquidity=False), NOW)
        self.assertEqual(len(decision.missing_evidence), 2)

    def test_neutral_structure_fails_closed(self) -> None:
        decision = self.engine.evaluate(observation(bias=StructureBias.NEUTRAL), NOW)
        self.assertEqual(decision.verdict, DecisionVerdict.WAIT)
        self.assertIn("neutral", decision.conflicts[0].lower())

    def test_bullish_change_of_character_fails_closed(self) -> None:
        """A CHoCH is a break against the classified bias -- a reversal
        signal per Smart Money Concepts methodology, not a second
        confirmation to require alongside break_of_structure. It must veto
        the candidate outright, even with every other gate satisfied."""
        decision = self.engine.evaluate(observation(change_of_character=True), NOW)
        self.assertEqual(decision.verdict, DecisionVerdict.WAIT)
        self.assertEqual(decision.score, 0.0)
        self.assertTrue(any("Character" in item for item in decision.conflicts))

    def test_bearish_change_of_character_fails_closed(self) -> None:
        decision = self.engine.evaluate(
            observation(
                bias=StructureBias.BEARISH,
                price=60,
                liquidity_side=LiquiditySide.BUY_SIDE,
                macd=1.0,
                change_of_character=True,
            ),
            NOW,
        )
        self.assertEqual(decision.verdict, DecisionVerdict.WAIT)
        self.assertTrue(any("Character" in item for item in decision.conflicts))

    def test_direction_without_structure_break_fails_closed(self) -> None:
        decision = self.engine.evaluate(observation(break_of_structure=False), NOW)
        self.assertEqual(decision.verdict, DecisionVerdict.WAIT)
        self.assertIn("confirmed break", decision.conflicts[0])

    def test_evaluation_time_requires_timezone(self) -> None:
        naive_time = datetime(2026, 8, 5, 12)
        with self.assertRaisesRegex(DecisionEvaluationError, "timezone-aware"):
            self.engine.evaluate(observation(), naive_time)

    def test_policy_rejects_unbalanced_weights(self) -> None:
        with self.assertRaisesRegex(ValueError, "sum to 1"):
            DecisionPolicy(structure_weight=0.5, location_weight=0.5, liquidity_weight=0.5)

    def test_policy_rejects_invalid_configuration(self) -> None:
        invalid_policies = (
            {"version": ""},
            {"maximum_age": timedelta(0)},
            {"equilibrium_band": 0.5},
            {"attention_threshold": 1.1},
        )
        for values in invalid_policies:
            with self.subTest(values=values), self.assertRaises(ValueError):
                DecisionPolicy(**values)

    def test_logging_failure_is_observable_and_preserves_cause(self) -> None:
        engine = DecisionEngine(DecisionPolicy(), FailingLogger())
        with self.assertRaisesRegex(DecisionEvaluationError, "decision logging failed") as context:
            engine.evaluate(observation(), NOW)
        self.assertIsInstance(context.exception.__cause__, OSError)


class MacdGateTests(unittest.TestCase):
    """The mandatory H1 MACD sign filter: BUY requires MACD line < 0, SELL
    requires MACD line > 0. A pure AND-gate -- it can only turn an otherwise
    valid BUY/SELL into WAIT, never grant a verdict the other three gates
    didn't already earn, and it contributes zero score."""

    def setUp(self) -> None:
        self.logger = RecordingLogger()
        self.engine = DecisionEngine(DecisionPolicy(), self.logger)

    def _sell_observation(self, *, macd: float | None) -> MarketObservation:
        return observation(
            bias=StructureBias.BEARISH,
            price=60,
            liquidity_side=LiquiditySide.BUY_SIDE,
            macd=macd,
        )

    # 1-6: direction x sign, including the exact-zero boundary.
    def test_buy_discount_macd_below_zero_yields_buy(self) -> None:
        decision = self.engine.evaluate(observation(macd=-1.0), NOW)
        self.assertEqual(decision.verdict, DecisionVerdict.BUY)

    def test_buy_discount_macd_above_zero_yields_wait(self) -> None:
        decision = self.engine.evaluate(observation(macd=1.0), NOW)
        self.assertEqual(decision.verdict, DecisionVerdict.WAIT)
        self.assertTrue(any("BUY requires MACD below zero" in item for item in decision.conflicts))

    def test_buy_macd_exactly_zero_yields_wait(self) -> None:
        decision = self.engine.evaluate(observation(macd=0.0), NOW)
        self.assertEqual(decision.verdict, DecisionVerdict.WAIT)

    def test_sell_premium_macd_above_zero_yields_sell(self) -> None:
        decision = self.engine.evaluate(self._sell_observation(macd=1.0), NOW)
        self.assertEqual(decision.verdict, DecisionVerdict.SELL)

    def test_sell_premium_macd_below_zero_yields_wait(self) -> None:
        decision = self.engine.evaluate(self._sell_observation(macd=-1.0), NOW)
        self.assertEqual(decision.verdict, DecisionVerdict.WAIT)
        self.assertTrue(any("SELL requires MACD above zero" in item for item in decision.conflicts))

    def test_sell_macd_exactly_zero_yields_wait(self) -> None:
        decision = self.engine.evaluate(self._sell_observation(macd=0.0), NOW)
        self.assertEqual(decision.verdict, DecisionVerdict.WAIT)

    # 7: missing MACD data.
    def test_macd_none_fails_closed(self) -> None:
        decision = self.engine.evaluate(observation(macd=None), NOW)
        self.assertEqual(decision.verdict, DecisionVerdict.WAIT)
        self.assertEqual(decision.score, 0.0)
        self.assertEqual(decision.confidence, Confidence.NONE)
        self.assertTrue(any("MACD" in item for item in decision.missing_evidence))

    # 8-10: MACD alone must never rescue a failed existing gate.
    def test_macd_aligned_but_structure_break_missing_still_waits(self) -> None:
        decision = self.engine.evaluate(observation(break_of_structure=False, macd=-1.0), NOW)
        self.assertEqual(decision.verdict, DecisionVerdict.WAIT)

    def test_macd_aligned_but_wrong_location_still_waits(self) -> None:
        decision = self.engine.evaluate(observation(price=60, macd=-1.0), NOW)
        self.assertEqual(decision.verdict, DecisionVerdict.WAIT)

    def test_macd_aligned_but_liquidity_undisplaced_still_waits(self) -> None:
        decision = self.engine.evaluate(observation(displacement=False, macd=-1.0), NOW)
        self.assertEqual(decision.verdict, DecisionVerdict.WAIT)

    # 11-12: score/reasons/conflicts are untouched by a passing MACD gate.
    def test_score_is_unchanged_when_macd_passes(self) -> None:
        weak = self.engine.evaluate(observation(macd=-0.0001), NOW)
        strong = self.engine.evaluate(observation(macd=-50.0), NOW)
        self.assertEqual(weak.score, 1.0)
        self.assertEqual(weak.score, strong.score)

    def test_reasons_and_conflicts_are_unchanged_when_macd_passes(self) -> None:
        decision = self.engine.evaluate(observation(macd=-1.0), NOW)
        self.assertEqual(len(decision.reasons), 3)
        self.assertFalse(decision.conflicts)

    # Boundary conditions (mission section 5) -- no tolerance around zero.
    def test_boundary_buy_macd_just_below_zero_passes(self) -> None:
        decision = self.engine.evaluate(observation(macd=-0.0001), NOW)
        self.assertEqual(decision.verdict, DecisionVerdict.BUY)

    def test_boundary_buy_macd_zero_fails(self) -> None:
        decision = self.engine.evaluate(observation(macd=0.0), NOW)
        self.assertEqual(decision.verdict, DecisionVerdict.WAIT)

    def test_boundary_buy_macd_just_above_zero_fails(self) -> None:
        decision = self.engine.evaluate(observation(macd=0.0001), NOW)
        self.assertEqual(decision.verdict, DecisionVerdict.WAIT)

    def test_boundary_sell_macd_just_above_zero_passes(self) -> None:
        decision = self.engine.evaluate(self._sell_observation(macd=0.0001), NOW)
        self.assertEqual(decision.verdict, DecisionVerdict.SELL)

    def test_boundary_sell_macd_zero_fails(self) -> None:
        decision = self.engine.evaluate(self._sell_observation(macd=0.0), NOW)
        self.assertEqual(decision.verdict, DecisionVerdict.WAIT)

    def test_boundary_sell_macd_just_below_zero_fails(self) -> None:
        decision = self.engine.evaluate(self._sell_observation(macd=-0.0001), NOW)
        self.assertEqual(decision.verdict, DecisionVerdict.WAIT)


class MacdGateRegressionTests(unittest.TestCase):
    """Critical regression requirement: every pre-existing WAIT fixture must
    remain WAIT once every fixture carries an aligned (non-None) MACD value
    -- an AND-only gate must never convert an existing WAIT into BUY/SELL."""

    def setUp(self) -> None:
        self.engine = DecisionEngine(DecisionPolicy(), RecordingLogger())

    def test_every_pre_existing_wait_fixture_remains_wait_with_aligned_macd(self) -> None:
        wait_fixtures = {
            "wrong_range_location": observation(price=60),
            "liquidity_without_displacement": observation(displacement=False),
            "missing_structure": observation(structure=False),
            "stale_evidence": observation(observed_at=NOW - timedelta(hours=5)),
            "future_evidence": observation(observed_at=NOW + timedelta(seconds=1)),
            "unsupported_symbol": observation(symbol="EURUSD"),
            "neutral_structure": observation(bias=StructureBias.NEUTRAL),
            "no_structure_break": observation(break_of_structure=False),
        }
        for name, fixture in wait_fixtures.items():
            with self.subTest(fixture=name):
                decision = self.engine.evaluate(fixture, NOW)
                self.assertEqual(decision.verdict, DecisionVerdict.WAIT)

    def test_existing_buy_fixture_unchanged_with_aligned_macd(self) -> None:
        decision = self.engine.evaluate(observation(macd=-1.0), NOW)
        self.assertEqual(decision.verdict, DecisionVerdict.BUY)
        self.assertEqual(decision.score, 1.0)
        self.assertEqual(decision.confidence, Confidence.HIGH)
        self.assertEqual(len(decision.reasons), 3)
        self.assertFalse(decision.conflicts)

    def test_existing_sell_fixture_unchanged_with_aligned_macd(self) -> None:
        decision = self.engine.evaluate(
            observation(
                bias=StructureBias.BEARISH,
                price=60,
                liquidity_side=LiquiditySide.BUY_SIDE,
                macd=1.0,
            ),
            NOW,
        )
        self.assertEqual(decision.verdict, DecisionVerdict.SELL)
        self.assertEqual(decision.score, 1.0)


class CompatibilityRegressionTests(unittest.TestCase):
    def test_compatibility_adapter_constructor_and_now_keyword_remain_supported(self) -> None:
        from gold_brain.engine import DecisionEngine as CompatibilityDecisionAdapter

        decision = CompatibilityDecisionAdapter().evaluate(observation(), now=NOW)
        self.assertEqual(decision.verdict, DecisionVerdict.BUY)


if __name__ == "__main__":
    unittest.main()
