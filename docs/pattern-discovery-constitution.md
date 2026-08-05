# Pattern Discovery

Pattern Discovery belongs to the Research Capability. It consumes referenced observations from
historical market data, Decision Memory, evidence graphs, the Knowledge Base, Learning Records,
and macro events. It never mutates production policy.

Every `DiscoveredPattern` records its identity, description, supporting evidence and source types,
sample size, complementary win/failure rates, sessions, macro context, confidence, lifecycle
status, validation record, review time, revision, and change reason. A single event is rejected.

## Promotion gates

The lifecycle is append-only and sequential:

1. `EXPERIMENTAL` — discovery only; never production eligible.
2. `OBSERVED` — requires documented statistical significance and at least two repeatability runs.
3. `VALIDATED` — additionally requires backtesting.
4. `INSTITUTIONAL_PATTERN` — additionally requires forward testing and documentation. This is the
   only production-eligible status.
5. `DEPRECATED` — removes the pattern from production eligibility without deleting its history.

Validation booleans are claims, not proof by themselves. Each significance or testing claim must
carry immutable references to the statistical report, dataset/version, test window, methodology,
and results. A future production adapter must retain those referenced artifacts and use a durable,
restart-safe append-only repository; the included in-memory adapter is for composition and tests.
