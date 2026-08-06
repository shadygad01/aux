"""Immutable, strongly typed domain models with no infrastructure concerns."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

RANGE_MIDPOINT_RATIO = 0.5


class StructureBias(StrEnum):
    BULLISH = "BULLISH"
    BEARISH = "BEARISH"
    NEUTRAL = "NEUTRAL"


class LiquiditySide(StrEnum):
    BUY_SIDE = "BUY_SIDE"
    SELL_SIDE = "SELL_SIDE"


class RangeLocation(StrEnum):
    PREMIUM = "PREMIUM"
    EQUILIBRIUM = "EQUILIBRIUM"
    DISCOUNT = "DISCOUNT"


class DecisionVerdict(StrEnum):
    BUY = "BUY"
    SELL = "SELL"
    WAIT = "WAIT"


class Confidence(StrEnum):
    NONE = "NONE"
    LOW = "LOW"
    MODERATE = "MODERATE"
    HIGH = "HIGH"


@dataclass(frozen=True, slots=True)
class MarketStructure:
    bias: StructureBias
    break_of_structure: bool
    change_of_character: bool = False


@dataclass(frozen=True, slots=True)
class DealingRange:
    low: float
    high: float
    current_price: float

    def __post_init__(self) -> None:
        if self.high <= self.low:
            raise ValueError("dealing range high must be greater than low")
        if not self.low <= self.current_price <= self.high:
            raise ValueError("current price must be inside the dealing range")

    @property
    def midpoint(self) -> float:
        return self.low + ((self.high - self.low) * RANGE_MIDPOINT_RATIO)

    def location(self, equilibrium_band: float) -> RangeLocation:
        position = (self.current_price - self.low) / (self.high - self.low)
        if position < RANGE_MIDPOINT_RATIO - equilibrium_band:
            return RangeLocation.DISCOUNT
        if position > RANGE_MIDPOINT_RATIO + equilibrium_band:
            return RangeLocation.PREMIUM
        return RangeLocation.EQUILIBRIUM


@dataclass(frozen=True, slots=True)
class LiquidityEvent:
    side: LiquiditySide
    swept: bool
    displacement_confirmed: bool


@dataclass(frozen=True, slots=True)
class MarketObservation:
    symbol: str
    timeframe: str
    observed_at: datetime
    structure: MarketStructure | None
    dealing_range: DealingRange | None
    liquidity: tuple[LiquidityEvent, ...]
    source: str
    higher_timeframe: str = "H1"
    execution_timeframe: str = "M5"

    def __post_init__(self) -> None:
        if self.observed_at.tzinfo is None:
            raise ValueError("observed_at must be timezone-aware")
        if not self.symbol.strip() or not self.timeframe.strip() or not self.source.strip():
            raise ValueError("symbol, timeframe, and source are required")


@dataclass(frozen=True, slots=True)
class Decision:
    verdict: DecisionVerdict
    confidence: Confidence
    score: float
    evaluated_at: datetime
    observation_time: datetime
    reasons: tuple[str, ...]
    conflicts: tuple[str, ...]
    missing_evidence: tuple[str, ...]
    policy_version: str
    contract_version: str
    disclaimer: str
