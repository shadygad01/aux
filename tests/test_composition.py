"""Tests for the publish-pipeline composition root (publish/composition.py).

Covers valid construction of every factory, that the DecisionEngine factory
actually wires the given policy/logger through to evaluation output (identity
through behavior, since the engine keeps both as private attributes), that
stateful engines are independent per call, and that the real generators no
longer construct these dependencies inline.
"""

import logging
import unittest
from datetime import UTC, datetime

from packages.application import DecisionEngine
from packages.application.execution_readiness_engine import ExecutionReadinessEngine
from packages.application.multi_timeframe_engine import MultiTimeframeEngine
from packages.application.opportunity_identity_engine import OpportunityIdentityEngine
from packages.domain import DecisionPolicy, MarketObservation
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
