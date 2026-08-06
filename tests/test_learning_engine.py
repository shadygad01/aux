import json
import unittest
from datetime import UTC, datetime
from pathlib import Path
from tempfile import TemporaryDirectory

from packages.application import LearningEngine, LearningPolicy
from packages.application.errors import DecisionEvaluationError
from packages.domain import (
    AttentionBias,
    HorizonBias,
    KnowledgeConcept,
    KnowledgeLevel,
    LearningRecommendation,
    LearningRecord,
    MarketSnapshot,
    OutcomeClassification,
    RangeLocation,
    Recommendation,
    RecommendationStatus,
    ResearchArtifact,
    ResearchArtifactKind,
    TradingHorizon,
)
from packages.infrastructure import JsonLinesLearningRepository, learning_record_to_json

NOW = datetime(2026, 8, 5, 12, tzinfo=UTC)


class RecordingLearningRepository:
    def __init__(self) -> None:
        self.records: list[LearningRecord] = []
        self.artifacts: list[ResearchArtifact] = []
        self.recommendations: list[LearningRecommendation] = []

    def append_record(self, record: LearningRecord) -> None:
        self.records.append(record)

    def append_artifact(self, artifact: ResearchArtifact) -> None:
        self.artifacts.append(artifact)

    def append_recommendation(self, recommendation: LearningRecommendation) -> None:
        self.recommendations.append(recommendation)


class FailingLearningRepository(RecordingLearningRepository):
    def append_record(self, record: LearningRecord) -> None:
        raise OSError("research store unavailable")


def learning_record(
    outcome: OutcomeClassification,
    *,
    identifier: str = "learning-001",
    opportunity_id: str | None = None,
) -> LearningRecord:
    return LearningRecord(
        record_id=identifier,
        decision_audit_id=f"audit-{identifier}",
        timestamp=NOW,
        market_snapshot=MarketSnapshot(3350.0, NOW, "reviewed-feed", "snapshot-001"),
        biases=tuple(
            HorizonBias(horizon, AttentionBias.BUY_ONLY, "reviewed bias")
            for horizon in TradingHorizon
        ),
        trade_quality=85,
        location=RangeLocation.DISCOUNT,
        liquidity=("PWL", "sell-side sweep"),
        macd=-2.5,
        news=("No active high-impact conflict",),
        macro="Rates and real yields assessed as supportive",
        dxy=97.2,
        real_yields=1.65,
        session="LONDON_NEW_YORK_OVERLAP",
        smc_evidence=("liquidity sweep", "reversal candle"),
        supporting_evidence=("discount", "MACD below zero"),
        contradicting_evidence=("minor DXY rebound",),
        decision=Recommendation.BUY_SETUPS_ONLY,
        outcome=outcome,
        maximum_favorable_excursion=18.4,
        maximum_adverse_excursion=4.1,
        learning_notes=("Review whether the DXY rebound was material.",),
        what_changed_after="Price displaced from discount after the decision.",
        opportunity_id=opportunity_id,
    )


class LearningEngineTests(unittest.TestCase):
    def setUp(self) -> None:
        self.repository = RecordingLearningRepository()
        self.engine = LearningEngine(LearningPolicy(), self.repository)

    def test_every_failure_classification_creates_working_hypothesis(self) -> None:
        failures = (
            OutcomeClassification.LOSING,
            OutcomeClassification.FALSE_POSITIVE,
            OutcomeClassification.FALSE_NEGATIVE,
            OutcomeClassification.MISSED,
            OutcomeClassification.REJECTED,
            OutcomeClassification.IGNORED,
        )
        for index, outcome in enumerate(failures):
            artifact = self.engine.record(learning_record(outcome, identifier=f"failure-{index}"))
            self.assertIsNotNone(artifact)
            assert artifact is not None
            self.assertEqual(artifact.kind, ResearchArtifactKind.HYPOTHESIS)
            self.assertEqual(artifact.knowledge_level, KnowledgeLevel.WORKING_HYPOTHESIS)
        self.assertEqual(len(self.repository.records), len(failures))
        self.assertEqual(len(self.repository.artifacts), len(failures))

    def test_every_success_creates_supporting_evidence_not_a_rule(self) -> None:
        artifact = self.engine.record(learning_record(OutcomeClassification.WINNING))
        self.assertIsNotNone(artifact)
        assert artifact is not None
        self.assertEqual(artifact.kind, ResearchArtifactKind.SUPPORTING_EVIDENCE)
        self.assertEqual(artifact.knowledge_level, KnowledgeLevel.EXPERIMENTAL)

    def test_pending_and_wait_records_are_stored_without_invented_findings(self) -> None:
        self.assertIsNone(self.engine.record(learning_record(OutcomeClassification.PENDING)))
        self.assertIsNone(self.engine.record(learning_record(OutcomeClassification.WAIT)))
        self.assertEqual(len(self.repository.records), 2)

    def test_edge_statistics_are_observed_and_reproducible(self) -> None:
        records = (
            learning_record(OutcomeClassification.WINNING, identifier="win-1"),
            learning_record(OutcomeClassification.WINNING, identifier="win-2"),
            learning_record(OutcomeClassification.LOSING, identifier="loss-1"),
            learning_record(OutcomeClassification.WAIT, identifier="wait-1"),
        )
        statistics = self.engine.evaluate_edge(
            records,
            ("discount", "PWL", "MACD below zero", "liquidity sweep"),
            evidence_quality=0.9,
            data_quality=0.8,
        )
        self.assertEqual(statistics.sample_size, 3)
        self.assertEqual(statistics.win_rate, 0.666667)
        self.assertEqual(statistics.confidence.sample_size_adequacy, 0.03)
        self.assertLess(statistics.confidence.score, 50)

    def test_empty_or_unmatched_edge_returns_no_invented_performance(self) -> None:
        with self.assertRaisesRegex(ValueError, "combination"):
            self.engine.evaluate_edge((), (), 1.0, 1.0)
        statistics = self.engine.evaluate_edge(
            (learning_record(OutcomeClassification.WINNING),),
            ("not present",),
            1.0,
            1.0,
        )
        self.assertEqual(statistics.sample_size, 0)
        self.assertEqual(statistics.win_rate, 0)
        self.assertEqual(statistics.confidence.score, 0)

    def test_opportunity_edge_deduplicates_records_sharing_an_opportunity_id(self) -> None:
        combination = ("discount", "PWL", "MACD below zero", "liquidity sweep")
        records = (
            learning_record(
                OutcomeClassification.LOSING, identifier="snap-1", opportunity_id="OPP-1"
            ),
            learning_record(
                OutcomeClassification.WINNING, identifier="snap-2", opportunity_id="OPP-1"
            ),
            learning_record(OutcomeClassification.WINNING, identifier="snap-3"),
        )

        statistics = self.engine.evaluate_opportunity_edge(
            records, combination, evidence_quality=0.9, data_quality=0.8
        )

        # snap-1 and snap-2 are the same opportunity lifetime; only the later
        # record (WINNING) should count, plus the standalone snap-3 record —
        # not all three raw snapshots.
        self.assertEqual(statistics.sample_size, 2)
        self.assertEqual(statistics.win_rate, 1.0)

    def test_opportunity_edge_falls_back_to_record_id_without_opportunity_id(self) -> None:
        combination = ("discount", "PWL", "MACD below zero", "liquidity sweep")
        records = (
            learning_record(OutcomeClassification.WINNING, identifier="snap-1"),
            learning_record(OutcomeClassification.LOSING, identifier="snap-2"),
        )

        statistics = self.engine.evaluate_opportunity_edge(
            records, combination, evidence_quality=0.9, data_quality=0.8
        )

        self.assertEqual(statistics.sample_size, 2)

    def test_recommendation_requires_validation_and_cannot_deploy(self) -> None:
        statistics = self.engine.evaluate_edge(
            (learning_record(OutcomeClassification.WINNING),),
            ("discount",),
            0.8,
            0.9,
        )
        recommendation = self.engine.propose(
            "proposal-001",
            "Location weight is 15.",
            "Test location weight 18 in a held-out study.",
            statistics,
            ("learning-001",),
            "Potentially improve poor-setup filtering.",
            "May overfit a small sample.",
        )
        self.assertEqual(recommendation.status, RecommendationStatus.VALIDATION_REQUIRED)
        self.assertTrue(recommendation.requires_approval)
        self.assertEqual(self.repository.recommendations, [recommendation])
        with self.assertRaisesRegex(ValueError, "cannot mark"):
            LearningRecommendation(
                recommendation.recommendation_id,
                recommendation.current_rule,
                recommendation.suggested_improvement,
                recommendation.supporting_evidence,
                recommendation.historical_statistics,
                recommendation.expected_impact,
                recommendation.migration_risk,
                recommendation.confidence,
                status=RecommendationStatus.APPROVED,
            )

    def test_storage_failure_is_observable(self) -> None:
        engine = LearningEngine(LearningPolicy(), FailingLearningRepository())
        with self.assertRaisesRegex(DecisionEvaluationError, "learning audit failed"):
            engine.record(learning_record(OutcomeClassification.LOSING))


class LearningDomainTests(unittest.TestCase):
    def test_knowledge_levels_enforce_production_eligibility(self) -> None:
        with self.assertRaisesRegex(ValueError, "never production"):
            KnowledgeConcept("exp-1", "experiment", KnowledgeLevel.EXPERIMENTAL, "test", (), True)
        with self.assertRaisesRegex(ValueError, "must remain"):
            KnowledgeConcept(
                "principle-1",
                "Trader owns execution",
                KnowledgeLevel.IMMUTABLE_PRINCIPLE,
                "constitution",
                (),
                False,
            )
        with self.assertRaisesRegex(ValueError, "backtest"):
            KnowledgeConcept(
                "rule-1",
                "candidate rule",
                KnowledgeLevel.VALIDATED_RULE,
                "research",
                ("study-1",),
                True,
            )
        validated = KnowledgeConcept(
            "rule-2",
            "validated rule",
            KnowledgeLevel.VALIDATED_RULE,
            "approved evidence",
            ("backtest-1", "forward-1", "approval-1"),
            True,
            backtested=True,
            forward_tested=True,
            approved=True,
        )
        self.assertTrue(validated.production_eligible)

    def test_record_requires_complete_traceable_context(self) -> None:
        record = learning_record(OutcomeClassification.PENDING)
        with self.assertRaises(ValueError):
            LearningRecord(
                "",
                record.decision_audit_id,
                record.timestamp,
                record.market_snapshot,
                record.biases,
                101,
                record.location,
                record.liquidity,
                record.macd,
                record.news,
                record.macro,
                record.dxy,
                record.real_yields,
                record.session,
                record.smc_evidence,
                record.supporting_evidence,
                record.contradicting_evidence,
                record.decision,
                record.outcome,
                None,
                None,
                (),
                "",
            )


class LearningInfrastructureTests(unittest.TestCase):
    def test_append_only_repository_stores_record_artifact_and_proposal(self) -> None:
        with TemporaryDirectory() as directory:
            path = Path(directory) / "learning.jsonl"
            engine = LearningEngine(
                LearningPolicy(minimum_edge_sample=1), JsonLinesLearningRepository(path)
            )
            record = learning_record(OutcomeClassification.LOSING)
            engine.record(record)
            statistics = engine.evaluate_edge(
                (learning_record(OutcomeClassification.WINNING),),
                ("discount",),
                1.0,
                1.0,
            )
            engine.propose(
                "proposal", "current", "suggested", statistics, ("ref",), "impact", "risk"
            )
            events = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
        payload = learning_record_to_json(record)
        self.assertEqual(payload["premium_discount"], "DISCOUNT")
        self.assertEqual(
            [event["event"] for event in events],
            [
                "learning_record",
                "research_artifact",
                "learning_recommendation",
            ],
        )
        self.assertTrue(events[2]["payload"]["requires_approval"])


if __name__ == "__main__":
    unittest.main()
