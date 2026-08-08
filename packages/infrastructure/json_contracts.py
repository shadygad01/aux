"""Versioned JSON adapters at the infrastructure boundary."""

from __future__ import annotations

from datetime import datetime
from typing import TypeAlias

from packages.domain import (
    DealingRange,
    Decision,
    LiquidityEvent,
    LiquiditySide,
    MarketObservation,
    MarketStructure,
    StructureBias,
)

from .errors import ContractValidationError

JsonScalar: TypeAlias = str | int | float | bool | None
JsonValue: TypeAlias = JsonScalar | list["JsonValue"] | dict[str, "JsonValue"]
JsonObject: TypeAlias = dict[str, JsonValue]

OBSERVATION_CONTRACT_VERSION = "1.0.0"


def _object(value: JsonValue | object, path: str) -> JsonObject:
    if not isinstance(value, dict) or not all(isinstance(key, str) for key in value):
        raise ContractValidationError(f"expected JSON object; path={path}")
    return {str(key): item for key, item in value.items()}


def _string(value: JsonValue | object, path: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ContractValidationError(f"expected non-empty string; path={path}")
    return value


def _number(value: JsonValue | object, path: str) -> float:
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise ContractValidationError(f"expected number; path={path}")
    return float(value)


def _boolean(value: JsonValue | object, path: str) -> bool:
    if not isinstance(value, bool):
        raise ContractValidationError(f"expected boolean; path={path}")
    return value


def _required(payload: JsonObject, key: str, path: str) -> JsonValue:
    if key not in payload:
        raise ContractValidationError(f"missing required field; path={path}.{key}")
    return payload[key]


def observation_from_json(payload_value: object) -> MarketObservation:
    payload = _object(payload_value, "$")
    contract_version = _string(_required(payload, "contract_version", "$"), "$.contract_version")
    if contract_version != OBSERVATION_CONTRACT_VERSION:
        raise ContractValidationError(
            f"unsupported observation contract; received={contract_version}; "
            f"supported={OBSERVATION_CONTRACT_VERSION}"
        )

    structure_value = payload.get("structure")
    structure = None
    if structure_value is not None:
        structure_payload = _object(structure_value, "$.structure")
        try:
            structure = MarketStructure(
                bias=StructureBias(
                    _string(_required(structure_payload, "bias", "$.structure"), "$.structure.bias")
                ),
                break_of_structure=_boolean(
                    _required(structure_payload, "break_of_structure", "$.structure"),
                    "$.structure.break_of_structure",
                ),
                change_of_character=_boolean(
                    structure_payload.get("change_of_character", False),
                    "$.structure.change_of_character",
                ),
            )
        except ValueError as error:
            raise ContractValidationError(
                f"invalid market structure; path=$.structure; error={error}"
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

    liquidity_value = payload.get("liquidity", [])
    if not isinstance(liquidity_value, list):
        raise ContractValidationError("expected array; path=$.liquidity")
    liquidity: list[LiquidityEvent] = []
    for index, event_value in enumerate(liquidity_value):
        event_path = f"$.liquidity[{index}]"
        event = _object(event_value, event_path)
        try:
            liquidity.append(
                LiquidityEvent(
                    side=LiquiditySide(
                        _string(_required(event, "side", event_path), f"{event_path}.side")
                    ),
                    swept=_boolean(_required(event, "swept", event_path), f"{event_path}.swept"),
                    displacement_confirmed=_boolean(
                        _required(event, "displacement_confirmed", event_path),
                        f"{event_path}.displacement_confirmed",
                    ),
                )
            )
        except ValueError as error:
            raise ContractValidationError(
                f"invalid liquidity event; path={event_path}; error={error}"
            ) from error

    macd_raw = payload.get("macd_value")
    macd_value = _number(macd_raw, "$.macd_value") if macd_raw is not None else None

    observed_at_text = _string(_required(payload, "observed_at", "$"), "$.observed_at")
    try:
        observed_at = datetime.fromisoformat(observed_at_text.replace("Z", "+00:00"))
        return MarketObservation(
            symbol=_string(_required(payload, "symbol", "$"), "$.symbol").upper(),
            timeframe=_string(_required(payload, "timeframe", "$"), "$.timeframe").upper(),
            observed_at=observed_at,
            structure=structure,
            dealing_range=dealing_range,
            liquidity=tuple(liquidity),
            source=_string(_required(payload, "source", "$"), "$.source"),
            macd_value=macd_value,
        )
    except ValueError as error:
        raise ContractValidationError(f"invalid observation; path=$; error={error}") from error


def decision_to_json(decision: Decision) -> JsonObject:
    meaning = (
        "Search for a high-quality setup"
        if decision.verdict.value != "WAIT"
        else "Do not search for a setup yet"
    )
    return {
        "contract_version": decision.contract_version,
        "verdict": decision.verdict.value,
        "meaning": meaning,
        "confidence": decision.confidence.value,
        "score": decision.score,
        "evaluated_at": decision.evaluated_at.isoformat(),
        "observation_time": decision.observation_time.isoformat(),
        "reasons": list(decision.reasons),
        "conflicts": list(decision.conflicts),
        "missing_evidence": list(decision.missing_evidence),
        "policy_version": decision.policy_version,
        "disclaimer": decision.disclaimer,
    }
