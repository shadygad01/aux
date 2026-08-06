"""Generate multi_timeframe.json — publishes canonical Multi-Timeframe Scalping artifact."""

from __future__ import annotations

import json
import logging
import sys
from datetime import UTC, datetime
from pathlib import Path

from packages.application import DecisionEngine, build_market_thesis, derive_trade_quality
from packages.application.execution_readiness_engine import ExecutionReadinessEngine
from packages.application.multi_timeframe_engine import MultiTimeframeEngine
from packages.domain import DecisionPolicy
from packages.infrastructure import JsonDecisionLogger
from packages.infrastructure.live_collector import LiveMarketCollector

from .envelope import build_envelope

GENERATOR = "publish.generators.multi_timeframe"
SCHEMA_VERSION = "1.0.0"


def generate(output_path: Path) -> None:
    """Generate canonical multi_timeframe.json artifact using dynamic real-time market data."""
    logging.basicConfig(level=logging.WARNING, stream=sys.stderr)
    logger = logging.getLogger("gold_brain.publish")

    collector = LiveMarketCollector()
    htf_obs, _ = collector.fetch_live_observation()
    # A genuine M5 candle fetch — not the H1 structure relabeled as M5.
    ltf_obs, _ = collector.fetch_live_observation(interval="5m", chart_range="5d", timeframe="M5")
    # Captured after both fetches — evaluating against a timestamp taken
    # before slow network calls could make an obs.observed_at land after
    # it, wrongly tripping the engine's "observation in the future" gate.
    now = datetime.now(UTC)

    policy = DecisionPolicy()
    decision_engine = DecisionEngine(policy, JsonDecisionLogger(logger))
    htf_decision = decision_engine.evaluate(htf_obs, now)
    trade_quality = derive_trade_quality(htf_obs, htf_decision, policy)

    readiness = ExecutionReadinessEngine().evaluate(
        htf_obs, htf_decision.verdict, trade_quality.score, None, now
    )

    htf_thesis = build_market_thesis(
        thesis_id=f"THESIS-{now.strftime('%Y%m%d')}-01",
        observation=htf_obs,
        decision=htf_decision,
        trade_quality=trade_quality,
        execution_readiness=readiness,
    )

    mtf_engine = MultiTimeframeEngine()
    mtf_thesis = mtf_engine.evaluate_multi_timeframe(htf_thesis, ltf_obs, readiness, now)

    statement = (
        "Multi-Timeframe Scalping cascades M5/M15 entry triggers from H1 structural bias. "
        "Strictly blocks execution if lower timeframe signals contradict H1 bias."
    )

    payload = {
        "statement": statement,
        "multi_timeframe_thesis": mtf_thesis.to_dict(),
    }

    artifact = build_envelope(GENERATOR, SCHEMA_VERSION, payload)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(artifact, indent=2), encoding="utf-8")
    print(f"  [OK] {output_path.name}")
