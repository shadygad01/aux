"""Generate decision.json — runs the DecisionEngine on a live-fetched market observation."""

from __future__ import annotations

import json
import logging
import sys
from datetime import UTC, datetime
from pathlib import Path

from packages.application import DecisionEngine
from packages.domain import DecisionPolicy
from packages.infrastructure import JsonDecisionLogger, decision_to_json
from packages.infrastructure.live_collector import LiveMarketCollector

from .envelope import build_envelope

GENERATOR = "publish.generators.decision"
SCHEMA_VERSION = "1.0.0"


def generate(output_path: Path) -> None:
    """Run DecisionEngine on a live-fetched XAUUSD observation and write decision.json."""
    logging.basicConfig(level=logging.WARNING, stream=sys.stderr)
    logger = logging.getLogger("gold_brain.publish")

    collector = LiveMarketCollector()
    observation, observation_source = collector.fetch_live_observation()

    engine = DecisionEngine(DecisionPolicy(), JsonDecisionLogger(logger))
    evaluated_at = datetime.now(UTC)
    decision = engine.evaluate(observation, evaluated_at)

    payload = {
        "label": "Live Evaluation — XAUUSD",
        "observation_source": observation_source,
        "current_price": (
            observation.dealing_range.current_price if observation.dealing_range else None
        ),
        "decision": decision_to_json(decision),
    }

    artifact = build_envelope(GENERATOR, SCHEMA_VERSION, payload)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(artifact, indent=2), encoding="utf-8")
    print(f"  [OK] {output_path.name}")
