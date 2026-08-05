"""Version 3 expiring-evidence decision engine with exactly four outputs."""

from datetime import datetime
from math import prod

from packages.domain import (
    Evidence,
    EvidenceDecision,
    EvidenceDirection,
    EvidenceKind,
    EvidencePolicy,
    Recommendation,
    WeightedEvidence,
)

from .errors import DecisionEvaluationError
from .ports import EvidenceDecisionAudit


class EvidenceDecisionEngine:
    def __init__(self, policy: EvidencePolicy, audit: EvidenceDecisionAudit) -> None:
        self._policy = policy
        self._audit = audit

    def evaluate(self, evidence: tuple[Evidence, ...], evaluated_at: datetime) -> EvidenceDecision:
        if evaluated_at.tzinfo is None:
            raise DecisionEvaluationError("evidence evaluation time must be timezone-aware")
        identifiers = [item.evidence_id for item in evidence]
        if len(set(identifiers)) != len(identifiers):
            raise DecisionEvaluationError("evidence identifiers must be unique within a snapshot")

        weighted: list[WeightedEvidence] = []
        why_not: list[str] = []
        reliable: list[WeightedEvidence] = []
        force_wait_reasons: list[str] = []
        for item in evidence:
            if item.observed_at > evaluated_at:
                freshness = 0.0
                effective_weight = 0.0
                why_not.append(f"{item.kind.value} evidence is future-dated and excluded.")
            else:
                freshness = item.freshness(evaluated_at)
                factors = (
                    item.strength,
                    item.reliability,
                    item.importance,
                    item.historical_performance,
                    item.confidence,
                )
                base_weight = prod(factors) ** (1 / len(factors))
                effective_weight = base_weight * freshness
                if freshness == 0:
                    why_not.append(
                        f"{item.kind.value} evidence expired at {item.expires_at.isoformat()}."
                    )
            weighted_item = WeightedEvidence(
                evidence_id=item.evidence_id,
                kind=item.kind,
                direction=item.direction,
                freshness=round(freshness, self._policy.weight_precision),
                effective_weight=round(effective_weight, self._policy.weight_precision),
                expires_at=item.expires_at,
                rationale=item.rationale,
            )
            weighted.append(weighted_item)
            if effective_weight >= self._policy.minimum_reliable_weight:
                reliable.append(weighted_item)
                if item.forces_wait:
                    force_wait_reasons.append(
                        f"{item.rationale} until {item.expires_at.isoformat()}"
                    )
            elif freshness > 0:
                why_not.append(
                    f"{item.kind.value} evidence is below the reliable-weight threshold."
                )

        buy_weight = sum(
            item.effective_weight for item in reliable if item.direction is EvidenceDirection.BUY
        )
        sell_weight = sum(
            item.effective_weight for item in reliable if item.direction is EvidenceDirection.SELL
        )
        directional_weight = buy_weight + sell_weight
        if directional_weight == 0:
            confidence = 0
        else:
            confidence = round(abs(buy_weight - sell_weight) / directional_weight * 100)
        candidate = (
            EvidenceDirection.BUY
            if buy_weight > sell_weight
            else EvidenceDirection.SELL
            if sell_weight > buy_weight
            else EvidenceDirection.NEUTRAL
        )

        reliable_kinds = {item.kind for item in reliable if item.direction is candidate}
        foundation_kinds = {EvidenceKind.MACRO, EvidenceKind.MARKET_BIAS}
        missing_foundation = sorted(foundation_kinds - reliable_kinds, key=lambda item: item.value)
        insufficient = (
            directional_weight < self._policy.minimum_directional_weight
            or confidence < self._policy.minimum_directional_confidence
            or candidate is EvidenceDirection.NEUTRAL
            or bool(missing_foundation)
        )

        missing_kinds = sorted(
            set(self._policy.required_execution_kinds) - reliable_kinds,
            key=lambda item: item.value,
        )
        completeness = (len(self._policy.required_execution_kinds) - len(missing_kinds)) / len(
            self._policy.required_execution_kinds
        )
        trade_quality = round(confidence * completeness)
        why = tuple(
            f"{item.kind.value}: {item.rationale} "
            f"(effective weight {item.effective_weight:.{self._policy.weight_precision}f})"
            for item in reliable
            if item.direction is candidate
        )
        missing = tuple(f"Reliable {kind.value} evidence is missing." for kind in missing_kinds)

        if insufficient:
            recommendation = Recommendation.NO_OPINION
        elif (
            force_wait_reasons
            or missing_kinds
            or trade_quality < self._policy.minimum_trade_quality
        ):
            recommendation = Recommendation.WAIT
        elif candidate is EvidenceDirection.BUY:
            recommendation = Recommendation.BUY_SETUPS_ONLY
        else:
            recommendation = Recommendation.SELL_SETUPS_ONLY

        change_conditions: list[str] = []
        if recommendation is Recommendation.NO_OPINION:
            change_conditions.append("Add fresh, reliable macro and market-bias evidence.")
            change_conditions.append(
                f"Directional confidence must reach {self._policy.minimum_directional_confidence}."
            )
        elif recommendation is Recommendation.WAIT:
            change_conditions.extend(missing)
            change_conditions.extend(
                f"Wait until this condition clears: {reason}" for reason in force_wait_reasons
            )
            if trade_quality < self._policy.minimum_trade_quality:
                change_conditions.append(
                    f"Trade quality must reach {self._policy.minimum_trade_quality}."
                )
        else:
            change_conditions.append(
                "A required evidence expiry, stronger contradiction, or pause condition "
                "would change this decision."
            )

        decision = EvidenceDecision(
            recommendation=recommendation,
            trade_quality=trade_quality,
            confidence=confidence,
            why=why,
            why_not=tuple(why_not),
            missing=missing,
            what_would_change=tuple(change_conditions),
            evidence=tuple(weighted),
            evaluated_at=evaluated_at,
            policy_version=self._policy.version,
            contract_version=self._policy.contract_version,
        )
        try:
            self._audit.record(evidence, decision)
        except Exception as error:
            raise DecisionEvaluationError(
                f"evidence decision audit failed; recommendation={decision.recommendation.value}; "
                f"evaluated_at={evaluated_at.isoformat()}"
            ) from error
        return decision
