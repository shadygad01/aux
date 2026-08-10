"""Conservative bar-level H-028 evaluation for midpoint-only supplied data."""

from __future__ import annotations

import json
from bisect import bisect_left
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path

from .bottom_up_reversal import HYPOTHESIS_ID, build_bottom_up_snapshots
from .mtf_feature_engine import FeatureSnapshot
from .mtf_models import BidAskBar, Direction, ExitMode, ExitPlan
from .mtf_storage import read_bars
from .research_governance import calculate_metrics, evaluate_acceptance


@dataclass(frozen=True, slots=True)
class BarTrade:
    signal_time: datetime
    entry_time: datetime
    exit_time: datetime
    direction: Direction
    net_r: float
    outcome: str


def _executable(value: float, direction: Direction, per_side_cost: float) -> float:
    return value + per_side_cost if direction is Direction.BUY else value - per_side_cost


def _exit_value(value: float, direction: Direction, per_side_cost: float) -> float:
    return value - per_side_cost if direction is Direction.BUY else value + per_side_cost


def simulate(
    snapshot: FeatureSnapshot,
    bars: Sequence[BidAskBar],
    timestamps: Sequence[datetime],
    plan: ExitPlan,
    *,
    per_side_cost: float,
    delay_bars: int,
    max_holding: timedelta = timedelta(days=5),
) -> BarTrade | None:
    entry_index = bisect_left(timestamps, snapshot.timestamp) + delay_bars
    if entry_index >= len(bars):
        return None
    entry_bar = bars[entry_index]
    entry = _executable(entry_bar.midpoint_open, snapshot.direction, per_side_cost)
    risk = snapshot.stop_distance
    stop = entry - risk if snapshot.direction is Direction.BUY else entry + risk
    target = (
        entry + plan.target_r * risk
        if snapshot.direction is Direction.BUY
        else entry - plan.target_r * risk
    )
    partial = (
        entry + plan.partial_r * risk
        if snapshot.direction is Direction.BUY
        else entry - plan.partial_r * risk
    )
    partial_taken = False
    best = entry
    deadline = snapshot.timestamp + max_holding
    last_bar: BidAskBar | None = None

    for bar in bars[entry_index:]:
        if bar.timestamp > deadline:
            break
        last_bar = bar
        favorable = (
            _exit_value(bar.midpoint_high, snapshot.direction, per_side_cost)
            if snapshot.direction is Direction.BUY
            else _exit_value(bar.midpoint_low, snapshot.direction, per_side_cost)
        )
        adverse = (
            _exit_value(bar.midpoint_low, snapshot.direction, per_side_cost)
            if snapshot.direction is Direction.BUY
            else _exit_value(bar.midpoint_high, snapshot.direction, per_side_cost)
        )
        stop_hit = adverse <= stop if snapshot.direction is Direction.BUY else adverse >= stop
        if stop_hit:
            remainder_r = (
                (stop - entry) / risk
                if snapshot.direction is Direction.BUY
                else (entry - stop) / risk
            )
            net_r = (
                plan.partial_fraction * plan.partial_r + (1 - plan.partial_fraction) * remainder_r
                if partial_taken
                else -1.0
            )
            return BarTrade(
                snapshot.timestamp,
                entry_bar.timestamp,
                bar.timestamp,
                snapshot.direction,
                net_r,
                "TRAIL_OR_STOP" if partial_taken else "STOP",
            )

        if plan.mode is ExitMode.FIXED_R:
            target_hit = (
                favorable >= target if snapshot.direction is Direction.BUY else favorable <= target
            )
            if target_hit:
                return BarTrade(
                    snapshot.timestamp,
                    entry_bar.timestamp,
                    bar.timestamp,
                    snapshot.direction,
                    plan.target_r,
                    "TARGET",
                )
            continue

        partial_hit = (
            favorable >= partial if snapshot.direction is Direction.BUY else favorable <= partial
        )
        if partial_hit and not partial_taken:
            partial_taken = True
            stop = entry
        if partial_taken:
            best = (
                max(best, favorable)
                if snapshot.direction is Direction.BUY
                else min(best, favorable)
            )
            trailing = (
                best - plan.trail_atr * snapshot.atr
                if snapshot.direction is Direction.BUY
                else best + plan.trail_atr * snapshot.atr
            )
            stop = (
                max(stop, trailing) if snapshot.direction is Direction.BUY else min(stop, trailing)
            )

    if last_bar is None:
        return None
    exit_price = _exit_value(last_bar.midpoint_close, snapshot.direction, per_side_cost)
    remainder_r = (
        (exit_price - entry) / risk
        if snapshot.direction is Direction.BUY
        else (entry - exit_price) / risk
    )
    net_r = (
        plan.partial_fraction * plan.partial_r + (1 - plan.partial_fraction) * remainder_r
        if partial_taken
        else remainder_r
    )
    return BarTrade(
        snapshot.timestamp,
        entry_bar.timestamp,
        last_bar.timestamp,
        snapshot.direction,
        net_r,
        "MAX_HOLD",
    )


def simulate_portfolio(
    snapshots: Sequence[FeatureSnapshot],
    bars: Sequence[BidAskBar],
    plan: ExitPlan,
    *,
    per_side_cost: float,
    delay_bars: int,
) -> list[BarTrade]:
    timestamps = [bar.timestamp for bar in bars]
    trades: list[BarTrade] = []
    busy_until: datetime | None = None
    daily: dict[object, int] = {}
    for snapshot in snapshots:
        if busy_until is not None and snapshot.timestamp < busy_until:
            continue
        day = snapshot.timestamp.date()
        if daily.get(day, 0) >= 3:
            continue
        trade = simulate(
            snapshot,
            bars,
            timestamps,
            plan,
            per_side_cost=per_side_cost,
            delay_bars=delay_bars,
        )
        if trade is None:
            continue
        trades.append(trade)
        daily[day] = daily.get(day, 0) + 1
        busy_until = trade.exit_time
    return trades


def plans() -> Mapping[str, ExitPlan]:
    return {
        "fixed_2R": ExitPlan(ExitMode.FIXED_R, target_r=2),
        "fixed_3R": ExitPlan(ExitMode.FIXED_R, target_r=3),
        "fixed_4R": ExitPlan(ExitMode.FIXED_R, target_r=4),
        "partial_50@2R_trail_0.5ATR": ExitPlan(
            ExitMode.PARTIAL_TRAIL,
            partial_r=2,
            partial_fraction=0.5,
            trail_atr=0.5,
        ),
    }


def _metrics(trades: Sequence[BarTrade]) -> dict[str, object]:
    return asdict(calculate_metrics([(trade.entry_time, trade.net_r) for trade in trades]))


def run(derived_root: Path, report_path: Path) -> dict[str, object]:
    m5 = read_bars(derived_root / "XAUUSD_M5.jsonl")
    m15 = read_bars(derived_root / "XAUUSD_M15.jsonl")
    h1 = read_bars(derived_root / "XAUUSD_H1.jsonl")
    snapshots = build_bottom_up_snapshots(h1, m15, m5)
    discovery_end = datetime(2024, 8, 3, tzinfo=UTC)
    holdout_start = datetime(2024, 8, 8, tzinfo=UTC)
    holdout_end = datetime(2026, 8, 8, tzinfo=UTC)
    discovery = [snapshot for snapshot in snapshots if snapshot.timestamp < discovery_end]
    holdout = [
        snapshot for snapshot in snapshots if holdout_start <= snapshot.timestamp < holdout_end
    ]
    base_cost = 0.15
    plan_results: dict[str, dict[str, object]] = {}
    scored: list[tuple[float, str]] = []
    fallback_scores: dict[str, float] = {}
    for name, plan in plans().items():
        trades = simulate_portfolio(discovery, m5, plan, per_side_cost=base_cost, delay_bars=0)
        metric_object = calculate_metrics([(trade.entry_time, trade.net_r) for trade in trades])
        plan_results[name] = {"metrics": asdict(metric_object)}
        fallback_scores[name] = metric_object.net_r
        eligible = bool(metric_object.yearly_net_r) and all(
            value > 0 for value in metric_object.yearly_net_r.values()
        )
        if eligible and metric_object.expectancy is not None and metric_object.expectancy > 0:
            scored.append((metric_object.net_r, name))
    selected_name = (
        max(scored)[1] if scored else max(fallback_scores, key=lambda name: fallback_scores[name])
    )
    selected = plans()[selected_name]
    trades = simulate_portfolio(holdout, m5, selected, per_side_cost=base_cost, delay_bars=0)
    stressed = simulate_portfolio(
        holdout, m5, selected, per_side_cost=base_cost * 1.5, delay_bars=1
    )
    metrics_object = calculate_metrics([(trade.entry_time, trade.net_r) for trade in trades])
    midpoint = holdout_start + (holdout_end - holdout_start) / 2
    halves = (
        sum(trade.net_r for trade in trades if trade.entry_time < midpoint),
        sum(trade.net_r for trade in trades if trade.entry_time >= midpoint),
    )
    neighboring = [
        sum(
            trade.net_r
            for trade in simulate_portfolio(
                holdout, m5, plan, per_side_cost=base_cost, delay_bars=0
            )
        )
        for name, plan in plans().items()
        if name != selected_name
    ]
    acceptance = evaluate_acceptance(
        metrics_object,
        stressed_net_r=sum(trade.net_r for trade in stressed),
        neighboring_parameter_net_r=neighboring,
        holdout_period_net_r=halves,
    )
    by_direction = {
        direction.value: _metrics([trade for trade in trades if trade.direction is direction])
        for direction in Direction
    }
    direction_acceptance: dict[str, object] = {}
    for direction in Direction:
        direction_trades = [trade for trade in trades if trade.direction is direction]
        direction_stressed = [trade for trade in stressed if trade.direction is direction]
        direction_metrics = calculate_metrics(
            [(trade.entry_time, trade.net_r) for trade in direction_trades]
        )
        direction_neighbors = [
            sum(
                trade.net_r
                for trade in simulate_portfolio(
                    holdout, m5, plan, per_side_cost=base_cost, delay_bars=0
                )
                if trade.direction is direction
            )
            for name, plan in plans().items()
            if name != selected_name
        ]
        direction_acceptance[direction.value] = asdict(
            evaluate_acceptance(
                direction_metrics,
                stressed_net_r=sum(trade.net_r for trade in direction_stressed),
                neighboring_parameter_net_r=direction_neighbors,
                holdout_period_net_r=(
                    sum(trade.net_r for trade in direction_trades if trade.entry_time < midpoint),
                    sum(trade.net_r for trade in direction_trades if trade.entry_time >= midpoint),
                ),
            )
        )

    discovery_atr = sorted(snapshot.atr for snapshot in discovery)
    low_cut = discovery_atr[len(discovery_atr) // 3]
    high_cut = discovery_atr[(2 * len(discovery_atr)) // 3]
    atr_by_signal = {snapshot.timestamp: snapshot.atr for snapshot in holdout}
    regime_trades: dict[str, list[BarTrade]] = {"LOW": [], "MID": [], "HIGH": []}
    for trade in trades:
        atr = atr_by_signal[trade.signal_time]
        regime = "LOW" if atr <= low_cut else "HIGH" if atr >= high_cut else "MID"
        regime_trades[regime].append(trade)
    regimes = {name: _metrics(items) for name, items in regime_trades.items()}
    cost_sensitivity = {
        f"{cost:.2f}_points_per_side": _metrics(
            simulate_portfolio(holdout, m5, selected, per_side_cost=cost, delay_bars=0)
        )
        for cost in (0.05, 0.15, 0.30, 0.60)
    }
    result: dict[str, object] = {
        "schema_version": "1.0.0",
        "hypothesis_id": HYPOTHESIS_ID,
        "generated_at": datetime.now(UTC).isoformat(),
        "data_quality": "MIDPOINT_ONLY; costs modeled; not tick executable",
        "split": {
            "discovery_end_with_embargo": discovery_end.isoformat(),
            "holdout_start": holdout_start.isoformat(),
            "holdout_end": holdout_end.isoformat(),
        },
        "signal_counts": {
            "all": len(snapshots),
            "discovery": len(discovery),
            "holdout": len(holdout),
        },
        "discovery": {"plans": plan_results, "selected_plan": selected_name},
        "holdout": {
            "metrics": asdict(metrics_object),
            "by_direction": by_direction,
            "direction_acceptance": direction_acceptance,
            "atr_regime_thresholds": {"low_max": low_cut, "high_min": high_cut},
            "by_atr_regime": regimes,
            "halves_net_r": halves,
            "stress_net_r": sum(trade.net_r for trade in stressed),
            "neighboring_net_r": neighboring,
            "cost_sensitivity": cost_sensitivity,
            "acceptance": asdict(acceptance),
            "trades": [asdict(trade) for trade in trades],
        },
    }
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(result, indent=2, default=str), encoding="utf-8")
    return result


if __name__ == "__main__":
    import sys

    payload = run(Path(sys.argv[1]), Path(sys.argv[2]))
    print(
        json.dumps(
            {"signals": payload["signal_counts"], "holdout": payload["holdout"]}, default=str
        )[:12000]
    )
