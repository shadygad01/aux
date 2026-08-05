"""Institutional knowledge, source, event, pattern, and question contracts."""

from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import StrEnum


class KnowledgeCategory(StrEnum):
    MACRO_ECONOMICS = "MACRO_ECONOMICS"
    FEDERAL_RESERVE = "FEDERAL_RESERVE"
    INTEREST_RATES = "INTEREST_RATES"
    INFLATION = "INFLATION"
    EMPLOYMENT = "EMPLOYMENT"
    GDP = "GDP"
    RETAIL_SALES = "RETAIL_SALES"
    PMI = "PMI"
    MANUFACTURING = "MANUFACTURING"
    CONSUMER_SPENDING = "CONSUMER_SPENDING"
    BOND_MARKET = "BOND_MARKET"
    US10Y = "US10Y"
    US02Y = "US02Y"
    REAL_YIELDS = "REAL_YIELDS"
    YIELD_CURVE = "YIELD_CURVE"
    DOLLAR = "DOLLAR"
    DXY = "DXY"
    DOLLAR_LIQUIDITY = "DOLLAR_LIQUIDITY"
    CENTRAL_BANKS = "CENTRAL_BANKS"
    GOLD = "GOLD"
    PHYSICAL_DEMAND = "PHYSICAL_DEMAND"
    ETF_FLOWS = "ETF_FLOWS"
    CENTRAL_BANK_PURCHASES = "CENTRAL_BANK_PURCHASES"
    FUTURES_POSITIONING = "FUTURES_POSITIONING"
    SESSION_BEHAVIOUR = "SESSION_BEHAVIOUR"
    ASIAN_SESSION = "ASIAN_SESSION"
    LONDON_SESSION = "LONDON_SESSION"
    NEW_YORK_SESSION = "NEW_YORK_SESSION"
    SESSION_OVERLAPS = "SESSION_OVERLAPS"
    MARKET_STRUCTURE = "MARKET_STRUCTURE"
    SMC = "SMC"
    PREMIUM = "PREMIUM"
    DISCOUNT = "DISCOUNT"
    LIQUIDITY = "LIQUIDITY"
    SWEEP = "SWEEP"
    ORDER_BLOCKS = "ORDER_BLOCKS"
    FAIR_VALUE_GAP = "FAIR_VALUE_GAP"
    REVERSAL_MODELS = "REVERSAL_MODELS"
    CANDLESTICK_BEHAVIOUR = "CANDLESTICK_BEHAVIOUR"
    RISK = "RISK"
    HISTORICAL_BEHAVIOUR = "HISTORICAL_BEHAVIOUR"


class KnowledgeStatus(StrEnum):
    OBSERVATION = "OBSERVATION"
    HYPOTHESIS = "HYPOTHESIS"
    VALIDATED = "VALIDATED"
    INSTITUTIONAL_RULE = "INSTITUTIONAL_RULE"
    DEPRECATED = "DEPRECATED"


class SourceType(StrEnum):
    OFFICIAL = "OFFICIAL"
    INSTITUTIONAL = "INSTITUTIONAL"
    ACADEMIC = "ACADEMIC"
    PROFESSIONAL = "PROFESSIONAL"
    COMMUNITY = "COMMUNITY"
    EXPERIMENTAL = "EXPERIMENTAL"


class InstitutionalQuestion(StrEnum):
    GOLD_IGNORED_DXY = "GOLD_IGNORED_DXY"
    YIELDS_DOMINATED_GOLD = "YIELDS_DOMINATED_GOLD"
    STRONGEST_MACRO_REVERSALS = "STRONGEST_MACRO_REVERSALS"
    PREMIUM_FAILURE_RATE = "PREMIUM_FAILURE_RATE"
    SWEEP_FAILURE_RATE = "SWEEP_FAILURE_RATE"


@dataclass(frozen=True, slots=True)
class SourceProfile:
    source_id: str
    name: str
    source_type: SourceType
    reliability: float
    authority: float
    historical_accuracy: float
    bias_risk: float
    transparency: float
    last_review: datetime
    review_interval: timedelta
    evidence_references: tuple[str, ...]

    def __post_init__(self) -> None:
        if self.last_review.tzinfo is None:
            raise ValueError("source last_review must be timezone-aware")
        if self.review_interval <= timedelta(0):
            raise ValueError("source review_interval must be positive")
        for value in (
            self.reliability,
            self.authority,
            self.historical_accuracy,
            self.bias_risk,
            self.transparency,
        ):
            if not 0 <= value <= 1:
                raise ValueError("source-quality values must be between 0 and 1")
        if not self.source_id.strip() or not self.name.strip() or not self.evidence_references:
            raise ValueError("source requires identity and ranking evidence")

    def freshness(self, evaluated_at: datetime) -> float:
        if evaluated_at.tzinfo is None:
            raise ValueError("source freshness time must be timezone-aware")
        age = evaluated_at - self.last_review
        if age <= timedelta(0):
            return 1.0
        return max(0.0, 1.0 - (age / self.review_interval))


@dataclass(frozen=True, slots=True)
class RankedSource:
    source_id: str
    score: float
    freshness: float
    rank: int


@dataclass(frozen=True, slots=True)
class KnowledgeObject:
    knowledge_id: str
    revision: int
    title: str
    category: KnowledgeCategory
    description: str
    source_ids: tuple[str, ...]
    reliability: float
    confidence: float
    historical_validation: str
    last_review: datetime
    review_interval: timedelta
    status: KnowledgeStatus
    supporting_evidence: tuple[str, ...]
    contradicting_evidence: tuple[str, ...]

    def __post_init__(self) -> None:
        if self.revision <= 0:
            raise ValueError("knowledge revision must be positive")
        if self.last_review.tzinfo is None or self.review_interval <= timedelta(0):
            raise ValueError("knowledge review schedule must be valid and timezone-aware")
        if not 0 <= self.reliability <= 1 or not 0 <= self.confidence <= 1:
            raise ValueError("knowledge reliability and confidence must be between 0 and 1")
        required_text = (
            self.knowledge_id,
            self.title,
            self.description,
            self.historical_validation,
        )
        if any(not value.strip() for value in required_text):
            raise ValueError("knowledge identity, description, and validation are required")
        if not self.source_ids or not self.supporting_evidence:
            raise ValueError("knowledge is not accepted without sources and supporting evidence")

    def review_due(self, evaluated_at: datetime) -> bool:
        if evaluated_at.tzinfo is None:
            raise ValueError("knowledge review time must be timezone-aware")
        return evaluated_at >= self.last_review + self.review_interval


@dataclass(frozen=True, slots=True)
class EventMoment:
    timestamp: datetime
    description: str

    def __post_init__(self) -> None:
        if self.timestamp.tzinfo is None or not self.description.strip():
            raise ValueError("event moments require time and description")


@dataclass(frozen=True, slots=True)
class HistoricalEvent:
    event_id: str
    title: str
    categories: tuple[KnowledgeCategory, ...]
    timeline: tuple[EventMoment, ...]
    market_reaction: str
    gold_behaviour: str
    dollar_behaviour: str
    yield_behaviour: str
    lessons_learned: tuple[str, ...]
    gold_reaction_percent: float
    gold_ignored_dxy: bool
    yields_dominated_gold: bool
    evidence_references: tuple[str, ...]

    def __post_init__(self) -> None:
        if not self.event_id.strip() or not self.title.strip() or not self.timeline:
            raise ValueError("historical events require identity and timeline")
        if not self.lessons_learned or not self.evidence_references:
            raise ValueError("historical events require lessons and evidence")


@dataclass(frozen=True, slots=True)
class PatternKnowledge:
    pattern_id: str
    title: str
    status: KnowledgeStatus
    conditions: tuple[str, ...]
    sample_size: int
    win_rate: float
    failure_rate: float
    known_weaknesses: tuple[str, ...]
    best_sessions: tuple[str, ...]
    worst_sessions: tuple[str, ...]
    evidence_references: tuple[str, ...]
    last_review: datetime
    review_interval: timedelta

    def __post_init__(self) -> None:
        if self.sample_size < 0:
            raise ValueError("pattern sample_size must be non-negative")
        if not 0 <= self.win_rate <= 1 or not 0 <= self.failure_rate <= 1:
            raise ValueError("pattern rates must be between 0 and 1")
        if self.win_rate + self.failure_rate > 1:
            raise ValueError("pattern win and failure rates cannot exceed one")
        if self.last_review.tzinfo is None or self.review_interval <= timedelta(0):
            raise ValueError("pattern review schedule must be valid")
        if not self.conditions or not self.evidence_references:
            raise ValueError("patterns require conditions and evidence")


@dataclass(frozen=True, slots=True)
class KnowledgeAnswer:
    question: InstitutionalQuestion
    summary: str
    result_ids: tuple[str, ...]
    statistics: tuple[str, ...]
    evidence_references: tuple[str, ...]
