"""Canonical models for reproducible bid/ask multi-timeframe research."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum


@dataclass(frozen=True, slots=True)
class Tick:
    timestamp: datetime
    bid: float
    ask: float
    bid_volume: float
    ask_volume: float

    def __post_init__(self) -> None:
        if self.timestamp.tzinfo is None:
            raise ValueError("tick timestamp must be timezone-aware")
        if self.bid <= 0 or self.ask <= 0 or self.ask < self.bid:
            raise ValueError("tick prices must be positive and ask must be >= bid")


@dataclass(frozen=True, slots=True)
class BidAskBar:
    timestamp: datetime
    seconds: int
    bid_open: float
    bid_high: float
    bid_low: float
    bid_close: float
    ask_open: float
    ask_high: float
    ask_low: float
    ask_close: float
    tick_count: int
    bid_volume: float
    ask_volume: float
    mean_spread: float

    @property
    def midpoint_open(self) -> float:
        return (self.bid_open + self.ask_open) / 2

    @property
    def midpoint_high(self) -> float:
        return (self.bid_high + self.ask_high) / 2

    @property
    def midpoint_low(self) -> float:
        return (self.bid_low + self.ask_low) / 2

    @property
    def midpoint_close(self) -> float:
        return (self.bid_close + self.ask_close) / 2

    @property
    def closed_at(self) -> datetime:
        from datetime import timedelta

        return self.timestamp + timedelta(seconds=self.seconds)

    def __post_init__(self) -> None:
        if self.timestamp.tzinfo is None:
            raise ValueError("bar timestamp must be timezone-aware")
        if self.seconds <= 0 or self.tick_count <= 0:
            raise ValueError("bar duration and tick count must be positive")
        if self.ask_open < self.bid_open or self.ask_close < self.bid_close:
            raise ValueError("ask prices must not be below bid prices")
        if not (
            self.bid_high >= max(self.bid_open, self.bid_close)
            and self.bid_low <= min(self.bid_open, self.bid_close)
            and self.ask_high >= max(self.ask_open, self.ask_close)
            and self.ask_low <= min(self.ask_open, self.ask_close)
        ):
            raise ValueError("invalid OHLC envelope")


class Direction(StrEnum):
    BUY = "BUY"
    SELL = "SELL"


class ExitMode(StrEnum):
    FIXED_R = "FIXED_R"
    PARTIAL_TRAIL = "PARTIAL_TRAIL"


class TradeOutcome(StrEnum):
    TARGET = "TARGET"
    STOP = "STOP"
    TRAIL = "TRAIL"
    DATA_END = "DATA_END"


@dataclass(frozen=True, slots=True)
class ExitPlan:
    mode: ExitMode
    target_r: float = 4.0
    partial_r: float = 2.0
    partial_fraction: float = 0.5
    trail_atr: float = 0.5

    def __post_init__(self) -> None:
        if self.target_r <= 0 or self.partial_r <= 0 or self.trail_atr <= 0:
            raise ValueError("exit multiples must be positive")
        if not 0 < self.partial_fraction < 1:
            raise ValueError("partial_fraction must be between zero and one")


@dataclass(frozen=True, slots=True)
class TradeIntent:
    pattern_id: str
    signal_time: datetime
    direction: Direction
    stop_distance: float
    atr: float
    exit_plan: ExitPlan

    def __post_init__(self) -> None:
        if self.signal_time.tzinfo is None:
            raise ValueError("signal_time must be timezone-aware")
        if self.stop_distance <= 0 or self.atr <= 0:
            raise ValueError("stop distance and ATR must be positive")


@dataclass(frozen=True, slots=True)
class TickTrade:
    pattern_id: str
    direction: Direction
    signal_time: datetime
    entry_time: datetime
    exit_time: datetime
    entry_price: float
    exit_price: float
    initial_stop: float
    outcome: TradeOutcome
    gross_r: float
    commission_r: float
    slippage_r: float
    net_r: float
    partial_taken: bool
