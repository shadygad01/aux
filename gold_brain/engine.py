"""Deprecated engine path retained while consumers migrate to application ports."""

import logging
import sys
from datetime import UTC, datetime

from packages.application import DecisionEngine as ApplicationDecisionEngine
from packages.domain import Decision, DecisionPolicy, MarketObservation
from packages.infrastructure import JsonDecisionLogger


class DecisionEngine:
    """Compatibility adapter for the pre-constitution constructor and `now` argument."""

    def __init__(self, policy: DecisionPolicy | None = None) -> None:
        logger = logging.getLogger("gold_brain.compatibility.decisions")
        if not logger.handlers:
            handler = logging.StreamHandler(sys.stderr)
            handler.setFormatter(logging.Formatter("%(message)s"))
            logger.addHandler(handler)
        logger.setLevel(logging.INFO)
        logger.propagate = False
        self._engine = ApplicationDecisionEngine(
            policy or DecisionPolicy(), JsonDecisionLogger(logger)
        )

    def evaluate(self, observation: MarketObservation, now: datetime | None = None) -> Decision:
        return self._engine.evaluate(observation, now or datetime.now(UTC))


__all__ = ["DecisionEngine", "DecisionPolicy"]
