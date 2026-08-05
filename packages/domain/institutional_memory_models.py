"""Unified append-only institutional memory records and market-day closures."""

from dataclasses import dataclass
from datetime import date, datetime
from enum import StrEnum


class MemoryCategory(StrEnum):
    RESEARCH = "RESEARCH"
    PATTERNS = "PATTERNS"
    FAILURES = "FAILURES"
    SUCCESSES = "SUCCESSES"
    MACRO_EVENTS = "MACRO_EVENTS"
    MARKET_REGIMES = "MARKET_REGIMES"
    HISTORICAL_COMPARISONS = "HISTORICAL_COMPARISONS"
    DECISION_EVOLUTION = "DECISION_EVOLUTION"
    KNOWLEDGE_EVOLUTION = "KNOWLEDGE_EVOLUTION"


@dataclass(frozen=True, slots=True)
class InstitutionalMemoryEntry:
    memory_id: str
    category: MemoryCategory
    occurred_at: datetime
    recorded_at: datetime
    source_reference: str
    summary: str
    canonical_payload: str
    payload_sha256: str
    contract_version: str = "1.0.0"

    def __post_init__(self) -> None:
        if self.occurred_at.tzinfo is None or self.recorded_at.tzinfo is None:
            raise ValueError("institutional memory timestamps must be timezone-aware")
        values = (self.memory_id, self.source_reference, self.summary, self.canonical_payload)
        if any(not value.strip() for value in values):
            raise ValueError("institutional memory requires identity, source, summary, and payload")
        if len(self.payload_sha256) != 64 or any(
            character not in "0123456789abcdef" for character in self.payload_sha256
        ):
            raise ValueError("institutional memory requires a lowercase SHA-256 payload hash")


@dataclass(frozen=True, slots=True)
class MarketDayMemoryClosure:
    market_day: date
    new_entries: int
    total_entries: int
    daily_digest_sha256: str
    closed_at: datetime

    def __post_init__(self) -> None:
        if self.closed_at.tzinfo is None or self.new_entries <= 0:
            raise ValueError("market-day closure requires time and new institutional memory")
        if self.total_entries < self.new_entries or len(self.daily_digest_sha256) != 64:
            raise ValueError("market-day closure counts or digest are invalid")
