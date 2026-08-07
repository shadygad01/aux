"""Tests for the real MACD momentum indicator (no network, pure math)."""

from __future__ import annotations

import unittest

from packages.infrastructure.momentum import build_momentum_assessment, compute_ema, compute_macd


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


class BuildMomentumAssessmentTests(unittest.TestCase):
    def test_insufficient_data_returns_none(self) -> None:
        self.assertIsNone(build_momentum_assessment([1.0, 2.0, 3.0]))

    def test_carries_the_real_macd_line_and_histogram(self) -> None:
        closes = [100.0 + i * 0.5 for i in range(60)]
        macd = compute_macd(closes)
        assert macd is not None
        assessment = build_momentum_assessment(closes)
        self.assertIsNotNone(assessment)
        assert assessment is not None
        self.assertEqual(assessment.macd_value, macd.macd_line)
        self.assertEqual(assessment.histogram, macd.histogram)
        self.assertIsNone(assessment.slope)

    def test_no_crossover_without_enough_history_for_a_prior_bar(self) -> None:
        closes = [100.0 + i for i in range(35)]  # exactly slow(26) + signal(9)
        assessment = build_momentum_assessment(closes)
        self.assertIsNotNone(assessment)
        assert assessment is not None
        self.assertFalse(assessment.crossover_confirmed)

    def test_detects_a_genuine_bullish_crossover_on_the_bar_it_happens(self) -> None:
        # A sustained downtrend (histogram stays negative) followed by a sharp
        # rally: the histogram flips sign exactly on this closing bar.
        closes = [200.0 - i * 0.5 for i in range(50)] + [175.0 + i * 3.0 for i in range(1, 2)]
        assessment = build_momentum_assessment(closes)
        self.assertIsNotNone(assessment)
        assert assessment is not None
        assert assessment.histogram is not None
        self.assertGreater(assessment.histogram, 0)
        self.assertTrue(assessment.crossover_confirmed)

    def test_no_crossover_one_bar_before_the_flip(self) -> None:
        closes = [200.0 - i * 0.5 for i in range(50)]
        assessment = build_momentum_assessment(closes)
        self.assertIsNotNone(assessment)
        assert assessment is not None
        assert assessment.histogram is not None
        self.assertLess(assessment.histogram, 0)
        self.assertFalse(assessment.crossover_confirmed)


if __name__ == "__main__":
    unittest.main()
