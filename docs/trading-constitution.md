# Trading Constitution

Status: **IMMUTABLE — explicit approval is required for changes.**

## Mission and authority

Gold Brain filters poor trades; it does not maximize trade count. Uncertainty prefers `WAIT`, which is a successful decision. Context always precedes entry. Gold Brain evaluates opportunities and never executes; the trader owns entry, stop, target, risk, and execution.

## Required decision flow

1. Understand macro environment.
2. Determine market bias.
3. Determine location.
4. Evaluate liquidity.
5. Evaluate momentum.
6. Evaluate SMC evidence.
7. Calculate trade quality from 0 through 100.
8. Return BUY setups only, SELL setups only, or WAIT.

## Immutable trading rules

- Bias allocates attention rather than predicts price. Long-term, medium-term, and scalping biases are independent and must all be exposed as `BUY_ONLY`, `SELL_ONLY`, or `WAIT`.
- BUY evaluation may continue only in discount. SELL evaluation may continue only in premium. Equilibrium means WAIT; location never creates a trade.
- Liquidity is contextual. PDL, PWL, and PML may support buying; PDH, PWH, and PMH may support selling. No fixed ranking is assumed.
- MACD is a filter, never an entry trigger. BUY requires MACD below zero; SELL requires MACD above zero. Crossovers are optional; histogram and slope are secondary.
- News never creates direction. It may support, reduce confidence, reject, pause, or force WAIT. Each item must include why, impact, expected duration, and confidence.
- Macro covers Fed, rates, inflation, employment, DXY, real yields, US10Y, geopolitical events, and sentiment. Its interpreted attention bias and reasoning are evidence inputs; the current engine does not invent a macro model.
- SMC requires a liquidity sweep and reversal candle. CHoCH, order block, and fair value gap are optional confirmations that improve quality.
- Every score explains supporting, contradicting, and missing evidence.
- Every evaluation is appended to the research record. Later winning, losing, ignored, rejected, and missed classifications are appended without mutating the original decision.

## Implementation mapping

`packages.application.TradingOpportunityEngine` enforces the flow and mandatory gates. `TradingPolicy` contains versioned scoring hypotheses. `trading-decision-v2.schema.json` publishes output `2.0.0`. `JsonLinesOpportunityRepository` stores evaluations with a pending outcome and accepts later append-only classifications.

The engine intentionally consumes reviewed macro and bias assessments. Automatic interpretation of raw Fed, inflation, employment, DXY, yields, geopolitical, sentiment, SMC, or news data is not validated and therefore is not claimed.
