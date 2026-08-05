"""Generate context.json — publishes canonical MarketContext environment artifact."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from packages.domain import (
    EnvironmentFlags,
    LiquidityConditions,
    MacroRegime,
    MarketContext,
    NewsWindow,
    TradingSession,
    VolatilityRegime,
)

from .envelope import build_envelope

GENERATOR = "publish.generators.context"
SCHEMA_VERSION = "1.0.0"


def generate(output_path: Path) -> None:
    """Generate canonical context.json artifact."""
    now = datetime(2026, 8, 5, 12, 0, 0, tzinfo=UTC)
    context = MarketContext(
        context_id="CTX-20260805-LONDON-01",
        symbol="XAUUSD",
        session=TradingSession.LONDON,
        news_window=NewsWindow.CLEAR,
        macro_regime=MacroRegime.NEUTRAL,
        volatility_regime=VolatilityRegime.LOW_VOLATILITY,
        liquidity_conditions=LiquidityConditions.NORMAL,
        flags=EnvironmentFlags(
            is_holiday=False,
            is_weekend=False,
            is_market_open=True,
            is_market_close=False,
        ),
        observed_at=now,
        ttl_seconds=3600,
        source="canonical-context-provider",
    )

    statement = (
        "Context is NOT Evidence. Context is NOT Knowledge. "
        "Context describes the environment in which evidence must be interpreted."
    )

    payload = {
        "statement": statement,
        "context": context.to_dict(),
    }

    artifact = build_envelope(GENERATOR, SCHEMA_VERSION, payload)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(artifact, indent=2), encoding="utf-8")
    print(f"  [OK] {output_path.name}")
