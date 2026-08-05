# Project Readiness Formula

Let `C` be all ten canonical capabilities in ADR-0001. Each score `r(c)` must be one of
`0, 20, 40, 60, 80, 100` and have current evidence.

```text
Project Readiness = min(r(c) for c in C)
```

Current inputs: `40, 40, 60, 60, 40, 40, 60, 40, 20, 20`.

Current derived Project Readiness: **20 — Prototype**.

The dashboard also reports the distribution and median (`40`). The arithmetic mean is not a
readiness result because it lets stronger capabilities conceal a production-path blocker. Missing
or stale evidence forces the affected capability to `0` until reassessed.

The result does not grant production permission. Every capability must score at least 80 and pass
Architecture, Documentation, Tests, Research, Explainability, and Governance. Institutional
Production requires every capability at 100 and a revision-bound Institutional Quality Gate record.
