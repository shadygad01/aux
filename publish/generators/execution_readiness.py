"""Generate execution_readiness.json — publishes canonical Execution Readiness artifact."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from packages.application.execution_readiness_engine import ExecutionReadinessEngine
from packages.domain import (
    DealingRange,
    DecisionVerdict,
    LiquidityEvent,
    LiquiditySide,
    MarketObservation,
    MarketStructure,
    StructureBias,
)
from packages.infrastructure.execution_backtest import ExecutionBacktestEngine

from .envelope import build_envelope

GENERATOR = "publish.generators.execution_readiness"
SCHEMA_VERSION = "1.0.0"


def generate(output_path: Path) -> None:
    """Generate canonical execution_readiness.json artifact."""
    now = datetime(2026, 8, 5, 12, 0, 0, tzinfo=UTC)

    # Observation where price has advanced (current_price 3368.0 -> LATE execution)
    obs = MarketObservation(
        symbol="XAUUSD",
        timeframe="H1",
        observed_at=now,
        structure=MarketStructure(
            bias=StructureBias.BULLISH, break_of_structure=True, change_of_character=True
        ),
        dealing_range=DealingRange(low=3300.0, high=3400.0, current_price=3368.0),
        liquidity=(
            LiquidityEvent(side=LiquiditySide.SELL_SIDE, swept=True, displacement_confirmed=True),
        ),
        source="reviewed-manual-observation",
    )

    engine = ExecutionReadinessEngine()
    readiness = engine.evaluate(obs, DecisionVerdict.BUY, 94, None, now)

    backtest_engine = ExecutionBacktestEngine()
    backtest_metrics = {k: v.to_dict() for k, v in backtest_engine.run_backtest().items()}

    statement = (
        "Execution Readiness separates Setup Quality (0-100) from Entry Timing (0-100). "
        "Evaluates whether a valid thesis is still executable without chasing price."
    )

    payload = {
        "statement": statement,
        "setup_quality_score": 94,
        "execution_readiness": readiness.to_dict(),
        "recommendation": "Wait for a new Discount retracement.",
        "backtest_metrics": backtest_metrics,
    }

    artifact = build_envelope(GENERATOR, SCHEMA_VERSION, payload)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(artifact, indent=2), encoding="utf-8")
    print(f"  [OK] {output_path.name}")
