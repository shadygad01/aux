"""Canonical Context domain model.

Context is NOT Evidence.
Context is NOT Knowledge.

Context describes the environment in which evidence must be interpreted.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import StrEnum


class TradingSession(StrEnum):
    LONDON = "LONDON"
    NEW_YORK = "NEW_YORK"
    ASIAN = "ASIAN"
    OVERLAP = "OVERLAP"
    CLOSED = "CLOSED"


class NewsWindow(StrEnum):
    CLEAR = "CLEAR"
    PRE_NEWS = "PRE_NEWS"
    ACTIVE_HIGH_IMPACT = "ACTIVE_HIGH_IMPACT"
    POST_NEWS = "POST_NEWS"


class MacroRegime(StrEnum):
    EXPANSION = "EXPANSION"
    CONTRACTION = "CONTRACTION"
    INFLATIONARY_PRESSURE = "INFLATIONARY_PRESSURE"
    NEUTRAL = "NEUTRAL"


class VolatilityRegime(StrEnum):
    LOW_VOLATILITY = "LOW_VOLATILITY"
    HIGH_VOLATILITY = "HIGH_VOLATILITY"
    COMPRESSION = "COMPRESSION"
    EXPANSION = "EXPANSION"


class LiquidityConditions(StrEnum):
    NORMAL = "NORMAL"
    THIN = "THIN"
    VACUUM = "VACUUM"
    HIGH = "HIGH"


@dataclass(frozen=True, slots=True)
class EnvironmentFlags:
    is_holiday: bool = False
    is_weekend: bool = False
    is_market_open: bool = True
    is_market_close: bool = False

    def to_dict(self) -> dict[str, bool]:
        return {
            "is_holiday": self.is_holiday,
            "is_weekend": self.is_weekend,
            "is_market_open": self.is_market_open,
            "is_market_close": self.is_market_close,
        }

    @classmethod
    def from_dict(cls, raw: dict[str, object]) -> EnvironmentFlags:
        return cls(
            is_holiday=bool(raw.get("is_holiday", False)),
            is_weekend=bool(raw.get("is_weekend", False)),
            is_market_open=bool(raw.get("is_market_open", True)),
            is_market_close=bool(raw.get("is_market_close", False)),
        )


@dataclass(frozen=True, slots=True)
class MarketContext:
    context_id: str
    symbol: str
    session: TradingSession
    news_window: NewsWindow
    macro_regime: MacroRegime
    volatility_regime: VolatilityRegime
    liquidity_conditions: LiquidityConditions
    flags: EnvironmentFlags
    observed_at: datetime
    ttl_seconds: int = 3600
    source: str = "canonical-context-provider"

    def __post_init__(self) -> None:
        if not self.context_id.strip():
            raise ValueError("context_id must not be empty")
        if not self.symbol.strip():
            raise ValueError("symbol must not be empty")
        if self.observed_at.tzinfo is None:
            raise ValueError("observed_at timestamp must be timezone-aware")
        if self.ttl_seconds <= 0:
            raise ValueError("ttl_seconds must be positive")

    def is_valid(self, evaluated_at: datetime) -> bool:
        if evaluated_at.tzinfo is None:
            raise ValueError("evaluation timestamp must be timezone-aware")
        if evaluated_at < self.observed_at:
            return False
        expiry = self.observed_at + timedelta(seconds=self.ttl_seconds)
        return evaluated_at <= expiry

    def to_dict(self) -> dict[str, object]:
        return {
            "context_id": self.context_id,
            "symbol": self.symbol,
            "session": str(self.session),
            "news_window": str(self.news_window),
            "macro_regime": str(self.macro_regime),
            "volatility_regime": str(self.volatility_regime),
            "liquidity_conditions": str(self.liquidity_conditions),
            "flags": self.flags.to_dict(),
            "observed_at": self.observed_at.isoformat(),
            "ttl_seconds": self.ttl_seconds,
            "source": self.source,
        }

    @classmethod
    def from_dict(cls, raw: dict[str, object]) -> MarketContext:
        observed_at_val = raw["observed_at"]
        if not isinstance(observed_at_val, str):
            raise TypeError("observed_at must be an ISO string")
        observed_at = datetime.fromisoformat(observed_at_val)

        flags_raw = raw.get("flags", {})
        flags_dict = flags_raw if isinstance(flags_raw, dict) else {}
        flags = EnvironmentFlags.from_dict(flags_dict)

        context_id_val = str(raw["context_id"])
        symbol_val = str(raw["symbol"])
        session_val = TradingSession(str(raw["session"]))
        news_window_val = NewsWindow(str(raw["news_window"]))
        macro_regime_val = MacroRegime(str(raw["macro_regime"]))
        volatility_regime_val = VolatilityRegime(str(raw["volatility_regime"]))
        liquidity_conditions_val = LiquidityConditions(str(raw["liquidity_conditions"]))

        ttl_val = raw.get("ttl_seconds", 3600)
        ttl_seconds = int(ttl_val) if isinstance(ttl_val, (int, str)) else 3600
        source_val = str(raw.get("source", "canonical-context-provider"))

        return cls(
            context_id=context_id_val,
            symbol=symbol_val,
            session=session_val,
            news_window=news_window_val,
            macro_regime=macro_regime_val,
            volatility_regime=volatility_regime_val,
            liquidity_conditions=liquidity_conditions_val,
            flags=flags,
            observed_at=observed_at,
            ttl_seconds=ttl_seconds,
            source=source_val,
        )
