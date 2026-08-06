"""Generate market_thesis.json — publishes canonical MarketThesis artifact."""

from __future__ import annotations

import json
import logging
import sys
from datetime import UTC, datetime
from pathlib import Path

from packages.application import DecisionEngine, build_market_thesis, derive_trade_quality
from packages.application.execution_readiness_engine import ExecutionReadinessEngine
from packages.domain import DecisionPolicy
from packages.infrastructure import JsonDecisionLogger
from packages.infrastructure.live_collector import LiveMarketCollector

from .envelope import build_envelope

GENERATOR = "publish.generators.market_thesis"
SCHEMA_VERSION = "1.0.0"


def generate(output_path: Path) -> None:
    """Generate canonical market_thesis.json artifact using real-time dynamic market data."""
    logging.basicConfig(level=logging.WARNING, stream=sys.stderr)
    logger = logging.getLogger("gold_brain.publish")

    now = datetime.now(UTC)
    collector = LiveMarketCollector()
    obs, _ = collector.fetch_live_observation()

    policy = DecisionPolicy()
    decision = DecisionEngine(policy, JsonDecisionLogger(logger)).evaluate(obs, now)
    trade_quality = derive_trade_quality(obs, decision, policy)

    readiness = ExecutionReadinessEngine().evaluate(
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
