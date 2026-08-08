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
    """Return the shared publish-pipeline logger.

    Every generator that logs decisions used to call ``logging.basicConfig``
    and ``logging.getLogger`` with identical arguments independently; this is
    the one place that does it now. ``logging.basicConfig`` is a no-op after
    its first effective call within a process -- unchanged stdlib behavior,
    and the same behavior ``generate_artifacts.py`` already had when each
    generator called it in turn.
    """
    logging.basicConfig(level=logging.WARNING, stream=sys.stderr)
    return logging.getLogger(PUBLISH_LOGGER_NAME)


def build_decision_policy() -> DecisionPolicy:
    """Construct the one production `DecisionPolicy` (all-default weights and gates).

    See `docs/hypothesis-register.md` for why every weight here is a labeled,
    unvalidated hypothesis rather than a tuned constant.
    """
    return DecisionPolicy()


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
