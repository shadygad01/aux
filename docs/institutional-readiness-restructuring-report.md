# Institutional Readiness Restructuring Report

## Completed Work

Replaced manually estimated project readiness with ten evidence-backed capability assessments, four
mandatory owned subprofiles, a weakest-link formula, maturity stages, promotion rules, blockers,
dependencies, dashboard projection, and append-only history contract.

## Architecture Changes

ADR-0006 preserves the ten canonical owners. Market Story, Market Thesis, Decision Presentation,
and Governance are independently visible blocking subprofiles under their existing owners. No
trading behavior, feature, UI, or performance implementation changed.

## Research Performed

Repository evidence was inventoried across capability implementations, contracts, tests,
documentation, ADRs, technical debt, research records, and the roadmap. No market research or
trading hypothesis work was performed.

## Problems Found

The prior aggregate was manually estimated and masked capability variance. The first draft history
shape could not preserve multiple snapshots and was corrected before completion. Publishing and
Monitoring remain prototypes; no capability is a Production Candidate.

## Suggested Improvements

Implement durable, revision-bound readiness evaluation under Monitoring only after canonical model
migration is authorized. Generate the dashboard from history and blockers to eliminate manual drift.

## Risks

- Scores use governed milestone judgments, not an executable evaluator.
- The current snapshot identifies an uncommitted worktree rather than an immutable revision hash.
- Performance evidence is absent for every capability.
- Owned subprofiles could be misread as new business owners despite ADR-0006.
- The minimum formula is intentionally conservative and assumes all ten capabilities are required.

## Technical Debt

RB-001 through RB-012 are the canonical readiness blockers. Existing TD items remain authoritative
for removal strategy and must not be duplicated into another debt register.

## Red-Team Verdict

The readiness structure is internally auditable, but institutional production permission remains
denied. Documentation and regression checks cannot substitute for durable governance, canonical
outputs, research validation, explainability evidence, or revision-bound approval.

## Next Sprint Recommendation

Stop. Do not resume features. Any next sprint requires explicit authorization and must address
canonical-model migration or durable readiness governance without changing trading logic.
