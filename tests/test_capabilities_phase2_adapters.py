"""Unit tests for Phase 2 capability adapters (Normalization, Reasoning, Research)."""

import unittest
from datetime import UTC, datetime

from capabilities.collection import CollectionBatch, CollectionRequest, RawDatum
from capabilities.normalization import (
    CanonicalNormalizationAdapter,
    NormalizationCapability,
)
from capabilities.reasoning import CanonicalReasoningAdapter, ReasoningCapability
from capabilities.research import CanonicalResearchAdapter, ResearchCapability
from packages.domain import ReasoningInput
from packages.infrastructure import InMemoryCapabilityTelemetry
from tests.test_capabilities import current_state, reasoning_decision

NOW = datetime(2026, 8, 8, 18, tzinfo=UTC)


class Phase2CapabilityAdaptersTests(unittest.TestCase):
    def test_normalization_adapter(self) -> None:
        telemetry = InMemoryCapabilityTelemetry()
        capability = NormalizationCapability(
            CanonicalNormalizationAdapter.DEFAULT_FIELD_UNITS, telemetry
        )
        adapter = CanonicalNormalizationAdapter(capability)

        request = CollectionRequest("XAUUSD", NOW)
        batch = CollectionBatch(
            request=request,
            records=(RawDatum("last_close", "3350.5", NOW, "test"),),
            collected_at=NOW,
        )

        normalized = adapter.normalize(batch)
        self.assertEqual(len(normalized), 1)
        self.assertEqual(normalized[0].field, "last_close")
        self.assertEqual(normalized[0].value, 3350.5)
        self.assertEqual(normalized[0].unit, "USD_PER_OUNCE")

    def test_reasoning_adapter(self) -> None:
        telemetry = InMemoryCapabilityTelemetry()
        adapter = CanonicalReasoningAdapter()
        capability = ReasoningCapability(adapter, telemetry)

        state = current_state()
        reasoning_val = ReasoningInput(
            "reasoning-1",
            state,
            (),
            (),
            (),
            (),
            (),
        )

        result = capability.reason(reasoning_val, state, (), state.captured_at)
        self.assertEqual(result.reasoning_id, "reasoning-1")
        self.assertEqual(result.trade_quality, 75)
        self.assertEqual(capability.health(NOW).details, "reasoner configured")


    def test_research_adapter(self) -> None:
        telemetry = InMemoryCapabilityTelemetry()
        adapter = CanonicalResearchAdapter()
        capability = ResearchCapability(
            research_service=adapter, proposal_service=adapter, telemetry=telemetry
        )

        stats = capability.evaluate_edge((), ("structure", "liquidity"), 0.8, 0.9)
        self.assertEqual(stats.sample_size, 0)
        self.assertEqual(stats.confidence.evidence_quality, 0.8)

        proposal = capability.propose(
            proposal_id="PROP-001",
            question="What is the edge of BOS lookback?",
            hypothesis="Lookback 10 increases entry reachability.",
            method="Walk-forward simulation",
            statistics=stats,
            evidence_references=("H-025",),
            risk="Low",
            expected_gain="High",
            migration_impact="Zero breaking change",
            proposed_at=NOW,
        )
        self.assertEqual(proposal.proposal_id, "PROP-001")


if __name__ == "__main__":
    unittest.main()
