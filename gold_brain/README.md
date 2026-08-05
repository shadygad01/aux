# Compatibility Facade

## Responsibility

Preserve the pre-constitution `gold_brain` imports and CLI while consumers migrate to monorepo package interfaces.

## Architecture notes

No new behavior belongs here. The facade delegates to application and infrastructure packages and is covered by regression tests.

## Public interfaces

`gold_brain.domain`, `gold_brain.engine.DecisionEngine`, package-level domain exports, and `python -m gold_brain`.

## Dependencies

Monorepo domain, application, infrastructure, and CLI packages. Owner: platform compatibility.
