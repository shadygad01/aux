"""Generate market_thesis.json — publishes canonical MarketThesis artifact."""

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
    MarketThesis,
    StructureBias,
    TradeQuality,
    TradeQualityGrade,
)

from .envelope import build_envelope

GENERATOR = "publish.generators.market_thesis"
SCHEMA_VERSION = "1.0.0"


def generate(output_path: Path) -> None:
    """Generate canonical market_thesis.json artifact."""
    now = datetime(2026, 8, 5, 12, 0, 0, tzinfo=UTC)

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

    tq = TradeQuality(
        score=94,
        grade=TradeQualityGrade.EXCELLENT,
        breakdown={
            "structure": 30,
            "location": 25,
            "liquidity": 25,
            "macro_news": 14,
        },
        explanation=(
            "High-quality setup with SMC alignment, discount location, "
            "and Sell Side liquidity sweep."
        ),
    )

    thesis = MarketThesis(
        thesis_id="THESIS-20260805-01",
        symbol="XAUUSD",
        timeframe="H1",
        verdict=DecisionVerdict.BUY,
        meaning="Search for a high-quality BUY setup",
        confidence="HIGH",
        confidence_score=1.0,
        uncertainty_score=0.0,
        setup_quality_score=94,
        execution_readiness=readiness,
        trade_quality=tq,
        reasons=(
            "Bullish structure has a confirmed break of structure.",
            "Price is in discount, aligned with the BUY thesis.",
            "Sell Side liquidity was swept with displacement confirmation.",
        ),
        conflicts=(),
        missing_evidence=(),
        evaluated_at=now,
        policy_version="v1-hypothesis-1",
        contract_version="1.0.0",
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
