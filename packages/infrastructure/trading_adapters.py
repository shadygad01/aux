"""JSON, structured logging, and append-only storage for trading evaluations."""

import json
import logging
from pathlib import Path

from packages.domain import (
    OpportunityTradeOutcome,
    OutcomeClassification,
    TradingDecision,
    TradingObservation,
)

from .json_contracts import JsonObject


def trading_decision_to_json(decision: TradingDecision) -> JsonObject:
    return {
        "contract_version": decision.contract_version,
        "opportunity_id": decision.opportunity_id,
        "bias": {
            item.horizon.value: {"value": item.bias.value, "reasoning": item.reasoning}
            for item in decision.biases
        },
        "trade_quality": decision.trade_quality,
        "execution_status": decision.execution_status.value,
        "reasoning": decision.reasoning,
        "supporting_factors": list(decision.supporting_factors),
        "contradicting_factors": list(decision.contradicting_factors),
        "missing_evidence": list(decision.missing_evidence),
        "next_improvement": decision.next_improvement,
        "last_update": decision.last_update.isoformat(),
        "policy_version": decision.policy_version,
    }


def trading_observation_to_json(observation: TradingObservation) -> JsonObject:
    macro: JsonObject | None = None
    if observation.macro is not None:
        macro = {
            "bias": observation.macro.bias.value,
            "reasoning": observation.macro.reasoning,
            "supporting_factors": list(observation.macro.supporting_factors),
            "contradicting_factors": list(observation.macro.contradicting_factors),
            "confidence": observation.macro.confidence,
        }
    dealing_range: JsonObject | None = None
    if observation.dealing_range is not None:
        dealing_range = {
            "low": observation.dealing_range.low,
            "high": observation.dealing_range.high,
            "current_price": observation.dealing_range.current_price,
        }
    momentum: JsonObject | None = None
    if observation.momentum is not None:
        momentum = {
            "macd_value": observation.momentum.macd_value,
            "histogram": observation.momentum.histogram,
            "slope": observation.momentum.slope,
            "crossover_confirmed": observation.momentum.crossover_confirmed,
        }
    smc: JsonObject | None = None
    if observation.smc is not None:
        liquidity: JsonObject | None = None
        if observation.smc.liquidity_event is not None:
            liquidity = {
                "side": observation.smc.liquidity_event.side.value,
                "swept": observation.smc.liquidity_event.swept,
                "displacement_confirmed": (observation.smc.liquidity_event.displacement_confirmed),
            }
        smc = {
            "liquidity_event": liquidity,
            "reversal_candle_confirmed": observation.smc.reversal_candle_confirmed,
            "change_of_character": observation.smc.change_of_character,
            "order_block": observation.smc.order_block,
            "fair_value_gap": observation.smc.fair_value_gap,
        }
    return {
        "opportunity_id": observation.opportunity_id,
        "symbol": observation.symbol,
        "execution_horizon": observation.execution_horizon.value,
        "observed_at": observation.observed_at.isoformat(),
        "source": observation.source,
        "horizon_biases": [
            {
                "horizon": item.horizon.value,
                "bias": item.bias.value,
                "reasoning": item.reasoning,
            }
            for item in observation.horizon_biases
        ],
        "nearby_liquidity_levels": list(observation.nearby_liquidity_levels),
        "macro": macro,
        "dealing_range": dealing_range,
        "momentum": momentum,
        "smc": smc,
        "news": [
            {
                "effect": item.effect.value,
                "why": item.why,
                "expected_impact": item.expected_impact,
                "expected_until": item.expected_until.isoformat(),
                "confidence": item.confidence,
            }
            for item in observation.news
        ],
    }


class JsonTradingDecisionLogger:
    def __init__(self, logger: logging.Logger) -> None:
        self._logger = logger

    def record(self, observation: TradingObservation, decision: TradingDecision) -> None:
        event: JsonObject = {
            "event": "trading_opportunity_evaluated",
            "observation": trading_observation_to_json(observation),
            "decision": trading_decision_to_json(decision),
        }
        self._logger.info(json.dumps(event, separators=(",", ":")))


class JsonLinesOpportunityRepository:
    """Append-only research record; one complete evaluation per line."""

    def __init__(self, path: Path) -> None:
        self._path = path

    def append(self, observation: TradingObservation, decision: TradingDecision) -> None:
        record: JsonObject = {
            "record_type": "evaluation",
            "observation": trading_observation_to_json(observation),
            "decision": trading_decision_to_json(decision),
            "outcome": OutcomeClassification.PENDING.value,
        }
        self._path.parent.mkdir(parents=True, exist_ok=True)
        with self._path.open("a", encoding="utf-8", newline="\n") as stream:
            stream.write(json.dumps(record, separators=(",", ":")))
            stream.write("\n")

    def append_outcome(self, outcome: OpportunityTradeOutcome) -> None:
        record: JsonObject = {
            "record_type": "outcome",
            "opportunity_id": outcome.opportunity_id,
            "classification": outcome.classification.value,
            "recorded_at": outcome.recorded_at.isoformat(),
            "evidence": outcome.evidence,
        }
        self._path.parent.mkdir(parents=True, exist_ok=True)
        with self._path.open("a", encoding="utf-8", newline="\n") as stream:
            stream.write(json.dumps(record, separators=(",", ":")))
            stream.write("\n")
