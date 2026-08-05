"""Version 4 institutional reasoning inputs, paths, decisions, and mistakes."""

from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import StrEnum

from .context_models import MarketContext
from .evidence_models import Evidence, Recommendation
from .knowledge_models import HistoricalEvent, KnowledgeObject
from .learning_models import LearningRecommendation, ResearchArtifact
from .macro_models import MacroAssessment, MacroContext
from .models import RangeLocation


class ReasoningStage(StrEnum):
    MACRO = "MACRO"
    BIAS = "BIAS"
    LOCATION = "LOCATION"
    LIQUIDITY = "LIQUIDITY"
    MOMENTUM = "MOMENTUM"
    SMC = "SMC"
    CONTRADICTIONS = "CONTRADICTIONS"
    TRADE_QUALITY = "TRADE_QUALITY"
    RECOMMENDATION = "RECOMMENDATION"


class StageStatus(StrEnum):
    COMPLETE = "COMPLETE"
    MISSING = "MISSING"
    CONTRADICTED = "CONTRADICTED"


class ReasoningMistakeKind(StrEnum):
    MISSING_EVIDENCE = "MISSING_EVIDENCE"
    MISWEIGHTED_EVIDENCE = "MISWEIGHTED_EVIDENCE"
    MISSED_CONTRADICTION = "MISSED_CONTRADICTION"
    BAD_HISTORICAL_ANALOGY = "BAD_HISTORICAL_ANALOGY"
    DATA_QUALITY = "DATA_QUALITY"
    PROCESS_VIOLATION = "PROCESS_VIOLATION"


@dataclass(frozen=True, slots=True)
class MarketState:
    state_id: str
    symbol: str
    captured_at: datetime
    time_to_live: timedelta
    price: float
    location: RangeLocation
    session: str
    volatility_regime: str
    summary: str
    alternative_explanations: tuple[str, ...]
    source: str

    def __post_init__(self) -> None:
        if self.captured_at.tzinfo is None or self.time_to_live <= timedelta(0):
            raise ValueError("market state requires valid timezone-aware lifecycle")
        if self.price <= 0:
            raise ValueError("market state price must be positive")
        required = (self.state_id, self.symbol, self.session, self.summary, self.source)
        if any(not value.strip() for value in required):
            raise ValueError("market state identity and context are required")

    def is_expired(self, evaluated_at: datetime) -> bool:
        if evaluated_at.tzinfo is None:
            raise ValueError("market-state evaluation time must be timezone-aware")
        return evaluated_at >= self.captured_at + self.time_to_live


@dataclass(frozen=True, slots=True)
class HistoricalSimilarity:
    event: HistoricalEvent
    similarity: float
    reasoning: str
    evidence_references: tuple[str, ...]

    def __post_init__(self) -> None:
        if not 0 <= self.similarity <= 1:
            raise ValueError("historical similarity must be between 0 and 1")
        if not self.reasoning.strip() or not self.evidence_references:
            raise ValueError("historical similarity requires reasoning and evidence")


@dataclass(frozen=True, slots=True)
class ReasoningInput:
    reasoning_id: str
    market_state: MarketState
    evidence: tuple[Evidence, ...]
    knowledge: tuple[KnowledgeObject, ...]
    historical_context: tuple[HistoricalSimilarity, ...]
    research: tuple[ResearchArtifact, ...]
    learning_suggestions: tuple[LearningRecommendation, ...]
    context: MarketContext | None = None
    macro_context: MacroContext | None = None
    macro_assessment: MacroAssessment | None = None

    def __post_init__(self) -> None:
        if not self.reasoning_id.strip():
            raise ValueError("reasoning_id is required")
        if self.context is not None and not self.context.is_valid(self.market_state.captured_at):
            raise ValueError("context provided to reasoning_input must be valid and unexpired")
        if self.macro_context is not None and not self.macro_context.is_valid(self.market_state.captured_at):
            raise ValueError("macro_context provided to reasoning_input must be valid and unexpired")



@dataclass(frozen=True, slots=True)
class StageReasoning:
    stage: ReasoningStage
    status: StageStatus
    explanation: str
    evidence_ids: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ReasoningDecision:
    reasoning_id: str
    recommendation: Recommendation
    trade_quality: int
    reliability: int
    what_is_happening: str
    why: tuple[str, ...]
    supporting_evidence: tuple[str, ...]
    contradicting_evidence: tuple[str, ...]
    missing_evidence: tuple[str, ...]
    alternative_explanations: tuple[str, ...]
    historical_similarities: tuple[str, ...]
    what_would_invalidate: tuple[str, ...]
    what_would_improve: tuple[str, ...]
    stages: tuple[StageReasoning, ...]
    evaluated_at: datetime
    policy_version: str
    contract_version: str


@dataclass(frozen=True, slots=True)
class ReasoningMistake:
    mistake_id: str
    reasoning_id: str
    recorded_at: datetime
    kind: ReasoningMistakeKind
    description: str
    evidence_references: tuple[str, ...]
    corrective_hypothesis: str

    def __post_init__(self) -> None:
        if self.recorded_at.tzinfo is None:
            raise ValueError("reasoning mistake time must be timezone-aware")
        required = (
            self.mistake_id,
            self.reasoning_id,
            self.description,
            self.corrective_hypothesis,
        )
        if any(not value.strip() for value in required) or not self.evidence_references:
            raise ValueError("reasoning mistakes require context, evidence, and correction")
