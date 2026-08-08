"""Generate opportunity_identity.json — publishes canonical Opportunity Identity artifact."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from packages.application import build_market_thesis, derive_trade_quality
from packages.domain import DecisionVerdict, OpportunityIdentity
from publish.composition import (
    build_decision_engine,
    build_decision_policy,
    build_execution_readiness_engine,
    build_live_market_collector,
    build_macro_collector,
    build_opportunity_identity_engine,
    configure_publish_logger,
)

from .envelope import build_envelope

GENERATOR = "publish.generators.opportunity_identity"
SCHEMA_VERSION = "1.0.0"

ARCHIVE_GENERATOR = "publish.generators.opportunity_identity.archive"
ARCHIVE_SCHEMA_VERSION = "1.0.0"
ARCHIVE_MAX_ENTRIES = 1000
ARCHIVE_STATEMENT = (
    "Opportunity Archive is the durable, append-only record of every real BUY/SELL "
    "trading opportunity that has been tracked and later archived or invalidated — "
    "kept for search and future learning. WAIT is not a trading opportunity and is "
    "never recorded here, independent of the current/previous opportunity snapshot."
)
# WAIT is "no setup" (score forced to 0, see DecisionEngine's fail-closed gates) --
# it is not a trading opportunity, so it must never be written to this durable log.
_ARCHIVABLE_VERDICTS = frozenset({DecisionVerdict.BUY, DecisionVerdict.SELL})


def _is_archivable(entry_verdict: object) -> bool:
    try:
        return DecisionVerdict(str(entry_verdict)) in _ARCHIVABLE_VERDICTS
    except ValueError:
        return False


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
    if not isinstance(entries, list):
        return []
    # Drops any WAIT entries written before this filter existed -- the next
    # write naturally cleans up the historical noise instead of leaving it
    # committed indefinitely.
    return [e for e in entries if isinstance(e, dict) and _is_archivable(e.get("verdict"))]


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
    prev_is_archivable = prev_opp is not None and prev_opp.verdict in _ARCHIVABLE_VERDICTS
    if is_new_archival and prev_is_archivable:
        assert prev_opp is not None
        entries.append(prev_opp.to_dict())
        entries = entries[-ARCHIVE_MAX_ENTRIES:]
    elif not entries and prev_is_archivable:
        # First time the archive is created but a previous opportunity is
        # already known (e.g. from before this log existed) — seed it so
        # that history isn't silently lost.
        assert prev_opp is not None
        entries.append(prev_opp.to_dict())

    _write_archive(archive_path, entries)


def generate(output_path: Path) -> None:
    """Generate canonical opportunity_identity.json artifact using real-time dynamic market data."""
    logger = configure_publish_logger()

    collector = build_live_market_collector()
    obs, _ = collector.fetch_live_observation()
    # Captured after the fetch — evaluating against a timestamp taken before
    # a slow network call could make obs.observed_at land after it, wrongly
    # tripping the engine's "observation timestamp is in the future" gate.
    now = datetime.now(UTC)

    policy = build_decision_policy()
    decision = build_decision_engine(policy, logger).evaluate(obs, now)
    trade_quality = derive_trade_quality(obs, decision, policy)

    macro_collector = build_macro_collector()
    macro_ctx = macro_collector.acquire_macro_context(now)
    macro_assessment = macro_collector.evaluate_macro_assessment(macro_ctx, now)

    readiness = build_execution_readiness_engine().evaluate(
        obs, decision.verdict, trade_quality.score, macro_assessment, now
    )

    thesis = build_market_thesis(
        thesis_id=f"THESIS-{now.strftime('%Y%m%d')}-01",
        observation=obs,
        decision=decision,
        trade_quality=trade_quality,
        execution_readiness=readiness,
        macro_score=macro_assessment.macro_score,
    )

    engine_opp = build_opportunity_identity_engine()
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
