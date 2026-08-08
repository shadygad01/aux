# Institutional Implementation Roadmap

**Scope note:** this roadmap governs the `capabilities/*` institutional governance framework
(ports, adapters, contracts under `capabilities/`) -- a separate architecture with no production
consumer today (see `publish/composition.py`'s docstring). It does not describe, and was never
updated to describe, the live canonical trading pipeline (`LiveMarketCollector` ->
`DecisionEngine` -> `ExecutionReadinessEngine` -> `MultiTimeframeEngine` ->
`OpportunityIdentityEngine` -> `publish/generate_artifacts.py`), which has continued active
development throughout this freeze and is deployed and running independently of this track. Read
"frozen"/"feature development prohibited" below as scoped to the `capabilities/*` governance
track specifically.

Status: **IMPLEMENTATION FROZEN** (for the `capabilities/*` track) until Governance Consolidation
exits its institutional gate.

## Phase 0 — Governance consolidation and readiness restructuring (current)

1. Establish canonical concept ownership and ADR history.
2. Classify every non-canonical representation as projection, view, DTO, snapshot, audit record,
   compatibility adapter, or removal candidate.
3. Consolidate quality reviews, lineage, health metrics, and technical debt.
4. Remove stale ownership claims and ambiguous terminology.
5. Complete an external-auditor review. Feature development remains prohibited.
6. Track readiness per capability, retain append-only history, and derive project readiness from
   required capability scores.

Exit evidence: all ten Institutional Quality Gate reviews approved, no P0 ownership ambiguity,
architecture/docs/tests synchronized, and every retained parallel representation has a documented
derivation from its canonical object.

## Phase 1 — Canonical model migration

Create no new trading behavior. Migrate Market Thesis, Trade Quality, Research Finding, lineage,
and presentation projections according to ADRs. Remove or isolate parallel decision paths behind
Compatibility Adapters. Prove output equivalence before deletion.

## Phase 2 — Durable institutional controls

Replace in-memory governance, review, research, pattern, critique, and health records with durable,
hash-bound stores. Add restore tests, identity verification, and backlog monitoring.

## Phase 3 — Research baseline

Measure abstention, calibration, explanation completeness, source quality, regime coverage, and
decision-quality trends. No hypothesis may enter production without Governance Level 2 evidence.

## Explicitly deferred

Live trading logic, prediction, automated execution, new scoring, model optimization, UI expansion,
and unvalidated data integrations.
