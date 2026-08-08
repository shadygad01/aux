"""Integration tests for capabilities production adapters."""

import unittest
from datetime import UTC, datetime
from unittest.mock import Mock

from capabilities.collection import (
    CollectionCapability,
    CollectionRequest,
    LiveMarketCollectionAdapter,
)
from capabilities.decision import OfficialDecision
from capabilities.publishing import CanonicalPublishingAdapter, PublishingCapability
from packages.domain import DealingRange, MarketObservation, NewsWindow
from packages.domain.macro_models import (
    DollarStrength,
    MacroContext,
    NewsEnvironment,
    NewsImpact,
    YieldEnvironment,
    YieldRegime,
)
from packages.infrastructure import InMemoryCapabilityTelemetry
from packages.infrastructure.live_collector import LiveMarketCollector
from packages.infrastructure.macro_collectors import MacroCollector


class CapabilitiesProductionAdaptersTests(unittest.TestCase):
    def test_collection_adapter_integration(self) -> None:
        """Uses Mock(spec=...) fakes for the real collectors so this test
        fails loudly (AttributeError) if the adapter calls a method that
        doesn't exist on them -- a prior version called
        LiveMarketCollector.fetch_latest_observation (real name:
        fetch_live_observation) and MacroCollector.collect (no such
        method; real entry point is acquire_macro_context), and a bare
        `except Exception` silently swallowed both, always falling back to
        "unavailable" placeholders in production. Asserting only
        `len(batch.records) > 0` (the previous version of this test) can't
        catch that, since the fallback branch also produces records."""
        observed_at = datetime.now(UTC)
        observation = MarketObservation(
            symbol="XAUUSD",
            timeframe="H1",
            observed_at=observed_at,
            structure=None,
            dealing_range=DealingRange(low=3300.0, high=3400.0, current_price=3350.5),
            liquidity=(),
            source="live-api:test",
        )
        market_collector = Mock(spec=LiveMarketCollector)
        market_collector.fetch_live_observation.return_value = (observation, "LIVE:test")

        macro_context = MacroContext(
            context_id="MACRO-CTX-TEST",
            dollar_strength=DollarStrength.BEARISH,
            yield_environment=YieldEnvironment(4.0, 4.0, "DOWN", "FALLING", YieldRegime.NEUTRAL),
            news_environment=NewsEnvironment(NewsImpact.LOW_IMPACT, NewsWindow.CLEAR, False, ""),
            liquidity_references=(),
            observed_at=observed_at,
        )
        macro_collector = Mock(spec=MacroCollector)
        macro_collector.acquire_macro_context.return_value = macro_context

        telemetry = InMemoryCapabilityTelemetry()
        adapter = LiveMarketCollectionAdapter(market_collector, macro_collector)
        capability = CollectionCapability(adapter, telemetry)

        req = CollectionRequest(symbol="XAUUSD", requested_at=datetime.now(UTC))
        batch = capability.collect(req)

        by_field = {record.field: record.value for record in batch.records}
        self.assertEqual(by_field["last_close"], "3350.5")
        self.assertEqual(by_field["collection_status"], "LIVE:test")
        self.assertEqual(by_field["dxy_trend"], "BEARISH")
        self.assertNotIn("market_data", by_field)  # would mean the live path raised
        self.assertNotIn("macro_data", by_field)
        self.assertEqual(batch.request.symbol, "XAUUSD")
        self.assertEqual(capability.health(datetime.now(UTC)).details, "adapter configured")

    def test_publishing_adapter_integration(self) -> None:
        from tests.test_capabilities import (
            decision_explanation,
            reasoning_decision,
            recommendation_trust,
        )

        telemetry = InMemoryCapabilityTelemetry()
        adapter = CanonicalPublishingAdapter()
        capability = PublishingCapability(adapter, telemetry)

        decision = OfficialDecision(
            decision_id="DEC-TEST-001",
            reasoning_id="reasoning-1",
            recommendation=reasoning_decision().recommendation,
            trade_quality=70,
            reliability=80,
            explanation=decision_explanation(),
            critique_id="critique-1",
            trust=recommendation_trust(),
            market_state_id="current-state-1",
            comprehension_review_id="comprehension-1",
            decided_at=datetime.now(UTC),
        )

        receipt = capability.publish(decision)
        self.assertEqual(receipt.decision_id, "DEC-TEST-001")
        self.assertTrue(receipt.publication_id.startswith("PUB-"))
        self.assertEqual(capability.health(datetime.now(UTC)).details, "sink configured")


if __name__ == "__main__":
    unittest.main()
