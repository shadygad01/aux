# Execution Readiness Capability

The **Execution Readiness Capability** evaluates whether a technically valid Market Thesis is still executable in real-time trading.

## Mission

- Separate **Setup Quality** (0-100) from **Entry Timing / Execution Readiness** (0-100).
- Assign canonical `ExecutionStatus`: `FRESH`, `ACTIVE`, `LATE`, `EXPIRED`, `WAIT`.
- Enforce strict rules: Execution Readiness never increases after price moves away from entry, and macro invalidations immediately trigger `WAIT`.
