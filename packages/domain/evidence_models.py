"""Version 3 expiring evidence and four-output decision contracts."""

from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import StrEnum


class EvidenceKind(StrEnum):
    MACRO = "MACRO"
    MARKET_BIAS = "MARKET_BIAS"
    LOCATION = "LOCATION"
    LIQUIDITY_SWEEP = "LIQUIDITY_SWEEP"
    MACD = "MACD"
    REVERSAL_CANDLE = "REVERSAL_CANDLE"
    NEWS = "NEWS"
    ORDER_BLOCK = "ORDER_BLOCK"
    FAIR_VALUE_GAP = "FAIR_VALUE_GAP"
    CHANGE_OF_CHARACTER = "CHANGE_OF_CHARACTER"
    OTHER = "OTHER"


class EvidenceDirection(StrEnum):
    BUY = "BUY"
    SELL = "SELL"
    NEUTRAL = "NEUTRAL"


class Recommendation(StrEnum):
    BUY_SETUPS_ONLY = "BUY_SETUPS_ONLY"
    SELL_SETUPS_ONLY = "SELL_SETUPS_ONLY"
    WAIT = "WAIT"
    NO_OPINION = "NO_OPINION"


@dataclass(frozen=True, slots=True)
class Evidence:
    evidence_id: str
    kind: EvidenceKind
    direction: EvidenceDirection
    observed_at: datetime
    time_to_live: timedelta
    strength: float
    reliability: float
    importance: float
    historical_performance: float
    confidence: float
    rationale: str
    source: str
    forces_wait: bool = False

    def __post_init__(self) -> None:
        if self.observed_at.tzinfo is None:
            raise ValueError("evidence observed_at must be timezone-aware")
        if self.time_to_live <= timedelta(0):
            raise ValueError("evidence time_to_live must be positive")
        for name, value in (
            ("strength", self.strength),
            ("reliability", self.reliability),
            ("importance", self.importance),
            ("historical_performance", self.historical_performance),
            ("confidence", self.confidence),
        ):
            if not 0 <= value <= 1:
                raise ValueError(f"evidence {name} must be between 0 and 1")
        if not self.evidence_id.strip() or not self.rationale.strip() or not self.source.strip():
            raise ValueError("evidence id, rationale, and source are required")

    def freshness(self, evaluated_at: datetime) -> float:
        """Linear, reproducible decay from 1 at observation to 0 at expiry."""
        if evaluated_at.tzinfo is None:
            raise ValueError("freshness evaluation time must be timezone-aware")
        age = evaluated_at - self.observed_at
        if age <= timedelta(0):
            return 1.0
        return max(0.0, 1.0 - (age / self.time_to_live))

    @property
    def expires_at(self) -> datetime:
        return self.observed_at + self.time_to_live


@dataclass(frozen=True, slots=True)
class WeightedEvidence:
    evidence_id: str
    kind: EvidenceKind
    direction: EvidenceDirection
    freshness: float
    effective_weight: float
    expires_at: datetime
    rationale: str


@dataclass(frozen=True, slots=True)
class EvidenceDecision:
    recommendation: Recommendation
    trade_quality: int
    confidence: int
    why: tuple[str, ...]
    why_not: tuple[str, ...]
    missing: tuple[str, ...]
    what_would_change: tuple[str, ...]
    evidence: tuple[WeightedEvidence, ...]
    evaluated_at: datetime
    policy_version: str
    contract_version: str
