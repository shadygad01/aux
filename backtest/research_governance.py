"""Holdout locking, configuration freezing, FDR, and acceptance gates."""

from __future__ import annotations

import hashlib
import json
import math
import random
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import TypeVar

T = TypeVar("T")


@dataclass(frozen=True, slots=True)
class ResearchSplit:
    discovery_start: datetime
    holdout_start: datetime
    holdout_end: datetime
    embargo: timedelta

    def __post_init__(self) -> None:
        boundaries = (self.discovery_start, self.holdout_start, self.holdout_end)
        if any(value.tzinfo is None for value in boundaries):
            raise ValueError("research boundaries must be timezone-aware")
        if not self.discovery_start < self.holdout_start < self.holdout_end:
            raise ValueError("research boundaries must be increasing")
        if self.embargo < timedelta(0):
            raise ValueError("embargo must be non-negative")


@dataclass(frozen=True, slots=True)
class FrozenConfiguration:
    schema_version: str
    frozen_at: str
    split: dict[str, str]
    selected_patterns: tuple[dict[str, object], ...]
    configuration_sha256: str


@dataclass(frozen=True, slots=True)
class DirectionMetrics:
    trades: int
    expectancy: float | None
    expectancy_ci_low: float | None
    profit_factor: float | None
    net_r: float
    max_drawdown_r: float
    max_losing_streak: int
    yearly_net_r: dict[int, float]
    largest_profit_concentration: float | None
    largest_month_concentration: float | None


@dataclass(frozen=True, slots=True)
class AcceptanceResult:
    status: str
    failures: tuple[str, ...]


def discovery_rows(
    rows: Sequence[T], split: ResearchSplit, timestamp: Callable[[T], datetime]
) -> list[T]:
    boundary = split.holdout_start - split.embargo
    return [row for row in rows if split.discovery_start <= timestamp(row) < boundary]


def holdout_rows(
    rows: Sequence[T],
    split: ResearchSplit,
    timestamp: Callable[[T], datetime],
    *,
    frozen_configuration: Path,
) -> list[T]:
    verify_frozen_configuration(frozen_configuration)
    return [row for row in rows if split.holdout_start <= timestamp(row) < split.holdout_end]


def _canonical_payload(
    split: ResearchSplit, selected_patterns: Sequence[Mapping[str, object]]
) -> dict[str, object]:
    return {
        "schema_version": "1.0.0",
        "split": {
            "discovery_start": split.discovery_start.isoformat(),
            "holdout_start": split.holdout_start.isoformat(),
            "holdout_end": split.holdout_end.isoformat(),
            "embargo_seconds": str(int(split.embargo.total_seconds())),
        },
        "selected_patterns": [dict(pattern) for pattern in selected_patterns],
    }


def freeze_configuration(
    split: ResearchSplit,
    selected_patterns: Sequence[Mapping[str, object]],
    path: Path,
    *,
    frozen_at: datetime,
) -> FrozenConfiguration:
    if frozen_at.tzinfo is None:
        raise ValueError("frozen_at must be timezone-aware")
    payload = _canonical_payload(split, selected_patterns)
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    digest = hashlib.sha256(canonical).hexdigest()
    document = {
        **payload,
        "frozen_at": frozen_at.isoformat(),
        "configuration_sha256": digest,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(document, indent=2), encoding="utf-8")
    return FrozenConfiguration(
        schema_version="1.0.0",
        frozen_at=frozen_at.isoformat(),
        split={
            "discovery_start": split.discovery_start.isoformat(),
            "holdout_start": split.holdout_start.isoformat(),
            "holdout_end": split.holdout_end.isoformat(),
            "embargo_seconds": str(int(split.embargo.total_seconds())),
        },
        selected_patterns=tuple(dict(item) for item in selected_patterns),
        configuration_sha256=digest,
    )


def verify_frozen_configuration(path: Path) -> dict[str, object]:
    if not path.exists():
        raise PermissionError("holdout is locked until a configuration is frozen")
    document = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(document, dict):
        raise ValueError("frozen configuration must be a JSON object")
    selected = document.get("selected_patterns")
    split = document.get("split")
    expected = document.get("configuration_sha256")
    if (
        not isinstance(selected, list)
        or not isinstance(split, dict)
        or not isinstance(expected, str)
    ):
        raise ValueError("invalid frozen configuration")
    payload = {
        "schema_version": document.get("schema_version"),
        "split": split,
        "selected_patterns": selected,
    }
    actual = hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    if actual != expected:
        raise PermissionError("frozen configuration hash mismatch")
    return document


def benjamini_hochberg(p_values: Mapping[str, float], alpha: float = 0.05) -> set[str]:
    if not 0 < alpha < 1:
        raise ValueError("alpha must be between zero and one")
    ordered = sorted(p_values.items(), key=lambda item: (item[1], item[0]))
    accepted_index = -1
    total = len(ordered)
    for index, (_, value) in enumerate(ordered, start=1):
        if not 0 <= value <= 1:
            raise ValueError("p-values must be between zero and one")
        if value <= alpha * index / total:
            accepted_index = index
    return {name for name, _ in ordered[:accepted_index]} if accepted_index >= 0 else set()


def _bootstrap_ci(
    values: Sequence[float], *, seed: int = 17, samples: int = 2000
) -> tuple[float, float]:
    if not values:
        raise ValueError("bootstrap requires values")
    rng = random.Random(seed)
    means = sorted(
        sum(rng.choice(values) for _ in values) / len(values) for _ in range(samples)
    )
    return means[int(samples * 0.025)], means[min(samples - 1, int(samples * 0.975))]


def calculate_metrics(trades: Sequence[tuple[datetime, float]]) -> DirectionMetrics:
    if not trades:
        return DirectionMetrics(0, None, None, None, 0.0, 0.0, 0, {}, None, None)
    values = [value for _, value in trades]
    ci_low, _ = _bootstrap_ci(values)
    gains = sum(value for value in values if value > 0)
    losses = -sum(value for value in values if value < 0)
    equity = peak = drawdown = 0.0
    current_streak = max_streak = 0
    yearly: dict[int, float] = {}
    monthly: dict[tuple[int, int], float] = {}
    for (timestamp, value) in trades:
        equity += value
        peak = max(peak, equity)
        drawdown = max(drawdown, peak - equity)
        current_streak = current_streak + 1 if value < 0 else 0
        max_streak = max(max_streak, current_streak)
        yearly[timestamp.year] = yearly.get(timestamp.year, 0.0) + value
        month = (timestamp.year, timestamp.month)
        monthly[month] = monthly.get(month, 0.0) + value
    positive = [value for value in values if value > 0]
    concentration = max(positive) / gains if gains > 0 and positive else None
    positive_months = [value for value in monthly.values() if value > 0]
    month_gains = sum(positive_months)
    month_concentration = (
        max(positive_months) / month_gains if month_gains > 0 and positive_months else None
    )
    return DirectionMetrics(
        trades=len(values),
        expectancy=sum(values) / len(values),
        expectancy_ci_low=ci_low,
        profit_factor=(gains / losses if losses > 0 else math.inf),
        net_r=sum(values),
        max_drawdown_r=drawdown,
        max_losing_streak=max_streak,
        yearly_net_r=yearly,
        largest_profit_concentration=concentration,
        largest_month_concentration=month_concentration,
    )


def evaluate_acceptance(
    metrics: DirectionMetrics,
    *,
    stressed_net_r: float,
    neighboring_parameter_net_r: Sequence[float],
    holdout_period_net_r: Sequence[float],
) -> AcceptanceResult:
    if metrics.trades < 60:
        return AcceptanceResult("INSUFFICIENT_EVIDENCE", ("fewer than 60 decided trades",))
    failures: list[str] = []
    if metrics.expectancy is None or metrics.expectancy <= 0:
        failures.append("expectancy is not positive")
    if metrics.expectancy_ci_low is None or metrics.expectancy_ci_low <= 0:
        failures.append("bootstrap 95% lower bound is not positive")
    if metrics.profit_factor is None or metrics.profit_factor < 1.2:
        failures.append("profit factor is below 1.20")
    if len(holdout_period_net_r) != 2 or any(value <= 0 for value in holdout_period_net_r):
        failures.append("one or more 12-month holdout periods are not profitable")
    if metrics.max_drawdown_r > 15:
        failures.append("max drawdown exceeds 15R")
    if metrics.max_losing_streak > 10:
        failures.append("max losing streak exceeds 10")
    if stressed_net_r < 0:
        failures.append("1.5x-cost/5-minute-delay stress is negative")
    concentrations = (
        metrics.largest_profit_concentration,
        metrics.largest_month_concentration,
    )
    if any(value is None or value > 0.4 for value in concentrations):
        failures.append("profit concentration exceeds 40%")
    if not neighboring_parameter_net_r or min(neighboring_parameter_net_r) < 0:
        failures.append("neighboring parameter robustness failed")
    return AcceptanceResult("REJECTED" if failures else "SUPPORTED", tuple(failures))
