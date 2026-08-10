from __future__ import annotations

import unittest
from datetime import UTC, datetime
from unittest.mock import patch

from packages.infrastructure.macro_collectors import MacroCollector
from packages.infrastructure.smc_detector import Candle

NOW = datetime(2026, 8, 10, 12, tzinfo=UTC)


def candles(values: list[float]) -> list[Candle]:
    return [Candle(NOW, value, value, value, value) for value in values]


class MacroCollectorTests(unittest.TestCase):
    def test_publishes_observed_values_and_delta_only(self) -> None:
        with patch(
            "packages.infrastructure.macro_collectors.fetch_yahoo_candles",
            side_effect=[candles([100.0, 100.7]), candles([4.3, 4.1])],
        ):
            snapshot = MacroCollector().acquire_snapshot(NOW)
        dxy, us10y = snapshot.factors
        self.assertTrue(dxy.available)
        self.assertEqual((dxy.value, dxy.delta, dxy.direction), (100.7, 0.7, "UP"))
        self.assertTrue(us10y.available)
        self.assertEqual((us10y.value, us10y.delta, us10y.direction), (4.1, -0.2, "DOWN"))

    def test_network_failure_is_unavailable_not_neutral_or_default(self) -> None:
        with patch(
            "packages.infrastructure.macro_collectors.fetch_yahoo_candles",
            side_effect=TimeoutError("offline"),
        ):
            snapshot = MacroCollector().acquire_snapshot(NOW)
        for factor in snapshot.factors:
            self.assertFalse(factor.available)
            self.assertIsNone(factor.value)
            self.assertIsNone(factor.direction)
            self.assertEqual(factor.error, "FETCH_FAILED")

    def test_one_candle_is_explicitly_insufficient(self) -> None:
        with patch(
            "packages.infrastructure.macro_collectors.fetch_yahoo_candles",
            return_value=candles([4.2]),
        ):
            snapshot = MacroCollector().acquire_snapshot(NOW)
        self.assertTrue(all(not factor.available for factor in snapshot.factors))
        self.assertTrue(all(factor.error == "INSUFFICIENT_HISTORY" for factor in snapshot.factors))
