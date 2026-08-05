# Architecture — Version 1 Foundation

## Decision boundary

Gold Brain answers one question: does the available evidence justify searching for a BUY setup, a SELL setup, or neither? A directional verdict is an attention-allocation decision, not an order.

The core is a pure, deterministic function:

`MarketObservation + DecisionPolicy + evaluation time -> Decision`

This boundary keeps future data ingestion, persistence, APIs, and dashboards from changing the meaning of the decision.

## Immutable methodology gates

The engine fails closed to `WAIT` when any mandatory input is missing, stale, invalid, or contradictory:

1. SMC market structure and a confirmed break of structure.
2. A valid dealing range and directionally appropriate premium/discount location.
3. A directionally appropriate liquidity sweep with displacement confirmation.
4. A supported symbol and trustworthy timestamp.

These gates encode the project philosophy. They must not be bypassed by a score.

## Configurable hypotheses

`DecisionPolicy` contains versioned, reviewable hypotheses: maximum observation age, equilibrium width, attention threshold, and evidence weights. Policy changes must update the hypothesis register and be evaluated against held-out historical periods before adoption.

The initial equal-ish weights do not claim predictive validity. Under the current mandatory-gate design they primarily expose attribution and prepare the contract for comparative research.

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
