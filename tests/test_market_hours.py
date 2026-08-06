"""Deterministic tests for wall-clock trading-session classification."""

from __future__ import annotations

import unittest
from datetime import UTC, datetime

from packages.domain import TradingSession
from packages.infrastructure.market_hours import classify_session, is_weekend_closed


class SessionClassificationTests(unittest.TestCase):
    def test_asian_session_before_london_open(self) -> None:
        self.assertEqual(
            classify_session(datetime(2026, 8, 5, 3, 0, tzinfo=UTC)), TradingSession.ASIAN
        )

    def test_london_session(self) -> None:
        self.assertEqual(
            classify_session(datetime(2026, 8, 5, 10, 0, tzinfo=UTC)), TradingSession.LONDON
        )

    def test_london_new_york_overlap(self) -> None:
        self.assertEqual(
            classify_session(datetime(2026, 8, 5, 14, 0, tzinfo=UTC)), TradingSession.OVERLAP
        )

    def test_new_york_session_after_london_close(self) -> None:
        self.assertEqual(
            classify_session(datetime(2026, 8, 5, 19, 0, tzinfo=UTC)), TradingSession.NEW_YORK
        )

    def test_closed_gap_between_new_york_close_and_asian_open(self) -> None:
        self.assertEqual(
            classify_session(datetime(2026, 8, 5, 23, 0, tzinfo=UTC)), TradingSession.CLOSED
        )

    def test_weekend_is_closed_regardless_of_hour(self) -> None:
        self.assertEqual(
            classify_session(datetime(2026, 8, 8, 12, 0, tzinfo=UTC)), TradingSession.CLOSED
        )


class WeekendClosureTests(unittest.TestCase):
    def test_saturday_is_always_closed(self) -> None:
        self.assertTrue(is_weekend_closed(datetime(2026, 8, 8, 12, 0, tzinfo=UTC)))

    def test_sunday_before_reopen_is_closed(self) -> None:
        self.assertTrue(is_weekend_closed(datetime(2026, 8, 9, 12, 0, tzinfo=UTC)))

    def test_sunday_after_reopen_is_open(self) -> None:
        self.assertFalse(is_weekend_closed(datetime(2026, 8, 9, 23, 0, tzinfo=UTC)))

    def test_friday_after_close_is_closed(self) -> None:
        self.assertTrue(is_weekend_closed(datetime(2026, 8, 7, 23, 0, tzinfo=UTC)))

    def test_friday_before_close_is_open(self) -> None:
        self.assertFalse(is_weekend_closed(datetime(2026, 8, 7, 10, 0, tzinfo=UTC)))

    def test_weekday_is_open(self) -> None:
        self.assertFalse(is_weekend_closed(datetime(2026, 8, 5, 10, 0, tzinfo=UTC)))


if __name__ == "__main__":
    unittest.main()
