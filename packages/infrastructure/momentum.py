"""Standard MACD (12/26/9 EMA) momentum indicator, plus Average True Range,
computed from real OHLC candles.

Nothing in this codebase computed MACD before this — market_story.py used to
claim "MACD histogram expansion confirms upward momentum alignment" as a
fixed narrative string regardless of any actual data. MACD itself is a
well-defined, standard indicator; this computes it for real instead.

ATR is co-located here (rather than a new module) for the same reason: it is
one more small, deterministic, real-candle-derived indicator following the
identical pattern, not a momentum indicator itself -- it exists to size the
Multi-Timeframe risk model's volatility buffer (see
packages/application/multi_timeframe_engine.py).
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from packages.domain import MomentumAssessment

from .smc_detector import Candle

DEFAULT_FAST_PERIOD = 12
DEFAULT_SLOW_PERIOD = 26
DEFAULT_SIGNAL_PERIOD = 9
DEFAULT_ATR_PERIOD = 14  # implementation convention, not a validated trading parameter


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


def build_momentum_assessment(
    closes: Sequence[float],
    fast_period: int = DEFAULT_FAST_PERIOD,
    slow_period: int = DEFAULT_SLOW_PERIOD,
    signal_period: int = DEFAULT_SIGNAL_PERIOD,
) -> MomentumAssessment | None:
    """MomentumAssessment for the trading-opportunity engine, from real closes.

    `crossover_confirmed` is a genuine event check, not a snapshot of the
    current line order: it compares this bar's MACD-vs-signal relationship
    against the prior bar's (recomputed independently on the series without
    the last close), so it is True only on the bar where the lines actually
    cross. Without enough history for a prior bar it stays False — an honest
    gap, not a fabricated crossover.
    """
    current = compute_macd(closes, fast_period, slow_period, signal_period)
    if current is None:
        return None

    previous = compute_macd(closes[:-1], fast_period, slow_period, signal_period)
    crossover_confirmed = False
    if previous is not None:
        previous_diff = previous.macd_line - previous.signal_line
        current_diff = current.macd_line - current.signal_line
        crossover_confirmed = current_diff != 0 and previous_diff * current_diff <= 0

    return MomentumAssessment(
        macd_value=current.macd_line,
        histogram=current.histogram,
        slope=None,
        crossover_confirmed=crossover_confirmed,
    )


def compute_atr(candles: Sequence[Candle], period: int = DEFAULT_ATR_PERIOD) -> float | None:
    """Average True Range over the most recent `period` bars, from real OHLC
    candles: a simple (non-Wilder-smoothed) average of the True Range series.
    This is the simplest defensible implementation, not claimed to be
    superior to Wilder smoothing or any other variant -- see the Multi-
    Timeframe risk model design report for why the period (14) and this
    averaging choice are implementation conventions, not validated
    parameters.

    Returns None when there aren't enough candles for a meaningful reading,
    mirroring compute_macd's honest-gap convention -- never a fabricated
    volatility reading.
    """
    if len(candles) < period + 1:
        return None

    true_ranges = [
        max(
            candles[i].high - candles[i].low,
            abs(candles[i].high - candles[i - 1].close),
            abs(candles[i].low - candles[i - 1].close),
        )
        for i in range(1, len(candles))
    ]
    recent = true_ranges[-period:]
    return round(sum(recent) / len(recent), 4)
