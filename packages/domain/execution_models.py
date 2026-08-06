"""Institutional Execution Readiness & Opportunity Lifecycle Domain Models.

Separates Setup Quality (0-100) from Entry Timing / Execution Readiness (0-100).
Defines ExecutionStatus (FRESH, ACTIVE, LATE, EXPIRED, WAIT) and ExecutionReadiness.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

from ._json_coerce import to_float, to_int


class ExecutionStatus(StrEnum):
    FRESH = "FRESH"
    ACTIVE = "ACTIVE"
    LATE = "LATE"
    EXPIRED = "EXPIRED"
    WAIT = "WAIT"


@dataclass(frozen=True, slots=True)
class ExecutionReadiness:
    readiness_score: int  # 0 to 100
    status: ExecutionStatus
    confidence: float  # 0.0 to 1.0
    explanation: str
    distance_from_ideal_entry_pct: float
    target_progress_pct: float
    current_risk_reward: float
    reasons_for_reduction: tuple[str, ...]
    evaluated_at: datetime

    def __post_init__(self) -> None:
        if not 0 <= self.readiness_score <= 100:
            raise ValueError("readiness_score must be between 0 and 100")
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("confidence must be between 0.0 and 1.0")
        if self.evaluated_at.tzinfo is None:
            raise ValueError("evaluated_at timestamp must be timezone-aware")

    def to_dict(self) -> dict[str, object]:
        return {
            "readiness_score": self.readiness_score,
            "status": str(self.status),
            "confidence": self.confidence,
            "explanation": self.explanation,
            "distance_from_ideal_entry_pct": self.distance_from_ideal_entry_pct,
            "target_progress_pct": self.target_progress_pct,
            "current_risk_reward": self.current_risk_reward,
            "reasons_for_reduction": list(self.reasons_for_reduction),
            "evaluated_at": self.evaluated_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, raw: dict[str, object]) -> ExecutionReadiness:
        evaluated_at_val = str(raw["evaluated_at"])
        evaluated_at = datetime.fromisoformat(evaluated_at_val)

        reasons_raw = raw.get("reasons_for_reduction", [])
        reasons_list = [str(x) for x in reasons_raw] if isinstance(reasons_raw, list) else []

        return cls(
            readiness_score=to_int(raw.get("readiness_score", 0)),
            status=ExecutionStatus(str(raw.get("status", "WAIT"))),
            confidence=to_float(raw.get("confidence", 0.0)),
            explanation=str(raw.get("explanation", "")),
            distance_from_ideal_entry_pct=to_float(raw.get("distance_from_ideal_entry_pct", 0.0)),
            target_progress_pct=to_float(raw.get("target_progress_pct", 0.0)),
            current_risk_reward=to_float(raw.get("current_risk_reward", 0.0)),
            reasons_for_reduction=tuple(reasons_list),
            evaluated_at=evaluated_at,
        )
