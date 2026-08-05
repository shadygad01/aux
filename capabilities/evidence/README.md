# Evidence Capability

Owns evaluation of one expiring evidence snapshot through a replaceable `EvidenceEvaluatorPort`. Input: typed evidence and evaluation time. Output: `EvidenceDecision`. Metrics and logs expose item count and recommendation. Health confirms evaluator configuration. No UI dependency.

Analysis also requires a current `MarketRegimeContext` and exactly one contextual interpretation
for every evidence item. Missing, stale, duplicate, or wrong-regime interpretations fail closed.
