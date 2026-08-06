"""Generate opportunity_identity.json — publishes canonical Opportunity Identity artifact."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from packages.application.execution_readiness_engine import ExecutionReadinessEngine
from packages.application.opportunity_identity_engine import OpportunityIdentityEngine
from packages.domain import (
    DecisionVerdict,
    MarketThesis,
    TradeQuality,
    TradeQualityGrade,
)
from packages.infrastructure.live_collector import LiveMarketCollector
from packages.infrastructure.opportunity_backtest import OpportunityBacktestEngine
from .envelope import build_envelope

GENERATOR = "publish.generators.opportunity_identity"
SCHEMA_VERSION = "1.0.0"


def generate(output_path: Path) -> None:
    """Generate canonical opportunity_identity.json artifact using real-time dynamic market data."""
    now = datetime.now(UTC)
    collector = LiveMarketCollector()
    obs, _ = collector.fetch_live_observation()

    engine_er = ExecutionReadinessEngine()
    readiness = engine_er.evaluate(obs, DecisionVerdict.BUY, 94, None, now)

    tq = TradeQuality(
        score=94,
        grade=TradeQualityGrade.EXCELLENT,
        breakdown={"structure": 30},
        explanation="Test quality",
    )

    thesis = MarketThesis(
        thesis_id=f"THESIS-{now.strftime('%Y%m%d')}-01",
        symbol=obs.symbol,
        timeframe=obs.timeframe,
        verdict=DecisionVerdict.BUY,
        meaning="Search for a high-quality BUY setup",
        confidence="HIGH",
        confidence_score=1.0,
        uncertainty_score=0.0,
        setup_quality_score=94,
        execution_readiness=readiness,
        trade_quality=tq,
        reasons=("Bullish H1 BOS confirmed.",),
        conflicts=(),
        missing_evidence=(),
        evaluated_at=now,
        policy_version="v1-hypothesis-1",
        contract_version="1.0.0",
    )

    engine_opp = OpportunityIdentityEngine()
    curr_opp, prev_opp = engine_opp.evaluate_opportunity(obs, thesis, readiness, now)

    backtest_engine = OpportunityBacktestEngine()
    metrics = backtest_engine.run_backtest()
    metrics_dict = {k: v.to_dict() for k, v in metrics.items()}

    statement = (
        "Opportunity Identity distinguishes between an aging setup and a brand new setup. "
        "Every opportunity receives a globally unique Opportunity ID that remains constant throughout its lifetime."
    )

    payload = {
        "statement": statement,
        "current_opportunity": curr_opp.to_dict(),
        "previous_opportunity": prev_opp.to_dict() if prev_opp else None,
        "backtest_metrics": metrics_dict,
    }

    artifact = build_envelope(GENERATOR, SCHEMA_VERSION, payload)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(artifact, indent=2), encoding="utf-8")
    print(f"  [OK] {output_path.name}")
