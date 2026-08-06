"""Canonical Market Story domain model.

Market Story explains how and why the current market state evolved across
macro, bias, dealing range, liquidity, momentum, and SMC stages.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import StrEnum

from ._json_coerce import to_int


class MarketStoryStage(StrEnum):
    MACRO = "MACRO"
    BIAS = "BIAS"
    DISCOUNT = "DISCOUNT"
    LIQUIDITY = "LIQUIDITY"
    MOMENTUM = "MOMENTUM"
    SMC = "SMC"
    THESIS = "THESIS"


@dataclass(frozen=True, slots=True)
class StoryStageDetail:
    stage: MarketStoryStage
    title: str
    status: str
    narrative: str
    evidence_ids: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "stage": str(self.stage),
            "title": self.title,
            "status": self.status,
            "narrative": self.narrative,
            "evidence_ids": list(self.evidence_ids),
        }

    @classmethod
    def from_dict(cls, raw: dict[str, object]) -> StoryStageDetail:
        evidence_raw = raw.get("evidence_ids", [])
        evidence_ids = tuple(str(x) for x in evidence_raw) if isinstance(evidence_raw, list) else ()
        return cls(
            stage=MarketStoryStage(str(raw["stage"])),
            title=str(raw["title"]),
            status=str(raw["status"]),
            narrative=str(raw["narrative"]),
            evidence_ids=evidence_ids,
        )


@dataclass(frozen=True, slots=True)
class MarketStory:
    story_id: str
    symbol: str
    timeframe: str
    evolution_summary: str
    stages: tuple[StoryStageDetail, ...]
    created_at: datetime
    ttl_seconds: int = 3600

    def __post_init__(self) -> None:
        if not self.story_id.strip():
            raise ValueError("story_id must not be empty")
        if not self.symbol.strip():
            raise ValueError("symbol must not be empty")
        if self.created_at.tzinfo is None:
            raise ValueError("created_at timestamp must be timezone-aware")
        if not self.stages:
            raise ValueError("market story requires at least one stage detail")

    def is_valid(self, evaluated_at: datetime) -> bool:
        if evaluated_at.tzinfo is None:
            raise ValueError("evaluated_at timestamp must be timezone-aware")
        if evaluated_at < self.created_at:
            return False
        expiry = self.created_at + timedelta(seconds=self.ttl_seconds)
        return evaluated_at <= expiry

    def to_dict(self) -> dict[str, object]:
        return {
            "story_id": self.story_id,
            "symbol": self.symbol,
            "timeframe": self.timeframe,
            "evolution_summary": self.evolution_summary,
            "stages": [s.to_dict() for s in self.stages],
            "created_at": self.created_at.isoformat(),
            "ttl_seconds": self.ttl_seconds,
        }

    @classmethod
    def from_dict(cls, raw: dict[str, object]) -> MarketStory:
        created_at_val = str(raw["created_at"])
        created_at = datetime.fromisoformat(created_at_val)

        stages_raw = raw.get("stages", [])
        stages = (
            tuple(StoryStageDetail.from_dict(s) for s in stages_raw if isinstance(s, dict))
            if isinstance(stages_raw, list)
            else ()
        )

        return cls(
            story_id=str(raw["story_id"]),
            symbol=str(raw["symbol"]),
            timeframe=str(raw["timeframe"]),
            evolution_summary=str(raw["evolution_summary"]),
            stages=stages,
            created_at=created_at,
            ttl_seconds=to_int(raw.get("ttl_seconds", 3600)),
        )
