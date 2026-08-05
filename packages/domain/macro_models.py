"""Canonical Macro domain models for Gold Brain (XAUUSD).

Defines immutable models for DXY Dollar Strength, Treasury Yields (US10Y, US02Y),
High Impact News Environment, Liquidity Reference Levels (PDH, PDL, PWH, PWL, PMH, PML),
MacroContext, and MacroAssessment.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import StrEnum

from .context_models import NewsWindow


class DollarStrength(StrEnum):
    STRONG_BULLISH = "STRONG_BULLISH"
    BULLISH = "BULLISH"
    NEUTRAL = "NEUTRAL"
    BEARISH = "BEARISH"
    STRONG_BEARISH = "STRONG_BEARISH"


class YieldRegime(StrEnum):
    EXPANSION = "EXPANSION"
    COMPRESSION = "COMPRESSION"
    INFLATIONARY = "INFLATIONARY"
    NEUTRAL = "NEUTRAL"


class NewsImpact(StrEnum):
    HIGH_IMPACT = "HIGH_IMPACT"
    MEDIUM_IMPACT = "MEDIUM_IMPACT"
    LOW_IMPACT = "LOW_IMPACT"
    IGNORE = "IGNORE"


class LiquidityReferenceLevel(StrEnum):
    PDH = "PDH"  # Previous Day High
    PDL = "PDL"  # Previous Day Low
    PWH = "PWH"  # Previous Week High
    PWL = "PWL"  # Previous Week Low
    PMH = "PMH"  # Previous Month High
    PML = "PML"  # Previous Month Low


@dataclass(frozen=True, slots=True)
class YieldEnvironment:
    us10y: float
    us02y: float
    yield_direction: str
    yield_momentum: str
    regime: YieldRegime

    def to_dict(self) -> dict[str, object]:
        return {
            "us10y": self.us10y,
            "us02y": self.us02y,
            "yield_direction": self.yield_direction,
            "yield_momentum": self.yield_momentum,
            "regime": str(self.regime),
        }

    @classmethod
    def from_dict(cls, raw: dict[str, object]) -> YieldEnvironment:
        return cls(
            us10y=float(raw.get("us10y", 4.25)),
            us02y=float(raw.get("us02y", 4.50)),
            yield_direction=str(raw.get("yield_direction", "NEUTRAL")),
            yield_momentum=str(raw.get("yield_momentum", "FLAT")),
            regime=YieldRegime(str(raw.get("regime", "NEUTRAL"))),
        )


@dataclass(frozen=True, slots=True)
class NewsEnvironment:
    impact: NewsImpact
    window: NewsWindow
    unresolved_high_impact: bool
    event_name: str

    def to_dict(self) -> dict[str, object]:
        return {
            "impact": str(self.impact),
            "window": str(self.window),
            "unresolved_high_impact": self.unresolved_high_impact,
            "event_name": self.event_name,
        }

    @classmethod
    def from_dict(cls, raw: dict[str, object]) -> NewsEnvironment:
        return cls(
            impact=NewsImpact(str(raw.get("impact", "IGNORE"))),
            window=NewsWindow(str(raw.get("window", "CLEAR"))),
            unresolved_high_impact=bool(raw.get("unresolved_high_impact", False)),
            event_name=str(raw.get("event_name", "None")),
        )


@dataclass(frozen=True, slots=True)
class LiquidityReferenceEvidence:
    level: LiquidityReferenceLevel
    price: float
    swept: bool
    displacement_confirmed: bool

    def to_dict(self) -> dict[str, object]:
        return {
            "level": str(self.level),
            "price": self.price,
            "swept": self.swept,
            "displacement_confirmed": self.displacement_confirmed,
        }

    @classmethod
    def from_dict(cls, raw: dict[str, object]) -> LiquidityReferenceEvidence:
        return cls(
            level=LiquidityReferenceLevel(str(raw["level"])),
            price=float(raw["price"]),
            swept=bool(raw["swept"]),
            displacement_confirmed=bool(raw.get("displacement_confirmed", False)),
        )


@dataclass(frozen=True, slots=True)
class MacroContext:
    context_id: str
    dollar_strength: DollarStrength
    yield_environment: YieldEnvironment
    news_environment: NewsEnvironment
    liquidity_references: tuple[LiquidityReferenceEvidence, ...]
    observed_at: datetime
    ttl_seconds: int = 3600

    def __post_init__(self) -> None:
        if not self.context_id.strip():
            raise ValueError("context_id must not be empty")
        if self.observed_at.tzinfo is None:
            raise ValueError("observed_at timestamp must be timezone-aware")

    def is_valid(self, evaluated_at: datetime) -> bool:
        if evaluated_at.tzinfo is None:
            raise ValueError("evaluated_at timestamp must be timezone-aware")
        if evaluated_at < self.observed_at:
            return False
        expiry = self.observed_at + timedelta(seconds=self.ttl_seconds)
        return evaluated_at <= expiry

    def to_dict(self) -> dict[str, object]:
        return {
            "context_id": self.context_id,
            "dollar_strength": str(self.dollar_strength),
            "yield_environment": self.yield_environment.to_dict(),
            "news_environment": self.news_environment.to_dict(),
            "liquidity_references": [lr.to_dict() for lr in self.liquidity_references],
            "observed_at": self.observed_at.isoformat(),
            "ttl_seconds": self.ttl_seconds,
        }

    @classmethod
    def from_dict(cls, raw: dict[str, object]) -> MacroContext:
        observed_at_val = str(raw["observed_at"])
        observed_at = datetime.fromisoformat(observed_at_val)

        yield_raw = raw.get("yield_environment")
        yield_dict = yield_raw if isinstance(yield_raw, dict) else {}
        yield_env = YieldEnvironment.from_dict(yield_dict)

        news_raw = raw.get("news_environment")
        news_dict = news_raw if isinstance(news_raw, dict) else {}
        news_env = NewsEnvironment.from_dict(news_dict)

        lr_raw = raw.get("liquidity_references", [])
        liquidity_refs = (
            tuple(
                LiquidityReferenceEvidence.from_dict(item)
                for item in lr_raw
                if isinstance(item, dict)
            )
            if isinstance(lr_raw, list)
            else ()
        )

        return cls(
            context_id=str(raw["context_id"]),
            dollar_strength=DollarStrength(str(raw["dollar_strength"])),
            yield_environment=yield_env,
            news_environment=news_env,
            liquidity_references=liquidity_refs,
            observed_at=observed_at,
            ttl_seconds=int(raw.get("ttl_seconds", 3600)),
        )


@dataclass(frozen=True, slots=True)
class MacroAssessment:
    assessment_id: str
    macro_score: float  # 0.0 to 1.0
    confidence_modifier: float  # e.g. -0.2 to +0.2
    force_wait: bool
    wait_reason: str
    evidence: tuple[str, ...]
    evaluated_at: datetime

    def __post_init__(self) -> None:
        if not self.assessment_id.strip():
            raise ValueError("assessment_id must not be empty")
        if self.evaluated_at.tzinfo is None:
            raise ValueError("evaluated_at timestamp must be timezone-aware")

    def to_dict(self) -> dict[str, object]:
        return {
            "assessment_id": self.assessment_id,
            "macro_score": self.macro_score,
            "confidence_modifier": self.confidence_modifier,
            "force_wait": self.force_wait,
            "wait_reason": self.wait_reason,
            "evidence": list(self.evidence),
            "evaluated_at": self.evaluated_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, raw: dict[str, object]) -> MacroAssessment:
        evaluated_at_val = str(raw["evaluated_at"])
        evaluated_at = datetime.fromisoformat(evaluated_at_val)

        evidence_raw = raw.get("evidence", [])
        evidence_list = [str(x) for x in evidence_raw] if isinstance(evidence_raw, list) else []

        return cls(
            assessment_id=str(raw["assessment_id"]),
            macro_score=float(raw.get("macro_score", 0.5)),
            confidence_modifier=float(raw.get("confidence_modifier", 0.0)),
            force_wait=bool(raw.get("force_wait", False)),
            wait_reason=str(raw.get("wait_reason", "")),
            evidence=tuple(evidence_list),
            evaluated_at=evaluated_at,
        )
