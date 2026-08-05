# Decision Engine Constitution

Status: **IMMUTABLE — explicit approval is required for changes.**

## Authority

The Decision Engine never predicts and never executes. It evaluates whether current evidence justifies paying attention to BUY or SELL.

Its only recommendations are:

- `BUY_SETUPS_ONLY`
- `SELL_SETUPS_ONLY`
- `WAIT`
- `NO_OPINION`

`NO_OPINION` means reliable evidence is insufficient to establish directional attention. `WAIT` means reliable directional context exists but execution conditions are incomplete, quality is below threshold, or an active pause/rejection condition remains.

## Evidence contract

Every evidence item records strength, reliability, freshness, importance, historical performance, confidence, observed time, time to live, source, and rationale. These values are evidence—not truth.

Freshness is calculated at evaluation time:

`freshness = max(0, 1 - age / TTL)`

Future-dated evidence receives zero effective weight. Effective weight is reproducible:

`geometric_mean(strength, reliability, importance, historical_performance, confidence) × freshness`

Expired evidence therefore reaches zero automatically. The engine is stateless: supplying an updated evidence snapshot or a later evaluation time recalculates every weight without hidden state.

## Confidence and quality

Directional confidence is:

`abs(BUY weight - SELL weight) / (BUY weight + SELL weight) × 100`

Trade quality is directional confidence multiplied by the fraction of mandatory execution evidence currently reliable. Every intermediate freshness and effective weight is returned in the decision record.

The formulas are hypotheses, not fixed truth. They may change only through a new policy version after documented research and approval; the constitutional semantics may not change without explicit approval.

## Explainability

Every output contains `why`, `why_not`, `missing`, and `what_would_change`. `WAIT` always names its incomplete conditions. `NO_OPINION` identifies the reliable directional foundation needed to form an opinion.

Active news pauses map to `WAIT` with an expiry/release condition; they never introduce a fifth recommendation.
