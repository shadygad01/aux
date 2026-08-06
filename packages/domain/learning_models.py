"""Immutable learning records, knowledge levels, and research outputs."""

from dataclasses import dataclass
from datetime import datetime
from enum import IntEnum, StrEnum
from math import isfinite, prod

from .evidence_models import Recommendation
from .models import RangeLocation
from .trading_models import HorizonBias, OutcomeClassification


class KnowledgeLevel(IntEnum):
    IMMUTABLE_PRINCIPLE = 1
    VALIDATED_RULE = 2
    WORKING_HYPOTHESIS = 3
    EXPERIMENTAL = 4
    REJECTED = 5


class ResearchArtifactKind(StrEnum):
    HYPOTHESIS = "HYPOTHESIS"
    SUPPORTING_EVIDENCE = "SUPPORTING_EVIDENCE"


class RecommendationStatus(StrEnum):
    PROPOSED = "PROPOSED"
    VALIDATION_REQUIRED = "VALIDATION_REQUIRED"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


@dataclass(frozen=True, slots=True)
class MarketSnapshot:
    xauusd_price: float
    captured_at: datetime
    source: str
    reference: str

    def __post_init__(self) -> None:
        if self.captured_at.tzinfo is None:
            raise ValueError("market snapshot timestamp must be timezone-aware")
        if (
            not isfinite(self.xauusd_price)
            or self.xauusd_price <= 0
            or not self.source.strip()
            or not self.reference.strip()
        ):
            raise ValueError("market snapshot requires positive price, source, and reference")


@dataclass(frozen=True, slots=True)
class LearningRecord:
    record_id: str
    decision_audit_id: str
    timestamp: datetime
    market_snapshot: MarketSnapshot
    biases: tuple[HorizonBias, ...]
    trade_quality: int
    location: RangeLocation
    liquidity: tuple[str, ...]
    macd: float
    news: tuple[str, ...]
    macro: str
    dxy: float
    real_yields: float
    session: str
    smc_evidence: tuple[str, ...]
    supporting_evidence: tuple[str, ...]
    contradicting_evidence: tuple[str, ...]
    decision: Recommendation
    outcome: OutcomeClassification
    maximum_favorable_excursion: float | None
    maximum_adverse_excursion: float | None
    learning_notes: tuple[str, ...]
    what_changed_after: str
    opportunity_id: str | None = None

    def __post_init__(self) -> None:
        if self.timestamp.tzinfo is None:
            raise ValueError("learning record timestamp must be timezone-aware")
        if not 0 <= self.trade_quality <= 100:
            raise ValueError("trade quality must be between 0 and 100")
        numeric_values = (self.macd, self.dxy, self.real_yields)
        excursions = (self.maximum_favorable_excursion, self.maximum_adverse_excursion)
        if not all(isfinite(value) for value in numeric_values):
            raise ValueError("market measurements must be finite")
        if any(value is not None and (not isfinite(value) or value < 0) for value in excursions):
            raise ValueError("excursions must be finite non-negative values or null")
        required_text = (
            self.record_id,
            self.decision_audit_id,
            self.macro,
            self.session,
            self.what_changed_after,
        )
        if (
            any(not value.strip() for value in required_text)
            or not self.learning_notes
            or not self.biases
        ):
            raise ValueError("learning record requires traceable identifiers, context, and notes")


@dataclass(frozen=True, slots=True)
class KnowledgeConcept:
    concept_id: str
    name: str
    level: KnowledgeLevel
    rationale: str
    evidence_references: tuple[str, ...]
    production_eligible: bool
    backtested: bool = False
    forward_tested: bool = False
    approved: bool = False

    def __post_init__(self) -> None:
        if (
            self.level
            in {
                KnowledgeLevel.WORKING_HYPOTHESIS,
                KnowledgeLevel.EXPERIMENTAL,
                KnowledgeLevel.REJECTED,
            }
            and self.production_eligible
        ):
            raise ValueError("unvalidated or rejected knowledge is never production eligible")
        if self.level is KnowledgeLevel.IMMUTABLE_PRINCIPLE and not self.production_eligible:
            raise ValueError("immutable principles must remain production eligible")
        if self.level is KnowledgeLevel.VALIDATED_RULE and not (
            self.backtested and self.forward_tested and self.approved
        ):
            raise ValueError("validated rules require backtest, forward test, and approval")


@dataclass(frozen=True, slots=True)
class LearningConfidence:
    historical_performance: float
    repeatability: float
    evidence_quality: float
    data_quality: float
    sample_size_adequacy: float

    def __post_init__(self) -> None:
        for value in (
            self.historical_performance,
            self.repeatability,
            self.evidence_quality,
            self.data_quality,
            self.sample_size_adequacy,
        ):
            if not 0 <= value <= 1:
                raise ValueError("learning confidence inputs must be between 0 and 1")

    @property
    def score(self) -> int:
        factors = (
            self.historical_performance,
            self.repeatability,
            self.evidence_quality,
            self.data_quality,
            self.sample_size_adequacy,
        )
        return round((prod(factors) ** (1 / len(factors))) * 100)


@dataclass(frozen=True, slots=True)
class ResearchArtifact:
    artifact_id: str
    source_record_id: str
    kind: ResearchArtifactKind
    question: str
    explanation: str
    knowledge_level: KnowledgeLevel


@dataclass(frozen=True, slots=True)
class EdgeStatistics:
    evidence_combination: tuple[str, ...]
    sample_size: int
    winning: int
    losing: int
    win_rate: float
    confidence: LearningConfidence


@dataclass(frozen=True, slots=True)
class LearningRecommendation:
    recommendation_id: str
    current_rule: str
    suggested_improvement: str
    supporting_evidence: tuple[str, ...]
    historical_statistics: EdgeStatistics
    expected_impact: str
    migration_risk: str
    confidence: LearningConfidence
    status: RecommendationStatus = RecommendationStatus.VALIDATION_REQUIRED
    requires_approval: bool = True

    def __post_init__(self) -> None:
        if self.status is RecommendationStatus.APPROVED:
            raise ValueError("learning subsystem cannot mark recommendations approved")
        if not self.requires_approval:
            raise ValueError("every learning recommendation requires approval")
        required_text = (
            self.recommendation_id,
            self.current_rule,
            self.suggested_improvement,
            self.expected_impact,
            self.migration_risk,
        )
        if any(not value.strip() for value in required_text) or not self.supporting_evidence:
            raise ValueError("learning recommendations require complete explainable context")
