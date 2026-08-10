"""Fail-closed early reversal-watch heuristic derived from one synchronized snapshot.

This is a pattern watch, not a tested trading edge. This repository's own H-028
research (backtest/reports/h028_supplied_5y_2026-08-10.md) evaluated a closely
related premium/discount structural-break reversal rule against five years of
tick data and rejected it: holdout profit factor was 1.087 (below the 1.20
acceptance gate) and the bootstrap expectancy lower bound was negative. This
label exists to surface the pattern for manual review only.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass

WATCH_SELL = "WATCH_SELL"
WATCH_BUY = "WATCH_BUY"
NONE_LABEL = "NONE"
UNAVAILABLE = "UNAVAILABLE"


@dataclass(frozen=True)
class ReversalSignalEvidence:
    name: str
    value: str


def build_reversal_signal(
    *,
    structure_bias: str,
    break_of_structure: bool | None,
    change_of_character: bool | None,
    range_location: str | None,
    macd_line: float | None,
) -> dict[str, object]:
    """Return a fail-closed "Reversal Signal Start" watch label.

    A watch fires only when structure bias, a structural break (BOS or
    CHoCH), range location, and MACD are all available, and:

    - bias is BULLISH, the H1 snapshot shows a BOS or CHoCH, price sits in
      the PREMIUM zone, and MACD is still positive (momentum has not turned
      yet) -> `WATCH_SELL`; or
    - bias is BEARISH, the H1 snapshot shows a BOS or CHoCH, price sits in
      the DISCOUNT zone, and MACD is still negative -> `WATCH_BUY`.

    Any missing input is `UNAVAILABLE`; a fully available snapshot that does
    not meet the pattern is `NONE`.
    """
    available = (
        structure_bias in ("BULLISH", "BEARISH")
        and break_of_structure is not None
        and change_of_character is not None
        and range_location is not None
        and macd_line is not None
    )

    event = NONE_LABEL
    if break_of_structure:
        event = "BOS"
    if change_of_character:
        event = "CHOCH" if event == NONE_LABEL else "BOS_AND_CHOCH"

    label = UNAVAILABLE
    reason = "Structure bias, a structural break, range location, and MACD must all be available."
    if available:
        assert macd_line is not None
        structural_break = event != NONE_LABEL
        if not structural_break:
            label, reason = NONE_LABEL, "No BOS or CHoCH detected on the current H1 snapshot."
        elif structure_bias == "BULLISH" and range_location == "PREMIUM" and macd_line > 0:
            label = WATCH_SELL
            reason = (
                "Price is rising, H1 printed a BOS or CHoCH inside the premium zone, "
                "and MACD is still positive -- an early bearish reversal watch."
            )
        elif structure_bias == "BEARISH" and range_location == "DISCOUNT" and macd_line < 0:
            label = WATCH_BUY
            reason = (
                "Price is falling, H1 printed a BOS or CHoCH inside the discount zone, "
                "and MACD is still negative -- an early bullish reversal watch."
            )
        else:
            label = NONE_LABEL
            reason = "A structural break was detected but zone or MACD do not align."

    return {
        "label": label,
        "name": "Reversal Signal Start",
        "reason": reason,
        "evidence": [
            asdict(ReversalSignalEvidence("H1_STRUCTURE_BIAS", structure_bias)),
            asdict(ReversalSignalEvidence("H1_STRUCTURAL_EVENT", event)),
            asdict(ReversalSignalEvidence("H1_RANGE_LOCATION", range_location or UNAVAILABLE)),
            asdict(
                ReversalSignalEvidence(
                    "MACD_LINE", f"{macd_line:.4f}" if macd_line is not None else UNAVAILABLE
                )
            ),
        ],
        "method": (
            "Heuristic watch: H1 BOS or CHoCH inside the premium (bullish bias) or "
            "discount (bearish bias) zone while MACD has not yet flipped."
        ),
        "validated": False,
        "validation_note": (
            "Not a tested edge. A closely related rule (H-028) was rejected in this "
            "repository's own five-year holdout backtest -- see method note."
        ),
        "execution_authority": False,
    }
