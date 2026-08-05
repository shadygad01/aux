# Market Regime

Regimes overlap. Gold may simultaneously be trending, expanding, high-volatility, risk-off, and
news-driven. `MarketRegimeContext` therefore records one primary regime plus a unique set of active
regimes rather than forcing a false single-label classification.

Every context has identity, identification time, TTL, confidence, rationale, evidence references,
source, and policy version. It expires automatically. The primary regime must be active and the
classification cannot exist without evidence.

The public Evidence Capability refuses analysis unless the regime is current and every evidence ID
has exactly one `RegimeInterpretation` for that regime. Each interpretation states its contextual
meaning and adjusted importance. The public Reasoning Capability repeats the current-regime and
complete-interpretation gates before constructing a reasoning path. Thus a sweep in a range and a
sweep in expansion cannot silently share the same interpretation.

Compatibility Adapter application classes that predate the Capability architecture do not accept this contract and
are compatibility/research paths only. They must not be composed as the new production analysis
path. Production still needs a validated regime classifier, change detection, durable regime audit,
and monitoring that stops analysis when classification is missing or stale.
