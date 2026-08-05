"""Market Story capability implementation."""

from __future__ import annotations

from datetime import datetime
from typing import Protocol

from capabilities.contracts import (
    CapabilityHealth,
    CapabilityLog,
    CapabilityMetric,
    CapabilityTelemetry,
    HealthState,
    LogLevel,
)
from packages.domain import MarketStory


class MarketStoryProvider(Protocol):
    def build_story(self, symbol: str, at: datetime) -> MarketStory: ...


class MarketStoryCapability:
    name = "market_story"

    def __init__(self, provider: MarketStoryProvider, telemetry: CapabilityTelemetry) -> None:
        self._provider = provider
        self._telemetry = telemetry

    def get_story(self, symbol: str, at: datetime) -> MarketStory:
        story = self._provider.build_story(symbol, at)
        if not story.is_valid(at):
            raise ValueError(f"generated story '{story.story_id}' is invalid or expired at {at.isoformat()}")

        self._telemetry.metric(CapabilityMetric(self.name, "stories_generated", 1, "count"))
        self._telemetry.log(
            CapabilityLog(
                self.name,
                LogLevel.INFO,
                "story_generated",
                (
                    ("story_id", story.story_id),
                    ("symbol", story.symbol),
                ),
            )
        )
        return story

    def health(self, checked_at: datetime) -> CapabilityHealth:
        return CapabilityHealth(self.name, HealthState.HEALTHY, checked_at, "market story engine active")
