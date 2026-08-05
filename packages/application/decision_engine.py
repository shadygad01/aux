"""Independent, deterministic decision-engine use case."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from packages.domain import (
    Confidence,
    Decision,
    DecisionPolicy,
    DecisionVerdict,
    LiquiditySide,
    MarketObservation,
    RangeLocation,
    StructureBias,
)

from .errors import DecisionEvaluationError
from .ports import DecisionLogger


class DecisionEngine:
    """Evaluate attention-worthiness; all external effects use injected ports."""

    def __init__(self, policy: DecisionPolicy, decision_logger: DecisionLogger) -> None:
        self._policy = policy
        self._decision_logger = decision_logger

    def evaluate(self, observation: MarketObservation, evaluated_at: datetime) -> Decision:
        if evaluated_at.tzinfo is None:
            raise DecisionEvaluationError(
                f"evaluation time must be timezone-aware; symbol={observation.symbol}"
            )

        missing: list[str] = []
        conflicts: list[str] = []
        reasons: list[str] = []

        if observation.symbol != self._policy.supported_symbol:
            unsupported_symbol = observation.symbol
            supported_symbol = self._policy.supported_symbol
            conflicts.append(
                f"Unsupported symbol {unsupported_symbol}; policy scope is {supported_symbol} only."
            )
        age = evaluated_at - observation.observed_at
        if age < timedelta(0):
            conflicts.append("Observation timestamp is in the future.")
        elif age > self._policy.maximum_age:
            maximum_age = self._policy.maximum_age
            missing.append(f"Fresh evidence required; observation age {age} exceeds {maximum_age}.")
        if observation.structure is None:
            missing.append("SMC market-structure evidence is missing.")
        if observation.dealing_range is None:
            missing.append("Premium/discount dealing range is missing.")
        if not observation.liquidity:
            missing.append("Liquidity evidence is missing.")

        if missing or conflicts:
            return self._recorded_decision(
                DecisionVerdict.WAIT, 0.0, evaluated_at, observation, reasons, conflicts, missing
            )

        structure = observation.structure
        dealing_range = observation.dealing_range
        if structure is None or dealing_range is None:
            raise DecisionEvaluationError(
                f"mandatory evidence gate invariant failed; symbol={observation.symbol}; "
                f"observed_at={observation.observed_at.isoformat()}"
            )
        if structure.bias is StructureBias.NEUTRAL:
            conflicts.append("Market structure is neutral; no directional thesis is justified.")
            return self._recorded_decision(
                DecisionVerdict.WAIT, 0.0, evaluated_at, observation, reasons, conflicts, missing
            )

        candidate = (
            DecisionVerdict.BUY if structure.bias is StructureBias.BULLISH else DecisionVerdict.SELL
        )
        required_location = (
            RangeLocation.DISCOUNT if candidate is DecisionVerdict.BUY else RangeLocation.PREMIUM
        )
        location = dealing_range.location(self._policy.equilibrium_band)
        required_sweep = (
            LiquiditySide.SELL_SIDE if candidate is DecisionVerdict.BUY else LiquiditySide.BUY_SIDE
        )

        score = 0.0
        if structure.break_of_structure:
            score += self._policy.structure_weight
            reasons.append(
                f"{structure.bias.value.title()} structure has a confirmed break of structure."
            )
        else:
            conflicts.append("Directional bias lacks a confirmed break of structure.")

        if location is required_location:
            score += self._policy.location_weight
            reasons.append(
                f"Price is in {location.value.lower()}, aligned with the {candidate.value} thesis."
            )
        else:
            actual_location = location.value.lower()
            expected_location = required_location.value.lower()
            conflicts.append(
                f"Price is in {actual_location}; {candidate.value} requires {expected_location}."
            )

        confirmed_sweep = any(
            event.side is required_sweep and event.swept and event.displacement_confirmed
            for event in observation.liquidity
        )
        if confirmed_sweep:
            score += self._policy.liquidity_weight
            swept_side = required_sweep.value.replace("_", " ").title()
            reasons.append(f"{swept_side} liquidity was swept with displacement confirmation.")
        else:
            missing_side = required_sweep.value.replace("_", " ").lower()
            conflicts.append(f"No confirmed {missing_side} liquidity sweep supports the thesis.")

        normalized_score = round(score, 4)
        verdict = (
            candidate
            if not conflicts and normalized_score >= self._policy.attention_threshold
            else DecisionVerdict.WAIT
        )
        return self._recorded_decision(
            verdict, normalized_score, evaluated_at, observation, reasons, conflicts, missing
        )

    def _recorded_decision(
        self,
        verdict: DecisionVerdict,
        score: float,
        evaluated_at: datetime,
        observation: MarketObservation,
        reasons: list[str],
        conflicts: list[str],
        missing: list[str],
    ) -> Decision:
        confidence = self._confidence(verdict, score)
        decision = Decision(
            verdict=verdict,
            confidence=confidence,
            score=score,
            evaluated_at=evaluated_at.astimezone(UTC),
            observation_time=observation.observed_at.astimezone(UTC),
            reasons=tuple(reasons),
            conflicts=tuple(conflicts),
            missing_evidence=tuple(missing),
            policy_version=self._policy.version,
            contract_version=self._policy.output_contract_version,
            disclaimer=self._policy.disclaimer,
        )
        try:
            self._decision_logger.record(observation, decision)
        except Exception as error:
            raise DecisionEvaluationError(
                f"decision logging failed; symbol={observation.symbol}; "
                f"verdict={decision.verdict.value}; policy={decision.policy_version}"
            ) from error
        return decision

    def _confidence(self, verdict: DecisionVerdict, score: float) -> Confidence:
        if verdict is DecisionVerdict.WAIT:
            return Confidence.NONE if score == 0 else Confidence.LOW
        return Confidence.HIGH
