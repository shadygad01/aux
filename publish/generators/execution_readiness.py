"""Generate execution_readiness.json — publishes canonical Execution Readiness artifact."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from packages.application.execution_readiness_engine import ExecutionReadinessEngine
from packages.domain import DecisionVerdict
from packages.infrastructure.execution_backtest import ExecutionBacktestEngine
from packages.infrastructure.live_collector import LiveMarketCollector
from .envelope import build_envelope

GENERATOR = "publish.generators.execution_readiness"
SCHEMA_VERSION = "1.0.0"


def generate(output_path: Path) -> None:
    """Generate canonical execution_readiness.json artifact using real-time dynamic market data."""
    now = datetime.now(UTC)
    collector = LiveMarketCollector()
    obs, _ = collector.fetch_live_observation()

    engine = ExecutionReadinessEngine()
    readiness = engine.evaluate(obs, DecisionVerdict.BUY, 94, None, now)

    backtest_engine = ExecutionBacktestEngine()
    metrics = backtest_engine.run_backtest()
    metrics_dict = {k: v.to_dict() for k, v in metrics.items()}

    statement = (
        "Execution Readiness separates Setup Quality from Entry Timing. "
        "Time alone never invalidates a setup; price structure and distance to liquidity dominate."
    )

    payload = {
        "statement": statement,
        "execution_readiness": readiness.to_dict(),
        "backtest_metrics": metrics_dict,
    }

    artifact = build_envelope(GENERATOR, SCHEMA_VERSION, payload)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(artifact, indent=2), encoding="utf-8")
    print(f"  [OK] {output_path.name}")
