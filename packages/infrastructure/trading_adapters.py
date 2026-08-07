"""JSON, structured logging, and append-only storage for trading evaluations."""

import json
import logging
from datetime import datetime
from pathlib import Path

from packages.domain import (
    AttentionBias,
    DealingRange,
    HorizonBias,
    LiquidityEvent,
    LiquiditySide,
    MomentumAssessment,
    NewsAssessment,
    NewsEffect,
    OpportunityTradeOutcome,
    OutcomeClassification,
    SmcAssessment,
    TradingDecision,
    TradingHorizon,
    TradingMacroAssessment,
    TradingObservation,
)

from .errors import ContractValidationError
from .json_contracts import JsonObject, JsonValue, _boolean, _number, _object, _required, _string

TRADING_OBSERVATION_CONTRACT_VERSION = "1.0.0"


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


def trading_observation_from_json(payload_value: object) -> TradingObservation:
    payload = _object(payload_value, "$")
    contract_version = _string(_required(payload, "contract_version", "$"), "$.contract_version")
    if contract_version != TRADING_OBSERVATION_CONTRACT_VERSION:
        raise ContractValidationError(
            f"unsupported trading observation contract; received={contract_version}; "
            f"supported={TRADING_OBSERVATION_CONTRACT_VERSION}"
        )

    macro_value = payload.get("macro")
    macro = None
    if macro_value is not None:
        macro_payload = _object(macro_value, "$.macro")
        try:
            macro = TradingMacroAssessment(
                bias=AttentionBias(
                    _string(_required(macro_payload, "bias", "$.macro"), "$.macro.bias")
                ),
                reasoning=_string(
                    _required(macro_payload, "reasoning", "$.macro"), "$.macro.reasoning"
                ),
                supporting_factors=_string_tuple(
                    macro_payload.get("supporting_factors", []), "$.macro.supporting_factors"
                ),
                contradicting_factors=_string_tuple(
                    macro_payload.get("contradicting_factors", []),
                    "$.macro.contradicting_factors",
                ),
                confidence=_number(
                    _required(macro_payload, "confidence", "$.macro"), "$.macro.confidence"
                ),
            )
        except ValueError as error:
            raise ContractValidationError(
                f"invalid macro assessment; path=$.macro; error={error}"
            ) from error

    horizon_biases_value = payload.get("horizon_biases", [])
    if not isinstance(horizon_biases_value, list):
        raise ContractValidationError("expected array; path=$.horizon_biases")
    horizon_biases: list[HorizonBias] = []
    for index, item_value in enumerate(horizon_biases_value):
        item_path = f"$.horizon_biases[{index}]"
        item = _object(item_value, item_path)
        try:
            horizon_biases.append(
                HorizonBias(
                    horizon=TradingHorizon(
                        _string(_required(item, "horizon", item_path), f"{item_path}.horizon")
                    ),
                    bias=AttentionBias(
                        _string(_required(item, "bias", item_path), f"{item_path}.bias")
                    ),
                    reasoning=_string(
                        _required(item, "reasoning", item_path), f"{item_path}.reasoning"
                    ),
                )
            )
        except ValueError as error:
            raise ContractValidationError(
                f"invalid horizon bias; path={item_path}; error={error}"
            ) from error

    range_value = payload.get("dealing_range")
    dealing_range = None
    if range_value is not None:
        range_payload = _object(range_value, "$.dealing_range")
        try:
            dealing_range = DealingRange(
                low=_number(
                    _required(range_payload, "low", "$.dealing_range"), "$.dealing_range.low"
                ),
                high=_number(
                    _required(range_payload, "high", "$.dealing_range"), "$.dealing_range.high"
                ),
                current_price=_number(
                    _required(range_payload, "current_price", "$.dealing_range"),
                    "$.dealing_range.current_price",
                ),
            )
        except ValueError as error:
            raise ContractValidationError(
                f"invalid dealing range; path=$.dealing_range; error={error}"
            ) from error

    nearby_liquidity_levels = _string_tuple(
        payload.get("nearby_liquidity_levels", []), "$.nearby_liquidity_levels"
    )

    momentum_value = payload.get("momentum")
    momentum = None
    if momentum_value is not None:
        momentum_payload = _object(momentum_value, "$.momentum")
        try:
            momentum = MomentumAssessment(
                macd_value=_number(
                    _required(momentum_payload, "macd_value", "$.momentum"),
                    "$.momentum.macd_value",
                ),
                histogram=_optional_number(
                    momentum_payload.get("histogram"), "$.momentum.histogram"
                ),
                slope=_optional_number(momentum_payload.get("slope"), "$.momentum.slope"),
                crossover_confirmed=_boolean(
                    momentum_payload.get("crossover_confirmed", False),
                    "$.momentum.crossover_confirmed",
                ),
            )
        except ValueError as error:
            raise ContractValidationError(
                f"invalid momentum assessment; path=$.momentum; error={error}"
            ) from error

    smc_value = payload.get("smc")
    smc = None
    if smc_value is not None:
        smc_payload = _object(smc_value, "$.smc")
        try:
            liquidity_event_value = smc_payload.get("liquidity_event")
            liquidity_event = None
            if liquidity_event_value is not None:
                liquidity_payload = _object(liquidity_event_value, "$.smc.liquidity_event")
                liquidity_event = LiquidityEvent(
                    side=LiquiditySide(
                        _string(
                            _required(liquidity_payload, "side", "$.smc.liquidity_event"),
                            "$.smc.liquidity_event.side",
                        )
                    ),
                    swept=_boolean(
                        _required(liquidity_payload, "swept", "$.smc.liquidity_event"),
                        "$.smc.liquidity_event.swept",
                    ),
                    displacement_confirmed=_boolean(
                        _required(
                            liquidity_payload, "displacement_confirmed", "$.smc.liquidity_event"
                        ),
                        "$.smc.liquidity_event.displacement_confirmed",
                    ),
                )
            smc = SmcAssessment(
                liquidity_event=liquidity_event,
                reversal_candle_confirmed=_boolean(
                    _required(smc_payload, "reversal_candle_confirmed", "$.smc"),
                    "$.smc.reversal_candle_confirmed",
                ),
                change_of_character=_boolean(
                    smc_payload.get("change_of_character", False), "$.smc.change_of_character"
                ),
                order_block=_boolean(smc_payload.get("order_block", False), "$.smc.order_block"),
                fair_value_gap=_boolean(
                    smc_payload.get("fair_value_gap", False), "$.smc.fair_value_gap"
                ),
            )
        except ValueError as error:
            raise ContractValidationError(
                f"invalid smc assessment; path=$.smc; error={error}"
            ) from error

    news_value = payload.get("news", [])
    if not isinstance(news_value, list):
        raise ContractValidationError("expected array; path=$.news")
    news: list[NewsAssessment] = []
    for index, item_value in enumerate(news_value):
        item_path = f"$.news[{index}]"
        item = _object(item_value, item_path)
        try:
            expected_until_text = _string(
                _required(item, "expected_until", item_path), f"{item_path}.expected_until"
            )
            news.append(
                NewsAssessment(
                    effect=NewsEffect(
                        _string(_required(item, "effect", item_path), f"{item_path}.effect")
                    ),
                    why=_string(_required(item, "why", item_path), f"{item_path}.why"),
                    expected_impact=_string(
                        _required(item, "expected_impact", item_path),
                        f"{item_path}.expected_impact",
                    ),
                    expected_until=datetime.fromisoformat(
                        expected_until_text.replace("Z", "+00:00")
                    ),
                    confidence=_number(
                        _required(item, "confidence", item_path), f"{item_path}.confidence"
                    ),
                )
            )
        except ValueError as error:
            raise ContractValidationError(
                f"invalid news assessment; path={item_path}; error={error}"
            ) from error

    observed_at_text = _string(_required(payload, "observed_at", "$"), "$.observed_at")
    try:
        observed_at = datetime.fromisoformat(observed_at_text.replace("Z", "+00:00"))
        return TradingObservation(
            opportunity_id=_string(_required(payload, "opportunity_id", "$"), "$.opportunity_id"),
            symbol=_string(_required(payload, "symbol", "$"), "$.symbol").upper(),
            execution_horizon=TradingHorizon(
                _string(_required(payload, "execution_horizon", "$"), "$.execution_horizon")
            ),
            observed_at=observed_at,
            source=_string(_required(payload, "source", "$"), "$.source"),
            macro=macro,
            horizon_biases=tuple(horizon_biases),
            dealing_range=dealing_range,
            nearby_liquidity_levels=nearby_liquidity_levels,
            momentum=momentum,
            smc=smc,
            news=tuple(news),
        )
    except ValueError as error:
        raise ContractValidationError(
            f"invalid trading observation; path=$; error={error}"
        ) from error


def _string_tuple(value: JsonValue, path: str) -> tuple[str, ...]:
    if not isinstance(value, list):
        raise ContractValidationError(f"expected array; path={path}")
    return tuple(_string(item, f"{path}[{index}]") for index, item in enumerate(value))


def _optional_number(value: JsonValue | None, path: str) -> float | None:
    if value is None:
        return None
    return _number(value, path)


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
