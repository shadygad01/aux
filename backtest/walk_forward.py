"""Walk-forward replay of real candles through the unmodified production
DecisionEngine.

Uses a sliding window (not an ever-growing one) matching
LiveMarketCollector's default chart_range="1mo" for H1: at each step the
detector sees only the same amount of history it would see live, not the
entire multi-month dataset. Running SMC detection over the full history at
every step would hand it structural context the live system never has --
not literal future leakage, but a fidelity mismatch that would make
results unrepresentative of what the live system actually decides.

Signal emission is edge-triggered: a SignalEvent is recorded only when the
verdict transitions into BUY or SELL, not on every candle a persistent
setup remains valid. Otherwise one real setup that stays above the
attention threshold for many consecutive candles would be counted as
dozens of duplicate "signals."
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from packages.application.decision_engine import DecisionEngine
from packages.domain import Decision, DecisionPolicy, DecisionVerdict, MarketObservation
from packages.infrastructure.momentum import compute_macd
from packages.infrastructure.smc_detector import (
    DEFAULT_SWING_WINDOW,
    MIN_CANDLES_FOR_STRUCTURE,
    Candle,
    build_observation_from_candles,
)

WINDOW_CANDLES = 720  # ~1 month of H1 gold-futures candles (24/5 trading)


class _NullDecisionLogger:
    def record(self, observation: MarketObservation, decision: Decision) -> None:
        pass


@dataclass(frozen=True, slots=True)
class SignalEvent:
    """A BUY/SELL verdict transition -- backtest-only bookkeeping, not a
    competing representation of Decision."""

    index: int
    observation: MarketObservation
    decision: Decision
    window_candles: tuple[Candle, ...]


def walk_forward(
    candles: Sequence[Candle],
    policy: DecisionPolicy | None = None,
    *,
    window: int = WINDOW_CANDLES,
    swing_window: int = DEFAULT_SWING_WINDOW,
) -> list[SignalEvent]:
    """Evaluate the real DecisionEngine at every candle index (once enough
    history exists), emitting a SignalEvent only on each BUY/SELL
    transition."""
    engine = DecisionEngine(policy or DecisionPolicy(), _NullDecisionLogger())
    signals: list[SignalEvent] = []
    previous_verdict: DecisionVerdict | None = None

    for i in range(MIN_CANDLES_FOR_STRUCTURE - 1, len(candles)):
        window_candles = tuple(candles[max(0, i - window + 1) : i + 1])
        if len(window_candles) < MIN_CANDLES_FOR_STRUCTURE:
            continue

        macd_result = compute_macd([c.close for c in window_candles])
        observation = build_observation_from_candles(
            window_candles,
            symbol="XAUUSD",
            timeframe="H1",
            source="backtest:yahoo-finance-gold-futures-1h",
            swing_window=swing_window,
            macd_value=macd_result.macd_line if macd_result is not None else None,
        )
        decision = engine.evaluate(observation, evaluated_at=window_candles[-1].timestamp)

        if decision.verdict in (DecisionVerdict.BUY, DecisionVerdict.SELL):
            if decision.verdict != previous_verdict:
                signals.append(
                    SignalEvent(
                        index=i,
                        observation=observation,
                        decision=decision,
                        window_candles=window_candles,
                    )
                )
            previous_verdict = decision.verdict
        else:
            previous_verdict = decision.verdict

    return signals
