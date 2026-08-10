"""Publish one synchronized market snapshot with fail-closed guidance.

The dashboard consumes this artifact only for market information.  It exposes
observations, arithmetic, provenance, and limitations; it deliberately emits
no trade command, confidence score, setup score, or execution plan.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from packages.domain.guidance import build_directional_guidance
from packages.infrastructure.market_hours import classify_session, is_weekend_closed
from packages.infrastructure.momentum import compute_atr
from packages.infrastructure.smc_detector import SwingKind, find_swings
from publish.composition import build_live_market_collector, build_macro_collector

from .envelope import build_envelope

GENERATOR = "publish.generators.market_data"
SCHEMA_VERSION = "1.0.0"


def _gold_effect(factor: str, direction: str) -> str:
    if factor == "DXY":
        if direction == "UP":
            return "HEADWIND"
        if direction == "DOWN":
            return "TAILWIND"
    if factor == "US10Y":
        if direction == "UP":
            return "HEADWIND"
        if direction == "DOWN":
            return "TAILWIND"
    return "NEUTRAL"


def generate(output_path: Path) -> None:
    captured_at = datetime.now(UTC)
    snapshot = build_live_market_collector().fetch_live_snapshot()
    observation = snapshot.observation
    macro = build_macro_collector().acquire_snapshot(captured_at)

    age_seconds = max(0, int((captured_at - observation.observed_at).total_seconds()))
    data_status = "CURRENT" if age_seconds <= 3600 else "STALE"
    if snapshot.spot_price is None:
        data_status = "UNAVAILABLE"

    range_payload: dict[str, object] | None = None
    if observation.dealing_range is not None:
        dealing_range = observation.dealing_range
        width = dealing_range.high - dealing_range.low
        midpoint = (dealing_range.high + dealing_range.low) / 2
        position = (dealing_range.current_price - dealing_range.low) / width * 100
        range_payload = {
            "low": dealing_range.low,
            "high": dealing_range.high,
            "midpoint": round(midpoint, 4),
            "candle_close": dealing_range.current_price,
            "position_pct": round(position, 2),
            "side_of_midpoint": "BELOW" if dealing_range.current_price < midpoint else "ABOVE",
            "definition": (
                "Two most recent alternating confirmed H1 fractal swings, "
                "extended to include the latest close."
            ),
        }

    swings = find_swings(snapshot.candles) if snapshot.candles else []
    highs = [s for s in swings if s.kind is SwingKind.HIGH]
    lows = [s for s in swings if s.kind is SwingKind.LOW]
    swing_evidence = {
        "recent_highs": [
            {"price": swing.price, "observed_at": swing.timestamp.isoformat()}
            for swing in highs[-2:]
        ],
        "recent_lows": [
            {"price": swing.price, "observed_at": swing.timestamp.isoformat()}
            for swing in lows[-2:]
        ],
    }

    structure = observation.structure
    structure_payload = {
        "classification": structure.bias.value if structure else "UNAVAILABLE",
        "break_of_structure_detected": structure.break_of_structure if structure else None,
        "change_of_character_detected": structure.change_of_character if structure else None,
        "evidence": swing_evidence,
        "method": (
            "Last two confirmed fractal swing highs and lows; classification is "
            "algorithm-dependent, not a forecast."
        ),
    }

    liquidity = [
        {
            "side": ("ABOVE_SWING_HIGH" if item.side.value == "BUY_SIDE" else "BELOW_SWING_LOW"),
            "level": item.level,
            "sweep_detected": item.swept,
            "displacement_detected": item.displacement_confirmed,
        }
        for item in observation.liquidity
    ]

    momentum = None
    if snapshot.momentum is not None:
        momentum = {
            "macd_line": snapshot.momentum.macd_line,
            "signal_line": snapshot.momentum.signal_line,
            "histogram": snapshot.momentum.histogram,
            "parameters": "EMA 12/26/9",
        }

    factors: list[dict[str, object]] = []
    for factor in macro.factors:
        item = factor.to_dict()
        item["gold_effect"] = (
            _gold_effect(factor.name, factor.direction or "") if factor.available else None
        )
        factors.append(item)
    effects = {
        str(factor["gold_effect"]) for factor in factors if factor["gold_effect"] is not None
    }
    if not effects:
        macro_balance = "UNAVAILABLE"
    elif {"HEADWIND", "TAILWIND"} <= effects:
        macro_balance = "MIXED"
    else:
        macro_balance = next(iter(effects))

    guidance = build_directional_guidance(
        data_status=data_status,
        synchronized=True,
        structure=structure.bias.value if structure else "UNAVAILABLE",
        macd_line=snapshot.momentum.macd_line if snapshot.momentum else None,
        signal_line=snapshot.momentum.signal_line if snapshot.momentum else None,
        histogram=snapshot.momentum.histogram if snapshot.momentum else None,
        macro_balance=macro_balance,
    )

    payload = {
        "purpose": "Auditable market measurements with fail-closed directional guidance.",
        "snapshot": {
            "snapshot_id": f"MKT-{captured_at:%Y%m%dT%H%M%SZ}",
            "symbol": observation.symbol,
            "timeframe": observation.timeframe,
            "captured_at": captured_at.isoformat(),
            "observation_at": observation.observed_at.isoformat(),
            "source": snapshot.source,
            "synchronized": True,
            "data_status": data_status,
            "age_seconds": age_seconds,
            "price": {
                "spot_usd_per_oz": snapshot.spot_price,
                "technical_candle_close": observation.dealing_range.current_price
                if observation.dealing_range
                else None,
                "note": (
                    "Technicals use spot-anchored GC=F candle shape; the spot quote is "
                    "the authoritative displayed price."
                ),
            },
            "range": range_payload,
            "structure": structure_payload,
            "liquidity_observations": liquidity,
            "indicators": {
                "macd": momentum,
                "atr_14_h1": compute_atr(snapshot.candles) if snapshot.candles else None,
            },
            "macro": {
                "captured_at": macro.captured_at.isoformat(),
                "factors": factors,
                "balance": macro_balance,
                "balance_note": (
                    "Unweighted DXY/US10Y context used as one of three required guidance families."
                ),
                "excluded": ["US02Y", "economic-news calendar", "composite macro score"],
            },
            "market_clock": {
                "session": classify_session(captured_at).value,
                "weekend": is_weekend_closed(captured_at),
                "source": "UTC clock rules",
            },
            "guidance": guidance,
            "limitations": [
                "Structure and sweep labels are deterministic detector outputs, not predictions.",
                "A non-detected sweep means only that this detector found none in its "
                "observation window.",
                "Macro factor effects are conventional interpretations and are not "
                "validated trading edge.",
                "Directional guidance is an unweighted consistency label, not a trade "
                "command or tested edge.",
            ],
        },
    }
    artifact = build_envelope(GENERATOR, SCHEMA_VERSION, payload)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(artifact, indent=2), encoding="utf-8")
