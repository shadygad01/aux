"""Generate policy.json — serializes DecisionPolicy (all labeled hypotheses and weights)."""

from __future__ import annotations

import json
from pathlib import Path

from publish.composition import build_decision_policy

from .envelope import build_envelope

GENERATOR = "publish.generators.policy"
SCHEMA_VERSION = "1.0.0"


def generate(output_path: Path) -> None:
    """Serialize all DecisionPolicy fields and write policy.json."""
    policy = build_decision_policy()

    payload = {
        "version": policy.version,
        "output_contract_version": policy.output_contract_version,
        "supported_symbol": policy.supported_symbol,
        "maximum_age_hours": policy.maximum_age.total_seconds() / 3600,
        "equilibrium_band": policy.equilibrium_band,
        "attention_threshold": policy.attention_threshold,
        "weights": {
            "structure": policy.structure_weight,
            "location": policy.location_weight,
            "liquidity": policy.liquidity_weight,
        },
        "disclaimer": policy.disclaimer,
        "hypothesis_note": (
            "Every configurable weight is labelled as a hypothesis, not a validated fact. "
            "See docs/hypothesis-register.md for the full register."
        ),
    }

    artifact = build_envelope(GENERATOR, SCHEMA_VERSION, payload)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(artifact, indent=2), encoding="utf-8")
    print(f"  [OK] {output_path.name}")
