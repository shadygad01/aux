"""Generate decision.json — runs the DecisionEngine on the bullish example observation."""

from __future__ import annotations

import json
import logging
import sys
from datetime import UTC
from pathlib import Path

from packages.application import DecisionEngine
from packages.domain import DecisionPolicy
from packages.infrastructure import JsonDecisionLogger, decision_to_json, observation_from_json

from .envelope import build_envelope

GENERATOR = "publish.generators.decision"
SCHEMA_VERSION = "1.0.0"
EXAMPLE_PATH = Path(__file__).parent.parent.parent / "examples" / "bullish_evaluation.json"


def generate(output_path: Path) -> None:
    """Run DecisionEngine on the bullish example and write decision.json."""
    logging.basicConfig(level=logging.WARNING, stream=sys.stderr)
    logger = logging.getLogger("gold_brain.publish")

    raw: object = json.loads(EXAMPLE_PATH.read_text(encoding="utf-8"))
    observation = observation_from_json(raw)

    engine = DecisionEngine(DecisionPolicy(), JsonDecisionLogger(logger))
    # Evaluate at the observation timestamp so the decision is always valid
    evaluated_at = observation.observed_at.replace(tzinfo=UTC)
    decision = engine.evaluate(observation, evaluated_at)

    payload = {
        "label": "Example Evaluation — Bullish Observation",
        "observation_source": str(EXAMPLE_PATH.relative_to(EXAMPLE_PATH.parent.parent)),
        "decision": decision_to_json(decision),
    }

    artifact = build_envelope(GENERATOR, SCHEMA_VERSION, payload)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(artifact, indent=2), encoding="utf-8")
    print(f"  [OK] {output_path.name}")
