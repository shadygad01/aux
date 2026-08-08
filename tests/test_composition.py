"""Tests for the publish-pipeline composition root (publish/composition.py).

Covers valid construction of every factory, that the DecisionEngine factory
actually wires the given policy/logger through to evaluation output (identity
through behavior, since the engine keeps both as private attributes), that
stateful engines are independent per call, and that the real generators no
longer construct these dependencies inline.
"""

import json
import logging
import tempfile
import unittest
from datetime import UTC, datetime, timedelta
from pathlib import Path

from packages.application import DecisionEngine
from packages.application.execution_readiness_engine import ExecutionReadinessEngine
from packages.application.multi_timeframe_engine import MultiTimeframeEngine
from packages.application.opportunity_identity_engine import OpportunityIdentityEngine
from packages.domain import (
    DealingRange,
    DecisionPolicy,
    DecisionVerdict,
    LiquidityEvent,
    LiquiditySide,
    MarketObservation,
    MarketStructure,
    StructureBias,
)
from packages.infrastructure.live_collector import LiveMarketCollector
from packages.infrastructure.macro_collectors import MacroCollector
from publish.composition import (
    MACRO_COLLECTOR_TIMEOUT_SECONDS,
    PUBLISH_LOGGER_NAME,
    build_decision_engine,
    build_decision_policy,
    build_execution_readiness_engine,
    build_live_market_collector,
    build_macro_collector,
    build_multi_timeframe_engine,
    build_opportunity_identity_engine,
    configure_publish_logger,
)


def _empty_observation() -> MarketObservation:
    return MarketObservation(
        symbol="XAUUSD",
        timeframe="H1",
        observed_at=datetime.now(UTC),
        structure=None,
        dealing_range=None,
        liquidity=(),
        source="test-fixture",
    )


def _full_alignment_observation() -> MarketObservation:
    return MarketObservation(
        symbol="XAUUSD",
        timeframe="H1",
        observed_at=datetime.now(UTC) - timedelta(minutes=10),
        structure=MarketStructure(StructureBias.BULLISH, break_of_structure=True),
        dealing_range=DealingRange(0, 100, 40),
        liquidity=(LiquidityEvent(LiquiditySide.SELL_SIDE, True, True),),
        source="test-fixture",
        macd_value=-1.0,
    )


class CompositionRootConstructionTests(unittest.TestCase):
    def test_configure_publish_logger_returns_the_named_logger(self) -> None:
        logger = configure_publish_logger()
        self.assertIsInstance(logger, logging.Logger)
        self.assertEqual(logger.name, PUBLISH_LOGGER_NAME)

    def test_build_decision_policy_returns_a_decision_policy(self) -> None:
        self.assertIsInstance(build_decision_policy(), DecisionPolicy)

    def test_build_decision_engine_returns_a_decision_engine(self) -> None:
        engine = build_decision_engine(build_decision_policy(), configure_publish_logger())
        self.assertIsInstance(engine, DecisionEngine)

    def test_build_live_market_collector_returns_a_live_market_collector(self) -> None:
        self.assertIsInstance(build_live_market_collector(), LiveMarketCollector)

    def test_build_macro_collector_uses_the_established_timeout(self) -> None:
        collector = build_macro_collector()
        self.assertIsInstance(collector, MacroCollector)
        self.assertEqual(collector.timeout_seconds, MACRO_COLLECTOR_TIMEOUT_SECONDS)

    def test_build_execution_readiness_engine_returns_the_engine_type(self) -> None:
        self.assertIsInstance(build_execution_readiness_engine(), ExecutionReadinessEngine)

    def test_build_multi_timeframe_engine_returns_the_engine_type(self) -> None:
        self.assertIsInstance(build_multi_timeframe_engine(), MultiTimeframeEngine)

    def test_build_opportunity_identity_engine_returns_the_engine_type(self) -> None:
        self.assertIsInstance(build_opportunity_identity_engine(), OpportunityIdentityEngine)


class _CapturingHandler(logging.Handler):
    def __init__(self) -> None:
        super().__init__()
        self.records: list[logging.LogRecord] = []

    def emit(self, record: logging.LogRecord) -> None:
        self.records.append(record)


class CompositionRootAuditLoggingTests(unittest.TestCase):
    """Regression coverage for the fix to docs/adr/0007-engine-consolidation.md
    AQ-3: JsonDecisionLogger.record() calls logger.info(...), and
    configure_publish_logger() previously left the root logger (and therefore
    "gold_brain.publish", which inherits from it) at WARNING -- silently
    discarding every audit record in production. The fix raises only the
    named publish logger to INFO; the root stays at WARNING so unrelated
    library logging is unaffected. These tests exercise the real
    configure_publish_logger()/build_decision_engine() factories, not a
    hand-rolled substitute, and the real DecisionEngine.evaluate() call --
    the actual production integration point, not an isolated re-simulation.
    """

    def setUp(self) -> None:
        self.logger = configure_publish_logger()
        self.handler = _CapturingHandler()
        self.logger.addHandler(self.handler)
        self.addCleanup(self.logger.removeHandler, self.handler)

    def test_the_production_logger_is_enabled_for_info(self) -> None:
        self.assertTrue(self.logger.isEnabledFor(logging.INFO))

    def test_configure_publish_logger_touches_only_its_own_logger(self) -> None:
        """The fix must not broaden logging scope beyond the one named
        logger. Asserting the *process-global root's* effective level here
        would be flaky -- other test modules legitimately call
        ``logging.basicConfig(..., force=True)`` at INFO (both CLIs do, by
        design) in the same shared test process, and execution order across
        files is not guaranteed. What is attributable to this fix alone,
        regardless of what else runs in the process, is that
        ``configure_publish_logger()`` sets its own logger's *own* level
        explicitly and does not touch any other logger's own level."""
        self.assertEqual(self.logger.level, logging.INFO)
        untouched = logging.getLogger("some.unrelated.library.never.configured")
        self.assertEqual(untouched.level, logging.NOTSET)

    def test_decision_engine_evaluation_produces_an_observable_audit_record(self) -> None:
        engine = build_decision_engine(build_decision_policy(), self.logger)
        decision = engine.evaluate(_full_alignment_observation(), datetime.now(UTC))

        self.assertEqual(len(self.handler.records), 1)
        event = json.loads(self.handler.records[0].getMessage())
        self.assertEqual(event["event"], "decision_evaluated")
        self.assertEqual(event["symbol"], "XAUUSD")
        self.assertEqual(event["timeframe"], "H1")
        self.assertEqual(event["decision"]["verdict"], decision.verdict.value)
        # Existing decision output is unchanged by this fix -- same formula,
        # same result as the pre-fix engine would have computed.
        self.assertEqual(decision.verdict, DecisionVerdict.BUY)
        self.assertEqual(decision.score, 1.0)

    def test_missing_evidence_decision_still_produces_a_safe_audit_record(self) -> None:
        """Missing/empty audit information (a WAIT decision with no
        reasons, only missing_evidence) must not be discarded or raise."""
        engine = build_decision_engine(build_decision_policy(), self.logger)
        decision = engine.evaluate(_empty_observation(), datetime.now(UTC))

        self.assertEqual(len(self.handler.records), 1)
        event = json.loads(self.handler.records[0].getMessage())
        self.assertEqual(event["decision"]["verdict"], "WAIT")
        self.assertEqual(event["decision"]["missing_evidence"], list(decision.missing_evidence))
        self.assertEqual(decision.score, 0.0)


class ProductionPathAuditLoggingTests(unittest.TestCase):
    """Exercises the actual production path -- generate_artifacts.py's real
    generator function, not an isolated DecisionEngine call -- proving the
    audit-log fix holds through the full
    entry-point -> composition root -> DecisionEngine -> artifact chain."""

    def test_the_decision_generator_emits_an_audit_record_and_a_correct_artifact(self) -> None:
        from publish.generators import decision as decision_generator

        logger = logging.getLogger(PUBLISH_LOGGER_NAME)
        handler = _CapturingHandler()
        logger.addHandler(handler)
        self.addCleanup(logger.removeHandler, handler)

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "decision.json"
            decision_generator.generate(output_path)

            # The artifact itself was already correct before this fix
            # (decision_to_json serializes the Decision object directly,
            # independent of the logger) -- confirmed unchanged here.
            self.assertTrue(output_path.exists())
            artifact = json.loads(output_path.read_text(encoding="utf-8"))
            self.assertIn("verdict", artifact["payload"]["decision"])

        # What was actually broken: the structured per-decision audit line.
        self.assertGreaterEqual(len(handler.records), 1)
        event = json.loads(handler.records[-1].getMessage())
        self.assertEqual(event["event"], "decision_evaluated")


class CompositionRootWiringIdentityTests(unittest.TestCase):
    """Prove the composition root wires the *given* dependency, not a hidden default."""

    def test_decision_engine_evaluates_against_the_supplied_policy_not_a_default(self) -> None:
        distinctive_policy = DecisionPolicy(version="composition-root-identity-check-v1")
        engine = build_decision_engine(distinctive_policy, configure_publish_logger())

        decision = engine.evaluate(_empty_observation(), datetime.now(UTC))

        self.assertEqual(decision.policy_version, "composition-root-identity-check-v1")

    def test_decision_engine_records_through_the_supplied_logger(self) -> None:
        captured: list[str] = []

        class _CapturingHandler(logging.Handler):
            def emit(self, record: logging.LogRecord) -> None:
                captured.append(record.getMessage())

        logger = logging.getLogger("test.composition.capture")
        logger.setLevel(logging.INFO)
        logger.addHandler(_CapturingHandler())

        engine = build_decision_engine(build_decision_policy(), logger)
        engine.evaluate(_empty_observation(), datetime.now(UTC))

        self.assertEqual(len(captured), 1)
        self.assertIn("decision_evaluated", captured[0])


class StatefulEngineIndependenceTests(unittest.TestCase):
    """Stateful engines must be fresh per call -- the composition root is not a singleton cache."""

    def test_each_call_returns_an_independent_opportunity_identity_engine(self) -> None:
        first = build_opportunity_identity_engine()
        second = build_opportunity_identity_engine()

        self.assertIsNot(first, second)
        first.restore_state(None, None, counter=7, last_sweep_signature="sig")
        self.assertIsNone(second.current_opportunity)


class GeneratorsUseCompositionRootTests(unittest.TestCase):
    """The real generators must source shared dependencies from the composition
    root instead of constructing them inline -- this is the duplication this
    mission exists to eliminate (docs/PHASE_0_MIGRATION_READINESS.md Migration
    Order step 1)."""

    def test_no_generator_constructs_decision_engine_inline(self) -> None:
        import ast
        from pathlib import Path

        generators_dir = Path(__file__).resolve().parents[1] / "publish" / "generators"
        offenders: list[str] = []
        inline_construction_names = {
            "DecisionEngine",
            "DecisionPolicy",
            "LiveMarketCollector",
            "MacroCollector",
            "ExecutionReadinessEngine",
            "MultiTimeframeEngine",
            "OpportunityIdentityEngine",
        }
        for path in generators_dir.glob("*.py"):
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            for node in ast.walk(tree):
                if (
                    isinstance(node, ast.Call)
                    and isinstance(node.func, ast.Name)
                    and node.func.id in inline_construction_names
                ):
                    offenders.append(f"{path.name}:{node.lineno} constructs {node.func.id}()")
        self.assertEqual(offenders, [])


if __name__ == "__main__":
    unittest.main()
