"""Characterization and parity-boundary tests supporting ADR-0007 (engine consolidation).

These tests do not change, replace, or migrate any engine. They exist to pin
down, with an executable assertion instead of only prose, the exact facts
docs/adr/0007-engine-consolidation.md's formula comparison (§8) and audit
finding (§6) depend on -- so if any of these facts silently drift, the
regression is caught here rather than leaving the ADR's evidence stale.

Three groups:

1. PolicyFormulaCharacterizationTests -- pins the exact weight/point constants
   compared across DecisionPolicy, TradingPolicy, and EvidencePolicy in the
   ADR's formula table.
2. BoundaryAgreementCharacterizationTests -- confirms, on each engine's own
   independently-defined "full alignment" fixture (not a cross-mapped
   scenario -- see ADR-0007 §8's explicit refusal to invent one), that all
   three trade-quality formulas agree exactly at the upper extreme (100) and
   the lower extreme (0 / a fail-closed state). This is the only form of
   cross-engine "parity" this document can support without inventing a
   MarketObservation<->TradingObservation<->Evidence mapping, which is a
   trading-policy decision reserved for AQ-6/TQ-1 in the review package.
3. DecisionEngineAuditObservabilityTests -- characterizes ADR-0007 AQ-3's
   finding precisely: JsonDecisionLogger.record() calls logger.info(), and
   publish/composition.py's production logger is configured at WARNING, so
   the structured per-decision audit line is silently discarded in every
   scheduled run today. This locks the mechanism down with an assertion so a
   future change to either side is caught deliberately.
"""

import logging
import unittest
from datetime import UTC, datetime, timedelta

from packages.application import DecisionEngine, EvidenceDecisionEngine, TradingOpportunityEngine
from packages.domain import (
    AttentionBias,
    DealingRange,
    DecisionPolicy,
    Evidence,
    EvidenceDirection,
    EvidenceKind,
    EvidencePolicy,
    HorizonBias,
    LiquidityEvent,
    LiquiditySide,
    MarketObservation,
    MarketStructure,
    MomentumAssessment,
    Recommendation,
    SmcAssessment,
    StructureBias,
    TradingHorizon,
    TradingMacroAssessment,
    TradingObservation,
    TradingPolicy,
)
from packages.infrastructure import JsonDecisionLogger

NOW = datetime(2026, 8, 5, 12, tzinfo=UTC)


class PolicyFormulaCharacterizationTests(unittest.TestCase):
    """Pins the exact constants ADR-0007 §8's formula table compares."""

    def test_decision_policy_weights_are_the_three_gate_weights_the_adr_compares(self) -> None:
        policy = DecisionPolicy()
        self.assertEqual(policy.structure_weight, 0.40)
        self.assertEqual(policy.location_weight, 0.30)
        self.assertEqual(policy.liquidity_weight, 0.30)
        self.assertEqual(policy.attention_threshold, 0.75)

    def test_trading_policy_points_are_the_nine_components_the_adr_compares(self) -> None:
        policy = TradingPolicy()
        self.assertEqual(policy.macro_points, 15)
        self.assertEqual(policy.execution_bias_points, 15)
        self.assertEqual(policy.cross_horizon_alignment_points, 5)
        self.assertEqual(policy.location_points, 15)
        self.assertEqual(policy.liquidity_sweep_points, 10)
        self.assertEqual(policy.nearby_liquidity_points, 5)
        self.assertEqual(policy.macd_points, 10)
        self.assertEqual(policy.reversal_candle_points, 15)
        self.assertEqual(policy.optional_smc_points, 10)
        self.assertEqual(policy.minimum_trade_quality, 75)

    def test_evidence_policy_thresholds_are_the_ones_the_adr_compares(self) -> None:
        policy = EvidencePolicy()
        self.assertEqual(policy.minimum_reliable_weight, 0.05)
        self.assertEqual(policy.minimum_directional_weight, 0.25)
        self.assertEqual(policy.minimum_directional_confidence, 60)
        self.assertEqual(policy.minimum_trade_quality, 75)
        self.assertEqual(len(policy.required_execution_kinds), 6)

    def test_all_three_minimum_trade_quality_thresholds_currently_agree_at_75(self) -> None:
        """Supporting evidence for review question TQ-5: is this agreement
        intentional or coincidental? This test only pins that it holds today."""
        self.assertEqual(DecisionPolicy().attention_threshold, 0.75)
        self.assertEqual(TradingPolicy().minimum_trade_quality, 75)
        self.assertEqual(EvidencePolicy().minimum_trade_quality, 75)


class _RecordingLogger:
    def __init__(self) -> None:
        self.decisions: list[object] = []

    def record(self, observation: object, decision: object) -> None:
        self.decisions.append(decision)

    def append(self, observation: object, decision: object) -> None:
        self.decisions.append(decision)


def _full_alignment_market_observation() -> MarketObservation:
    return MarketObservation(
        symbol="XAUUSD",
        timeframe="H1",
        observed_at=NOW - timedelta(minutes=10),
        structure=MarketStructure(StructureBias.BULLISH, break_of_structure=True),
        dealing_range=DealingRange(0, 100, 40),
        liquidity=(LiquidityEvent(LiquiditySide.SELL_SIDE, True, True),),
        source="characterization-fixture",
        macd_value=-1.0,
    )


def _full_alignment_trading_observation() -> TradingObservation:
    horizon_biases = tuple(
        HorizonBias(horizon, AttentionBias.BUY_ONLY, "reviewed structure")
        for horizon in TradingHorizon
    )
    return TradingObservation(
        opportunity_id="characterization-opp-001",
        symbol="XAUUSD",
        execution_horizon=TradingHorizon.MEDIUM_TERM,
        observed_at=NOW - timedelta(minutes=5),
        source="characterization-fixture",
        macro=TradingMacroAssessment(AttentionBias.BUY_ONLY, "macro aligns", ("rates",), (), 0.8),
        horizon_biases=horizon_biases,
        dealing_range=DealingRange(0, 100, 40),
        nearby_liquidity_levels=("PDL",),
        momentum=MomentumAssessment(-1),
        smc=SmcAssessment(
            LiquidityEvent(LiquiditySide.SELL_SIDE, True, True),
            True,
            change_of_character=True,
            order_block=True,
            fair_value_gap=True,
        ),
        news=(),
    )


def _full_alignment_evidence() -> tuple[Evidence, ...]:
    def item(kind: EvidenceKind) -> Evidence:
        return Evidence(
            evidence_id=kind.value.lower(),
            kind=kind,
            direction=EvidenceDirection.BUY,
            observed_at=NOW,
            time_to_live=timedelta(hours=1),
            strength=1.0,
            reliability=1.0,
            importance=1.0,
            historical_performance=1.0,
            confidence=1.0,
            rationale=f"reviewed {kind.value} evidence",
            source="characterization-fixture",
            forces_wait=False,
        )

    return tuple(item(kind) for kind in EvidencePolicy().required_execution_kinds)


class BoundaryAgreementCharacterizationTests(unittest.TestCase):
    """Cross-engine agreement at the two extremes only -- see module docstring
    for why mid-range comparison is out of scope for this document."""

    def test_all_three_engines_agree_on_100_at_full_evidence_alignment(self) -> None:
        decision_engine = DecisionEngine(DecisionPolicy(), _RecordingLogger())
        decision = decision_engine.evaluate(_full_alignment_market_observation(), NOW)
        self.assertEqual(round(decision.score * 100), 100)

        trading_engine = TradingOpportunityEngine(
            TradingPolicy(), _RecordingLogger(), _RecordingLogger()
        )
        trading_decision = trading_engine.evaluate(_full_alignment_trading_observation(), NOW)
        self.assertEqual(trading_decision.trade_quality, 100)

        evidence_engine = EvidenceDecisionEngine(EvidencePolicy(), _RecordingLogger())
        evidence_decision = evidence_engine.evaluate(_full_alignment_evidence(), NOW)
        self.assertEqual(evidence_decision.trade_quality, 100)

    def test_all_three_engines_fail_closed_when_mandatory_evidence_is_entirely_absent(self) -> None:
        decision_engine = DecisionEngine(DecisionPolicy(), _RecordingLogger())
        empty_observation = MarketObservation(
            symbol="XAUUSD",
            timeframe="H1",
            observed_at=NOW - timedelta(minutes=10),
            structure=None,
            dealing_range=None,
            liquidity=(),
            source="characterization-fixture",
        )
        decision = decision_engine.evaluate(empty_observation, NOW)
        self.assertEqual(decision.score, 0.0)

        evidence_engine = EvidenceDecisionEngine(EvidencePolicy(), _RecordingLogger())
        evidence_decision = evidence_engine.evaluate((), NOW)
        self.assertEqual(evidence_decision.recommendation, Recommendation.NO_OPINION)
        # NO_OPINION, not WAIT -- the fourth state DecisionEngine's DecisionVerdict
        # cannot express at all (ADR-0007 §8, review question TQ-2).


class DecisionEngineAuditObservabilityTests(unittest.TestCase):
    """Characterizes ADR-0007 §6 / AQ-3: DecisionEngine's only audit mechanism
    is silently discarded under the exact logger configuration
    publish/composition.py uses in production."""

    def test_record_is_silently_discarded_at_the_production_configured_level(self) -> None:
        captured: list[str] = []

        class _CapturingHandler(logging.Handler):
            def emit(self, record: logging.LogRecord) -> None:
                captured.append(record.getMessage())

        logger = logging.getLogger("test.characterization.warning-level")
        # WARNING matches publish/composition.py's configure_publish_logger.
        logger.setLevel(logging.WARNING)
        logger.addHandler(_CapturingHandler())

        self.assertFalse(logger.isEnabledFor(logging.INFO))

        json_logger = JsonDecisionLogger(logger)
        engine = DecisionEngine(DecisionPolicy(), json_logger)
        engine.evaluate(_full_alignment_market_observation(), NOW)

        self.assertEqual(captured, [], "expected the INFO-level audit record to be discarded")

    def test_record_is_observable_when_the_logger_permits_info_level(self) -> None:
        captured: list[str] = []

        class _CapturingHandler(logging.Handler):
            def emit(self, record: logging.LogRecord) -> None:
                captured.append(record.getMessage())

        logger = logging.getLogger("test.characterization.info-level")
        logger.setLevel(logging.INFO)
        logger.addHandler(_CapturingHandler())

        self.assertTrue(logger.isEnabledFor(logging.INFO))

        json_logger = JsonDecisionLogger(logger)
        engine = DecisionEngine(DecisionPolicy(), json_logger)
        engine.evaluate(_full_alignment_market_observation(), NOW)

        self.assertEqual(len(captured), 1)
        self.assertIn("decision_evaluated", captured[0])


if __name__ == "__main__":
    unittest.main()
