"""Simulates each SignalEvent forward against subsequent real candles to
classify a real outcome.

Risk levels reuse packages.application.multi_timeframe_engine's real,
unmodified risk-guidance derivation (_compute_risk_guidance /
_select_invalidation / _select_target) rather than inventing new logic --
see the module docstring below for the one deliberate, documented
deviation (H1 ATR instead of execution-timeframe ATR, since this backtest
is H1-only).
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from enum import StrEnum

from packages.application.multi_timeframe_engine import _compute_risk_guidance
from packages.domain import DecisionVerdict, RiskGuidance
from packages.infrastructure.momentum import compute_atr
from packages.infrastructure.smc_detector import Candle

from .walk_forward import SignalEvent

# _compute_risk_guidance's `atr` argument is fetched from the execution
# timeframe (M5/M15) in production -- see
# publish/generators/multi_timeframe.py::_fetch_execution_atr. This
# backtest is explicitly H1-only (no M5/M15 replay), so atr here comes
# from the same H1 window already in hand. This is a parameter
# substitution into an unmodified formula, not new risk logic -- but H1
# ATR is systematically larger than M5/M15 ATR, so stop/target/R:R numbers
# here are NOT numerically identical to what live execution would use.
# The BUY/SELL/WAIT verdict itself carries none of this deviation:
# DecisionEngine never touches ATR.
METHODOLOGY_NOTE_ATR_TIMEFRAME = (
    "Risk guidance uses H1 ATR (this backtest replays H1 only), not the "
    "execution-timeframe (M5/M15) ATR production risk guidance actually "
    "uses -- stop/target/R:R figures are a documented approximation. The "
    "BUY/SELL/WAIT verdict itself is unaffected: DecisionEngine never uses ATR."
)

# OHLC data has no intrabar ordering: when a single candle's range touches
# both the stop and the target, which happened first is genuinely unknown.
# Conservative choice, stated explicitly rather than buried: treat it as
# the stop.
AMBIGUOUS_CANDLE_RULE = "CONSERVATIVE_STOP_FIRST"


class Outcome(StrEnum):
    TARGET_HIT = "TARGET_HIT"
    STOP_HIT = "STOP_HIT"
    OPEN_AT_END_OF_DATA = "OPEN_AT_END_OF_DATA"
    NO_RISK_GUIDANCE = "NO_RISK_GUIDANCE"


@dataclass(frozen=True, slots=True)
class SimulatedTrade:
    signal: SignalEvent
    risk_guidance: RiskGuidance
    outcome: Outcome
    exit_index: int | None
    achieved_rr: float | None  # signed multiple of the planned risk, at exit


def simulate_trade(signal: SignalEvent, all_candles: Sequence[Candle]) -> SimulatedTrade:
    """Derives risk guidance from the signal's own window, then walks
    candles strictly AFTER the signal candle to classify the outcome --
    never the signal candle's own high/low, which would be self-referential
    lookahead rather than a real trade."""
    atr = compute_atr(signal.window_candles)
    risk_guidance = _compute_risk_guidance(signal.observation, signal.decision.verdict, atr)

    if risk_guidance.risk_status != "OK":
        return SimulatedTrade(
            signal=signal,
            risk_guidance=risk_guidance,
            outcome=Outcome.NO_RISK_GUIDANCE,
            exit_index=None,
            achieved_rr=None,
        )

    is_buy = signal.decision.verdict is DecisionVerdict.BUY
    stop = risk_guidance.stop_loss_price
    target = risk_guidance.target_price
    assert stop is not None and target is not None  # guaranteed by risk_status == "OK"

    for j in range(signal.index + 1, len(all_candles)):
        candle = all_candles[j]
        hit_stop = candle.low <= stop if is_buy else candle.high >= stop
        hit_target = candle.high >= target if is_buy else candle.low <= target

        if hit_stop and hit_target:
            return SimulatedTrade(
                signal=signal,
                risk_guidance=risk_guidance,
                outcome=Outcome.STOP_HIT,
                exit_index=j,
                achieved_rr=-1.0,
            )
        if hit_stop:
            return SimulatedTrade(
                signal=signal,
                risk_guidance=risk_guidance,
                outcome=Outcome.STOP_HIT,
                exit_index=j,
                achieved_rr=-1.0,
            )
        if hit_target:
            return SimulatedTrade(
                signal=signal,
                risk_guidance=risk_guidance,
                outcome=Outcome.TARGET_HIT,
                exit_index=j,
                achieved_rr=risk_guidance.risk_reward,
            )

    return SimulatedTrade(
        signal=signal,
        risk_guidance=risk_guidance,
        outcome=Outcome.OPEN_AT_END_OF_DATA,
        exit_index=None,
        achieved_rr=None,
    )
