"""Generate execution_readiness.json — publishes canonical Execution Readiness artifact."""

from __future__ import annotations

import json
import logging
import sys
from datetime import UTC, datetime
from pathlib import Path

from packages.application import DecisionEngine, derive_trade_quality
from packages.application.execution_readiness_engine import ExecutionReadinessEngine
from packages.domain import DecisionPolicy
from packages.infrastructure import JsonDecisionLogger
from packages.infrastructure.live_collector import LiveMarketCollector

from .envelope import build_envelope

GENERATOR = "publish.generators.execution_readiness"
SCHEMA_VERSION = "1.0.0"


def generate(output_path: Path) -> None:
    """Generate canonical execution_readiness.json artifact using real-time dynamic market data."""
    logging.basicConfig(level=logging.WARNING, stream=sys.stderr)
    logger = logging.getLogger("gold_brain.publish")

    collector = LiveMarketCollector()
    obs, _ = collector.fetch_live_observation()
    # Captured after the fetch — evaluating against a timestamp taken before
    # a slow network call could make obs.observed_at land after it, wrongly
    # tripping the engine's "observation timestamp is in the future" gate.
    evaluated_at = datetime.now(UTC)

    policy = DecisionPolicy()
    decision = DecisionEngine(policy, JsonDecisionLogger(logger)).evaluate(obs, evaluated_at)
    trade_quality = derive_trade_quality(obs, decision, policy)

    engine = ExecutionReadinessEngine()
    readiness = engine.evaluate(obs, decision.verdict, trade_quality.score, None, evaluated_at)

    statement = (
        "Execution Readiness separates Setup Quality from Entry Timing. "
        "Time alone never invalidates a setup; price structure and distance to liquidity dominate."
    )

    payload = {
        "statement": statement,
        "execution_readiness": readiness.to_dict(),
    }

    artifact = build_envelope(GENERATOR, SCHEMA_VERSION, payload)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(artifact, indent=2), encoding="utf-8")
    print(f"  [OK] {output_path.name}")
