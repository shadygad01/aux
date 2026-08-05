# Decision Memory

Decision Memory is the permanent, append-only record of every evaluated decision. It records
evaluation state; it does not execute trades and it does not rewrite history.

## Identity and evolution

`DecisionMemory.create()` allocates an atomic, date-scoped identifier such as
`DECISION-20260805-000194`. `DecisionMemory.evolve()` appends the next contiguous version and
records field-level before/after changes plus the timestamp and reason. An evolution with no
observable change is rejected. Existing versions have no update or delete operation.

Each version contains the market and macro snapshots, horizon biases, trade quality, one of the
four decision outputs, all four graphs, referenced knowledge objects, reproducible confidence and
uncertainty, supporting and contradicting evidence, rejected alternatives, outcome, and lineage.

## Durable archive

`SqliteDecisionMemory` stores the complete versioned JSON record inside a SQLite transaction. ID
allocation uses an immediate transaction, preventing duplicate sequences across concurrent
processes. The adapter reconstructs domain objects from SQLite for both `latest()` and `search()`;
correctness never depends on an in-process cache.

The archive supports the constitution's four searches:

- BUY versions at or above a trade-quality threshold.
- failed BUY versions at or above a threshold.
- WAIT versions that later became BUY under the same decision identity.
- rejected decisions whose counterfactual outcome was winning.

“Forever” is an operational retention obligation, not a property SQLite can guarantee alone.
Production must back up the database, test restoration, control access, and define migrations for
future contract versions. The application deliberately exposes no deletion API.

## Integration boundary

The Decision Capability may archive only a complete `DecisionSnapshot`. Its smaller
`OfficialDecision` contract is not enough to manufacture the required graphs and snapshots.
Composition code must build the complete snapshot from referenced upstream contracts and call
Decision Memory as part of publishing an official production decision.
