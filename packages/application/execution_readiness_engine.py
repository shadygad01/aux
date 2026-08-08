"""Execution Readiness Engine implementation.

Evaluates entry timing and opportunity lifecycle independently from Setup Quality.
Calculates ExecutionReadiness (0-100) and assigns ExecutionStatus
(FRESH, ACTIVE, LATE, EXPIRED, WAIT).
"""

from __future__ import annotations

from datetime import datetime

from packages.domain import (
    DecisionVerdict,
    ExecutionReadiness,
    ExecutionStatus,
    MacroAssessment,
    MarketObservation,
    RangeLocation,
)


class ExecutionReadinessEngine:
    """Calculates Execution Readiness (0-100) and status based on price distance and macro."""

    def evaluate(
        self,
        observation: MarketObservation,
        verdict: DecisionVerdict,
        setup_quality_score: int,
        macro_assessment: MacroAssessment | None,
        evaluated_at: datetime,
    ) -> ExecutionReadiness:
        # Mandatory WAIT gate
        if verdict is DecisionVerdict.WAIT:
            return ExecutionReadiness(
                readiness_score=0,
                status=ExecutionStatus.WAIT,
                confidence=0.0,
                explanation="Mandatory SMC setup conditions incomplete. No execution allowed.",
                distance_from_ideal_entry_pct=0.0,
                target_progress_pct=0.0,
                current_risk_reward=0.0,
                reasons_for_reduction=("Mandatory setup conditions incomplete.",),
                evaluated_at=evaluated_at,
            )

        if macro_assessment and macro_assessment.force_wait:
            return ExecutionReadiness(
                readiness_score=0,
                status=ExecutionStatus.WAIT,
                confidence=0.0,
                explanation=f"Macro context invalidates execution: {macro_assessment.wait_reason}",
                distance_from_ideal_entry_pct=0.0,
                target_progress_pct=0.0,
                current_risk_reward=0.0,
                reasons_for_reduction=(macro_assessment.wait_reason,),
                evaluated_at=evaluated_at,
            )

        dr = observation.dealing_range
        if not dr:
            return ExecutionReadiness(
                readiness_score=0,
                status=ExecutionStatus.WAIT,
                confidence=0.0,
                explanation="Dealing range missing.",
                distance_from_ideal_entry_pct=0.0,
                target_progress_pct=0.0,
                current_risk_reward=0.0,
                reasons_for_reduction=("Dealing range missing.",),
                evaluated_at=evaluated_at,
            )

        # Calculate Price Position and Distances
        range_span = dr.high - dr.low if dr.high > dr.low else 1.0
        price_pos_pct = max(0.0, min(100.0, ((dr.current_price - dr.low) / range_span) * 100.0))

        if verdict is DecisionVerdict.BUY:
            distance_from_ideal_entry = price_pos_pct
            target_progress_pct = price_pos_pct
            is_in_discount = dr.location(0.05) == RangeLocation.DISCOUNT
            risk = max(1.0, dr.current_price - dr.low)
            reward = max(1.0, dr.high - dr.current_price)
        else:
            distance_from_ideal_entry = 100.0 - price_pos_pct
            target_progress_pct = 100.0 - price_pos_pct
            is_in_discount = dr.location(0.05) == RangeLocation.PREMIUM
            risk = max(1.0, dr.high - dr.current_price)
            reward = max(1.0, dr.current_price - dr.low)

        current_rr = round(reward / risk, 2)
        score = 100
        reasons: list[str] = []

        if distance_from_ideal_entry > 60.0:
            score -= 40
            reasons.append(
                f"Price advanced {distance_from_ideal_entry:.1f}% away from ideal entry zone."
            )
        elif distance_from_ideal_entry > 30.0:
            score -= 20
            reasons.append(
                f"Price moved {distance_from_ideal_entry:.1f}% beyond optimal entry zone."
            )

        if target_progress_pct > 70.0:
            score -= 35
            reasons.append(
                f"Price already traveled {target_progress_pct:.1f}% toward target liquidity."
            )
        elif target_progress_pct > 40.0:
            score -= 15
            reasons.append(f"Price traveled {target_progress_pct:.1f}% toward target liquidity.")

        if current_rr < 1.0:
            score -= 30
            reasons.append(f"Risk/Reward ratio deteriorated to {current_rr:.2f}:1 (unfavorable).")
        elif current_rr < 1.8:
            score -= 15
            reasons.append(f"Risk/Reward ratio reduced to {current_rr:.2f}:1.")

        if not is_in_discount:
            score -= 20
            reasons.append("Price exited the optimal Discount/Premium zone.")

        final_score = max(0, min(100, score))

        if target_progress_pct >= 85.0 or current_rr < 0.8 or final_score < 25:
            status = ExecutionStatus.EXPIRED
            explanation = (
                "Setup has completed/expired. Target liquidity nearly reached. Do not chase price."
            )
        elif final_score >= 80 and distance_from_ideal_entry <= 20.0 and current_rr >= 2.2:
            status = ExecutionStatus.FRESH
            explanation = "Optimal execution window is fresh. Immediate execution preferred."
        elif final_score >= 55 and current_rr >= 1.5:
            status = ExecutionStatus.ACTIVE
            explanation = "Setup remains active and executable with favorable Risk/Reward."
        else:
            status = ExecutionStatus.LATE
            explanation = (
                "Setup is technically valid but LATE. Price has advanced; Risk/Reward is reduced. "
                "Recommendation: Wait for a new Discount retracement."
            )

        confidence = final_score / 100.0
        if macro_assessment is not None:
            # Macro never grants or boosts the trade decision itself (that
            # stays a pure structure/location/liquidity/MACD gate) -- it only
            # nudges how confident the execution-timing layer is, same as it
            # can only force WAIT above, never force an entry.
            confidence += macro_assessment.confidence_modifier
        confidence = round(max(0.0, min(1.0, confidence)), 2)

        return ExecutionReadiness(
            readiness_score=final_score,
            status=status,
            confidence=confidence,
            explanation=explanation,
            distance_from_ideal_entry_pct=round(distance_from_ideal_entry, 1),
            target_progress_pct=round(target_progress_pct, 1),
            current_risk_reward=current_rr,
            reasons_for_reduction=tuple(reasons),
            evaluated_at=evaluated_at,
        )
