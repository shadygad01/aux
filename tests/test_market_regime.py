import unittest
from datetime import UTC, datetime, timedelta

from capabilities.evidence import EvidenceCapability
from packages.application import MarketRegimeIdentification
from packages.domain import (
    AttentionBias,
    CurrentMarketState,
    Evidence,
    EvidenceDecision,
    EvidenceDirection,
    EvidenceKind,
    HorizonBias,
    MarketRegime,
    MarketRegimeContext,
    Recommendation,
    RegimeInterpretation,
    TradingHorizon,
)
from packages.infrastructure import InMemoryCapabilityTelemetry

NOW = datetime(2026, 8, 5, 12, tzinfo=UTC)


def evidence() -> Evidence:
    return Evidence(
        "sweep-1",
        EvidenceKind.LIQUIDITY_SWEEP,
        EvidenceDirection.BUY,
        NOW,
        timedelta(minutes=5),
        0.8,
        0.8,
        0.8,
        0.6,
        0.7,
        "Sell-side liquidity swept.",
        "market-feed:1",
    )


def regime() -> MarketRegimeContext:
    return MarketRegimeIdentification("regime-v1").identify(
        MarketRegime.RANGING,
        (MarketRegime.RANGING, MarketRegime.LOW_VOLATILITY, MarketRegime.LIQUIDITY_DRIVEN),
        NOW,
        timedelta(minutes=5),
        82,
        "Boundaries persist and liquidity events dominate movement.",
        ("range-study:1", "volatility:1"),
        "regime-classifier:reviewed",
    )


def state() -> CurrentMarketState:
    return CurrentMarketState(
        "state-1",
        "XAUUSD",
        NOW,
        timedelta(minutes=5),
        regime(),
        "Macro neutral.",
        (HorizonBias(TradingHorizon.SCALPING, AttentionBias.WAIT, "Range context."),),
        "Low volatility.",
        "Range liquidity active.",
        "Momentum compressed.",
        "No active news catalyst.",
        75,
        25,
        ("state-evidence:1",),
        "review",
        "state-policy",
    )


class CapturingEvaluator:
    def __init__(self) -> None:
        self.interpretations: tuple[RegimeInterpretation, ...] = ()

    def evaluate(
        self,
        items: tuple[Evidence, ...],
        evaluated_at: datetime,
        current_state: CurrentMarketState,
        interpretations: tuple[RegimeInterpretation, ...],
    ) -> EvidenceDecision:
        self.interpretations = interpretations
        return EvidenceDecision(
            Recommendation.WAIT,
            50,
            60,
            ("Range interpretation reviewed.",),
            ("Expansion is unconfirmed.",),
            ("Execution confirmation",),
            ("Expansion would change the interpretation.",),
            (),
            evaluated_at,
            "policy",
            "3.0.0",
        )


class MarketRegimeTests(unittest.TestCase):
    def test_every_evidence_is_interpreted_inside_current_regime(self) -> None:
        evaluator = CapturingEvaluator()
        capability = EvidenceCapability(evaluator, InMemoryCapabilityTelemetry())
        interpretation = RegimeInterpretation(
            "sweep-1", regime().regime_id, "Range sweep may revert at the opposite boundary.", 0.7
        )
        result = capability.evaluate((evidence(),), state(), (interpretation,), NOW)
        self.assertEqual(result.recommendation, Recommendation.WAIT)
        self.assertEqual(evaluator.interpretations, (interpretation,))

    def test_analysis_rejects_missing_wrong_or_expired_regime_context(self) -> None:
        capability = EvidenceCapability(CapturingEvaluator(), InMemoryCapabilityTelemetry())
        with self.assertRaisesRegex(ValueError, "exactly one"):
            capability.evaluate((evidence(),), state(), (), NOW)
        wrong = RegimeInterpretation("sweep-1", "other-regime", "Different context.", 0.5)
        with self.assertRaisesRegex(ValueError, "current regime"):
            capability.evaluate((evidence(),), state(), (wrong,), NOW)
        valid = RegimeInterpretation("sweep-1", regime().regime_id, "Range context.", 0.5)
        with self.assertRaisesRegex(ValueError, "current market state"):
            capability.evaluate((evidence(),), state(), (valid,), NOW + timedelta(minutes=5))

    def test_primary_regime_must_be_active_and_evidence_backed(self) -> None:
        with self.assertRaisesRegex(ValueError, "included"):
            MarketRegimeIdentification("policy").identify(
                MarketRegime.TRENDING,
                (MarketRegime.RANGING,),
                NOW,
                timedelta(minutes=5),
                50,
                "Conflicting classification.",
                ("evidence:1",),
                "review",
            )


if __name__ == "__main__":
    unittest.main()
