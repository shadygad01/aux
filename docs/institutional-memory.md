# Institutional Memory

Institutional Memory is a unified, durable ledger over Gold Brain's specialized memories. It stores
canonical payloads for Research, Patterns, Failures, Successes, Macro Events, Market Regimes,
Historical Comparisons, Decision Evolution, and Knowledge Evolution. It does not replace the
specialized domain models; it preserves and indexes their valuable outputs under one contract.

Every entry has a deterministic identity derived from its category, event time, source reference,
and payload hash. SQLite stores the complete canonical payload and SHA-256 digest in an append-only
table. No update or delete method is exposed. Duplicate records fail rather than overwrite history,
and entries reconstruct after process restart.

At the end of a declared market day, `close_market_day()` refuses completion unless at least one new
memory occurred that day. The closure records new and cumulative counts plus a digest over the
day's payload hashes. This proves growth, not learning quality; Quality, Research, Knowledge, and
Governance gates still determine whether a memory is reliable or production eligible.

“Continuously” still requires orchestration. Production must connect each specialized append event
to this ledger transactionally, define the XAUUSD market calendar and timezone, retry failed writes,
monitor unclosed days, back up and restore SQLite, and periodically verify every payload hash. Until
those adapters exist, the ledger and daily closure gate are durable foundations—not a claim that
automatic daily capture is already operating.
