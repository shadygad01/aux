# Decision CLI

## Responsibility

Provide a command-line presentation and the dependency-injection composition root. It reads one file and prints one decision; it contains no market logic.

## Architecture notes

The CLI constructs `DecisionPolicy`, `JsonDecisionLogger`, and `DecisionEngine`. This is the only layer allowed to select concrete adapters.

## Public interface

`python -m gold_brain <observation.json> [--at <ISO-8601>]` remains the backward-compatible command.

## Dependencies

Application, domain, and infrastructure packages plus the Python standard library. Owner: application delivery.
