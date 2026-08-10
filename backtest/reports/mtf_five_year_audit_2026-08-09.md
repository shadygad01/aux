# H1/M15/M5 Five-Year Research Audit

Generated: 2026-08-09  
Repository commit: `191e13557`  
Instrument/source: Dukascopy XAU/USD BID+ASK midpoint

## Decision

The supplied files do **not** support a valid claim of a continuous five-year
multi-timeframe backtest. H1 is continuous on a calendar grid, but M15/M5 contain
only 912 complete weekdays and omit many otherwise tradable weekdays. The prior
H-026 headline result cannot be reproduced from the repository because its research
runner lived in an external scratchpad and is not committed.

The production policy remains a `TESTING` hypothesis. No tested replacement is
stable enough across years, costs, and manual-entry delays to justify a production
policy change from this dataset.

## Source-data audit

All OHLC prices were divided by 100,000 (for example, `176319500` becomes
`1763.19500`). Input files were read-only; no source values were modified.

| Check | H1 | M15 | M5 |
|---|---:|---:|---:|
| Rows | 43,635 | 87,552 | 262,656 |
| Start (UTC) | 2021-08-08 21:00 | 2021-08-11 00:00 | 2021-08-11 00:00 |
| End (UTC) | 2026-07-31 23:00 | 2026-08-07 23:45 | 2026-08-07 23:55 |
| Duplicate timestamps | 0 | 0 | 0 |
| Invalid OHLC rows | 0 | 0 | 0 |
| Zero-volume flat rows | 14,162 | 5,855 | 17,573 |
| Maximum observed gap | 1 hour | 55 days 15 minutes | 55 days 5 minutes |

M15 contains exactly 912 dates, each with 96 rows. Across the date range there
are roughly 1,303 weekdays, so only about 70% of weekdays are present. Missing
dates are not limited to weekends or holidays; examples include six-day and
47-day gaps. M5 has the identical date selection.

M5 -> M15 integrity is excellent: all 87,552 M15 candles have exactly three M5
children and open/high/low/close match exactly after aggregation. For the 21,768
hours with four M15 children, M15 -> H1 is mostly exact, but 472 highs, 501 lows,
13 opens, and 3 closes differ. The midpoint source identity and UTC timestamp grid
are consistent across all three files.

## Conservative replay protocol

- H1 decisions use the unmodified production policy returned by
  `build_production_h1_policy()` and the production SMC detector.
- Zero-volume H1 calendar fills are excluded before the H1 walk-forward replay.
- A signal is known only at the end of its H1 candle. Entry is tested at the next
  available M5 open with 0, 5, and 15 minute manual delays.
- M15 structure and ATR use only candles closed before entry. At least 35 contiguous
  M15 candles are required; no M15 structure is carried across a data gap.
- M5 determines stop/partial/trailing outcomes. A gap in M5 censors the trade as
  `DATA_GAP`; price is never allowed to jump across missing history.
- Only one decided manual trade can be open at a time.
- Same-candle ambiguity is stop-first. After a 50% partial at 2R, the remainder
  moves to breakeven and trails by 0.5x entry ATR. The runner is not capped at 4R,
  matching the H-026 prose that trailing replaces the fixed runner exit.
- Cost sensitivity deducts round-trip spread/commission/slippage equivalents of
  $0.00, $0.40, and $0.80 per ounce, normalized by each trade's initial risk.

This protocol is deliberately stricter than the undocumented external scratchpad.
It is a coverage-censored audit, not a substitute for a complete dataset.

## Baseline result: current production cascade

The active H1 replay generated 930 edge-triggered BUY/SELL signals. Only 340 had
usable contiguous M15/M5 data at zero delay; 99 of those (29.1%) were later censored
by a data gap, leaving 241 decided trades.

Primary cost case: $0.40 round trip.

| Manual delay | Decided | Win rate | Net R | Expectancy | Max drawdown | Max losing streak |
|---:|---:|---:|---:|---:|---:|---:|
| 0 min | 241 | 35.3% | +8.18R | +0.034R | 32.36R | 9 |
| 5 min | 242 | 33.5% | -4.31R | -0.018R | 34.04R | 18 |
| 15 min | 241 | 34.0% | +0.38R | +0.002R | 33.84R | 11 |

The zero-delay aggregate is weak and not year-stable: at $0.40 cost it produced
about -23.67R in 2022, then +5.51R / +6.64R / +2.91R / +14.75R in 2023-2026.
At $0.80 cost, the zero-delay full-sample result becomes negative. The apparent
edge is therefore concentrated in recent years and sensitive to execution cost.

For the nominal OOS period 2024-2026, zero-delay/$0.40 produced 112 decided trades,
+24.30R, but this is not a valid independent confirmation because the same period
was already used to select H-026 and only the supplied subset of days is observable.

## Gate ablations and additions

### Require M15 bias to agree with H1

This is the only addition worth carrying forward as a new test hypothesis. It is
not ready for production.

At zero delay/$0.40 it reduced decided trades from 241 to 116, net R from +8.18R
to +7.22R, and max drawdown from 32.36R to 18.78R. Expectancy rose from +0.034R
to +0.062R. However 2021-2023 were all negative after costs, and its 15-minute
delay result was negative in 2024. It improves selectivity and drawdown, but the
year instability prevents promotion.

### Require M15 bias agreement plus M15 BOS

At zero delay/$0.40 this produced 85 decided trades, +5.24R, +0.062R expectancy,
and 16.23R max drawdown. It further reduces drawdown but removes too many
opportunities and remains negative in 2021-2023. It is dominated by the simpler
same-bias filter on total opportunity count and has insufficient evidence.

### Require a high H1 score / sweep-dominant event

Raising the effective H1 requirement from 0.1 to 0.9 was harmful: at zero
delay/$0.40 it left 54 decided trades, a 27.8% win rate, -10.28R, and a 19.42R
max drawdown. A score of 1.0 left only three decided trades.

This exposes a naming problem in H-026. With structure weight 0.1 and threshold
0.1, a BOS by itself passes even without a liquidity sweep. In the usable baseline
set, 270 of 340 candidates scored below 0.9. The active policy is not operationally
"liquidity-sweep dominant"; it is mostly an either-BOS-or-sweep trigger whose
direction comes from the structural bias.

## Reproducibility and implementation findings

1. `backtest/` is still H1-only. It does not reproduce the H1/M15/M5 experiment.
2. The committed `trade_simulator.py` exits at the fixed target and does not
   simulate the published partial/breakeven/trailing plan.
3. H-026 explicitly states that its five-year research script was not committed.
4. `MultiTimeframeEngine` labels missing/neutral M15 structure as `ALIGNED`; only
   explicit opposition is blocked. That behavior should be named `NOT_OPPOSED`,
   not `ALIGNED`, to avoid overstating execution confirmation.
5. The engine publishes both a 4R target and a trailing-runner plan, while H-026
   says trailing replaces a fixed runner exit. The execution rule must be made
   unambiguous before another outcome test.

## Recommended next action

Do not change the production decision policy from these results. First obtain
complete M15/M5 history (or regenerate both from one complete M1/M5 source), then
commit a reproducible multi-timeframe harness with:

- candle-completeness and closed-candle gates;
- explicit entry timestamp semantics and manual-delay scenarios;
- bid/ask spread, commission, and slippage sensitivity;
- one-trade-at-a-time portfolio accounting;
- partial/breakeven/trailing state-machine tests;
- yearly expanding-window evaluation and a final untouched holdout;
- reporting of censored trades and missing-day coverage;
- comparison of `NOT_OPPOSED`, `SAME_BIAS`, and `SAME_BIAS+BOS` M15 modes.

The provisional candidate for the next registered hypothesis is M15 same-bias
confirmation because it materially reduced drawdown. It must remain shadow-only
until complete-data results are positive across multiple years and realistic
cost/delay cases.
