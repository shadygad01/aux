"""Unit tests for Phase 2 capability adapters (Normalization, Reasoning, Research)."""

import dataclasses
import unittest
from datetime import UTC, datetime, timedelta

from capabilities.collection import CollectionBatch, CollectionRequest, RawDatum
from capabilities.normalization import (
    CanonicalNormalizationAdapter,
    NormalizationCapability,
)
from capabilities.reasoning import CanonicalReasoningAdapter, ReasoningCapability
from capabilities.research import CanonicalResearchAdapter, ResearchCapability
from packages.domain import (
    AttentionBias,
    CurrentMarketState,
    Evidence,
    EvidenceDirection,
    EvidenceKind,
    HorizonBias,
    ReasoningInput,
    ReasoningStage,
    Recommendation,
    StageStatus,
    TradingHorizon,
)
from packages.infrastructure import InMemoryCapabilityTelemetry
from tests.test_capabilities import current_state

NOW = datetime(2026, 8, 8, 18, tzinfo=UTC)


def evidence(
    kind: EvidenceKind,
    direction: EvidenceDirection,
    *,
    identifier: str,
    observed_at: datetime,
    value: float = 1.0,
    forces_wait: bool = False,
) -> Evidence:
    return Evidence(
        evidence_id=identifier,
        kind=kind,
        direction=direction,
        observed_at=observed_at,
        time_to_live=timedelta(hours=1),
        strength=value,
        reliability=value,
        importance=value,
        historical_performance=value,
        confidence=value,
        rationale=f"{identifier} rationale",
        source="unit-test",
        forces_wait=forces_wait,
    )


def biased_state(bias: AttentionBias) -> CurrentMarketState:
    base = current_state()
    return dataclasses.replace(
        base, biases=(HorizonBias(TradingHorizon.MEDIUM_TERM, bias, "Directional context."),)
    )


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

    def test_reasoning_adapter_recommends_buy_from_weighted_evidence(self) -> None:
        adapter = CanonicalReasoningAdapter()
        state = biased_state(AttentionBias.BUY_ONLY)
        buy_evidence = evidence(
            EvidenceKind.LIQUIDITY_SWEEP,
            EvidenceDirection.BUY,
            identifier="buy-1",
            observed_at=state.captured_at,
        )
        sell_evidence = evidence(
            EvidenceKind.MACD,
            EvidenceDirection.SELL,
            identifier="sell-1",
            observed_at=state.captured_at,
            value=0.5,
        )
        reasoning_input = ReasoningInput(
            "reasoning-buy", state, (buy_evidence, sell_evidence), (), (), (), ()
        )

        result = adapter.evaluate(reasoning_input, state, (), state.captured_at)

        self.assertEqual(result.recommendation, Recommendation.BUY_SETUPS_ONLY)
        self.assertIn("buy-1", result.supporting_evidence)
        self.assertIn("sell-1", result.contradicting_evidence)
        self.assertIn("buy-1 rationale", result.why)
        # trade_quality is the winning side's mean weighted score (strength * confidence *
        # reliability * importance * freshness, all 1.0 here), scaled to a 0-100 int.
        self.assertEqual(result.trade_quality, 100)
        self.assertGreater(result.reliability, 0)
        location_stage = next(s for s in result.stages if s.stage is ReasoningStage.LOCATION)
        self.assertEqual(location_stage.status, StageStatus.MISSING)
        liquidity_stage = next(s for s in result.stages if s.stage is ReasoningStage.LIQUIDITY)
        self.assertEqual(liquidity_stage.status, StageStatus.COMPLETE)

    def test_reasoning_adapter_no_opinion_without_evidence(self) -> None:
        telemetry = InMemoryCapabilityTelemetry()
        adapter = CanonicalReasoningAdapter()
        capability = ReasoningCapability(adapter, telemetry)

        state = current_state()
        reasoning_val = ReasoningInput("reasoning-1", state, (), (), (), (), ())

        result = capability.reason(reasoning_val, state, (), state.captured_at)
        self.assertEqual(result.reasoning_id, "reasoning-1")
        self.assertEqual(result.recommendation, Recommendation.NO_OPINION)
        self.assertEqual(result.trade_quality, 0)
        # reliability falls back to state confidence discounted by uncertainty:
        # round(80 * (1 - 20/100)) == 64.
        self.assertEqual(result.reliability, 64)
        self.assertEqual(capability.health(NOW).details, "reasoner configured")

    def test_reasoning_adapter_forced_wait_overrides_direction(self) -> None:
        adapter = CanonicalReasoningAdapter()
        state = biased_state(AttentionBias.BUY_ONLY)
        forcing_evidence = evidence(
            EvidenceKind.NEWS,
            EvidenceDirection.NEUTRAL,
            identifier="news-1",
            observed_at=state.captured_at,
            forces_wait=True,
        )
        reasoning_input = ReasoningInput(
            "reasoning-wait", state, (forcing_evidence,), (), (), (), ()
        )

        result = adapter.evaluate(reasoning_input, state, (), state.captured_at)

        self.assertEqual(result.recommendation, Recommendation.WAIT)
        self.assertEqual(result.trade_quality, 0)
        self.assertIn("news-1", result.contradicting_evidence)

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
