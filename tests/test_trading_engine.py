import json
import logging
import unittest
from datetime import UTC, datetime, timedelta
from pathlib import Path
from tempfile import TemporaryDirectory

from packages.application import TradingOpportunityEngine
from packages.application.errors import DecisionEvaluationError
from packages.domain import (
    AttentionBias,
    DealingRange,
    ExecutionStatus,
    HorizonBias,
    LiquidityEvent,
    LiquiditySide,
    MacroAssessment,
    MomentumAssessment,
    NewsAssessment,
    NewsEffect,
    OpportunityOutcome,
    OutcomeClassification,
    SmcAssessment,
    TradingDecision,
    TradingHorizon,
    TradingObservation,
    TradingPolicy,
)
from packages.infrastructure import JsonLinesOpportunityRepository, JsonTradingDecisionLogger

NOW = datetime(2026, 8, 5, 12, tzinfo=UTC)


class RecordingAudit:
    def __init__(self) -> None:
        self.decisions: list[TradingDecision] = []

    def record(self, observation: TradingObservation, decision: TradingDecision) -> None:
        self.decisions.append(decision)

    def append(self, observation: TradingObservation, decision: TradingDecision) -> None:
        self.decisions.append(decision)


class FailingRepository:
    def append(self, observation: TradingObservation, decision: TradingDecision) -> None:
        raise OSError("disk full")


def biases(direction: AttentionBias) -> tuple[HorizonBias, ...]:
    return tuple(
        HorizonBias(horizon, direction, "reviewed structure") for horizon in TradingHorizon
    )


def trading_observation(
    *,
    direction: AttentionBias = AttentionBias.BUY_ONLY,
    price: float = 40,
    macd: float = -1,
    macro: MacroAssessment | None = None,
    horizon_biases: tuple[HorizonBias, ...] | None = None,
    smc: SmcAssessment | None = None,
    news: tuple[NewsAssessment, ...] = (),
    levels: tuple[str, ...] = ("PDL",),
) -> TradingObservation:
    is_buy = direction is AttentionBias.BUY_ONLY
    return TradingObservation(
        opportunity_id="opp-001",
        symbol="XAUUSD",
        execution_horizon=TradingHorizon.MEDIUM_TERM,
        observed_at=NOW - timedelta(minutes=5),
        source="reviewed-test-evidence",
        macro=macro or MacroAssessment(direction, "macro aligns", ("rates",), (), 0.8),
        horizon_biases=horizon_biases or biases(direction),
        dealing_range=DealingRange(0, 100, price),
        nearby_liquidity_levels=levels,
        momentum=MomentumAssessment(macd),
        smc=smc
        or SmcAssessment(
            LiquidityEvent(
                LiquiditySide.SELL_SIDE if is_buy else LiquiditySide.BUY_SIDE,
                True,
                True,
            ),
            True,
            change_of_character=True,
            order_block=True,
            fair_value_gap=True,
        ),
        news=news,
    )


class TradingOpportunityEngineTests(unittest.TestCase):
    def setUp(self) -> None:
        self.logger = RecordingAudit()
        self.repository = RecordingAudit()
        self.engine = TradingOpportunityEngine(TradingPolicy(), self.logger, self.repository)

    def test_full_buy_evidence_grants_setup_search_only(self) -> None:
        decision = self.engine.evaluate(trading_observation(), NOW)
        self.assertEqual(decision.execution_status, ExecutionStatus.SEARCH_BUY_SETUPS)
        self.assertEqual(decision.trade_quality, 100)
        self.assertEqual(len(decision.biases), 3)
        self.assertIn("trader-owned entry", decision.next_improvement)
        self.assertEqual(self.logger.decisions, [decision])
        self.assertEqual(self.repository.decisions, [decision])

    def test_full_sell_evidence_grants_sell_search_only(self) -> None:
        decision = self.engine.evaluate(
            trading_observation(
                direction=AttentionBias.SELL_ONLY,
                price=60,
                macd=1,
                levels=("PDH",),
            ),
            NOW,
        )
        self.assertEqual(decision.execution_status, ExecutionStatus.SEARCH_SELL_SETUPS)

    def test_missing_macro_forces_wait(self) -> None:
        value = trading_observation()
        value = TradingObservation(
            value.opportunity_id,
            value.symbol,
            value.execution_horizon,
            value.observed_at,
            value.source,
            None,
            value.horizon_biases,
            value.dealing_range,
            value.nearby_liquidity_levels,
            value.momentum,
            value.smc,
            value.news,
        )
        decision = self.engine.evaluate(value, NOW)
        self.assertEqual(decision.execution_status, ExecutionStatus.WAIT)
        self.assertIn("Macro environment", decision.missing_evidence[0])

    def test_equilibrium_and_wrong_macd_force_wait(self) -> None:
        decision = self.engine.evaluate(trading_observation(price=50, macd=1), NOW)
        self.assertEqual(decision.execution_status, ExecutionStatus.WAIT)
        self.assertTrue(any("EQUILIBRIUM" in item for item in decision.contradicting_factors))
        self.assertTrue(any("MACD" in item for item in decision.contradicting_factors))

    def test_missing_optional_evidence_reduces_quality_without_blocking(self) -> None:
        smc = SmcAssessment(LiquidityEvent(LiquiditySide.SELL_SIDE, True, True), True)
        decision = self.engine.evaluate(trading_observation(smc=smc, levels=()), NOW)
        self.assertEqual(decision.trade_quality, 85)
        self.assertEqual(decision.execution_status, ExecutionStatus.SEARCH_BUY_SETUPS)
        self.assertEqual(len(decision.missing_evidence), 2)

    def test_cross_horizon_disagreement_forces_wait(self) -> None:
        mixed = (
            HorizonBias(TradingHorizon.LONG_TERM, AttentionBias.SELL_ONLY, "bearish"),
            HorizonBias(TradingHorizon.MEDIUM_TERM, AttentionBias.BUY_ONLY, "bullish"),
            HorizonBias(TradingHorizon.SCALPING, AttentionBias.WAIT, "uncertain"),
        )
        decision = self.engine.evaluate(trading_observation(horizon_biases=mixed), NOW)
        self.assertEqual(decision.execution_status, ExecutionStatus.WAIT)
        self.assertIn("disagree", decision.contradicting_factors[0])

    def test_active_news_can_pause_execution(self) -> None:
        news = NewsAssessment(
            NewsEffect.PAUSES_EXECUTION,
            "FOMC release window",
            "abnormal volatility",
            NOW + timedelta(hours=1),
            0.9,
        )
        decision = self.engine.evaluate(trading_observation(news=(news,)), NOW)
        self.assertEqual(decision.execution_status, ExecutionStatus.PAUSED)

    def test_news_can_reduce_quality_without_creating_direction(self) -> None:
        news = NewsAssessment(
            NewsEffect.REDUCES_CONFIDENCE,
            "employment uncertainty",
            "lower conviction",
            NOW + timedelta(hours=1),
            1.0,
        )
        decision = self.engine.evaluate(trading_observation(news=(news,)), NOW)
        self.assertEqual(decision.trade_quality, 90)
        self.assertEqual(decision.execution_status, ExecutionStatus.SEARCH_BUY_SETUPS)

    def test_audit_storage_failure_makes_decision_unavailable(self) -> None:
        engine = TradingOpportunityEngine(TradingPolicy(), self.logger, FailingRepository())
        with self.assertRaisesRegex(DecisionEvaluationError, "audit failed") as context:
            engine.evaluate(trading_observation(), NOW)
        self.assertIsInstance(context.exception.__cause__, OSError)

    def test_naive_evaluation_time_is_rejected(self) -> None:
        with self.assertRaisesRegex(DecisionEvaluationError, "timezone-aware"):
            self.engine.evaluate(trading_observation(), datetime(2026, 8, 5, 12))

    def test_absent_context_categories_and_horizons_force_wait(self) -> None:
        base = trading_observation()
        sparse = TradingObservation(
            base.opportunity_id,
            "EURUSD",
            base.execution_horizon,
            NOW - timedelta(hours=5),
            base.source,
            None,
            (),
            None,
            (),
            None,
            None,
            (),
        )
        decision = self.engine.evaluate(sparse, NOW)
        self.assertEqual(decision.execution_status, ExecutionStatus.WAIT)
        self.assertGreaterEqual(len(decision.missing_evidence), 8)
        self.assertIn("Unsupported symbol", decision.contradicting_factors[0])

    def test_news_rejection_forces_wait_and_expired_news_is_ignored(self) -> None:
        rejected = NewsAssessment(
            NewsEffect.REJECTS_SETUP,
            "unexpected inflation surprise",
            "invalidates macro premise",
            NOW + timedelta(hours=1),
            1.0,
        )
        expired = NewsAssessment(
            NewsEffect.FORCE_WAIT,
            "old event",
            "no longer active",
            NOW - timedelta(seconds=1),
            1.0,
        )
        rejected_decision = self.engine.evaluate(trading_observation(news=(rejected,)), NOW)
        expired_decision = self.engine.evaluate(trading_observation(news=(expired,)), NOW)
        self.assertEqual(rejected_decision.execution_status, ExecutionStatus.WAIT)
        self.assertEqual(expired_decision.execution_status, ExecutionStatus.SEARCH_BUY_SETUPS)

    def test_macro_wait_and_opposing_news_force_wait(self) -> None:
        macro = MacroAssessment(AttentionBias.WAIT, "macro uncertainty", (), (), 0.5)
        news = NewsAssessment(
            NewsEffect.SUPPORTS_SELL,
            "dollar expansion",
            "opposes buy attention",
            NOW + timedelta(hours=1),
            0.8,
        )
        decision = self.engine.evaluate(trading_observation(macro=macro, news=(news,)), NOW)
        self.assertEqual(decision.execution_status, ExecutionStatus.WAIT)
        self.assertGreaterEqual(len(decision.contradicting_factors), 2)


class TradingInfrastructureTests(unittest.TestCase):
    def test_json_lines_repository_durably_appends_evaluation(self) -> None:
        logger = JsonTradingDecisionLogger(logging.getLogger("trading-test"))
        with TemporaryDirectory() as directory:
            path = Path(directory) / "evaluations.jsonl"
            repository = JsonLinesOpportunityRepository(path)
            engine = TradingOpportunityEngine(TradingPolicy(), logger, repository)
            decision = engine.evaluate(trading_observation(), NOW)
            repository.append_outcome(
                OpportunityOutcome(
                    decision.opportunity_id,
                    OutcomeClassification.IGNORED,
                    NOW + timedelta(hours=2),
                    "Trader recorded no execution.",
                )
            )
            records = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
            record = records[0]
        self.assertEqual(record["decision"]["opportunity_id"], decision.opportunity_id)
        self.assertEqual(record["decision"]["trade_quality"], 100)
        self.assertEqual(record["observation"]["execution_horizon"], "MEDIUM_TERM")
        self.assertEqual(record["observation"]["macro"]["bias"], "BUY_ONLY")
        self.assertEqual(record["outcome"], "PENDING")
        self.assertEqual(records[1]["classification"], "IGNORED")


class TradingDomainFailureTests(unittest.TestCase):
    def test_macro_and_news_validate_confidence_and_context(self) -> None:
        with self.assertRaises(ValueError):
            MacroAssessment(AttentionBias.BUY_ONLY, "", (), (), 1.1)
        with self.assertRaises(ValueError):
            NewsAssessment(NewsEffect.FORCE_WAIT, "", "", datetime(2026, 1, 1), -1)

    def test_trading_observation_rejects_duplicate_horizons(self) -> None:
        duplicate = (
            HorizonBias(TradingHorizon.LONG_TERM, AttentionBias.BUY_ONLY, "one"),
            HorizonBias(TradingHorizon.LONG_TERM, AttentionBias.BUY_ONLY, "two"),
        )
        with self.assertRaisesRegex(ValueError, "unique"):
            trading_observation(horizon_biases=duplicate)

    def test_policy_requires_exactly_one_hundred_positive_points(self) -> None:
        with self.assertRaisesRegex(ValueError, "total 100"):
            TradingPolicy(macro_points=16)

    def test_policy_rejects_invalid_thresholds_and_penalties(self) -> None:
        for policy in (
            {"minimum_trade_quality": 101},
            {"equilibrium_band": 0.5},
            {"news_confidence_penalty_points": -1},
        ):
            with self.subTest(policy=policy), self.assertRaises(ValueError):
                TradingPolicy(**policy)

    def test_outcome_requires_traceable_context(self) -> None:
        with self.assertRaises(ValueError):
            OpportunityOutcome("", OutcomeClassification.MISSED, NOW, "")


if __name__ == "__main__":
    unittest.main()
