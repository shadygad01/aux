# Backtest Report

## Run parameters

- Ticker: `GC=F`
- Generated at: 2026-08-08T15:24:57.165486+00:00
- Window (candles per observation): 720
- Policy version: `v1-hypothesis-1`

## Data coverage actually obtained

- Candle count: 5704
- Data start: 2025-08-08T15:00:00+00:00
- Data end: 2026-08-07T20:00:00+00:00
- **Note:** Yahoo's real intraday history limit is not assumed by this tool -- the range above is what was actually returned, not a requested target. Treat a shorter-than-expected range as the discovered boundary, not a bug.

## Summary statistics

| Metric | Overall | BUY | SELL |
|---|---|---|---|
| Signals | 0 | 0 | 0 |
| Win rate | None | None | None |
| Average R:R | None | None | None |

Target hit: 0 · Stop hit: 0 · Open at end of data: 0 · No risk guidance: 0

## Sensitivity sweep (attention_threshold)

| Threshold | Signals | Win rate | Avg R:R |
|---|---|---|---|
| 0.65 | 0 | None | None |
| 0.7 | 0 | None | None |
| 0.75 | 0 | None | None |
| 0.8 | 0 | None | None |
| 0.85 | 0 | None | None |

## Caveats

- **Risk model:** Risk guidance uses H1 ATR (this backtest replays H1 only), not the execution-timeframe (M5/M15) ATR production risk guidance actually uses -- stop/target/R:R figures are a documented approximation. The BUY/SELL/WAIT verdict itself is unaffected: DecisionEngine never uses ATR.
- **Ambiguous candles:** when a single candle's range touches both the stop and the target, this backtest classifies it as `CONSERVATIVE_STOP_FIRST` -- a deliberate conservative choice, not a modeling gap.
- **Signal counting:** one signal is recorded per verdict transition (edge-triggered), not per candle a setup remains valid. A different counting convention would change these totals but not the underlying trades.
- **Open trades:** 0 signal(s) never resolved before the data ended and are excluded from win rate / R:R, not counted as either a win or a loss.
