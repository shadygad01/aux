"""Integration tests for capabilities production adapters."""

import unittest
from datetime import UTC, datetime

from capabilities.collection import (
    CollectionCapability,
    CollectionRequest,
    LiveMarketCollectionAdapter,
)
from capabilities.decision import OfficialDecision
from capabilities.publishing import CanonicalPublishingAdapter, PublishingCapability
from packages.infrastructure import InMemoryCapabilityTelemetry



class CapabilitiesProductionAdaptersTests(unittest.TestCase):
    def test_collection_adapter_integration(self) -> None:
        telemetry = InMemoryCapabilityTelemetry()
        adapter = LiveMarketCollectionAdapter()
        capability = CollectionCapability(adapter, telemetry)

        req = CollectionRequest(symbol="XAUUSD", requested_at=datetime.now(UTC))
        batch = capability.collect(req)

        self.assertEqual(batch.request.symbol, "XAUUSD")
        self.assertGreater(len(batch.records), 0)
        self.assertEqual(capability.health(datetime.now(UTC)).details, "adapter configured")

    def test_publishing_adapter_integration(self) -> None:
        from tests.test_capabilities import (
            comprehension_review,
            current_state,
            decision_critique,
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
