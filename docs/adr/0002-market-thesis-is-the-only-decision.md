# ADR-0002: Market Thesis Is the Only Canonical Decision

## Problem

`Decision`, `EvidenceDecision`, `TradingDecision`, `ReasoningDecision`, `OfficialDecision`, and
`DecisionVersion` can be mistaken for competing decisions.

## Context

Evidence and reasoning need intermediate outputs, audit requires immutable history, and old clients
need compatibility contracts. Those needs do not justify multiple business decisions.

## Alternatives

1. Keep every output as a decision.
2. Build one giant decision object containing every stage.
3. Define one Market Thesis and classify all other outputs by role.

## Decision

The Decision Capability owns one canonical **Market Thesis**. Evidence output is an Evidence
Assessment. Reasoning output is a Reasoning Projection. Decision Memory stores Decision Audit
versions. Publishing produces Decision Presentation. Old decision contracts are Compatibility
Adapters until migration evidence permits deletion.

## Consequences

`OfficialDecision` is the current implementation precursor but must be migrated to the canonical
domain name `MarketThesis`. No new decision-shaped model is allowed. Existing scoring paths remain
a P0 consolidation debt and feature work stays blocked until one path produces the thesis.
