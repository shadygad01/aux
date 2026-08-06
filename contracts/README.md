# JSON Contracts

## Responsibility

Own published, immutable schemas for communication between engines and consumers.

## Versioning

Contracts use semantic versions. Additive optional fields require a minor version; breaking field or meaning changes require a new major schema and a migration document. Existing major schemas remain available while consumers migrate.

## Published outputs

- `market-observation-v1.schema.json` documents engine input `1.0.0`.
- `decision-output-v1.schema.json` documents engine output `1.0.0`.
- `trading-decision-v2.schema.json` documents the trading-constitution output `2.0.0`.
- `evidence-decision-v3.schema.json` documents the expiring-evidence output `3.0.0` with exactly four recommendations.
- `learning-record-v1.schema.json` documents the permanent learning record `1.0.0`.
- `knowledge-object-v1.schema.json` documents versioned institutional knowledge objects.
- `reasoning-decision-v4.schema.json` documents the full institutional reasoning path and four-output decision.
- `capability-health-v1.schema.json` documents capability-owned health output.
- `official-decision-v1.schema.json` documents the Decision Capability output.
- `official-decision-v2.schema.json` requires complete explanations and a pre-publication critique.
- `official-decision-v3.schema.json` adds reproducible facts, measurements, audit, and input fingerprints.
- `decision-memory-v1.schema.json` documents immutable decision versions and snapshots.
- `decision-critique-v1.schema.json` documents independent self-critic records.
- `discovered-pattern-v1.schema.json` documents governed pattern discovery.
- `governance-change-v1.schema.json` documents constitutional authorization requests.
- `research-proposal-v1.schema.json` documents canonical non-production research proposals.
- `institutional-quality-completion-v1.schema.json` documents the canonical ten-area quality gate.
- `capability-readiness-history-v1.schema.json` documents immutable capability-derived readiness snapshots.
- `institutional-memory-v1.schema.json` documents content-addressed institutional experience.
- `market-regime-v1.schema.json` documents evidence-backed, expiring, multi-label regime context.
- `current-market-state-v1.schema.json` documents the complete downstream state aggregate.
- `official-decision-v4.schema.json` binds an official recommendation to its Current State ID.
- `reasoning-comprehension-v1.schema.json` documents professional-trader comprehension review.
- `official-decision-v5.schema.json` requires an approved comprehension review.
- `context-v1.schema.json` documents the canonical environmental context (session, news, macro, volatility, liquidity, calendar flags).
- `market-story-v1.schema.json` documents the multi-stage market evolution narrative.
- `market-thesis-v1.schema.json` documents the sole canonical Market Thesis and 0-100 Trade Quality decision output.
- `execution-readiness-v1.schema.json` documents Execution Readiness (0-100) and ExecutionStatus (FRESH, ACTIVE, LATE, EXPIRED, WAIT).
- `opportunity-identity-v1.schema.json` documents canonical Opportunity Identity tracking, separating current vs previous opportunities and fresh vs repeated opportunity backtesting.
- `multi-timeframe-v1.schema.json` documents Multi-Timeframe Scalping thesis, cascading M5/M15 execution triggers from H1 structural bias.
- `signal-prediction-v1.schema.json` documents Signal Prediction forecasting the next expected setup opportunity window based on backtest session frequency.
- `macro-context-v1.schema.json` documents institutional macro context (DXY, US10Y/US02Y yields, news, liquidity reference levels).
- `macro-assessment-v1.schema.json` documents macro score, confidence modifier, and fail-closed WAIT signals.
- `macro-evidence-v1.schema.json` documents institutional macro evidence items.

Runtime validation is implemented by `packages.infrastructure.json_contracts` without coupling the domain to JSON Schema tooling.

Version 1 remains available during migration. Version 2 adds three-horizon bias, 0–100 trade quality, execution status, complete evidence categories, and next improvement; it is a new major contract because those semantics cannot be added compatibly to Version 1.

Version 3 separates `NO_OPINION` from `WAIT`, removes `PAUSED` as a recommendation, and publishes reproducible freshness, effective weight, and confidence. Version 2 remains available because changing its output enum in place would break consumers.

## Dependencies

JSON Schema 2020-12 vocabulary; no runtime validator dependency is currently required.
