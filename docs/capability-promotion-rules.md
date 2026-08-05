# Capability Promotion Rules

| Score | Label | Minimum evidence |
|---:|---|---|
| 0 | Concept | Mission exists; implementation evidence absent or stale |
| 20 | Prototype | Bounded experiment, named owner, risks, and disposal path |
| 40 | Architecture Ready | Canonical ownership, ADRs, interfaces, contract plan, dependency map |
| 60 | Implementation Ready | Implementation, published contracts, tests, documentation, known debt |
| 80 | Production Candidate | Production-like validation, measured performance, durable audit, complete explainability, no critical blocker |
| 100 | Institutional Production | Proven operations, current research, signed approval, monitored SLOs, recovery evidence |

Before Production, each capability must independently pass Architecture, Documentation, Tests,
Research, Explainability, and Governance. Missing or expired evidence blocks promotion.

Promotion evidence includes revision hash, assessor, timestamp, contracts, test run, research,
explainability, blockers, effort, and Institutional Quality Gate ID. Self-attestation by the owner
cannot satisfy final Governance approval.

Critical blockers cap readiness at 60. Missing canonical ownership or a public contract caps it at
40. A prototype-only required subprofile caps its owner at 40; an absent required subprofile caps
its owner at 20. Regression and demotion use the same evidence rules as promotion.
