"""Aggregates SimulatedTrade results into real win-rate/R:R statistics.

Win rate and average R:R are computed only over trades with a decided
outcome (TARGET_HIT or STOP_HIT); OPEN_AT_END_OF_DATA and NO_RISK_GUIDANCE
correctly stay out of that denominator instead of being silently counted
as either a win or a loss.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from packages.domain import DecisionPolicy, DecisionVerdict
from packages.infrastructure.smc_detector import Candle

from .trade_simulator import Outcome, SimulatedTrade, simulate_trade
from .walk_forward import walk_forward

_DECIDED_OUTCOMES = (Outcome.TARGET_HIT, Outcome.STOP_HIT)


@dataclass(frozen=True, slots=True)
class BacktestSummary:
    total_signals: int
    total_buy: int
    total_sell: int
    win_rate_overall: float | None
    win_rate_buy: float | None
    win_rate_sell: float | None
    average_rr_overall: float | None
    average_rr_buy: float | None
    average_rr_sell: float | None
    target_hit_count: int
    stop_hit_count: int
    open_at_end_count: int
    no_risk_guidance_count: int


def _win_rate(trades: Sequence[SimulatedTrade]) -> float | None:
    decided = [t for t in trades if t.outcome in _DECIDED_OUTCOMES]
    if not decided:
        return None
    wins = sum(1 for t in decided if t.outcome is Outcome.TARGET_HIT)
    return round(wins / len(decided), 4)


def _average_rr(trades: Sequence[SimulatedTrade]) -> float | None:
    decided_rrs = [
        t.achieved_rr
        for t in trades
        if t.outcome in _DECIDED_OUTCOMES and t.achieved_rr is not None
    ]
    if not decided_rrs:
        return None
    return round(sum(decided_rrs) / len(decided_rrs), 4)


def summarize(trades: Sequence[SimulatedTrade]) -> BacktestSummary:
    buy_trades = [t for t in trades if t.signal.decision.verdict is DecisionVerdict.BUY]
    sell_trades = [t for t in trades if t.signal.decision.verdict is DecisionVerdict.SELL]

    return BacktestSummary(
        total_signals=len(trades),
        total_buy=len(buy_trades),
        total_sell=len(sell_trades),
        win_rate_overall=_win_rate(trades),
        win_rate_buy=_win_rate(buy_trades),
        win_rate_sell=_win_rate(sell_trades),
        average_rr_overall=_average_rr(trades),
        average_rr_buy=_average_rr(buy_trades),
        average_rr_sell=_average_rr(sell_trades),
        target_hit_count=sum(1 for t in trades if t.outcome is Outcome.TARGET_HIT),
        stop_hit_count=sum(1 for t in trades if t.outcome is Outcome.STOP_HIT),
        open_at_end_count=sum(1 for t in trades if t.outcome is Outcome.OPEN_AT_END_OF_DATA),
        no_risk_guidance_count=sum(1 for t in trades if t.outcome is Outcome.NO_RISK_GUIDANCE),
    )


def run_and_summarize(
    candles: Sequence[Candle], policy: DecisionPolicy | None = None
) -> tuple[BacktestSummary, list[SimulatedTrade]]:
    """Convenience: full pipeline (walk-forward -> simulate -> summarize)
    for one DecisionPolicy -- the unit sensitivity_sweep repeats per
    candidate threshold."""
    signals = walk_forward(candles, policy)
    trades = [simulate_trade(signal, candles) for signal in signals]
    return summarize(trades), trades


def sensitivity_sweep(
    candles: Sequence[Candle],
    base_policy: DecisionPolicy,
    attention_thresholds: Sequence[float] = (0.65, 0.70, 0.75, 0.80, 0.85),
) -> dict[float, BacktestSummary]:
    """Re-runs the full pipeline once per candidate attention_threshold,
    holding structure/location/liquidity weights fixed at base_policy's
    values (DecisionPolicy already validates they sum to 1.0, so only
    attention_threshold is swept here -- jointly sweeping the three
    weights needs a constrained search and is out of scope for this
    deliverable). Secondary/optional: answers whether 0.75 (H-007) is
    materially different from nearby values, without inventing a
    weight-search framework.

    Known limitation, discovered while testing this function rather than
    assumed: DecisionEngine only reaches `verdict = candidate` when
    `not conflicts` -- and structure/location/liquidity each either fully
    contribute their weight or add a conflict, so `not conflicts` implies
    score == 1.0 exactly (0.40+0.30+0.30) whenever a candidate direction
    exists. Since DecisionPolicy requires attention_threshold <= 1.0, that
    score trivially clears every valid threshold. In the current engine,
    attention_threshold cannot reject a conflict-free candidate -- this
    sweep will show identical results across thresholds until/unless
    DecisionEngine's score-vs-conflicts relationship changes. Report this
    as evidence for H-007, not a bug in the sweep itself."""
    results: dict[float, BacktestSummary] = {}
    for threshold in attention_thresholds:
        policy = DecisionPolicy(
            version=base_policy.version,
            output_contract_version=base_policy.output_contract_version,
            supported_symbol=base_policy.supported_symbol,
            maximum_age=base_policy.maximum_age,
            equilibrium_band=base_policy.equilibrium_band,
            attention_threshold=threshold,
            structure_weight=base_policy.structure_weight,
            location_weight=base_policy.location_weight,
            liquidity_weight=base_policy.liquidity_weight,
            disclaimer=base_policy.disclaimer,
        )
        summary, _ = run_and_summarize(candles, policy)
        results[threshold] = summary
    return results
