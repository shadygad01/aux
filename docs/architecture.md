# Architecture — Version 1 Foundation

## Decision boundary

Gold Brain answers one question: does the available evidence justify searching for a BUY setup, a SELL setup, or neither? A directional verdict is an attention-allocation decision, not an order.

The core is a pure, deterministic function:

`MarketObservation + DecisionPolicy + evaluation time -> Decision`

This boundary keeps future data ingestion, persistence, APIs, and dashboards from changing the meaning of the decision.

## Context boundary

Context describes the environment in which evidence must be interpreted.
- **Context is NOT Evidence**: Context contains session, news window, macro regime, volatility regime, liquidity conditions, and calendar flags (not directional observations).
- **Context is NOT Knowledge**: Context is a transient, expiring environmental wrapper.
- Every downstream capability must consume a valid `MarketContext` before producing reasoning or decision output.

## Immutable methodology gates

The engine fails closed to `WAIT` when any mandatory input is missing, stale, invalid, or contradictory:

1. SMC market structure (directional bias) must be present and non-neutral. A confirmed break of structure is **not** mandatory as of 2026-08-08 (owner instruction, see `docs/hypothesis-register.md`'s H-025 follow-up): it still contributes its score weight when present, but its absence no longer forces a conflict/WAIT on its own.
2. A valid dealing range and directionally appropriate premium/discount location. Mandatory by default (`DecisionPolicy.location_mandatory=True`); a policy may relax this to a score-only bonus (same treatment as gate 1) -- see gate 6.
3. A directionally appropriate liquidity sweep with displacement confirmation. Mandatory by default (`DecisionPolicy.sweep_mandatory=True`); a policy may relax this the same way as gate 2.
4. A supported symbol and trustworthy timestamp.
5. An H1 MACD line sign that supports the candidate direction: below zero for BUY, above zero for SELL by default (`DecisionPolicy.macd_mode="asis"`). MACD is a filter, never an entry trigger — it contributes no score and cannot grant a verdict the other gates did not already earn; it can only convert a candidate BUY/SELL into WAIT. Uses the MACD line specifically, not the histogram, signal line, or slope. A policy may flip the sign requirement (`macd_mode="flipped"`) or disable the filter entirely (`macd_mode="off"`, in which case MACD evidence is not even required) -- see gate 6.
6. Gates 2, 3, and 5's mandatoriness/mode are `DecisionPolicy`-level configuration, not hardcoded, as of 2026-08-09 (see `docs/hypothesis-register.md` H-026). **Every live artifact generator** (`decision.json`, `market_thesis.json`, `execution_readiness.json`, `market_story.json`, `opportunity_identity.json`, `policy.json`, and the Multi-Timeframe engine's H1 role in `multi_timeframe.json`) evaluates H1 under the SAME policy: `build_production_h1_policy()` -- a separately-tuned, owner-validated configuration (liquidity-sweep-dominant weights, location/sweep relaxed to bonus-only, MACD disabled) that replaces the original all-mandatory/"asis" default. This is deliberate unification, not the original design: before 2026-08-09 the Multi-Timeframe cascade alone used this policy while every other generator used the separate `build_decision_policy()` default, which meant the dashboard's headline "Current Thesis" verdict and the cascade's H1 bias could silently disagree on the exact same H1 candle. `build_decision_policy()` still exists (kept for tests and `backtest/` CLI comparisons) but no live generator calls it anymore.

These gates encode the project philosophy. They must not be bypassed by a score, except where explicitly demoted to a score-only contributor per gate 1, or relaxed per the production policy's documented, owner-approved configuration in gate 6.

## Multi-Timeframe cascade (H1 -> M15)

`MultiTimeframeEngine` (`packages/application/multi_timeframe_engine.py`) is a second, separate decision path from the single-timeframe boundary above -- it does not replace it, but as of the H-026 unification (gate 6) it evaluates H1 under the exact same policy the primary thesis now uses, so the two paths' H1 bias can never disagree. H1 sets the trade **direction** only (BUY/SELL/WAIT); M15 is not independently gated -- it triggers the entry moment and is blocked only if its own structure explicitly opposes the H1 direction. This "H1 direction, M15 timing, no independent M15 gates" design, M15 (not M5) as the execution timeframe, and the risk-guidance methodology below are all owner-validated per `docs/hypothesis-register.md` H-026 -- see that entry for the full evidence trail and its disclosed limits.

Risk guidance (`_compute_risk_guidance`) derives, from the same ATR-buffered structural stop this engine always used:
- a target at `entry +/- RR_TARGET_MULTIPLE(4) * stop_distance` -- guaranteeing at least a 1:3 reward-to-risk by construction, replacing the earlier structure/liquidity-derived target which offered no such guarantee;
- a partial-exit plan: close `PARTIAL_FRACTION(50%)` at `RR_PARTIAL_MULTIPLE(2)` R, move the remainder's stop to breakeven, then trail it by `TRAIL_ATR_MULTIPLE(0.5)` * ATR behind the best price reached, instead of holding the whole position for a single fixed exit.

This is decision-support information for a **manually executed** trade (the owner does not run an automated bot) -- surfaced on the dashboard's Trade Plan card, never auto-executed.

## Configurable hypotheses

`DecisionPolicy` contains versioned, reviewable hypotheses: maximum observation age, equilibrium width, attention threshold, evidence weights, gate mandatoriness, and MACD mode. Policy changes must update the hypothesis register and be evaluated against held-out historical periods before adoption.

The default policy's initial equal-ish weights do not claim predictive validity; under its mandatory-gate design they primarily expose attribution and prepare the contract for comparative research. The H1-cascade policy's weights are the one exception that IS backed by out-of-sample validation -- see H-026.

## Explainability contract

Every decision records:

- verdict and its precise meaning;
- confidence category and normalized score;
- evidence supporting the thesis;
- conflicts opposing it;
- missing mandatory evidence;
- observation and evaluation timestamps;
- policy version and execution disclaimer.

The decision is JSON-serializable so the same record can be stored, displayed, or audited without recomputing hidden logic.

## Planned seams, not implemented claims

- **Ingestion adapters:** broker candles, economic data, and reviewed news each map into provenance-bearing evidence.
- **SMC extraction:** swing, structure, liquidity, displacement, and dealing-range algorithms need explicit definitions and labeled evaluation sets.
- **Research harness:** walk-forward experiments compare policies and report uncertainty, abstention, and regime behavior.
- **Audit store:** append-only observations, policy versions, and resulting decisions.
- **Delivery:** an API and dashboard consume decisions but never create alternate decision logic.

No live-data or automated-pattern capability should be labelled production-ready until its data provenance, failure behavior, and validation evidence are documented.
