"""Generate market_story.json — publishes canonical MarketStory artifact."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from packages.domain import MarketStory, MarketStoryStage, StoryStageDetail

from .envelope import build_envelope

GENERATOR = "publish.generators.market_story"
SCHEMA_VERSION = "1.0.0"


def generate(output_path: Path) -> None:
    """Generate canonical market_story.json artifact."""
    now = datetime(2026, 8, 5, 12, 0, 0, tzinfo=UTC)

    stages = (
        StoryStageDetail(
            stage=MarketStoryStage.MACRO,
            title="Macro Environment",
            status="NEUTRAL",
            narrative="Macro indicators show stable non-farm payroll expectations.",
            evidence_ids=("EVD-MACRO-01",),
        ),
        StoryStageDetail(
            stage=MarketStoryStage.BIAS,
            title="Structural Bias",
            status="BULLISH",
            narrative="H1 timeframe established higher high structure with confirmed BOS.",
            evidence_ids=("EVD-SMC-01",),
        ),
        StoryStageDetail(
            stage=MarketStoryStage.DISCOUNT,
            title="Dealing Range Location",
            status="DISCOUNT_ZONE",
            narrative="Price (3340.0) trades below equilibrium (3350.0) in discount zone.",
            evidence_ids=("EVD-LOC-01",),
        ),
        StoryStageDetail(
            stage=MarketStoryStage.LIQUIDITY,
            title="Liquidity Sweeps",
            status="SELL_SIDE_SWEPT",
            narrative="Sell Side liquidity swept below 3300 low with displacement.",
            evidence_ids=("EVD-LIQ-01",),
        ),
        StoryStageDetail(
            stage=MarketStoryStage.MOMENTUM,
            title="Momentum Alignment",
            status="ALIGNED",
            narrative="MACD histogram expansion confirms upward momentum alignment.",
            evidence_ids=("EVD-MOM-01",),
        ),
        StoryStageDetail(
            stage=MarketStoryStage.SMC,
            title="Smart Money Setup",
            status="VALIDATED",
            narrative="Order block mitigation in discount zone completes SMC validation.",
            evidence_ids=("EVD-SMC-02",),
        ),
        StoryStageDetail(
            stage=MarketStoryStage.THESIS,
            title="Current Market Thesis",
            status="BUY",
            narrative=(
                "Discount location and Sell Side liquidity sweep justify searching for BUY setup."
            ),
            evidence_ids=("EVD-DEC-01",),
        ),
    )

    story = MarketStory(
        story_id="STORY-20260805-01",
        symbol="XAUUSD",
        timeframe="H1",
        evolution_summary=(
            "Market evolved into a Sell Side liquidity sweep in discount, "
            "triggering a bullish SMC BOS setup."
        ),
        stages=stages,
        created_at=now,
        ttl_seconds=3600,
    )

    statement = (
        "Market Story explains how and why current market state evolved across macro, "
        "bias, discount, liquidity, momentum, and SMC stages."
    )

    payload = {
        "statement": statement,
        "story": story.to_dict(),
    }

    artifact = build_envelope(GENERATOR, SCHEMA_VERSION, payload)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(artifact, indent=2), encoding="utf-8")
    print(f"  [OK] {output_path.name}")
