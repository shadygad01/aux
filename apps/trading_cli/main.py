"""Composition root and presentation-only CLI for trading-opportunity evaluation."""

from __future__ import annotations

import argparse
import json
import logging
import sys
from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path

from packages.application import TradingOpportunityEngine
from packages.domain import TradingPolicy
from packages.infrastructure import (
    JsonLinesOpportunityRepository,
    JsonTradingDecisionLogger,
    trading_decision_to_json,
    trading_observation_from_json,
)
from packages.infrastructure.errors import ContractValidationError

LOGGER_NAME = "gold_brain.trading_decisions"
LOG_FORMAT = "%(message)s"
JSON_INDENT = 2
DEFAULT_LEDGER_PATH = Path("var/trading_opportunities.jsonl")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Evaluate an XAUUSD trading-opportunity observation"
    )
    parser.add_argument(
        "observation", type=Path, help="path to a versioned JSON trading observation"
    )
    parser.add_argument("--at", help="ISO-8601 evaluation time; defaults to current UTC time")
    parser.add_argument(
        "--ledger",
        type=Path,
        default=DEFAULT_LEDGER_PATH,
        help="append-only JSONL ledger path for evaluated opportunities",
    )
    return parser


def _evaluation_time(value: str | None) -> datetime:
    if value is None:
        return datetime.now(UTC)
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("--at must include a UTC offset")
    return parsed


def main(arguments: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(arguments)
    logging.basicConfig(level=logging.INFO, format=LOG_FORMAT, stream=sys.stderr, force=True)
    logger = logging.getLogger(LOGGER_NAME)

    try:
        raw_payload: object = json.loads(args.observation.read_text(encoding="utf-8"))
        observation = trading_observation_from_json(raw_payload)
        engine = TradingOpportunityEngine(
            TradingPolicy(),
            JsonTradingDecisionLogger(logger),
            JsonLinesOpportunityRepository(args.ledger),
        )
        decision = engine.evaluate(observation, _evaluation_time(args.at))
    except (OSError, ContractValidationError, ValueError, json.JSONDecodeError) as error:
        parser.error(f"observation={args.observation}; error={error}")

    print(json.dumps(trading_decision_to_json(decision), indent=JSON_INDENT))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
