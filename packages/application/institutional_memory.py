"""Record durable experience and prove that each market day added memory."""

from datetime import date, datetime
from hashlib import sha256
from typing import Protocol

from packages.domain import (
    InstitutionalMemoryEntry,
    MarketDayMemoryClosure,
    MemoryCategory,
)


class InstitutionalMemoryArchive(Protocol):
    def append(self, entry: InstitutionalMemoryEntry) -> None: ...

    def entries_for_day(self, market_day: date) -> tuple[InstitutionalMemoryEntry, ...]: ...

    def total_entries(self) -> int: ...

    def append_closure(self, closure: MarketDayMemoryClosure) -> None: ...


class InstitutionalMemory:
    def __init__(self, archive: InstitutionalMemoryArchive) -> None:
        self._archive = archive

    def remember(
        self,
        category: MemoryCategory,
        occurred_at: datetime,
        recorded_at: datetime,
        source_reference: str,
        summary: str,
        canonical_payload: str,
    ) -> InstitutionalMemoryEntry:
        payload_hash = sha256(canonical_payload.encode("utf-8")).hexdigest()
        identity_input = (
            f"{category.value}|{occurred_at.isoformat()}|{source_reference}|{payload_hash}"
        )
        memory_id = f"MEMORY-{sha256(identity_input.encode('utf-8')).hexdigest()[:24]}"
        entry = InstitutionalMemoryEntry(
            memory_id,
            category,
            occurred_at,
            recorded_at,
            source_reference,
            summary,
            canonical_payload,
            payload_hash,
        )
        self._archive.append(entry)
        return entry

    def close_market_day(self, market_day: date, closed_at: datetime) -> MarketDayMemoryClosure:
        entries = self._archive.entries_for_day(market_day)
        if not entries:
            raise ValueError(f"market day cannot close without new memory; day={market_day}")
        digest_input = "|".join(sorted(entry.payload_sha256 for entry in entries))
        closure = MarketDayMemoryClosure(
            market_day,
            len(entries),
            self._archive.total_entries(),
            sha256(digest_input.encode("utf-8")).hexdigest(),
            closed_at,
        )
        self._archive.append_closure(closure)
        return closure

    @staticmethod
    def verifies(entry: InstitutionalMemoryEntry) -> bool:
        return sha256(entry.canonical_payload.encode("utf-8")).hexdigest() == entry.payload_sha256
