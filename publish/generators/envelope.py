"""Standard artifact envelope — every published JSON file shares this wrapper."""

from __future__ import annotations

import os
from datetime import UTC, datetime
from typing import Any


def build_envelope(
    generator: str,
    schema_version: str,
    payload: dict[str, Any],
) -> dict[str, Any]:
    """Wrap a capability payload with provenance metadata.

    Every artifact must contain:
      - artifact_version  : envelope format version
      - generated_at      : UTC ISO-8601 generation timestamp
      - commit            : git commit SHA (from GITHUB_SHA env var, or "local")
      - generator         : dotted module name of the generating capability
      - schema_version    : payload schema version
      - payload           : the capability-specific data object
    """
    commit = os.environ.get("GITHUB_SHA", "local")[:40] or "local"
    return {
        "artifact_version": "1.0.0",
        "generated_at": datetime.now(UTC).isoformat(),
        "commit": commit,
        "generator": generator,
        "schema_version": schema_version,
        "payload": payload,
    }
