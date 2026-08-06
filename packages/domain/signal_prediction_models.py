"""Signal Prediction domain models.

Defines canonical SignalPrediction output forecasting the next expected trading opportunity
window based on historical backtesting session frequency and liquidity cycles.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class SignalPrediction:
    symbol: str
    current_price: float
    next_window_start: datetime
    next_window_end: datetime
    probability_next_2h_pct: float
    estimated_minutes_remaining: int
    primary_session_trigger: str
    historical_backtest_confidence_pct: float
    evaluation_time: datetime

    def __post_init__(self) -> None:
        if not self.symbol.strip():
            raise ValueError("symbol is required")
        if not 0.0 <= self.probability_next_2h_pct <= 100.0:
            raise ValueError("probability_next_2h_pct must be between 0 and 100")

    def to_dict(self) -> dict[str, object]:
        return {
            "symbol": self.symbol,
            "current_price": self.current_price,
            "next_window_start": self.next_window_start.isoformat(),
            "next_window_end": self.next_window_end.isoformat(),
            "probability_next_2h_pct": self.probability_next_2h_pct,
            "estimated_minutes_remaining": self.estimated_minutes_remaining,
            "primary_session_trigger": self.primary_session_trigger,
            "historical_backtest_confidence_pct": self.historical_backtest_confidence_pct,
            "evaluation_time": self.evaluation_time.isoformat(),
        }

    @classmethod
    def from_dict(cls, raw: dict[str, object]) -> SignalPrediction:
        return cls(
            symbol=str(raw["symbol"]),
            current_price=float(raw.get("current_price", 3340.0)),
            next_window_start=datetime.fromisoformat(str(raw["next_window_start"])),
            next_window_end=datetime.fromisoformat(str(raw["next_window_end"])),
            probability_next_2h_pct=float(raw["probability_next_2h_pct"]),
            estimated_minutes_remaining=int(raw["estimated_minutes_remaining"]),
            primary_session_trigger=str(raw.get("primary_session_trigger", "")),
            historical_backtest_confidence_pct=float(raw.get("historical_backtest_confidence_pct", 84.0)),
            evaluation_time=datetime.fromisoformat(str(raw["evaluation_time"])),
        )
