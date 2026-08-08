# Governance Consolidation Sprint Report

## Architecture Entropy Report

See `architecture-entropy-report.md`. Primary entropy comes from parallel decision paths, ambiguous
model names, fragmented lineage, and transient institutional records.

## Concept Ownership Matrix

See `concept-ownership.md`. Ten capabilities remain the only public business owners. Market Thesis
is the sole canonical decision.

## Canonical Domain Map

`Fact → Evidence → Knowledge Object → Market Story → Reasoning → Market Thesis`

Market State, Market Regime, Bias, and Trade Quality are contextual/value objects. Decision Memory
stores audit versions; it is not another decision.

## Projection Map

Evidence Assessment, Reasoning Projection, Horizon Bias, Decision Audit Snapshot, Knowledge Answer,
Source Ranking, Regime Interpretation, Trust Manifest, and Comprehension Review are immutable
projections or audit records. See the full map in `concept-ownership.md`.

## Adapter Map

The `gold_brain` facade, v1 CLI, historical engine entry points, and superseded schemas are
Compatibility Adapters. They may not gain business logic.

## Deletion Plan

1. Route the CLI through Decision Presentation, then remove its parallel decision computation.
2. Migrate `OfficialDecision` to canonical `MarketThesis`; retire v1–v4 after consumer evidence.
3. Consolidate Trade Quality and remove duplicate calculators after equivalence/research review.
4. Convert or delete `Decision`, `TradingDecision`, and old Market State representations.
5. Remove business-owning `*Engine` entry points after capability parity tests.
6. Delete transient production adapters after durable stores pass restore tests.

No deletion is executed without consumer inventory, parity evidence, and rollback plan.

## Migration Plan

Phase 1 names and exports canonical objects without changing trading semantics. Phase 2 creates
adapters from old contracts and runs golden/parity tests. Phase 3 migrates composition and clients.
Phase 4 observes a deprecation window. Phase 5 deletes adapters through Governance approval.

## Remaining Risks

- Market Thesis, Trade Quality, Research Finding, Lineage Graph, Decision Presentation, Dashboard
  View, and Institutional Health still require canonical code migration.
- Nine P0 debt items block production.
- All 25 trading hypotheses remain unvalidated.
- Compatibility CLI bypasses modern trust/state/comprehension controls.
- Institutional records are not durably identity/hash bound.
- No measured decision-quality trend exists.

## Institutional Readiness Assessment

The former manually estimated aggregate was invalidated by ADR-0006. Current readiness is assessed
per canonical capability in `capability-readiness-matrix.md`; project readiness is derived by
`project-readiness-formula.md` and rendered in `institutional-readiness-dashboard.md`.

## Sprint Verdict

Governance artifacts are consolidated, but architecture has not yet passed readiness review. Feature
development remains frozen. The next authorized work is canonical-model migration only.
