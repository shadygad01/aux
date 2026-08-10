"""Interpretable rule discovery with chronological validation and FDR control."""

from __future__ import annotations

import hashlib
import json
import math
import random
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass
from datetime import datetime
from enum import StrEnum

from .mtf_models import Direction
from .research_governance import benjamini_hochberg, calculate_metrics


class Operator(StrEnum):
    EQ = "EQ"
    LE = "LE"
    GE = "GE"


@dataclass(frozen=True, slots=True)
class Condition:
    feature: str
    operator: Operator
    value: bool | float | int | str

    def matches(self, features: Mapping[str, object]) -> bool:
        actual = features.get(self.feature)
        if self.operator is Operator.EQ:
            return actual == self.value
        if not isinstance(actual, int | float) or not isinstance(self.value, int | float):
            return False
        return actual <= self.value if self.operator is Operator.LE else actual >= self.value


@dataclass(frozen=True, slots=True)
class LabeledOpportunity:
    timestamp: datetime
    exit_time: datetime
    direction: Direction
    exit_plan_id: str
    features: Mapping[str, object]
    net_r: float


def _manual_portfolio(items: Sequence[LabeledOpportunity]) -> list[LabeledOpportunity]:
    selected: list[LabeledOpportunity] = []
    busy_until: datetime | None = None
    daily: dict[object, int] = {}
    for item in sorted(items, key=lambda opportunity: opportunity.timestamp):
        if busy_until is not None and item.timestamp < busy_until:
            continue
        day = item.timestamp.date()
        if daily.get(day, 0) >= 3:
            continue
        selected.append(item)
        daily[day] = daily.get(day, 0) + 1
        busy_until = item.exit_time
    return selected


@dataclass(frozen=True, slots=True)
class PatternRule:
    pattern_id: str
    direction: Direction
    exit_plan_id: str
    conditions: tuple[Condition, ...]

    def matches(self, opportunity: LabeledOpportunity) -> bool:
        return (
            opportunity.direction is self.direction
            and opportunity.exit_plan_id == self.exit_plan_id
            and all(condition.matches(opportunity.features) for condition in self.conditions)
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "pattern_id": self.pattern_id,
            "direction": self.direction.value,
            "exit_plan_id": self.exit_plan_id,
            "conditions": [asdict(condition) for condition in self.conditions],
        }


@dataclass(frozen=True, slots=True)
class DiscoveryResult:
    rule: PatternRule
    sample_size: int
    p_value: float
    fold_expectancies: tuple[float, ...]
    net_r: float
    max_drawdown_r: float
    accepted_by_fdr: bool


def _pattern_id(direction: Direction, exit_plan_id: str, conditions: Sequence[Condition]) -> str:
    payload = {
        "direction": direction.value,
        "exit_plan_id": exit_plan_id,
        "conditions": [asdict(condition) for condition in conditions],
    }
    digest = hashlib.sha256(json.dumps(payload, sort_keys=True, default=str).encode()).hexdigest()
    return f"PAT-{digest[:12].upper()}"


def generate_rules(
    directions: Sequence[Direction],
    exit_plan_ids: Sequence[str],
    condition_space: Mapping[str, Sequence[tuple[Operator, bool | float | int | str]]],
    *,
    maximum_conditions: int = 2,
) -> list[PatternRule]:
    if maximum_conditions not in (1, 2):
        raise ValueError("maximum_conditions must be one or two")
    atomic = [
        Condition(feature, operator, value)
        for feature, candidates in sorted(condition_space.items())
        for operator, value in candidates
    ]
    combinations: list[tuple[Condition, ...]] = [(condition,) for condition in atomic]
    if maximum_conditions == 2:
        combinations += [
            (left, right)
            for index, left in enumerate(atomic)
            for right in atomic[index + 1 :]
            if left.feature != right.feature
        ]
    return [
        PatternRule(
            pattern_id=_pattern_id(direction, exit_plan_id, conditions),
            direction=direction,
            exit_plan_id=exit_plan_id,
            conditions=conditions,
        )
        for direction in directions
        for exit_plan_id in exit_plan_ids
        for conditions in combinations
    ]


def _one_sided_sign_flip(values: Sequence[float], *, seed: int, samples: int = 2000) -> float:
    if not values:
        return 1.0
    observed = sum(values) / len(values)
    if observed <= 0:
        return 1.0
    rng = random.Random(seed)
    exceedances = 0
    for _ in range(samples):
        mean = sum(value * rng.choice((-1, 1)) for value in values) / len(values)
        exceedances += mean >= observed
    return (exceedances + 1) / (samples + 1)


def discover_rules(
    opportunities: Sequence[LabeledOpportunity],
    rules: Sequence[PatternRule],
    validation_boundaries: Sequence[datetime],
    *,
    minimum_fold_trades: int = 20,
    fdr_alpha: float = 0.05,
) -> list[DiscoveryResult]:
    if len(validation_boundaries) < 2:
        raise ValueError("at least two validation boundaries are required")
    preliminary: list[tuple[PatternRule, list[LabeledOpportunity], tuple[float, ...], float]] = []
    for rule in rules:
        matched = _manual_portfolio([item for item in opportunities if rule.matches(item)])
        fold_expectancies: list[float] = []
        stable = True
        for start, end in zip(validation_boundaries, validation_boundaries[1:], strict=False):
            fold = [item.net_r for item in matched if start <= item.timestamp < end]
            if len(fold) < minimum_fold_trades:
                stable = False
                break
            fold_expectancies.append(sum(fold) / len(fold))
        if not stable or min(fold_expectancies, default=-math.inf) <= 0:
            continue
        values = [item.net_r for item in matched]
        seed = int(rule.pattern_id[-8:], 16)
        p_value = _one_sided_sign_flip(values, seed=seed)
        preliminary.append((rule, matched, tuple(fold_expectancies), p_value))
    accepted = benjamini_hochberg(
        {rule.pattern_id: p_value for rule, _, _, p_value in preliminary}, fdr_alpha
    )
    results: list[DiscoveryResult] = []
    for rule, matched, stable_fold_expectancies, p_value in preliminary:
        metrics = calculate_metrics([(item.timestamp, item.net_r) for item in matched])
        results.append(
            DiscoveryResult(
                rule=rule,
                sample_size=len(matched),
                p_value=p_value,
                fold_expectancies=stable_fold_expectancies,
                net_r=metrics.net_r,
                max_drawdown_r=metrics.max_drawdown_r,
                accepted_by_fdr=rule.pattern_id in accepted,
            )
        )
    return sorted(
        results,
        key=lambda result: (
            not result.accepted_by_fdr,
            -min(result.fold_expectancies),
            result.max_drawdown_r,
            result.rule.pattern_id,
        ),
    )
