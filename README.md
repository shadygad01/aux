# Gold Brain

Gold Brain is an explainable decision-intelligence foundation for discretionary XAUUSD traders. It evaluates whether current evidence justifies searching for a high-quality **BUY**, **SELL**, or **WAIT** setup. It does not generate entries, stops, targets, or execution instructions.

## Version 1 foundation

**Scope note:** the bullet list below describes the `capabilities/*` institutional governance
framework's target design -- a separate architecture with no production consumer today (see
`publish/composition.py`'s docstring). The system that actually runs and is deployed is the live
canonical pipeline (`LiveMarketCollector` -> `DecisionEngine` -> `ExecutionReadinessEngine` ->
`MultiTimeframeEngine` -> `OpportunityIdentityEngine` -> `publish/generate_artifacts.py`), which
is simpler than everything described below and does not implement most of it.

The initial implementation deliberately keeps the decision path small and auditable:

- Smart Money Concepts market structure establishes directional context.
- A valid dealing range classifies price as premium, equilibrium, or discount.
- Liquidity evidence is mandatory and directionally interpreted.
- Data freshness and completeness are hard gates.
- A deterministic policy produces a verdict, confidence category, reasons, conflicts, and missing evidence.
- Every configurable weight is labelled as a hypothesis rather than a fact.
- The trading-constitution engine evaluates macro, three independent bias horizons, location, liquidity, MACD, SMC, news, and 0–100 trade quality.
- Every trading evaluation is durably appendable for later winning, losing, ignored, rejected, or missed research classification.
- The Version 3 evidence engine distinguishes insufficient evidence (`NO_OPINION`) from incomplete execution (`WAIT`) and automatically decays every evidence item to zero across its TTL.
- The learning subsystem permanently stores complete evaluation/outcome records, turns failures into hypotheses and successes into research evidence, and can propose—but never deploy—changes.
- The institutional knowledge base governs evidence-backed sources, historical events, patterns, append-only knowledge revisions, review expiry, source ranking, and structured questions.
- The Version 4 reasoning layer enforces the complete macro-to-recommendation chain across evidence, current knowledge, market state, historical similarities, research, and non-deploying learning suggestions.
- Decision Memory assigns atomic institutional IDs, preserves complete immutable version history in SQLite, reconstructs decisions after restart, and supports outcome and evolution searches.
- Pattern Discovery stores evidence-linked experimental behavior and permits production use only after sequential significance, repeatability, backtest, forward-test, and documentation gates.
- Official Decision 2.0 rejects unexplained outputs and exposes every answer plus reasoning-to-source lineage; scores never substitute for evidence.
- Self-Critic requires a pre-publication challenge, questions wins as well as failures, and automatically opens evidence-linked Research Tasks for failed decisions.
- Constitutional Governance maps every artifact to an authority level, rejects unauthorized actors and mislabelled domains, and requires explicit evidence gates before authorization.
- Research Governance requires complete question-to-migration proposals and structurally prevents every research output from representing production policy.
- Quality Assurance blocks sprint completion until ten evidence-backed reviews pass and documentation, tests, and architecture remain synchronized.
- Trust manifests make official recommendations replayable and auditable by exposing facts, lineage, contradictions, measurements, policy, and canonical input fingerprints.
- Institutional Memory durably preserves content-addressed research, patterns, outcomes, regimes, comparisons, and decision/knowledge evolution, and blocks empty market-day closure.
- Market Regime gates public evidence and reasoning analysis on a current, evidence-backed, multi-label context and per-evidence interpretation.
- Current Market State unifies regime, macro, bias, volatility, liquidity, momentum, news, confidence, and uncertainty under one downstream state ID.
- Institutional Comprehension rejects abstract, statistical, or opaque reasoning unless it is translated into verifiable professional-trader terms before authorization.

`BUY` and `SELL` mean only “the evidence justifies searching for a setup.” `WAIT` is the fail-closed result whenever mandatory evidence is unavailable, stale, contradictory, or too weak.

## Quick start

Requires Python 3.11 or newer.

```powershell
python -m gold_brain examples/bullish_evaluation.json --at 2026-08-05T12:00:00Z
python -m unittest discover -s tests -v
```

The command prints a JSON decision record suitable for later API, dashboard, or audit-log use.

## Monorepo map

- `capabilities/` — the public business-first architecture and ten independently replaceable capability interfaces.
- `apps/decision_cli/` — presentation and dependency-injection composition root.
- `packages/domain/` — immutable evidence, decisions, and named policy configuration.
- `packages/application/` — independent decision engine and external-effect ports.
- `packages/infrastructure/` — versioned JSON and structured logging adapters.
- `contracts/` — published JSON schemas and compatibility policy.
- `runtime/` — runtime composition, configuration, and security notes.
- `gold_brain/` — backward-compatible facade for the pre-constitution interface.
- `tests/` — behavior and invariant tests.
- `docs/` — architecture, errors, dependencies, migration, and research hypotheses.

## Non-goals

The `capabilities/*` governance framework described above does not ingest live market data, backtest weights, identify order blocks, or recommend trades on its own -- those require separately validated data contracts and research evidence within that framework, and it accepts only synthetic or manually prepared observations to keep its decision contract executable and testable. This does not describe the live canonical pipeline: that pipeline does ingest real live market data (`LiveMarketCollector`, `MacroCollector`) and, as of `backtest/`, has an offline backtest tool that replays real history through the unmodified production `DecisionEngine` (see `backtest/README.md`).

## Quality gates

Pull requests must pass Ruff formatting and lint, strict mypy checking, architecture rules, all tests, and at least 90% branch-aware coverage. See `.github/workflows/quality.yml`.

Feature development is currently frozen by the Governance Consolidation Roadmap for the `capabilities/*` track specifically -- see the scope note in `docs/roadmap.md`. The live canonical pipeline is not part of that freeze and continues active development. See
`docs/roadmap.md`, `docs/capability-readiness-matrix.md`, and
`docs/institutional-readiness-dashboard.md`.

## Safety and responsibility

Gold Brain is research and decision-support software, not financial advice. Market data can be delayed, incomplete, or wrong. The trader owns all execution decisions and risk.
