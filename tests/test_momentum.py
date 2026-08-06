"""Tests for the real MACD momentum indicator (no network, pure math)."""

from __future__ import annotations

import unittest

from packages.infrastructure.momentum import compute_ema, compute_macd


class ComputeEmaTests(unittest.TestCase):
    def test_empty_input_returns_empty(self) -> None:
        self.assertEqual(compute_ema([], 12), [])

    def test_flat_series_stays_flat(self) -> None:
        ema = compute_ema([100.0] * 10, 5)
        self.assertTrue(all(v == 100.0 for v in ema))

    def test_length_matches_input(self) -> None:
        values = [float(i) for i in range(20)]
        self.assertEqual(len(compute_ema(values, 5)), len(values))


class ComputeMacdTests(unittest.TestCase):
    def test_insufficient_data_returns_none(self) -> None:
        self.assertIsNone(compute_macd([1.0, 2.0, 3.0]))

    def test_boundary_length_returns_none_one_short(self) -> None:
        closes = [100.0 + i for i in range(34)]  # slow(26) + signal(9) - 1
        self.assertIsNone(compute_macd(closes))

    def test_sustained_uptrend_is_bullish(self) -> None:
        closes = [100.0 + i * 0.5 for i in range(60)]
        result = compute_macd(closes)
        self.assertIsNotNone(result)
        assert result is not None
        self.assertTrue(result.bullish)
        self.assertGreater(result.histogram, 0)

    def test_sustained_downtrend_is_bearish(self) -> None:
        closes = [200.0 - i * 0.5 for i in range(60)]
        result = compute_macd(closes)
        self.assertIsNotNone(result)
        assert result is not None
        self.assertFalse(result.bullish)
        self.assertLess(result.histogram, 0)

    def test_flat_series_has_zero_histogram(self) -> None:
        result = compute_macd([100.0] * 60)
        self.assertIsNotNone(result)
        assert result is not None
        self.assertEqual(result.histogram, 0.0)
        self.assertFalse(result.bullish)


if __name__ == "__main__":
    unittest.main()
