# Compatibility and Migration

The engineering-constitution refactor preserves the original command and import surface:

- `python -m gold_brain ...` delegates to `apps.decision_cli`.
- `gold_brain.domain` re-exports `packages.domain`.
- `gold_brain.engine.DecisionEngine()` retains the optional policy and `now=` calling convention.

New code should import domain contracts from `packages.domain`, inject infrastructure through `packages.application.DecisionEngine`, and serialize through `packages.infrastructure`. The compatibility facade will remain through the 1.x line; removal requires a new major version and consumer migration evidence.

Observation JSON now requires `contract_version: "1.0.0"`. Inputs without a version are rejected rather than guessed.
