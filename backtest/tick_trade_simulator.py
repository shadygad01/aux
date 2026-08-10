"""Tick-ordered execution simulator with realistic bid/ask fills."""

from __future__ import annotations

from bisect import bisect_left
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import timedelta

from .mtf_models import (
    Direction,
    ExitMode,
    Tick,
    TickTrade,
    TradeIntent,
    TradeOutcome,
)


@dataclass(frozen=True, slots=True)
class ExecutionAssumptions:
    entry_delay: timedelta = timedelta(0)
    commission_per_side_points: float = 0.0
    slippage_per_side_points: float = 0.0
    max_holding: timedelta = timedelta(days=5)
    max_tick_gap: timedelta = timedelta(minutes=15)
    max_trades_per_day: int = 3

    def __post_init__(self) -> None:
        if self.entry_delay < timedelta(0):
            raise ValueError("entry_delay must be non-negative")
        if self.commission_per_side_points < 0 or self.slippage_per_side_points < 0:
            raise ValueError("execution costs must be non-negative")
        if self.max_holding <= timedelta(0) or self.max_tick_gap <= timedelta(0):
            raise ValueError("holding and gap limits must be positive")
        if self.max_trades_per_day <= 0:
            raise ValueError("max_trades_per_day must be positive")


def _entry_price(tick: Tick, direction: Direction, slippage: float) -> float:
    return tick.ask + slippage if direction is Direction.BUY else tick.bid - slippage


def _executable_price(tick: Tick, direction: Direction) -> float:
    return tick.bid if direction is Direction.BUY else tick.ask


def _r_multiple(entry: float, exit_price: float, risk: float, direction: Direction) -> float:
    return (
        (exit_price - entry) / risk
        if direction is Direction.BUY
        else (entry - exit_price) / risk
    )


def simulate_intent(
    intent: TradeIntent,
    ticks: Sequence[Tick],
    assumptions: ExecutionAssumptions,
) -> TickTrade | None:
    if not ticks:
        return None
    timestamps = [tick.timestamp for tick in ticks]
    entry_index = bisect_left(timestamps, intent.signal_time + assumptions.entry_delay)
    if entry_index >= len(ticks):
        return None
    entry_tick = ticks[entry_index]
    entry = _entry_price(entry_tick, intent.direction, assumptions.slippage_per_side_points)
    risk = intent.stop_distance
    stop = entry - risk if intent.direction is Direction.BUY else entry + risk
    fixed_target = (
        entry + intent.exit_plan.target_r * risk
        if intent.direction is Direction.BUY
        else entry - intent.exit_plan.target_r * risk
    )
    partial_target = (
        entry + intent.exit_plan.partial_r * risk
        if intent.direction is Direction.BUY
        else entry - intent.exit_plan.partial_r * risk
    )
    previous = entry_tick.timestamp
    best_price = entry
    partial_taken = False
    gross_r = 0.0
    exit_tick = entry_tick
    outcome = TradeOutcome.DATA_END

    for tick in ticks[entry_index:]:
        if tick.timestamp - entry_tick.timestamp > assumptions.max_holding:
            exit_tick = tick
            break
        if tick.timestamp - previous > assumptions.max_tick_gap:
            exit_tick = ticks[max(entry_index, bisect_left(timestamps, tick.timestamp) - 1)]
            break
        previous = tick.timestamp
        executable = _executable_price(tick, intent.direction)
        stop_hit = executable <= stop if intent.direction is Direction.BUY else executable >= stop
        if stop_hit:
            runner_r = _r_multiple(entry, stop, risk, intent.direction)
            gross_r += (
                (1 - intent.exit_plan.partial_fraction) * runner_r
                if partial_taken
                else runner_r
            )
            exit_tick = tick
            outcome = TradeOutcome.TRAIL if partial_taken else TradeOutcome.STOP
            break
        if intent.exit_plan.mode is ExitMode.FIXED_R:
            target_hit = (
                executable >= fixed_target
                if intent.direction is Direction.BUY
                else executable <= fixed_target
            )
            if target_hit:
                gross_r = intent.exit_plan.target_r
                exit_tick = tick
                outcome = TradeOutcome.TARGET
                break
            continue
        if not partial_taken:
            hit_partial = (
                executable >= partial_target
                if intent.direction is Direction.BUY
                else executable <= partial_target
            )
            if hit_partial:
                partial_taken = True
                gross_r = intent.exit_plan.partial_fraction * intent.exit_plan.partial_r
                stop = entry
                best_price = executable
            continue
        if intent.direction is Direction.BUY:
            best_price = max(best_price, executable)
            stop = max(stop, best_price - intent.exit_plan.trail_atr * intent.atr)
        else:
            best_price = min(best_price, executable)
            stop = min(stop, best_price + intent.exit_plan.trail_atr * intent.atr)

    exit_before_cost = _executable_price(exit_tick, intent.direction)
    exit_price = (
        exit_before_cost - assumptions.slippage_per_side_points
        if intent.direction is Direction.BUY
        else exit_before_cost + assumptions.slippage_per_side_points
    )
    if outcome is TradeOutcome.DATA_END:
        open_fraction = 1 - intent.exit_plan.partial_fraction if partial_taken else 1.0
        gross_r += open_fraction * _r_multiple(entry, exit_before_cost, risk, intent.direction)
    commission_r = 2 * assumptions.commission_per_side_points / risk
    slippage_r = 2 * assumptions.slippage_per_side_points / risk
    return TickTrade(
        pattern_id=intent.pattern_id,
        direction=intent.direction,
        signal_time=intent.signal_time,
        entry_time=entry_tick.timestamp,
        exit_time=exit_tick.timestamp,
        entry_price=entry,
        exit_price=exit_price,
        initial_stop=entry - risk if intent.direction is Direction.BUY else entry + risk,
        outcome=outcome,
        gross_r=gross_r,
        commission_r=commission_r,
        slippage_r=slippage_r,
        net_r=gross_r - commission_r - slippage_r,
        partial_taken=partial_taken,
    )


def simulate_portfolio(
    intents: Sequence[TradeIntent],
    ticks: Sequence[Tick],
    assumptions: ExecutionAssumptions,
) -> list[TickTrade]:
    results: list[TickTrade] = []
    busy_until = None
    daily_counts: dict[object, int] = {}
    for intent in sorted(intents, key=lambda item: (item.signal_time, item.pattern_id)):
        if busy_until is not None and intent.signal_time < busy_until:
            continue
        day = intent.signal_time.date()
        if daily_counts.get(day, 0) >= assumptions.max_trades_per_day:
            continue
        trade = simulate_intent(intent, ticks, assumptions)
        if trade is None:
            continue
        results.append(trade)
        daily_counts[day] = daily_counts.get(day, 0) + 1
        busy_until = trade.exit_time
    return results
