"""Evidence-backed, expiring, multi-label market regime context."""

from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import StrEnum


class MarketRegime(StrEnum):
    TRENDING = "TRENDING"
    RANGING = "RANGING"
    EXPANSION = "EXPANSION"
    COMPRESSION = "COMPRESSION"
    HIGH_VOLATILITY = "HIGH_VOLATILITY"
    LOW_VOLATILITY = "LOW_VOLATILITY"
    RISK_ON = "RISK_ON"
    RISK_OFF = "RISK_OFF"
    NEWS_DRIVEN = "NEWS_DRIVEN"
    LIQUIDITY_DRIVEN = "LIQUIDITY_DRIVEN"


@dataclass(frozen=True, slots=True)
class MarketRegimeContext:
    regime_id: str
    primary_regime: MarketRegime
    active_regimes: tuple[MarketRegime, ...]
    identified_at: datetime
    time_to_live: timedelta
    confidence: int
    rationale: str
    evidence_references: tuple[str, ...]
    source: str
    policy_version: str

    def __post_init__(self) -> None:
        if self.identified_at.tzinfo is None or self.time_to_live <= timedelta(0):
            raise ValueError("market regime requires a timezone-aware, positive lifecycle")
        if self.primary_regime not in self.active_regimes:
            raise ValueError("primary regime must be included in active regimes")
        if len(set(self.active_regimes)) != len(self.active_regimes):
            raise ValueError("active market regimes must be unique")
        if not 0 <= self.confidence <= 100:
            raise ValueError("market regime confidence must be between zero and 100")
        values = (self.regime_id, self.rationale, self.source, self.policy_version)
        if any(not value.strip() for value in values) or not self.evidence_references:
            raise ValueError("market regime requires identity, explanation, source, and evidence")

    def is_current(self, evaluated_at: datetime) -> bool:
        if evaluated_at.tzinfo is None:
            raise ValueError("regime evaluation time must be timezone-aware")
        return self.identified_at <= evaluated_at < self.identified_at + self.time_to_live


@dataclass(frozen=True, slots=True)
class RegimeInterpretation:
    evidence_id: str
    regime_id: str
    meaning: str
    adjusted_importance: float

    def __post_init__(self) -> None:
        if not self.evidence_id.strip() or not self.regime_id.strip() or not self.meaning.strip():
            raise ValueError("regime interpretation requires evidence, regime, and meaning")
        if not 0 <= self.adjusted_importance <= 1:
            raise ValueError("regime-adjusted importance must be between zero and one")
