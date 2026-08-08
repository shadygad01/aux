# Publish Pipeline Composition Root

Owner: the production artifact-generation pipeline (`publish/generate_artifacts.py`), the
repository's real, CI-scheduled production entry point (see `docs/PHASE_0_MIGRATION_READINESS.md`
§A and §N). This document is a short pointer; `publish/composition.py`'s own module docstring is
the authoritative, detailed statement of scope.

## Target shape

```text
Production Entry Point            publish/generate_artifacts.py
        |                         (unchanged; still owns the GENERATORS registry
        v                          and artifact-writing loop)
Canonical Composition Root        publish/composition.py
        |                         (construction only: policy, engines, collectors,
        v                          logger — no business logic, no sequencing)
Application Services              packages/application/*Engine, build_market_thesis,
        |                          derive_trade_quality
        v
Domain / Infrastructure           packages/domain/*, packages/infrastructure/*
        |
        v
Persistence / External Systems    docs/artifacts/*.json (committed output),
                                   Yahoo Finance / gold-api.com (live collectors)
```

## What the composition root owns

Construction of every dependency the publish generators share:

- `configure_publish_logger()` — the shared `gold_brain.publish` logger.
- `build_decision_policy()` — the one production `DecisionPolicy`.
- `build_decision_engine(policy, logger)` — a `DecisionEngine` wired to a given policy/logger.
- `build_live_market_collector()` — the live XAUUSD collector.
- `build_macro_collector()` — the macro-context collector.
- `build_execution_readiness_engine()` — stateless.
- `build_multi_timeframe_engine()` — stateless.
- `build_opportunity_identity_engine()` — stateful; each call returns a **fresh** instance. State
  restoration from the previous run's committed artifact stays in
  `publish/generators/opportunity_identity.py`, not here — that is generator-specific execution
  logic tied to one artifact's on-disk format, not generic construction.

## What it deliberately does not own

- Any business decision, evaluation, or data-flow sequencing — that stays in each generator.
- Any capability under `capabilities/` — none has a production consumer today (see
  `docs/PHASE_0_MIGRATION_READINESS.md` §B). Wiring one in has no basis until the migration that
  gives it a real caller.
- `TradingOpportunityEngine` — reachable only from `apps/trading_cli`, which no CI workflow
  schedules; not part of the production graph this root represents.
- The 14 other orphaned `packages/application` classes (`EvidenceDecisionEngine`,
  `InstitutionalReasoningEngine`, `LearningEngine`, `DecisionMemory`, `InstitutionalKnowledgeBase`,
  `ConstitutionalGovernance`, `InstitutionalQualityGate`, `ResearchGovernance`, `SelfCritic`,
  `PatternDiscovery`, `InstitutionalComprehensionGate`, `InstitutionalMemory`, `TrustAssurance`,
  `CurrentMarketStateAssembly`, `MarketRegimeIdentification`).

## Consumers

`publish/generators/{decision,execution_readiness,market_story,market_thesis,multi_timeframe,
opportunity_identity,macro_assessment,macro_context,macro_evidence,policy}.py`. Not yet consumed by
`apps/decision_cli` or `apps/trading_cli` — those remain separate, unscheduled composition roots
(see `docs/PHASE_0_MIGRATION_READINESS.md` §E for the case for eventually consolidating them, and
why that was not done in the same change that introduced this module).

## Configuration

There is none to load or validate. Every constructed value is the exact literal default the
generators already hardcoded before this module existed (e.g., `MacroCollector(timeout_seconds=2)`).
No environment variable, config file, or secret exists anywhere in this pipeline. If one is
introduced later, it belongs here, and must fail explicitly on a missing required value rather than
substitute a fabricated default — consistent with the fix already made to
`MarketThesis.setup_quality_score` (see `docs/PHASE_0_MIGRATION_READINESS.md` §L).
