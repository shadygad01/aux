"""Eight-stage, fail-closed trading-constitution evaluation engine."""

from datetime import datetime, timedelta

from packages.domain import (
    AttentionBias,
    LiquiditySide,
    NewsEffect,
    OpportunityExecutionStatus,
    RangeLocation,
    TradingDecision,
    TradingHorizon,
    TradingObservation,
    TradingPolicy,
)

from .errors import DecisionEvaluationError
from .ports import OpportunityRepository, TradingDecisionLogger


class TradingOpportunityEngine:
    """Evaluate setup-search permission; never produce execution instructions."""

    def __init__(
        self,
        policy: TradingPolicy,
        logger: TradingDecisionLogger,
        repository: OpportunityRepository,
    ) -> None:
        self._policy = policy
        self._logger = logger
        self._repository = repository

    def evaluate(self, observation: TradingObservation, evaluated_at: datetime) -> TradingDecision:
        if evaluated_at.tzinfo is None:
            raise DecisionEvaluationError(
                f"evaluation time must be timezone-aware; opportunity={observation.opportunity_id}"
            )

        support: list[str] = []
        conflicts: list[str] = []
        missing: list[str] = []
        score = 0
        forced_status: OpportunityExecutionStatus | None = None

        if observation.symbol != self._policy.supported_symbol:
            conflicts.append(f"Unsupported symbol {observation.symbol}.")
        age = evaluated_at - observation.observed_at
        if age < timedelta(0):
            conflicts.append("Observation timestamp is in the future.")
        elif age > self._policy.maximum_age:
            missing.append("Fresh market context is required.")

        required_horizons = set(TradingHorizon)
        supplied_horizons = {item.horizon for item in observation.horizon_biases}
        absent_horizons = required_horizons - supplied_horizons
        for horizon in sorted(absent_horizons, key=lambda item: item.value):
            missing.append(f"{horizon.value} bias is missing.")
        execution_bias = next(
            (
                item.bias
                for item in observation.horizon_biases
                if item.horizon is observation.execution_horizon
            ),
            None,
        )
        if execution_bias is None:
            missing.append("Execution-horizon bias is missing.")
        elif execution_bias is AttentionBias.WAIT:
            conflicts.append("Execution-horizon bias is WAIT.")
        else:
            score += self._policy.execution_bias_points
            support.append(f"{observation.execution_horizon.value} bias is {execution_bias.value}.")
            directional_biases = {
                item.bias
                for item in observation.horizon_biases
                if item.bias is not AttentionBias.WAIT
            }
            if directional_biases == {execution_bias}:
                score += self._policy.cross_horizon_alignment_points
                support.append("Directional timeframes do not contradict the execution horizon.")
            elif len(directional_biases) > 1:
                conflicts.append("Directional timeframes disagree.")

        if observation.macro is None:
            missing.append("Macro environment assessment is missing.")
        elif execution_bias is not None and observation.macro.bias is execution_bias:
            score += self._policy.macro_points
            support.append(f"Macro supports {execution_bias.value}: {observation.macro.reasoning}")
            for factor in observation.macro.contradicting_factors:
                conflicts.append(f"Macro contradiction: {factor}")
                score -= self._policy.macro_contradiction_penalty_points
        elif observation.macro.bias is AttentionBias.WAIT:
            conflicts.append(f"Macro requires WAIT: {observation.macro.reasoning}")
        else:
            conflicts.append(f"Macro disagrees with execution bias: {observation.macro.reasoning}")

        required_location = None
        required_liquidity_side = None
        relevant_levels: tuple[str, ...] = ()
        if execution_bias is AttentionBias.BUY_ONLY:
            required_location = RangeLocation.DISCOUNT
            required_liquidity_side = LiquiditySide.SELL_SIDE
            relevant_levels = self._policy.buy_liquidity_levels
        elif execution_bias is AttentionBias.SELL_ONLY:
            required_location = RangeLocation.PREMIUM
            required_liquidity_side = LiquiditySide.BUY_SIDE
            relevant_levels = self._policy.sell_liquidity_levels

        if observation.dealing_range is None:
            missing.append("Premium/discount location is missing.")
        elif required_location is not None:
            location = observation.dealing_range.location(self._policy.equilibrium_band)
            if location is required_location:
                score += self._policy.location_points
                support.append(f"Location grants permission: {location.value}.")
            else:
                conflicts.append(
                    f"Location is {location.value}; required location is {required_location.value}."
                )

        if observation.smc is None:
            missing.append("SMC evidence is missing.")
        else:
            sweep = observation.smc.liquidity_event
            if sweep is None:
                missing.append("Mandatory liquidity sweep is missing.")
            elif (
                required_liquidity_side is not None
                and sweep.side is required_liquidity_side
                and sweep.swept
            ):
                score += self._policy.liquidity_sweep_points
                support.append(f"Mandatory {sweep.side.value} liquidity sweep is confirmed.")
            else:
                conflicts.append("Liquidity sweep does not support the execution bias.")

            if observation.smc.reversal_candle_confirmed:
                score += self._policy.reversal_candle_points
                support.append("Mandatory reversal candle is confirmed.")
            else:
                missing.append("Mandatory reversal candle is missing.")

            optional_confirmations = sum(
                (
                    observation.smc.change_of_character,
                    observation.smc.order_block,
                    observation.smc.fair_value_gap,
                )
            )
            optional_total = 3
            optional_score = round(
                self._policy.optional_smc_points * optional_confirmations / optional_total
            )
            score += optional_score
            if optional_confirmations:
                support.append(f"{optional_confirmations} optional SMC confirmations are present.")
            else:
                missing.append("No optional CHoCH, order block, or fair value gap confirmation.")

        if relevant_levels and set(observation.nearby_liquidity_levels).intersection(
            relevant_levels
        ):
            score += self._policy.nearby_liquidity_points
            support.append("A context-relevant prior liquidity level is nearby.")
        else:
            missing.append("No context-relevant prior liquidity level is nearby.")

        if observation.momentum is None:
            missing.append("Mandatory MACD evidence is missing.")
        elif execution_bias is AttentionBias.BUY_ONLY and observation.momentum.macd_value < 0:
            score += self._policy.macd_points
            support.append("MACD is below zero and permits BUY evaluation.")
        elif execution_bias is AttentionBias.SELL_ONLY and observation.momentum.macd_value > 0:
            score += self._policy.macd_points
            support.append("MACD is above zero and permits SELL evaluation.")
        else:
            conflicts.append("MACD is on the wrong side of zero for the execution bias.")

        for news in observation.news:
            if news.expected_until < evaluated_at:
                continue
            if news.effect is NewsEffect.PAUSES_EXECUTION:
                forced_status = OpportunityExecutionStatus.PAUSED
            elif news.effect in {NewsEffect.FORCE_WAIT, NewsEffect.REJECTS_SETUP}:
                forced_status = OpportunityExecutionStatus.WAIT
            elif news.effect is NewsEffect.REDUCES_CONFIDENCE:
                conflicts.append(f"Active news reduces confidence: {news.why}")
                score -= round(self._policy.news_confidence_penalty_points * news.confidence)
            elif (
                news.effect is NewsEffect.SUPPORTS_BUY and execution_bias is AttentionBias.BUY_ONLY
            ) or (
                news.effect is NewsEffect.SUPPORTS_SELL
                and execution_bias is AttentionBias.SELL_ONLY
            ):
                support.append(f"Active news supports the bias: {news.why}")
            else:
                conflicts.append(f"Active news contradicts the bias: {news.why}")

        quality = max(0, min(100, score))
        non_blocking_missing = (
            "No optional CHoCH",
            "No context-relevant prior liquidity level",
        )
        non_blocking_conflicts = (
            "Macro contradiction:",
            "Active news reduces confidence:",
        )
        mandatory_failure = any(
            not item.startswith(non_blocking_missing) for item in missing
        ) or any(not item.startswith(non_blocking_conflicts) for item in conflicts)
        if forced_status is not None:
            status = forced_status
        elif mandatory_failure or quality < self._policy.minimum_trade_quality:
            status = OpportunityExecutionStatus.WAIT
        elif execution_bias is AttentionBias.BUY_ONLY:
            status = OpportunityExecutionStatus.SEARCH_BUY_SETUPS
        elif execution_bias is AttentionBias.SELL_ONLY:
            status = OpportunityExecutionStatus.SEARCH_SELL_SETUPS
        else:
            status = OpportunityExecutionStatus.WAIT

        next_improvement = (
            missing[0]
            if missing
            else conflicts[0]
            if conflicts
            else "Wait for trader-owned entry, stop, target, and execution decisions."
        )
        reasoning = (
            f"{status.value}: quality {quality}/100; "
            f"{len(support)} supporting, {len(conflicts)} contradicting, {len(missing)} missing."
        )
        decision = TradingDecision(
            opportunity_id=observation.opportunity_id,
            biases=observation.horizon_biases,
            trade_quality=quality,
            execution_status=status,
            reasoning=reasoning,
            supporting_factors=tuple(support),
            contradicting_factors=tuple(conflicts),
            missing_evidence=tuple(missing),
            next_improvement=next_improvement,
            last_update=evaluated_at,
            policy_version=self._policy.version,
            contract_version=self._policy.contract_version,
        )
        try:
            self._logger.record(observation, decision)
            self._repository.append(observation, decision)
        except Exception as error:
            raise DecisionEvaluationError(
                f"trading decision audit failed; opportunity={observation.opportunity_id}; "
                f"status={decision.execution_status.value}"
            ) from error
        return decision
