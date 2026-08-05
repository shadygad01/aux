# Quality Assurance

A sprint is not complete because code was merged or tests passed. `InstitutionalQualityGate` issues
an append-only completion record only after exactly one approved review exists for Architecture,
Trading, Research, Learning, Documentation, Testing, Performance, Security, Explainability, and
Maintainability.

Every review includes hostile/red-team findings and identifies its reviewer, evidence references,
and timestamp. Any
`CHANGES_REQUIRED` verdict blocks completion. The gate separately requires evidence that
documentation, tests, and architecture remain synchronized; six approvals cannot bypass a failed
synchronization check.

CI runs formatting, lint, strict typing, architecture tests, the entire behavioral suite, and the
coverage threshold. A synchronization test additionally fails when a published JSON schema is
missing from the contracts catalog. Human review evidence must reference the relevant diff,
analysis, benchmark, trading-policy review, or research audit rather than merely state “approved.”

The included audit is in-memory for composition and tests. Production sprint/release enforcement
requires durable review storage, reviewer identity verification, artifact commit/hash binding,
freshness rules, and branch protection that requires the completion ID.
