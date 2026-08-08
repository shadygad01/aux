"""Multi-Timeframe Scalping domain models.

Defines canonical MultiTimeframeThesis cascading lower timeframe execution (M5/M15)
from higher timeframe structural bias (H1), and RiskGuidance, its market-derived
stop/target/risk-reward output.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from ._json_coerce import to_float, to_int
from .execution_models import ExecutionReadiness
from .models import DecisionVerdict


@dataclass(frozen=True, slots=True)
class RiskGuidance:
    """Market-derived stop/target/risk-reward guidance for the execution
    timeframe. Every populated field traces to a real price (dealing-range
    boundary, a swept liquidity level, or an ATR reading); when required
    data is unavailable the field is None and `risk_status` says why. This
    type replaces the fixed `tight_stop_loss_pips`/`target_rr` constants
    MultiTimeframeThesis previously carried -- see
    docs/adr/0007-engine-consolidation.md and the Multi-Timeframe risk model
    design report this implements.
    """

    entry_price: float | None
    stop_loss_price: float | None
    target_price: float | None
    stop_distance: float | None
    target_distance: float | None
    risk_reward: float | None
    invalidation_level: float | None
    invalidation_source: str | None  # "LIQUIDITY_SWEEP" | "DEALING_RANGE" | None
    atr: float | None
    target_source: str | None  # "EXECUTION_LIQUIDITY" | "DEALING_RANGE" | None
    risk_status: str  # "OK" | "INSUFFICIENT_DATA" | "UNAVAILABLE"
    calculation_method: str

    def to_dict(self) -> dict[str, object]:
        return {
            "entry_price": self.entry_price,
            "stop_loss_price": self.stop_loss_price,
            "target_price": self.target_price,
            "stop_distance": self.stop_distance,
            "target_distance": self.target_distance,
            "risk_reward": self.risk_reward,
            "invalidation_level": self.invalidation_level,
            "invalidation_source": self.invalidation_source,
            "atr": self.atr,
            "target_source": self.target_source,
            "risk_status": self.risk_status,
            "calculation_method": self.calculation_method,
        }

    @classmethod
    def from_dict(cls, raw: dict[str, object]) -> RiskGuidance:
        def optional_float(key: str) -> float | None:
            value = raw.get(key)
            return to_float(value) if value is not None else None

        def optional_str(key: str) -> str | None:
            value = raw.get(key)
            return str(value) if value is not None else None

        return cls(
            entry_price=optional_float("entry_price"),
            stop_loss_price=optional_float("stop_loss_price"),
            target_price=optional_float("target_price"),
            stop_distance=optional_float("stop_distance"),
            target_distance=optional_float("target_distance"),
            risk_reward=optional_float("risk_reward"),
            invalidation_level=optional_float("invalidation_level"),
            invalidation_source=optional_str("invalidation_source"),
            atr=optional_float("atr"),
            target_source=optional_str("target_source"),
            risk_status=str(raw["risk_status"]),
            calculation_method=str(raw["calculation_method"]),
        )


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
    risk_guidance: RiskGuidance
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
            "risk_guidance": self.risk_guidance.to_dict(),
            "reasons": list(self.reasons),
            "evaluated_at": self.evaluated_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, raw: dict[str, object]) -> MultiTimeframeThesis:
        er_raw = raw.get("execution_readiness")
        er_dict = er_raw if isinstance(er_raw, dict) else {}
        execution_readiness = ExecutionReadiness.from_dict(er_dict)

        risk_raw = raw["risk_guidance"]
        if not isinstance(risk_raw, dict):
            raise ValueError("risk_guidance must be an object")
        risk_guidance = RiskGuidance.from_dict(risk_raw)

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
            risk_guidance=risk_guidance,
            reasons=reasons,
            evaluated_at=datetime.fromisoformat(str(raw["evaluated_at"])),
        )
