"""Generate opportunity_identity.json — publishes canonical Opportunity Identity artifact."""

from __future__ import annotations

import json
import logging
import sys
from datetime import UTC, datetime
from pathlib import Path

from packages.application import DecisionEngine, build_market_thesis, derive_trade_quality
from packages.application.execution_readiness_engine import ExecutionReadinessEngine
from packages.application.opportunity_identity_engine import OpportunityIdentityEngine
from packages.domain import DecisionPolicy
from packages.infrastructure import JsonDecisionLogger
from packages.infrastructure.live_collector import LiveMarketCollector

from .envelope import build_envelope

GENERATOR = "publish.generators.opportunity_identity"
SCHEMA_VERSION = "1.0.0"


def generate(output_path: Path) -> None:
    """Generate canonical opportunity_identity.json artifact using real-time dynamic market data."""
    logging.basicConfig(level=logging.WARNING, stream=sys.stderr)
    logger = logging.getLogger("gold_brain.publish")

    collector = LiveMarketCollector()
    obs, _ = collector.fetch_live_observation()
    # Captured after the fetch — evaluating against a timestamp taken before
    # a slow network call could make obs.observed_at land after it, wrongly
    # tripping the engine's "observation timestamp is in the future" gate.
    now = datetime.now(UTC)

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

    engine_opp = OpportunityIdentityEngine()
    curr_opp, prev_opp = engine_opp.evaluate_opportunity(obs, thesis, readiness, now)

    statement = (
        "Opportunity Identity distinguishes between an aging setup and a new setup. "
        "Every opportunity receives a unique Opportunity ID constant throughout its lifetime."
    )

    payload = {
        "statement": statement,
        "current_opportunity": curr_opp.to_dict(),
        "previous_opportunity": prev_opp.to_dict() if prev_opp else None,
    }

    artifact = build_envelope(GENERATOR, SCHEMA_VERSION, payload)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(artifact, indent=2), encoding="utf-8")
    print(f"  [OK] {output_path.name}")
