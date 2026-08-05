# Capability Constitution

Status: **GOVERNING ARCHITECTURE — explicit approval is required for changes.**

## Public architecture

Gold Brain is publicly composed of ten business capabilities: collection, normalization, evidence, knowledge, reasoning, decision, learning, research, publishing, and monitoring. New production composition must use `capabilities.*` interfaces. Compatibility Adapter classes suffixed `Engine` remain outside this layer solely for backward compatibility and implementation migration; architecture tests prevent capability code from importing them.

Each capability folder owns one responsibility, interface, typed input/output contracts, test coverage, metrics, logs, health status, and README. Capabilities import domain contracts and shared operational contracts only. They never import apps, UI, dashboards, or Compatibility Adapter application implementations.

## Responsibility boundaries

- Collection acquires raw strings through a replaceable adapter.
- Normalization converts raw numeric values into configured canonical units.
- Evidence evaluates an expiring evidence snapshot.
- Knowledge answers governed questions and exposes ranking/review state.
- Reasoning creates the complete institutional reasoning path.
- Decision authorizes a complete nine-stage path as the official output.
- Learning stores evaluated outcomes and immediate learning artifacts.
- Research computes cohorts and writes approval-required proposals.
- Publishing delivers an immutable official decision through a replaceable sink.
- Monitoring aggregates health contracts without inspecting internals.

Learning and research are deliberately separate even though a Compatibility Adapter service implements both. Capability-owned protocols prove alternate implementations can replace that service.

## Operational ownership

Every operation emits capability-named metrics and logs through `CapabilityTelemetry`. Every capability implements `health(checked_at)` and returns `HEALTHY`, `DEGRADED`, or `NOT_READY`. Missing external collection or publishing adapters produce `NOT_READY`; the code does not claim those integrations exist.

## Communication

Capabilities communicate only through dataclasses, enums, and protocols exported from public modules. Internal implementation access, UI dependencies, and hidden shared mutable state are prohibited by architecture tests.
