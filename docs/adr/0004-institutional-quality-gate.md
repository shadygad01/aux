# ADR-0004: One Institutional Quality Gate

## Problem

Three review lists defined six, eight, and ten different completion requirements.

## Context

A sprint cannot be complete under conflicting quality definitions.

## Alternatives

1. Run every list independently.
2. Keep the smallest automated gate.
3. Replace all lists with the union required by Institutional Standards.

## Decision

One Institutional Quality Gate owns exactly ten reviews: Architecture, Trading, Research, Learning,
Documentation, Testing, Performance, Security, Explainability, and Maintainability. Red-team
findings are mandatory evidence within each review. Synchronization of architecture, documentation,
and tests remains a separate hard gate.

## Consequences

The six-review sprint schema is deleted. A completion record cannot be issued until all ten areas
approve the exact artifact revision. Durable reviewer identity and commit-hash binding remain debt.
