# Runtime

## Responsibility

Document deployment-time composition and configuration boundaries. Version 1 has a local CLI runtime only; no server, scheduler, secret, URL, or external data endpoint exists.

## Configuration

The CLI composition root injects `DecisionPolicy` and `JsonDecisionLogger`. Policy fields are the sole source of thresholds, weights, intervals, symbol scope, versions, and disclaimer text.

## Security

No secrets are required. Future credentials must be supplied through environment configuration and must never enter policy objects, logs, fixtures, or source control.

## Dependencies

The deployable runtime uses only packages declared in this monorepo and the Python standard library.
