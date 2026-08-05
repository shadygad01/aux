"""Tests for Context domain model, capability, contracts, and publishing."""

from __future__ import annotations

import json
import tempfile
import unittest
from datetime import UTC, datetime, timedelta
from pathlib import Path

from capabilities.context import ContextCapability, ContextProvider
from capabilities.contracts import HealthState
from packages.domain import (
    EnvironmentFlags,
    LiquidityConditions,
    MacroRegime,
    MarketContext,
    MarketState,
    NewsWindow,
    RangeLocation,
    ReasoningInput,
    TradingSession,
    VolatilityRegime,
)
from publish.generators import context as context_generator


class MockTelemetry:
    def __init__(self) -> None:
        self.metrics: list[object] = []
        self.logs: list[object] = []

    def metric(self, value: object) -> None:
        self.metrics.append(value)

    def log(self, value: object) -> None:
        self.logs.append(value)


class MockContextProvider:
    def __init__(self, context: MarketContext) -> None:
        self.context = context

    def acquire_context(self, symbol: str, at: datetime) -> MarketContext:
        return self.context


class ContextDomainTests(unittest.TestCase):
    def setUp(self) -> None:
        self.now = datetime(2026, 8, 5, 12, 0, 0, tzinfo=UTC)
        flags = EnvironmentFlags(
            is_holiday=False,
            is_weekend=False,
            is_market_open=True,
            is_market_close=False,
        )
        self.context = MarketContext(
            context_id="CTX-001",
            symbol="XAUUSD",
            session=TradingSession.LONDON,
            news_window=NewsWindow.CLEAR,
            macro_regime=MacroRegime.NEUTRAL,
            volatility_regime=VolatilityRegime.LOW_VOLATILITY,
            liquidity_conditions=LiquidityConditions.NORMAL,
            flags=flags,
            observed_at=self.now,
            ttl_seconds=3600,
            source="canonical-context-provider",
        )

    def test_market_context_is_not_evidence_or_knowledge(self) -> None:
        self.assertEqual(self.context.session, TradingSession.LONDON)
        self.assertEqual(self.context.news_window, NewsWindow.CLEAR)
        self.assertEqual(self.context.macro_regime, MacroRegime.NEUTRAL)
        self.assertTrue(self.context.flags.is_market_open)

    def test_market_context_lifecycle_and_validity(self) -> None:
        self.assertTrue(self.context.is_valid(self.now + timedelta(minutes=30)))
        self.assertFalse(self.context.is_valid(self.now + timedelta(hours=2)))
        self.assertFalse(self.context.is_valid(self.now - timedelta(minutes=1)))

    def test_timezone_aware_validation_required(self) -> None:
        with self.assertRaises(ValueError):
            MarketContext(
                context_id="CTX-002",
                symbol="XAUUSD",
                session=TradingSession.LONDON,
                news_window=NewsWindow.CLEAR,
                macro_regime=MacroRegime.NEUTRAL,
                volatility_regime=VolatilityRegime.LOW_VOLATILITY,
                liquidity_conditions=LiquidityConditions.NORMAL,
                flags=EnvironmentFlags(),
                observed_at=datetime(2026, 8, 5, 12, 0, 0),  # Naive
            )

    def test_serialization_roundtrip(self) -> None:
        raw = self.context.to_dict()
        restored = MarketContext.from_dict(raw)
        self.assertEqual(self.context.context_id, restored.context_id)
        self.assertEqual(self.context.session, restored.session)
        self.assertEqual(self.context.observed_at, restored.observed_at)

    def test_reasoning_input_consumes_valid_context(self) -> None:
        state = MarketState(
            state_id="STATE-001",
            symbol="XAUUSD",
            captured_at=self.now,
            time_to_live=timedelta(hours=1),
            price=3340.0,
            location=RangeLocation.DISCOUNT,
            session="LONDON",
            volatility_regime="LOW_VOLATILITY",
            summary="London discount state",
            alternative_explanations=("None",),
            source="manual",
        )
        reasoning_input = ReasoningInput(
            reasoning_id="REASONING-001",
            market_state=state,
            evidence=(),
            knowledge=(),
            historical_context=(),
            research=(),
            learning_suggestions=(),
            context=self.context,
        )
        self.assertIsNotNone(reasoning_input.context)
        if reasoning_input.context:
            self.assertEqual(reasoning_input.context.context_id, "CTX-001")


class ContextCapabilityTests(unittest.TestCase):
    def test_capability_telemetry_and_health(self) -> None:
        now = datetime(2026, 8, 5, 12, 0, 0, tzinfo=UTC)
        context = MarketContext(
            context_id="CTX-001",
            symbol="XAUUSD",
            session=TradingSession.LONDON,
            news_window=NewsWindow.CLEAR,
            macro_regime=MacroRegime.NEUTRAL,
            volatility_regime=VolatilityRegime.LOW_VOLATILITY,
            liquidity_conditions=LiquidityConditions.NORMAL,
            flags=EnvironmentFlags(),
            observed_at=now,
            ttl_seconds=3600,
        )
        provider = MockContextProvider(context)
        telemetry = MockTelemetry()
        capability = ContextCapability(provider, telemetry)

        acquired = capability.get_context("XAUUSD", now)
        self.assertEqual(acquired.context_id, "CTX-001")
        self.assertEqual(len(telemetry.metrics), 1)
        self.assertEqual(len(telemetry.logs), 1)

        health = capability.health(now)
        self.assertEqual(health.state, HealthState.HEALTHY)
        self.assertEqual(health.capability, "context")


class ContextPublishingTests(unittest.TestCase):
    def test_generate_context_artifact(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            out_file = Path(tmpdir) / "context.json"
            context_generator.generate(out_file)
            self.assertTrue(out_file.exists())

            data = json.loads(out_file.read_text(encoding="utf-8"))
            self.assertEqual(data["generator"], "publish.generators.context")
            self.assertIn("context", data["payload"])
            self.assertEqual(data["payload"]["context"]["symbol"], "XAUUSD")
