# Architecture

## Product boundary

Gold Brain is a market-measurement and consistency-guidance publisher. The production graph is:

```text
source collectors -> synchronized snapshot -> unanimity gate -> market_data.json -> browser
```

There is no execution or trade-planning layer. A pure domain function converts
three evidence families into `LEAN_BUY`, `LEAN_SELL`, or `NEUTRAL`; the browser
consumes exactly one artifact and performs presentation only. A second pure
domain function converts M15 structure, range location, and MACD (a
separate M15 collector fetch, independent of the H1 guidance snapshot) into
a `WATCH_SELL`/`WATCH_BUY`/`NONE` reversal-watch label ("Reversal Signal
Start"), explicitly marked `validated: false`.

## Retained measurements

- authoritative spot quote and observation timestamp;
- spot-anchored H1 OHLC-derived range, midpoint, and range position;
- deterministic MACD and ATR values;
- fractal swing evidence, structure classification, and detected sweeps;
- observed DXY and US10Y values, deltas, directions, and source timestamps;
- UTC-derived session/weekend clock state;
- source, method, availability, age, and limitations for every group.

## Fail-closed rules

- A missing spot quote is `UNAVAILABLE`; no proxy close is presented as spot.
- Missing or insufficient macro history is `UNAVAILABLE`; it never becomes a
  neutral value or a static default.
- News, US02Y, composite macro scores, volatility regimes, liquidity regimes,
  forecasts, confidence, setup quality, and trade plans are not produced.
- Structure and sweep classifications are labeled detector outputs, never
  forecasts.
- Guidance is `NEUTRAL` unless the snapshot is current and synchronized and all
  three required evidence families unanimously lean in the same direction.
- No weights, confidence percentage, or hidden score is used.
- The reversal-watch label is an unvalidated heuristic pattern, not a tested
  edge; it never carries execution authority.

## Research isolation

`backtest/` is an offline research workspace. It has no import path into
`publish/` or `docs/app.js`. Legacy simulation direction/risk types remain only
where current reproducibility tests require them; they cannot become a product
output without a new explicit architecture decision.
