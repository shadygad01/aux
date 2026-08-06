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
    VolatilityRegime,
)
from packages.infrastructure.market_hours import classify_session, is_weekend_closed

from .envelope import build_envelope

GENERATOR = "publish.generators.context"
SCHEMA_VERSION = "1.0.0"


def generate(output_path: Path) -> None:
    """Generate canonical context.json artifact.

    Timestamp, session, and weekend/open flags are derived from the real
    clock. macro_regime, volatility_regime, liquidity_conditions, news_window,
    and is_holiday remain fixed placeholders: there is no macro/news/holiday
    data source wired up yet, and no ATR-based volatility classifier — rather
    than fabricate values for those, they're left honestly static pending a
    real data source for each.
    """
    now = datetime.now(UTC)
    session = classify_session(now)
    weekend_closed = is_weekend_closed(now)
    context = MarketContext(
        context_id=f"CTX-{now:%Y%m%d%H%M}-{session.value}-01",
        symbol="XAUUSD",
        session=session,
        news_window=NewsWindow.CLEAR,
        macro_regime=MacroRegime.NEUTRAL,
        volatility_regime=VolatilityRegime.LOW_VOLATILITY,
        liquidity_conditions=LiquidityConditions.NORMAL,
        flags=EnvironmentFlags(
            is_holiday=False,
            is_weekend=weekend_closed,
            is_market_open=not weekend_closed,
            is_market_close=weekend_closed,
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
