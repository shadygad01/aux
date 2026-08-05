# Learning Constitution

Status: **IMMUTABLE — explicit approval is required for changes.**

## Mission and boundary

Learning is permanent and exists only to improve decision quality. It may never replace or modify Smart Money Concepts, premium/discount, liquidity philosophy, decision support, explainability, or trader-owned execution.

The subsystem has no production-policy mutation interface. It stores observations, creates research artifacts, calculates transparent cohort statistics, and emits validation- and approval-required recommendations. Deployment remains a separate human-approved workflow.

## Complete records

Every evaluated setup receives an append-only learning record containing its timestamp, referenced market snapshot, three-horizon bias, trade quality, location and premium/discount, liquidity, MACD, news, macro, DXY, real yields, session, SMC, supporting and contradicting evidence, decision, outcome, MFE, MAE, learning notes, and what changed afterward.

Outcomes cover pending, winning, losing, ignored, rejected, WAIT, missed, false positive, and false negative. Unknown MFE or MAE remains explicit `null`; it is never invented.

Every failure-like outcome creates a Level 3 working hypothesis. Every winning outcome creates Level 4 supporting evidence, not a production rule. Pending and WAIT records are stored without manufacturing a conclusion.

## Knowledge levels

1. Immutable principle — never changes.
2. Validated rule — backtested, forward tested, and approved.
3. Working hypothesis — promising and awaiting evidence.
4. Experimental — research only and never production eligible.
5. Rejected — historically disproven and never production eligible.

Every concept has exactly one level. Working hypotheses, experimental concepts, and rejected concepts cannot be marked production eligible. A Level 2 rule is rejected unless backtest, forward-test, and approval flags are all present.

## Confidence

Learning confidence is the geometric mean of five explicit normalized inputs: historical performance, repeatability, evidence quality, data quality, and sample-size adequacy. Sample adequacy is capped at one and calculated against the versioned `minimum_edge_sample` policy.

Edge statistics report the observed sample, wins, losses, and win rate. Non-winning/losing outcomes do not enter win-rate denominators. Empty cohorts report zero rather than invented performance.

## Recommendations

Every recommendation includes the current rule, proposed experiment, record references, historical statistics, expected impact, migration risk, confidence score and inputs, status, and mandatory approval flag. The learning subsystem rejects attempts to label its own recommendation approved.
