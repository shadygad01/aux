# Constitutional Governance

Governance authorizes changes; it does not implement them. Every request identifies the artifact,
governed domain, authority level, requester, applying actor, evidence, time, and proposed change.
Every authorization or rejection is appended to an audit record with explicit reasons.

## Authority policy

- Level 1 — Immutable Principles and the Decision Constitution. Only the project owner may apply a
  revision, and an explicit owner-approval reference is mandatory. “Immutable” means immutable to
  every subsystem and automation; the constitution's owner-approval clause is the sole exception.
- Level 2 — Validated Trading Rules. Research may request a revision, but only the project owner
  may apply it after research, backtesting, documentation, and owner approval are all referenced.
- Level 3 — Implementation. The implementation actor may apply changes only when the request
  attests that observable logic remains identical.
- Level 4 — Performance Improvements. Automation may apply changes only with passing-test evidence.
- Level 5 — Documentation. The documentation actor may continuously improve documentation.

The domain-to-level mapping is fixed, preventing a Trading Constitution change from being
mislabelled as documentation. Learning and Research have no apply authority. Learning cannot modify
the Trading Constitution; Research cannot modify the Decision Constitution. Both may contribute
evidence or submit requests for authorized actors to review.

An authorization record is necessary but not sufficient operational security. Production mutation
paths must require the authorization ID, verify it against durable append-only storage, bind it to
the exact artifact revision/hash, and enforce repository protections. The included in-memory audit
is for composition and tests and must not be described as production governance.
