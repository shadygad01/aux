"""Generate market_thesis.json — publishes canonical MarketThesis artifact."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from packages.application import build_market_thesis, derive_trade_quality
from publish.composition import (
    build_decision_engine,
    build_decision_policy,
    build_execution_readiness_engine,
    build_live_market_collector,
    configure_publish_logger,
)

from .envelope import build_envelope

GENERATOR = "publish.generators.market_thesis"
SCHEMA_VERSION = "1.0.0"


def generate(output_path: Path) -> None:
    """Generate canonical market_thesis.json artifact using real-time dynamic market data."""
    logger = configure_publish_logger()

    collector = build_live_market_collector()
    obs, _ = collector.fetch_live_observation()
    # Captured after the fetch — evaluating against a timestamp taken before
    # a slow network call could make obs.observed_at land after it, wrongly
    # tripping the engine's "observation timestamp is in the future" gate.
    now = datetime.now(UTC)

    policy = build_decision_policy()
    decision = build_decision_engine(policy, logger).evaluate(obs, now)
    trade_quality = derive_trade_quality(obs, decision, policy)

    readiness = build_execution_readiness_engine().evaluate(
        obs, decision.verdict, trade_quality.score, None, now
    )

    thesis = build_market_thesis(
        thesis_id=f"THESIS-{now.strftime('%Y%m%d')}-01",
        observation=obs,
        decision=decision,
        trade_quality=trade_quality,
        execution_readiness=readiness,
    )

    statement = (
        "Market Thesis is the sole canonical decision output unifying verdict, "
        "0-100 trade quality, confidence, uncertainty, and evidence lineage."
    )

    payload = {
        "statement": statement,
        "thesis": thesis.to_dict(),
    }

    artifact = build_envelope(GENERATOR, SCHEMA_VERSION, payload)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(artifact, indent=2), encoding="utf-8")
    print(f"  [OK] {output_path.name}")
