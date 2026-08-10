"""End-to-end discovery and locked-holdout evaluation for XAUUSD patterns."""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path

from .mtf_data import H1_SECONDS, M15_SECONDS, aggregate_bars, ticks_to_bars, validate_bar_lineage
from .mtf_feature_engine import FeatureSnapshot, build_feature_snapshots
from .mtf_models import Direction, ExitMode, ExitPlan, TickTrade, TradeOutcome
from .mtf_storage import TickArchive, read_bars, write_bars
from .pattern_discovery_research import (
    Condition,
    DiscoveryResult,
    LabeledOpportunity,
    Operator,
    PatternRule,
    discover_rules,
    generate_rules,
)
from .research_governance import (
    AcceptanceResult,
    ResearchSplit,
    calculate_metrics,
    discovery_rows,
    evaluate_acceptance,
    freeze_configuration,
    holdout_rows,
    verify_frozen_configuration,
)
from .tick_trade_simulator import ExecutionAssumptions, simulate_intent


@dataclass(frozen=True, slots=True)
class ResearchPaths:
    raw_root: Path
    derived_root: Path
    report_root: Path


def default_exit_plans() -> dict[str, ExitPlan]:
    plans = {
        f"fixed_{target:g}R": ExitPlan(ExitMode.FIXED_R, target_r=target)
        for target in (2.0, 3.0, 4.0)
    }
    for partial_r in (1.5, 2.0):
        for fraction in (0.25, 0.5):
            for trail in (0.5, 1.0, 2.0):
                key = f"partial_{fraction:g}@{partial_r:g}R_trail_{trail:g}ATR"
                plans[key] = ExitPlan(
                    ExitMode.PARTIAL_TRAIL,
                    partial_r=partial_r,
                    partial_fraction=fraction,
                    trail_atr=trail,
                )
    return plans


def default_condition_space() -> dict[
    str, Sequence[tuple[Operator, bool | float | int | str]]
]:
    return {
        "h1_bos": ((Operator.EQ, True), (Operator.EQ, False)),
        "h1_choch": ((Operator.EQ, True), (Operator.EQ, False)),
        "h1_sweep": ((Operator.EQ, True), (Operator.EQ, False)),
        "h1_location_aligned": ((Operator.EQ, True), (Operator.EQ, False)),
        "m15_relation": (
            (Operator.EQ, "ALIGNED"),
            (Operator.EQ, "NOT_OPPOSED"),
            (Operator.EQ, "OPPOSED"),
        ),
        "m15_bos": ((Operator.EQ, True), (Operator.EQ, False)),
        "macd_agrees": ((Operator.EQ, True), (Operator.EQ, False)),
        "macd_slope_agrees": ((Operator.EQ, True), (Operator.EQ, False)),
        "breakout_20": ((Operator.EQ, True),),
        "breakdown_20": ((Operator.EQ, True),),
        "session": tuple(
            (Operator.EQ, value) for value in ("ASIAN", "LONDON", "OVERLAP", "NEW_YORK")
        ),
        "h1_bias_age": tuple((Operator.LE, value) for value in (1, 3, 6, 12)),
        "body_ratio": tuple((Operator.GE, value) for value in (0.25, 0.5, 0.75)),
        "range_compression": (
            (Operator.LE, 0.75),
            (Operator.LE, 1.0),
            (Operator.GE, 1.25),
        ),
        "daily_high_distance_atr": tuple((Operator.LE, value) for value in (0.5, 1.0, 2.0)),
        "daily_low_distance_atr": tuple((Operator.LE, value) for value in (0.5, 1.0, 2.0)),
    }


def build_derived_bars(
    archive: TickArchive,
    start: datetime,
    end: datetime,
    derived_root: Path,
) -> tuple[Path, Path, Path]:
    m5 = [
        bar
        for hour, ticks in archive.iter_hours(start, end)
        for bar in ticks_to_bars(ticks, closed_before=hour + timedelta(hours=1))
    ]
    m15 = aggregate_bars(m5, M15_SECONDS)
    h1 = aggregate_bars(m5, H1_SECONDS)
    validate_bar_lineage(m5, m15, h1)
    paths = (
        derived_root / "XAUUSD_M5.jsonl",
        derived_root / "XAUUSD_M15.jsonl",
        derived_root / "XAUUSD_H1.jsonl",
    )
    for path, bars in zip(paths, (m5, m15, h1), strict=True):
        write_bars(path, bars)
    return paths


def _edge_snapshots(snapshots: Sequence[FeatureSnapshot]) -> list[FeatureSnapshot]:
    selected: list[FeatureSnapshot] = []
    previous: tuple[object, ...] | None = None
    for snapshot in snapshots:
        state = (
            snapshot.direction,
            snapshot.features["h1_bos"],
            snapshot.features["h1_sweep"],
            snapshot.features["h1_choch"],
        )
        active = bool(snapshot.features["h1_bos"] or snapshot.features["h1_sweep"])
        if active and state != previous:
            selected.append(snapshot)
        previous = state
    return selected


def _label(
    snapshots: Sequence[FeatureSnapshot],
    archive: TickArchive,
    plans: Mapping[str, ExitPlan],
    assumptions: ExecutionAssumptions,
) -> list[LabeledOpportunity]:
    labeled: list[LabeledOpportunity] = []
    for snapshot in snapshots:
        for plan_id, plan in plans.items():
            intent = snapshot.intent("UNFILTERED", plan)
            ticks = archive.between(
                intent.signal_time,
                intent.signal_time + assumptions.entry_delay + assumptions.max_holding,
            )
            trade = simulate_intent(intent, ticks, assumptions)
            if trade is None or trade.outcome is TradeOutcome.DATA_END:
                continue
            labeled.append(
                LabeledOpportunity(
                    timestamp=trade.entry_time,
                    exit_time=trade.exit_time,
                    direction=snapshot.direction,
                    exit_plan_id=plan_id,
                    features=snapshot.features,
                    net_r=trade.net_r,
                )
            )
    return labeled


def run_discovery(
    paths: ResearchPaths,
    archive: TickArchive,
    split: ResearchSplit,
    assumptions: ExecutionAssumptions,
    *,
    frozen_at: datetime,
) -> list[DiscoveryResult]:
    m15 = read_bars(paths.derived_root / "XAUUSD_M15.jsonl")
    h1 = read_bars(paths.derived_root / "XAUUSD_H1.jsonl")
    snapshots = _edge_snapshots(build_feature_snapshots(h1, m15))
    discovery = discovery_rows(snapshots, split, lambda item: item.timestamp)
    plans = default_exit_plans()
    labeled = _label(discovery, archive, plans, assumptions)
    rules = generate_rules(
        (Direction.BUY, Direction.SELL),
        tuple(plans),
        default_condition_space(),
        maximum_conditions=2,
    )
    first = split.discovery_start
    boundaries = (
        first,
        first.replace(year=first.year + 1),
        first.replace(year=first.year + 2),
        split.holdout_start - split.embargo,
    )
    results = discover_rules(labeled, rules, boundaries)
    selected: list[DiscoveryResult] = []
    for direction in (Direction.BUY, Direction.SELL):
        candidates = [
            result
            for result in results
            if result.accepted_by_fdr and result.rule.direction is direction
        ]
        selected.extend(candidates[:3])
    frozen_path = paths.report_root / "frozen_patterns.json"
    freeze_configuration(
        split,
        [
            {**result.rule.to_dict(), "exit_plan": asdict(plans[result.rule.exit_plan_id])}
            for result in selected
        ],
        frozen_path,
        frozen_at=frozen_at,
    )
    _write_discovery_report(paths.report_root, results, selected)
    return selected


def _rule_from_dict(payload: Mapping[str, object]) -> PatternRule:
    raw_conditions = payload["conditions"]
    if not isinstance(raw_conditions, list):
        raise ValueError("pattern conditions must be a list")
    return PatternRule(
        pattern_id=str(payload["pattern_id"]),
        direction=Direction(str(payload["direction"])),
        exit_plan_id=str(payload["exit_plan_id"]),
        conditions=tuple(
            Condition(str(item["feature"]), Operator(str(item["operator"])), item["value"])
            for item in raw_conditions
            if isinstance(item, dict)
        ),
    )


def _matching_snapshots(
    rule: PatternRule, snapshots: Sequence[FeatureSnapshot]
) -> list[FeatureSnapshot]:
    return [
        snapshot
        for snapshot in snapshots
        if snapshot.direction is rule.direction
        and all(condition.matches(snapshot.features) for condition in rule.conditions)
    ]


def _simulate_rule(
    rule: PatternRule,
    snapshots: Sequence[FeatureSnapshot],
    archive: TickArchive,
    plan: ExitPlan,
    assumptions: ExecutionAssumptions,
) -> list[TickTrade]:
    trades: list[TickTrade] = []
    busy_until: datetime | None = None
    daily: dict[object, int] = {}
    for snapshot in _matching_snapshots(rule, snapshots):
        signal_time = snapshot.timestamp
        if not isinstance(signal_time, datetime):
            continue
        if busy_until is not None and signal_time < busy_until:
            continue
        day = signal_time.date()
        if daily.get(day, 0) >= assumptions.max_trades_per_day:
            continue
        intent = snapshot.intent(rule.pattern_id, plan)
        ticks = archive.between(
            intent.signal_time,
            intent.signal_time + assumptions.entry_delay + assumptions.max_holding,
        )
        trade = simulate_intent(intent, ticks, assumptions)
        if trade is None or trade.outcome is TradeOutcome.DATA_END:
            continue
        trades.append(trade)
        daily[day] = daily.get(day, 0) + 1
        busy_until = trade.exit_time
    return trades


def run_holdout(
    paths: ResearchPaths,
    archive: TickArchive,
    split: ResearchSplit,
    assumptions: ExecutionAssumptions,
) -> dict[str, AcceptanceResult]:
    frozen_path = paths.report_root / "frozen_patterns.json"
    document = verify_frozen_configuration(frozen_path)
    m15 = read_bars(paths.derived_root / "XAUUSD_M15.jsonl")
    h1 = read_bars(paths.derived_root / "XAUUSD_H1.jsonl")
    all_snapshots = _edge_snapshots(build_feature_snapshots(h1, m15))
    snapshots = holdout_rows(
        all_snapshots,
        split,
        lambda item: item.timestamp,
        frozen_configuration=frozen_path,
    )
    plans = default_exit_plans()
    results: dict[str, AcceptanceResult] = {}
    report_patterns: list[dict[str, object]] = []
    selected = document["selected_patterns"]
    if not isinstance(selected, list):
        raise ValueError("frozen selected_patterns must be a list")
    for raw in selected:
        if not isinstance(raw, dict):
            continue
        rule = _rule_from_dict(raw)
        plan = plans[rule.exit_plan_id]
        trades = _simulate_rule(rule, snapshots, archive, plan, assumptions)
        metrics = calculate_metrics([(trade.entry_time, trade.net_r) for trade in trades])
        stressed = ExecutionAssumptions(
            entry_delay=timedelta(minutes=5),
            commission_per_side_points=assumptions.commission_per_side_points * 1.5,
            slippage_per_side_points=assumptions.slippage_per_side_points * 1.5,
            max_holding=assumptions.max_holding,
            max_tick_gap=assumptions.max_tick_gap,
            max_trades_per_day=assumptions.max_trades_per_day,
        )
        stressed_trades = _simulate_rule(rule, snapshots, archive, plan, stressed)
        neighboring = _neighboring_plans(plan)
        neighboring_net = [
            sum(
                trade.net_r
                for trade in _simulate_rule(
                    rule, snapshots, archive, neighbor, assumptions
                )
            )
            for neighbor in neighboring
        ]
        midpoint = split.holdout_start + (split.holdout_end - split.holdout_start) / 2
        holdout_period_net_r = (
            sum(trade.net_r for trade in trades if trade.entry_time < midpoint),
            sum(trade.net_r for trade in trades if trade.entry_time >= midpoint),
        )
        acceptance = evaluate_acceptance(
            metrics,
            stressed_net_r=sum(trade.net_r for trade in stressed_trades),
            neighboring_parameter_net_r=neighboring_net,
            holdout_period_net_r=holdout_period_net_r,
        )
        results[rule.pattern_id] = acceptance
        report_patterns.append(
            {
                "rule": rule.to_dict(),
                "metrics": asdict(metrics),
                "stress_net_r": sum(trade.net_r for trade in stressed_trades),
                "neighboring_net_r": neighboring_net,
                "acceptance": asdict(acceptance),
                "trades": [_trade_dict(trade) for trade in trades],
            }
        )
    _write_holdout_report(paths.report_root, document, report_patterns)
    return results


def _neighboring_plans(plan: ExitPlan) -> tuple[ExitPlan, ExitPlan]:
    if plan.mode is ExitMode.FIXED_R:
        return (
            ExitPlan(ExitMode.FIXED_R, target_r=max(1.0, plan.target_r - 1)),
            ExitPlan(ExitMode.FIXED_R, target_r=plan.target_r + 1),
        )
    return (
        ExitPlan(
            ExitMode.PARTIAL_TRAIL,
            partial_r=plan.partial_r,
            partial_fraction=plan.partial_fraction,
            trail_atr=max(0.25, plan.trail_atr / 2),
        ),
        ExitPlan(
            ExitMode.PARTIAL_TRAIL,
            partial_r=plan.partial_r,
            partial_fraction=plan.partial_fraction,
            trail_atr=plan.trail_atr * 2,
        ),
    )


def _trade_dict(trade: TickTrade) -> dict[str, object]:
    payload = asdict(trade)
    for key in ("signal_time", "entry_time", "exit_time"):
        payload[key] = getattr(trade, key).isoformat()
    return payload


def _write_discovery_report(
    root: Path, results: Sequence[DiscoveryResult], selected: Sequence[DiscoveryResult]
) -> None:
    root.mkdir(parents=True, exist_ok=True)
    payload = {
        "generated_at": datetime.now(UTC).isoformat(),
        "tested_patterns": len(results),
        "fdr_accepted": sum(result.accepted_by_fdr for result in results),
        "selected": [result.rule.to_dict() for result in selected],
        "results": [
            {
                **asdict(result),
                "rule": result.rule.to_dict(),
            }
            for result in results
        ],
    }
    (root / "discovery_report.json").write_text(
        json.dumps(payload, indent=2, default=str), encoding="utf-8"
    )
    lines = [
        "# XAUUSD Pattern Discovery",
        "",
        f"Tested stable candidates: {len(results)}",
        f"Accepted after FDR: {payload['fdr_accepted']}",
        f"Frozen selections: {len(selected)}",
        "",
    ]
    for result in selected:
        lines.append(
            f"- `{result.rule.pattern_id}` {result.rule.direction}: folds "
            f"{result.fold_expectancies}, net {result.net_r:.2f}R, DD {result.max_drawdown_r:.2f}R"
        )
    (root / "discovery_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_holdout_report(
    root: Path, frozen: Mapping[str, object], patterns: Sequence[Mapping[str, object]]
) -> None:
    payload = {
        "generated_at": datetime.now(UTC).isoformat(),
        "frozen_configuration_sha256": frozen["configuration_sha256"],
        "patterns": patterns,
    }
    (root / "holdout_report.json").write_text(
        json.dumps(payload, indent=2, default=str), encoding="utf-8"
    )
    lines = [
        "# Locked Holdout Results",
        "",
        f"Frozen hash: `{payload['frozen_configuration_sha256']}`",
        "",
    ]
    for pattern in patterns:
        rule = pattern["rule"]
        acceptance = pattern["acceptance"]
        if not isinstance(rule, Mapping) or not isinstance(acceptance, Mapping):
            raise ValueError("report pattern rule and acceptance must be mappings")
        lines.append(
            f"- `{rule['pattern_id']}`: **{acceptance['status']}** — "
            f"{', '.join(acceptance['failures']) or 'all gates passed'}"
        )
    (root / "holdout_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
