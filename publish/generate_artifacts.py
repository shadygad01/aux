"""Artifact orchestration entry point -- run this script to regenerate all published artifacts.

Usage (from repo root):
    python publish/generate_artifacts.py

GitHub Actions runs this automatically on every push to main.
"""

from __future__ import annotations

import json
import sys
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

# Ensure repo root is on sys.path so package imports work
REPO_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(REPO_ROOT))

from publish.generators import (  # noqa: E402
    context,
    decision,
    health,
    hypotheses,
    market_story,
    market_thesis,
    policy,
    readiness,
    technical_debt,
)

ARTIFACTS_DIR = REPO_ROOT / "docs" / "artifacts"

GENERATORS: list[tuple[str, Callable[[Path], None]]] = [
    ("context.json", context.generate),
    ("market_story.json", market_story.generate),
    ("market_thesis.json", market_thesis.generate),
    ("decision.json", decision.generate),
    ("policy.json", policy.generate),
    ("capability_readiness.json", readiness.generate),
    ("technical_debt.json", technical_debt.generate),
    ("hypothesis_register.json", hypotheses.generate),
]


def run() -> int:
    print(f"\nGold Brain — artifact generation ({datetime.now(UTC).isoformat()})")
    print(f"Output directory: {ARTIFACTS_DIR}\n")

    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    generated: list[dict[str, Any]] = []
    failed: list[str] = []

    for filename, generator_fn in GENERATORS:
        output_path = ARTIFACTS_DIR / filename
        try:
            generator_fn(output_path)
            generated.append({"file": filename, "status": "ok"})
            print(f"  [OK] {filename}")
        except Exception as exc:
            print(f"  [FAIL] {filename}: {exc}", file=sys.stderr)
            failed.append(filename)

    # health.json depends on readiness + debt, so run after them
    health_path = ARTIFACTS_DIR / "institutional_health.json"
    try:
        health.generate(health_path, ARTIFACTS_DIR)
        generated.append({"file": "institutional_health.json", "status": "ok"})
    except Exception as exc:
        print(f"  [FAIL] institutional_health.json: {exc}", file=sys.stderr)
        failed.append("institutional_health.json")

    # Write the manifest last
    manifest = {
        "artifact_version": "1.0.0",
        "generated_at": datetime.now(UTC).isoformat(),
        "artifacts": [entry["file"] for entry in generated if entry["status"] == "ok"],
    }
    manifest_path = ARTIFACTS_DIR / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"  [OK] manifest.json ({len(manifest['artifacts'])} artifacts)\n")

    if failed:
        print(f"FAILED: {failed}", file=sys.stderr)
        return 1

    print("All artifacts generated successfully.")
    return 0


if __name__ == "__main__":
    sys.exit(run())
