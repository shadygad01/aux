# ADR-0001: Capability Ownership Is the Public System Boundary

## Problem

Application services and compatibility engines accumulated without an explicit ownership record.

## Context

The Constitution defines ten capabilities: Collection, Normalization, Evidence, Knowledge,
Reasoning, Decision, Learning, Research, Publishing, and Monitoring.

## Alternatives

1. Add a capability for every cross-cutting service.
2. Let application services become independent business owners.
3. Keep ten owners and treat application services as orchestrators implementing capability ports.

## Decision

Keep exactly ten public capability owners. Application services own no business truth. Governance,
quality, lineage, state assembly, critique, and memory services are policies or infrastructure used
through a capability owner. Any exception requires a new ADR and Constitutional approval.

## Consequences

Current cross-cutting services need an ownership mapping. New capability folders are prohibited
without approval. Monitoring owns institutional health aggregation; Decision owns Market Thesis;
Research owns Research Finding; Learning owns Learning Recommendation.
