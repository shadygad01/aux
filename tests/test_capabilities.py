import unittest
from datetime import UTC, datetime, timedelta

from capabilities.collection import (
    CollectionBatch,
    CollectionCapability,
    CollectionRequest,
    RawDatum,
)
from capabilities.contracts import HealthState
from capabilities.decision import DecisionCapability, OfficialDecision
from capabilities.evidence import EvidenceCapability
from capabilities.knowledge import KnowledgeCapability
from capabilities.learning import LearningCapability
from capabilities.monitoring import MonitoringCapability
from capabilities.normalization import NormalizationCapability
from capabilities.publishing import PublicationReceipt, PublishingCapability
from capabilities.reasoning import ReasoningCapability
from capabilities.research import ResearchCapability
from packages.application import TrustAssurance
from packages.domain import (
    AttentionBias,
    ComprehensionVerdict,
    CritiqueAssessment,
    CritiqueStage,
    CurrentMarketState,
    DecisionCritique,
    DecisionExplanation,
    DecisionOutcome,
    EdgeStatistics,
    Evidence,
    EvidenceDecision,
    ExplainedConcept,
    ExplainedStatistic,
    ExplanationTrace,
    HorizonBias,
    InstitutionalQuestion,
    KnowledgeAnswer,
    KnowledgeObject,
    LearningConfidence,
    LearningRecommendation,
    LearningRecord,
    MarketRegime,
    MarketRegimeContext,
    MarketSnapshot,
    MarketState,
    OutcomeClassification,
    RangeLocation,
    RankedSource,
    ReasoningComprehensionReview,
    ReasoningDecision,
    ReasoningInput,
    ReasoningStage,
    Recommendation,
    RecommendationTrust,
    RegimeInterpretation,
    ResearchArtifact,
    StageReasoning,
    StageStatus,
    TradingHorizon,
)
from packages.infrastructure import InMemoryCapabilityTelemetry

NOW = datetime(2026, 8, 5, 12, tzinfo=UTC)


class FakeCollector:
    def collect(self, request: CollectionRequest) -> CollectionBatch:
        return CollectionBatch(request, (RawDatum("price", "3350.5", NOW, "fake"),), NOW)


class FakeKnowledgeService:
    def answer(self, question: InstitutionalQuestion) -> KnowledgeAnswer:
        return KnowledgeAnswer(question, "No records.", (), (), ())

    def due_for_review(self, evaluated_at: datetime) -> tuple[KnowledgeObject, ...]:
        return ()

    def rank_sources(self, evaluated_at: datetime) -> tuple[RankedSource, ...]:
        return ()


class FakeEvidenceEvaluator:
    def evaluate(
        self,
        evidence: tuple[Evidence, ...],
        evaluated_at: datetime,
        state: CurrentMarketState,
        interpretations: tuple[RegimeInterpretation, ...],
    ) -> EvidenceDecision:
        return EvidenceDecision(
            Recommendation.NO_OPINION,
            0,
            0,
            (),
            (),
            (),
            ("Add evidence",),
            (),
            evaluated_at,
            "policy",
            "3.0.0",
        )


class FakeReasoner:
    def evaluate(
        self,
        value: ReasoningInput,
        state: CurrentMarketState,
        interpretations: tuple[RegimeInterpretation, ...],
        evaluated_at: datetime,
    ) -> ReasoningDecision:
        return reasoning_decision()


class FakeLearningService:
    def record(self, record: LearningRecord) -> ResearchArtifact | None:
        return None


class FakeResearchService:
    def evaluate_edge(
        self,
        records: tuple[LearningRecord, ...],
        evidence_combination: tuple[str, ...],
        evidence_quality: float,
        data_quality: float,
    ) -> EdgeStatistics:
        confidence = LearningConfidence(0, 0, evidence_quality, data_quality, 0)
        return EdgeStatistics(evidence_combination, 0, 0, 0, 0, confidence)

    def propose(
        self,
        recommendation_id: str,
        current_rule: str,
        suggested_improvement: str,
        statistics: EdgeStatistics,
        supporting_evidence: tuple[str, ...],
        expected_impact: str,
        migration_risk: str,
    ) -> LearningRecommendation:
        return LearningRecommendation(
            recommendation_id,
            current_rule,
            suggested_improvement,
            supporting_evidence,
            statistics,
            expected_impact,
            migration_risk,
            statistics.confidence,
        )


class FakePublisher:
    def publish(self, decision: OfficialDecision) -> PublicationReceipt:
        return PublicationReceipt("publication-1", decision.decision_id, NOW, "test")


def learning_record() -> LearningRecord:
    return LearningRecord(
        "record-1",
        "audit-1",
        NOW,
        MarketSnapshot(3350, NOW, "test", "snapshot"),
        (HorizonBias(TradingHorizon.MEDIUM_TERM, AttentionBias.WAIT, "wait"),),
        0,
        RangeLocation.EQUILIBRIUM,
        (),
        0,
        (),
        "uncertain",
        100,
        1.5,
        "ASIA",
        (),
        (),
        (),
        Recommendation.NO_OPINION,
        OutcomeClassification.PENDING,
        None,
        None,
        ("Await outcome.",),
        "Nothing changed yet.",
    )


def reasoning_decision() -> ReasoningDecision:
    stages = tuple(
        StageReasoning(stage, StageStatus.COMPLETE, "complete", ()) for stage in ReasoningStage
    )
    return ReasoningDecision(
        "reasoning-1",
        Recommendation.WAIT,
        70,
        80,
        "Current evidence favors waiting.",
        (),
        (),
        (),
        (),
        (),
        (),
        ("New evidence",),
        ("Complete missing evidence",),
        stages,
        NOW,
        "policy",
        "4.0.0",
    )


def decision_explanation() -> DecisionExplanation:
    trace = ExplanationTrace("reasoning:macro", "knowledge:1", "evidence:1", "Fact", "source:1")
    return DecisionExplanation(
        Recommendation.WAIT,
        ("Execution evidence is incomplete.",),
        ("The latest reviewed evidence has not confirmed execution.",),
        ("Neither directional side has complete support.",),
        ("WAIT is selected until the named evidence arrives.",),
        ("evidence:1",),
        ("Directional confirmation is weak.",),
        ("Liquidity confirmation is missing.",),
        ("Fresh directional evidence would replace WAIT.",),
        (trace,),
    )


def decision_critique() -> DecisionCritique:
    assessment = CritiqueAssessment(
        "No ignored evidence identified in the reviewed set.",
        "No overweighted evidence identified.",
        "Liquidity may be underweighted.",
        "Uncertainty remains material.",
        "Conflicting directional evidence exists.",
        "An alternative path retains NO OPINION.",
        ("evidence:1",),
    )
    return DecisionCritique(
        "critique-1",
        "decision-1",
        1,
        CritiqueStage.PRE_PUBLICATION,
        DecisionOutcome.PENDING,
        assessment,
        NOW,
        "critic-v1",
    )


def recommendation_trust() -> RecommendationTrust:
    return TrustAssurance.issue(
        decision_explanation(),
        80,
        20,
        "policy",
        '{"canonical":"input"}',
        "calculation:1",
        "audit:1",
        NOW,
    )


def market_regime() -> MarketRegimeContext:
    return MarketRegimeContext(
        "regime-1",
        MarketRegime.RANGING,
        (MarketRegime.RANGING, MarketRegime.LOW_VOLATILITY),
        NOW,
        timedelta(minutes=15),
        80,
        "Range boundaries remain intact.",
        ("regime-evidence:1",),
        "test",
        "regime-policy",
    )


def current_state() -> CurrentMarketState:
    return CurrentMarketState(
        "current-state-1",
        "XAUUSD",
        NOW,
        timedelta(minutes=15),
        market_regime(),
        "Macro neutral.",
        (HorizonBias(TradingHorizon.MEDIUM_TERM, AttentionBias.WAIT, "Mixed context."),),
        "Low volatility.",
        "Range liquidity intact.",
        "Momentum neutral.",
        "No active high-impact news.",
        80,
        20,
        ("state-evidence:1",),
        "test",
        "state-policy",
    )


def comprehension_review() -> ReasoningComprehensionReview:
    return ReasoningComprehensionReview(
        "comprehension-1",
        "reasoning-1",
        ComprehensionVerdict.APPROVED,
        "Evidence is incomplete, so the trader should wait.",
        (ExplainedConcept("Liquidity sweep", "Price traded beyond a watched liquidity level."),),
        (
            ExplainedStatistic(
                "Reliability 80", "Four-fifths of weighted support is reliable.", "calc:1"
            ),
        ),
        (),
        "The trader decides whether later execution quality is acceptable.",
        "The platform does not place or manage trades.",
        "institutional-reviewer",
        ("reasoning:1", "calculation:1"),
        NOW,
        "comprehension-v1",
    )


class CapabilityTests(unittest.TestCase):
    def setUp(self) -> None:
        self.telemetry = InMemoryCapabilityTelemetry()

    def test_collection_and_normalization_are_separate_replaceable_capabilities(self) -> None:
        request = CollectionRequest("XAUUSD", NOW)
        collection = CollectionCapability(FakeCollector(), self.telemetry)
        batch = collection.collect(request)
        normalization = NormalizationCapability({"price": "USD_PER_OUNCE"}, self.telemetry)
        normalized = normalization.normalize(batch)
        self.assertEqual(normalized[0].value, 3350.5)
        self.assertEqual(normalized[0].unit, "USD_PER_OUNCE")
        self.assertEqual(collection.health(NOW).state, HealthState.HEALTHY)
        self.assertEqual(normalization.health(NOW).state, HealthState.HEALTHY)

    def test_unconfigured_external_capabilities_report_not_ready(self) -> None:
        collection = CollectionCapability(None, self.telemetry)
        publishing = PublishingCapability(None, self.telemetry)
        self.assertEqual(collection.health(NOW).state, HealthState.NOT_READY)
        self.assertEqual(publishing.health(NOW).state, HealthState.NOT_READY)
        with self.assertRaisesRegex(RuntimeError, "not ready"):
            collection.collect(CollectionRequest("XAUUSD", NOW))

    def test_knowledge_learning_and_research_interfaces_are_independent(self) -> None:
        knowledge = KnowledgeCapability(FakeKnowledgeService(), self.telemetry)
        learning = LearningCapability(FakeLearningService(), self.telemetry)
        research = ResearchCapability(FakeResearchService(), self.telemetry)
        answer = knowledge.answer(InstitutionalQuestion.GOLD_IGNORED_DXY)
        artifact = learning.learn(learning_record())
        statistics = research.evaluate_edge((), ("discount",), 1, 1)
        self.assertEqual(answer.result_ids, ())
        self.assertIsNone(artifact)
        self.assertEqual(statistics.sample_size, 0)

    def test_evidence_and_reasoning_capabilities_use_replaceable_ports(self) -> None:
        evidence_capability = EvidenceCapability(FakeEvidenceEvaluator(), self.telemetry)
        evidence_result = evidence_capability.evaluate((), current_state(), (), NOW)
        reasoning_value = ReasoningInput(
            "reasoning-1",
            MarketState(
                "state-1",
                "XAUUSD",
                NOW,
                timedelta(minutes=5),
                3350,
                RangeLocation.EQUILIBRIUM,
                "ASIA",
                "NORMAL",
                "No directional context.",
                (),
                "test",
            ),
            (),
            (),
            (),
            (),
            (),
        )
        reasoning_capability = ReasoningCapability(FakeReasoner(), self.telemetry)
        reasoning_result = reasoning_capability.reason(reasoning_value, current_state(), (), NOW)
        self.assertEqual(evidence_result.recommendation, Recommendation.NO_OPINION)
        self.assertEqual(reasoning_result.reasoning_id, "reasoning-1")

    def test_decision_and_publishing_do_not_mutate_reasoning(self) -> None:
        decision_capability = DecisionCapability(self.telemetry)
        official = decision_capability.decide(
            "decision-1",
            reasoning_decision(),
            decision_explanation(),
            decision_critique(),
            recommendation_trust(),
            current_state(),
            comprehension_review(),
        )
        publishing = PublishingCapability(FakePublisher(), self.telemetry)
        receipt = publishing.publish(official)
        self.assertEqual(official.recommendation, Recommendation.WAIT)
        self.assertEqual(receipt.decision_id, official.decision_id)

    def test_monitoring_aggregates_capability_owned_health(self) -> None:
        providers = (
            CollectionCapability(FakeCollector(), self.telemetry),
            PublishingCapability(None, self.telemetry),
        )
        monitoring = MonitoringCapability(providers, self.telemetry)
        health = monitoring.check(NOW)
        self.assertEqual(health.state, HealthState.NOT_READY)
        self.assertEqual(len(health.capabilities), 2)

    def test_every_operation_emits_owned_metrics_or_logs(self) -> None:
        CollectionCapability(FakeCollector(), self.telemetry).collect(
            CollectionRequest("XAUUSD", NOW)
        )
        self.assertTrue(self.telemetry.metrics)
        self.assertTrue(self.telemetry.logs)


if __name__ == "__main__":
    unittest.main()
