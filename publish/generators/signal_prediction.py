"""Generate signal_prediction.json — publishes canonical Signal Prediction artifact."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from packages.application.signal_prediction_engine import SignalPredictionEngine
from packages.infrastructure.live_collector import LiveMarketCollector

from .envelope import build_envelope

GENERATOR = "publish.generators.signal_prediction"
SCHEMA_VERSION = "1.0.0"


def generate(output_path: Path) -> None:
    """Generate canonical signal_prediction.json artifact using dynamic market data."""
    now = datetime.now(UTC)
    collector = LiveMarketCollector()
    obs, _ = collector.fetch_live_observation()

    engine = SignalPredictionEngine()
    prediction = engine.predict_next_signal(obs, now)

    statement = (
        "Signal Prediction Engine forecasts expected setup opportunity emergence windows based on "
        "backtest session liquidity frequency (London/NY Open) and current market structure."
    )

    payload = {
        "statement": statement,
        "signal_prediction": prediction.to_dict(),
    }

    artifact = build_envelope(GENERATOR, SCHEMA_VERSION, payload)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(artifact, indent=2), encoding="utf-8")
    print(f"  [OK] {output_path.name}")
