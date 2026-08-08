"""Tests for Live Market Collector, Market Story, Market Thesis, and Sqlite Durable Store."""

from __future__ import annotations

import json
import tempfile
import unittest
from datetime import UTC, datetime
from pathlib import Path

from capabilities.contracts import HealthState
from capabilities.market_story import MarketStoryCapability
from packages.domain import (
    DecisionVerdict,
    MarketStory,
    MarketStoryStage,
    MarketThesis,
    StoryStageDetail,
    TradeQuality,
    TradeQualityGrade,
)
from packages.infrastructure.live_collector import LiveMarketCollector
from packages.infrastructure.sqlite_decision_store import SqliteDecisionStore
from publish.generators import market_story as story_generator
from publish.generators import market_thesis as thesis_generator


class MockTelemetry:
    def __init__(self) -> None:
        self.metrics: list[object] = []
        self.logs: list[object] = []

    def metric(self, value: object) -> None:
        self.metrics.append(value)

    def log(self, value: object) -> None:
        self.logs.append(value)


class MockStoryProvider:
    def __init__(self, story: MarketStory) -> None:
        self.story = story

    def build_story(self, symbol: str, at: datetime) -> MarketStory:
        return self.story


class LiveCollectorTests(unittest.TestCase):
    def test_live_collector_fallback(self) -> None:
        collector = LiveMarketCollector(timeout_seconds=1)
        obs, source = collector.fetch_live_observation()
        self.assertIsNotNone(obs)
        self.assertEqual(obs.symbol, "XAUUSD")
        self.assertTrue(source.startswith("LIVE:") or source.startswith("FALLBACK:"))


class MarketStoryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.now = datetime(2026, 8, 5, 12, 0, 0, tzinfo=UTC)
        stage = StoryStageDetail(
            stage=MarketStoryStage.SMC,
            title="SMC BOS",
            status="VALIDATED",
            narrative="Confirmed BOS",
            evidence_ids=("EVD-01",),
        )
        self.story = MarketStory(
            story_id="STORY-001",
            symbol="XAUUSD",
            timeframe="H1",
            evolution_summary="Bullish BOS evolution",
            stages=(stage,),
            created_at=self.now,
            ttl_seconds=3600,
        )

    def test_story_lifecycle_and_serialization(self) -> None:
        self.assertTrue(self.story.is_valid(self.now))
        raw = self.story.to_dict()
        restored = MarketStory.from_dict(raw)
        self.assertEqual(self.story.story_id, restored.story_id)
        self.assertEqual(self.story.stages[0].stage, restored.stages[0].stage)

    def test_market_story_capability(self) -> None:
        provider = MockStoryProvider(self.story)
        telemetry = MockTelemetry()
        capability = MarketStoryCapability(provider, telemetry)

        acquired = capability.get_story("XAUUSD", self.now)
        self.assertEqual(acquired.story_id, "STORY-001")
        self.assertEqual(capability.health(self.now).state, HealthState.HEALTHY)


class MarketThesisAndStoreTests(unittest.TestCase):
    def setUp(self) -> None:
        self.now = datetime(2026, 8, 5, 12, 0, 0, tzinfo=UTC)
        tq = TradeQuality(
            score=90,
            grade=TradeQualityGrade.EXCELLENT,
            breakdown={"structure": 30, "location": 30, "liquidity": 30},
            explanation="High alignment",
        )
        self.thesis = MarketThesis(
            thesis_id="THESIS-001",
            symbol="XAUUSD",
            timeframe="H1",
            verdict=DecisionVerdict.BUY,
            meaning="Search for BUY setup",
            confidence="HIGH",
            confidence_score=1.0,
            uncertainty_score=0.0,
            trade_quality=tq,
            reasons=("Bullish BOS",),
            conflicts=(),
            missing_evidence=(),
            evaluated_at=self.now,
            policy_version="v1",
            setup_quality_score=90,
        )

    def test_market_thesis_serialization(self) -> None:
        raw = self.thesis.to_dict()
        restored = MarketThesis.from_dict(raw)
        self.assertEqual(self.thesis.thesis_id, restored.thesis_id)
        self.assertEqual(self.thesis.trade_quality.score, restored.trade_quality.score)

    def test_from_dict_rejects_missing_setup_quality_score(self) -> None:
        raw = self.thesis.to_dict()
        del raw["setup_quality_score"]
        with self.assertRaises(KeyError):
            MarketThesis.from_dict(raw)

    def test_sqlite_durable_store(self) -> None:
        store = SqliteDecisionStore(":memory:")
        content_hash = store.save_thesis(self.thesis)
        self.assertTrue(len(content_hash) > 0)

        retrieved = store.get_thesis("THESIS-001")
        self.assertIsNotNone(retrieved)
        if retrieved:
            self.assertEqual(retrieved.thesis_id, "THESIS-001")
            self.assertEqual(retrieved.trade_quality.score, 90)


class CompletionPublishingTests(unittest.TestCase):
    def test_generators(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            story_file = Path(tmpdir) / "market_story.json"
            thesis_file = Path(tmpdir) / "market_thesis.json"

            story_generator.generate(story_file)
            thesis_generator.generate(thesis_file)

            self.assertTrue(story_file.exists())
            self.assertTrue(thesis_file.exists())

            story_data = json.loads(story_file.read_text(encoding="utf-8"))
            thesis_data = json.loads(thesis_file.read_text(encoding="utf-8"))

            self.assertIn("story", story_data["payload"])
            self.assertIn("thesis", thesis_data["payload"])
