"""Generate execution_readiness.json — publishes canonical Execution Readiness artifact."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from packages.application import derive_trade_quality
from publish.composition import (
    build_decision_engine,
    build_decision_policy,
    build_execution_readiness_engine,
    build_live_market_collector,
    configure_publish_logger,
)

from .envelope import build_envelope

GENERATOR = "publish.generators.execution_readiness"
SCHEMA_VERSION = "1.0.0"


def generate(output_path: Path) -> None:
    """Generate canonical execution_readiness.json artifact using real-time dynamic market data."""
    logger = configure_publish_logger()

    collector = build_live_market_collector()
    obs, _ = collector.fetch_live_observation()
    # Captured after the fetch — evaluating against a timestamp taken before
    # a slow network call could make obs.observed_at land after it, wrongly
    # tripping the engine's "observation timestamp is in the future" gate.
    evaluated_at = datetime.now(UTC)

    policy = build_decision_policy()
    decision = build_decision_engine(policy, logger).evaluate(obs, evaluated_at)
    trade_quality = derive_trade_quality(obs, decision, policy)

    engine = build_execution_readiness_engine()
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
