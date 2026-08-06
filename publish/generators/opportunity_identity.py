"""Generate opportunity_identity.json — publishes canonical Opportunity Identity artifact."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from packages.application.execution_readiness_engine import ExecutionReadinessEngine
from packages.application.opportunity_identity_engine import OpportunityIdentityEngine
from packages.domain import (
    DealingRange,
    DecisionVerdict,
    LiquidityEvent,
    LiquiditySide,
    MarketObservation,
    MarketStructure,
    MarketThesis,
    OpportunityArchiveStatus,
    OpportunityIdentity,
    OpportunityLifecycleState,
    OpportunityOutcome,
    StructureBias,
    TradeQuality,
    TradeQualityGrade,
)
from packages.infrastructure.opportunity_backtest import OpportunityBacktestEngine

from .envelope import build_envelope

GENERATOR = "publish.generators.opportunity_identity"
SCHEMA_VERSION = "1.0.0"


def generate(output_path: Path) -> None:
    """Generate canonical opportunity_identity.json artifact."""
    now = datetime(2026, 8, 5, 12, 0, 0, tzinfo=UTC)

    obs = MarketObservation(
        symbol="XAUUSD",
        timeframe="H1",
        observed_at=now,
        structure=MarketStructure(
            bias=StructureBias.BULLISH, break_of_structure=True, change_of_character=True
        ),
        dealing_range=DealingRange(low=3300.0, high=3400.0, current_price=3345.0),
        liquidity=(
            LiquidityEvent(side=LiquiditySide.SELL_SIDE, swept=True, displacement_confirmed=True),
        ),
        source="reviewed-manual-observation",
    )

    engine_er = ExecutionReadinessEngine()
    readiness = engine_er.evaluate(obs, DecisionVerdict.BUY, 94, None, now)

    tq = TradeQuality(
        score=94,
        grade=TradeQualityGrade.EXCELLENT,
        breakdown={"structure": 30, "location": 25, "liquidity": 25, "macro_news": 14},
        explanation="High-quality setup with SMC alignment and Sell Side liquidity sweep.",
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
        reasons=("Bullish BOS confirmed.", "Discount location."),
        conflicts=(),
        missing_evidence=(),
        evaluated_at=now,
        policy_version="v1-hypothesis-1",
        contract_version="1.0.0",
    )

    engine_opp = OpportunityIdentityEngine()
    curr_opp, _ = engine_opp.evaluate_opportunity(obs, thesis, readiness, now)

    prev_opp = OpportunityIdentity(
        opportunity_id="OPP-20260804-003",
        symbol="XAUUSD",
        timeframe="H1",
        created_at=datetime(2026, 8, 4, 14, 0, 0, tzinfo=UTC),
        last_updated_at=datetime(2026, 8, 4, 18, 0, 0, tzinfo=UTC),
        creation_conditions=(
            "Structure: BULLISH (BOS=True)",
            "Liquidity Swept: SELL_SIDE at 3280.0",
        ),
        verdict=DecisionVerdict.BUY,
        setup_quality_score=88,
        max_setup_quality_score=92,
        execution_readiness=readiness,
        current_state=OpportunityLifecycleState.COMPLETED,
        outcome=OpportunityOutcome.WINNING,
        archive_status=OpportunityArchiveStatus.ARCHIVED,
        is_fresh=False,
    )

    backtest_engine = OpportunityBacktestEngine()
    backtest_metrics = {k: v.to_dict() for k, v in backtest_engine.run_backtest().items()}

    statement = (
        "Opportunity Identity distinguishes aging setups from new opportunities. "
        "Every opportunity maintains a globally unique ID throughout its lifetime."
    )

    payload = {
        "statement": statement,
        "current_opportunity": curr_opp.to_dict(),
        "previous_opportunity": prev_opp.to_dict(),
        "backtest_metrics": backtest_metrics,
    }

    artifact = build_envelope(GENERATOR, SCHEMA_VERSION, payload)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(artifact, indent=2), encoding="utf-8")
    print(f"  [OK] {output_path.name}")
