# ADR-0006: Institutional Readiness Is Capability-Derived

## Problem

A manually estimated project score concealed large differences between capability maturity levels.

## Context

Gold Brain has ten canonical capability owners. Market Story, Market Thesis, Decision Presentation,
and Governance require independent visibility, but ADR-0001 assigns them to Reasoning, Decision,
Publishing, and Monitoring rather than allowing parallel owners.

## Alternatives

1. Retain one expert-estimated project score.
2. Create new capability owners for every output and cross-cutting policy.
3. Score each canonical capability, expose mandatory owned subprofiles, and derive project readiness.

## Decision

Use the six-point readiness scale `0, 20, 40, 60, 80, 100`. Each capability assessment must cite
evidence, missing work, blockers, effort, maturity, and confidence. Project readiness is the minimum
canonical-capability score because every capability is required by the institutional production
path. Distribution and median are context, never substitutes for the floor.

Market Story, Market Thesis, Decision Presentation, and Governance are mandatory blocking
subprofiles. Their scores cap their owning capability but do not create additional business owners.

## Consequences

The manually estimated 36/100 score is invalid and removed. Promotion requires evidence at the
exact artifact revision. A high average cannot hide a weak required capability. Readiness history
is append-only and cannot be rewritten when later evidence changes an assessment.
