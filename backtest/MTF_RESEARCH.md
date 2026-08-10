# XAUUSD multi-timeframe hypothesis research

This package is an isolated research harness. It does not update production policy,
decision gates, dashboards, or trade recommendations. A result marked `SUPPORTED`
is evidence for manual review only; there is no automatic promotion path.

## Fixed protocol

- Source: Dukascopy XAUUSD BID/ASK ticks, stored under ignored `var/dukascopy/raw`.
- Lineage: ticks -> M5 -> M15 and H1. M15 and H1 are never independently sourced.
- Discovery: 2021-08-08 through 2024-08-08, less a five-day embargo.
- Locked holdout: 2024-08-08 through 2026-08-08.
- BUY and SELL are discovered and accepted separately.
- At most one position may be open and at most three trades may start per UTC day.
- Open trades at the data boundary are censored, not counted as wins or losses.
- Intrabar stop, target, partial, breakeven, and trailing order is resolved from ticks.
- Entries and exits use the executable ASK/BID side and apply configurable commission,
  slippage, entry delay, and maximum holding time.

The feature search is finite and interpretable: H1 BOS/CHoCH/sweeps and range
location; M15 direction and BOS; candle body and range regime; breakout/reversion;
MACD line, slope, and histogram; session, weekday, daily/weekly location; spread and
tick activity. Rules contain one or two explicit conditions and a single coherent
exit plan. Chronological discovery folds must all have positive expectancy, and
Benjamini-Hochberg false-discovery control is applied before freezing candidates.

## Reproducible stages

Run from the repository root:

```powershell
python -m backtest.mtf_research_cli download
python -m backtest.mtf_research_cli build
python -m backtest.mtf_research_cli discover
python -m backtest.mtf_research_cli holdout
```

The download is resumable. Raw files are written atomically and excluded from Git.
`tick_manifest.json` records coverage, per-hour SHA-256, tick counts, missing hours,
and gaps. `derived_manifest.json` hashes both the source manifest and every derived
bar file. Discovery freezes selected rule definitions and a configuration hash
before the holdout command can read the locked period.

Reports are written to `backtest/reports/mtf_research/` in JSON and Markdown. They
include the number of tested/rejected patterns, frozen lineage, BUY/SELL identity,
annual results, full trades, ordinary and stressed results, and neighboring exit
parameters.

## Acceptance gate

A direction is `SUPPORTED` only with at least 60 decided holdout trades, positive
net expectancy with a bootstrap 95% lower bound above zero, profit factor >= 1.20,
positive net R in each of the two consecutive 12-month holdout halves, drawdown <=
15R, losing streak <= 10, non-negative result under 1.5x explicit costs plus a
five-minute delay, no single trade or positive month contributing over 40% of
profits, and non-negative neighboring exit parameters. Fewer than 60 trades is
`INSUFFICIENT_EVIDENCE`; every other failure is `REJECTED`. The thresholds are not
relaxed after observing the holdout.
