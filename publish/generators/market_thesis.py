"""Generate market_thesis.json — publishes canonical MarketThesis artifact."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from packages.domain import DecisionVerdict, MarketThesis, TradeQuality, TradeQualityGrade

from .envelope import build_envelope

GENERATOR = "publish.generators.market_thesis"
SCHEMA_VERSION = "1.0.0"


def generate(output_path: Path) -> None:
    """Generate canonical market_thesis.json artifact."""
    now = datetime(2026, 8, 5, 12, 0, 0, tzinfo=UTC)

    tq = TradeQuality(
        score=92,
        grade=TradeQualityGrade.EXCELLENT,
        breakdown={
            "structure": 30,
            "location": 25,
            "liquidity": 25,
            "macro_news": 12,
        },
        explanation=(
            "High-quality setup with SMC alignment, discount location, and Sell Side liquidity sweep."
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
