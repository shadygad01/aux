"""Composition root and CLI for the backtest tool.

Run as: python -m backtest.cli --ticker GC=F --days 365 --output-dir backtest/reports/
"""

from __future__ import annotations

import argparse
import logging
import sys
from collections.abc import Sequence
from pathlib import Path

from packages.domain import DecisionPolicy

from .candle_fetcher import fetch_h1_history
from .report import write_report
from .statistics import run_and_summarize
from .statistics import sensitivity_sweep as run_sensitivity_sweep

LOGGER_NAME = "backtest"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Replay real H1 candles through the live DecisionEngine and report results."
    )
    parser.add_argument("--ticker", default="GC=F", help="Yahoo Finance ticker (default: GC=F)")
    parser.add_argument(
        "--days", type=int, default=365, help="Days of H1 history to request (default: 365)"
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("backtest/reports"),
        help="Directory to write backtest_report.json/.md into",
    )
    parser.add_argument(
        "--sensitivity",
        action="store_true",
        help="Also run the attention_threshold sensitivity sweep (secondary/optional)",
    )
    parser.add_argument(
        "--timeout-seconds", type=int, default=10, help="Per-request network timeout"
    )
    return parser


def main(arguments: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(arguments)
    logging.basicConfig(level=logging.INFO, stream=sys.stderr, force=True)
    logger = logging.getLogger(LOGGER_NAME)

    candles = fetch_h1_history(args.ticker, args.days, timeout_seconds=args.timeout_seconds)
    if not candles:
        logger.error("No candles were fetched -- nothing to backtest.")
        return 1

    policy = DecisionPolicy()
    summary, trades = run_and_summarize(candles, policy)

    sensitivity = None
    if args.sensitivity:
        sensitivity = run_sensitivity_sweep(candles, policy)

    write_report(
        args.output_dir,
        ticker=args.ticker,
        policy=policy,
        candle_count=len(candles),
        data_start=candles[0].timestamp,
        data_end=candles[-1].timestamp,
        summary=summary,
        trades=trades,
        sensitivity=sensitivity,
    )
    logger.info(f"Report written to {args.output_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
