"""Generate opportunity_identity.json — publishes canonical Opportunity Identity artifact."""

from __future__ import annotations

import json
import logging
import sys
from datetime import UTC, datetime
from pathlib import Path

from packages.application import DecisionEngine, build_market_thesis, derive_trade_quality
from packages.application.execution_readiness_engine import ExecutionReadinessEngine
from packages.application.opportunity_identity_engine import OpportunityIdentityEngine
from packages.domain import DecisionPolicy, OpportunityIdentity
from packages.infrastructure import JsonDecisionLogger
from packages.infrastructure.live_collector import LiveMarketCollector

from .envelope import build_envelope

GENERATOR = "publish.generators.opportunity_identity"
SCHEMA_VERSION = "1.0.0"

ARCHIVE_GENERATOR = "publish.generators.opportunity_identity.archive"
ARCHIVE_SCHEMA_VERSION = "1.0.0"
ARCHIVE_MAX_ENTRIES = 1000
ARCHIVE_STATEMENT = (
    "Opportunity Archive is the durable, append-only record of every opportunity "
    "that has been tracked and later archived or invalidated — kept for search, "
    "learning, and review, independent of the current/previous opportunity snapshot."
)


def _load_engine_state(
    output_path: Path,
) -> tuple[OpportunityIdentity | None, OpportunityIdentity | None, int, str | None]:
    """Reload the engine state persisted by the previous generation run.

    `output_path` is the same artifact file this generator wrote last time
    (it is committed to the repo), so it doubles as the engine's durable
    state store across the separate process invocations that CI runs.
    """
    if not output_path.exists():
        return None, None, 1, None
    try:
        raw = json.loads(output_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None, None, 1, None

    payload = raw.get("payload", {})
    curr_raw = payload.get("current_opportunity")
    prev_raw = payload.get("previous_opportunity")
    state_raw = payload.get("engine_state") or {}

    current = OpportunityIdentity.from_dict(curr_raw) if curr_raw else None
    previous = OpportunityIdentity.from_dict(prev_raw) if prev_raw else None
    counter = int(state_raw.get("counter", 1))
    last_sweep_signature = state_raw.get("last_sweep_signature")
    return current, previous, counter, last_sweep_signature


def _load_archive_entries(archive_path: Path) -> list[dict[str, object]]:
    if not archive_path.exists():
        return []
    try:
        raw = json.loads(archive_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    entries = raw.get("payload", {}).get("entries", [])
    return list(entries) if isinstance(entries, list) else []


def _write_archive(archive_path: Path, entries: list[dict[str, object]]) -> None:
    payload = {"statement": ARCHIVE_STATEMENT, "entries": entries}
    artifact = build_envelope(ARCHIVE_GENERATOR, ARCHIVE_SCHEMA_VERSION, payload)
    archive_path.parent.mkdir(parents=True, exist_ok=True)
    archive_path.write_text(json.dumps(artifact, indent=2), encoding="utf-8")


def _record_archive_entry(
    archive_path: Path,
    restored_previous: OpportunityIdentity | None,
    prev_opp: OpportunityIdentity | None,
) -> None:
    """Append a newly-archived opportunity to the durable search/review log.

    `current_opportunity`/`previous_opportunity` in opportunity_identity.json
    only ever hold the latest two — this log accumulates every opportunity
    that has ever been archived or invalidated, so past setups remain
    searchable and reviewable instead of being overwritten and lost.
    """
    entries = _load_archive_entries(archive_path)

    is_new_archival = prev_opp is not None and (
        restored_previous is None
        or restored_previous.opportunity_id != prev_opp.opportunity_id
        or restored_previous.last_updated_at != prev_opp.last_updated_at
    )
    if is_new_archival:
        assert prev_opp is not None
        entries.append(prev_opp.to_dict())
        entries = entries[-ARCHIVE_MAX_ENTRIES:]
    elif not entries and prev_opp is not None:
        # First time the archive is created but a previous opportunity is
        # already known (e.g. from before this log existed) — seed it so
        # that history isn't silently lost.
        entries.append(prev_opp.to_dict())

    _write_archive(archive_path, entries)


def generate(output_path: Path) -> None:
    """Generate canonical opportunity_identity.json artifact using real-time dynamic market data."""
    logging.basicConfig(level=logging.WARNING, stream=sys.stderr)
    logger = logging.getLogger("gold_brain.publish")

    collector = LiveMarketCollector()
    obs, _ = collector.fetch_live_observation()
    # Captured after the fetch — evaluating against a timestamp taken before
    # a slow network call could make obs.observed_at land after it, wrongly
    # tripping the engine's "observation timestamp is in the future" gate.
    now = datetime.now(UTC)

    policy = DecisionPolicy()
    decision = DecisionEngine(policy, JsonDecisionLogger(logger)).evaluate(obs, now)
    trade_quality = derive_trade_quality(obs, decision, policy)

    readiness = ExecutionReadinessEngine().evaluate(
        obs, decision.verdict, trade_quality.score, None, now
    )

    thesis = build_market_thesis(
        thesis_id=f"THESIS-{now.strftime('%Y%m%d')}-01",
        observation=obs,
        decision=decision,
        trade_quality=trade_quality,
        execution_readiness=readiness,
    )

    engine_opp = OpportunityIdentityEngine()
    restored_current, restored_previous, counter, last_sweep_signature = _load_engine_state(
        output_path
    )
    engine_opp.restore_state(restored_current, restored_previous, counter, last_sweep_signature)
    curr_opp, prev_opp = engine_opp.evaluate_opportunity(obs, thesis, readiness, now)

    statement = (
        "Opportunity Identity distinguishes between an aging setup and a new setup. "
        "Every opportunity receives a unique Opportunity ID constant throughout its lifetime."
    )

    payload = {
        "statement": statement,
        "current_opportunity": curr_opp.to_dict(),
        "previous_opportunity": prev_opp.to_dict() if prev_opp else None,
        "engine_state": engine_opp.snapshot_state(),
    }

    artifact = build_envelope(GENERATOR, SCHEMA_VERSION, payload)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(artifact, indent=2), encoding="utf-8")
    print(f"  [OK] {output_path.name}")

    archive_path = output_path.with_name("opportunity_archive.json")
    _record_archive_entry(archive_path, restored_previous, prev_opp)
    print(f"  [OK] {archive_path.name}")
