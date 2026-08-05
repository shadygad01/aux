import json
import unittest
from datetime import UTC, datetime, timedelta
from pathlib import Path
from tempfile import TemporaryDirectory

from packages.application import InstitutionalKnowledgeBase, KnowledgePolicy
from packages.domain import (
    EventMoment,
    HistoricalEvent,
    InstitutionalQuestion,
    KnowledgeCategory,
    KnowledgeObject,
    KnowledgeStatus,
    PatternKnowledge,
    SourceProfile,
    SourceType,
)
from packages.infrastructure import InMemoryKnowledgeRepository, JsonLinesKnowledgeRepository

NOW = datetime(2026, 8, 5, 12, tzinfo=UTC)


def source(
    identifier: str = "fed",
    *,
    reviewed_at: datetime = NOW,
    reliability: float = 0.9,
) -> SourceProfile:
    return SourceProfile(
        identifier,
        identifier.upper(),
        SourceType.OFFICIAL,
        reliability,
        1.0,
        0.9,
        0.1,
        0.9,
        reviewed_at,
        timedelta(days=30),
        (f"source-review-{identifier}",),
    )


def knowledge(
    *,
    status: KnowledgeStatus = KnowledgeStatus.OBSERVATION,
    revision: int = 1,
    reviewed_at: datetime = NOW,
) -> KnowledgeObject:
    return KnowledgeObject(
        "knowledge-001",
        revision,
        "Gold response to real-yield shocks",
        KnowledgeCategory.REAL_YIELDS,
        "Reviewed observation with explicit evidence.",
        ("fed",),
        0.8,
        0.7,
        "Initial historical review; validation is incomplete.",
        reviewed_at,
        timedelta(days=90),
        status,
        ("event-001",),
        ("event-contradiction-001",),
    )


def event(
    identifier: str,
    reaction: float,
    *,
    ignored_dxy: bool = False,
    yields_dominated: bool = False,
) -> HistoricalEvent:
    return HistoricalEvent(
        identifier,
        identifier.replace("-", " ").title(),
        (KnowledgeCategory.MACRO_ECONOMICS, KnowledgeCategory.GOLD),
        (EventMoment(NOW, "Event began and markets repriced."),),
        "Cross-asset repricing followed the event.",
        "Gold reversed sharply.",
        "DXY expanded.",
        "Real yields moved materially.",
        ("Context determines whether the inverse DXY relation holds.",),
        reaction,
        ignored_dxy,
        yields_dominated,
        (f"evidence-{identifier}",),
    )


def pattern(
    identifier: str,
    condition: str,
    failure_rate: float,
    sample_size: int,
    *,
    status: KnowledgeStatus = KnowledgeStatus.VALIDATED,
) -> PatternKnowledge:
    return PatternKnowledge(
        identifier,
        identifier.replace("-", " ").title(),
        status,
        (condition,),
        sample_size,
        1 - failure_rate,
        failure_rate,
        ("Regime sensitivity",),
        ("LONDON",),
        ("ASIA",),
        (f"study-{identifier}",),
        NOW,
        timedelta(days=90),
    )


class KnowledgeBaseTests(unittest.TestCase):
    def setUp(self) -> None:
        self.repository = InMemoryKnowledgeRepository()
        self.base = InstitutionalKnowledgeBase(KnowledgePolicy(), self.repository)

    def test_knowledge_requires_registered_evidence_source(self) -> None:
        with self.assertRaisesRegex(ValueError, "unknown sources"):
            self.base.register_knowledge(knowledge())
        self.base.register_source(source())
        self.base.register_knowledge(knowledge())
        self.assertEqual(self.repository.knowledge(), (knowledge(),))

    def test_status_evolves_only_through_governed_append_only_revisions(self) -> None:
        self.base.register_source(source())
        observation = knowledge()
        self.base.register_knowledge(observation)
        with self.assertRaisesRegex(ValueError, "invalid knowledge transition"):
            self.base.transition(
                observation,
                KnowledgeStatus.VALIDATED,
                NOW,
                "Skipped hypothesis stage.",
                ("study",),
            )
        hypothesis = self.base.transition(
            observation,
            KnowledgeStatus.HYPOTHESIS,
            NOW,
            "Hypothesis registered for testing.",
            ("study-plan",),
        )
        self.assertEqual(hypothesis.revision, 2)
        self.assertEqual(len(self.repository.knowledge()), 2)

    def test_due_for_review_uses_latest_revision_only(self) -> None:
        self.base.register_source(source())
        old = knowledge(reviewed_at=NOW - timedelta(days=100))
        fresh = knowledge(revision=2, reviewed_at=NOW)
        self.base.register_knowledge(old)
        self.base.register_knowledge(fresh)
        self.assertEqual(self.base.due_for_review(NOW), ())
        self.assertEqual(self.base.due_for_review(NOW + timedelta(days=91)), (fresh,))

    def test_source_ranking_recalculates_freshness_and_historical_quality(self) -> None:
        self.base.register_source(source("fresh-high"))
        self.base.register_source(
            source("stale-low", reviewed_at=NOW - timedelta(days=30), reliability=0.5)
        )
        ranking = self.base.rank_sources(NOW)
        self.assertEqual(ranking[0].source_id, "fresh-high")
        self.assertEqual(ranking[0].rank, 1)
        self.assertEqual(ranking[1].freshness, 0)

    def test_event_questions_return_only_explicit_evidence_backed_flags(self) -> None:
        self.base.register_event(event("covid", 8.0, ignored_dxy=True))
        self.base.register_event(event("yield-shock", -4.0, yields_dominated=True))
        ignored = self.base.answer(InstitutionalQuestion.GOLD_IGNORED_DXY)
        yields = self.base.answer(InstitutionalQuestion.YIELDS_DOMINATED_GOLD)
        strongest = self.base.answer(InstitutionalQuestion.STRONGEST_MACRO_REVERSALS)
        self.assertEqual(ignored.result_ids, ("covid",))
        self.assertEqual(yields.result_ids, ("yield-shock",))
        self.assertEqual(strongest.result_ids, ("covid", "yield-shock"))
        self.assertIn("evidence-covid", ignored.evidence_references)

    def test_pattern_question_uses_validated_samples_and_weighted_failure_rate(self) -> None:
        self.base.register_pattern(pattern("premium-a", "premium", 0.2, 100))
        self.base.register_pattern(pattern("premium-b", "premium", 0.4, 50))
        self.base.register_pattern(
            pattern(
                "premium-experiment",
                "premium",
                1.0,
                1000,
                status=KnowledgeStatus.HYPOTHESIS,
            )
        )
        answer = self.base.answer(InstitutionalQuestion.PREMIUM_FAILURE_RATE)
        self.assertIn("26.6667%", answer.summary)
        self.assertEqual(answer.result_ids, ("premium-a", "premium-b"))

    def test_no_evidence_produces_explicit_abstention_answer(self) -> None:
        event_answer = self.base.answer(InstitutionalQuestion.GOLD_IGNORED_DXY)
        pattern_answer = self.base.answer(InstitutionalQuestion.SWEEP_FAILURE_RATE)
        self.assertIn("No evidence-backed", event_answer.summary)
        self.assertIn("No validated", pattern_answer.summary)


class KnowledgeDomainTests(unittest.TestCase):
    def test_objects_reject_missing_evidence_and_invalid_statistics(self) -> None:
        with self.assertRaises(ValueError):
            SourceProfile(
                "source",
                "Source",
                SourceType.COMMUNITY,
                0.5,
                0.5,
                0.5,
                0.5,
                0.5,
                NOW,
                timedelta(days=1),
                (),
            )
        with self.assertRaises(ValueError):
            pattern("bad", "sweep", 0.6, 10).__class__(
                "bad",
                "Bad",
                KnowledgeStatus.HYPOTHESIS,
                ("sweep",),
                10,
                0.6,
                0.6,
                (),
                (),
                (),
                ("study",),
                NOW,
                timedelta(days=1),
            )

    def test_review_and_freshness_require_timezone_aware_time(self) -> None:
        with self.assertRaises(ValueError):
            source().freshness(datetime(2026, 8, 5))
        with self.assertRaises(ValueError):
            knowledge().review_due(datetime(2026, 8, 5))

    def test_policy_rejects_unbalanced_weights(self) -> None:
        with self.assertRaisesRegex(ValueError, "total one"):
            KnowledgePolicy(reliability_weight=0.5)


class KnowledgeInfrastructureTests(unittest.TestCase):
    def test_journal_persists_all_structured_object_types(self) -> None:
        with TemporaryDirectory() as directory:
            path = Path(directory) / "knowledge.jsonl"
            repository = JsonLinesKnowledgeRepository(path)
            base = InstitutionalKnowledgeBase(KnowledgePolicy(), repository)
            base.register_source(source())
            base.register_knowledge(knowledge())
            base.register_event(event("event-1", 3.0))
            base.register_pattern(pattern("sweep-1", "sweep", 0.3, 20))
            records = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
        self.assertEqual(
            [record["record_type"] for record in records],
            ["source", "knowledge", "event", "pattern"],
        )
        self.assertEqual(records[1]["payload"]["supporting_evidence"], ["event-001"])


if __name__ == "__main__":
    unittest.main()
