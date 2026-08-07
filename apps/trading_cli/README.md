# Trading CLI

## Responsibility

Provide a command-line presentation and the dependency-injection composition root for the trading-opportunity ("Discount + MACD" constitution) evaluation. It reads one versioned JSON trading observation and prints one trading decision; it contains no market logic.

## Architecture notes

The CLI constructs `TradingPolicy`, `JsonTradingDecisionLogger`, `JsonLinesOpportunityRepository`, and `TradingOpportunityEngine`. This is the only layer allowed to select concrete adapters. It never fetches market data itself — `packages.infrastructure.smc_detector` and `packages.infrastructure.momentum` compute the structure, liquidity-sweep, reversal-candle, and MACD evidence from real candles, but macro assessment, per-horizon bias, and news evidence must still be supplied in the observation JSON: this v1 has no live macro/news collector wired to the `TradingObservation` contract, so nothing here fabricates them.

## Public interface

```
python -m apps.trading_cli.main <observation.json> [--at <ISO-8601>] [--ledger <path.jsonl>]
```

## Dependencies

Application, domain, and infrastructure packages plus the Python standard library. Owner: application delivery.
