"""Canonical Market Thesis and Trade Quality domain model.

Market Thesis is the sole canonical decision output of the Gold Brain decision pipeline.
Unifies verdict, 0-100 trade quality, confidence, uncertainty, and evidence lineage.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

from .models import DecisionVerdict


class TradeQualityGrade(StrEnum):
    EXCELLENT = "EXCELLENT"
    GOOD = "GOOD"
    MODERATE = "MODERATE"
    WEAK = "WEAK"
    INVALID = "INVALID"


@dataclass(frozen=True, slots=True)
class TradeQuality:
    score: int  # 0 to 100
    grade: TradeQualityGrade
    breakdown: dict[str, int]
    explanation: str

    def __post_init__(self) -> None:
        if not 0 <= self.score <= 100:
            raise ValueError("trade quality score must be between 0 and 100")

    def to_dict(self) -> dict[str, object]:
        return {
            "score": self.score,
            "grade": str(self.grade),
            "breakdown": self.breakdown,
            "explanation": self.explanation,
        }

    @classmethod
    def from_dict(cls, raw: dict[str, object]) -> TradeQuality:
        score = int(raw["score"])
        grade = TradeQualityGrade(str(raw["grade"]))
        breakdown_raw = raw.get("breakdown", {})
        breakdown = (
            {str(k): int(v) for k, v in breakdown_raw.items()}
            if isinstance(breakdown_raw, dict)
            else {}
        )
        explanation = str(raw.get("explanation", ""))
        return cls(score=score, grade=grade, breakdown=breakdown, explanation=explanation)


@dataclass(frozen=True, slots=True)
class MarketThesis:
    thesis_id: str
    symbol: str
    timeframe: str
    verdict: DecisionVerdict
    meaning: str
    confidence: str
    confidence_score: float
    uncertainty_score: float
    trade_quality: TradeQuality
    reasons: tuple[str, ...]
    conflicts: tuple[str, ...]
    missing_evidence: tuple[str, ...]
    evaluated_at: datetime
    policy_version: str
    technical_score: float = 1.0
    macro_score: float = 0.5
    contract_version: str = "1.0.0"

    def __post_init__(self) -> None:
        if not self.thesis_id.strip():
            raise ValueError("thesis_id must not be empty")
        if self.evaluated_at.tzinfo is None:
            raise ValueError("evaluated_at timestamp must be timezone-aware")
        if not 0.0 <= self.confidence_score <= 1.0:
            raise ValueError("confidence_score must be between 0.0 and 1.0")

    def to_dict(self) -> dict[str, object]:
        return {
            "thesis_id": self.thesis_id,
            "symbol": self.symbol,
            "timeframe": self.timeframe,
            "verdict": str(self.verdict),
            "meaning": self.meaning,
            "confidence": self.confidence,
            "confidence_score": self.confidence_score,
            "uncertainty_score": self.uncertainty_score,
            "technical_score": self.technical_score,
            "macro_score": self.macro_score,
            "trade_quality": self.trade_quality.to_dict(),
            "reasons": list(self.reasons),
            "conflicts": list(self.conflicts),
            "missing_evidence": list(self.missing_evidence),
            "evaluated_at": self.evaluated_at.isoformat(),
            "policy_version": self.policy_version,
            "contract_version": self.contract_version,
        }

    @classmethod
    def from_dict(cls, raw: dict[str, object]) -> MarketThesis:
        evaluated_at_val = str(raw["evaluated_at"])
        evaluated_at = datetime.fromisoformat(evaluated_at_val)

        tq_raw = raw["trade_quality"]
        tq_dict = tq_raw if isinstance(tq_raw, dict) else {}
        trade_quality = TradeQuality.from_dict(tq_dict)

        reasons_raw = raw.get("reasons", [])
        conflicts_raw = raw.get("conflicts", [])
        missing_raw = raw.get("missing_evidence", [])

        reasons_list = [str(x) for x in reasons_raw] if isinstance(reasons_raw, list) else []
        conflicts_list = [str(x) for x in conflicts_raw] if isinstance(conflicts_raw, list) else []
        missing_list = [str(x) for x in missing_raw] if isinstance(missing_raw, list) else []

        return cls(
            thesis_id=str(raw["thesis_id"]),
            symbol=str(raw["symbol"]),
            timeframe=str(raw["timeframe"]),
            verdict=DecisionVerdict(str(raw["verdict"])),
            meaning=str(raw["meaning"]),
            confidence=str(raw["confidence"]),
            confidence_score=float(raw["confidence_score"]),
            uncertainty_score=float(raw["uncertainty_score"]),
            technical_score=float(raw.get("technical_score", 1.0)),
            macro_score=float(raw.get("macro_score", 0.5)),
            trade_quality=trade_quality,
            reasons=tuple(reasons_list),
            conflicts=tuple(conflicts_list),
            missing_evidence=tuple(missing_list),
            evaluated_at=evaluated_at,
            policy_version=str(raw["policy_version"]),
            contract_version=str(raw.get("contract_version", "1.0.0")),
        )
