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
) -> MarketObservation:
    return MarketObservation(
        symbol=symbol,
        timeframe="H1",
        observed_at=observed_at,
        structure=MarketStructure(bias, break_of_structure=break_of_structure)
        if structure
        else None,
        dealing_range=DealingRange(0, 100, price) if dealing_range else None,
        liquidity=(LiquidityEvent(liquidity_side, swept, displacement),) if liquidity else (),
        source="unit-test",
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


class CompatibilityRegressionTests(unittest.TestCase):
    def test_compatibility_adapter_constructor_and_now_keyword_remain_supported(self) -> None:
        from gold_brain.engine import DecisionEngine as CompatibilityDecisionAdapter

        decision = CompatibilityDecisionAdapter().evaluate(observation(), now=NOW)
        self.assertEqual(decision.verdict, DecisionVerdict.BUY)


if __name__ == "__main__":
    unittest.main()
