# Hypothesis Register

This register prevents assumptions from becoming silent facts. Status values are `UNVALIDATED`, `TESTING`, `SUPPORTED`, or `REJECTED`.

| ID | Hypothesis | Initial implementation | Status | Required evidence |
|---|---|---|---|---|
| H-001 | A confirmed structure break is necessary before directional attention is justified. | Mandatory gate | UNVALIDATED | Labeled SMC sample, inter-rater definition, walk-forward comparison |
| H-002 | BUY attention belongs in discount and SELL attention in premium. | Mandatory philosophy rule | UNVALIDATED | Immutable project requirement; measure operational definitions, not removal |
| H-003 | A liquidity sweep needs displacement confirmation to support direction. | Mandatory gate | UNVALIDATED | Formal displacement definition and labeled-event study |
| H-004 | A 2% band around the dealing-range midpoint represents equilibrium. | `equilibrium_band=0.02` | UNVALIDATED | Sensitivity analysis across instruments, timeframes, and regimes |
| H-005 | Evidence older than four hours is unsuitable for the current decision. | `maximum_age=4h` | UNVALIDATED | Timeframe-aware decay analysis |
| H-006 | Structure/location/liquidity weights of 0.40/0.30/0.30 are useful attribution values. | Policy weights | UNVALIDATED | Ablation study; calibration and abstention analysis |
| H-007 | A score of 0.75 is an appropriate attention threshold. | `attention_threshold=0.75` | UNVALIDATED | Walk-forward utility evaluation with transaction-independent decision metrics |
| H-008 | Trading-quality attribution of 15 macro, 20 bias/alignment, 15 location, 15 liquidity, 10 MACD, and 25 SMC points is useful. | `TradingPolicy` points totaling 100 | UNVALIDATED | Component ablation, calibration, regime and horizon analysis |
| H-009 | A trading-quality threshold of 75 appropriately separates attention from WAIT. | `minimum_trade_quality=75` | UNVALIDATED | Walk-forward utility and abstention analysis |
| H-010 | Each documented macro contradiction should remove five points. | `macro_contradiction_penalty_points=5` | UNVALIDATED | Severity-labeled macro event study |
| H-011 | News confidence times ten points is a useful uncertainty penalty. | `news_confidence_penalty_points=10` | UNVALIDATED | Event-window analysis with duration and surprise controls |
| H-012 | Linear TTL decay represents evidence freshness adequately. | `Evidence.freshness` | UNVALIDATED | Compare linear, step, and exponential decay out of sample by evidence kind |
| H-013 | The geometric mean of strength, reliability, importance, historical performance, and confidence is a useful base evidence weight. | Version 3 evidence engine | UNVALIDATED | Calibration, ablation, and robustness against correlated attributes |
| H-014 | Directional weight 0.25 and confidence 60 are sufficient to form an opinion. | `EvidencePolicy` | UNVALIDATED | Abstention and false-attention analysis by regime |
| H-015 | Directional confidence times mandatory-evidence completeness is useful trade quality. | Version 3 quality formula | UNVALIDATED | Walk-forward calibration and decision-utility analysis |
| H-016 | A minimum edge cohort of 100 resolved winning/losing observations is adequate for initial research. | `LearningPolicy.minimum_edge_sample` | UNVALIDATED | Power analysis by base rate, effect size, horizon, and regime |
| H-017 | Absolute distance from a 50% win rate is a useful repeatability input. | Learning edge statistics | UNVALIDATED | Compare stability across rolling windows and market regimes |
| H-018 | The geometric mean of five learning-confidence inputs is suitably conservative. | `LearningConfidence.score` | UNVALIDATED | Calibration and sensitivity analysis; inspect zero-factor behavior |
| H-019 | Source ranking weights of 25/15/20/20/15/5 appropriately combine reliability, freshness, authority, historical accuracy, transparency, and inverse bias. | `KnowledgePolicy` | UNVALIDATED | Source-outcome calibration and sensitivity analysis |
| H-020 | Linear review freshness is appropriate for all source types. | `SourceProfile.freshness` | UNVALIDATED | Source-type-specific decay study |
| H-021 | Sample-weighted aggregation across validated patterns answers premium/sweep failure questions without unacceptable regime distortion. | Knowledge question engine | UNVALIDATED | Stratify by session, horizon, volatility, and regime |
| H-022 | Evidence confidence multiplied by average validated-knowledge reliability/confidence is a useful reasoning reliability measure. | Version 4 reasoning engine | UNVALIDATED | Calibration, ablation, and stale-knowledge sensitivity analysis |
| H-023 | A reliable evidence threshold of 0.05 is appropriate for reasoning-stage completion. | `ReasoningPolicy` | UNVALIDATED | Abstention and stage-failure analysis by evidence type |
| H-024 | An H1 MACD line below zero for BUY / above zero for SELL is a necessary directional filter. | Mandatory gate, `DecisionEngine` (contributes no score) | UNVALIDATED | Labeled directional sample; walk-forward comparison with and without the gate |
| H-025 | A break of structure remains valid for 10 candles after it occurs, allowing a retracement into discount/premium on a later candle to still count as a confirmed break. | `BOS_LOOKBACK=10`, `smc_detector.classify_structure` | UNVALIDATED | Sensitivity analysis on lookback length; walk-forward comparison against the instantaneous (lookback=1) definition |

## Change protocol

1. State the proposed change and expected mechanism.
2. Freeze a baseline policy version.
3. Define data, labels, leakage controls, metrics, and rejection criteria before testing.
4. Compare on out-of-sample periods and relevant market regimes.
5. Document failures and uncertainty, not only aggregate improvement.
6. Request approval before changing decision behavior.

## Open follow-ups

- **A real walk-forward harness now exists (`backtest/`) but has not yet been run.** It replays
  real historical H1 candles through the unmodified production `DecisionEngine`/`DecisionPolicy`
  and can produce real evidence for H-001 through H-007, H-024, and H-025 -- the hypotheses the
  live canonical pipeline actually runs on (H-008 onward, excluding H-024, belong to
  `capabilities/*`'s dormant policies and this harness does not address them). No run has happened
  yet: this repository's own execution environment cannot reach Yahoo Finance (network policy).
  Run it from an environment with real network access:
  ```
  python -m backtest.cli --ticker GC=F --days 365 --output-dir backtest/reports/ --sensitivity
  ```
  See `backtest/README.md` for what the results do and do not prove, then follow the change
  protocol above before moving any status off `UNVALIDATED`.
- **H-007 finding (discovered while testing the sensitivity sweep, not yet acted on):**
  `DecisionEngine` only reaches `verdict = candidate` (required for any BUY/SELL) when
  `not conflicts` -- and structure/location/liquidity each either fully contribute their weight or
  add a conflict, so `not conflicts` implies `score == 1.0` exactly (0.40+0.30+0.30) whenever a
  candidate direction exists. Since `DecisionPolicy` requires `attention_threshold <= 1.0`, that
  score trivially clears every valid threshold -- in the current engine, `attention_threshold`
  cannot reject a conflict-free candidate at all. H-007 is not falsifiable by threshold variation
  alone until this score-vs-conflicts relationship changes; see
  `backtest/statistics.py::sensitivity_sweep`'s docstring for the full derivation. This is a
  finding, not a fix applied here -- changing `DecisionEngine`'s scoring logic is a live-decision
  methodology change requiring explicit approval, the same as H-025's `BOS_LOOKBACK` was.
