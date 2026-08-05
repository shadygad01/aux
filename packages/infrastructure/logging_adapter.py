"""Structured decision logging adapter."""

from __future__ import annotations

import json
import logging

from packages.domain import Decision, MarketObservation

from .json_contracts import decision_to_json


class JsonDecisionLogger:
    def __init__(self, logger: logging.Logger) -> None:
        self._logger = logger

    def record(self, observation: MarketObservation, decision: Decision) -> None:
        event = {
            "event": "decision_evaluated",
            "symbol": observation.symbol,
            "timeframe": observation.timeframe,
            "source": observation.source,
            "decision": decision_to_json(decision),
        }
        self._logger.info(json.dumps(event, separators=(",", ":")))
