"""Small detector result types retained for measurement tests."""

from dataclasses import dataclass

from .models import LiquidityEvent


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
