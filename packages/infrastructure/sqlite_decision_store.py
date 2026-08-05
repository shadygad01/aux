"""Durable SQLite Hash-bound Store for Decision Memory and Learning Records.

Provides persistent, hash-bound storage, rehydration, and outcome searches
without paid services or external persistent servers.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
from datetime import UTC, datetime
from pathlib import Path

from packages.domain import MarketThesis


class SqliteDecisionStore:
    """Hash-bound durable store backed by local SQLite database."""

    def __init__(self, db_path: Path | str = ":memory:") -> None:
        self.db_path = str(db_path)
        self._shared_conn: sqlite3.Connection | None = None
        if self.db_path == ":memory:":
            self._shared_conn = sqlite3.connect(":memory:")
            self._shared_conn.row_factory = sqlite3.Row
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        if self._shared_conn is not None:
            return self._shared_conn
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        conn = self._get_connection()
        try:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS decision_theses (
                    thesis_id TEXT PRIMARY KEY,
                    symbol TEXT NOT NULL,
                    verdict TEXT NOT NULL,
                    trade_quality INTEGER NOT NULL,
                    evaluated_at TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    content_hash TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS learning_records (
                    record_id TEXT PRIMARY KEY,
                    snapshot_id TEXT NOT NULL,
                    recommendation_id TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    content_hash TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
            """)
            conn.commit()
        finally:
            if self._shared_conn is None:
                conn.close()

    def _compute_hash(self, payload: dict[str, object]) -> str:
        serialized = json.dumps(payload, sort_keys=True)
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()

    def save_thesis(self, thesis: MarketThesis) -> str:
        payload = thesis.to_dict()
        content_hash = self._compute_hash(payload)
        now_iso = datetime.now(UTC).isoformat()

        conn = self._get_connection()
        try:
            conn.execute(
                """
                INSERT OR REPLACE INTO decision_theses
                (thesis_id, symbol, verdict, trade_quality, evaluated_at,
                 payload_json, content_hash, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    thesis.thesis_id,
                    thesis.symbol,
                    str(thesis.verdict),
                    thesis.trade_quality.score,
                    thesis.evaluated_at.isoformat(),
                    json.dumps(payload),
                    content_hash,
                    now_iso,
                ),
            )
            conn.commit()
        finally:
            if self._shared_conn is None:
                conn.close()

        return content_hash

    def get_thesis(self, thesis_id: str) -> MarketThesis | None:
        conn = self._get_connection()
        try:
            row = conn.execute(
                "SELECT payload_json, content_hash FROM decision_theses WHERE thesis_id = ?",
                (thesis_id,),
            ).fetchone()
            if row is None:
                return None

            payload = json.loads(row["payload_json"])
            computed = self._compute_hash(payload)
            if computed != row["content_hash"]:
                raise ValueError(f"Content hash mismatch for thesis_id {thesis_id}")

            return MarketThesis.from_dict(payload)
        finally:
            if self._shared_conn is None:
                conn.close()

    def list_theses(self, limit: int = 50) -> list[MarketThesis]:
        conn = self._get_connection()
        try:
            rows = conn.execute(
                "SELECT payload_json FROM decision_theses ORDER BY evaluated_at DESC LIMIT ?",
                (limit,),
            ).fetchall()
            return [MarketThesis.from_dict(json.loads(row["payload_json"])) for row in rows]
        finally:
            if self._shared_conn is None:
                conn.close()
