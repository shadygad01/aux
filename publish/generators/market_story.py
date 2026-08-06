"""Generate market_story.json — publishes canonical MarketStory artifact.

Every stage narrative used to be a fixed fictional string (a hardcoded
"Price (3340.0) trades below equilibrium", a permanent "BUY" thesis, a
claimed "MACD histogram expansion" that nothing computed) regardless of
real market conditions or the date. This builds the same seven stages
from the same real observation/decision/macro pipeline the other
artifacts use.
"""

from __future__ import annotations

import json
import logging
import sys
from datetime import UTC, datetime
from pathlib import Path

from packages.application import DecisionEngine
from packages.domain import (
    Decision,
    DecisionPolicy,
    DecisionVerdict,
    MacroAssessment,
    MarketObservation,
    MarketStory,
    MarketStoryStage,
    StoryStageDetail,
    StructureBias,
)
from packages.infrastructure import JsonDecisionLogger
from packages.infrastructure.live_collector import LiveMarketCollector
from packages.infrastructure.macro_collectors import MacroCollector
from packages.infrastructure.momentum import MacdResult, compute_macd
from packages.infrastructure.smc_detector import (
    MIN_CANDLES_FOR_STRUCTURE,
    build_observation_from_candles,
)
from packages.infrastructure.yahoo_chart import fetch_yahoo_candles

from .envelope import build_envelope

GENERATOR = "publish.generators.market_story"
SCHEMA_VERSION = "1.0.0"
GOLD_TICKER = "GC=F"


def generate(output_path: Path) -> None:
    """Generate canonical market_story.json artifact from real live data."""
    logging.basicConfig(level=logging.WARNING, stream=sys.stderr)
    logger = logging.getLogger("gold_brain.publish")

    now = datetime.now(UTC)
    stamp = now.strftime("%Y%m%d%H%M")

    obs, macd_closes = _fetch_observation_and_closes()
    macd = compute_macd(macd_closes) if macd_closes else None

    macro_collector = MacroCollector(timeout_seconds=2)
    macro_ctx = macro_collector.acquire_macro_context(now)
    macro_assessment = macro_collector.evaluate_macro_assessment(macro_ctx, now)

    # Captured after every fetch above — evaluating against a timestamp taken
    # before slow network calls could make obs.observed_at land after it,
    # wrongly tripping the engine's "observation timestamp is in the future"
    # gate. story_id/stamp above stay tied to the original `now`; that's just
    # a label and isn't subject to the freshness check.
    evaluated_at = datetime.now(UTC)
    policy = DecisionPolicy()
    decision = DecisionEngine(policy, JsonDecisionLogger(logger)).evaluate(obs, evaluated_at)

    stages = (
        _macro_stage(macro_assessment, stamp),
        _bias_stage(obs, stamp),
        _discount_stage(obs, policy, stamp),
        _liquidity_stage(obs, stamp),
        _momentum_stage(macd, stamp),
        _smc_stage(obs, stamp),
        _thesis_stage(decision, stamp),
    )

    story = MarketStory(
        story_id=f"STORY-{stamp}-01",
        symbol=obs.symbol,
        timeframe=obs.timeframe,
        evolution_summary=_evolution_summary(decision),
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


def _fetch_observation_and_closes() -> tuple[MarketObservation, list[float]]:
    """Fetch H1 candles once for both structure and MACD. Falls back to
    LiveMarketCollector's own honest fallback tiers if candles are too few."""
    try:
        candles = fetch_yahoo_candles(GOLD_TICKER, "1h", "1mo", timeout_seconds=5)
    except Exception:
        candles = []

    if len(candles) >= MIN_CANDLES_FOR_STRUCTURE:
        obs = build_observation_from_candles(
            candles,
            symbol="XAUUSD",
            timeframe="H1",
            source="live-api:yahoo-finance-gold-futures-1h",
        )
        return obs, [c.close for c in candles]

    obs, _source = LiveMarketCollector().fetch_live_observation()
    return obs, []


def _macro_stage(assessment: MacroAssessment, stamp: str) -> StoryStageDetail:
    if assessment.macro_score > 0.5:
        status = "BULLISH_FOR_GOLD"
    elif assessment.macro_score < 0.5:
        status = "BEARISH_FOR_GOLD"
    else:
        status = "NEUTRAL"
    narrative = (
        "; ".join(assessment.evidence) if assessment.evidence else "No macro evidence collected."
    )
    return StoryStageDetail(
        stage=MarketStoryStage.MACRO,
        title="Macro Environment",
        status=status,
        narrative=narrative,
        evidence_ids=(f"EVD-MACRO-{stamp}",),
    )


def _bias_stage(obs: MarketObservation, stamp: str) -> StoryStageDetail:
    if obs.structure is None:
        return StoryStageDetail(
            stage=MarketStoryStage.BIAS,
            title="Structural Bias",
            status="UNKNOWN",
            narrative="No structure evidence available from the live feed.",
            evidence_ids=(f"EVD-BIAS-{stamp}",),
        )
    bos_clause = (
        "with a confirmed break of structure"
        if obs.structure.break_of_structure
        else "without a confirmed break of structure yet"
    )
    return StoryStageDetail(
        stage=MarketStoryStage.BIAS,
        title="Structural Bias",
        status=obs.structure.bias.value,
        narrative=f"{obs.timeframe} structure is {obs.structure.bias.value} {bos_clause}.",
        evidence_ids=(f"EVD-BIAS-{stamp}",),
    )


def _discount_stage(obs: MarketObservation, policy: DecisionPolicy, stamp: str) -> StoryStageDetail:
    if obs.dealing_range is None:
        return StoryStageDetail(
            stage=MarketStoryStage.DISCOUNT,
            title="Dealing Range Location",
            status="UNKNOWN",
            narrative="No dealing range evidence available.",
            evidence_ids=(f"EVD-LOC-{stamp}",),
        )
    dr = obs.dealing_range
    location = dr.location(policy.equilibrium_band)
    narrative = (
        f"Price ({dr.current_price:.2f}) trades in {location.value.lower()} of the "
        f"[{dr.low:.2f}-{dr.high:.2f}] dealing range."
    )
    return StoryStageDetail(
        stage=MarketStoryStage.DISCOUNT,
        title="Dealing Range Location",
        status=location.value,
        narrative=narrative,
        evidence_ids=(f"EVD-LOC-{stamp}",),
    )


def _liquidity_stage(obs: MarketObservation, stamp: str) -> StoryStageDetail:
    swept = [event for event in obs.liquidity if event.swept]
    if not swept:
        return StoryStageDetail(
            stage=MarketStoryStage.LIQUIDITY,
            title="Liquidity Sweeps",
            status="NOT_SWEPT",
            narrative="No liquidity sweep detected in the current observation.",
            evidence_ids=(f"EVD-LIQ-{stamp}",),
        )
    parts = []
    for event in swept:
        side = event.side.value.replace("_", " ").title()
        confirmation = (
            "with displacement confirmation"
            if event.displacement_confirmed
            else "without confirmed displacement"
        )
        parts.append(f"{side} liquidity swept {confirmation}")
    return StoryStageDetail(
        stage=MarketStoryStage.LIQUIDITY,
        title="Liquidity Sweeps",
        status=f"{swept[0].side.value}_SWEPT",
        narrative="; ".join(parts) + ".",
        evidence_ids=(f"EVD-LIQ-{stamp}",),
    )


def _momentum_stage(macd: MacdResult | None, stamp: str) -> StoryStageDetail:
    if macd is None:
        return StoryStageDetail(
            stage=MarketStoryStage.MOMENTUM,
            title="Momentum Alignment",
            status="UNKNOWN",
            narrative="Insufficient candle history to compute MACD.",
            evidence_ids=(f"EVD-MOM-{stamp}",),
        )
    status = "BULLISH" if macd.bullish else "BEARISH"
    narrative = (
        f"MACD histogram is {macd.histogram:+.4f} "
        f"(MACD {macd.macd_line:+.4f}, signal {macd.signal_line:+.4f}), {status.lower()}."
    )
    return StoryStageDetail(
        stage=MarketStoryStage.MOMENTUM,
        title="Momentum Alignment",
        status=status,
        narrative=narrative,
        evidence_ids=(f"EVD-MOM-{stamp}",),
    )


def _smc_stage(obs: MarketObservation, stamp: str) -> StoryStageDetail:
    bos = bool(obs.structure and obs.structure.break_of_structure)
    directional = bool(obs.structure and obs.structure.bias is not StructureBias.NEUTRAL)
    swept = any(event.swept and event.displacement_confirmed for event in obs.liquidity)
    validated = bos and directional and swept

    if validated:
        narrative = "Confirmed break of structure and a displaced liquidity sweep both align."
    else:
        gaps = []
        if not directional:
            gaps.append("no directional structure bias")
        if not bos:
            gaps.append("no confirmed break of structure")
        if not swept:
            gaps.append("no displaced liquidity sweep")
        narrative = f"SMC setup incomplete: {', '.join(gaps)}."

    return StoryStageDetail(
        stage=MarketStoryStage.SMC,
        title="Smart Money Setup",
        status="VALIDATED" if validated else "NOT_VALIDATED",
        narrative=narrative,
        evidence_ids=(f"EVD-SMC-{stamp}",),
    )


def _thesis_stage(decision: Decision, stamp: str) -> StoryStageDetail:
    text = decision.reasons or decision.conflicts or decision.missing_evidence
    narrative = " ".join(text) if text else f"{decision.verdict.value} evaluation."
    return StoryStageDetail(
        stage=MarketStoryStage.THESIS,
        title="Current Market Thesis",
        status=decision.verdict.value,
        narrative=narrative,
        evidence_ids=(f"EVD-DEC-{stamp}",),
    )


def _evolution_summary(decision: Decision) -> str:
    if decision.verdict is not DecisionVerdict.WAIT:
        reasons = "; ".join(decision.reasons)
        verdict = decision.verdict.value
        return (
            f"Real-time evaluation currently justifies searching for a {verdict} setup: {reasons}"
        )
    blockers = "; ".join(decision.conflicts or decision.missing_evidence)
    return f"Real-time evaluation does not justify a setup search: {blockers}"
