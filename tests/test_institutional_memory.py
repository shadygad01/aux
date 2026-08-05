import sqlite3
import unittest
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from tempfile import TemporaryDirectory

from packages.application import InstitutionalMemory
from packages.domain import MemoryCategory
from packages.infrastructure import SqliteInstitutionalMemory

NOW = datetime(2026, 8, 5, 12, tzinfo=UTC)


class InstitutionalMemoryTests(unittest.TestCase):
    def test_all_categories_persist_across_restart_and_close_market_day(self) -> None:
        with TemporaryDirectory() as directory:
            path = Path(directory) / "institutional-memory.db"
            archive = SqliteInstitutionalMemory(path)
            memory = InstitutionalMemory(archive)
            recorded = []
            for index, category in enumerate(MemoryCategory):
                recorded.append(
                    memory.remember(
                        category,
                        NOW + timedelta(minutes=index),
                        NOW + timedelta(minutes=index),
                        f"source:{category.value}",
                        f"Institutional memory for {category.value}",
                        f'{{"category":"{category.value}","revision":1}}',
                    )
                )
            closure = memory.close_market_day(date(2026, 8, 5), NOW + timedelta(hours=8))
            self.assertEqual(closure.new_entries, len(MemoryCategory))
            self.assertEqual(closure.total_entries, len(MemoryCategory))

            reopened = SqliteInstitutionalMemory(path)
            restored = reopened.entries_for_day(date(2026, 8, 5))
            self.assertEqual({entry.category for entry in restored}, set(MemoryCategory))
            self.assertTrue(all(InstitutionalMemory.verifies(entry) for entry in restored))
            self.assertEqual(
                {entry.memory_id for entry in restored}, {entry.memory_id for entry in recorded}
            )

    def test_empty_market_day_cannot_close(self) -> None:
        with TemporaryDirectory() as directory:
            archive = SqliteInstitutionalMemory(Path(directory) / "memory.db")
            with self.assertRaisesRegex(ValueError, "cannot close"):
                InstitutionalMemory(archive).close_market_day(date(2026, 8, 5), NOW)

    def test_duplicate_memory_and_duplicate_closure_cannot_overwrite_history(self) -> None:
        with TemporaryDirectory() as directory:
            archive = SqliteInstitutionalMemory(Path(directory) / "memory.db")
            memory = InstitutionalMemory(archive)
            arguments = (
                MemoryCategory.RESEARCH,
                NOW,
                NOW,
                "research:1",
                "Research proposal retained",
                '{"proposal":"1"}',
            )
            memory.remember(*arguments)
            with self.assertRaises(sqlite3.IntegrityError):
                memory.remember(*arguments)
            memory.close_market_day(date(2026, 8, 5), NOW)
            with self.assertRaises(sqlite3.IntegrityError):
                memory.close_market_day(date(2026, 8, 5), NOW)


if __name__ == "__main__":
    unittest.main()
