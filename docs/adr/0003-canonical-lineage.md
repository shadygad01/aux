# ADR-0003: One Canonical Lineage Graph

## Problem

Provenance is represented by string tuples, explanation traces, graphs, audit IDs, and source fields
without one authoritative graph.

## Context

Every presentation must trace through Facts, Evidence, Knowledge, Market Story, Reasoning, and
Market Thesis without copying or losing provenance.

## Alternatives

1. Continue stage-specific reference conventions.
2. Put all source data into one giant object.
3. Use one immutable typed lineage DAG and let stages expose projections of it.

## Decision

Adopt one canonical lineage DAG with typed node kinds, immutable node IDs, typed edges, artifact
hashes, timestamps, source identity, policy version, and transformation references. Stage-specific
traces are projections, never separate truth.

## Consequences

`DecisionGraph`, `ExplanationTrace`, evidence-reference tuples, and trust references require a
migration adapter into the lineage DAG. Production remains blocked until every Market Thesis and
Decision Presentation references a complete graph.
