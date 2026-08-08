# Backtest

Standalone offline tool that replays real historical XAUUSD H1 candles through the unmodified
production `DecisionEngine`/`DecisionPolicy`, to produce real evidence for the hypotheses in
`docs/hypothesis-register.md` (H-001, H-002, H-003, H-004, H-005, H-006, H-007, H-024, H-025) —
the actual weights and gates the live decision path runs on. It is deliberately not wired into
`publish/`, `capabilities/`, or any live path; it never runs automatically.

## Run

```bash
python -m backtest.cli --ticker GC=F --days 365 --output-dir backtest/reports/
python -m backtest.cli --ticker GC=F --days 365 --output-dir backtest/reports/ --sensitivity
```

Writes `backtest_report.json` (machine-readable) and `backtest_report.md` (human-readable) to
`--output-dir`.

## What this does and does not prove

- **Faithful to production for the BUY/SELL/WAIT verdict itself.** The walk-forward loop builds
  each `MarketObservation` exactly the way `LiveMarketCollector` does (same sliding window size,
  same `smc_detector` functions, same `DecisionEngine`/`DecisionPolicy`), so the verdicts measured
  here are the verdicts production would have made on the same history.
- **Risk guidance (stop/target/R:R) uses H1 ATR, not the execution-timeframe ATR production risk
  guidance actually uses** (M5/M15 — see `publish/generators/multi_timeframe.py`). This backtest
  is H1-only by design; stop/target/R:R figures here are a documented approximation, not what live
  execution would size. The verdict itself carries none of this deviation — `DecisionEngine` never
  touches ATR.
- **Same-candle stop/target ambiguity** (OHLC has no intrabar order): when a single candle's range
  touches both levels, this tool classifies it as a stop-out (`CONSERVATIVE_STOP_FIRST`) —
  deliberate and conservative, not a guess.
- **Signal counting is edge-triggered** (one signal per verdict transition, not per candle a setup
  remains valid) — a modeling choice stated explicitly in every report, since a different
  convention would change totals without changing the underlying trades.
- **Yahoo's real H1 history limit is discovered empirically, not assumed.** `candle_fetcher.py`
  walks backward in chunks and stops the first time a chunk returns nothing; the report's "Data
  coverage actually obtained" section states exactly what was returned.

This tool measures whether the live methodology's weights and gates historically produced
favorable outcomes. It does not modify `DecisionEngine`, `DecisionPolicy`, or any other production
code, and a favorable result here is not, by itself, authorization to change production behavior —
see `docs/hypothesis-register.md`'s change protocol.
