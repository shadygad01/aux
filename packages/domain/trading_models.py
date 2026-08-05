"""Immutable trading-constitution evidence and output models."""

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

from .models import DealingRange, LiquidityEvent


class AttentionBias(StrEnum):
    BUY_ONLY = "BUY_ONLY"
    SELL_ONLY = "SELL_ONLY"
    WAIT = "WAIT"


class TradingHorizon(StrEnum):
    LONG_TERM = "LONG_TERM"
    MEDIUM_TERM = "MEDIUM_TERM"
    SCALPING = "SCALPING"


class ExecutionStatus(StrEnum):
    SEARCH_BUY_SETUPS = "SEARCH_BUY_SETUPS"
    SEARCH_SELL_SETUPS = "SEARCH_SELL_SETUPS"
    WAIT = "WAIT"
    PAUSED = "PAUSED"


class NewsEffect(StrEnum):
    SUPPORTS_BUY = "SUPPORTS_BUY"
    SUPPORTS_SELL = "SUPPORTS_SELL"
    REDUCES_CONFIDENCE = "REDUCES_CONFIDENCE"
    REJECTS_SETUP = "REJECTS_SETUP"
    PAUSES_EXECUTION = "PAUSES_EXECUTION"
    FORCE_WAIT = "FORCE_WAIT"


class OutcomeClassification(StrEnum):
    PENDING = "PENDING"
    WINNING = "WINNING"
    LOSING = "LOSING"
    IGNORED = "IGNORED"
    REJECTED = "REJECTED"
    MISSED = "MISSED"
    WAIT = "WAIT"
    FALSE_POSITIVE = "FALSE_POSITIVE"
    FALSE_NEGATIVE = "FALSE_NEGATIVE"


@dataclass(frozen=True, slots=True)
class HorizonBias:
    horizon: TradingHorizon
    bias: AttentionBias
    reasoning: str


@dataclass(frozen=True, slots=True)
class MacroAssessment:
    bias: AttentionBias
    reasoning: str
    supporting_factors: tuple[str, ...]
    contradicting_factors: tuple[str, ...]
    confidence: float

    def __post_init__(self) -> None:
        if not 0 <= self.confidence <= 1:
            raise ValueError("macro confidence must be between 0 and 1")
        if not self.reasoning.strip():
            raise ValueError("macro reasoning is required")


@dataclass(frozen=True, slots=True)
class MomentumAssessment:
    macd_value: float
    histogram: float | None = None
    slope: float | None = None
    crossover_confirmed: bool = False


@dataclass(frozen=True, slots=True)
class SmcAssessment:
    liquidity_event: LiquidityEvent | None
    reversal_candle_confirmed: bool
    change_of_character: bool = False
    order_block: bool = False
    fair_value_gap: bool = False


@dataclass(frozen=True, slots=True)
class NewsAssessment:
    effect: NewsEffect
    why: str
    expected_impact: str
    expected_until: datetime
    confidence: float

    def __post_init__(self) -> None:
        if self.expected_until.tzinfo is None:
            raise ValueError("news expected_until must be timezone-aware")
        if not 0 <= self.confidence <= 1:
            raise ValueError("news confidence must be between 0 and 1")
        if not self.why.strip() or not self.expected_impact.strip():
            raise ValueError("news why and expected impact are required")


@dataclass(frozen=True, slots=True)
class TradingObservation:
    opportunity_id: str
    symbol: str
    execution_horizon: TradingHorizon
    observed_at: datetime
    source: str
    macro: MacroAssessment | None
    horizon_biases: tuple[HorizonBias, ...]
    dealing_range: DealingRange | None
    nearby_liquidity_levels: tuple[str, ...]
    momentum: MomentumAssessment | None
    smc: SmcAssessment | None
    news: tuple[NewsAssessment, ...]

    def __post_init__(self) -> None:
        if self.observed_at.tzinfo is None:
            raise ValueError("observed_at must be timezone-aware")
        if not self.opportunity_id.strip() or not self.source.strip():
            raise ValueError("opportunity_id and source are required")
        horizons = {item.horizon for item in self.horizon_biases}
        if len(horizons) != len(self.horizon_biases):
            raise ValueError("horizon biases must be unique")


@dataclass(frozen=True, slots=True)
class TradingDecision:
    opportunity_id: str
    biases: tuple[HorizonBias, ...]
    trade_quality: int
    execution_status: ExecutionStatus
    reasoning: str
    supporting_factors: tuple[str, ...]
    contradicting_factors: tuple[str, ...]
    missing_evidence: tuple[str, ...]
    next_improvement: str
    last_update: datetime
    policy_version: str
    contract_version: str


@dataclass(frozen=True, slots=True)
class OpportunityOutcome:
    opportunity_id: str
    classification: OutcomeClassification
    recorded_at: datetime
    evidence: str

    def __post_init__(self) -> None:
        if self.recorded_at.tzinfo is None:
            raise ValueError("outcome recorded_at must be timezone-aware")
        if not self.opportunity_id.strip() or not self.evidence.strip():
            raise ValueError("outcome opportunity_id and evidence are required")
