"""One complete, expiring state used by every public downstream decision step."""

from dataclasses import dataclass
from datetime import datetime, timedelta

from .market_regime_models import MarketRegimeContext
from .trading_models import HorizonBias


@dataclass(frozen=True, slots=True)
class CurrentMarketState:
    state_id: str
    symbol: str
    captured_at: datetime
    time_to_live: timedelta
    regime: MarketRegimeContext
    macro_state: str
    biases: tuple[HorizonBias, ...]
    volatility_state: str
    liquidity_state: str
    momentum_state: str
    news_state: str
    confidence: int
    uncertainty: int
    evidence_references: tuple[str, ...]
    source: str
    policy_version: str

    def __post_init__(self) -> None:
        if self.captured_at.tzinfo is None or self.time_to_live <= timedelta(0):
            raise ValueError("current state requires a timezone-aware, positive lifecycle")
        if not self.regime.is_current(self.captured_at):
            raise ValueError("current state requires a current market regime")
        if not 0 <= self.confidence <= 100 or not 0 <= self.uncertainty <= 100:
            raise ValueError(
                "current-state confidence and uncertainty must be between zero and 100"
            )
        values = (
            self.state_id,
            self.symbol,
            self.macro_state,
            self.volatility_state,
            self.liquidity_state,
            self.momentum_state,
            self.news_state,
            self.source,
            self.policy_version,
        )
        if any(not value.strip() for value in values):
            raise ValueError("current state requires every named state and identity field")
        if not self.biases or not self.evidence_references:
            raise ValueError("current state requires bias and supporting evidence")
        horizons = {bias.horizon for bias in self.biases}
        if len(horizons) != len(self.biases):
            raise ValueError("current-state bias horizons must be unique")

    def is_current(self, evaluated_at: datetime) -> bool:
        if evaluated_at.tzinfo is None:
            raise ValueError("current-state evaluation time must be timezone-aware")
        state_current = self.captured_at <= evaluated_at < self.captured_at + self.time_to_live
        return state_current and self.regime.is_current(evaluated_at)
