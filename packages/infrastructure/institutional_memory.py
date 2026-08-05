"""Restart-safe SQLite institutional-memory ledger with no mutation API."""

import sqlite3
from contextlib import closing
from datetime import date, datetime
from pathlib import Path

from packages.domain import InstitutionalMemoryEntry, MarketDayMemoryClosure, MemoryCategory


class SqliteInstitutionalMemory:
    def __init__(self, path: Path) -> None:
        self._path = path
        path.parent.mkdir(parents=True, exist_ok=True)
        with closing(self._connect()) as connection, connection:
            connection.executescript("""
            CREATE TABLE IF NOT EXISTS institutional_memory(
                memory_id TEXT PRIMARY KEY, category TEXT NOT NULL, occurred_at TEXT NOT NULL,
                recorded_at TEXT NOT NULL, source_reference TEXT NOT NULL, summary TEXT NOT NULL,
                canonical_payload TEXT NOT NULL, payload_sha256 TEXT NOT NULL,
                contract_version TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS institutional_memory_day_idx
            ON institutional_memory(occurred_at, category);
            CREATE TABLE IF NOT EXISTS market_day_closures(
                market_day TEXT PRIMARY KEY, new_entries INTEGER NOT NULL,
                total_entries INTEGER NOT NULL, daily_digest_sha256 TEXT NOT NULL,
                closed_at TEXT NOT NULL
            );
            """)

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self._path)

    def append(self, entry: InstitutionalMemoryEntry) -> None:
        with closing(self._connect()) as connection, connection:
            connection.execute(
                "INSERT INTO institutional_memory VALUES(?,?,?,?,?,?,?,?,?)",
                (
                    entry.memory_id,
                    entry.category.value,
                    entry.occurred_at.isoformat(),
                    entry.recorded_at.isoformat(),
                    entry.source_reference,
                    entry.summary,
                    entry.canonical_payload,
                    entry.payload_sha256,
                    entry.contract_version,
                ),
            )

    def entries_for_day(self, market_day: date) -> tuple[InstitutionalMemoryEntry, ...]:
        prefix = market_day.isoformat()
        with closing(self._connect()) as connection:
            rows = connection.execute(
                "SELECT * FROM institutional_memory WHERE substr(occurred_at,1,10)=? "
                "ORDER BY occurred_at, memory_id",
                (prefix,),
            ).fetchall()
        return tuple(self._entry(row) for row in rows)

    def total_entries(self) -> int:
        with closing(self._connect()) as connection:
            row = connection.execute("SELECT COUNT(*) FROM institutional_memory").fetchone()
        return 0 if row is None else int(row[0])

    def append_closure(self, closure: MarketDayMemoryClosure) -> None:
        with closing(self._connect()) as connection, connection:
            connection.execute(
                "INSERT INTO market_day_closures VALUES(?,?,?,?,?)",
                (
                    closure.market_day.isoformat(),
                    closure.new_entries,
                    closure.total_entries,
                    closure.daily_digest_sha256,
                    closure.closed_at.isoformat(),
                ),
            )

    @staticmethod
    def _entry(row: tuple[object, ...]) -> InstitutionalMemoryEntry:
        return InstitutionalMemoryEntry(
            str(row[0]),
            MemoryCategory(str(row[1])),
            datetime.fromisoformat(str(row[2])),
            datetime.fromisoformat(str(row[3])),
            str(row[4]),
            str(row[5]),
            str(row[6]),
            str(row[7]),
            str(row[8]),
        )
