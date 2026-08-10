"""Transparent consensus guidance derived from one synchronized snapshot."""

from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class GuidanceInput:
    name: str
    value: str
    direction: str
    available: bool


def build_directional_guidance(
    *,
    data_status: str,
    synchronized: bool,
    structure: str,
    macd_line: float | None,
    signal_line: float | None,
    histogram: float | None,
    macro_balance: str,
) -> dict[str, object]:
    """Return a fail-closed, unweighted three-family consensus.

    A lean is permitted only when structure, momentum, and macro are all
    available and unanimously point in the same direction.
    """
    structure_direction = {
        "BULLISH": "LEAN_BUY",
        "BEARISH": "LEAN_SELL",
        "NEUTRAL": "NEUTRAL",
    }.get(structure, "UNAVAILABLE")

    momentum_available = all(value is not None for value in (macd_line, signal_line, histogram))
    momentum_direction = "UNAVAILABLE"
    if momentum_available:
        assert macd_line is not None and signal_line is not None and histogram is not None
        if macd_line > signal_line and histogram > 0:
            momentum_direction = "LEAN_BUY"
        elif macd_line < signal_line and histogram < 0:
            momentum_direction = "LEAN_SELL"
        else:
            momentum_direction = "NEUTRAL"

    macro_direction = {
        "TAILWIND": "LEAN_BUY",
        "HEADWIND": "LEAN_SELL",
        "MIXED": "NEUTRAL",
        "NEUTRAL": "NEUTRAL",
    }.get(macro_balance, "UNAVAILABLE")

    inputs = [
        GuidanceInput(
            "H1_STRUCTURE", structure, structure_direction, structure_direction != "UNAVAILABLE"
        ),
        GuidanceInput(
            "MACD_12_26_9",
            "UNAVAILABLE" if not momentum_available else f"histogram={histogram:.4f}",
            momentum_direction,
            momentum_available,
        ),
        GuidanceInput(
            "DXY_US10Y_BALANCE", macro_balance, macro_direction, macro_direction != "UNAVAILABLE"
        ),
    ]

    label = "NEUTRAL"
    if not synchronized or data_status != "CURRENT":
        consistency = "INSUFFICIENT_DATA"
        reason = "Snapshot must be synchronized and CURRENT before directional guidance is allowed."
    elif not all(item.available for item in inputs):
        consistency = "INSUFFICIENT_DATA"
        reason = "At least one required evidence family is unavailable."
    else:
        directions = {item.direction for item in inputs}
        if directions == {"LEAN_BUY"}:
            label = "LEAN_BUY"
            consistency = "CONSISTENT"
            reason = "Structure, MACD momentum, and macro context unanimously lean higher."
        elif directions == {"LEAN_SELL"}:
            label = "LEAN_SELL"
            consistency = "CONSISTENT"
            reason = "Structure, MACD momentum, and macro context unanimously lean lower."
        else:
            consistency = "CONFLICT"
            reason = "Required evidence families do not unanimously point in one direction."

    return {
        "label": label,
        "consistency": consistency,
        "reason": reason,
        "inputs": [asdict(item) for item in inputs],
        "method": "Unweighted unanimity across H1 structure, MACD 12/26/9, and DXY/US10Y balance.",
        "execution_authority": False,
    }
