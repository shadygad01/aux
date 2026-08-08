"""Generate multi_timeframe.json — publishes canonical Multi-Timeframe Scalping artifact."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from packages.application import build_market_thesis, derive_trade_quality
from packages.infrastructure.momentum import compute_atr
from packages.infrastructure.yahoo_chart import fetch_yahoo_candles
from publish.composition import (
    build_decision_engine,
    build_decision_policy,
    build_execution_readiness_engine,
    build_live_market_collector,
    build_macro_collector,
    build_multi_timeframe_engine,
    configure_publish_logger,
)

from .envelope import build_envelope

GENERATOR = "publish.generators.multi_timeframe"
SCHEMA_VERSION = "1.0.0"
GOLD_TICKER = "GC=F"
_ATR_INTERVAL_BY_EXECUTION_TIMEFRAME = {"M5": "5m", "M15": "15m"}
_ATR_CANDLE_RANGE = "5d"
_ATR_FETCH_TIMEOUT_SECONDS = 5


def generate(output_path: Path) -> None:
    """Generate canonical multi_timeframe.json artifact using dynamic real-time market data."""
    logger = configure_publish_logger()

    collector = build_live_market_collector()
    htf_obs, _ = collector.fetch_live_observation()
    # A genuine M5 candle fetch — not the H1 structure relabeled as M5.
    ltf_obs, _ = collector.fetch_live_observation(interval="5m", chart_range="5d", timeframe="M5")
    # Captured after both fetches — evaluating against a timestamp taken
    # before slow network calls could make an obs.observed_at land after
    # it, wrongly tripping the engine's "observation in the future" gate.
    now = datetime.now(UTC)

    policy = build_decision_policy()
    decision_engine = build_decision_engine(policy, logger)
    htf_decision = decision_engine.evaluate(htf_obs, now)
    trade_quality = derive_trade_quality(htf_obs, htf_decision, policy)

    macro_collector = build_macro_collector()
    macro_ctx = macro_collector.acquire_macro_context(now)
    macro_assessment = macro_collector.evaluate_macro_assessment(macro_ctx, now)

    readiness = build_execution_readiness_engine().evaluate(
        htf_obs, htf_decision.verdict, trade_quality.score, macro_assessment, now
    )

    htf_thesis = build_market_thesis(
        thesis_id=f"THESIS-{now.strftime('%Y%m%d')}-01",
        observation=htf_obs,
        decision=htf_decision,
        trade_quality=trade_quality,
        execution_readiness=readiness,
        macro_score=macro_assessment.macro_score,
    )

    atr = _fetch_execution_atr(ltf_obs.execution_timeframe)

    mtf_engine = build_multi_timeframe_engine()
    mtf_thesis = mtf_engine.evaluate_multi_timeframe(htf_thesis, ltf_obs, readiness, now, atr)

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


def _fetch_execution_atr(execution_timeframe: str) -> float | None:
    """ATR for the same execution timeframe the risk guidance applies to --
    M5 risk uses M5 volatility, M15 risk uses M15 volatility. A direct
    fetch_yahoo_candles call, mirroring market_story.py's existing pattern
    for reading raw OHLC without changing LiveMarketCollector's interface.
    Returns None (never fabricates a reading) on any fetch or data failure --
    the engine turns that into an honest "INSUFFICIENT_DATA" risk_status."""
    interval = _ATR_INTERVAL_BY_EXECUTION_TIMEFRAME.get(execution_timeframe, "5m")
    try:
        candles = fetch_yahoo_candles(
            GOLD_TICKER, interval, _ATR_CANDLE_RANGE, _ATR_FETCH_TIMEOUT_SECONDS
        )
    except Exception:
        return None
    return compute_atr(candles)
