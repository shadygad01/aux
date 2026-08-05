import json
import unittest
from datetime import UTC, datetime, timedelta
from pathlib import Path
from tempfile import TemporaryDirectory

from packages.application import (
    EvidenceDecisionEngine,
    InstitutionalReasoningEngine,
    ReasoningPolicy,
)
from packages.application.errors import DecisionEvaluationError
from packages.domain import (
    EdgeStatistics,
    EventMoment,
    Evidence,
    EvidenceDecision,
    EvidenceDirection,
    EvidenceKind,
    EvidencePolicy,
    HistoricalEvent,
    HistoricalSimilarity,
    KnowledgeCategory,
    KnowledgeLevel,
    KnowledgeObject,
    KnowledgeStatus,
    LearningConfidence,
    LearningRecommendation,
    MarketState,
    RangeLocation,
    ReasoningDecision,
    ReasoningInput,
    ReasoningMistake,
    ReasoningMistakeKind,
    ReasoningStage,
    Recommendation,
    ResearchArtifact,
    ResearchArtifactKind,
)
from packages.infrastructure import JsonLinesReasoningAudit, reasoning_decision_to_json

NOW = datetime(2026, 8, 5, 12, tzinfo=UTC)


class RecordingEvidenceAudit:
    def record(self, evidence: tuple[Evidence, ...], decision: EvidenceDecision) -> None:
        pass


class RecordingReasoningAudit:
    def __init__(self) -> None:
        self.paths: list[ReasoningDecision] = []
        self.mistakes: list[ReasoningMistake] = []

    def append_path(self, reasoning_input: ReasoningInput, decision: ReasoningDecision) -> None:
        self.paths.append(decision)

    def append_mistake(self, mistake: ReasoningMistake) -> None:
        self.mistakes.append(mistake)


class FailingReasoningAudit(RecordingReasoningAudit):
    def append_path(self, reasoning_input: ReasoningInput, decision: ReasoningDecision) -> None:
        raise OSError("reasoning audit unavailable")


def evidence(kind: EvidenceKind, identifier: str | None = None) -> Evidence:
    return Evidence(
        identifier or kind.value.lower(),
        kind,
        EvidenceDirection.BUY,
        NOW,
        timedelta(hours=1),
        1.0,
        1.0,
        1.0,
        1.0,
        1.0,
        f"reviewed {kind.value.lower()} context",
        "reasoning-test",
    )


def complete_evidence() -> tuple[Evidence, ...]:
    return tuple(evidence(kind) for kind in EvidencePolicy().required_execution_kinds)


def historical_event() -> HistoricalEvent:
    return HistoricalEvent(
        "event-001",
        "Historical real-yield shock",
        (KnowledgeCategory.REAL_YIELDS,),
        (EventMoment(NOW - timedelta(days=365), "Yields repriced."),),
        "Cross-asset repricing",
        "Gold reversed",
        "DXY expanded",
        "Yields rose",
        ("Liquidity context mattered",),
        3.5,
        False,
        True,
        ("event-study-001",),
    )


def validated_knowledge(*, reviewed_at: datetime = NOW) -> KnowledgeObject:
    return KnowledgeObject(
        "knowledge-001",
        3,
        "Validated real-yield context",
        KnowledgeCategory.REAL_YIELDS,
        "Validated historical relationship with known exceptions.",
        ("official-source",),
        0.8,
        0.8,
        "Backtested and reviewed.",
        reviewed_at,
        timedelta(days=90),
        KnowledgeStatus.VALIDATED,
        ("study-001",),
        ("exception-001",),
    )


def suggestion() -> LearningRecommendation:
    confidence = LearningConfidence(0.6, 0.2, 0.8, 0.9, 0.5)
    statistics = EdgeStatistics(("discount",), 50, 30, 20, 0.6, confidence)
    return LearningRecommendation(
        "suggestion-001",
        "Current location weight",
        "Test a higher location weight out of sample.",
        ("study-001",),
        statistics,
        "May improve filtering.",
        "Could overfit.",
        confidence,
    )


def reasoning_input(
    *,
    items: tuple[Evidence, ...] | None = None,
    knowledge: tuple[KnowledgeObject, ...] | None = None,
    state_time: datetime = NOW,
) -> ReasoningInput:
    event = historical_event()
    research = ResearchArtifact(
        "research-001",
        "learning-001",
        ResearchArtifactKind.HYPOTHESIS,
        "Could yields explain the move?",
        "Requires validation.",
        KnowledgeLevel.WORKING_HYPOTHESIS,
    )
    return ReasoningInput(
        "reasoning-001",
        MarketState(
            "state-001",
            "XAUUSD",
            state_time,
            timedelta(minutes=15),
            3350.0,
            RangeLocation.DISCOUNT,
            "LONDON_NEW_YORK_OVERLAP",
            "ELEVATED",
            "Gold is trading in discount after a liquidity event.",
            ("The move may be temporary position covering.",),
            "reviewed-market-state",
        ),
        items if items is not None else complete_evidence(),
        knowledge if knowledge is not None else (validated_knowledge(),),
        (HistoricalSimilarity(event, 0.75, "Comparable yield repricing", ("study-001",)),),
        (research,),
        (suggestion(),),
    )


class ReasoningEngineTests(unittest.TestCase):
    def setUp(self) -> None:
        self.audit = RecordingReasoningAudit()
        evaluator = EvidenceDecisionEngine(EvidencePolicy(), RecordingEvidenceAudit())
        self.engine = InstitutionalReasoningEngine(ReasoningPolicy(), evaluator, self.audit)

    def test_complete_chain_returns_explained_buy_attention(self) -> None:
        decision = self.engine.evaluate(reasoning_input(), NOW)
        self.assertEqual(decision.recommendation, Recommendation.BUY_SETUPS_ONLY)
        self.assertEqual(decision.reliability, 80)
        self.assertEqual(tuple(stage.stage for stage in decision.stages), tuple(ReasoningStage))
        self.assertTrue(all(stage.evidence_ids for stage in decision.stages[:6]))
        self.assertIn("favors BUY attention", decision.what_is_happening)
        self.assertTrue(decision.alternative_explanations)
        self.assertTrue(decision.historical_similarities)
        self.assertTrue(any("requiring approval" in value for value in decision.what_would_improve))
        self.assertEqual(self.audit.paths, [decision])

    def test_no_validated_knowledge_downgrades_to_no_opinion(self) -> None:
        decision = self.engine.evaluate(reasoning_input(knowledge=()), NOW)
        self.assertEqual(decision.recommendation, Recommendation.NO_OPINION)
        self.assertEqual(decision.reliability, 0)
        self.assertTrue(any("validated knowledge" in item for item in decision.missing_evidence))

    def test_incomplete_execution_chain_returns_wait_and_names_missing_stages(self) -> None:
        partial = (evidence(EvidenceKind.MACRO), evidence(EvidenceKind.MARKET_BIAS))
        decision = self.engine.evaluate(reasoning_input(items=partial), NOW)
        self.assertEqual(decision.recommendation, Recommendation.WAIT)
        self.assertTrue(any("LIQUIDITY" in item for item in decision.missing_evidence))
        self.assertEqual(decision.stages[3].stage, ReasoningStage.LIQUIDITY)

    def test_expired_market_state_forces_no_opinion(self) -> None:
        decision = self.engine.evaluate(
            reasoning_input(state_time=NOW - timedelta(minutes=15)), NOW
        )
        self.assertEqual(decision.recommendation, Recommendation.NO_OPINION)
        self.assertTrue(any("Market state expired" in item for item in decision.missing_evidence))

    def test_expired_knowledge_is_reported_and_not_used(self) -> None:
        expired = validated_knowledge(reviewed_at=NOW - timedelta(days=91))
        decision = self.engine.evaluate(reasoning_input(knowledge=(expired,)), NOW)
        self.assertEqual(decision.recommendation, Recommendation.NO_OPINION)
        self.assertTrue(any("due for review" in item for item in decision.missing_evidence))

    def test_reasoning_mistakes_are_permanently_auditable(self) -> None:
        mistake = ReasoningMistake(
            "mistake-001",
            "reasoning-001",
            NOW,
            ReasoningMistakeKind.MISSED_CONTRADICTION,
            "DXY evidence was omitted.",
            ("audit-001",),
            "Test mandatory cross-asset contradiction checks.",
        )
        self.engine.record_mistake(mistake)
        self.assertEqual(self.audit.mistakes, [mistake])

    def test_path_audit_failure_makes_reasoning_unavailable(self) -> None:
        evaluator = EvidenceDecisionEngine(EvidencePolicy(), RecordingEvidenceAudit())
        engine = InstitutionalReasoningEngine(ReasoningPolicy(), evaluator, FailingReasoningAudit())
        with self.assertRaisesRegex(DecisionEvaluationError, "path audit failed"):
            engine.evaluate(reasoning_input(), NOW)

    def test_naive_evaluation_time_is_rejected(self) -> None:
        with self.assertRaisesRegex(DecisionEvaluationError, "timezone-aware"):
            self.engine.evaluate(reasoning_input(), datetime(2026, 8, 5, 12))


class ReasoningDomainTests(unittest.TestCase):
    def test_market_state_and_similarity_validate_lifecycle(self) -> None:
        with self.assertRaises(ValueError):
            MarketState(
                "state",
                "XAUUSD",
                NOW,
                timedelta(0),
                1,
                RangeLocation.DISCOUNT,
                "session",
                "normal",
                "summary",
                (),
                "source",
            )
        with self.assertRaises(ValueError):
            HistoricalSimilarity(historical_event(), 1.1, "", ())

    def test_reasoning_policy_rejects_invalid_threshold(self) -> None:
        with self.assertRaises(ValueError):
            ReasoningPolicy(minimum_reliable_evidence_weight=1.1)

    def test_mistake_requires_evidence_and_correction(self) -> None:
        with self.assertRaises(ValueError):
            ReasoningMistake(
                "mistake",
                "reasoning",
                NOW,
                ReasoningMistakeKind.DATA_QUALITY,
                "bad data",
                (),
                "",
            )


class ReasoningInfrastructureTests(unittest.TestCase):
    def test_json_audit_stores_complete_path_and_mistake(self) -> None:
        with TemporaryDirectory() as directory:
            path = Path(directory) / "reasoning.jsonl"
            audit = JsonLinesReasoningAudit(path)
            evaluator = EvidenceDecisionEngine(EvidencePolicy(), RecordingEvidenceAudit())
            engine = InstitutionalReasoningEngine(ReasoningPolicy(), evaluator, audit)
            decision = engine.evaluate(reasoning_input(), NOW)
            mistake = ReasoningMistake(
                "mistake-001",
                decision.reasoning_id,
                NOW,
                ReasoningMistakeKind.PROCESS_VIOLATION,
                "Review discovered a missing alternative.",
                ("review-001",),
                "Add a regression scenario.",
            )
            engine.record_mistake(mistake)
            records = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
        payload = reasoning_decision_to_json(decision)
        self.assertEqual(payload["contract_version"], "4.0.0")
        self.assertEqual(
            [record["event"] for record in records],
            [
                "reasoning_path",
                "reasoning_mistake",
            ],
        )
        self.assertEqual(len(records[0]["payload"]["decision"]["stages"]), 9)


if __name__ == "__main__":
    unittest.main()
