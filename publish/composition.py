"""Canonical composition root for the production artifact-generation pipeline.

``publish/generate_artifacts.py`` is the repository's real, CI-scheduled
production entry point (``.github/workflows/publish.yml`` and
``deploy_interserver.yml`` both run it on every push to ``main``; see
``docs/PHASE_0_MIGRATION_READINESS.md``, Migration Order step 1). Its
generators each independently constructed the same handful of application-
and infrastructure-layer objects with identical arguments -- a fresh
``DecisionPolicy()``, a fresh ``DecisionEngine(policy, JsonDecisionLogger(logger))``,
a fresh ``LiveMarketCollector()`` or ``MacroCollector(timeout_seconds=2)`` -- in
up to nine different files. This module is the one place that owns *how*
those objects are built, so there is a single canonical construction path
instead of nine duplicated ones.

This module builds objects. It does not evaluate them, decide anything, hold
market/business state, or read any configuration a generator doesn't already
read today -- every value here is the exact literal default the generators
already used. Sequencing (what gets called, in what order, with what
already-computed inputs) stays in each generator, which alone knows what its
artifact needs; the composition root supplies dependencies, it does not
orchestrate their use.

Deliberately not wired here, and left untouched -- not yet wired, scheduled
for downstream migration (see ``docs/PHASE_0_MIGRATION_READINESS.md`` for the
full inventory and the migration order):

- ``TradingOpportunityEngine`` -- reachable only from ``apps/trading_cli``,
  which no CI workflow schedules; not part of the production graph this root
  represents.
- Every ``capabilities/*`` class and the remaining orphaned
  ``packages/application`` classes (``EvidenceDecisionEngine``,
  ``InstitutionalReasoningEngine``, ``LearningEngine``, ``DecisionMemory``,
  ``InstitutionalKnowledgeBase``, ``ConstitutionalGovernance``,
  ``InstitutionalQualityGate``, ``ResearchGovernance``, ``SelfCritic``,
  ``PatternDiscovery``, ``InstitutionalComprehensionGate``,
  ``InstitutionalMemory``, ``TrustAssurance``, ``CurrentMarketStateAssembly``,
  ``MarketRegimeIdentification``) -- none has a production consumer today;
  wiring any of them in has no basis until the migration that gives it a real
  caller.
"""

from __future__ import annotations

import logging
import sys

from packages.application import DecisionEngine
from packages.application.execution_readiness_engine import ExecutionReadinessEngine
from packages.application.multi_timeframe_engine import MultiTimeframeEngine
from packages.application.opportunity_identity_engine import OpportunityIdentityEngine
from packages.domain import DecisionPolicy
from packages.infrastructure import JsonDecisionLogger
from packages.infrastructure.live_collector import LiveMarketCollector
from packages.infrastructure.macro_collectors import MacroCollector

PUBLISH_LOGGER_NAME = "gold_brain.publish"
MACRO_COLLECTOR_TIMEOUT_SECONDS = 2


def configure_publish_logger() -> logging.Logger:
    """Return the shared publish-pipeline logger, audit records enabled.

    Every generator that logs decisions used to call ``logging.basicConfig``
    and ``logging.getLogger`` with identical arguments independently; this is
    the one place that does it now. ``logging.basicConfig`` is a no-op after
    its first effective call within a process -- unchanged stdlib behavior,
    and the same behavior ``generate_artifacts.py`` already had when each
    generator called it in turn.

    The root level stays ``WARNING`` (so third-party library logging remains
    quiet, unchanged from before), but ``gold_brain.publish`` itself is
    explicitly raised to ``INFO``. Without this, ``JsonDecisionLogger.record()``
    -- called by every ``DecisionEngine`` evaluation through this logger --
    calls ``logger.info(...)``, which the root's ``WARNING`` threshold
    silently discarded: the audit record was computed and handed to the
    logger correctly, but never reached stderr or anywhere else. Every real
    ``Decision``/``MarketThesis`` output was already correct and unaffected
    (`decision_to_json` serializes the domain object directly, independent of
    this logger) -- only the structured per-decision audit line was lost. See
    docs/adr/0007-engine-consolidation.md AQ-3 for the original finding.
    """
    logging.basicConfig(level=logging.WARNING, stream=sys.stderr)
    logger = logging.getLogger(PUBLISH_LOGGER_NAME)
    logger.setLevel(logging.INFO)
    return logger


def build_decision_policy() -> DecisionPolicy:
    """Construct the original, all-default-weights `DecisionPolicy`
    (structure/location/liquidity 0.40/0.30/0.30, threshold 0.75, every gate
    mandatory except break_of_structure).

    See `docs/hypothesis-register.md` for why every weight here is a
    labeled, unvalidated hypothesis rather than a tuned constant. As of
    2026-08-09 (H-026 unification, owner-directed), this is **not** the
    policy any live artifact generator uses anymore -- every H1 evaluation
    across the site uses `build_production_h1_policy()` below instead, so
    the dashboard's "Current Thesis" headline and the Multi-Timeframe
    cascade's H1 bias can never silently disagree with each other again
    (they used to: this policy fed decision.json/market_thesis.json/etc
    while the cascade used the other one, so the same H1 candle could
    produce two different displayed verdicts at once). This function is
    kept for tests, `backtest/` CLI comparisons, and as a documented,
    still-available baseline -- not deleted, just retired from production.
    """
    return DecisionPolicy()


def build_production_h1_policy() -> DecisionPolicy:
    """Construct the ONE H1 `DecisionPolicy` every live artifact generator
    uses (decision.json, market_thesis.json, execution_readiness.json,
    market_story.json, opportunity_identity.json, policy.json, and the
    Multi-Timeframe cascade's H1 role in multi_timeframe.json) -- a single
    source of truth so every H1-derived verdict shown anywhere on the
    dashboard is always the same verdict. Before 2026-08-09 this policy was
    used only inside the Multi-Timeframe cascade while every other
    generator used the separate, conservative `build_decision_policy()`
    above, which meant the same H1 candle could silently produce two
    different verdicts depending which artifact you looked at; H-026's
    unification retired that split.

    Weights/threshold/gate-mandatory flags are the "Active" configuration
    the owner validated via exhaustive walk-forward backtesting on 5 years
    of real M15 XAUUSD data (a train(2021-2023)/test(2024-2026) split, plus
    an independent 4-way expanding-window per-year check spanning all of
    2021-2026) -- see docs/hypothesis-register.md H-026 for the full
    methodology, results, and disclosed limits (spread/commission/slippage
    and manual, non-instant trade entry are not modeled).

    Liquidity-sweep dominates the score (weight 0.9); location contributes
    nothing (weight 0). Location and liquidity-sweep are both non-mandatory
    bonuses here (like break_of_structure always is) rather than gates --
    requiring them independently was tested and found to only remove valid
    signals, never add edge, when H1 is used purely as a direction source.
    MACD is disabled for the same reason. threshold=0.1 is deliberately low
    -- a confirmed sweep alone (0.9) clears it with margin.
    """
    return DecisionPolicy(
        version="v2-active-h1-cascade",
        attention_threshold=0.1,
        structure_weight=0.1,
        location_weight=0.0,
        liquidity_weight=0.9,
        location_mandatory=False,
        sweep_mandatory=False,
        macd_mode="off",
    )


def build_decision_engine(policy: DecisionPolicy, logger: logging.Logger) -> DecisionEngine:
    """Construct a `DecisionEngine` wired to the given policy and structured logger."""
    return DecisionEngine(policy, JsonDecisionLogger(logger))


def build_live_market_collector() -> LiveMarketCollector:
    """Construct the production live XAUUSD collector (Yahoo futures + gold-api.com spot)."""
    return LiveMarketCollector()


def build_macro_collector() -> MacroCollector:
    """Construct the production macro-context collector at its established timeout."""
    return MacroCollector(timeout_seconds=MACRO_COLLECTOR_TIMEOUT_SECONDS)


def build_execution_readiness_engine() -> ExecutionReadinessEngine:
    """Construct the (stateless) Execution Readiness engine."""
    return ExecutionReadinessEngine()


def build_multi_timeframe_engine() -> MultiTimeframeEngine:
    """Construct the (stateless) Multi-Timeframe cascading engine."""
    return MultiTimeframeEngine()


def build_opportunity_identity_engine() -> OpportunityIdentityEngine:
    """Construct a fresh Opportunity Identity engine.

    Stateful by design (tracks current/previous opportunity across calls),
    but every process run starts a new instance and immediately restores its
    state from the previous run's committed artifact -- see
    `publish/generators/opportunity_identity.py`'s `_load_engine_state`. That
    restore sequencing is generator-specific execution logic tied to one
    artifact's on-disk state, not generic construction, so it stays in the
    generator rather than moving here.
    """
    return OpportunityIdentityEngine()
