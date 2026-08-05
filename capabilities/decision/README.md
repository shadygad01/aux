# Decision Capability

Owns authorization of a complete nine-stage reasoning result as `OfficialDecision`. It rejects incomplete paths, emits decision metrics/logs, and reports health. It does not collect, normalize, reason, publish, or execute trades.

Permanent memory is provided by the independent `DecisionMemory` application service. Production
composition must provide its complete `DecisionSnapshot`; the reduced `OfficialDecision` object is
intentionally not expanded with invented graph or snapshot data. See
`docs/decision-memory-constitution.md`.

`OfficialDecision 2.0` also requires all eight constitutional explanation answers and complete
reasoning-to-source traces. The Decision Capability rejects mismatched recommendations. See
`docs/explainability-constitution.md`.

`OfficialDecision 3.0` additionally requires a reproducible trust manifest with explicit facts,
contradictions, confidence, uncertainty, audit/calculation references, and canonical input hash.
See `docs/trust-constitution.md`.

`OfficialDecision 4.0` binds authorization to the same non-expired `CurrentMarketState` consumed by
Evidence and Reasoning.

`OfficialDecision 5.0` additionally requires an approved professional-trader comprehension review.
