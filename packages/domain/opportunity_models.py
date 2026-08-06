"""Opportunity Identity domain models.

Defines canonical OpportunityIdentity, lifecycle states, outcomes, and archive status.
Ensures every trading opportunity maintains a globally unique ID throughout its lifetime.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

from ._json_coerce import to_int
from .execution_models import ExecutionReadiness
from .models import DecisionVerdict


class OpportunityLifecycleState(StrEnum):
    CREATING = "CREATING"
    ACTIVE = "ACTIVE"
    AGING = "AGING"
    COMPLETED = "COMPLETED"
    INVALIDATED = "INVALIDATED"
    ARCHIVED = "ARCHIVED"


class OpportunityOutcome(StrEnum):
    PENDING = "PENDING"
    WINNING = "WINNING"
    LOSING = "LOSING"
    EXPIRED = "EXPIRED"
    CANCELLED = "CANCELLED"


class OpportunityArchiveStatus(StrEnum):
    LIVE = "LIVE"
    ARCHIVED = "ARCHIVED"


@dataclass(frozen=True, slots=True)
class OpportunityIdentity:
    opportunity_id: str
    symbol: str
    timeframe: str
    created_at: datetime
    last_updated_at: datetime
    creation_conditions: tuple[str, ...]
    verdict: DecisionVerdict
    setup_quality_score: int
    max_setup_quality_score: int
    execution_readiness: ExecutionReadiness
    current_state: OpportunityLifecycleState
    outcome: OpportunityOutcome
    archive_status: OpportunityArchiveStatus
    is_fresh: bool

    def __post_init__(self) -> None:
        if not self.opportunity_id.strip():
            raise ValueError("opportunity_id is required")
        if not 0 <= self.setup_quality_score <= 100:
            raise ValueError("setup_quality_score must be between 0 and 100")
        if not 0 <= self.max_setup_quality_score <= 100:
            raise ValueError("max_setup_quality_score must be between 0 and 100")

    def to_dict(self) -> dict[str, object]:
        return {
            "opportunity_id": self.opportunity_id,
            "symbol": self.symbol,
            "timeframe": self.timeframe,
            "created_at": self.created_at.isoformat(),
            "last_updated_at": self.last_updated_at.isoformat(),
            "creation_conditions": list(self.creation_conditions),
            "verdict": str(self.verdict),
            "setup_quality_score": self.setup_quality_score,
            "max_setup_quality_score": self.max_setup_quality_score,
            "execution_readiness": self.execution_readiness.to_dict(),
            "current_state": str(self.current_state),
            "outcome": str(self.outcome),
            "archive_status": str(self.archive_status),
            "is_fresh": self.is_fresh,
        }

    @classmethod
    def from_dict(cls, raw: dict[str, object]) -> OpportunityIdentity:
        created_at_val = str(raw["created_at"])
        last_updated_val = str(raw["last_updated_at"])
        conds_raw = raw.get("creation_conditions", [])
        creation_conditions = (
            tuple(str(x) for x in conds_raw) if isinstance(conds_raw, list) else ()
        )

        er_raw = raw.get("execution_readiness")
        er_dict = er_raw if isinstance(er_raw, dict) else {}
        execution_readiness = ExecutionReadiness.from_dict(er_dict)

        return cls(
            opportunity_id=str(raw["opportunity_id"]),
            symbol=str(raw["symbol"]),
            timeframe=str(raw.get("timeframe", "H1")),
            created_at=datetime.fromisoformat(created_at_val),
            last_updated_at=datetime.fromisoformat(last_updated_val),
            creation_conditions=creation_conditions,
            verdict=DecisionVerdict(str(raw["verdict"])),
            setup_quality_score=to_int(raw["setup_quality_score"]),
            max_setup_quality_score=to_int(raw["max_setup_quality_score"]),
            execution_readiness=execution_readiness,
            current_state=OpportunityLifecycleState(str(raw["current_state"])),
            outcome=OpportunityOutcome(str(raw.get("outcome", "PENDING"))),
            archive_status=OpportunityArchiveStatus(str(raw.get("archive_status", "LIVE"))),
            is_fresh=bool(raw.get("is_fresh", True)),
        )
