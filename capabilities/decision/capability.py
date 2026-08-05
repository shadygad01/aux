"""Decision capability: authorize a reasoned recommendation as the official output."""

from dataclasses import dataclass
from datetime import datetime

from capabilities.contracts import (
    CapabilityHealth,
    CapabilityLog,
    CapabilityMetric,
    CapabilityTelemetry,
    HealthState,
    LogLevel,
)
from packages.domain import (
    ComprehensionVerdict,
    CritiqueStage,
    CurrentMarketState,
    DecisionCritique,
    DecisionExplanation,
    ReasoningComprehensionReview,
    ReasoningDecision,
    Recommendation,
    RecommendationTrust,
)


@dataclass(frozen=True, slots=True)
class OfficialDecision:
    decision_id: str
    reasoning_id: str
    recommendation: Recommendation
    trade_quality: int
    reliability: int
    explanation: DecisionExplanation
    critique_id: str
    trust: RecommendationTrust
    market_state_id: str
    comprehension_review_id: str
    decided_at: datetime
    contract_version: str = "5.0.0"

    def __post_init__(self) -> None:
        if self.decided_at.tzinfo is None:
            raise ValueError("official decision timestamp must be timezone-aware")
        if not self.decision_id.strip() or not self.reasoning_id.strip():
            raise ValueError("official decision identity is required")
        if not self.critique_id.strip():
            raise ValueError("official decision requires a self-critique")
        if not self.market_state_id.strip():
            raise ValueError("official decision requires current market state")
        if not self.comprehension_review_id.strip():
            raise ValueError("official decision requires institutional comprehension review")
        if self.explanation.decision is not self.recommendation:
            raise ValueError("official decision and explanation must match")
        if self.trust.recommendation is not self.recommendation:
            raise ValueError("official decision and trust manifest must match")


class DecisionCapability:
    name = "decision"

    def __init__(self, telemetry: CapabilityTelemetry) -> None:
        self._telemetry = telemetry

    def decide(
        self,
        decision_id: str,
        reasoning: ReasoningDecision,
        explanation: DecisionExplanation,
        critique: DecisionCritique,
        trust: RecommendationTrust,
        state: CurrentMarketState,
        comprehension: ReasoningComprehensionReview,
    ) -> OfficialDecision:
        if len(reasoning.stages) != 9:
            raise ValueError("official decision requires all nine reasoning stages")
        if explanation.decision is not reasoning.recommendation:
            raise ValueError("explanation decision must match the reasoning recommendation")
        if (
            critique.decision_id != decision_id
            or critique.stage is not CritiqueStage.PRE_PUBLICATION
        ):
            raise ValueError("official decision requires its matching pre-publication critique")
        if trust.recommendation is not reasoning.recommendation:
            raise ValueError("trust recommendation must match the reasoning recommendation")
        if trust.confidence != reasoning.reliability:
            raise ValueError("trust confidence must reproduce reasoning reliability")
        if not state.is_current(reasoning.evaluated_at):
            raise ValueError("official decision requires the current market state")
        if (
            comprehension.reasoning_id != reasoning.reasoning_id
            or comprehension.verdict is not ComprehensionVerdict.APPROVED
        ):
            raise ValueError("official decision requires an approved comprehension review")
        trace_facts = {trace.fact for trace in explanation.traces}
        if not set(trust.facts).issubset(trace_facts):
            raise ValueError("trust facts must resolve through the explanation tree")
        decision = OfficialDecision(
            decision_id,
            reasoning.reasoning_id,
            reasoning.recommendation,
            reasoning.trade_quality,
            reasoning.reliability,
            explanation,
            critique.critique_id,
            trust,
            state.state_id,
            comprehension.review_id,
            reasoning.evaluated_at,
        )
        self._telemetry.metric(CapabilityMetric(self.name, "official_decisions", 1, "decisions"))
        self._telemetry.log(
            CapabilityLog(
                self.name, LogLevel.INFO, "decision_authorized", (("decision_id", decision_id),)
            )
        )
        return decision

    def health(self, checked_at: datetime) -> CapabilityHealth:
        return CapabilityHealth(
            self.name, HealthState.HEALTHY, checked_at, "decision contract configured"
        )
