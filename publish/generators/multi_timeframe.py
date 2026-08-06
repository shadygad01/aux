"""Generate multi_timeframe.json — publishes canonical Multi-Timeframe Scalping artifact."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from packages.application.execution_readiness_engine import ExecutionReadinessEngine
from packages.application.multi_timeframe_engine import MultiTimeframeEngine
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

GENERATOR = "publish.generators.multi_timeframe"
SCHEMA_VERSION = "1.0.0"


def generate(output_path: Path) -> None:
    """Generate canonical multi_timeframe.json artifact."""
    now = datetime(2026, 8, 5, 12, 0, 0, tzinfo=UTC)

    htf_obs = MarketObservation(
        symbol="XAUUSD",
        timeframe="H1",
        observed_at=now,
        structure=MarketStructure(
            bias=StructureBias.BULLISH, break_of_structure=True, change_of_character=True
        ),
        dealing_range=DealingRange(low=3300.0, high=3400.0, current_price=3305.0),
        liquidity=(
            LiquidityEvent(
                side=LiquiditySide.SELL_SIDE, swept=True, displacement_confirmed=True
            ),
        ),
        source="reviewed-manual-observation",
    )

    engine_er = ExecutionReadinessEngine()
    readiness = engine_er.evaluate(htf_obs, DecisionVerdict.BUY, 94, None, now)

    tq = TradeQuality(
        score=94,
        grade=TradeQualityGrade.EXCELLENT,
        breakdown={"structure": 30, "location": 25, "liquidity": 25, "macro_news": 14},
        explanation="High-quality setup with H1 SMC alignment.",
    )

    htf_thesis = MarketThesis(
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
        reasons=("Bullish H1 BOS confirmed.", "Discount location."),
        conflicts=(),
        missing_evidence=(),
        evaluated_at=now,
        policy_version="v1-hypothesis-1",
        contract_version="1.0.0",
    )

    ltf_obs = MarketObservation(
        symbol="XAUUSD",
        timeframe="M5",
        observed_at=now,
        structure=MarketStructure(
            bias=StructureBias.BULLISH, break_of_structure=True, change_of_character=True
        ),
        dealing_range=DealingRange(low=3302.0, high=3312.0, current_price=3304.5),
        liquidity=(
            LiquidityEvent(
                side=LiquiditySide.SELL_SIDE, swept=True, displacement_confirmed=True
            ),
        ),
        source="reviewed-manual-observation-m5",
        higher_timeframe="H1",
        execution_timeframe="M5",
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
