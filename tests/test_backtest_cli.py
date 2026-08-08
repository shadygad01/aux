"""Tests for the backtest CLI's argument parsing and wiring (mocked
network -- no real Yahoo fetch)."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from test_real_candle_decision_reachability import (
    _bullish_break_then_discount_retracement_rows,
    _candles,
)

from backtest.cli import build_parser, main


class BuildParserTests(unittest.TestCase):
    def test_defaults(self) -> None:
        args = build_parser().parse_args([])
        self.assertEqual(args.ticker, "GC=F")
        self.assertEqual(args.days, 365)
        self.assertEqual(args.output_dir, Path("backtest/reports"))
        self.assertFalse(args.sensitivity)

    def test_overrides(self) -> None:
        args = build_parser().parse_args(
            ["--ticker", "XAUUSD=X", "--days", "30", "--output-dir", "/tmp/x", "--sensitivity"]
        )
        self.assertEqual(args.ticker, "XAUUSD=X")
        self.assertEqual(args.days, 30)
        self.assertEqual(args.output_dir, Path("/tmp/x"))
        self.assertTrue(args.sensitivity)


class MainTests(unittest.TestCase):
    def test_no_candles_fetched_returns_failure_without_writing_a_report(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp) / "reports"
            with patch("backtest.cli.fetch_h1_history", return_value=[]):
                result = main(["--output-dir", str(output_dir)])
            self.assertEqual(result, 1)
            self.assertFalse(output_dir.exists())

    def test_successful_run_writes_a_report(self) -> None:
        candles = _candles(_bullish_break_then_discount_retracement_rows())
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp) / "reports"
            with patch("backtest.cli.fetch_h1_history", return_value=candles):
                result = main(["--output-dir", str(output_dir)])
            self.assertEqual(result, 0)
            self.assertTrue((output_dir / "backtest_report.json").exists())
            self.assertTrue((output_dir / "backtest_report.md").exists())

    def test_sensitivity_flag_includes_the_sweep_in_the_report(self) -> None:
        candles = _candles(_bullish_break_then_discount_retracement_rows())
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp) / "reports"
            with patch("backtest.cli.fetch_h1_history", return_value=candles):
                result = main(["--output-dir", str(output_dir), "--sensitivity"])
            self.assertEqual(result, 0)
            markdown = (output_dir / "backtest_report.md").read_text()
            self.assertIn("Sensitivity sweep", markdown)


if __name__ == "__main__":
    unittest.main()
