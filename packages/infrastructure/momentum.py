"""Standard MACD (12/26/9 EMA) momentum indicator computed from real closes.

Nothing in this codebase computed MACD before this — market_story.py used to
claim "MACD histogram expansion confirms upward momentum alignment" as a
fixed narrative string regardless of any actual data. MACD itself is a
well-defined, standard indicator; this computes it for real instead.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

DEFAULT_FAST_PERIOD = 12
DEFAULT_SLOW_PERIOD = 26
DEFAULT_SIGNAL_PERIOD = 9


@dataclass(frozen=True, slots=True)
class MacdResult:
    macd_line: float
    signal_line: float
    histogram: float

    @property
    def bullish(self) -> bool:
        return self.histogram > 0


def compute_ema(values: Sequence[float], period: int) -> list[float]:
    if not values:
        return []
    k = 2.0 / (period + 1)
    ema = [values[0]]
    for value in values[1:]:
        ema.append(value * k + ema[-1] * (1 - k))
    return ema


def compute_macd(
    closes: Sequence[float],
    fast_period: int = DEFAULT_FAST_PERIOD,
    slow_period: int = DEFAULT_SLOW_PERIOD,
    signal_period: int = DEFAULT_SIGNAL_PERIOD,
) -> MacdResult | None:
    """Standard MACD: EMA(fast) - EMA(slow), with an EMA(signal) of that line.

    Returns None when there aren't enough closes for a meaningful signal —
    an honest gap, not a fabricated momentum reading.
    """
    if len(closes) < slow_period + signal_period:
        return None

    fast_ema = compute_ema(closes, fast_period)
    slow_ema = compute_ema(closes, slow_period)
    macd_line = [f - s for f, s in zip(fast_ema, slow_ema, strict=True)]
    signal_line = compute_ema(macd_line, signal_period)

    return MacdResult(
        macd_line=round(macd_line[-1], 4),
        signal_line=round(signal_line[-1], 4),
        histogram=round(macd_line[-1] - signal_line[-1], 4),
    )
