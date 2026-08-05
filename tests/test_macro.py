"""Tests for Macro Intelligence Foundation (DXY, Yields, News, Reference Levels, Capability)."""

from __future__ import annotations

import json
import tempfile
import unittest
from datetime import UTC, datetime, timedelta
from pathlib import Path

from capabilities.contracts import HealthState
from capabilities.macro import MacroCapability
from packages.domain import (
    DollarStrength,
    LiquidityReferenceEvidence,
    LiquidityReferenceLevel,
    MacroAssessment,
    MacroContext,
    NewsEnvironment,
    NewsImpact,
    NewsWindow,
    YieldEnvironment,
    YieldRegime,
)
from packages.infrastructure.macro_collectors import MacroCollector
from publish.generators import macro_assessment as assessment_generator
from publish.generators import macro_context as context_generator
from publish.generators import macro_evidence as evidence_generator


class MockTelemetry:
    def __init__(self) -> None:
        self.metrics: list[object] = []
        self.logs: list[object] = []

    def metric(self, value: object) -> None:
        self.metrics.append(value)

    def log(self, value: object) -> None:
        self.logs.append(value)


class MockMacroProvider:
    def __init__(self, ctx: MacroContext, assessment: MacroAssessment) -> None:
        self.ctx = ctx
        self.assessment = assessment

    def acquire_macro_context(self, now: datetime) -> MacroContext:
        return self.ctx

    def evaluate_macro_assessment(
        self, ctx: MacroContext, evaluated_at: datetime
    ) -> MacroAssessment:
        return self.assessment


class MacroDomainTests(unittest.TestCase):
    def setUp(self) -> None:
        self.now = datetime(2026, 8, 5, 12, 0, 0, tzinfo=UTC)
        yield_env = YieldEnvironment(
            us10y=4.25,
            us02y=4.50,
            yield_direction="DOWN",
            yield_momentum="MODERATE",
            regime=YieldRegime.NEUTRAL,
        )
        news_env = NewsEnvironment(
            impact=NewsImpact.HIGH_IMPACT,
            window=NewsWindow.CLEAR,
            unresolved_high_impact=False,
            event_name="NFP",
        )
        lr = LiquidityReferenceEvidence(
            level=LiquidityReferenceLevel.PDL, price=3300.0, swept=True, displacement_confirmed=True
        )

        self.ctx = MacroContext(
            context_id="MACRO-001",
            dollar_strength=DollarStrength.BEARISH,
            yield_environment=yield_env,
            news_environment=news_env,
            liquidity_references=(lr,),
            observed_at=self.now,
            ttl_seconds=3600,
        )

    def test_macro_context_serialization_and_validity(self) -> None:
        self.assertTrue(self.ctx.is_valid(self.now + timedelta(minutes=30)))
        self.assertFalse(self.ctx.is_valid(self.now + timedelta(hours=2)))

        raw = self.ctx.to_dict()
        restored = MacroContext.from_dict(raw)
        self.assertEqual(self.ctx.context_id, restored.context_id)
        self.assertEqual(self.ctx.dollar_strength, restored.dollar_strength)

    def test_high_impact_news_forces_wait(self) -> None:
        news_env = NewsEnvironment(
            impact=NewsImpact.HIGH_IMPACT,
            window=NewsWindow.ACTIVE_HIGH_IMPACT,
            unresolved_high_impact=True,
            event_name="FOMC Interest Rate Decision",
        )
        ctx = MacroContext(
            context_id="MACRO-002",
            dollar_strength=DollarStrength.NEUTRAL,
            yield_environment=self.ctx.yield_environment,
            news_environment=news_env,
            liquidity_references=(),
            observed_at=self.now,
        )

        collector = MacroCollector()
        assessment = collector.evaluate_macro_assessment(ctx, self.now)
        self.assertTrue(assessment.force_wait)
        self.assertIn("FOMC", assessment.wait_reason)


class MacroCapabilityTests(unittest.TestCase):
    def test_capability(self) -> None:
        now = datetime(2026, 8, 5, 12, 0, 0, tzinfo=UTC)
        collector = MacroCollector()
        ctx = collector.acquire_macro_context(now)
        assessment = collector.evaluate_macro_assessment(ctx, now)

        provider = MockMacroProvider(ctx, assessment)
        telemetry = MockTelemetry()
        capability = MacroCapability(provider, telemetry)

        acquired = capability.get_macro_context(now)
        self.assertEqual(acquired.context_id, ctx.context_id)
        self.assertEqual(capability.health(now).state, HealthState.HEALTHY)


class MacroPublishingTests(unittest.TestCase):
    def test_generators(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            ctx_file = Path(tmpdir) / "macro_context.json"
            asm_file = Path(tmpdir) / "macro_assessment.json"
            evd_file = Path(tmpdir) / "macro_evidence.json"

            context_generator.generate(ctx_file)
            assessment_generator.generate(asm_file)
            evidence_generator.generate(evd_file)

            self.assertTrue(ctx_file.exists())
            self.assertTrue(asm_file.exists())
            self.assertTrue(evd_file.exists())

            ctx_data = json.loads(ctx_file.read_text(encoding="utf-8"))
            self.assertIn("macro_context", ctx_data["payload"])
