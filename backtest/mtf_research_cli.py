"""CLI for complete Dukascopy tick research and locked holdout evaluation."""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import sys
from collections.abc import Sequence
from datetime import UTC, datetime, timedelta
from pathlib import Path

from .dukascopy_ticks import build_manifest, download_range, write_manifest
from .mtf_research_runner import (
    ResearchPaths,
    build_derived_bars,
    run_discovery,
    run_holdout,
)
from .mtf_storage import TickArchive, read_bars
from .research_governance import ResearchSplit
from .tick_trade_simulator import ExecutionAssumptions

DEFAULT_START = datetime(2021, 8, 8, tzinfo=UTC)
DEFAULT_HOLDOUT_START = datetime(2024, 8, 8, tzinfo=UTC)
DEFAULT_END = datetime(2026, 8, 8, tzinfo=UTC)


def _date(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise argparse.ArgumentTypeError("date must include a timezone")
    return parsed.astimezone(UTC)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Leakage-safe XAUUSD tick pattern research")
    parser.add_argument("command", choices=("download", "build", "discover", "holdout"))
    parser.add_argument("--instrument", default="XAUUSD")
    parser.add_argument("--start", type=_date, default=DEFAULT_START)
    parser.add_argument("--holdout-start", type=_date, default=DEFAULT_HOLDOUT_START)
    parser.add_argument("--end", type=_date, default=DEFAULT_END)
    parser.add_argument("--raw-root", type=Path, default=Path("var/dukascopy/raw"))
    parser.add_argument("--derived-root", type=Path, default=Path("var/dukascopy/derived"))
    parser.add_argument("--report-root", type=Path, default=Path("backtest/reports/mtf_research"))
    parser.add_argument("--price-scale", type=int, default=1000)
    parser.add_argument("--commission-per-side", type=float, default=0.0)
    parser.add_argument("--slippage-per-side", type=float, default=0.0)
    parser.add_argument("--embargo-hours", type=int, default=120)
    parser.add_argument("--timeout-seconds", type=int, default=30)
    parser.add_argument("--workers", type=int, default=8)
    return parser


def _paths(args: argparse.Namespace) -> ResearchPaths:
    return ResearchPaths(args.raw_root, args.derived_root, args.report_root)


def _archive(args: argparse.Namespace) -> TickArchive:
    return TickArchive(
        args.raw_root, args.instrument, price_scale=args.price_scale, cache_hours=168
    )


def _split(args: argparse.Namespace) -> ResearchSplit:
    return ResearchSplit(
        discovery_start=args.start,
        holdout_start=args.holdout_start,
        holdout_end=args.end,
        embargo=timedelta(hours=args.embargo_hours),
    )


def _assumptions(args: argparse.Namespace) -> ExecutionAssumptions:
    return ExecutionAssumptions(
        commission_per_side_points=args.commission_per_side,
        slippage_per_side_points=args.slippage_per_side,
        max_trades_per_day=3,
    )


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main(arguments: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(arguments)
    logging.basicConfig(level=logging.INFO, stream=sys.stderr, force=True)
    logger = logging.getLogger("mtf-research")
    if not args.start < args.holdout_start < args.end:
        logger.error("start, holdout-start, and end must be increasing")
        return 2
    if args.command == "download":
        downloaded, missing = download_range(
            args.instrument,
            args.start,
            args.end,
            args.raw_root,
            timeout_seconds=args.timeout_seconds,
            workers=args.workers,
        )
        manifest = build_manifest(
            args.instrument,
            args.start,
            args.end,
            args.raw_root,
            price_scale=args.price_scale,
        )
        write_manifest(manifest, args.report_root / "tick_manifest.json")
        logger.info(f"downloaded={downloaded} unavailable_hours={missing}")
        return 0
    archive = _archive(args)
    paths = _paths(args)
    if args.command == "build":
        source_manifest = args.report_root / "tick_manifest.json"
        if not source_manifest.exists():
            logger.error("tick manifest is required before building derived bars")
            return 2
        derived = build_derived_bars(archive, args.start, args.end, args.derived_root)
        payload = {
            "schema_version": "1.0.0",
            "source_manifest": str(source_manifest),
            "source_manifest_sha256": _sha256(source_manifest),
            "files": [
                {
                    "path": str(path),
                    "sha256": _sha256(path),
                    "bars": len(read_bars(path)),
                }
                for path in derived
            ],
        }
        args.report_root.mkdir(parents=True, exist_ok=True)
        (args.report_root / "derived_manifest.json").write_text(
            json.dumps(payload, indent=2), encoding="utf-8"
        )
        return 0
    if args.command == "discover":
        selected = run_discovery(
            paths,
            archive,
            _split(args),
            _assumptions(args),
            frozen_at=datetime.now(UTC),
        )
        logger.info(f"frozen_patterns={len(selected)}")
        return 0
    results = run_holdout(paths, archive, _split(args), _assumptions(args))
    logger.info(f"holdout_patterns={len(results)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
