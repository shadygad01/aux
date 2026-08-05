# ADR-0005: Compatibility Adapter Terminology and Isolation

## Problem

Informal age-based terminology hides whether old code is supported, authoritative, or scheduled for removal.

## Context

Backward compatibility is necessary for the v1 CLI and import surface, but old decision paths must
not compete with canonical production ownership.

## Alternatives

1. Keep an informal age-based label.
2. Delete all old interfaces immediately.
3. Name and isolate Compatibility Adapters with owners and removal criteria.

## Decision

Use **Compatibility Adapter** exclusively. Every adapter must identify the canonical target,
supported consumers, equivalence tests, deprecation state, and removal milestone. Compatibility
Adapters cannot contain new business logic.

## Consequences

The v1 CLI, `gold_brain` facade, older schemas, and engine entry points remain temporarily. Their
business logic must be redirected to canonical capabilities or deleted during Phase 1.
