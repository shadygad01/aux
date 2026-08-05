# Research Governance

Research is encouraged and permanently separated from production authority. The canonical
`ResearchProposal` contains a question, hypothesis, method, evidence references, reproducible
statistics, risk, expected gain, confidence, migration impact, timestamp, and identity.

Its only status is `PROPOSAL`; `production_eligible` is structurally always false. Research has no
deployment or policy-mutation method. A useful result may support a separate constitutional change
request, but it must then pass the applicable Governance level—including backtesting,
documentation, approval, and the authorized applying actor. A proposal is never that approval.

Confidence must equal the confidence attached to the proposal's statistics. Missing evidence or
any missing narrative field rejects the proposal. Evidence references should resolve to immutable
datasets, Decision Memory cohorts, methods, code versions, and statistical outputs.

`LearningRecommendation` remains a compatibility learning-improvement output and is also
non-production. New Research Capability proposals use `ResearchProposal 1.0`; callers must not
present compatibility recommendations as governed research proposals.

The included archive is in-memory for tests and composition. Production requires durable,
append-only proposal storage, artifact hashes, and reproducible statistical bundles.
