import json
import unittest
from datetime import UTC, datetime, timedelta
from pathlib import Path
from tempfile import TemporaryDirectory

from packages.application import EvidenceDecisionEngine
from packages.application.errors import DecisionEvaluationError
from packages.domain import (
    Evidence,
    EvidenceDecision,
    EvidenceDirection,
    EvidenceKind,
    EvidencePolicy,
    Recommendation,
)
from packages.infrastructure import JsonLinesEvidenceDecisionAudit, evidence_decision_to_json

NOW = datetime(2026, 8, 5, 12, tzinfo=UTC)


class RecordingEvidenceAudit:
    def __init__(self) -> None:
        self.decisions: list[EvidenceDecision] = []

    def record(self, evidence: tuple[Evidence, ...], decision: EvidenceDecision) -> None:
        self.decisions.append(decision)


class FailingEvidenceAudit:
    def record(self, evidence: tuple[Evidence, ...], decision: EvidenceDecision) -> None:
        raise OSError("audit unavailable")


def item(
    kind: EvidenceKind,
    *,
    direction: EvidenceDirection = EvidenceDirection.BUY,
    identifier: str | None = None,
    observed_at: datetime = NOW,
    ttl: timedelta = timedelta(hours=1),
    value: float = 1.0,
    forces_wait: bool = False,
) -> Evidence:
    return Evidence(
        evidence_id=identifier or kind.value.lower(),
        kind=kind,
        direction=direction,
        observed_at=observed_at,
        time_to_live=ttl,
        strength=value,
        reliability=value,
        importance=value,
        historical_performance=value,
        confidence=value,
        rationale=f"reviewed {kind.value.lower()} evidence",
        source="unit-test",
        forces_wait=forces_wait,
    )


def complete(direction: EvidenceDirection = EvidenceDirection.BUY) -> tuple[Evidence, ...]:
    return tuple(
        item(kind, direction=direction) for kind in EvidencePolicy().required_execution_kinds
    )


class EvidenceDecisionEngineTests(unittest.TestCase):
    def setUp(self) -> None:
        self.audit = RecordingEvidenceAudit()
        self.engine = EvidenceDecisionEngine(EvidencePolicy(), self.audit)

    def test_complete_buy_evidence_returns_buy_setups_only(self) -> None:
        decision = self.engine.evaluate(complete(), NOW)
        self.assertEqual(decision.recommendation, Recommendation.BUY_SETUPS_ONLY)
        self.assertEqual(decision.trade_quality, 100)
        self.assertEqual(decision.confidence, 100)
        self.assertEqual(len(decision.why), 6)
        self.assertIn("expiry", decision.what_would_change[0])
        self.assertEqual(self.audit.decisions, [decision])

    def test_complete_sell_evidence_returns_sell_setups_only(self) -> None:
        decision = self.engine.evaluate(complete(EvidenceDirection.SELL), NOW)
        self.assertEqual(decision.recommendation, Recommendation.SELL_SETUPS_ONLY)

    def test_insufficient_reliable_evidence_returns_no_opinion(self) -> None:
        decision = self.engine.evaluate((item(EvidenceKind.MACRO),), NOW)
        self.assertEqual(decision.recommendation, Recommendation.NO_OPINION)
        self.assertTrue(any("market-bias" in value.lower() for value in decision.what_would_change))

    def test_direction_exists_but_execution_evidence_missing_returns_wait(self) -> None:
        partial = tuple(item(kind) for kind in (EvidenceKind.MACRO, EvidenceKind.MARKET_BIAS))
        decision = self.engine.evaluate(partial, NOW)
        self.assertEqual(decision.recommendation, Recommendation.WAIT)
        self.assertTrue(any("LIQUIDITY_SWEEP" in value for value in decision.missing))
        self.assertTrue(decision.what_would_change)

    def test_expired_evidence_loses_all_weight_automatically(self) -> None:
        expired = tuple(
            item(kind, observed_at=NOW - timedelta(hours=1))
            for kind in EvidencePolicy().required_execution_kinds
        )
        decision = self.engine.evaluate(expired, NOW)
        self.assertEqual(decision.recommendation, Recommendation.NO_OPINION)
        self.assertTrue(all(value.effective_weight == 0 for value in decision.evidence))
        self.assertTrue(all(value.freshness == 0 for value in decision.evidence))
        self.assertTrue(any("expired" in value for value in decision.why_not))

    def test_freshness_and_weight_decay_are_reproducible(self) -> None:
        evidence = complete()
        decision = self.engine.evaluate(evidence, NOW + timedelta(minutes=30))
        self.assertTrue(all(value.freshness == 0.5 for value in decision.evidence))
        self.assertTrue(all(value.effective_weight == 0.5 for value in decision.evidence))
        self.assertEqual(decision.confidence, 100)

    def test_conflicting_evidence_reduces_reproducible_confidence(self) -> None:
        contradiction = item(
            EvidenceKind.OTHER,
            direction=EvidenceDirection.SELL,
            identifier="dxy-contradiction",
        )
        decision = self.engine.evaluate(complete() + (contradiction,), NOW)
        self.assertEqual(decision.confidence, 71)
        self.assertEqual(decision.trade_quality, 71)
        self.assertEqual(decision.recommendation, Recommendation.WAIT)

    def test_force_wait_evidence_never_becomes_a_fifth_output(self) -> None:
        news = item(
            EvidenceKind.NEWS,
            direction=EvidenceDirection.NEUTRAL,
            forces_wait=True,
        )
        decision = self.engine.evaluate(complete() + (news,), NOW)
        self.assertEqual(decision.recommendation, Recommendation.WAIT)
        self.assertTrue(any("condition clears" in value for value in decision.what_would_change))

    def test_future_evidence_is_excluded(self) -> None:
        future = tuple(
            item(kind, observed_at=NOW + timedelta(seconds=1))
            for kind in EvidencePolicy().required_execution_kinds
        )
        decision = self.engine.evaluate(future, NOW)
        self.assertEqual(decision.recommendation, Recommendation.NO_OPINION)
        self.assertTrue(any("future-dated" in value for value in decision.why_not))

    def test_duplicate_identifiers_and_naive_time_are_rejected(self) -> None:
        duplicate = (item(EvidenceKind.MACRO, identifier="same"),) * 2
        with self.assertRaisesRegex(DecisionEvaluationError, "unique"):
            self.engine.evaluate(duplicate, NOW)
        with self.assertRaisesRegex(DecisionEvaluationError, "timezone-aware"):
            self.engine.evaluate((), datetime(2026, 8, 5, 12))

    def test_audit_failure_makes_decision_unavailable(self) -> None:
        engine = EvidenceDecisionEngine(EvidencePolicy(), FailingEvidenceAudit())
        with self.assertRaisesRegex(DecisionEvaluationError, "audit failed") as context:
            engine.evaluate(complete(), NOW)
        self.assertIsInstance(context.exception.__cause__, OSError)


class EvidenceDomainTests(unittest.TestCase):
    def test_evidence_validates_ttl_attributes_and_context(self) -> None:
        with self.assertRaises(ValueError):
            item(EvidenceKind.MACRO, ttl=timedelta(0))
        with self.assertRaises(ValueError):
            item(EvidenceKind.MACRO, value=1.1)

    def test_freshness_rejects_naive_time_and_future_age_is_full(self) -> None:
        evidence = item(EvidenceKind.MACRO)
        with self.assertRaisesRegex(ValueError, "timezone-aware"):
            evidence.freshness(datetime(2026, 8, 5, 12))
        self.assertEqual(evidence.freshness(NOW - timedelta(seconds=1)), 1.0)

    def test_policy_validates_thresholds_and_precision(self) -> None:
        with self.assertRaises(ValueError):
            EvidencePolicy(minimum_reliable_weight=1.1)
        with self.assertRaises(ValueError):
            EvidencePolicy(minimum_trade_quality=101)
        with self.assertRaises(ValueError):
            EvidencePolicy(weight_precision=-1)


class EvidenceInfrastructureTests(unittest.TestCase):
    def test_json_contract_and_append_only_audit_preserve_weights(self) -> None:
        with TemporaryDirectory() as directory:
            path = Path(directory) / "evidence.jsonl"
            decision = EvidenceDecisionEngine(
                EvidencePolicy(), JsonLinesEvidenceDecisionAudit(path)
            ).evaluate(complete(), NOW)
            record = json.loads(path.read_text(encoding="utf-8"))
        payload = evidence_decision_to_json(decision)
        self.assertEqual(payload["contract_version"], "3.0.0")
        self.assertEqual(record["event"], "evidence_decision_evaluated")
        self.assertEqual(record["evidence"][0]["time_to_live_seconds"], 3600.0)
        self.assertEqual(record["decision"]["confidence"], 100)


if __name__ == "__main__":
    unittest.main()
