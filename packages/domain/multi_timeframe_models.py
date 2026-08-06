"""Multi-Timeframe Scalping domain models.

Defines canonical MultiTimeframeThesis cascading lower timeframe execution (M5/M15)
from higher timeframe structural bias (H1).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from ._json_coerce import to_float, to_int
from .execution_models import ExecutionReadiness
from .models import DecisionVerdict


@dataclass(frozen=True, slots=True)
class MultiTimeframeThesis:
    thesis_id: str
    symbol: str
    higher_timeframe: str
    execution_timeframe: str
    htf_bias: DecisionVerdict
    ltf_trigger: str
    cascade_status: str
    setup_quality_score: int
    execution_readiness: ExecutionReadiness
    tight_stop_loss_pips: float
    target_rr: float
    reasons: tuple[str, ...]
    evaluated_at: datetime

    def __post_init__(self) -> None:
        if not self.thesis_id.strip() or not self.symbol.strip():
            raise ValueError("thesis_id and symbol are required")
        if not 0 <= self.setup_quality_score <= 100:
            raise ValueError("setup_quality_score must be between 0 and 100")

    def to_dict(self) -> dict[str, object]:
        return {
            "thesis_id": self.thesis_id,
            "symbol": self.symbol,
            "higher_timeframe": self.higher_timeframe,
            "execution_timeframe": self.execution_timeframe,
            "htf_bias": str(self.htf_bias),
            "ltf_trigger": self.ltf_trigger,
            "cascade_status": self.cascade_status,
            "setup_quality_score": self.setup_quality_score,
            "execution_readiness": self.execution_readiness.to_dict(),
            "tight_stop_loss_pips": self.tight_stop_loss_pips,
            "target_rr": self.target_rr,
            "reasons": list(self.reasons),
            "evaluated_at": self.evaluated_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, raw: dict[str, object]) -> MultiTimeframeThesis:
        er_raw = raw.get("execution_readiness")
        er_dict = er_raw if isinstance(er_raw, dict) else {}
        execution_readiness = ExecutionReadiness.from_dict(er_dict)
        reasons_raw = raw.get("reasons", [])
        reasons = tuple(str(x) for x in reasons_raw) if isinstance(reasons_raw, list) else ()

        return cls(
            thesis_id=str(raw["thesis_id"]),
            symbol=str(raw["symbol"]),
            higher_timeframe=str(raw.get("higher_timeframe", "H1")),
            execution_timeframe=str(raw.get("execution_timeframe", "M5")),
            htf_bias=DecisionVerdict(str(raw["htf_bias"])),
            ltf_trigger=str(raw.get("ltf_trigger", "")),
            cascade_status=str(raw.get("cascade_status", "ALIGNED")),
            setup_quality_score=to_int(raw["setup_quality_score"]),
            execution_readiness=execution_readiness,
            tight_stop_loss_pips=to_float(raw.get("tight_stop_loss_pips", 15.0)),
            target_rr=to_float(raw.get("target_rr", 3.0)),
            reasons=reasons,
            evaluated_at=datetime.fromisoformat(str(raw["evaluated_at"])),
        )
